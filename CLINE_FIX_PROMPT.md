# Cline Fix Prompt — Autonomous AI Researcher
## Model: claude-opus-4-7

Paste the text below as-is into Cline. It is a self-contained brief with every bug, its root cause, and the exact fix required.

---

## PROMPT (paste into Cline)

You are fixing a Python multi-agent research application. The stack is: **Streamlit frontend (ui/app.py)** → **FastAPI backend (api/server.py)** → **agent pipeline (agents/, core/, memory/, tools/)**. The user reports the frontend is broken. Below is an exhaustive list of every confirmed bug across the project, grouped by file. Fix all of them.

---

### BUG 1 — `requirements.txt`: Malformed `nest-asyncio` pin (CRITICAL — blocks install)

**File:** `requirements.txt`  
**Problem:** The last line reads `nest-asyncio===` — triple equals sign with no version. This causes `pip install -r requirements.txt` to fail entirely, so nothing can be installed.  
**Fix:** Replace `nest-asyncio===` with `nest-asyncio>=1.6.0`

---

### BUG 2 — `memory/knowledge_graph.py`: `save()` crashes with numpy serialization error (CRITICAL)

**File:** `memory/knowledge_graph.py` — `save()` method and `add_paper()` method  
**Problem:** Node attributes include `embedding` which is a `numpy.ndarray`. When `nx.node_link_data(self.graph)` is called and then passed to `json.dump()`, it raises `TypeError: Object of type ndarray is not JSON serializable`. This means the knowledge graph can never persist after the first paper is added — the entire research run crashes.  
**Fix:** In the `save()` method, before calling `nx.node_link_data`, convert all `embedding` attributes to Python lists. Also do the reverse (convert lists back to `np.array`) when loading in `__init__`. Concretely:

In `__init__` after loading from JSON:
```python
for node_id, data in self.graph.nodes(data=True):
    if "embedding" in data and isinstance(data["embedding"], list):
        self.graph.nodes[node_id]["embedding"] = np.array(data["embedding"])
```

In `save()`, before `json.dump`:
```python
import copy
data = nx.node_link_data(self.graph)
for node in data["nodes"]:
    if "embedding" in node and isinstance(node["embedding"], np.ndarray):
        node["embedding"] = node["embedding"].tolist()
with open(self.graph_path, "w") as f:
    json.dump(data, f)
```

Also add `import numpy as np` at the top of the file if not already there (it is imported inside functions; move it to the top level).

---

### BUG 3 — `memory/knowledge_graph.py`: Race condition creating the asyncio Lock (CRITICAL)

**File:** `memory/knowledge_graph.py` — `add_paper()` method  
**Problem:** `_lock` is a class-level variable (`None`). Inside `add_paper`, the check `if self._lock is None: self._lock = asyncio.Lock()` has a race condition — two coroutines running concurrently (via `asyncio.gather` in `agent_loop.py`) can both observe `None` and both create a new `Lock`, discarding each other's, so the lock never actually protects the critical section.  
**Fix:** Create the lock eagerly in `__init__` as an instance variable, not a class variable:

```python
def __init__(self):
    self._lock = asyncio.Lock()
    # ... rest of init
```

Remove the class-level `_lock: Optional[asyncio.Lock] = None` annotation and remove the `if self._lock is None:` check inside `add_paper`.

---

### BUG 4 — `tools/code_executor.py`: Docker unavailability crashes at import time (CRITICAL)

**File:** `tools/code_executor.py` — `PythonExecutor.__init__`  
**File:** `core/tool_registry.py` — `_init_default_tools`  
**Problem:** `PythonExecutor.__init__` calls `docker.from_env()` and immediately raises `RuntimeError` if Docker is not running. `ToolRegistry._init_default_tools()` creates `PythonExecutor()` at singleton init time, which means importing `core.tool_registry` will crash the entire process if Docker is unavailable. This kills Streamlit on startup too.  
**Fix:** Make Docker initialization lazy and graceful. Change `PythonExecutor.__init__` to catch the exception and store `self.client = None` with a warning. In `execute()`, check `if self.client is None` and return a structured error dict instead of raising:

```python
def __init__(self):
    try:
        self.client = docker.from_env()
        self.client.ping()
    except Exception as e:
        import warnings
        warnings.warn(f"[PythonExecutor] Docker unavailable: {e}. Code execution will return errors.")
        self.client = None

def execute(self, code: str, timeout: int = 120, work_dir=None):
    if self.client is None:
        return {
            "stdout": "",
            "stderr": "Docker is unavailable. Cannot execute code.",
            "exit_code": -1,
            "runtime": 0.0,
            "artifacts": []
        }
    # ... rest of existing execute() logic
```

---

### BUG 5 — `ui/app.py`: WebSocket loop blocks Streamlit render — UI freezes (CRITICAL)

**File:** `ui/app.py`  
**Problem:** The `asyncio.get_event_loop().run_until_complete(stream_ws())` call runs a blocking async loop inside Streamlit's synchronous render cycle. This means:
1. The UI completely freezes until the entire research run finishes.
2. Intermediate `st.info(...)` and `st.markdown(...)` calls inside `stream_ws()` do NOT update the browser — they run inside a non-rendering context.
3. `st.rerun()` inside an async function called via `run_until_complete` will raise a `StopException` that bubbles out incorrectly.

**Fix:** Refactor the streaming to use a background thread with a `queue.Queue` for thread-safe communication, and use `st.empty()` containers updated via a polling `while` loop with `time.sleep()` and `st.rerun()`. Here is the corrected pattern:

```python
import threading
import queue
import time

# Replace the stream_ws async block with:
if getattr(st.session_state, "running", False) and "run_id" in st.session_state:
    run_id = st.session_state.run_id
    
    if "event_queue" not in st.session_state:
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
    
    # Drain the queue and update state
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
                del st.session_state["event_queue"]
            elif data["type"] == "error":
                st.error(f"Stream error: {data.get('error')}")
                st.session_state.running = False
                del st.session_state["event_queue"]
    except queue.Empty:
        pass
    
    # Render current state
    with feed_container.container():
        for t in st.session_state.tasks[-10:]:
            st.info(f"**[{t.get('status','?').upper()}]** {t.get('kind','?')}: {str(t.get('input',''))[:100]}...")
    
    if st.session_state.get("buffers"):
        with token_container.container():
            for agent, text in st.session_state.buffers.items():
                st.markdown(f"**{agent} (streaming...)**\n\n{text} ▌")
    
    if getattr(st.session_state, "running", False):
        time.sleep(0.5)
        st.rerun()
```

Also remove the top-level `import nest_asyncio` and `nest_asyncio.apply()` — they are no longer needed and can cause event loop conflicts.

---

### BUG 6 — `ui/app.py`: `agent_card` imported but never used

**File:** `ui/app.py`  
**Problem:** `from ui.components import agent_card` is imported at the top but `agent_card()` is never called anywhere in the file. This is dead import that adds confusion.  
**Fix:** Remove the import line entirely.

---

### BUG 7 — `ui/app.py`: Missing `.env` loading

**File:** `ui/app.py`  
**Problem:** The Streamlit app never calls `load_dotenv()`, so environment variables defined in `.env` (API keys, `LLM_PROVIDER`, `RUNS_DIR`, etc.) are not loaded when running locally with `streamlit run ui/app.py`. The `LLMClient` will raise `EnvironmentError` because `OPENAI_API_KEY` is not set.  
**Fix:** Add near the top of `ui/app.py`, before other imports that trigger LLM usage:

```python
from dotenv import load_dotenv
load_dotenv()
```

---

### BUG 8 — `api/server.py` vs `api/api_server.py`: Duplicate server files

**File:** `api/api_server.py`  
**Problem:** There are two nearly identical FastAPI server files — `api/server.py` and `api/api_server.py`. The `Dockerfile` references `api.server:app`. The `api_server.py` is a leftover duplicate that will cause confusion and divergence. The only difference is that `api_server.py` hardcodes `RUNS_DIR` default to `/app/runs` while `server.py` uses `./runs`.  
**Fix:** 
1. Delete `api/api_server.py` entirely.
2. In `api/server.py`, update the `get_report` endpoint's `RUNS_DIR` default to `/app/runs` (matching the Docker environment set in `docker-compose.yml`), while keeping the `TaskManager` in `core/task_manager.py` using `./runs` as a local fallback. This is already correct — just confirm `server.py` is the single source of truth.

---

### BUG 9 — `core/tool_registry.py`: `ToolDefinition` uses Pydantic for a `Callable` field

**File:** `core/tool_registry.py`  
**Problem:** `ToolDefinition` is a Pydantic `BaseModel` with a `callable: Callable` field. In Pydantic v2, this works for validation but the field name `callable` shadows Python's built-in `callable()` function within the class scope. More critically, if Pydantic ever tries to serialize a `ToolDefinition` (e.g., for logging), it will fail because functions are not JSON-serializable.  
**Fix:** Replace `ToolDefinition` with a plain Python dataclass:

```python
from dataclasses import dataclass

@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict
    fn: Callable  # renamed from 'callable' to avoid shadowing builtin
```

Update all usages of `tool_def.callable` → `tool_def.fn` in `ToolRegistry.execute()` and `_init_default_tools()`. Also update instantiation calls: replace `callable=...` → `fn=...`.

---

### BUG 10 — `core/agent_loop.py`: `kg.query_related` called before any papers are added (minor, UX)

**File:** `core/agent_loop.py`  
**Problem:** `related_nodes = kg.query_related(research_question, k=3)` is called right after the plan is generated, before any papers have been added to the graph. On a fresh run the graph is empty so this always returns `[]`, yet it still calls `embed()` which is a network call (OpenAI) or model load (sentence-transformers). No crash, but it wastes time and tokens on every run.  
**Fix:** Wrap with an early-exit guard:

```python
related_nodes = kg.query_related(research_question, k=3) if len(self.graph.nodes) > 0 else []
```

Wait — `kg` is a `KnowledgeGraph` instance, not `self`. Fix:
```python
related_nodes = kg.query_related(research_question, k=3) if kg.graph.number_of_nodes() > 0 else []
```

---

### BUG 11 — `memory/knowledge_graph.py`: Missing `import numpy as np` at module level

**File:** `memory/knowledge_graph.py`  
**Problem:** `numpy` is imported inside the `add_paper()` and `query_related()` function bodies via `import numpy as np`. This works but is non-standard and means the `save()` fix from BUG 2 (which also needs `np`) won't have access to `np` at the top-level `save()` scope without an inline import.  
**Fix:** Move `import numpy as np` to the top of the file alongside other module-level imports.

---

### BUG 12 — `requirements.txt`: Package versions too old to support current Anthropic/OpenAI APIs

**File:** `requirements.txt`  
**Problem:** `anthropic==0.21.3` is many major versions behind (current is 0.40+). The newer `Messages` API response shape, streaming events (`content_block_delta`), and model names like `claude-opus-4-7` require a much newer SDK. Similarly `openai==1.14.0` may not support all current features.  
**Fix:** Update to current stable versions:
```
anthropic>=0.40.0
openai>=1.30.0
```
Also add the latest model to `LLMClient.pricing` in `core/llm_client.py`:
```python
"claude-opus-4-7": [0.015, 0.075],
"claude-opus-4-6": [0.015, 0.075],
"claude-sonnet-4-6": [0.003, 0.015],
```

---

### VERIFICATION STEPS

After all fixes are applied, verify by running:

```bash
# 1. Confirm pip install works
pip install -r requirements.txt --dry-run

# 2. Confirm imports don't crash (Docker may be absent)
python -c "from core.tool_registry import ToolRegistry; r = ToolRegistry(); print('ToolRegistry OK')"

# 3. Confirm KG save/load round-trip works
python -c "
import numpy as np, asyncio
from memory.knowledge_graph import KnowledgeGraph
kg = KnowledgeGraph()
asyncio.run(kg.add_paper('Test', 'http://x.com', 'summary text here', 'run-test-001'))
kg2 = KnowledgeGraph()
print('KG round-trip OK, nodes:', kg2.graph.number_of_nodes())
"

# 4. Confirm Streamlit UI starts without crashing
streamlit run ui/app.py --server.headless true &
sleep 5 && curl -s http://localhost:8501 | grep -q "Autonomous" && echo "Streamlit OK"
```

Fix all issues. Do not introduce new dependencies beyond those already in `requirements.txt`. Preserve all existing functionality.
