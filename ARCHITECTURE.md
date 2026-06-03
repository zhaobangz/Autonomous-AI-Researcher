# Architecture

Autonomous AI Researcher has two runtime paths:

- A full local research stack: Streamlit UI -> FastAPI API -> async multi-agent loop -> Markdown/PDF reports.
- A public static website: GitHub Pages static assets -> lightweight Vercel chat endpoint -> concise public research brief.

The public website is intentionally not the full research system. It does not run arXiv search, PDF parsing, Docker experiments, or report generation.

## Full Local Research Flow

```text
User
  -> Streamlit UI (ui/app.py)
  -> FastAPI API (api/server.py)
  -> RunManager (Redis if available, in-memory fallback)
  -> run_agent_async (core/agent_loop.py)
      -> Planner
      -> Researcher steps in parallel
      -> Coder for code/exec steps
      -> Critic after code execution
      -> Optional Coder reroute when confidence is low
      -> Final Critic
      -> Debater
      -> Revised Critic
      -> ReportGenerator
  -> runs/<run_id>/report.md and report.pdf
```

FastAPI publishes task and token events to the run manager. Streamlit consumes those events over `/api/research/{run_id}/stream` and updates the live activity feed.

## Agent Roles

| Agent | File | Current role |
|---|---|---|
| Planner | `agents/planner.py` | Produces a structured plan with at least one `search` and one `code` step. |
| Researcher | `agents/researcher.py` | Runs a ReAct loop over `search_arxiv`, `parse_pdf`, and `web_search`, then summarizes findings. |
| Coder | `agents/coder.py` | Generates a complete Python experiment and executes it through `run_python_code`. Retries once on missing imports. |
| Critic | `agents/critic.py` | Produces a structured review with strengths, weaknesses, bias check, confidence score, recommendations, and verdict. |
| Debater | `agents/debater.py` | Challenges the Critic's reasoning and surfaces unsupported conclusions or alternative explanations. |

## Orchestration Details

`core/agent_loop.py` is the main coordinator.

1. Create a per-run `TaskManager`, `VectorStore`, `ToolRegistry`, and `KnowledgeGraph`.
2. Ask Planner for a validated `Plan`.
3. Query prior knowledge from the global graph and add it to the run context.
4. Run all `search` and `summarize` plan steps concurrently through Researcher.
5. Execute non-search steps up to `MAX_STEPS`.
6. For `code` and `exec` steps, call Coder and inspect the sandbox exit code.
7. Retry once when code execution fails.
8. Ask Critic to review successful code results.
9. If Critic confidence is below `0.4`, reroute to Coder up to `MAX_REROUTES`.
10. Run final Critic, Debater, and revised Critic passes.
11. Build reports and return report paths, tasks, and token/cost usage.

The whole run is wrapped in `asyncio.wait_for` using `RUN_TIMEOUT_SECONDS`.

## Tool Registry

`core/tool_registry.py` registers these tools for each run:

| Tool | Implementation | Notes |
|---|---|---|
| `search_arxiv` | `tools/arxiv_search.py` | Searches arXiv and returns title, authors, abstract, PDF URL, and publication date. |
| `parse_pdf` | `tools/paper_parser.py` | Allows `https://arxiv.org/pdf/...` URLs, enforces PDF content type and a 50 MB limit, and blocks local paths for agent calls. |
| `web_search` | `tools/web_search.py` | Uses Tavily when `TAVILY_API_KEY` is set, otherwise falls back to DuckDuckGo. |
| `run_python_code` | `tools/code_executor.py` | Lazily builds/uses the Docker executor image and runs generated scripts. |

The tool registry is intentionally not a singleton. Each research run gets its own registry and lazy Docker executor.

## Code Sandbox

The Coder agent is instructed to use only the Python standard library plus `numpy`, `pandas`, `matplotlib`, and `scipy`. The executor image is defined in `executor.Dockerfile`.

`tools/code_executor.py` runs generated scripts with:

- Docker network disabled.
- Non-root user `1000:1000`.
- Read-only container filesystem with limited writable `/tmp`, `/home/sandbox`, and `/output`.
- 512 MB memory limit.
- Half CPU quota.
- Dropped Linux capabilities and `no-new-privileges`.
- PID and file-descriptor limits.
- Maximum generated code size of 200 KB.
- Maximum execution timeout of 120 seconds.

This reduces risk but is not a perfect security boundary for hostile code.

## Memory

| Component | File | Purpose |
|---|---|---|
| Vector store | `memory/vector_store.py` | Stores per-run context in ChromaDB by default, or Pinecone when configured. |
| Embeddings | `memory/embeddings.py` | Uses OpenAI `text-embedding-3-small` when `OPENAI_API_KEY` is available, otherwise `sentence-transformers/all-MiniLM-L6-v2`, then zeros as a last fallback. |
| Knowledge graph | `memory/knowledge_graph.py` | Stores cross-run paper/research summaries in `RUNS_DIR/global_graph.json` and links nodes by cosine similarity. |

## API Layer

`api/server.py` exposes:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check. |
| `POST` | `/api/research` | Start a run and return `run_id`. |
| `GET` | `/api/runs` | List tracked runs. |
| `GET` | `/api/research/{run_id}/status` | Check run status. |
| `DELETE` | `/api/research/{run_id}` | Request cancellation. |
| `WS` | `/api/research/{run_id}/stream` | Stream task, token, done, error, and cancelled events. |
| `GET` | `/api/research/{run_id}/report` | Fetch `report.md`. |
| `POST` | `/api/research/{run_id}/approve` | Publish an approval event for integrations. |

When `INTERNAL_API_KEY` is set, protected REST routes and the WebSocket stream require a matching `X-API-Key` header.

## User Interfaces

### Streamlit

`ui/app.py` is the full local control plane. It starts runs through the FastAPI API, streams WebSocket events, renders task cards and token buffers, supports cancellation, queries the local knowledge graph, and exposes report downloads.

`ui/components.py` contains reusable HTML snippets for agent and task cards.

### Static Website

The public site consists of `index.html`, `404.html`, `assets/css/styles.css`, `assets/js/app.js`, and `assets/js/config.js`.

`assets/js/app.js`:

- Reads `window.AIR_SITE_CONFIG.chatEndpoint`.
- Supports optional demo video settings from `demoVideoSrc`, `demoPosterSrc`, or `demoEmbedUrl`.
- Validates prompt length.
- Sends `POST { "prompt": "..." }` to the configured endpoint.
- Uses a 30 second browser timeout.
- Displays returned `output` and `model`.
- Handles copy, clear, status, and character-count UI behavior.

## Public Chat Endpoint

`vercel-chat-api/api/chat.js` is the lightweight hosted prompt endpoint. The root `api/chat.js` file re-exports the same handler for Vercel deployments that intentionally include it.

The handler:

- Accepts `POST` and `OPTIONS`.
- Requires `Content-Type: application/json`.
- Accepts `prompt` strings from 10 to 2000 characters.
- Enforces origin checks through `PUBLIC_SITE_ORIGIN`.
- Rate limits by IP using `SITE_RATE_LIMIT_PER_MINUTE`.
- Supports `LLM_PROVIDER=openrouter` and `LLM_PROVIDER=openai`.
- Returns JSON with `output`, `model`, and optional `usage`.
- Instructs the model not to claim live searches, paper downloads, code execution, or experiments.

## Reports

`core/report_generator.py` writes:

- `report.md`
- `report.pdf`

Report sections currently include:

1. Research Question
2. Research Plan
3. Literature Synthesis
4. Code & Results
5. Critic Review
6. Adversarial Debate, when Debater output exists

If WeasyPrint is unavailable or fails, the PDF path still exists but contains a short placeholder message telling the user to use the Markdown report or install native PDF dependencies.
