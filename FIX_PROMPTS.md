# Fix Prompts for Claude Code / Cline

Copy and paste each prompt individually into Claude Code or Cline. They are ordered by priority — start with CRITICAL.

---

## 🚨 CRITICAL — Exposed API Key

**Paste this first, before anything else.**

```
URGENT SECURITY FIX: There is a real OpenAI API key committed to the file `.env.bak`.

1. Immediately delete the file `.env.bak` from the project directory. Do not keep it, rename it, or move it — delete it entirely.

2. Add the following lines to `.gitignore` so secrets can never be accidentally committed again:
   ```
   .env
   .env.bak
   .env.local
   .env.*.local
   *.bak
   ```

3. Check whether `.env.bak` or any file containing `sk-proj-` or `OPENAI_API_KEY=sk-` was ever committed to git history. Run:
   ```
   git log --all --full-history -- .env.bak
   git grep -i "sk-proj-" $(git rev-list --all)
   ```
   If it appears in git history, the key is permanently compromised and must be revoked at https://platform.openai.com/api-keys — even after deletion from the working tree.

4. Confirm `.gitignore` exists and covers `.env*` before moving on to anything else.
```

---

## 🔴 SECURITY FIX 1 — SSRF Protection in `tools/paper_parser.py`

```
Fix the SSRF (Server-Side Request Forgery) vulnerability and download safety issues in `tools/paper_parser.py`.

Current problems:
- The URL allowlist check (`url_or_path.startswith("https://arxiv.org/pdf/")`) can be bypassed with URLs like `https://arxiv.org/pdf/../../` or `https://arxiv.org/pdf/@evil.com/x`
- The content-type and size checks happen AFTER the entire file is loaded into memory with `requests.get()` — a 500MB response will be fully buffered before the size check fires
- `requests.get()` is a synchronous blocking call that will freeze the asyncio event loop

Apply all three fixes:

1. Harden the URL validation using `urllib.parse.urlparse` to check the scheme is exactly `https` and the hostname is exactly `arxiv.org`, in addition to checking the path starts with `/pdf/`. Reject anything else before making a network request.

2. Replace `requests.get()` with a streaming download using `httpx` (which is already in requirements). Use `httpx.stream("GET", url, timeout=30, follow_redirects=False)` and check the `Content-Type` response header BEFORE reading the body. Stream the content in chunks, accumulating bytes up to the 50 MB limit and raising `ValueError` the moment the limit is exceeded — never load the full body into memory first.

3. Since `parse_pdf` is called from async agent code, convert it to `async def parse_pdf(...)` using `httpx.AsyncClient` for the HTTP download. Keep the rest of the function synchronous (pypdf is CPU-bound) and wrap only the HTTP part in async.

Show the complete rewritten `tools/paper_parser.py` with all three changes applied.
```

---

## 🔴 SECURITY FIX 2 — Code Executor Artifact Leakage (`tools/code_executor.py`)

```
Fix a bug in `tools/code_executor.py` where the Docker sandbox has the host `tmpdir` mounted as **read-only** (`"mode": "ro"`), but the code tries to collect output artifacts from that same directory after the container finishes.

The problem: because the volume is read-only, the user script cannot write any output files to `/code/` inside the container, so the `artifacts` list returned by `execute()` will always be empty (the only file present is `experiment.py` which is explicitly excluded). Any charts, CSVs, or data files produced by the research scripts are silently lost.

Fix this by adding a **second volume mount** for outputs:
1. Create a separate `output_dir = Path(tmpdir) / "output"` and `output_dir.mkdir()`.
2. Mount it into the container as `{str(output_dir): {"bind": "/output", "mode": "rw"}}` alongside the existing read-only `/code` mount.
3. Update the container command to: `"pip install numpy pandas matplotlib scipy --quiet && python /code/experiment.py"` — the user script will naturally write to `/output` if instructed to do so. Also inject the environment variable `OUTPUT_DIR=/output` via the `environment` parameter so scripts know where to write files.
4. Change the `artifacts` collection at the end to scan `output_dir` instead of `tmpdir`: `[str(p) for p in output_dir.iterdir() if p.is_file()]`.

Show the complete rewritten `tools/code_executor.py`.
```

---

## 🔴 BUG FIX 1 — Agent Loop Bypasses Centralized Settings (`core/agent_loop.py`)

```
Fix `core/agent_loop.py` which reads configuration directly from environment variables instead of using the centralized `Settings` object in `config.py`.

Problems to fix:

1. Line `MAX_REROUTES = int(os.getenv("MAX_REROUTES", "2"))` at module level — replace with `from config import get_settings` and read `get_settings().max_reroutes` at call time instead of module import time.

2. Line `max_steps = int(os.getenv("MAX_STEPS", "12"))` inside `run_agent_async` — replace with `get_settings().max_steps`.

3. **Missing timeout enforcement**: The settings have a `run_timeout_seconds` field (default 600s) but it is never enforced anywhere in `run_agent_async`. Wrap the entire agent execution body in `asyncio.wait_for(..., timeout=settings.run_timeout_seconds)` and catch `asyncio.TimeoutError`, raising a descriptive `RuntimeError(f"Research run {run_id} exceeded timeout of {settings.run_timeout_seconds}s")`.

4. Remove the now-unused `import os` if `os` is no longer referenced after the above changes (check first).

Make only these targeted changes. Do not refactor anything else.
```

---

## 🔴 BUG FIX 2 — Deprecated Event Loop in UI (`ui/app.py`)

```
Fix the deprecated asyncio event loop usage in `ui/app.py`.

Problem: The line `asyncio.get_event_loop().run_until_complete(...)` inside the `with col2:` block is deprecated since Python 3.10 and will raise a `DeprecationWarning` or `RuntimeError` in Python 3.12+. In Streamlit specifically, there is already a running event loop (managed by `nest_asyncio`), so this pattern is fragile.

Fix:
1. Since `nest_asyncio.apply()` is already called at the top of the file, replace `asyncio.get_event_loop().run_until_complete(coro)` with `asyncio.get_event_loop().run_until_complete(coro)` → use `asyncio.run(coro)` wrapped in a try/except that falls back to the nest_asyncio path, OR simply use the already-established pattern:
   ```python
   loop = asyncio.new_event_loop()
   try:
       loop.run_until_complete(_stream_research_events(...))
   finally:
       loop.close()
   ```
   This is the safest pattern because it creates a fresh loop that is unambiguously not the Streamlit event loop.

2. Also fix: `import os` is at the top but `os.path.exists(...)` is used — that's fine, keep it. However `import sys` is also present but only used for `sys.path.append` which should be removed in favour of proper package installation (the project has a `pyproject.toml`). Remove the `sys.path.append` hack and the `import sys` line.

Show the complete rewritten `ui/app.py`.
```

---

## 🟠 BUG FIX 3 — Thread-Unsafe Model Cache in `memory/embeddings.py`

```
Fix two issues in `memory/embeddings.py`:

1. **Thread-unsafe model caching**: The `SentenceTransformer` model is cached by attaching it as an attribute of the function object: `embed._model = SentenceTransformer(...)`. This is not thread-safe — if two threads call `embed()` simultaneously before the model is loaded, both will try to initialise it, causing either a race condition or double initialization. Replace with a module-level `_model: Optional[SentenceTransformer] = None` variable and a threading lock:
   ```python
   import threading
   _model = None
   _model_lock = threading.Lock()

   def _get_model():
       global _model
       if _model is None:
           with _model_lock:
               if _model is None:
                   from sentence_transformers import SentenceTransformer
                   _model = SentenceTransformer("all-MiniLM-L6-v2")
       return _model
   ```
   Then call `_get_model().encode(texts)` instead of `embed._model.encode(texts)`.

2. **Silent failures via print()**: Replace both `print(f"OpenAI embedding error: {e}")` and `print(f"SentenceTransformer error: {e}")` with proper structured logging:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   # then use:
   logger.warning("OpenAI embedding error: %s", e)
   logger.warning("SentenceTransformer error, falling back to zeros: %s", e)
   ```

Show the complete rewritten `memory/embeddings.py`.
```

---

## 🟠 BUG FIX 4 — KnowledgeGraph asyncio.Lock Lifecycle (`memory/knowledge_graph.py`)

```
Fix the `asyncio.Lock` lifecycle bug in `memory/knowledge_graph.py`.

Problem: `KnowledgeGraph._lock` is a class-level variable initialized to `None` and lazily created by `_get_lock()`. However, an `asyncio.Lock` is bound to the event loop that was running when it was created. If `_get_lock()` is called across different event loops (e.g., in tests, or after an event loop restart), the lock silently belongs to the wrong loop, leading to `RuntimeError: Task got Future attached to a different loop`.

Fix: Remove the class-level `_lock` and `_get_lock()` classmethod entirely. Instead, create the lock as an **instance variable** in `__init__`:
```python
self._lock = asyncio.Lock()
```
Instance-level locks are created fresh each time a `KnowledgeGraph` is instantiated, which happens inside `run_agent_async` — always within the correct running event loop. This is the correct pattern for asyncio objects.

Also: In `save()`, the file write is synchronous and called inside `async with lock:` via `await asyncio.to_thread(self.save)`. This is already correct in `add_paper`. But the bare `self.save()` call path (if ever called directly) would block. Add a docstring note: `# Always call via asyncio.to_thread(self.save) from async contexts.`

Make only these targeted changes to `memory/knowledge_graph.py`.
```

---

## 🟠 BUG FIX 5 — Replace All `os.getenv()` with Centralized Settings

```
The project has a centralized `config.py` with a validated `Settings` class, but many modules bypass it by calling `os.getenv()` directly. This means changes to defaults in `config.py` have no effect on these modules and values are never validated.

Fix all of the following files to use `from config import get_settings` instead of `os.getenv()`:

**`memory/vector_store.py`**:
- `os.getenv("VECTOR_BACKEND", "chroma")` → `get_settings().vector_backend`
- `os.getenv("RUNS_DIR", "./runs")` → `get_settings().runs_dir`
- `os.getenv("PINECONE_API_KEY")` → `get_settings().pinecone_api_key`
- `os.getenv("PINECONE_INDEX", "research-context")` → `get_settings().pinecone_index`

**`memory/knowledge_graph.py`**:
- `os.getenv("RUNS_DIR", "./runs")` → `get_settings().runs_dir`

**`memory/embeddings.py`**:
- `os.getenv("OPENAI_API_KEY")` → `get_settings().openai_api_key`

**`core/task_manager.py`**:
- `os.getenv("RUNS_DIR", "./runs")` → `get_settings().runs_dir`

**`core/report_generator.py`**:
- `os.getenv("RUNS_DIR", "./runs")` → `get_settings().runs_dir`

**`core/llm_client.py`**:
- `os.getenv("LLM_PROVIDER", "openai")` → `get_settings().llm_provider`
- `os.getenv("LLM_MODEL", "gpt-4o")` → `get_settings().llm_model`
- `os.getenv("OPENAI_API_KEY", "")` and `os.getenv("ANTHROPIC_API_KEY", "")` → `get_settings().active_llm_api_key` (the `Settings` class already has this property)

For each file, add `from config import get_settings` at the top (after existing imports) and call `get_settings()` once at the top of the relevant function or `__init__` method. Do not call `get_settings()` at module import time (it caches fine, but lazy access is cleaner for tests).

Apply all changes. Show each modified file in full.
```

---

## 🟠 BUG FIX 6 — Fix `LLM_MODEL` Value in `.env.example`

```
The model identifier `gpt-5.5` used in the project's `.env.bak` / example env file does not exist in OpenAI's API. Requests using this model will fail immediately with a 404 from the OpenAI API.

1. Open `.env.example` (if it exists) and change `LLM_MODEL=gpt-5.5` to `LLM_MODEL=gpt-4o`. The `gpt-4o` model is stable, well-supported, and matches what the pricing table in `core/llm_client.py` expects.

2. In `core/llm_client.py`, the `pricing` dict has entries for `claude-opus-4-7` which does not exist (the real model is `claude-opus-4` or `claude-opus-4-6`). Remove `claude-opus-4-7` from the pricing dict to avoid confusion. Keep `claude-opus-4-6` and `claude-sonnet-4-6`.

3. Add a startup validation so a bad model name fails loudly rather than silently at the first API call. In `config.py`, add a validator on the `llm_model` field that logs a warning if the model string doesn't appear in a known-good list, but does not hard-fail (to allow new models):
   ```python
   _KNOWN_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5-20251001"}

   @field_validator("llm_model")
   @classmethod
   def _warn_unknown_model(cls, v: str) -> str:
       if v not in _KNOWN_MODELS:
           import warnings
           warnings.warn(f"LLM_MODEL='{v}' is not in the known-good model list. Double-check spelling.", stacklevel=2)
       return v
   ```
```

---

## 🟡 IMPROVEMENT 1 — Replace `print()` with `logging` in Tools

```
Replace all bare `print()` error/warning calls in the tools layer with proper structured logging. Using `print()` bypasses the application's log level controls, log formatters, and log routing.

Fix the following files:

**`tools/web_search.py`**:
- Add `import logging` and `logger = logging.getLogger(__name__)` near the top.
- Replace `print(f"Tavily search error: {e}")` with `logger.warning("Tavily search failed, falling back to DuckDuckGo: %s", e)`
- Replace `print(f"DDG search error: {e}")` with `logger.warning("DuckDuckGo search failed, returning empty results: %s", e)`

**`tools/arxiv_search.py`**:
- Add `import logging` and `logger = logging.getLogger(__name__)`.
- Replace `print(f"Error searching arxiv: {e}")` with `logger.error("arXiv search failed for query %r: %s", query, e)`

Show the complete rewritten versions of both files.
```

---

## 🟡 IMPROVEMENT 2 — Add `.gitignore` and Secret Scanning

```
The project is missing a comprehensive `.gitignore`. Create or update `.gitignore` in the project root to include:

```
# Python
__pycache__/
*.py[cod]
*.pyo
*.pyd
.Python
*.egg-info/
dist/
build/
*.egg
.venv/
venv/
env/

# Environment / Secrets — NEVER commit these
.env
.env.*
*.env
*.bak
.env.local
.env.development
.env.production
*.pem
*.key

# Runtime artefacts
runs/
/runs/
*.sqlite3
*.bin

# IDE
.DS_Store
.idea/
.vscode/
*.swp

# Test cache
.pytest_cache/
htmlcov/
.coverage
```

Also add a pre-commit check by creating `.github/workflows/secret-scan.yml`:
```yaml
name: Secret Scan
on: [push, pull_request]
jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Scan for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
```

This will block future accidental key commits in CI.
```

---

## 🟡 IMPROVEMENT 3 — Add Input Validation to API Endpoints (`api/server.py`)

```
The `ResearchRequest` model in `api/server.py` validates `min_length=1` on the question but has no upper bound. A user could submit a 10 MB string and cause excessive LLM token usage or memory pressure.

Add the following improvements to `api/server.py`:

1. Add `max_length=2000` to the `question` field in `ResearchRequest`:
   ```python
   class ResearchRequest(BaseModel):
       question: str = Field(..., min_length=10, max_length=2000, description="The research question to investigate.")
   ```
   Change `min_length` from 1 to 10 to catch accidental empty-ish submissions.

2. Add a `@app.exception_handler(Exception)` global handler that logs unexpected errors and returns a generic 500 JSON response instead of leaking stack traces to clients:
   ```python
   @app.exception_handler(Exception)
   async def _unhandled_exception_handler(request: Request, exc: Exception):
       logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
       return JSONResponse(status_code=500, content={"detail": "Internal server error"})
   ```

3. The `_verify_api_key` helper is defined but only called by manually adding `Depends(_verify_api_key)` to each endpoint that needs it. Audit every POST/DELETE endpoint and confirm they all include `dependencies=[Depends(_verify_api_key)]`. Any endpoint that modifies state (start run, cancel run, approve run) must require the API key when `INTERNAL_API_KEY` is set.

Show the changed sections of `api/server.py`.
```

---

## 🟡 IMPROVEMENT 4 — Add Comprehensive Tests for Critical Paths

```
The `tests/` directory has test files but coverage of critical failure paths is thin. Add the following test cases to the existing test files (or create new ones as appropriate):

1. **`tests/test_paper_parser.py`** (create if missing):
   - Test that a non-arxiv URL raises `ValueError` (SSRF block test)
   - Test that a URL passing the hostname check but returning a non-PDF content-type raises `ValueError`
   - Test that a PDF exceeding 50MB raises `ValueError` before consuming full memory (mock the httpx response with a streaming body that yields >50MB)

2. **`tests/test_code_executor.py`** (create if missing):
   - Test that `PythonExecutor.execute()` with a simple `print("hello")` script returns `exit_code=0` and `stdout` containing `"hello"` (requires Docker — skip with `pytest.mark.skipif(not shutil.which("docker"), reason="Docker not available")`)
   - Test that a script that writes a file to `/output/result.txt` results in that file appearing in `artifacts`

3. **`tests/test_config.py`** (create if missing):
   - Test that `Settings()` raises `ValidationError` when `max_steps` is set to 0 (below `ge=1`)
   - Test that `Settings(llm_provider="openai").validate_llm_ready()` raises `RuntimeError` when `openai_api_key` is None or starts with `"your_"`
   - Test that `allowed_origins_list` correctly parses a comma-separated string

4. **`tests/test_embeddings.py`** (create if missing):
   - Test that `embed("hello world")` returns a numpy array of shape `(384,)` when OpenAI key is absent (falls back to SentenceTransformer or zeros)
   - Test that calling `embed()` from multiple threads concurrently does not raise an exception (thread-safety test for the lock fix)

Use `unittest.mock.patch` to avoid real API calls in all tests. Each test file should have a module-level docstring explaining what it tests.
```

---

## 🟢 QUICK CLEANUP — Remove Dead Code and Fix Minor Issues

```
Apply the following small cleanups across the codebase:

1. **`core/agent_loop.py`**: The `base_agent` import (`from agents.base_agent import ...`) may be unused — check and remove if so. Also, the comment `# Max reroute attempts — configurable via env var` at the top of the file is now wrong after the settings fix; update or remove it.

2. **`core/report_generator.py`**: The `build()` method accepts `critique` as either a Pydantic model or a dict (it calls `critique.model_dump()` if the attribute exists, then uses `.get()` for dict access). This dual-type parameter is fragile. Add a type annotation `critique: Union[BaseModel, dict]` and add an explicit `isinstance` check with a clear comment explaining why both types are accepted.

3. **`tools/paper_parser.py`**: The fallback `pdfminer` import is inside an `if not text.strip():` branch deep in the function with no import at the top. If `pdfminer` is not installed this raises `ModuleNotFoundError` at runtime with no helpful message. Add a top-level try/import:
   ```python
   try:
       from pdfminer.high_level import extract_text as _pdfminer_extract
   except ImportError:
       _pdfminer_extract = None
   ```
   Then in the fallback branch: `if _pdfminer_extract is None: logger.warning("pdfminer not installed, skipping fallback extraction")` else call it.

4. **`memory/vector_store.py`**: The `query()` method returns an empty `[]` at the bottom if neither backend matched — but the constructor raises on unknown backends, so this line is unreachable. Replace with `raise RuntimeError(f"Unknown vector backend: {self.backend}")` so it's an explicit guard, not silent.

5. **`ui/app.py`**: Remove the `sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` hack — this is only needed for scripts run directly, not for a properly installed package. The project has a `pyproject.toml` with the package defined; users should run `pip install -e .` and then `streamlit run ui/app.py` without needing path manipulation.

Apply all five cleanups. Show each changed file in full.
```

---

*Generated by code analysis of the Autonomous AI Researcher project — May 2026.*
*Run these prompts in order. Each prompt is self-contained and safe to apply independently.*
