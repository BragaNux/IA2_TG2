"""Configuração central, lida do arquivo .env (ou variáveis de ambiente)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

RAW_DIR = ROOT_DIR / "data" / "raw"
PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CACHE_DIR = ROOT_DIR / ".cache"

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag:rag@localhost:5433/primeiros_socorros")

# Modelo multilíngue (bom em PT-BR), 384 dimensões, ~220 MB, roda em CPU via ONNX.
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

# Justificativa em docs/chunk_experiment.md (experimento hit@k / MRR).
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1200"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K = int(os.getenv("TOP_K", "5"))

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
_EFFORTS = {"low", "medium", "high", "xhigh", "max"}
ANTHROPIC_EFFORT = os.getenv("ANTHROPIC_EFFORT", "low").strip().lower()
if ANTHROPIC_EFFORT not in _EFFORTS:      # valor inválido viraria erro 400 na API
    ANTHROPIC_EFFORT = "low"

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
