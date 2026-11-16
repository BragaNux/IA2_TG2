"""Catálogo de tópicos (topic key) e classificador por palavras-chave.

Cada chunk recebe o tópico com maior número de ocorrências de palavras-chave.
É uma abordagem simples, determinística e explicável; chunks sem nenhuma
ocorrência recebem o tópico "geral".
"""
from __future__ import annotations

import re
import unicodedata

TOPICS: dict[str, dict] = {
    "avaliacao_e_acionamento": {
        "label": "Avaliação da vítima e acionamento do socorro",
        "keywords": ["192", "193", "samu", "acionar", "acione", "avaliacao", "sinais vitais", "seguranca da cena",
                     "nivel de consciencia", "avaliacao primaria", "socorrista", "omissao de socorro"],
    },
    "rcp_parada_cardiorrespiratoria": {
        "label": "Parada cardiorrespiratória e RCP",
        "keywords": ["rcp", "reanimacao", "ressuscitacao", "parada cardiaca", "parada cardiorrespiratoria",
                     "compressoes toracicas", "compressao toracica", "massagem cardiaca", "dea", "desfibrilador"],
    },
    "engasgo_obstrucao_vias_aereas": {
        "label": "Engasgo e obstrução das vias aéreas",
        "keywords": ["engasgo", "engasgad", "heimlich", "obstrucao", "asfixia", "sufocacao", "corpo estranho",
                     "desobstrucao", "vias aereas"],
    },
    "hemorragias_e_ferimentos": {
        "label": "Hemorragias e ferimentos",
        "keywords": ["hemorragia", "sangramento", "sangrando", "torniquete", "ferimento", "compressao direta",
                     "curativo", "epistaxe", "sangramento nasal", "corte"],
    },
    "queimaduras": {
        "label": "Queimaduras",
        "keywords": ["queimadura", "queimado", "queimada", "bolhas", "escaldadura"],
    },
    "fraturas_e_traumas": {
        "label": "Fraturas, entorses e traumas",
        "keywords": ["fratura", "luxacao", "entorse", "imobiliza", "tala", "coluna cervical", "trauma",
                     "contusao", "transporte da vitima", "colar cervical"],
    },
    "afogamento": {
        "label": "Afogamento",
        "keywords": ["afogamento", "afogad", "submers", "piscina", "praia", "guarda-vidas", "salvamento aquatico"],
    },
    "intoxicacao_e_envenenamento": {
        "label": "Intoxicação e envenenamento",
        "keywords": ["intoxicacao", "envenenamento", "veneno", "ingeriu", "ingestao", "produtos de limpeza",
                     "ceatox", "monoxido", "toxic"],
    },
    "animais_peconhentos": {
        "label": "Acidentes com animais peçonhentos",
        "keywords": ["cobra", "serpente", "escorpiao", "aranha", "picada", "mordedura", "peconh", "abelha",
                     "soro antiofidico"],
    },
    "convulsao_e_desmaio": {
        "label": "Convulsão e desmaio",
        "keywords": ["convulsao", "convulsiva", "epilepsia", "epileptic", "desmaio", "sincope", "lipotimia",
                     "posicao lateral de seguranca"],
    },
    "choque_eletrico": {
        "label": "Choque elétrico",
        "keywords": ["choque eletrico", "eletricidade", "descarga eletrica", "corrente eletrica", "eletrocuss",
                     "rede eletrica"],
    },
    "estado_de_choque": {
        "label": "Estado de choque",
        "keywords": ["estado de choque", "choque hipovolemico", "choque anafilatico", "pele palida", "pulso fraco"],
    },
    "emergencias_clinicas": {
        "label": "Emergências clínicas (infarto, AVC, hipoglicemia...)",
        "keywords": ["infarto", "avc", "acidente vascular", "derrame", "hipoglicemia", "diabet", "dor no peito",
                     "crise hipertensiva", "asma", "febre"],
    },
    "prevencao_de_acidentes": {
        "label": "Prevenção de acidentes",
        "keywords": ["prevencao", "prevenir", "evite", "acidentes domesticos", "tomadas", "fogao", "quedas",
                     "mantenha fora do alcance"],
    },
    "geral": {
        "label": "Geral / outros",
        "keywords": [],
    },
}


def normalize(text: str) -> str:
    """Minúsculas e sem acentos, para comparação robusta."""
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


def _pattern(kw: str) -> re.Pattern:
    # Palavras curtas (rcp, dea, avc, 192) exigem palavra inteira; as demais funcionam como radical.
    return re.compile(r"\b" + re.escape(kw) + (r"\b" if len(kw) <= 4 else ""))


_PATTERNS = {key: [_pattern(kw) for kw in spec["keywords"]] for key, spec in TOPICS.items()}


def classify_topic(text: str) -> str:
    norm = normalize(text)
    scores = {key: sum(len(p.findall(norm)) for p in pats) for key, pats in _PATTERNS.items() if pats}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "geral"
