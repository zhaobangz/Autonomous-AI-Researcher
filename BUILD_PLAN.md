# Technical Build Plan — Autonomous AI Researcher

This document is the engineering blueprint for taking the current scaffold to a fully working, user-installable product that satisfies every capability promised in `README.md` and every component described in `ARCHITECTURE.md`.

---

## 1. Current State Audit

| Area | File | Status | Issue |
| :--- | :--- | :--- | :--- |
| Docs | `README.md` | Complete | Promises features that don't exist yet. |
| Docs | `ARCHITECTURE.md` | Complete | Mermaid flow references modules that are stubs. |
| Core | `core/llm_client.py` | Partial | OpenAI only; `structured_output` is a mock; no retries/timeouts; no token tracking. |
| Core | `core/base_agent.py` | Functional | Works but has no memory hook, no tool-use protocol. |
| Core | `core/agent_loop.py` | **Broken stub** | No imports; references undefined `planner`, `arxiv_search`, `execute_code`, `generate_report`; defines `agent_loop` but `ui/app.py` imports `run_agent`. |
| Core | `core/task_manager.py` | **Empty** | Central state store from ARCHITECTURE is missing. |
| Agents | `agents/planner.py` | Functional | OK. |
| Agents | `agents/researcher.py` | Functional | Imports from misnamed folder `tools ` (trailing space) and misspelled file `arvix_search`. |
| Agents | `agents/coder.py` | Broken | Imports `tools .code_executor.PythonExecutor` which does not exist (file is empty). |
| Agents | `agents/critic.py` | Functional | OK, but does not produce a structured report artifact. |
| Tools | `tools /arvix_search.py` | Partial | Returns raw XML; no parsing; folder + filename typos. |
| Tools | `tools /web_search.py` | **Empty** | |
| Tools | `tools /paper_parser.py` | **Empty** | |
| Tools | `tools /code_executor.py` | **Empty** | Coder agent imports from here. |
| Memory | `memory/vector_store.py` | **Empty** | README + ARCHITECTURE both promise this. |
| Memory | `memory/embeddings.py` | **Empty** | |
| UI | `ui/app.py` | Broken | Calls `run_agent` which doesn't exist; no streaming view, no agent activity panel, no report download. |
| Infra | `requirements.txt` | **Empty** | Nothing installable. |
| Infra | `Dockerfile` | **Empty** | |
| Infra | `__init__.py` files | Missing everywhere | Python package imports will fail. |
| Infra | `.env.example` | Missing | README references `.env` but no template. |
| Infra | `tests/` | Missing | No verification harness. |

### Critical bugs that must be fixed first
1. Folder name `tools ` has a trailing space — rename to `tools` and update every import.
2. File `arvix_search.py` is misspelled — rename to `arxiv_search.py` and update imports.
3. UI/agent_loop function name mismatch (`run_agent` vs `agent_loop`).

---

## 2. Target Architecture (matches `ARCHITECTURE.md`)

```
autonomous-ai-researcher/
├── core/
│   ├── __init__.py
│   ├── llm_client.py          # Multi-provider (OpenAI + Anthropic) w/ JSON mode, retries, token meter
│   ├── base_agent.py          # + tool-calling protocol, + memory hook
│   ├── task_manager.py        # State store: tasks, statuses, artifacts, transitions
│   ├── agent_loop.py          # Orchestrator exposing run_agent(question, callbacks)
│   └── report_generator.py    # Markdown + PDF report assembly
├── agents/
│   ├── __init__.py
│   ├── planner.py             # JSON plan with explicit step types
│   ├── researcher.py          # arXiv search + paper parsing + summarization
│   ├── coder.py               # Hypothesis → Python script → sandbox exec
│   └── critic.py              # Structured review w/ scoring rubric
├── tools/                     # NOTE: no trailing space
│   ├── __init__.py
│   ├── arxiv_search.py        # Parsed arXiv results (title, authors, abstract, pdf_url)
│   ├── paper_parser.py        # PDF → text via pypdf, with chunking
│   ├── web_search.py          # Tavily/DuckDuckGo fallback
│   └── code_executor.py       # PythonExecutor: subprocess, timeout, capture stdout/stderr/artifacts
├── memory/
│   ├── __init__.py
│   ├── embeddings.py          # OpenAI/sentence-transformers embedding interface
│   └── vector_store.py        # ChromaDB local-first, Pinecone optional
├── ui/
│   ├── app.py                 # Streamlit dashboard w/ live agent activity feed
│   └── components.py          # Reusable widgets (agent card, plan view, report viewer)
├── tests/
│   ├── test_planner.py
│   ├── test_researcher.py
│   ├── test_coder.py
│   ├── test_executor.py
│   └── test_agent_loop.py
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── ARCHITECTURE.md
```

---

## 3. Module-by-Module Specification

### 3.1 `core/llm_client.py`
- Support `openai`, `anthropic`, and (optional) `google-generativeai` providers selected via `LLM_PROVIDER` env var.
- `chat_completion(messages, temperature, max_tokens)` with exponential-backoff retry (3 attempts) on rate limits and transient 5xx.
- `structured_output(messages, schema: pydantic.BaseModel)` using OpenAI JSON-mode / Anthropic tool-use; validates against the pydantic schema and re-prompts once on failure.
- Token usage tracker exposed as `client.usage` (prompt_tokens, completion_tokens, cost_estimate).
- Streaming generator `stream_completion(...)` for the UI.

### 3.2 `core/base_agent.py`
- Add `memory: Optional[VectorStore]` constructor parameter.
- Add `tools: List[Callable]` registry and a `call_tool(name, **kwargs)` helper.
- Add `emit(event_type, payload)` to publish progress events on a queue the UI subscribes to.

### 3.3 `core/task_manager.py` (was empty)
- `Task` dataclass: `id`, `parent_id`, `kind` (plan|search|summarize|code|exec|review), `status` (pending|running|done|failed), `input`, `output`, `created_at`, `finished_at`.
- `TaskManager` class:
  - `add(task)`, `update(id, **fields)`, `get(id)`, `pending()`, `history()`.
  - In-memory store with optional JSON persistence to `./runs/<run_id>/tasks.json`.
  - Pub/sub: `subscribe(callback)` so the UI can listen.

### 3.4 `core/agent_loop.py` (rewrite)
- Public function: `run_agent(research_question: str, on_event: Callable = None) -> ReportBundle`.
- Execution order:
  1. `Planner.run(question)` → list of typed steps.
  2. For each step, dispatch to the right agent (Researcher / Coder / Critic) and store output via `TaskManager`.
  3. After every step, push results into `VectorStore` so subsequent agents can retrieve relevant prior context.
  4. After the plan completes (or max iterations reached), call `Critic.run(context)` to produce final critique.
  5. Call `report_generator.build(context, critique)`.
- Hard limits: `MAX_STEPS=12`, total wall-clock 30 min, exec sandbox 5 min per script.

### 3.5 `core/report_generator.py` (new)
- Builds a markdown report with sections: Question, Plan, Literature Synthesis, Hypotheses, Code & Results, Critic Review, Citations, Appendix (raw logs).
- Optional PDF rendering via `weasyprint` or `reportlab`.
- Saves to `./runs/<run_id>/report.md` and `report.pdf`.

### 3.6 `agents/planner.py` (extend)
- Force structured output via pydantic `Plan(steps: list[PlanStep])` where `PlanStep.kind ∈ {search, summarize, code, exec, review}` and includes a `rationale` and `expected_output`.
- Validate that the plan contains at least one search and one code step (per ARCHITECTURE).

### 3.7 `agents/researcher.py` (extend)
- Use the new `tools.arxiv_search.search_arxiv()` which returns parsed dicts (not raw XML).
- For each top result, call `tools.paper_parser.parse_pdf(pdf_url)` to extract abstract + key sections, then summarize via LLM.
- Persist summaries to `VectorStore` with metadata `{paper_id, title, year}`.
- Fallback to `tools.web_search` when arXiv returns < 2 hits.

### 3.8 `agents/coder.py` (extend)
- Strip markdown fences robustly (already partially done).
- Inject a small preamble (`import sys, json, time`) so scripts can dump structured results to stdout.
- Pass the executor a temp working directory; capture artifacts (`.png`, `.csv`, `.json`) and reference them in the result dict.
- Auto-retry once on `ImportError` by appending the missing package install hint into the next prompt (do **not** auto-pip-install — surface to user).

### 3.9 `agents/critic.py` (extend)
- Output a structured `CriticReport` (pydantic): `strengths`, `weaknesses`, `bias_check`, `confidence_score (0-1)`, `recommendations`, `final_verdict`.
- Reject and re-route the loop back to Coder if `confidence_score < 0.4` (max one re-route to avoid infinite loop).

### 3.10 `tools/arxiv_search.py` (rewrite from `arvix_search.py`)
- Use the `arxiv` PyPI package (or parse XML with `feedparser`).
- Return `list[ArxivPaper]` with `id, title, authors, abstract, pdf_url, published`.
- Handle network errors and empty results gracefully.

### 3.11 `tools/paper_parser.py` (new)
- `parse_pdf(url_or_path) -> ParsedPaper(text, sections, metadata)` using `pypdf` (for digital PDFs) and falling back to `pdfminer.six` for messy PDFs.
- Chunk into ~1000-token windows for embedding.

### 3.12 `tools/web_search.py` (new)
- `web_search(query, k=5)` via Tavily (`TAVILY_API_KEY`) if the key is set, else DuckDuckGo via `duckduckgo-search`.

### 3.13 `tools/code_executor.py` (new — Coder agent depends on this)
- `class PythonExecutor:`
  - `execute(code: str, timeout: int = 300, work_dir: Optional[Path] = None) -> ExecResult`
  - Runs in a subprocess with `resource.setrlimit` (Linux) for memory caps; on macOS use timeout-only.
  - Captures stdout, stderr, exit_code, runtime, list of files created in `work_dir`.
  - **Sandbox note**: Document loudly that this is *not* a security boundary — Docker should be used for untrusted goals.

### 3.14 `memory/embeddings.py` (new)
- `embed(text: str | list[str]) -> np.ndarray` switching between `openai` text-embedding-3-small and `sentence-transformers/all-MiniLM-L6-v2` (offline default).

### 3.15 `memory/vector_store.py` (new)
- ChromaDB persistent client at `./runs/<run_id>/chroma/`.
- API: `add(texts, metadatas, ids)`, `query(text, k=5) -> list[Hit]`.
- Optional Pinecone backend selected via `VECTOR_BACKEND=pinecone`.

### 3.16 `ui/app.py` (rewrite)
- Streamlit page with three columns:
  - **Left**: research question input, run button, run history sidebar.
  - **Center**: live agent activity log driven by `TaskManager.subscribe()` (uses `st.empty()` + polling).
  - **Right**: rendered report preview + download buttons (`.md`, `.pdf`).
- Show per-agent cards (Planner / Researcher / Coder / Critic) with current status, last output, token spend.
- Keep `run_agent` as the imported entry point (matches existing import).

### 3.17 `tests/`
- Mock the `LLMClient.chat_completion` so unit tests are deterministic.
- Smoke test: `test_agent_loop.py` runs the full loop on a tiny question with a mocked LLM and asserts a report is produced.

### 3.18 Infra
- `requirements.txt`: pinned versions for `openai`, `anthropic`, `streamlit`, `arxiv`, `pypdf`, `pdfminer.six`, `chromadb`, `sentence-transformers`, `pydantic>=2`, `python-dotenv`, `tenacity`, `rich`, `weasyprint`, `duckduckgo-search`, `tavily-python`, `feedparser`, `pytest`, `pytest-mock`.
- `Dockerfile`: `python:3.11-slim`, install system deps for weasyprint (`libpango`, `libcairo`), copy app, expose 8501, `CMD streamlit run ui/app.py`.
- `docker-compose.yml`: app service + (optional) Chroma persistent volume.
- `.env.example`: every key referenced by the app (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `LLM_PROVIDER`, `LLM_MODEL`, `TAVILY_API_KEY`, `PINECONE_API_KEY`, `VECTOR_BACKEND`, `MAX_STEPS`).
- `pyproject.toml`: package metadata so `pip install -e .` works.

---

## 4. Build Order (dependency-correct)

1. **Hygiene fixes**: rename `tools ` → `tools`, rename `arvix_search.py` → `arxiv_search.py`, add `__init__.py` to every package, fix `from tools .X` imports, fix UI `run_agent` symbol.
2. `requirements.txt` + `.env.example` + `pyproject.toml`.
3. `core/llm_client.py` upgrade.
4. `core/task_manager.py`.
5. `tools/` (`arxiv_search`, `paper_parser`, `web_search`, `code_executor`).
6. `memory/` (`embeddings`, `vector_store`).
7. `core/base_agent.py` extension (memory + tool registry + event emitter).
8. Agent upgrades (`planner`, `researcher`, `coder`, `critic`) using the new infra.
9. `core/report_generator.py`.
10. `core/agent_loop.py` rewrite exporting `run_agent`.
11. `ui/app.py` rewrite.
12. `tests/` and CI green.
13. `Dockerfile` + `docker-compose.yml`.

---

## 5. Definition of Done

- `pip install -r requirements.txt && streamlit run ui/app.py` starts the UI without errors on a clean machine.
- Submitting the example question from README ("Analyze the impact of different activation functions on Transformer convergence speed") produces:
  - A Planner JSON plan visible in the UI.
  - At least 3 arXiv papers fetched, parsed, and summarized.
  - A generated PyTorch script that runs to completion in the sandbox.
  - A Critic review with structured strengths/weaknesses.
  - A downloadable Markdown + PDF report.
- `pytest -q` passes with mocked LLM calls.
- `docker compose up` boots the app and exposes it on `http://localhost:8501`.
