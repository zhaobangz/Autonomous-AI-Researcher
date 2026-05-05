# ui/app.py
"""
Streamlit Web UI consuming WebSocket Events and the global Knowledge Graph.
"""
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import json
import asyncio
import websockets
import httpx

st.set_page_config(layout="wide", page_title="Autonomous AI Researcher")
st.title("Autonomous AI Researcher 🔬🤖")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns([1, 2, 2])

with col1:
    st.header("Control Panel")
    question = st.text_area("Research Question", "Analyze the impact of different activation functions on Transformer convergence speed.")
    
    if st.button("Run Research", type="primary"):
        st.session_state.running = True
        st.session_state.result = None
        st.session_state.tasks = []
        st.session_state.buffers = {}
        
        try:
            resp = httpx.post("http://localhost:8000/api/research", json={"question": question})
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
                for r in related:
                    st.markdown(f"**Run [{r.get('run_id')}]**\n\n*Summary*: {r.get('summary')[:100]}...\n\n*Sim*: {r.get('similarity', 0):.2f}")
        except Exception as e:
            st.error("Knowledge graph unavailable or empty.")

with col2:
    st.header("Live Agent Activity")
    feed_container = st.empty()
    token_container = st.empty()
    
    if getattr(st.session_state, "running", False) and "run_id" in st.session_state:
        run_id = st.session_state.run_id
        
        if "event_queue" not in st.session_state:
            import queue
            import threading
            import time
            st.session_state.event_queue = queue.Queue()
            
            def ws_thread():
                import asyncio, websockets, json
                async def _stream():
                    uri = f"ws://localhost:8000/api/research/{run_id}/stream"
                    try:
                        async with websockets.connect(uri) as ws:
                            while True:
                                msg = await ws.recv()
                                st.session_state.event_queue.put(json.loads(msg))
                                data = json.loads(msg)
                                if data["type"] in ("done", "error"):
                                    break
                    except Exception as e:
                        st.session_state.event_queue.put({"type": "error", "error": str(e)})
                asyncio.run(_stream())
            
            t = threading.Thread(target=ws_thread, daemon=True)
            t.start()
        
        import queue
        import time
        try:
            while True:
                data = st.session_state.event_queue.get_nowait()
                if data["type"] == "task_update":
                    st.session_state.tasks.append(data["task"])
                elif data["type"] == "token":
                    agent = data["agent"]
                    if "buffers" not in st.session_state:
                        st.session_state.buffers = {}
                    st.session_state.buffers.setdefault(agent, "")
                    st.session_state.buffers[agent] += data["delta"]
                elif data["type"] == "done":
                    st.session_state.result = data["result"]
                    st.session_state.running = False
                    if "event_queue" in st.session_state:
                        del st.session_state["event_queue"]
                elif data["type"] == "error":
                    st.error(f"Stream error: {data.get('error')}")
                    st.session_state.running = False
                    if "event_queue" in st.session_state:
                        del st.session_state["event_queue"]
        except queue.Empty:
            pass
        
        with feed_container.container():
            for t in st.session_state.tasks[-10:]:
                st.info(f"**[{t.get('status','?').upper()}]** {t.get('kind','?')}: {str(t.get('input',''))[:100]}...")
        
        if getattr(st.session_state, "buffers", None):
            with token_container.container():
                for agent, text in st.session_state.buffers.items():
                    st.markdown(f"**{agent} (streaming...)**\n\n{text} ▌")
        
        if getattr(st.session_state, "running", False):
            time.sleep(0.5)
            st.rerun()
    else:
        with feed_container.container():
            for t in st.session_state.tasks[-10:]:
                kind = t.get('kind', 'unknown')
                status = t.get('status', 'unknown')
                input_str = t.get('input', '')
                st.info(f"**[{status.upper()}]** {kind}: {str(input_str)[:100]}...")

with col3:
    st.header("Report")
    res = getattr(st.session_state, "result", None)
    if res:
        st.success(f"Cost Estimate: ${res['usage']['cost_estimate']:.3f}")
        
        md_path = res.get("report_md")
        pdf_path = res.get("report_pdf_path")
        
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
