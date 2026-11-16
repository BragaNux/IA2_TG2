"""Guardrails de entrada e de saída.

ENTRADA (em camadas, da mais barata para a mais cara):
  1. Regras: mensagem vazia/longa demais e padrões conhecidos de prompt injection (regex).
  2. Piso de similaridade: se nenhum trecho da base passa de um score mínimo e não há vocabulário
     de primeiros socorros, a pergunta é rejeitada sem gastar LLM.
  3. Classificador com LLM (saída estruturada): primeiros socorros x fora do escopo x prescrição
     médica x prompt injection x conteúdo nocivo, além de detectar emergência em andamento.

SAÍDA (programática, sobre a resposta e os trechos efetivamente recuperados via MCP):
  1. Precisa ter havido recuperação (sem trechos -> sem fundamento).
  2. Citações: cada [chunk_id] citado precisa estar entre os recuperados; exige ao menos uma válida.
  3. Suporte por frase: cada frase da resposta precisa ter similaridade semântica OU sobreposição
     lexical suficiente com alguma frase dos trechos recuperados.
  4. Números (tempos, quantidades) citados precisam aparecer nos trechos.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Literal

import anthropic
import numpy as np
from pydantic import BaseModel, Field

from rag.embeddings import embed_texts
from rag.topics import TOPICS, normalize

from backend.prompts import CLASSIFIER_PROMPT, NO_EVIDENCE_MARKER

MAX_INPUT_CHARS = 1000
SIMILARITY_FLOOR = 0.25          # abaixo disso, sem vocabulário do domínio, rejeita sem LLM
SENTENCE_SIM_THRESHOLD = 0.60    # suporte semântico frase-a-frase
LEXICAL_THRESHOLD = 0.60         # fração de palavras de conteúdo da frase presentes no contexto
BLOCK_RATIO = 0.50               # suporte abaixo disso -> resposta bloqueada
WARN_RATIO = 0.75                # suporte abaixo disso -> resposta com aviso
EMERGENCY_NUMBERS = {"190", "192", "193", "199", "188"}

# ----------------------------------------------------------------------------- ENTRADA

_INJECTION_PATTERNS = [
    r"(ignore|ignora|esqueca|esqueça|desconsidere|desconsidera|descarte)\w*\s+(todas?\s+)?(as\s+|os\s+|suas\s+|seus\s+)?(instruc|regra|orientac|diretriz|comando|prompt)",
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules)",
    r"(prompt|instruc\w*)\s+(do\s+|de\s+)?sistema",
    r"system\s*prompt",
    r"(revele|mostre|repita|imprima|exiba|vaze)\w*\s+((o|a|os|as|me|seu|sua|seus|suas)\s+){0,3}(prompt|instruc|configurac|regras)",
    r"(voce|tu)\s+agora\s+(e|eh|sera|vai ser)\s+",
    r"a\s+partir\s+de\s+agora\s+(voce|responda|aja|seja)",
    r"(finja|fingir|aja como|atue como|faca de conta|roleplay|interprete o papel)",
    r"\b(dan|jailbreak|modo\s+desenvolvedor|developer\s+mode|sem\s+restric\w*|sem\s+filtro)\b",
    r"</?\s*(system|assistant|instructions?)\s*>",
    r"novas?\s+instruc\w*\s*:",
]
_INJECTION_RE = [re.compile(p) for p in _INJECTION_PATTERNS]

_EMERGENCY_RE = re.compile(
    r"(nao (esta|ta) respirando|parou de respirar|sem respirar|desmaiou|desacordad|inconscient|"
    r"convulsionando|tendo (uma )?convuls|sangrando muito|nao para de sangrar|engasgad[oa] agora|"
    r"esta engasgad|ta engasgad|roxo|engoliu|bebeu (agua sanitaria|veneno|soda)|levou um choque|se afogou)"
)

_DOMAIN_TERMS = {kw for spec in TOPICS.values() for kw in spec["keywords"] if len(kw) > 4} | {
    "socorr", "emergenc", "urgenc", "desmai", "sangr", "respir", "mordeu", "mordid", "picad", "queim",
    "engas", "machuc", "ferid", "acidente", "vitima", "samu", "bombeiro", "pulso", "inconsc", "torc",
    "caiu", "queda", "bateu a cabeca", "engoliu", "intoxic", "afog",
}


class InputClassification(BaseModel):
    categoria: Literal["primeiros_socorros", "fora_do_escopo", "prescricao_medica",
                       "prompt_injection", "conteudo_nocivo"]
    emergencia_em_andamento: bool
    justificativa: str = Field(description="Uma frase curta explicando a classificação")


@dataclass
class InputCheck:
    allowed: bool
    category: str
    reason: str
    emergency: bool = False
    layer: str = ""                       # regras | similaridade | llm
    top_score: float | None = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


BLOCK_MESSAGES = {
    "prompt_injection": "Não posso atender a esse pedido. Posso ajudar com orientações de primeiros socorros, "
                        "como agir em engasgos, queimaduras, sangramentos ou desmaios.",
    "fora_do_escopo": "Sou um assistente de primeiros socorros e só respondo dúvidas sobre como agir em acidentes "
                      "e emergências, com base em manuais oficiais. Pode me perguntar, por exemplo, "
                      "\"o que fazer em caso de queimadura?\".",
    "prescricao_medica": "Não posso indicar medicamentos, doses ou diagnósticos: isso exige avaliação de um "
                         "profissional de saúde. Procure atendimento médico ou ligue 192 (SAMU) em caso de urgência. "
                         "Posso orientar sobre os primeiros socorros enquanto a ajuda não chega.",
    "conteudo_nocivo": "Não posso ajudar com isso. Se alguém estiver em perigo, ligue 190 (Polícia) ou 192 (SAMU).",
    "invalida": "Mensagem inválida. Escreva sua dúvida de primeiros socorros em até 1000 caracteres.",
}


def detect_emergency(text: str) -> bool:
    return bool(_EMERGENCY_RE.search(normalize(text)))


def rule_based_check(text: str) -> InputCheck | None:
    """Camada 1. Retorna um bloqueio, ou None se passou nas regras."""
    stripped = text.strip()
    if not stripped or len(stripped) > MAX_INPUT_CHARS:
        return InputCheck(False, "invalida", f"Mensagem vazia ou com mais de {MAX_INPUT_CHARS} caracteres", layer="regras")
    norm = normalize(stripped)
    for pat in _INJECTION_RE:
        m = pat.search(norm)
        if m:
            return InputCheck(False, "prompt_injection", "Padrão de manipulação de instruções detectado",
                              layer="regras", details={"padrao": m.group(0)})
    return None


def has_domain_vocabulary(text: str) -> bool:
    norm = normalize(text)
    return any(term in norm for term in _DOMAIN_TERMS)


def similarity_floor_check(text: str, top_score: float) -> InputCheck | None:
    """Camada 2. Rejeita sem LLM o que está claramente longe da base."""
    if top_score < SIMILARITY_FLOOR and not has_domain_vocabulary(text):
        return InputCheck(False, "fora_do_escopo",
                          f"Similaridade máxima com a base ({top_score:.2f}) abaixo do piso {SIMILARITY_FLOOR}",
                          layer="similaridade", top_score=top_score)
    return None


async def llm_classify(client: anthropic.AsyncAnthropic, model: str, text: str):
    """Camada 3. Classificação com saída estruturada (JSON validado por Pydantic).

    Retorna (InputClassification, usage)."""
    resp = await client.messages.parse(
        model=model,
        max_tokens=1024,
        system=CLASSIFIER_PROMPT,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"<mensagem>\n{text}\n</mensagem>"}],
        output_format=InputClassification,
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        # Falha fechada: se o classificador recusar, tratamos como conteúdo nocivo
        return InputClassification(categoria="conteudo_nocivo", emergencia_em_andamento=False,
                                   justificativa="Classificador recusou a mensagem"), resp.usage
    return resp.parsed_output, resp.usage


# ----------------------------------------------------------------------------- SAÍDA

_CITATION_RE = re.compile(r"\b([a-z0-9_]+#\d+)\b")
_NUMBER_RE = re.compile(r"(?<![#\w])(\d+(?:[.,]\d+)?)(?![\w#])")
_STOPWORDS = set(normalize(
    "a o os as um uma uns umas de do da dos das em no na nos nas por para pelo pela com sem que se e ou mas "
    "como mais menos muito pouco ja nao sim ao aos sua seu suas seus ele ela eles elas isso isto esse essa "
    "este esta ser estar ter fazer pode deve caso quando onde entre sobre ate apos antes depois tambem vez "
    "voce pessoa vitima sempre nunca cada outro outra mesmo assim entao porque pois forma modo"
).split())
# Frases de segurança padrão não precisam de fundamento documental
_SAFE_BOILERPLATE = re.compile(r"(192|193|samu|bombeiros|atendimento medico|profissional de saude|procure ajuda|"
                               r"fontes divergem|orientacao mais recente|divergencia entre)")
_LIST_MARKER = re.compile(r"^\s*\d+[.)]\s", re.MULTILINE)
_YEAR = re.compile(r"^(19|20)\d{2}$")


@dataclass
class SentenceCheck:
    sentence: str
    supported: bool
    semantic_score: float
    lexical_score: float


@dataclass
class OutputCheck:
    status: str                       # answered | answered_with_warning | no_evidence | blocked_output
    reason: str
    support_ratio: float | None = None
    cited_ids: list[str] = field(default_factory=list)
    invalid_citations: list[str] = field(default_factory=list)
    unsupported_numbers: list[str] = field(default_factory=list)
    sentences: list[SentenceCheck] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _split_sentences(text: str) -> list[str]:
    text = re.sub(r"\[[^\]]*#\d+[^\]]*\]", " ", text)          # remove citações
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [re.sub(r"^\s*(\d+[.)]|[-*•])\s*", "", p).strip() for p in parts if p.strip()]


def _content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", normalize(text)) if w not in _STOPWORDS}


def check_output(answer: str, retrieved: dict[str, str], question: str = "") -> OutputCheck:
    """retrieved: {chunk_id: conteúdo} de todos os trechos recuperados via MCP neste turno.
    question: pergunta do usuário (números citados nela, como a idade, não exigem respaldo)."""
    if answer.strip().startswith(NO_EVIDENCE_MARKER):
        return OutputCheck("no_evidence", "O modelo indicou que a base não tem evidência suficiente")
    if not retrieved:
        return OutputCheck("blocked_output", "Resposta gerada sem nenhum trecho recuperado da base")

    cited = list(dict.fromkeys(_CITATION_RE.findall(answer)))
    valid = [c for c in cited if c in retrieved]
    invalid = [c for c in cited if c not in retrieved]
    if not valid:
        return OutputCheck("blocked_output", "Resposta sem citação válida dos trechos recuperados",
                           cited_ids=cited, invalid_citations=invalid)

    context = "\n".join(retrieved.values())
    norm_context = normalize(context)
    context_words = _content_words(context)

    # Suporte frase-a-frase
    sentences = [s for s in _split_sentences(answer)
                 if len(s.split()) >= 5 and not _SAFE_BOILERPLATE.search(normalize(s))]
    evidence = [s for s in _split_sentences(context) if len(s.split()) >= 3]
    checks: list[SentenceCheck] = []
    if sentences and evidence:
        sims = embed_texts(sentences) @ embed_texts(evidence).T
        for i, s in enumerate(sentences):
            words = _content_words(s)
            lex = len(words & context_words) / len(words) if words else 1.0
            sem = float(np.max(sims[i]))
            checks.append(SentenceCheck(s, sem >= SENTENCE_SIM_THRESHOLD or lex >= LEXICAL_THRESHOLD,
                                        round(sem, 3), round(lex, 3)))
    ratio = (sum(c.supported for c in checks) / len(checks)) if checks else 1.0

    # Números citados (ex.: "30 compressões", "20 minutos") precisam constar nos trechos
    answer_no_cites = _LIST_MARKER.sub(" ", re.sub(r"\[[^\]]*\]", " ", answer))   # sem citações e sem "1.", "2."
    question_numbers = set(_NUMBER_RE.findall(question))
    numbers = {n for n in _NUMBER_RE.findall(answer_no_cites)
               if n not in EMERGENCY_NUMBERS and n not in question_numbers and not _YEAR.match(n)}
    unsupported_numbers = sorted(n for n in numbers if not re.search(rf"(?<!\d){re.escape(n)}(?!\d)", norm_context))

    base = dict(support_ratio=round(ratio, 3), cited_ids=valid, invalid_citations=invalid,
                unsupported_numbers=unsupported_numbers, sentences=checks)
    if ratio < BLOCK_RATIO:
        return OutputCheck("blocked_output", f"Apenas {ratio:.0%} das frases têm respaldo nos trechos", **base)
    warnings = []
    if ratio < WARN_RATIO:
        warnings.append(f"{ratio:.0%} das frases com respaldo")
    if invalid:
        warnings.append(f"citações inválidas removidas: {', '.join(invalid)}")
    if unsupported_numbers:
        warnings.append(f"números sem respaldo: {', '.join(unsupported_numbers)}")
    if warnings:
        return OutputCheck("answered_with_warning", "; ".join(warnings), **base)
    return OutputCheck("answered", "Resposta fundamentada nos trechos recuperados", **base)
