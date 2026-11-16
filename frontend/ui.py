"""Design system e componentes visuais (identidade "salva-vidas": vermelho resgate, branco e amarelo guarda-vidas)."""
from __future__ import annotations

from html import escape

# ------------------------------------------------------------------ estilos globais

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root{
  --red:#D7192D; --red-700:#A60F1F; --red-50:#FDEDEF;
  --yellow:#FFC300; --yellow-50:#FFF6D6; --yellow-700:#8A6100;
  --navy:#0B1B2B; --ink-2:#3E4C5E; --ink-3:#6A7789;
  --bg:#F6F7F9; --card:#FFFFFF; --line:#E3E7ED;
  --green:#0F7B55; --green-50:#E6F5EE;
  --slate:#475467; --slate-50:#EEF1F5;
  --radius:16px; --radius-sm:10px;
  --shadow:0 1px 2px rgba(16,24,40,.05),0 6px 16px rgba(16,24,40,.06);
  --display:'Barlow Condensed','Arial Narrow',sans-serif;
  --body:'Inter',system-ui,-apple-system,'Segoe UI',sans-serif;
}

html, body, .stApp, .stMarkdown, button, input, textarea{font-family:var(--body);}
.stApp{background:var(--bg);color:var(--navy);}
header[data-testid="stHeader"]{background:transparent;}
.block-container{max-width:960px;padding:3.2rem 1.25rem 2rem;}
.stMarkdown p, .stMarkdown li{font-size:1rem;line-height:1.65;color:var(--navy);}
a{color:var(--red);}

/* ---------- hero ---------- */
.hero{position:relative;overflow:hidden;border-radius:22px;color:#fff;
  background:linear-gradient(135deg,#E11D33 0%,#C0122A 55%,#9E0D20 100%);box-shadow:0 10px 30px rgba(167,15,31,.25);
  padding:1.6rem 1.7rem;display:flex;gap:1.5rem;align-items:center;justify-content:space-between;flex-wrap:wrap;margin-bottom:1.4rem;}
.hero::before{content:"";position:absolute;inset:0;opacity:.09;pointer-events:none;
  background:repeating-linear-gradient(-45deg,#fff 0 18px,transparent 18px 40px);}
.hero > *{position:relative;}
.brand{display:flex;align-items:center;gap:.9rem;}
.buoy{flex:none;width:58px;height:58px;border-radius:50%;background:#fff;display:grid;place-items:center;
  box-shadow:0 4px 14px rgba(0,0,0,.18);}
.eyebrow{font:700 .78rem/1 var(--body);letter-spacing:.14em;text-transform:uppercase;color:var(--yellow);}
.hero h1{font:800 2.5rem/1 var(--display);letter-spacing:.01em;margin:.25rem 0 0;padding:0;color:#fff;text-transform:uppercase;}
.lead{margin:.9rem 0 0;max-width:34rem;font-size:1rem;line-height:1.55;color:rgba(255,255,255,.92);}
.chips{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:1rem;}
.chip{display:inline-flex;align-items:center;gap:.35rem;font-size:.8rem;font-weight:600;padding:.35rem .7rem;
  border-radius:999px;background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);color:#fff;}
.hero-cta{display:flex;flex-direction:column;gap:.6rem;min-width:13rem;}
.call{display:flex;align-items:center;justify-content:space-between;gap:1rem;text-decoration:none!important;
  background:#fff;color:var(--red-700)!important;border-radius:14px;padding:.7rem 1rem;font-weight:700;font-size:.92rem;
  box-shadow:0 4px 12px rgba(0,0,0,.15);transition:transform .15s ease, box-shadow .15s ease;}
.call b{font:800 1.7rem/1 var(--display);color:var(--red);}
.call:hover{transform:translateY(-2px);box-shadow:0 8px 18px rgba(0,0,0,.2);}
.call:focus-visible{outline:3px solid var(--yellow);outline-offset:2px;}
.call small{display:block;font-weight:500;font-size:.72rem;color:var(--ink-3);}
.hero.compact{padding:.9rem 1.1rem;border-radius:18px;margin-bottom:1rem;}
.hero.compact h1{font-size:1.7rem;}
.hero.compact .buoy{width:44px;height:44px;}
.hero.compact .hero-cta{flex-direction:row;min-width:0;}
.hero.compact .call{padding:.45rem .8rem;}
.hero.compact .call b{font-size:1.35rem;}
.hero.compact .call small{display:none;}

/* ---------- seções ---------- */
.section-title{font:700 1.45rem/1.1 var(--display);text-transform:uppercase;letter-spacing:.02em;margin:.4rem 0 .2rem;color:var(--navy);}
.section-sub{color:var(--ink-3);font-size:.92rem;margin:0 0 .9rem;}

/* ---------- atalhos de situação ---------- */
/* um único bloco de 6 colunas que quebra em 3 por linha (desktop) e 2 por linha (celular) */
.st-key-quick [data-testid="stHorizontalBlock"]{flex-wrap:wrap;gap:.75rem;}
.st-key-quick [data-testid="stColumn"]{flex:1 1 calc(33.333% - .75rem)!important;min-width:calc(33.333% - .75rem)!important;width:auto!important;}
.st-key-quick button > div{justify-content:flex-start;width:100%;}
.st-key-quick button [data-testid="stMarkdownContainer"], .st-key-quick button p{white-space:normal;overflow:visible;text-overflow:clip;}
.st-key-quick button{min-height:92px;height:100%;justify-content:flex-start;text-align:left;align-items:center;
  background:var(--card);border:1px solid var(--line);border-radius:var(--radius);box-shadow:var(--shadow);
  padding:.9rem 1rem;color:var(--navy);transition:border-color .15s, transform .15s, box-shadow .15s;}
.st-key-quick button:hover{border-color:var(--red);transform:translateY(-2px);color:var(--navy);
  box-shadow:0 10px 22px rgba(215,25,45,.12);}
.st-key-quick button:focus-visible{outline:3px solid var(--yellow);outline-offset:2px;}
.st-key-quick button p{font-size:.86rem;line-height:1.35;color:var(--ink-3);margin:0;}
.st-key-quick button p strong{display:block;font-size:1rem;color:var(--navy);margin-bottom:.15rem;}
.st-key-quick button [data-testid="stIconMaterial"]{font-size:1.6rem;color:var(--red);background:var(--red-50);
  border-radius:12px;padding:.45rem;margin-right:.5rem;}

/* ---------- mensagens ---------- */
[data-testid="stChatMessage"]{background:var(--card);border:1px solid var(--line);border-radius:var(--radius);
  box-shadow:var(--shadow);padding:1rem 1.15rem;margin-bottom:.9rem;}
[data-testid="stChatMessage"]:has([class*="st-key-user-msg"]){background:#FFF;border-color:#F3C9CE;
  box-shadow:none;border-left:4px solid var(--red);}
[data-testid="stChatMessage"]:has([class*="st-key-user-msg"]) p{font-weight:500;}

.status{display:inline-flex;align-items:center;gap:.4rem;font-size:.78rem;font-weight:700;letter-spacing:.02em;
  padding:.3rem .65rem;border-radius:999px;margin-bottom:.55rem;}
.status .dot{width:.5rem;height:.5rem;border-radius:50%;background:currentColor;}
.status.ok{background:var(--green-50);color:var(--green);}
.status.warn{background:var(--yellow-50);color:var(--yellow-700);}
.status.none{background:var(--slate-50);color:var(--slate);}
.status.block{background:var(--red-50);color:var(--red-700);}
.status .time{font-weight:500;color:var(--ink-3);margin-left:.25rem;}

.alert{display:flex;gap:.9rem;align-items:center;justify-content:space-between;flex-wrap:wrap;
  background:var(--red);color:#fff;border-radius:14px;padding:.85rem 1rem;margin:.2rem 0 .9rem;}
.alert strong{font-size:1rem;}
.alert span{font-size:.88rem;opacity:.92;}
.alert .alert-actions{display:flex;gap:.5rem;}
.alert a{background:#fff;color:var(--red-700)!important;text-decoration:none!important;font-weight:800;
  border-radius:10px;padding:.45rem .8rem;font-size:.9rem;}
@media (prefers-reduced-motion:no-preference){.alert{animation:pulse 2.2s ease-in-out 2;}}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(215,25,45,.45)}50%{box-shadow:0 0 0 10px rgba(215,25,45,0)}}

/* ---------- fontes ---------- */
.sources{margin-top:1rem;border-top:1px dashed var(--line);padding-top:.9rem;}
.sources-head{font:700 .78rem/1 var(--body);text-transform:uppercase;letter-spacing:.1em;color:var(--ink-3);margin-bottom:.6rem;}
.src-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:.6rem;}
.src{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:.65rem .75rem;}
.src[open]{background:#fff;grid-column:1/-1;}
.src summary{list-style:none;cursor:pointer;display:grid;grid-template-columns:auto 1fr;gap:.6rem;align-items:start;}
.src summary::-webkit-details-marker{display:none;}
.src-n{display:grid;place-items:center;width:1.6rem;height:1.6rem;border-radius:8px;background:var(--navy);color:#fff;
  font:700 .8rem/1 var(--body);}
.src-title{display:block;font-weight:650;font-size:.9rem;line-height:1.3;color:var(--navy);}
.src-meta{display:block;font-size:.76rem;color:var(--ink-3);margin-top:.15rem;}
.bar{display:block;height:4px;border-radius:4px;background:var(--line);margin-top:.45rem;overflow:hidden;}
.bar i{display:block;height:100%;background:var(--red);border-radius:4px;}
.src-excerpt{white-space:pre-wrap;font-size:.84rem;line-height:1.55;color:var(--ink-2);margin:.7rem 0 .1rem;
  border-left:3px solid var(--yellow);padding-left:.7rem;}
.src-hint{font-size:.72rem;color:var(--ink-3);margin-top:.4rem;}

/* ---------- "como esta resposta foi construída" ---------- */
.steps{list-style:none;margin:0;padding:0;}
.step{position:relative;padding:0 0 1rem 2rem;}
.step::before{content:"";position:absolute;left:.62rem;top:1.5rem;bottom:0;width:2px;background:var(--line);}
.step:last-child::before{display:none;}
.step-ico{position:absolute;left:0;top:.05rem;width:1.35rem;height:1.35rem;border-radius:50%;display:grid;place-items:center;
  font-size:.75rem;font-weight:800;color:#fff;background:var(--green);}
.step-ico.warn{background:var(--yellow);color:var(--navy);}
.step-ico.block{background:var(--red);}
.step-title{font-weight:700;font-size:.9rem;}
.step-body{font-size:.84rem;color:var(--ink-2);margin-top:.2rem;}
.step-body code{font-size:.78rem;background:var(--slate-50);padding:.1rem .35rem;border-radius:6px;color:var(--navy);}
.tool{display:flex;flex-wrap:wrap;gap:.35rem .6rem;align-items:baseline;padding:.35rem 0;border-bottom:1px dotted var(--line);}
.tool:last-child{border-bottom:0;}
.tool .ms{color:var(--ink-3);font-size:.75rem;}
.tool .q{color:var(--ink-2);font-style:italic;}
.flag{font-size:.8rem;color:var(--ink-2);padding:.25rem 0;}
.flag b{color:var(--yellow-700);}
.meta-line{font-size:.75rem;color:var(--ink-3);margin-top:.3rem;}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"]{background:#fff;border-right:1px solid var(--line);}
.side-brand{font:800 1.35rem/1 var(--display);text-transform:uppercase;color:var(--red);display:flex;align-items:center;gap:.5rem;}
.side-card{border:1px solid var(--line);border-radius:12px;padding:.7rem .8rem;margin:.6rem 0;font-size:.84rem;background:var(--bg);}
.side-card b{display:block;margin-bottom:.25rem;}
.ok-dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:var(--green);margin-right:.35rem;}
.bad-dot{display:inline-block;width:.55rem;height:.55rem;border-radius:50%;background:var(--red);margin-right:.35rem;}
.doc-item{padding:.45rem 0;border-bottom:1px solid var(--line);font-size:.82rem;line-height:1.35;}
.doc-item:last-child{border-bottom:0;}
.doc-item small{color:var(--ink-3);}

/* ---------- botão flutuante de emergência ---------- */
.fab{position:fixed;right:1.2rem;bottom:6.2rem;z-index:1000;display:flex;align-items:center;gap:.45rem;
  background:var(--red);color:#fff!important;text-decoration:none!important;font-weight:800;border-radius:999px;
  padding:.7rem 1rem;box-shadow:0 10px 24px rgba(215,25,45,.38);font-size:.95rem;}
.fab:hover{background:var(--red-700);}
.fab:focus-visible{outline:3px solid var(--yellow);outline-offset:3px;}

.st-key-scrolltop{position:absolute!important;width:0;height:0;overflow:hidden;opacity:0;pointer-events:none;}
.footer-note{text-align:center;color:var(--ink-3);font-size:.78rem;margin-top:1.5rem;}
.demo-banner{background:var(--yellow-50);border:1px solid #F5DD8A;color:var(--yellow-700);border-radius:12px;
  padding:.6rem .9rem;font-size:.85rem;margin-bottom:1rem;}

[data-testid="stChatInput"] textarea{font-size:1rem;}
[data-testid="stExpander"] details{border-radius:12px;border-color:var(--line);background:#fff;}

/* ---------- responsivo ---------- */
@media (max-width: 760px){
  .block-container{padding:3rem .85rem 2rem;}
  .hero{padding:1.1rem 1rem;border-radius:18px;gap:.9rem;margin-bottom:1rem;}
  .hero h1{font-size:1.85rem;}
  .buoy{width:48px;height:48px;}
  .lead{font-size:.9rem;margin-top:.7rem;}
  .chips{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;margin:.8rem -1rem 0;padding:0 1rem;}
  .chips::-webkit-scrollbar{display:none;}
  .chip{flex:none;font-size:.74rem;}
  .hero-cta{flex-direction:row;width:100%;min-width:0;}
  .hero-cta .call{flex:1;padding:.6rem .8rem;}
  .call small{display:none;}
  .section-title{font-size:1.25rem;}
  .hero.compact .brand .eyebrow{display:none;}
  .hero.compact h1{font-size:1.35rem;}
  /* atalhos: 2 por linha no celular (o Streamlit empilharia 1 por linha) */
  .st-key-quick [data-testid="stHorizontalBlock"]{gap:.6rem;}
  .st-key-quick [data-testid="stColumn"]{flex:1 1 calc(50% - .6rem)!important;min-width:calc(50% - .6rem)!important;}
  .st-key-quick button{min-height:84px;padding:.75rem;}
  .st-key-quick button p{font-size:.78rem;}
  .st-key-quick button [data-testid="stIconMaterial"]{font-size:1.3rem;margin-right:.3rem;}
  [data-testid="stChatMessage"]{padding:.85rem .8rem;}
  /* no celular o avatar rouba ~40px de largura; a borda vermelha e o chip de status já distinguem quem fala */
  [data-testid="stChatMessage"] > :first-child:not([data-testid="stChatMessageContent"]){display:none;}
  .alert-actions{width:100%;}
  .alert a{flex:1;text-align:center;white-space:nowrap;}
  .fab{right:.8rem;bottom:7.2rem;padding:.6rem .85rem;}
  .fab .fab-label{display:none;}
}
@media (max-width: 420px){
  .hero.compact .hero-cta .call small, .hero.compact .call span{display:none;}
  .src-grid{grid-template-columns:1fr;}
}
</style>
"""

# ------------------------------------------------------------------ ícones

# st.html sanitiza o HTML e remove <svg> inline; por isso os ícones vão como <img> com data URI.
_BUOY_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
<circle cx="24" cy="24" r="17" fill="none" stroke="#ffffff" stroke-width="11"/>
<circle cx="24" cy="24" r="17" fill="none" stroke="#D7192D" stroke-width="11"
  stroke-dasharray="13.35 13.35" transform="rotate(-22.5 24 24)"/>
<circle cx="24" cy="24" r="11.5" fill="none" stroke="#9AA4B2" stroke-width="1.2"/>
<circle cx="24" cy="24" r="22.5" fill="none" stroke="#9AA4B2" stroke-width="1.2"/>
</svg>"""

_PHONE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#ffffff">
<path d="M6.6 10.8a15.1 15.1 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.25 11.4 11.4 0 0 0 3.6.57 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.46.57 3.6a1 1 0 0 1-.25 1z"/></svg>"""


def _svg_img(svg: str, size: str, alt: str = "") -> str:
    import base64
    data = base64.b64encode(svg.encode()).decode()
    return f'<img src="data:image/svg+xml;base64,{data}" width="{size}" height="{size}" alt="{alt}" style="display:block">'


def buoy(size: str = "70%") -> str:
    return _svg_img(_BUOY_SVG, size)

# ------------------------------------------------------------------ componentes


def hero(compact: bool) -> str:
    lead = "" if compact else (
        '<p class="lead">Orientação passo a passo para quem está socorrendo alguém, com base em manuais '
        "oficiais do Ministério da Saúde, Corpos de Bombeiros e universidades federais.</p>"
        '<div class="chips"><span class="chip">📚 7 manuais oficiais</span>'
        '<span class="chip">🔎 Fonte em cada orientação</span>'
        '<span class="chip">🛡️ Verificação de segurança</span></div>'
    )
    return f"""
<section class="hero{' compact' if compact else ''}" aria-label="Assistente de Primeiros Socorros">
  <div>
    <div class="brand">
      <div class="buoy">{buoy()}</div>
      <div><div class="eyebrow">Assistente de</div><h1>Primeiros Socorros</h1></div>
    </div>
    {lead}
  </div>
  <nav class="hero-cta" aria-label="Telefones de emergência">
    <a class="call" href="tel:192"><span>SAMU<small>Urgência médica</small></span><b>192</b></a>
    <a class="call" href="tel:193"><span>Bombeiros<small>Resgate e acidentes</small></span><b>193</b></a>
  </nav>
</section>"""


def fab() -> str:
    return (f'<a class="fab" href="tel:192" aria-label="Ligar para o SAMU 192">{_svg_img(_PHONE_SVG, "18")}'
            f'<span class="fab-label">Ligar</span> 192</a>')


STATUS = {
    "answered": ("ok", "Resposta fundamentada nos manuais"),
    "answered_with_warning": ("warn", "Fundamentada, com ressalvas"),
    "no_evidence": ("none", "Sem evidência suficiente nos manuais"),
    "blocked_input": ("block", "Pedido fora do que posso orientar"),
    "blocked_output": ("warn", "Resposta retida pela verificação de segurança"),
    "error": ("block", "Não foi possível responder agora"),
}


def status_chip(status: str, elapsed_ms: float | None) -> str:
    cls, label = STATUS.get(status, ("none", status))
    t = f'<span class="time">· {elapsed_ms / 1000:.1f}s</span>' if elapsed_ms and elapsed_ms >= 100 else ""
    return f'<span class="status {cls}"><span class="dot"></span>{escape(label)}{t}</span>'


def emergency_alert() -> str:
    return """
<div class="alert" role="alert">
  <div><strong>🚨 Parece uma emergência.</strong><br><span>Ligue agora e siga as orientações enquanto a ajuda chega.</span></div>
  <div class="alert-actions"><a href="tel:192">📞 SAMU 192</a><a href="tel:193">🚒 Bombeiros 193</a></div>
</div>"""


def sources_grid(sources: list[dict], topic_labels: dict[str, str]) -> str:
    cards = []
    for s in sources:
        pct = max(4, min(100, round(s["score"] * 100)))
        topic = topic_labels.get(s["topic"], s["topic"])
        cards.append(f"""
<details class="src">
  <summary>
    <span class="src-n">{s['ref']}</span>
    <span>
      <span class="src-title">{escape(s['document_title'])}</span>
      <span class="src-meta">{escape(s.get('organization') or '')} · p. {escape(str(s['pages']))} · {escape(topic)}</span>
      <span class="bar" title="Similaridade com a pergunta: {s['score']:.2f}"><i style="width:{pct}%"></i></span>
    </span>
  </summary>
  <p class="src-excerpt">{escape(s['excerpt'])}</p>
  <div class="src-hint">Trecho <code>{escape(s['chunk_id'])}</code> · similaridade {s['score']:.2f}</div>
</details>""")
    return f'<div class="sources"><div class="sources-head">Fontes consultadas · toque para ver o trecho</div>' \
           f'<div class="src-grid">{"".join(cards)}</div></div>'


_CATEGORY_LABELS = {
    "primeiros_socorros": "primeiros socorros", "fora_do_escopo": "fora do escopo",
    "prescricao_medica": "prescrição médica", "prompt_injection": "tentativa de manipulação (prompt injection)",
    "conteudo_nocivo": "conteúdo nocivo", "invalida": "mensagem inválida",
}
_LAYER_LABELS = {"regras": "regras programáticas", "similaridade": "piso de similaridade", "llm": "classificador LLM"}


def build_trace(res: dict) -> str:
    """Linha do tempo: guardrail de entrada -> tools MCP -> guardrail de saída."""
    steps = []
    g_in = res.get("input_guardrail")
    if g_in:
        ok = g_in["allowed"]
        cat = _CATEGORY_LABELS.get(g_in["category"], g_in["category"])
        score = f" · similaridade máx. {g_in['top_score']:.2f}" if g_in.get("top_score") is not None else ""
        steps.append(("" if ok else "block", "✓" if ok else "✕", "Guardrail de entrada",
                      f"{'Liberado' if ok else 'Bloqueado'}: <b>{escape(cat)}</b> · camada: "
                      f"{escape(_LAYER_LABELS.get(g_in['layer'], g_in['layer']))}{score}<br>{escape(g_in['reason'])}"))

    calls = res.get("tool_calls") or []
    if calls:
        rows = []
        for tc in calls:
            args = tc["arguments"]
            q = f'<span class="q">“{escape(str(args.get("query")))}”</span>' if "query" in args else \
                f"<code>{escape(str(args))}</code>" if args else ""
            n = len(tc["result_summary"]) if isinstance(tc.get("result_summary"), list) else None
            found = "" if n is None else (f"{n} trecho · " if n == 1 else f"{n} trechos · ")
            who = "guardrail" if tc.get("purpose") == "guardrail_entrada" else "LLM"
            rows.append(f'<div class="tool"><code>{escape(tc["name"])}</code>{q}'
                        f'<span class="ms">{found}{tc["duration_ms"]:.0f} ms · chamada pelo {who}'
                        f'{" · erro" if tc["is_error"] else ""}</span></div>')
        steps.append(("", str(len(calls)), "Consultas à base via MCP", "".join(rows)))

    g_out = res.get("output_guardrail")
    if g_out:
        cls = {"answered": "", "no_evidence": "", "answered_with_warning": "warn"}.get(g_out["status"], "block")
        body = escape(g_out["reason"])
        if g_out.get("support_ratio") is not None:
            pct = round(g_out["support_ratio"] * 100)
            body += f'<span class="bar" title="{pct}% das frases com respaldo"><i style="width:{pct}%;background:var(--green)"></i></span>'
            flagged = [s for s in g_out.get("sentences", []) if not s["supported"]]
            for s in flagged[:4]:
                body += f'<div class="flag"><b>Sem respaldo direto:</b> “{escape(s["sentence"][:160])}”</div>'
        steps.append((cls, "✓" if cls == "" else "!", "Guardrail de saída", body))

    items = "".join(
        f'<li class="step"><span class="step-ico {c}">{ico}</span><div class="step-title">{t}</div>'
        f'<div class="step-body">{b}</div></li>' for c, ico, t, b in steps)
    u = res.get("usage") or {}
    meta = ""
    if u.get("llm_calls"):
        meta = (f'<div class="meta-line">{u["llm_calls"]} chamadas ao LLM · {u.get("input_tokens", 0):,} tokens de entrada '
                f'({u.get("cache_read_input_tokens", 0):,} do cache) · {u.get("output_tokens", 0):,} de saída</div>').replace(",", ".")
    return f'<ol class="steps">{items}</ol>{meta}'


def sidebar_status(health: dict | None, backend_url: str) -> str:
    if not health:
        return f'<div class="side-card"><span class="bad-dot"></span><b style="display:inline">Backend offline</b>' \
               f'<div>Inicie a API em {escape(backend_url)}</div></div>'
    tools = ", ".join(f"<code>{escape(t)}</code>" for t in health["mcp_tools"])
    return (f'<div class="side-card"><span class="ok-dot"></span><b style="display:inline">Sistema operacional</b>'
            f'<div style="margin-top:.35rem">Modelo: <code>{escape(health["model"])}</code></div>'
            f'<div style="margin-top:.25rem">Tools MCP: {tools}</div></div>')


def documents_list(docs: list[dict]) -> str:
    return "".join(f'<div class="doc-item"><b>{escape(d["title"])}</b><br><small>{escape(d["organization"] or "")}'
                   f'{" · " + str(d["year"]) if d.get("year") else ""} · {d["num_pages"]} p.</small></div>' for d in docs)
