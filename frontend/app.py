"""Frontend (Streamlit): chat de primeiros socorros com fontes, trace das tools MCP e guardrails.

Uso:  streamlit run frontend/app.py
      streamlit run frontend/app.py  ->  http://localhost:8501/?demo=1  (reexibe os cenários gravados em
      docs/evidencias/cenarios.json, sem chamar o LLM; útil para apresentação)
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests
import streamlit as st

import ui

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
EVIDENCE_FILE = Path(__file__).resolve().parent.parent / "docs" / "evidencias" / "cenarios.json"

QUICK_ACTIONS = [
    ("queimadura", ":material/local_fire_department:", "Queimadura", "O que fazer e o que evitar",
     "Alguém se queimou. O que devo fazer e o que não devo passar na pele?"),
    ("engasgo", ":material/air:", "Engasgo", "Adulto, criança ou bebê",
     "Como ajudar uma pessoa engasgada? E se for um bebê?"),
    ("rcp", ":material/ecg_heart:", "Parada cardíaca", "Como fazer a RCP",
     "Como fazer massagem cardíaca (RCP) em um adulto que não respira?"),
    ("sangramento", ":material/water_drop:", "Sangramento", "Como estancar",
     "Como estancar um sangramento forte de um corte?"),
    ("convulsao", ":material/neurology:", "Convulsão", "Como proteger a pessoa",
     "O que fazer quando alguém está tendo uma convulsão?"),
    ("afogamento", ":material/pool:", "Afogamento", "Depois de tirar da água",
     "O que fazer com uma pessoa que se afogou e foi retirada da água?"),
]

st.set_page_config(page_title="Primeiros Socorros · Assistente", page_icon="🛟", layout="centered",
                   initial_sidebar_state="auto")
st.markdown(ui.CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------ backend

@st.cache_data(ttl=120, show_spinner=False)
def fetch(path: str) -> dict | None:
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None


def ask(message: str, history: list[dict]) -> dict:
    try:
        r = requests.post(f"{BACKEND_URL}/chat", json={"message": message, "history": history}, timeout=300)
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return {"status": "error", "sources": [], "tool_calls": [], "emergency": False,
                "answer": "Não consegui falar com o servidor agora. **Se for uma emergência, ligue 192 (SAMU) "
                          "ou 193 (Bombeiros).**"}


def build_history(messages: list[dict]) -> list[dict]:
    """Pares (pergunta, resposta) válidos; turnos bloqueados ou com erro ficam fora do contexto."""
    history = []
    for user_msg, bot_msg in zip(messages[::2], messages[1::2]):
        if bot_msg.get("result", {}).get("status") not in ("blocked_input", "error"):
            history += [{"role": "user", "content": user_msg["content"]},
                        {"role": "assistant", "content": bot_msg["content"]}]
    return history


# ------------------------------------------------------------------ estado

if "messages" not in st.session_state:
    st.session_state.messages = []

demo = st.query_params.get("demo") == "1"
if demo and not st.session_state.get("demo_loaded") and EVIDENCE_FILE.exists():
    for item in json.loads(EVIDENCE_FILE.read_text(encoding="utf-8")):
        st.session_state.messages += [
            {"role": "user", "content": item["question"]},
            {"role": "assistant", "content": item["result"]["answer"], "result": item["result"]},
        ]
    st.session_state.demo_loaded = True


def queue_prompt(text: str) -> None:
    st.session_state.pending = text


topics = fetch("/topics")
topic_labels = {t["topic_key"]: t["label"] for t in topics["topics"]} if topics else {}


# ------------------------------------------------------------------ renderização

def render_assistant(res: dict) -> None:
    st.html(ui.status_chip(res["status"], res.get("elapsed_ms")))
    if res.get("emergency"):
        st.html(ui.emergency_alert())
    st.markdown(res["answer"])
    if res.get("sources"):
        st.html(ui.sources_grid(res["sources"], topic_labels))
    if res.get("tool_calls") or res.get("input_guardrail"):
        with st.expander("Como esta resposta foi construída", icon=":material/account_tree:"):
            st.html(ui.build_trace(res))


# ------------------------------------------------------------------ sidebar

with st.sidebar:
    st.html(f'<div class="side-brand">{ui.buoy("30")} Primeiros Socorros</div>')
    st.html(ui.sidebar_status(fetch("/health"), BACKEND_URL))
    if st.button("Nova conversa", icon=":material/add_comment:", width="stretch", type="primary"):
        st.session_state.messages = []
        st.session_state.pop("demo_loaded", None)
        st.query_params.clear()
        st.rerun()
    docs = fetch("/documents")
    if docs:
        with st.expander(f"Base de conhecimento · {docs['total']} documentos", icon=":material/menu_book:"):
            st.html(ui.documents_list(docs["documents"]))
    if topics:
        with st.expander(f"Tópicos cobertos · {topics['total']}", icon=":material/label:"):
            st.html("".join(f'<div class="doc-item">{t["label"]} <small>· {t["num_chunks"]} trechos</small></div>'
                            for t in topics["topics"] if t["topic_key"] != "geral"))
    st.caption("Trabalho acadêmico de IA II (AMF). As orientações vêm dos documentos citados e não substituem "
               "atendimento profissional.")


# ------------------------------------------------------------------ página

messages = st.session_state.messages
pending = st.session_state.get("pending")

st.html(ui.hero(compact=bool(messages or pending)))
st.html(ui.fab())

if demo:
    st.html('<div class="demo-banner">▶ <b>Modo demonstração</b>: respostas gravadas dos cenários de teste '
            '(docs/evidencias/cenarios.json). Use “Nova conversa” para voltar ao modo normal.</div>')

if not messages and not pending:
    st.html('<div class="section-title">O que está acontecendo?</div>'
            '<p class="section-sub">Escolha uma situação ou descreva com suas palavras no campo abaixo.</p>')
    with st.container(key="quick"):
        for col, (key, icon, title, sub, prompt) in zip(st.columns(len(QUICK_ACTIONS)), QUICK_ACTIONS):
            col.button(f"**{title}** {sub}", key=f"qa_{key}", icon=icon, width="stretch",
                       on_click=queue_prompt, args=(prompt,))
    # Em apps de chat o Streamlit abre a página rolada até o fim; no estado inicial queremos o topo (hero).
    # (HTML estático e nosso; nada vindo do usuário ou do LLM passa por st.iframe)
    with st.container(key="scrolltop"):
        st.iframe("""<script>
          const go = () => { const c = window.parent.document.querySelector('[data-testid="stAppScrollToBottomContainer"]');
                             if (c) c.scrollTop = 0; };
          [50, 300, 900].forEach(t => setTimeout(go, t));
        </script>""", height=1)

for i, msg in enumerate(messages):
    if msg["role"] == "user":
        with st.chat_message("user", avatar=":material/person:"):
            with st.container(key=f"user-msg-{i}"):
                st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar="🛟"):
            render_assistant(msg["result"])

prompt = st.chat_input("Descreva a situação…", max_chars=1000)
if not prompt and pending:
    prompt = st.session_state.pop("pending")

if prompt:
    history = build_history(messages)
    messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar=":material/person:"):
        with st.container(key=f"user-msg-{len(messages) - 1}"):
            st.markdown(prompt)
    with st.chat_message("assistant", avatar="🛟"):
        with st.spinner("Consultando os manuais oficiais…"):
            res = ask(prompt, history)
        render_assistant(res)
    messages.append({"role": "assistant", "content": res["answer"], "result": res})

st.html('<p class="footer-note">As orientações vêm dos manuais citados e não substituem atendimento profissional. '
        'Em emergência, ligue <b>192</b> (SAMU) ou <b>193</b> (Bombeiros).</p>')
