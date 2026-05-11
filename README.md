# Autonomous AI Researcher 🔬🤖

An autonomous multi-agent system that conducts end-to-end scientific research: it searches academic literature, synthesises findings, writes and executes Python experiments in a sandboxed Docker container, critiques its own results through an adversarial debate loop, and produces structured Markdown + PDF reports.

---

## Key Capabilities

- **Literature Synthesis** — parallel arXiv search and PDF parsing with semantic summarisation
- **Hypothesis-Driven Experimentation** — generates and self-corrects Python experiments
- **Secure Code Execution** — isolated Docker sandbox with CPU/memory limits
- **Adversarial Quality Control** — Critic and Debater agents score and challenge results
- **Long-Term Memory** — ChromaDB vector store + knowledge graph links findings across runs
- **Real-Time UI** — Streamlit dashboard with live agent feed, streaming tokens, and run history
- **Production-Grade API** — FastAPI backend with WebSocket streaming, rate limiting, and run cancellation

---

## Architecture

```
User ──► Streamlit UI ──► FastAPI (WebSocket) ──► Agent Loop
                                                      │
                              ┌───────────────────────┤
                              │                       │
                           Planner              [parallel]
                              │                  Researcher ×N
                           Coder ◄──────────────────┘
                              │
                           Critic ──► (low confidence?) ──► Coder retry
                              │
                           Debater
                              │
                           Critic (revised)
                              │
                        Report Generator ──► report.md / report.pdf
```

| Agent | Role |
|---|---|
| **Planner** | Decomposes the research question into a structured step plan |
| **Researcher** | Runs arXiv search + PDF parsing via a ReAct loop |
| **Coder** | Translates insights into executable Python experiments |
| **Critic** | Scores results (0–1 confidence) and identifies weaknesses |
| **Debater** | Challenges the Critic's conclusions to prevent confirmation bias |

---

## Quickstart

### 1. Prerequisites

- Python 3.10+
- Docker Desktop (required for the code sandbox)
- An OpenAI or Anthropic API key

### 2. Install

```bash
git clone <repo>
cd autonomous-ai-researcher
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic)
```

All configuration options are documented in `.env.example`.

### 4. Run

```bash
# Terminal 1 — API server
uvicorn api.server:app --port 8000 --reload

# Terminal 2 — Streamlit UI
streamlit run ui/app.py
```

Or use Docker Compose (single command):

```bash
docker-compose up --build
```

Open **http://localhost:8501** in your browser.

---

## Configuration Reference

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4o` | Model string for the chosen provider |
| `OPENAI_API_KEY` | — | Required when `LLM_PROVIDER=openai` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=anthropic` |
| `TAVILY_API_KEY` | — | Optional. Better web search. Falls back to DuckDuckGo |
| `VECTOR_BACKEND` | `chroma` | `chroma` (local) or `pinecone` (cloud) |
| `MAX_STEPS` | `12` | Max agent steps per run |
| `RUN_TIMEOUT_SECONDS` | `600` | Hard timeout per run |
| `RUNS_DIR` | `./runs` | Where run artefacts are stored |
| `INTERNAL_API_KEY` | — | Require `X-API-Key` header on all API endpoints |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max run starts per IP per minute |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_JSON` | `false` | Set `true` for structured JSON logs (Docker) |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns active run count |
| `POST` | `/api/research` | Start a research run. Body: `{"question": "…"}` |
| `GET` | `/api/runs` | List all tracked runs |
| `DELETE` | `/api/research/{run_id}` | Cancel a running run |
| `WS` | `/api/research/{run_id}/stream` | Stream task/token events |
| `GET` | `/api/research/{run_id}/report` | Fetch completed report as Markdown |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Development

```bash
# Run tests
pytest tests/ -v

# Run with live reload
uvicorn api.server:app --reload
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI GPT-4o / Anthropic Claude |
| Backend | FastAPI + uvicorn + WebSockets |
| Frontend | Streamlit |
| Memory | ChromaDB (local) / Pinecone (cloud) |
| Embeddings | OpenAI `text-embedding-3-small` / sentence-transformers |
| Code Sandbox | Docker (python:3.11-slim) |
| Knowledge Graph | NetworkX + cosine similarity |
| Config | Pydantic Settings |
| Testing | pytest + pytest-mock |
