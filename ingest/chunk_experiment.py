"""Experimento para justificar chunk_size / chunk_overlap.

Para cada configuração, segmenta o corpus, gera embeddings em memória e mede,
num conjunto de perguntas com resposta conhecida:
  - hit@k : fração de perguntas em que algum dos top-k chunks contém a evidência esperada
  - MRR   : média do inverso da posição do primeiro chunk relevante
Um chunk é relevante se contém TODAS as palavras-chave de evidência (sem acento/minúsculas).

Uso:  python -m ingest.chunk_experiment
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from rag.config import RAW_DIR, ROOT_DIR
from rag.embeddings import embed_texts
from rag.topics import normalize

from ingest.processing import process_pdf

CONFIGS = [(300, 50), (500, 100), (800, 150), (1200, 200), (1600, 300)]
K = 5

# (pergunta, palavras-chave que o trecho com a resposta precisa conter)
QUESTIONS: list[tuple[str, list[str]]] = [
    ("O que fazer em caso de queimadura? Posso passar pasta de dente?", ["queimadura", "pasta de dente"]),
    ("Como fazer a manobra de Heimlich em um adulto engasgado?", ["heimlich"]),
    ("Qual a frequência das compressões torácicas na RCP?", ["compress", "por minuto"]),
    ("Como estancar um sangramento no nariz?", ["nariz", "sangra"]),
    ("O que fazer quando alguém está tendo uma convulsão?", ["convuls", "boca"]),
    ("O que fazer se uma criança ingerir produto de limpeza?", ["produtos de limpeza"]),
    ("Fui picado por uma cobra, devo fazer torniquete ou chupar o veneno?", ["cobra", "torniquete"]),
    ("Como socorrer uma pessoa que levou choque elétrico?", ["eletric", "deslig"]),
    ("Como imobilizar uma fratura no braço?", ["fratura", "imobiliz"]),
    ("Quais os sinais de que a vítima está em estado de choque?", ["choque", "pulso"]),
    ("O que fazer com uma pessoa que se afogou e foi retirada da água?", ["afoga"]),
    ("Como colocar a vítima na posição lateral de segurança?", ["lateral de seguranca"]),
    ("Qual número devo ligar para chamar o SAMU?", ["192"]),
    ("O que fazer em caso de desmaio?", ["desmaio", "pernas"]),
    ("Como agir com um bebê engasgado?", ["bebe", "engasg"]),
    ("Como usar o desfibrilador externo automático (DEA)?", ["dea"]),
]


def evaluate(chunk_size: int, overlap: int, pdfs: list[Path], q_vecs: np.ndarray) -> dict:
    chunks = [c for pdf in pdfs for c in process_pdf(pdf, chunk_size, overlap).chunks]
    texts = [c.content for c in chunks]
    norm_texts = [normalize(t) for t in texts]
    vecs = embed_texts(texts)
    sims = q_vecs @ vecs.T

    hits, rr = 0, 0.0
    for qi, (_, keys) in enumerate(QUESTIONS):
        top = np.argsort(-sims[qi])[:K]
        for rank, idx in enumerate(top, start=1):
            if all(normalize(k) in norm_texts[idx] for k in keys):
                hits += 1
                rr += 1 / rank
                break
    avg_len = sum(map(len, texts)) / len(texts)
    return {"chunk_size": chunk_size, "overlap": overlap, "n_chunks": len(chunks), "avg_len": avg_len,
            "hit@k": hits / len(QUESTIONS), "mrr": rr / len(QUESTIONS)}


def main() -> None:
    pdfs = sorted(RAW_DIR.glob("*.pdf"))
    q_vecs = embed_texts([q for q, _ in QUESTIONS])
    rows = []
    for size, overlap in CONFIGS:
        r = evaluate(size, overlap, pdfs, q_vecs)
        rows.append(r)
        print(f"size={size:>5} overlap={overlap:>4} chunks={r['n_chunks']:>5} "
              f"hit@{K}={r['hit@k']:.2f} MRR={r['mrr']:.3f}")

    lines = [
        "# Experimento de chunking",
        "",
        f"Corpus: {len(pdfs)} PDFs. {len(QUESTIONS)} perguntas com evidência conhecida. "
        f"Relevante = chunk contém todas as palavras-chave de evidência. k = {K}.",
        "",
        f"| chunk_size | chunk_overlap | nº chunks | tamanho médio | hit@{K} | MRR |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for r in rows:
        lines.append(f"| {r['chunk_size']} | {r['overlap']} | {r['n_chunks']} | {r['avg_len']:.0f} | "
                     f"{r['hit@k']:.2f} | {r['mrr']:.3f} |")
    out = ROOT_DIR / "docs" / "chunk_experiment.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nTabela salva em {out}")


if __name__ == "__main__":
    main()
