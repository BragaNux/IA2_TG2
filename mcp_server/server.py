"""Servidor MCP (FastMCP) que expõe a base de conhecimento de primeiros socorros.

Tools:
  - search_knowledge : busca semântica top-k no pgvector (com filtro opcional de tópico/documento)
  - get_document     : metadados e conteúdo (paginado) de um documento
  - list_topics      : tópicos (topic keys) disponíveis, com contagem de chunks
  - list_documents   : documentos do corpus com metadados

Transporte: stdio (o backend sobe este processo e conversa via JSON-RPC).
Uso manual / inspeção:  mcp dev mcp_server/server.py   ou   python -m mcp_server.server
"""
from __future__ import annotations

import logging
import sys
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from rag import db
from rag.embeddings import embed_query
from rag.topics import TOPICS

# Em stdio, stdout é o canal do protocolo: logs vão para stderr.
logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="[mcp] %(message)s")
log = logging.getLogger(__name__)

mcp = FastMCP(
    "primeiros-socorros-kb",
    instructions=(
        "Base de conhecimento de primeiros socorros construída a partir de manuais e cartilhas "
        "oficiais brasileiros (Ministério da Saúde/Fiocruz, Corpos de Bombeiros, universidades federais, "
        "SOBRASA, MDH). Use search_knowledge para recuperar evidências antes de responder."
    ),
)


# ------------------------------------------------------------------ modelos de retorno (estruturados)

class ChunkHit(BaseModel):
    chunk_id: str = Field(description="Identificador do trecho, usado para citação. Ex.: ufs_primeiros_socorros_para_todos#12")
    doc_id: str
    document_title: str
    organization: str | None
    topic: str = Field(description="Topic key do trecho")
    page_start: int | None
    page_end: int | None
    score: float = Field(description="Similaridade de cosseno com a consulta (0 a 1)")
    content: str


class SearchResult(BaseModel):
    query: str
    topic_filter: str | None
    doc_filter: str | None
    total: int
    results: list[ChunkHit]


class DocumentDetail(BaseModel):
    doc_id: str
    title: str
    organization: str | None
    year: int | None
    category: str | None
    url: str | None
    num_pages: int
    num_chunks: int
    topics: dict[str, int] = Field(description="Quantidade de chunks por tópico neste documento")
    offset: int
    content: str = Field(description="Trecho do texto completo do documento a partir de 'offset'")
    total_chars: int
    has_more: bool


class TopicInfo(BaseModel):
    topic_key: str
    label: str
    num_chunks: int
    documents: list[str]


class TopicList(BaseModel):
    total: int
    topics: list[TopicInfo]


class DocumentSummary(BaseModel):
    doc_id: str
    title: str
    organization: str | None
    year: int | None
    category: str | None
    num_pages: int
    num_chunks: int


class DocumentList(BaseModel):
    total: int
    documents: list[DocumentSummary]


# ------------------------------------------------------------------ tools

@mcp.tool()
def search_knowledge(
    query: Annotated[str, Field(description="Pergunta ou termos de busca em português", min_length=2, max_length=500)],
    top_k: Annotated[int, Field(description="Quantidade de trechos a retornar", ge=1, le=10)] = 5,
    topic: Annotated[str | None, Field(description="Filtra por topic key (veja list_topics). Opcional.")] = None,
    doc_id: Annotated[str | None, Field(description="Filtra por documento (veja list_documents). Opcional.")] = None,
) -> SearchResult:
    """Busca semântica na base de primeiros socorros. Retorna os trechos (chunks) mais
    similares à consulta, com documento de origem, páginas, tópico e score de similaridade.
    Use sempre antes de responder perguntas do usuário e cite os chunk_id retornados."""
    if topic and topic not in TOPICS:
        raise ValueError(f"Tópico desconhecido: {topic!r}. Use list_topics para ver os válidos.")
    vec = embed_query(query)
    with db.connect() as conn:
        rows = db.search(conn, vec, top_k, topic=topic, doc_id=doc_id)
    log.info("search_knowledge(%r, top_k=%s, topic=%s) -> %d", query, top_k, topic, len(rows))
    hits = [ChunkHit(**{**r, "score": round(float(r["score"]), 4)}) for r in rows]
    return SearchResult(query=query, topic_filter=topic, doc_filter=doc_id, total=len(hits), results=hits)


@mcp.tool()
def get_document(
    doc_id: Annotated[str, Field(description="Identificador do documento (ex.: ms_fiocruz_manual_primeiros_socorros)")],
    offset: Annotated[int, Field(description="Posição (em caracteres) a partir da qual ler o texto", ge=0)] = 0,
    max_chars: Annotated[int, Field(description="Máximo de caracteres de conteúdo retornados", ge=200, le=8000)] = 3000,
) -> DocumentDetail:
    """Recupera os metadados (título, órgão, ano, URL, páginas, tópicos) e o conteúdo textual
    de um documento específico do corpus, de forma paginada (offset/max_chars)."""
    with db.connect() as conn:
        doc = conn.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,)).fetchone()
        if not doc:
            raise ValueError(f"Documento não encontrado: {doc_id!r}. Use list_documents.")
        topics = conn.execute(
            "SELECT topic, COUNT(*) AS n FROM chunks WHERE doc_id = %s GROUP BY topic ORDER BY n DESC", (doc_id,)
        ).fetchall()
    text = doc["full_text"] or ""
    content = text[offset: offset + max_chars]
    log.info("get_document(%s, offset=%s)", doc_id, offset)
    return DocumentDetail(
        doc_id=doc["doc_id"], title=doc["title"], organization=doc["organization"], year=doc["year"],
        category=doc["category"], url=doc["url"], num_pages=doc["num_pages"], num_chunks=doc["num_chunks"],
        topics={t["topic"]: t["n"] for t in topics}, offset=offset, content=content,
        total_chars=len(text), has_more=offset + max_chars < len(text),
    )


@mcp.tool()
def list_topics() -> TopicList:
    """Lista os tópicos (topic keys) do corpus de primeiros socorros, com descrição,
    quantidade de chunks e documentos em que aparecem. Útil para filtrar search_knowledge."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT topic, COUNT(*) AS n, ARRAY_AGG(DISTINCT doc_id) AS docs FROM chunks GROUP BY topic ORDER BY n DESC"
        ).fetchall()
    topics = [TopicInfo(topic_key=r["topic"], label=TOPICS.get(r["topic"], {}).get("label", r["topic"]),
                        num_chunks=r["n"], documents=sorted(r["docs"])) for r in rows]
    return TopicList(total=len(topics), topics=topics)


@mcp.tool()
def list_documents() -> DocumentList:
    """Lista os documentos do corpus (manuais e cartilhas) com órgão emissor, ano e tamanho."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT doc_id, title, organization, year, category, num_pages, num_chunks FROM documents ORDER BY title"
        ).fetchall()
    docs = [DocumentSummary(**r) for r in rows]
    return DocumentList(total=len(docs), documents=docs)


if __name__ == "__main__":
    embed_query("aquecimento")   # carrega o modelo de embeddings antes da primeira chamada
    log.info("Servidor MCP pronto (stdio)")
    mcp.run(transport="stdio")
