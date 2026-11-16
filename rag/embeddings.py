"""Geração de embeddings com fastembed (ONNX, CPU, sem PyTorch)."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
from fastembed import TextEmbedding

from rag.config import CACHE_DIR, EMBED_MODEL


@lru_cache(maxsize=1)
def _model() -> TextEmbedding:
    return TextEmbedding(model_name=EMBED_MODEL, cache_dir=str(CACHE_DIR / "fastembed"))


def embed_texts(texts: list[str], batch_size: int = 64) -> np.ndarray:
    """Retorna matriz (n, dim) com vetores normalizados (norma L2 = 1)."""
    if not texts:
        return np.zeros((0, embedding_dim()), dtype=np.float32)
    vecs = np.array(list(_model().embed(texts, batch_size=batch_size)), dtype=np.float32)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    return vecs / np.clip(norms, 1e-12, None)


def embed_query(text: str) -> np.ndarray:
    return embed_texts([text])[0]


def embedding_dim() -> int:
    return len(next(iter(_model().embed(["dim"]))))
