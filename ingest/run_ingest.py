"""Pipeline de ingestão: PDF -> limpeza -> chunks -> embeddings -> PostgreSQL/pgvector.

Uso:  python -m ingest.run_ingest
"""
from __future__ import annotations

import json
import time
from collections import Counter
from dataclasses import asdict

from rag import db
from rag.catalog import DOCUMENTS
from rag.config import CHUNK_OVERLAP, CHUNK_SIZE, EMBED_MODEL, PROCESSED_DIR, RAW_DIR
from rag.embeddings import embed_texts, embedding_dim

from ingest.processing import process_pdf


def main() -> None:
    t0 = time.time()
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    print(f"[1/4] {len(pdfs)} PDFs em {RAW_DIR} | chunk_size={CHUNK_SIZE} overlap={CHUNK_OVERLAP}")

    docs = []
    for pdf in pdfs:
        if pdf.stem not in DOCUMENTS:
            print(f"  ! {pdf.name} sem metadados em rag/catalog.py — ignorado")
            continue
        d = process_pdf(pdf, CHUNK_SIZE, CHUNK_OVERLAP)
        docs.append(d)
        print(f"  - {d.doc_id}: {d.num_pages} páginas -> {len(d.chunks)} chunks")

    all_chunks = [c for d in docs for c in d.chunks]
    print(f"[2/4] Gerando embeddings ({EMBED_MODEL}) para {len(all_chunks)} chunks...")
    vectors = embed_texts([c.content for c in all_chunks])

    print("[3/4] Gravando no PostgreSQL/pgvector...")
    with db.connect() as conn:
        db.create_schema(conn, embedding_dim())
        for d in docs:
            meta = DOCUMENTS[d.doc_id]
            conn.execute(
                "INSERT INTO documents (doc_id, title, organization, year, category, url, num_pages, num_chunks, full_text)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (d.doc_id, meta["title"], meta["organization"], meta["year"], meta["category"], meta["url"],
                 d.num_pages, len(d.chunks), d.full_text),
            )
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (chunk_id, doc_id, chunk_index, page_start, page_end, topic, content, embedding)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                [(c.chunk_id, c.doc_id, c.chunk_index, c.page_start, c.page_end, c.topic, c.content, v)
                 for c, v in zip(all_chunks, vectors)],
            )
        conn.commit()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / "chunks.jsonl"
    with out.open("w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(asdict(c), ensure_ascii=False) + "\n")

    topics = Counter(c.topic for c in all_chunks)
    print(f"[4/4] OK em {time.time() - t0:.1f}s. Chunks por tópico: {dict(topics.most_common())}")
    print(f"      Cópia inspecionável dos chunks: {out}")


if __name__ == "__main__":
    main()
