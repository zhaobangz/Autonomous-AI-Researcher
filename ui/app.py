import nest_asyncio
nest_asyncio.apply()

import streamlit as st
import os, json, asyncio, websockets, httpx
import html
from config import get_settings
from core.logging_setup import configure_logging

try:
    from ui.components import task_event_card
except ImportError:
    from components import task_event_card


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
    return f"{text[: max(0, limit - 1)].rstrip()}…"


def _inject_css() -> None:
    st.markdown(
        """
        <style>
            :root {
                --research-bg: #f7f8fb;
                --research-surface: #ffffff;
                --research-primary: #0f766e;
                --research-secondary: #6d28d9;
                --research-danger: #b91c1c;
                --research-text: #172033;
                --research-muted: #617087;
                --research-border: #d8dee8;
                --research-shadow: 0 4px 24px rgba(23,32,51,0.08);
                --research-radius: 14px;
                --research-font: ui-sans-serif, system-ui, -apple-system, sans-serif;
            }

            html, body, [class*="css"] {
                font-family: var(--research-font);
            }

            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(15, 118, 110, 0.08), transparent 28rem),
                    linear-gradient(180deg, #ffffff 0%, var(--research-bg) 18rem);
                color: var(--research-text);
            }

            .block-container {
                max-width: 1280px;
                padding-top: 2rem;
                padding-bottom: 2.5rem;
            }

            h1, h2, h3, h4, h5, h6, p {
                font-family: var(--research-font);
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                background: var(--research-surface);
                border: 1px solid var(--research-border);
                border-radius: var(--research-radius);
                box-shadow: var(--research-shadow);
            }

            div[data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 1.1rem 1.15rem;
            }

            div[data-testid="stTextArea"] textarea {
                border-color: var(--research-border);
                border-radius: 12px;
                color: var(--research-text);
                line-height: 1.5;
            }

            div[data-testid="stTextArea"] textarea:focus {
                border-color: var(--research-primary);
                box-shadow: 0 0 0 1px var(--research-primary);
            }

            .stButton > button,
            .stDownloadButton > button {
                border-radius: 999px;
                border-color: var(--research-border);
                font-weight: 700;
                min-height: 2.75rem;
            }

            .stButton > button[kind="primary"] {
                background: linear-gradient(135deg, var(--research-primary), #115e59);
                border: 1px solid var(--research-primary);
                color: #ffffff;
                box-shadow: 0 10px 22px rgba(15, 118, 110, 0.18);
            }

            .stTabs [data-baseweb="tab-list"] {
                gap: 0.5rem;
                border-bottom: 1px solid var(--research-border);
            }

            .stTabs [data-baseweb="tab"] {
                border-radius: 999px 999px 0 0;
                font-weight: 700;
                color: var(--research-muted);
            }

            .stTabs [aria-selected="true"] {
                color: var(--research-primary);
            }

            .research-hero {
                background:
                    linear-gradient(135deg, rgba(23, 32, 51, 0.96), rgba(15, 118, 110, 0.88)),
                    linear-gradient(90deg, rgba(109, 40, 217, 0.2), rgba(15, 118, 110, 0.1));
                border: 1px solid rgba(255,255,255,0.14);
                border-radius: 20px;
                box-shadow: 0 18px 48px rgba(23,32,51,0.18);
                color: #ffffff;
                margin-bottom: 1.4rem;
                overflow: hidden;
                padding: 2rem;
                position: relative;
            }

            .research-hero:after {
                background: linear-gradient(135deg, rgba(255,255,255,0.12), transparent);
                content: "";
                height: 100%;
                position: absolute;
                right: -12%;
                top: 0;
                transform: skewX(-18deg);
                width: 34%;
            }

            .hero-badge {
                align-items: center;
                background: rgba(204, 251, 241, 0.16);
                border: 1px solid rgba(204, 251, 241, 0.36);
                border-radius: 999px;
                color: #ccfbf1;
                display: inline-flex;
                font-size: 0.78rem;
                font-weight: 800;
                letter-spacing: 0;
                padding: 0.32rem 0.68rem;
                text-transform: uppercase;
            }

            .research-hero h1 {
                color: #ffffff;
                font-size: clamp(2.1rem, 4vw, 4.2rem);
                line-height: 1.02;
                margin: 0.8rem 0 0.75rem;
                max-width: 880px;
            }

            .research-hero p {
                color: rgba(255,255,255,0.84);
                font-size: 1.05rem;
                margin: 0 0 1.2rem;
            }

            .agent-pill-row {
                display: flex;
                flex-wrap: wrap;
                gap: 0.55rem;
                position: relative;
                z-index: 1;
            }

            .agent-pill {
                border-radius: 999px;
                font-size: 0.86rem;
                font-weight: 800;
                padding: 0.42rem 0.78rem;
            }

            .agent-pill--planner { background: #ccfbf1; color: #115e59; }
            .agent-pill--researcher { background: #ede9fe; color: #5b21b6; }
            .agent-pill--coder { background: #dbeafe; color: #1d4ed8; }
            .agent-pill--critic { background: #fee2e2; color: #991b1b; }

            .section-heading {
                align-items: center;
                color: var(--research-text);
                display: flex;
                font-size: 1.02rem;
                font-weight: 850;
                gap: 0.45rem;
                margin: 0 0 0.9rem;
            }

            .section-caption {
                color: var(--research-muted);
                font-size: 0.88rem;
                margin: -0.35rem 0 0.9rem;
            }

            .panel-title {
                color: var(--research-text);
                font-size: 1.24rem;
                font-weight: 900;
                margin: 0 0 1.1rem;
            }

            .status-bar,
            .placeholder-card,
            .success-banner,
            .stream-card,
            .kg-card,
            .task-event-card,
            .agent-card {
                background: var(--research-surface);
                border: 1px solid var(--research-border);
                border-radius: var(--research-radius);
                box-shadow: var(--research-shadow);
            }

            .status-bar {
                align-items: center;
                display: flex;
                gap: 0.65rem;
                margin: 0.25rem 0 1rem;
                padding: 0.85rem 1rem;
            }

            .status-bar__dot {
                border-radius: 999px;
                display: inline-block;
                height: 0.68rem;
                width: 0.68rem;
            }

            .status-bar__text {
                color: var(--research-text);
                font-weight: 750;
            }

            .placeholder-card {
                color: var(--research-muted);
                font-weight: 650;
                margin: 0.6rem 0;
                padding: 1.2rem;
                text-align: center;
            }

            .task-event-card {
                margin: 0 0 0.75rem;
                padding: 0.95rem 1rem;
            }

            .task-event-card__top {
                align-items: center;
                display: flex;
                gap: 0.65rem;
                margin-bottom: 0.55rem;
            }

            .task-event-card code {
                background: #f1f5f9;
                border: 1px solid #e2e8f0;
                border-radius: 7px;
                color: var(--research-text);
                font-size: 0.84rem;
                padding: 0.17rem 0.38rem;
            }

            .task-event-card p {
                color: var(--research-muted);
                font-size: 0.92rem;
                line-height: 1.45;
                margin: 0;
            }

            .task-status-badge,
            .agent-status-badge,
            .score-badge,
            .cost-badge,
            .stream-agent-badge {
                border-radius: 999px;
                display: inline-flex;
                font-size: 0.72rem;
                font-weight: 850;
                letter-spacing: 0;
                line-height: 1;
                padding: 0.34rem 0.55rem;
                text-transform: uppercase;
            }

            .stream-agent-badge,
            .cost-badge {
                background: #ccfbf1;
                color: #115e59;
            }

            .stream-card {
                background: #f0fdfa;
                margin-top: 1rem;
                padding: 1rem;
            }

            .stream-card pre {
                color: var(--research-text);
                font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                font-size: 0.86rem;
                line-height: 1.55;
                margin: 0.7rem 0 0;
                white-space: pre-wrap;
                word-break: break-word;
            }

            .cursor {
                animation: blink 1s step-end infinite;
                color: var(--research-primary);
                font-weight: 900;
            }

            @keyframes blink {
                50% { opacity: 0; }
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
                color: #166534;
                font-size: 1.02rem;
            }

            .kg-card {
                margin: 0.75rem 0 0;
                padding: 0.9rem 0.95rem;
            }

            .kg-card__top {
                align-items: center;
                display: flex;
                gap: 0.65rem;
                justify-content: space-between;
                margin-bottom: 0.55rem;
            }

            .kg-card__run {
                color: var(--research-text);
                font-weight: 820;
            }

            .kg-card p {
                color: var(--research-muted);
                font-size: 0.9rem;
                line-height: 1.45;
                margin: 0;
            }

            .agent-card {
                border-left: 5px solid var(--research-muted);
                margin: 0 0 0.9rem;
                padding: 1rem;
            }

            .agent-card__header {
                align-items: flex-start;
                display: flex;
                gap: 0.8rem;
                justify-content: space-between;
            }

            .agent-card h4 {
                color: var(--research-text);
                font-size: 1rem;
                margin: 0 0 0.2rem;
            }

            .agent-card p {
                color: var(--research-muted);
                font-size: 0.88rem;
                margin: 0;
            }

            .agent-card__footer {
                border-top: 1px solid var(--research-border);
                color: var(--research-muted);
                display: flex;
                flex-wrap: wrap;
                font-size: 0.82rem;
                font-weight: 700;
                gap: 0.75rem;
                margin-top: 0.9rem;
                padding-top: 0.75rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero() -> None:
    st.markdown(
        """
        <div class="research-hero">
            <span class="hero-badge">CS Class Project</span>
            <h1>Autonomous AI Researcher</h1>
            <p>Planner → Researcher → Coder → Critic — fully autonomous.</p>
            <div class="agent-pill-row">
                <span class="agent-pill agent-pill--planner">Planner</span>
                <span class="agent-pill agent-pill--researcher">Researcher</span>
                <span class="agent-pill agent-pill--coder">Coder</span>
                <span class="agent-pill agent-pill--critic">Critic</span>
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
    dot_color = "#22c55e" if running else "#cbd5e1"
    label = "Agents running..." if running else "Idle — ready to run"
    st.markdown(
        f"""
        <div class="status-bar">
            <span class="status-bar__dot" style="background: {dot_color};"></span>
            <span class="status-bar__text">{html.escape(label)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_placeholder(message: str) -> None:
    st.markdown(
        f'<div class="placeholder-card">{html.escape(message)}</div>',
        unsafe_allow_html=True,
    )


def _render_task_feed(tasks: list[dict]) -> None:
    if not tasks:
        _render_placeholder("Run a research question to watch agents work in real time.")
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
                <pre>{safe_content}<span class="cursor">▌</span></pre>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _similarity_badge_style(score: float) -> tuple[str, str]:
    if score > 0.7:
        return "#dcfce7", "#166534"
    if score >= 0.4:
        return "#fef3c7", "#92400e"
    return "#eef2f7", "#465469"


def _render_knowledge_card(item: dict) -> None:
    score = float(item.get("similarity", 0) or 0)
    badge_bg, badge_text = _similarity_badge_style(score)
    run_id = html.escape(str(item.get("run_id", "unknown")))
    summary = html.escape(_truncate(item.get("summary", ""), 140))
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


async def _stream_research_events(settings, run_id: str, feed_container, token_container) -> None:
    ws_url = settings.api_base_url.replace("http", "ws", 1)
    uri = f"{ws_url}/api/research/{run_id}/stream"
    try:
        async with websockets.connect(uri) as ws:
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
                elif data["type"] in {"error", "cancelled"}:
                    st.error(data.get("error", f"Run {data['type']}"))
                    st.session_state.running = False
                    break
    except Exception as e:
        st.error(f"WebSocket Error: {e}")
        st.session_state.running = False


def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    st.set_page_config(layout="wide", page_title="Autonomous AI Researcher")
    _init_session_state()
    _inject_css()
    _render_hero()

    left_col, right_col = st.columns([0.28, 0.72], gap="large")

    with left_col:
        with st.container(border=True):
            st.markdown('<div class="panel-title">Control Panel</div>', unsafe_allow_html=True)
            _render_section_heading(
                "🔬",
                "Research Question",
                "Set the direction for the multi-agent research run.",
            )
            question = st.text_area(
                "Research Question",
                "Analyze the impact of different activation functions on Transformer convergence speed.",
                height=150,
                placeholder="Analyze the impact of different activation functions on Transformer convergence speed.",
                label_visibility="collapsed",
            )
            if st.button("▶ Run Research", type="primary", use_container_width=True):
                st.session_state.running = True
                st.session_state.result = None
                st.session_state.tasks = []
                st.session_state.buffers = {}
                try:
                    resp = httpx.post(
                        f"{settings.api_base_url}/api/research",
                        json={"question": question},
                        timeout=30,
                    )
                    resp.raise_for_status()
                    st.session_state.run_id = resp.json()["run_id"]
                except Exception as e:
                    st.error(f"Failed to start run: {e}")
                    st.session_state.running = False

            st.divider()

            _render_section_heading(
                "🗂️",
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
                except Exception as e:
                    st.error(f"Knowledge graph unavailable: {e}")

    with right_col:
        live_tab, report_tab = st.tabs(["🔴 Live Activity", "📄 Report"])

        with live_tab:
            _render_status_bar()
            feed_container = st.empty()
            token_container = st.empty()
            if st.session_state.running and "run_id" in st.session_state:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(
                        _stream_research_events(settings, st.session_state.run_id, feed_container, token_container)
                    )
                finally:
                    loop.close()
            else:
                with feed_container.container():
                    _render_task_feed(st.session_state.tasks)
                with token_container.container():
                    _render_token_buffers()

        with report_tab:
            result = st.session_state.result
            if result:
                cost_estimate = result["usage"]["cost_estimate"]
                st.markdown(
                    f"""
                    <div class="success-banner">
                        <strong>✅ Research complete</strong>
                        <span class="cost-badge">${cost_estimate:.3f}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                md_path = result.get("report_md")
                pdf_path = result.get("report_pdf_path")
                md_content = None

                download_col_1, download_col_2 = st.columns([1, 1])
                if md_path and os.path.exists(md_path):
                    with open(md_path, "r", encoding="utf-8") as f:
                        md_content = f.read()
                    with download_col_1:
                        st.download_button(
                            "⬇ Markdown",
                            md_content,
                            "report.md",
                            "text/markdown",
                            use_container_width=True,
                        )

                if pdf_path and os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        pdf_bytes = f.read()
                    with download_col_2:
                        st.download_button(
                            "⬇ PDF",
                            pdf_bytes,
                            "report.pdf",
                            "application/pdf",
                            use_container_width=True,
                        )

                if md_content is not None:
                    with st.expander("Preview Report", expanded=True):
                        st.markdown(md_content)
            else:
                _render_placeholder("Your report will appear here after a research run completes.")


if __name__ == "__main__":
    main()
