# Autonomous AI Researcher

**An open-source research workspace for planning, running, critiquing, and exporting AI-assisted research briefs.**

![Project](https://img.shields.io/badge/v2.0-Open%20Source-6d5dfc)
![UI](https://img.shields.io/badge/UI-Static%20Site%20%2B%20Streamlit-0f9f8f)
![Agents](https://img.shields.io/badge/Agents-Planner%20%7C%20Researcher%20%7C%20Coder%20%7C%20Critic%20%7C%20Debater-f6a623)

An autonomous multi-agent system that conducts end-to-end scientific research: it searches academic literature, synthesises findings, writes and executes Python experiments in a sandboxed Docker container, critiques its own results through an adversarial debate loop, and produces structured Markdown + PDF reports.

---

## How To Use This Project

You can use Autonomous AI Researcher in three ways:

1. **Try the public website** — use the static GitHub Pages interface for a short research brief.
2. **Run the full researcher locally** — run the Streamlit + FastAPI app on your machine with your own API key.
3. **Fork and deploy your own demo** — host the static site on GitHub Pages and deploy your own Vercel chat endpoint.

The public website is meant as a lightweight demo. The full local app is the complete multi-agent workflow with arXiv search, memory, Docker-based code execution, critique, debate, and Markdown/PDF reports.

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

## Try The Public Website

Open the hosted site:

```text
https://research.autonomous-ai.io
```

Enter a research question and click **Run prompt**. The public prompt form calls a separately hosted HTTPS backend and does not expose `OPENAI_API_KEY` in browser code.

For your own fork, do not rely on this repository owner's backend endpoint. Deploy your own endpoint by following [Deploy Your Own Public Demo](#deploy-your-own-public-demo).

---

## Run The Full App Locally

### 1. Prerequisites

- Python 3.10+
- Docker Desktop (required for the code sandbox)
- An OpenAI or Anthropic API key
- Optional: Redis for persistent multi-worker run state. Without Redis, the API falls back to in-memory local tracking.

### 2. Install

```bash
git clone https://github.com/zhaobangz/Autonomous-AI-Researcher.git
cd Autonomous-AI-Researcher
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

OpenAI model selection is controlled by configuration, not by the API key itself:

- Full local app: set `LLM_MODEL`, for example `gpt-4o`, `gpt-4o-mini`, or another model your OpenAI account can access.
- Public Vercel chat endpoint: set `OPENAI_MODEL`, for example `gpt-4o-mini` for lower-cost demos.

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

### 5. Generate Reports Without The UI

```bash
# Single question
python scripts/run_research.py "Your research question here"

# Batch from file
python scripts/batch_research.py questions.txt

# GitHub Actions
# Push to main or manually trigger the "Scheduled Research" workflow.
# Set RESEARCH_QUESTION and OPENAI_API_KEY (or ANTHROPIC_API_KEY)
# as repository secrets.
```

---

## Deploy Your Own Public Demo

GitHub Pages can host the frontend, but it cannot run server code or safely store `OPENAI_API_KEY`. To make your fork's prompt form live, deploy the included lightweight Vercel backend and point the frontend at it.

### 1. Deploy the Vercel backend

```bash
cd vercel-chat-api
npx vercel link
npx vercel env add OPENAI_API_KEY production
npx vercel env add OPENAI_MODEL production
npx vercel env add SITE_RATE_LIMIT_PER_MINUTE production
npx vercel env add PUBLIC_SITE_ORIGIN production
npx vercel deploy --prod
```

Recommended values:

```text
OPENAI_MODEL=gpt-4o-mini
SITE_RATE_LIMIT_PER_MINUTE=6
PUBLIC_SITE_ORIGIN=https://your-github-pages-domain.example
```

Set a conservative `SITE_RATE_LIMIT_PER_MINUTE` because public visitors can submit prompts that consume your OpenAI credits.

### 2. Connect the frontend

Update `assets/js/config.js`:

```js
window.AIR_SITE_CONFIG = {
    chatEndpoint: "https://your-vercel-project.vercel.app/api/chat",
};
```

Then verify the static site locally:

```bash
npm run test:site
npm run build
python3 -m http.server 3000 --directory _site
```

Open **http://localhost:3000** and submit a prompt.

### 3. Publish with GitHub Pages

Push your changes to `main`. The included GitHub Pages workflow builds `_site/` and publishes the static frontend. After the workflow finishes, open your Pages URL and submit a test prompt.

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
| `INTERNAL_API_KEY` | — | Require a non-placeholder `X-API-Key` of at least 16 chars on REST and WebSocket API routes |
| `OPENAI_MODEL` | `gpt-4o-mini` | Model for the lightweight public Vercel chat endpoint |
| `PUBLIC_SITE_ORIGIN` | — | Comma-separated frontend origins allowed to call the public prompt endpoint |
| `RATE_LIMIT_PER_MINUTE` | `10` | Max run starts per IP per minute |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `LOG_JSON` | `false` | Set `true` for structured JSON logs (Docker) |

---

## API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/research` | Start a research run. Body: `{"question": "…"}` |
| `GET` | `/api/runs` | List all tracked runs |
| `DELETE` | `/api/research/{run_id}` | Cancel a running run |
| `WS` | `/api/research/{run_id}/stream` | Stream task/token events; requires `X-API-Key` when `INTERNAL_API_KEY` is set |
| `GET` | `/api/research/{run_id}/report` | Fetch completed report as Markdown |
| `GET` | `/docs` | Interactive Swagger UI |

---

## Development

```bash
# Run tests
python -m pytest -q

# Validate the static website
npm run test:site

# Test the configured live Vercel chat endpoint
npm run test:live-chat

# Run the API with live reload
uvicorn api.server:app --reload
```

## Public GitHub Pages Site

The static public website is deployed with GitHub Pages from the generated `_site/` artifact.

```bash
npm run build
python3 -m http.server 3000 --directory _site
```

Open **http://localhost:3000** to preview it locally.

GitHub Pages cannot run server code or store `OPENAI_API_KEY`, so live prompt responses require a separately hosted HTTPS backend. Set that endpoint in `assets/js/config.js`.

To add a demo video later, place a file such as `assets/media/demo.mp4` in the repo and set:

```js
window.AIR_SITE_CONFIG = {
    demoVideoSrc: "assets/media/demo.mp4",
    demoPosterSrc: "assets/media/demo-poster.jpg",
};
```

For hosted video platforms, set `demoEmbedUrl` in `assets/js/config.js` instead.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM | OpenAI model from `LLM_MODEL` / Anthropic Claude |
| Backend | FastAPI + uvicorn + WebSockets |
| Frontend | Streamlit |
| Memory | ChromaDB (local) / Pinecone (cloud) |
| Embeddings | OpenAI `text-embedding-3-small` / sentence-transformers |
| Code Sandbox | Docker (python:3.11-slim) |
| Knowledge Graph | NetworkX + cosine similarity |
| Config | Pydantic Settings |
| Testing | pytest + pytest-mock |

---

## Limitations

- The Docker sandbox runs generated code without network access, as a non-root user, with resource limits and reduced container privileges. It is still **not** a complete security boundary for arbitrary hostile code, especially when Docker socket access is enabled.
- Each research run consumes real API credits. With GPT-4o, typical runs may cost approximately **$0.10–$0.50** depending on question complexity and retries.
- LLM outputs may contain factual errors or unsupported claims. Always review generated reports before citing or sharing them.
- arXiv search is limited to papers available in the arXiv corpus and does not provide paywall access.
- Complex multi-step questions can run long and may hit `RUN_TIMEOUT_SECONDS` (default: `600` seconds).

---

## Troubleshooting

- **Docker daemon unavailable** — If you see `docker: Cannot connect to the Docker daemon`, start Docker Desktop and retry the run.
- **WeasyPrint errors on macOS** — Install the required system libraries with `brew install pango cairo`.
- **OpenAI 401 errors** — Check your `.env` file, confirm `OPENAI_API_KEY` is valid, and ensure there is no extra whitespace.
- **Public prompt fails before submitting** — Confirm the Vercel endpoint responds to `OPTIONS` preflight and includes `Access-Control-Allow-Origin` for your Pages/custom domain.
- **Public prompt returns "Origin not allowed"** — Add your GitHub Pages/custom domain origin to `PUBLIC_SITE_ORIGIN` in Vercel and redeploy. Use origins only, for example `https://zhaobangz.github.io`, with no path.
- **Custom domain does not resolve** — Keep `CNAME` in the repo, then add a DNS `CNAME` record at your domain provider from `research` to `zhaobangz.github.io`.
- **Redis connection refused** — `RunManager` falls back to in-memory tracking automatically. For persistent run state, start Redis with `docker run -p 6379:6379 redis`.
- **Python version mismatch** — Use Python 3.11 via pyenv: `pyenv install 3.11 && pyenv local 3.11`.
