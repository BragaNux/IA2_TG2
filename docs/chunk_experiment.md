# Experimento de chunking

Corpus: 7 PDFs. 16 perguntas com evidência conhecida. Relevante = chunk contém todas as palavras-chave de evidência. k = 5.

| chunk_size | chunk_overlap | nº chunks | tamanho médio | hit@5 | MRR |
|---:|---:|---:|---:|---:|---:|
| 300 | 50 | 2338 | 219 | 0.62 | 0.490 |
| 500 | 100 | 1463 | 367 | 0.69 | 0.544 |
| 800 | 150 | 890 | 607 | 0.69 | 0.523 |
| 1200 | 200 | 588 | 911 | 0.69 | 0.656 |
| 1600 | 300 | 471 | 1166 | 0.62 | 0.552 |
