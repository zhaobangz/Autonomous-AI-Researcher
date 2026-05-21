import nest_asyncio
nest_asyncio.apply()

import streamlit as st
import os, json, asyncio, websockets, httpx
from config import get_settings
from core.logging_setup import configure_logging


def _init_session_state() -> None:
    """Initialize Streamlit session keys in one place."""
    st.session_state.setdefault("tasks", [])
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("buffers", {})


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
                        st.markdown(f"**{agent} (streaming...)**\n{st.session_state.buffers[agent]} ▌")
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


def _render_task_feed(tasks: list[dict]) -> None:
    for task in tasks[-10:]:
        st.info(
            f"**[{task.get('status','?').upper()}]** "
            f"{task.get('kind','?')}: {str(task.get('input',''))[:100]}..."
        )


def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.log_json)

    st.set_page_config(layout="wide", page_title="Autonomous AI Researcher")
    _init_session_state()

    # Global spacing/typography tweaks for a tidier layout.
    st.markdown(
        """
        <style>
            .block-container { padding-top: 2.5rem; padding-bottom: 2rem; }
            section[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
            h1, h2, h3 { margin-top: 0.25rem !important; margin-bottom: 0.75rem !important; }
            div[data-testid="stHeader"] { margin-bottom: 0.5rem; }
            div[data-testid="column"] { padding: 0 0.75rem; }
            div[data-testid="stVerticalBlock"] > div { margin-bottom: 0.5rem; }
            .stButton > button { margin-top: 0.5rem; margin-bottom: 0.5rem; }
            .stDownloadButton > button { margin-top: 0.5rem; margin-bottom: 0.5rem; }
            div[data-testid="stAlert"] { margin: 0.5rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Autonomous AI Researcher 🔬🤖")
    st.write("")  # vertical breathing room beneath the title

    col1, col2, col3 = st.columns([1, 2, 2], gap="large")
    with col1:
        st.header("Control Panel")
        question = st.text_area(
            "Research Question",
            "Analyze the impact of different activation functions on Transformer convergence speed.",
            height=140,
        )
        if st.button("Run Research", type="primary"):
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
        st.header("Related Past Research")
        if st.button("Load Knowledge Graph"):
            try:
                from memory.knowledge_graph import KnowledgeGraph
                kg = KnowledgeGraph()
                related = kg.query_related(question, k=3)
                if not related:
                    st.info("No prior related research found.")
                else:
                    for item in related:
                        st.markdown(
                            f"**Run [{item.get('run_id')}]**\n\n"
                            f"*Summary*: {item.get('summary','')[:100]}...\n\n"
                            f"*Sim*: {item.get('similarity', 0):.2f}"
                        )
            except Exception as e:
                st.error(f"Knowledge graph unavailable: {e}")

    with col2:
        st.header("Live Agent Activity")
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

    with col3:
        st.header("Report")
        result = st.session_state.result
        if result:
            st.success(f"Cost Estimate: ${result['usage']['cost_estimate']:.3f}")
            md_path = result.get("report_md")
            pdf_path = result.get("report_pdf_path")
            if md_path and os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    md_content = f.read()
                st.download_button("Download Markdown", md_content, "report.md", "text/markdown")
                with st.expander("Preview Markdown", expanded=True):
                    st.markdown(md_content)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button("Download PDF", pdf_bytes, "report.pdf", "application/pdf")


if __name__ == "__main__":
    main()
