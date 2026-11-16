"""Extração, limpeza e segmentação (chunking) dos PDFs do corpus."""
from __future__ import annotations

import bisect
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter

from rag.topics import classify_topic

# ---------------------------------------------------------------- extração


def extract_pages(pdf_path: Path) -> list[str]:
    """Texto bruto de cada página (pymupdf)."""
    with pymupdf.open(pdf_path) as doc:
        return [page.get_text() for page in doc]


# ---------------------------------------------------------------- limpeza

# O PDF do MS/Fiocruz (2003, PageMaker) tem texto CP1252 decodificado como CP437:
# "MinistΘrio da Sa·de" -> "Ministério da Saúde". Detectamos pelos caracteres típicos.
_MOJIBAKE_MARKERS = set("ΘτπφΩ≤⌡╔·ßσ")


def fix_mojibake(text: str) -> str:
    if sum(text.count(c) for c in _MOJIBAKE_MARKERS) < 3:
        return text
    try:
        return text.encode("cp437", errors="strict").decode("cp1252", errors="replace")
    except UnicodeEncodeError:
        # Página mista: corrige caractere a caractere o que for possível
        out = []
        for ch in text:
            try:
                out.append(ch.encode("cp437").decode("cp1252"))
            except (UnicodeEncodeError, UnicodeDecodeError):
                out.append(ch)
        return "".join(out)


_BULLETS = re.compile(r"^[-•●▪■◦○➢►✓✔·\-–]\s*")
_PAGE_NUMBER = re.compile(r"^(p[aá]g(ina)?\.?\s*)?\d{1,3}$", re.IGNORECASE)
# Créditos de imagem e legendas de figura: ruído para a recuperação
_NOISE_LINE = re.compile(r"^(fonte\s*:|figura\s*\d+|fig\.\s*\d+)", re.IGNORECASE)
_END_PUNCT = tuple(".!?:;")


def _repeated_lines(pages: list[list[str]]) -> set[str]:
    """Linhas curtas que se repetem em muitas páginas (cabeçalhos/rodapés)."""
    if len(pages) < 5:
        return set()
    counts = Counter(line for lines in pages for line in set(lines) if 0 < len(line) < 100)
    return {line for line, n in counts.items() if n >= max(3, 0.4 * len(pages))}


def _join_lines(lines: list[str]) -> str:
    """Junta linhas quebradas pelo layout em parágrafos; preserva tópicos (bullets)."""
    out: list[str] = []
    for line in lines:
        if not line:
            if out and out[-1] != "":
                out.append("")
            continue
        is_bullet = bool(_BULLETS.match(line))
        if is_bullet:
            line = "- " + _BULLETS.sub("", line)
        prev = out[-1] if out else ""
        # Continua o parágrafo se a linha anterior não terminou a frase e: a linha começa em
        # minúscula/dígito, ou uma das duas é muito curta (layout de slides/cartazes: 1 palavra por linha).
        continues = line[0].islower() or line[0].isdigit() or len(prev.split()) <= 2 or len(line.split()) <= 2
        if prev and not is_bullet and not prev.endswith(_END_PUNCT) and continues:
            if prev.endswith("-") and line[0].islower():   # hifenização: "socor-\nrista"
                out[-1] = prev[:-1] + line
            else:
                out[-1] = prev + " " + line
        else:
            out.append(line)
    return "\n".join(out).strip()


def clean_pages(raw_pages: list[str]) -> list[str]:
    pages = []
    for raw in raw_pages:
        text = fix_mojibake(raw).replace(" ", " ").replace("\t", " ")
        lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
        pages.append(lines)

    repeated = _repeated_lines(pages)
    cleaned = []
    for lines in pages:
        kept = [ln for ln in lines
                if ln not in repeated and not _PAGE_NUMBER.match(ln) and not _NOISE_LINE.match(ln)]
        text = _join_lines(kept)
        text = re.sub(r"\n{3,}", "\n\n", text)
        cleaned.append(text)
    return cleaned


# ---------------------------------------------------------------- chunking


@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    chunk_index: int
    page_start: int
    page_end: int
    topic: str
    content: str


@dataclass
class ProcessedDocument:
    doc_id: str
    num_pages: int
    full_text: str
    chunks: list[Chunk] = field(default_factory=list)


def chunk_document(doc_id: str, pages: list[str], chunk_size: int, chunk_overlap: int,
                   min_chars: int = 80) -> ProcessedDocument:
    """Concatena as páginas (guardando offsets) e segmenta com RecursiveCharacterTextSplitter.

    O splitter tenta quebrar primeiro em parágrafos, depois linhas, frases e palavras,
    preservando ao máximo unidades semânticas (um procedimento inteiro, p.ex.).
    """
    offsets, parts, pos = [], [], 0
    for text in pages:
        offsets.append(pos)
        parts.append(text)
        pos += len(text) + 2
    full_text = "\n\n".join(parts)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", "; ", ", ", " ", ""],
        add_start_index=True,
    )
    docs = splitter.create_documents([full_text])

    chunks: list[Chunk] = []
    for d in docs:
        content = d.page_content.strip()
        if len(content) < min_chars:      # descarta fragmentos sem conteúdo útil
            continue
        start = d.metadata["start_index"]
        end = start + len(d.page_content)
        page_start = bisect.bisect_right(offsets, start)          # páginas 1-indexadas
        page_end = bisect.bisect_right(offsets, max(start, end - 1))
        idx = len(chunks)
        chunks.append(Chunk(
            chunk_id=f"{doc_id}#{idx}",
            doc_id=doc_id,
            chunk_index=idx,
            page_start=page_start,
            page_end=page_end,
            topic=classify_topic(content),
            content=content,
        ))
    return ProcessedDocument(doc_id=doc_id, num_pages=len(pages), full_text=full_text, chunks=chunks)


def process_pdf(pdf_path: Path, chunk_size: int, chunk_overlap: int) -> ProcessedDocument:
    pages = clean_pages(extract_pages(pdf_path))
    return chunk_document(pdf_path.stem, pages, chunk_size, chunk_overlap)
