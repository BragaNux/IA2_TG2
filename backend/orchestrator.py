"""Orquestração da inferência: guardrail de entrada -> loop de tool use (Claude + MCP) -> guardrail de saída.

O loop é manual (e não o tool runner do SDK) para que a aplicação controle e registre cada
chamada de tool, colete os trechos recuperados e os entregue ao guardrail de saída.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field

import anthropic

from rag.config import ANTHROPIC_EFFORT, ANTHROPIC_MODEL

from backend import guardrails as gr
from backend.mcp_client import MCPToolClient, ToolCallRecord
from backend.prompts import NO_EVIDENCE_MARKER, SYSTEM_PROMPT

log = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 4        # limita o loop de tool use (economia de tokens)
MAX_HISTORY_MESSAGES = 4
MAX_OUTPUT_TOKENS = 4096   # teto por chamada; respostas esperadas têm ~250 palavras

NO_EVIDENCE_ANSWER = ("Não encontrei informações suficientes sobre isso nos manuais consultados. "
                      "Se for uma situação de urgência, ligue 192 (SAMU) ou 193 (Bombeiros).")
BLOCKED_OUTPUT_ANSWER = ("Não consegui gerar uma resposta suficientemente fundamentada nos documentos para esta "
                         "pergunta. Veja abaixo os trechos mais relevantes encontrados, ou reformule a pergunta. "
                         "Em caso de urgência, ligue 192 (SAMU) ou 193 (Bombeiros).")


@dataclass
class Source:
    ref: int
    chunk_id: str
    doc_id: str
    document_title: str
    organization: str | None
    pages: str
    topic: str
    score: float
    excerpt: str


@dataclass
class ChatResult:
    status: str                    # answered | answered_with_warning | no_evidence | blocked_input | blocked_output | error
    answer: str
    emergency: bool = False
    sources: list[Source] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    input_guardrail: dict | None = None
    output_guardrail: dict | None = None
    usage: dict = field(default_factory=dict)
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


class Orchestrator:
    def __init__(self, mcp: MCPToolClient, client: anthropic.AsyncAnthropic | None = None,
                 model: str = ANTHROPIC_MODEL, effort: str = ANTHROPIC_EFFORT) -> None:
        self.mcp = mcp
        self.client = client or anthropic.AsyncAnthropic()
        self.model = model
        self.effort = effort
        self.tools = mcp.anthropic_tools()

    # ------------------------------------------------------------------ guardrail de entrada

    async def check_input(self, question: str, usage: dict) -> tuple[gr.InputCheck, ToolCallRecord | None]:
        blocked = gr.rule_based_check(question)
        if blocked:
            return blocked, None

        # A sondagem de similaridade também passa pelo MCP (o backend não acessa o banco diretamente)
        probe = await self.mcp.call("search_knowledge", {"query": question[:500], "top_k": 1})
        top_score = probe.result["results"][0]["score"] if probe.result and probe.result["results"] else 0.0
        blocked = gr.similarity_floor_check(question, top_score)
        if blocked:
            return blocked, probe

        cls, cls_usage = await gr.llm_classify(self.client, self.model, question)
        _accumulate_usage(usage, cls_usage)
        emergency = cls.emergencia_em_andamento or gr.detect_emergency(question)
        allowed = cls.categoria == "primeiros_socorros"
        return gr.InputCheck(allowed, cls.categoria, cls.justificativa, emergency=emergency, layer="llm",
                             top_score=top_score), probe

    # ------------------------------------------------------------------ fluxo principal

    async def answer(self, question: str, history: list[dict] | None = None) -> ChatResult:
        t0 = time.perf_counter()
        usage = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "llm_calls": 0}

        try:
            in_check, probe = await self.check_input(question, usage)
        except anthropic.APIError as e:
            log.exception("Falha no classificador de entrada")
            return ChatResult("error", f"Erro ao consultar o modelo: {e.__class__.__name__}", elapsed_ms=_ms(t0))

        probe_calls = [_tool_call_dict(probe, purpose="guardrail_entrada")] if probe else []
        if not in_check.allowed:
            return ChatResult("blocked_input", gr.BLOCK_MESSAGES.get(in_check.category, gr.BLOCK_MESSAGES["fora_do_escopo"]),
                              emergency=in_check.emergency, tool_calls=probe_calls,
                              input_guardrail=in_check.to_dict(), usage=usage, elapsed_ms=_ms(t0))

        messages = _history_to_messages(history) + [{"role": "user", "content": question}]
        if in_check.emergency:
            # Instrução do operador no meio da conversa (mensagem de sistema após a do usuário)
            messages.append({"role": "system", "content": "O classificador de entrada indicou uma emergência em "
                             "andamento: comece a resposta orientando ligar 192 (SAMU) ou 193 (Bombeiros)."})

        retrieved: dict[str, dict] = {}
        tool_calls: list[dict] = list(probe_calls)
        final_text, stop_reason = "", None

        try:
            for _ in range(MAX_TOOL_ROUNDS):
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=MAX_OUTPUT_TOKENS,
                    system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
                    tools=self.tools,
                    messages=messages,
                    output_config={"effort": self.effort},
                )
                _accumulate_usage(usage, response.usage)
                stop_reason = response.stop_reason

                if stop_reason == "pause_turn":
                    messages.append({"role": "assistant", "content": response.content})
                    continue
                if stop_reason != "tool_use":
                    final_text = "".join(b.text for b in response.content if b.type == "text").strip()
                    break

                messages.append({"role": "assistant", "content": response.content})
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                records = await asyncio.gather(*(self.mcp.call(b.name, dict(b.input)) for b in tool_uses))

                results = []
                for block, rec in zip(tool_uses, records):
                    tool_calls.append(_tool_call_dict(rec, purpose="llm"))
                    _collect_chunks(rec, retrieved)
                    content = rec.error if rec.is_error else json.dumps(_compact_for_llm(rec.result), ensure_ascii=False)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": content,
                                    "is_error": rec.is_error})
                messages.append({"role": "user", "content": results})   # todos os resultados numa só mensagem
            else:
                final_text = ""
                stop_reason = "max_rounds"
        except anthropic.APIError as e:
            log.exception("Falha na chamada ao modelo")
            return ChatResult("error", f"Erro ao consultar o modelo: {e.__class__.__name__}", tool_calls=tool_calls,
                              input_guardrail=in_check.to_dict(), usage=usage, elapsed_ms=_ms(t0))

        if stop_reason == "refusal":
            return ChatResult("blocked_output", "O modelo recusou responder a esta solicitação.",
                              emergency=in_check.emergency, tool_calls=tool_calls,
                              input_guardrail=in_check.to_dict(), usage=usage, elapsed_ms=_ms(t0))

        # ------------------------------------------------------------ guardrail de saída
        out_check = gr.check_output(final_text, {cid: c["content"] for cid, c in retrieved.items()}, question)

        if out_check.status == "no_evidence":
            answer = final_text.replace(NO_EVIDENCE_MARKER, "").strip() or NO_EVIDENCE_ANSWER
            sources = []
        elif out_check.status == "blocked_output":
            answer = BLOCKED_OUTPUT_ANSWER
            top = sorted(retrieved.values(), key=lambda c: -c["score"])[:3]
            sources = [_source(i + 1, c) for i, c in enumerate(top)]
        else:
            answer, sources = _number_citations(final_text, out_check.cited_ids, retrieved)

        return ChatResult(out_check.status, answer, emergency=in_check.emergency, sources=sources,
                          tool_calls=tool_calls, input_guardrail=in_check.to_dict(),
                          output_guardrail=out_check.to_dict(), usage=usage, elapsed_ms=_ms(t0))


# ---------------------------------------------------------------------- utilitários

def _ms(t0: float) -> float:
    return round((time.perf_counter() - t0) * 1000, 1)


def _history_to_messages(history: list[dict] | None) -> list[dict]:
    msgs = [{"role": h["role"], "content": h["content"]} for h in (history or [])
            if h.get("role") in ("user", "assistant") and h.get("content")]
    msgs = msgs[-MAX_HISTORY_MESSAGES:]
    while msgs and msgs[0]["role"] != "user":   # a conversa precisa começar com o usuário
        msgs.pop(0)
    return msgs


def _accumulate_usage(total: dict, u) -> None:
    total["llm_calls"] += 1
    total["input_tokens"] += u.input_tokens or 0
    total["output_tokens"] += u.output_tokens or 0
    total["cache_read_input_tokens"] += getattr(u, "cache_read_input_tokens", 0) or 0


def _tool_call_dict(rec: ToolCallRecord, purpose: str) -> dict:
    summary = None
    if rec.result and "results" in rec.result:
        summary = [{"chunk_id": h["chunk_id"], "score": h["score"]} for h in rec.result["results"]]
    elif rec.result:
        summary = {k: v for k, v in rec.result.items() if k not in ("content", "topics", "documents")}
    return {"name": rec.name, "arguments": rec.arguments, "duration_ms": round(rec.duration_ms, 1),
            "is_error": rec.is_error, "error": rec.error, "purpose": purpose, "result_summary": summary}


def _compact_for_llm(result: dict) -> dict:
    """Envia ao LLM só o necessário dos resultados de busca (economia de tokens).

    A versão completa (scores, órgão, doc_id) continua guardada para o guardrail e a interface.
    """
    if "results" not in result:
        return result
    return {"results": [
        {"chunk_id": h["chunk_id"], "documento": h["document_title"],
         "paginas": f"{h['page_start']}-{h['page_end']}", "conteudo": h["content"]}
        for h in result["results"]
    ]}


def _collect_chunks(rec: ToolCallRecord, retrieved: dict[str, dict]) -> None:
    if rec.is_error or not rec.result:
        return
    for h in rec.result.get("results", []):
        prev = retrieved.get(h["chunk_id"])
        if not prev or h["score"] > prev["score"]:
            retrieved[h["chunk_id"]] = h


def _source(ref: int, c: dict) -> Source:
    pages = f"{c['page_start']}" if c["page_start"] == c["page_end"] else f"{c['page_start']}-{c['page_end']}"
    return Source(ref, c["chunk_id"], c["doc_id"], c["document_title"], c.get("organization"), pages,
                  c["topic"], c["score"], c["content"][:600])


def _number_citations(text: str, cited_ids: list[str], retrieved: dict[str, dict]) -> tuple[str, list[Source]]:
    """Troca [chunk_id] por [1], [2]... e monta a lista de fontes na mesma ordem.

    Citações a trechos não recuperados (inválidas) são removidas do texto.
    """
    refs = {cid: i + 1 for i, cid in enumerate(cited_ids)}

    def repl(m: re.Match) -> str:
        ids = re.findall(r"[a-z0-9_]+#\d+", m.group(0))
        nums = sorted({refs[i] for i in ids if i in refs})
        return "".join(f"[{n}]" for n in nums)

    text = re.sub(r"\[[^\[\]]*#\d+[^\[\]]*\]", repl, text)
    text = re.sub(r"[ \t]+([.,;:])", r"\1", text)
    sources = [_source(refs[cid], retrieved[cid]) for cid in cited_ids]
    return text.strip(), sources
