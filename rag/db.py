"""Acesso ao PostgreSQL + pgvector: schema, inserção e busca semântica."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from rag.config import DATABASE_URL


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(conn)
        yield conn


def create_schema(conn: psycopg.Connection, dim: int) -> None:
    conn.execute("DROP TABLE IF EXISTS chunks")
    conn.execute("DROP TABLE IF EXISTS documents")
    conn.execute(
        """
        CREATE TABLE documents (
            doc_id        TEXT PRIMARY KEY,
            title         TEXT NOT NULL,
            organization  TEXT,
            year          INT,
            category      TEXT,
            url           TEXT,
            num_pages     INT,
            num_chunks    INT,
            full_text     TEXT
        )
        """
    )
    conn.execute(
        f"""
        CREATE TABLE chunks (
            chunk_id     TEXT PRIMARY KEY,          -- ex.: ufs_primeiros_socorros_para_todos#12
            doc_id       TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
            chunk_index  INT  NOT NULL,
            page_start   INT,
            page_end     INT,
            topic        TEXT NOT NULL,             -- topic key (rag/topics.py)
            content      TEXT NOT NULL,
            embedding    vector({dim}) NOT NULL
        )
        """
    )
    # Índice HNSW para busca aproximada por distância de cosseno
    conn.execute("CREATE INDEX chunks_embedding_hnsw ON chunks USING hnsw (embedding vector_cosine_ops)")
    conn.execute("CREATE INDEX chunks_topic_idx ON chunks (topic)")
    conn.execute("CREATE INDEX chunks_doc_idx ON chunks (doc_id)")


def search(conn: psycopg.Connection, query_vec: np.ndarray, top_k: int, topic: str | None = None,
           doc_id: str | None = None) -> list[dict]:
    """Top-k por similaridade de cosseno (1 - distância), com filtros opcionais de metadados."""
    where, params = [], []
    if topic:
        where.append("c.topic = %s")
        params.append(topic)
    if doc_id:
        where.append("c.doc_id = %s")
        params.append(doc_id)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT c.chunk_id, c.doc_id, d.title AS document_title, d.organization, c.topic,
               c.page_start, c.page_end, c.content,
               1 - (c.embedding <=> %s) AS score
        FROM chunks c JOIN documents d USING (doc_id)
        {where_sql}
        ORDER BY c.embedding <=> %s
        LIMIT %s
    """
    return conn.execute(sql, [query_vec, *params, query_vec, top_k]).fetchall()
