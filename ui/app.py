from __future__ import annotations

import asyncio
import html
import inspect
import json
import os

import httpx
import nest_asyncio
import streamlit as st
import websockets

from config import get_settings
from core.logging_setup import configure_logging

try:
    from ui.components import task_event_card
except ImportError:
    from components import task_event_card

nest_asyncio.apply()


DEFAULT_QUESTION = (
    "Analyze one practical way autonomous AI agents could make literature "
    "reviews more reliable for independent researchers."
)


def _api_headers(settings) -> dict[str, str]:
    api_key = getattr(settings, "internal_api_key", None)
    return {"X-API-Key": api_key} if api_key else {}


def _websocket_connect(uri: str, headers: dict[str, str]):
    if not headers:
        return websockets.connect(uri)

    params = inspect.signature(websockets.connect).parameters
    header_arg = "additional_headers" if "additional_headers" in params else "extra_headers"
    return websockets.connect(uri, **{header_arg: headers})

STYLE_BLOCK = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,700;9..144,800&family=Nunito+Sans:wght@400;600;700;800;900&display=swap" rel="stylesheet">
<style>
    :root {
        --air-bg: #fff8ec;
        --air-bg-soft: #f7efe2;
        --air-surface: #ffffff;
        --air-surface-strong: #fff0d7;
        --air-ink: #243047;
        --air-muted: #687386;
        --air-line: #eadfce;
        --air-primary: #6d5dfc;
        --air-primary-dark: #4f46d8;
        --air-primary-light: rgba(109, 93, 252, 0.12);
        --air-teal: #0f9f8f;
        --air-teal-dark: #087f73;
        --air-teal-light: rgba(15, 159, 143, 0.12);
        --air-coral: #f97361;
        --air-coral-light: rgba(249, 115, 97, 0.13);
        --air-amber: #f6a623;
        --air-amber-light: rgba(246, 166, 35, 0.16);
        --air-sky: #2f80ed;
        --air-sky-light: rgba(47, 128, 237, 0.12);
        --air-rose: #e85d75;
        --air-error: #c2413d;
        --air-success: #18875f;
        --air-agent-planner: #7c3aed;
        --air-agent-researcher: #0f9f8f;
        --air-agent-coder: #2f80ed;
        --air-agent-critic: #f97361;
        --air-agent-debater: #f6a623;
        --air-shadow: 0 24px 70px rgba(57, 46, 34, 0.12);
        --air-shadow-soft: 0 14px 35px rgba(57, 46, 34, 0.09);
        --air-radius: 18px;
        --air-radius-lg: 24px;
        --air-display-font: "Fraunces", ui-serif, Georgia, serif;
        --air-font: "Nunito Sans", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        --air-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
    }

    html, body, [class*="css"] {
        font-family: var(--air-font);
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 8%, rgba(109, 93, 252, 0.15), transparent 26rem),
            radial-gradient(circle at 90% 18%, rgba(15, 159, 143, 0.12), transparent 23rem),
            linear-gradient(180deg, #fffaf1 0%, var(--air-bg) 40%, var(--air-bg-soft) 100%);
        color: var(--air-ink);
    }

    .block-container {
        max-width: 1280px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3, h4, h5, h6 {
        color: var(--air-ink);
        font-family: var(--air-display-font);
        letter-spacing: 0;
    }

    p {
        color: var(--air-muted);
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid var(--air-line);
        border-radius: var(--air-radius);
        box-shadow: var(--air-shadow-soft);
    }

    div[data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 1.15rem 1.2rem;
    }

    div[data-testid="stTextArea"] textarea {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid var(--air-line);
        border-radius: 16px;
        color: var(--air-ink);
        line-height: 1.5;
    }

    div[data-testid="stTextArea"] textarea:focus {
        border-color: var(--air-primary);
        box-shadow: 0 0 0 4px rgba(109, 93, 252, 0.15);
    }

    .stButton > button,
    .stDownloadButton > button {
        border: 1px solid var(--air-line);
        border-radius: 999px;
        font-weight: 900;
        min-height: 2.85rem;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-1px);
        box-shadow: var(--air-shadow-soft);
    }

    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--air-primary), var(--air-teal));
        border-color: transparent;
        color: #ffffff;
        box-shadow: 0 16px 30px rgba(109, 93, 252, 0.24);
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.45rem;
        border-bottom: 1px solid var(--air-line);
    }

    .stTabs [data-baseweb="tab"] {
        border-radius: 999px 999px 0 0;
        color: var(--air-muted);
        font-weight: 900;
    }

    .stTabs [aria-selected="true"] {
        color: var(--air-primary-dark);
    }

    .research-hero {
        position: relative;
        overflow: hidden;
        margin-bottom: 1.3rem;
        border: 1px solid rgba(234, 223, 206, 0.95);
        border-radius: 26px;
        background:
            radial-gradient(circle at 80% 18%, rgba(246, 166, 35, 0.25), transparent 14rem),
            linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(255, 240, 215, 0.86));
        box-shadow: var(--air-shadow);
        padding: clamp(1.35rem, 3vw, 2.2rem);
    }

    .research-hero:after {
        position: absolute;
        right: -4rem;
        bottom: -6rem;
        width: 18rem;
        height: 18rem;
        border-radius: 42% 58% 52% 48%;
        background: rgba(109, 93, 252, 0.12);
        content: "";
    }

    .hero-badge,
    .agent-pill,
    .task-status-badge,
    .agent-status-badge,
    .score-badge,
    .cost-badge,
    .stream-agent-badge,
    .mini-pill {
        border-radius: 999px;
        display: inline-flex;
        align-items: center;
        width: fit-content;
        font-weight: 1000;
    }

    .hero-badge {
        background: var(--air-primary-light);
        border: 1px solid rgba(109, 93, 252, 0.2);
        color: var(--air-primary-dark);
        font-size: 0.76rem;
        letter-spacing: 0.08em;
        padding: 0.32rem 0.72rem;
        text-transform: uppercase;
    }

    .research-hero h1 {
        color: var(--air-ink);
        font-size: clamp(2.4rem, 5vw, 4.8rem);
        line-height: 0.95;
        margin: 0.75rem 0 0.65rem;
        max-width: 900px;
        position: relative;
        z-index: 1;
    }

    .research-hero p {
        color: var(--air-muted);
        font-size: 1.08rem;
        margin: 0 0 1.1rem;
        max-width: 760px;
        position: relative;
        z-index: 1;
    }

    .agent-pill-row {
        display: flex;
        flex-wrap: wrap;
        gap: 0.55rem;
        position: relative;
        z-index: 1;
    }

    .agent-pill {
        border: 1px solid transparent;
        font-size: 0.8rem;
        padding: 0.42rem 0.78rem;
        text-transform: uppercase;
    }

    .agent-pill--planner { background: rgba(124, 58, 237, 0.11); border-color: rgba(124, 58, 237, 0.22); color: var(--air-agent-planner); }
    .agent-pill--researcher { background: var(--air-teal-light); border-color: rgba(15, 159, 143, 0.22); color: var(--air-teal-dark); }
    .agent-pill--coder { background: var(--air-sky-light); border-color: rgba(47, 128, 237, 0.2); color: var(--air-sky); }
    .agent-pill--critic { background: var(--air-coral-light); border-color: rgba(249, 115, 97, 0.24); color: #c44a3d; }
    .agent-pill--debater { background: var(--air-amber-light); border-color: rgba(246, 166, 35, 0.28); color: #98600b; }

    .panel-title {
        color: var(--air-ink);
        font-family: var(--air-display-font);
        font-size: 1.55rem;
        font-weight: 800;
        line-height: 1.05;
        margin: 0 0 0.25rem;
    }

    .panel-caption,
    .section-caption {
        color: var(--air-muted);
        font-size: 0.92rem;
        margin: 0 0 1rem;
    }

    .section-heading {
        align-items: center;
        color: var(--air-ink);
        display: flex;
        font-size: 1.02rem;
        font-weight: 1000;
        gap: 0.45rem;
        margin: 0.2rem 0 0.35rem;
    }

    .tip-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 0.75rem;
    }

    .tip-card,
    .status-bar,
    .placeholder-card,
    .success-banner,
    .stream-card,
    .kg-card,
    .task-event-card,
    .agent-card {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid var(--air-line);
        border-radius: var(--air-radius);
        box-shadow: var(--air-shadow-soft);
    }

    .tip-card {
        padding: 0.95rem;
    }

    .tip-card strong {
        color: var(--air-ink);
        display: block;
        margin-bottom: 0.22rem;
    }

    .tip-card span {
        color: var(--air-muted);
        font-size: 0.88rem;
    }

    .status-bar {
        align-items: center;
        display: flex;
        gap: 0.7rem;
        margin: 0.25rem 0 1rem;
        padding: 0.9rem 1rem;
    }

    .status-bar__dot {
        border-radius: 999px;
        display: inline-block;
        height: 0.78rem;
        width: 0.78rem;
    }

    .status-bar__dot.is-running {
        animation: airPulse 1.7s ease-in-out infinite;
    }

    .status-bar__text {
        color: var(--air-ink);
        font-weight: 900;
    }

    .placeholder-card {
        color: var(--air-muted);
        font-weight: 750;
        margin: 0.6rem 0;
        padding: 1.35rem;
        text-align: center;
    }

    .placeholder-card strong {
        color: var(--air-ink);
        display: block;
        font-family: var(--air-display-font);
        font-size: 1.25rem;
        margin-bottom: 0.25rem;
    }

    .task-event-card,
    .agent-card {
        border-left: 6px solid var(--agent-accent, var(--air-primary));
        margin: 0 0 0.75rem;
        padding: 0.95rem 1rem;
    }

    .task-event-card__top,
    .agent-card__header,
    .kg-card__top {
        align-items: center;
        display: flex;
        gap: 0.65rem;
        justify-content: space-between;
        margin-bottom: 0.55rem;
    }

    .task-event-card__top {
        justify-content: flex-start;
    }

    .task-event-card code {
        background: var(--air-bg-soft);
        border: 1px solid var(--air-line);
        border-radius: 9px;
        color: var(--air-ink);
        font-size: 0.84rem;
        padding: 0.2rem 0.42rem;
    }

    .task-event-card p,
    .kg-card p,
    .agent-card p {
        color: var(--air-muted);
        font-size: 0.92rem;
        line-height: 1.45;
        margin: 0;
    }

    .task-status-badge,
    .agent-status-badge,
    .score-badge,
    .cost-badge,
    .stream-agent-badge,
    .mini-pill {
        font-size: 0.72rem;
        letter-spacing: 0.05em;
        line-height: 1;
        padding: 0.38rem 0.58rem;
        text-transform: uppercase;
    }

    .status-running { background: var(--air-sky-light); color: var(--air-sky); }
    .status-done { background: rgba(24, 135, 95, 0.13); color: var(--air-success); }
    .status-error { background: #fee4e2; color: var(--air-error); }
    .status-cancelled { background: var(--air-amber-light); color: #98600b; }
    .status-pending, .status-default { background: var(--air-bg-soft); color: var(--air-muted); }

    .stream-card {
        background: linear-gradient(135deg, rgba(109, 93, 252, 0.08), rgba(15, 159, 143, 0.08));
        margin-top: 1rem;
        padding: 1rem;
    }

    .stream-agent-badge,
    .cost-badge {
        background: var(--air-teal-light);
        color: var(--air-teal-dark);
    }

    .stream-card pre {
        color: var(--air-ink);
        font-family: var(--air-mono);
        font-size: 0.86rem;
        line-height: 1.55;
        margin: 0.7rem 0 0;
        white-space: pre-wrap;
        word-break: break-word;
    }

    .cursor {
        animation: blink 1s step-end infinite;
        color: var(--air-primary);
        font-weight: 1000;
    }

    .success-banner {
        align-items: center;
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
        justify-content: space-between;
        margin: 0.25rem 0 1rem;
        padding: 1rem 1.1rem;
    }

    .success-banner strong {
        color: var(--air-success);
        font-size: 1.04rem;
    }

    .download-note {
        color: var(--air-muted);
        font-size: 0.9rem;
        margin: 0 0 0.8rem;
    }

    .kg-card {
        margin: 0.75rem 0 0;
        padding: 0.95rem;
    }

    .kg-card__run {
        color: var(--air-ink);
        font-weight: 900;
    }

    .score-badge {
        background: var(--air-primary-light);
        color: var(--air-primary-dark);
    }

    .agent-card h4 {
        color: var(--air-ink);
        font-size: 1rem;
        margin: 0 0 0.2rem;
    }

    .agent-card__footer {
        border-top: 1px solid var(--air-line);
        color: var(--air-muted);
        display: flex;
        flex-wrap: wrap;
        font-size: 0.82rem;
        font-weight: 800;
        gap: 0.75rem;
        margin-top: 0.9rem;
        padding-top: 0.75rem;
    }

    @keyframes blink {
        50% { opacity: 0; }
    }

    @keyframes airPulse {
        0%, 100% {
            box-shadow: 0 0 0 8px rgba(15, 159, 143, 0.12);
            transform: scale(1);
        }
        50% {
            box-shadow: 0 0 0 15px rgba(15, 159, 143, 0.04);
            transform: scale(1.12);
        }
    }

    @media (prefers-reduced-motion: reduce) {
        *, *::before, *::after {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
        }
    }
</style>
"""


def _init_session_state() -> None:
    """Initialize Streamlit session keys in one place."""
    st.session_state.setdefault("tasks", [])
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("buffers", {})
    st.session_state.setdefault("run_id", "")


def _truncate(value: object, limit: int) -> str:
    text = str(value or "").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return f"{text[: max(0, limit - 1)].rstrip()}..."


def _inject_css() -> None:
    st.markdown(STYLE_BLOCK, unsafe_allow_html=True)


def _render_hero() -> None:
    st.markdown(
        """
        <div class="research-hero">
            <span class="hero-badge">v2.0 · Open Source</span>
            <h1>Autonomous AI Researcher</h1>
            <p>A friendly control room for turning a question into a planned, tested, and critiqued research brief.</p>
            <div class="agent-pill-row">
                <span class="agent-pill agent-pill--planner">Planner</span>
                <span class="agent-pill agent-pill--researcher">Researcher</span>
                <span class="agent-pill agent-pill--coder">Coder</span>
                <span class="agent-pill agent-pill--critic">Critic</span>
                <span class="agent-pill agent-pill--debater">Debater</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_tips() -> None:
    with st.expander("How it works", expanded=False):
        st.markdown(
            """
            <div class="tip-grid">
                <div class="tip-card">
                    <strong>Start specific</strong>
                    <span>Ask about one method, dataset, tradeoff, or research direction.</span>
                </div>
                <div class="tip-card">
                    <strong>Watch the agents</strong>
                    <span>The live feed shows task updates and token streams as the run unfolds.</span>
                </div>
                <div class="tip-card">
                    <strong>Review critically</strong>
                    <span>The Critic helps, but final claims still need human checking.</span>
                </div>
                <div class="tip-card">
                    <strong>Export the report</strong>
                    <span>Download Markdown or PDF when the backend writes those files.</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_section_heading(icon: str, title: str, caption: str | None = None) -> None:
    st.markdown(
        f"""
        <div class="section-heading">
            <span>{html.escape(icon)}</span>
            <span>{html.escape(title)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if caption:
        st.markdown(
            f'<p class="section-caption">{html.escape(caption)}</p>',
            unsafe_allow_html=True,
        )


def _render_status_bar() -> None:
    running = st.session_state.running
    dot_color = "#0f9f8f" if running else "#c8bfaf"
    dot_class = "is-running" if running else ""
    label = "Agents running..." if running else "Idle — ready to run"
    st.markdown(
        f"""
        <div class="status-bar">
            <span class="status-bar__dot {dot_class}" style="background: {dot_color};"></span>
            <span class="status-bar__text">{html.escape(label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_placeholder(title: str, message: str | None = None) -> None:
    body = html.escape(message or "")
    st.markdown(
        f"""
        <div class="placeholder-card">
            <strong>{html.escape(title)}</strong>
            {body}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_task_feed(tasks: list[dict]) -> None:
    if not tasks:
        _render_placeholder(
            "No agent notes yet",
            "Run a research question to watch Planner, Researcher, Coder, Critic, and Debater updates appear here.",
        )
        return

    for task in tasks[-10:]:
        st.markdown(task_event_card(task), unsafe_allow_html=True)


def _render_token_buffers() -> None:
    for agent, content in st.session_state.buffers.items():
        safe_agent = html.escape(str(agent))
        safe_content = html.escape(str(content))
        st.markdown(
            f"""
            <div class="stream-card">
                <span class="stream-agent-badge">{safe_agent}</span>
                <pre>{safe_content}<span class="cursor">|</span></pre>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _similarity_badge_style(score: float) -> tuple[str, str]:
    if score > 0.7:
        return "rgba(24, 135, 95, 0.13)", "#18875f"
    if score >= 0.4:
        return "rgba(246, 166, 35, 0.16)", "#98600b"
    return "#f7efe2", "#687386"


def _render_knowledge_card(item: dict) -> None:
    score = float(item.get("similarity", 0) or 0)
    badge_bg, badge_text = _similarity_badge_style(score)
    run_id = html.escape(str(item.get("run_id", "unknown")))
    summary = html.escape(_truncate(item.get("summary", ""), 160))
    st.markdown(
        f"""
        <div class="kg-card">
            <div class="kg-card__top">
                <span class="kg-card__run">Run ID: {run_id}</span>
                <span class="score-badge" style="background: {badge_bg}; color: {badge_text};">
                    {score:.2f}
                </span>
            </div>
            <p>{summary if summary else "No summary available."}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _cancel_run(settings) -> None:
    run_id = st.session_state.run_id
    if not run_id:
        st.info("No active run is available to cancel.")
        st.session_state.running = False
        return

    try:
        response = httpx.delete(
            f"{settings.api_base_url}/api/research/{run_id}",
            headers=_api_headers(settings),
            timeout=15,
        )
        if response.status_code == 404:
            st.info("That run already finished or could not be found.")
        else:
            response.raise_for_status()
            if hasattr(st, "toast"):
                st.toast("Research run cancellation requested.")
            else:
                st.info("Research run cancellation requested.")
        st.session_state.running = False
    except Exception as exc:
        st.error(f"Failed to cancel run: {exc}")


async def _stream_research_events(settings, run_id: str, feed_container, token_container) -> None:
    ws_url = settings.api_base_url.replace("http", "ws", 1)
    uri = f"{ws_url}/api/research/{run_id}/stream"
    try:
        async with _websocket_connect(uri, _api_headers(settings)) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data["type"] == "task_update":
                    st.session_state.tasks.append(data["task"])
                    with feed_container.container():
                        _render_task_feed(st.session_state.tasks)
                elif data["type"] == "token":
                    agent = data["agent"]
                    delta = data["delta"]
                    st.session_state.buffers[agent] = st.session_state.buffers.get(agent, "") + delta
                    with token_container.container():
                        _render_token_buffers()
                elif data["type"] == "done":
                    st.session_state.result = data["result"]
                    st.session_state.running = False
                    st.rerun()
                    break
                elif data["type"] == "cancelled":
                    st.info(data.get("error", "Run cancelled."))
                    st.session_state.running = False
                    break
                elif data["type"] == "error":
                    st.error(data.get("error", "Run failed."))
                    st.session_state.running = False
                    break
    except Exception as exc:
        st.error(f"WebSocket Error: {exc}")
        st.session_state.running = False


def _start_research(settings, question: str) -> None:
    st.session_state.running = True
    st.session_state.result = None
    st.session_state.tasks = []
    st.session_state.buffers = {}
    try:
        response = httpx.post(
            f"{settings.api_base_url}/api/research",
            json={"question": question},
            headers=_api_headers(settings),
            timeout=30,
        )
        response.raise_for_status()
        st.session_state.run_id = response.json()["run_id"]
    except Exception as exc:
        st.error(f"Failed to start run: {exc}")
        st.session_state.running = False


def _render_control_panel(settings) -> None:
    with st.container(border=True):
        st.markdown('<div class="panel-title">Control Panel</div>', unsafe_allow_html=True)
        st.markdown(
            '<p class="panel-caption">Choose a question, start a run, and optionally compare it to prior local research.</p>',
            unsafe_allow_html=True,
        )
        _render_tips()

        _render_section_heading(
            "🔬",
            "Research Question",
            "Set the direction for the multi-agent research run.",
        )
        question = st.text_area(
            "Research Question",
            DEFAULT_QUESTION,
            height=170,
            placeholder=DEFAULT_QUESTION,
            label_visibility="collapsed",
        )
        if st.button("▶ Run Research", type="primary", use_container_width=True):
            _start_research(settings, question)

        st.divider()

        _render_section_heading(
            "🧠",
            "Prior Knowledge",
            "Find related past research from the local knowledge graph.",
        )
        if st.button("Load Knowledge Graph", use_container_width=True):
            try:
                from memory.knowledge_graph import KnowledgeGraph

                kg = KnowledgeGraph()
                related = kg.query_related(question, k=3)
                if not related:
                    st.info("No prior related research found.")
                else:
                    for item in related:
                        _render_knowledge_card(item)
            except Exception as exc:
                st.error(f"Knowledge graph unavailable: {exc}")


def _render_live_tab(settings) -> None:
    _render_status_bar()
    if st.session_state.running:
        if st.button("Cancel run", use_container_width=True):
            _cancel_run(settings)
            st.rerun()

    feed_container = st.empty()
    token_container = st.empty()
    if st.session_state.running and st.session_state.run_id:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                _stream_research_events(
                    settings,
                    st.session_state.run_id,
                    feed_container,
                    token_container,
                )
            )
        finally:
            loop.close()
    else:
        with feed_container.container():
            _render_task_feed(st.session_state.tasks)
        with token_container.container():
            _render_token_buffers()


def _render_report_tab() -> None:
    result = st.session_state.result
    if not result:
        _render_placeholder(
            "No report yet",
            "When a run completes, the cost badge, downloads, and Markdown preview will appear here.",
        )
        return

    cost_estimate = result["usage"]["cost_estimate"]
    st.markdown(
        f"""
        <div class="success-banner">
            <strong>Research complete</strong>
            <span class="cost-badge">${cost_estimate:.3f}</span>
        </div>
        <p class="download-note">Download the generated report files or review the Markdown preview below.</p>
        """,
        unsafe_allow_html=True,
    )

    md_path = result.get("report_md")
    pdf_path = result.get("report_pdf_path")
    md_content = None

    download_col_1, download_col_2 = st.columns([1, 1])
    if md_path and os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8") as file:
            md_content = file.read()
        with download_col_1:
            st.download_button(
                "Download Markdown",
                md_content,
                "report.md",
                "text/markdown",
                use_container_width=True,
            )

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as file:
            pdf_bytes = file.read()
        with download_col_2:
            st.download_button(
                "Download PDF",
                pdf_bytes,
                "report.pdf",
                "application/pdf",
                use_container_width=True,
            )

    if md_content is not None:
        with st.expander("Preview Report", expanded=True):
            st.markdown(md_content)


def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    st.set_page_config(layout="wide", page_title="Autonomous AI Researcher")
    _init_session_state()
    _inject_css()
    _render_hero()

    left_col, right_col = st.columns([0.3, 0.7], gap="large")

    with left_col:
        _render_control_panel(settings)

    with right_col:
        live_tab, report_tab = st.tabs(["🔴 Live Activity", "📄 Report"])

        with live_tab:
            _render_live_tab(settings)

        with report_tab:
            _render_report_tab()


if __name__ == "__main__":
    main()
