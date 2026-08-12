# User Manual

This manual explains how to use Autonomous AI Researcher as a visitor, local user, or project operator.

Autonomous AI Researcher has two different user experiences:

- The public static website is a lightweight prompt demo. It sends a prompt to a hosted Vercel endpoint and returns a concise research brief. It does not run arXiv search, PDF parsing, Docker experiments, or the full agent loop.
- The local Streamlit and FastAPI app is the full researcher. It runs Planner, Researcher, Coder, Critic, and Debater agents; streams live run events; executes generated Python in Docker; and writes Markdown/PDF reports.

## 1. Use The Public Website

1. Open the hosted website:

   ```text
   https://zhaobangz.github.io/Autonomous-AI-Researcher/
   ```

2. Enter a research prompt of 10 to 2000 characters.
3. Click `Run prompt`.
4. Read the returned brief in the `Research Brief` panel.
5. Use `Copy` to copy the response or `Clear` to reset the form.

The public page uses `assets/js/config.js` to find the chat endpoint. If that endpoint is missing or unavailable, the page shows a configuration or service error instead of silently failing.

### Public Demo Limits

- The public endpoint returns a concise Markdown brief with `Summary`, `Research Plan`, `Critical Risks`, and `Next Step`.
- The public endpoint is rate limited.
- The public endpoint must not claim it ran live searches, downloaded papers, executed code, or performed experiments.
- Provider API keys stay on the server. Do not put keys in browser files.

## 2. Run The Full App Locally

Use the local app when you want the complete multi-agent research workflow.

### Prerequisites

- Python 3.11 recommended. The package declares Python 3.10+ support.
- Docker Desktop for the generated-code sandbox.
- Node.js 22 if you want to build or validate the static website.
- An LLM provider key:
  - OpenRouter: `OPENROUTER_API_KEY`
  - OpenAI: `OPENAI_API_KEY`
  - Anthropic: `ANTHROPIC_API_KEY`
- Optional: Redis for persistent multi-worker run state. Without Redis, the API uses in-memory local run tracking.

### Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For the static site tooling:

```bash
npm install
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` and set the provider values you want. OpenRouter is the default:

```env
LLM_PROVIDER=openrouter
LLM_MODEL=openai/gpt-4o-mini
OPENROUTER_API_KEY=your_real_key
```

Optional settings:

- `TAVILY_API_KEY` improves web search; otherwise DuckDuckGo is used as a fallback.
- `VECTOR_BACKEND=pinecone` and `PINECONE_API_KEY` use Pinecone instead of local ChromaDB.
- `INTERNAL_API_KEY` requires `X-API-Key` on protected REST and WebSocket API routes.
- `RUNS_DIR` changes where reports, task files, Chroma databases, and the global knowledge graph are written.

### Start The API And UI

Terminal 1:

```bash
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
source .venv/bin/activate
streamlit run ui/app.py
```

Open:

```text
http://localhost:8501
```

### Run With Docker Compose

```bash
docker compose up --build
```

Open:

```text
http://localhost:8501
```

Docker Compose starts Redis, the FastAPI backend on port `8000`, and the Streamlit UI on port `8501`. It also mounts `./runs` into the container and mounts the Docker socket so the Coder agent can start sandbox containers.

## 3. Run A Research Job

1. Open the Streamlit UI.
2. Enter a focused research question. Good questions name a method, dataset, tradeoff, or hypothesis.
3. Click `Run Research`.
4. Watch `Live Activity` for task cards and token streams.
5. Use `Cancel run` while a run is active if you need to stop it.
6. Open the `Report` tab when the run completes.
7. Download `report.md` or `report.pdf`.

Generated artifacts are written under:

```text
RUNS_DIR/<run_id>/
```

Common files include:

- `tasks.json`: persisted task state.
- `report.md`: generated Markdown report.
- `report.pdf`: generated PDF, or a small placeholder file if WeasyPrint cannot generate a PDF on the host.
- `chroma/`: local vector-store data when `VECTOR_BACKEND=chroma`.
- `global_graph.json`: cross-run knowledge graph stored directly under `RUNS_DIR`.

## 4. Use Prior Knowledge

The Streamlit `Load Knowledge Graph` button queries the local knowledge graph for records similar to the current question.

This only returns useful results after previous runs have added research summaries to the graph. Similarity scores are based on embeddings from OpenAI embeddings when `OPENAI_API_KEY` is configured, otherwise from the local `sentence-transformers` fallback.

## 5. Run Without The UI

Single question:

```bash
python scripts/run_research.py "Compare LoRA and full fine-tuning for small language models."
```

Custom output directory:

```bash
python scripts/run_research.py "Your question" --output-dir runs/manual
```

Batch file:

```bash
python scripts/batch_research.py questions.txt
```

The batch script ignores blank lines and lines starting with `#`, then writes `runs/auto/batch_summary.csv`.

## 6. API Reference

When `INTERNAL_API_KEY` is set, include this header on protected REST and WebSocket requests:

```text
X-API-Key: your_internal_api_key
```

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/api/research` | Start a run with `{"question": "..."}` |
| `GET` | `/api/runs` | List tracked runs |
| `GET` | `/api/research/{run_id}/status` | Check run status |
| `DELETE` | `/api/research/{run_id}` | Request run cancellation |
| `WS` | `/api/research/{run_id}/stream` | Stream task, token, done, error, and cancelled events |
| `GET` | `/api/research/{run_id}/report` | Fetch the generated Markdown report |
| `POST` | `/api/research/{run_id}/approve` | Publish an approval event for integrations |

## 7. Deploy A Public Demo

The static site can be deployed by GitHub Pages from the generated `_site/` artifact.

```bash
npm run build
```

The prompt form needs a separate HTTPS backend. The included lightweight backend lives in `vercel-chat-api/`; the root `api/chat.js` file is a compatibility wrapper around the same handler for Vercel deployments that intentionally include it.

Set `assets/js/config.js` to the deployed endpoint:

```js
window.AIR_SITE_CONFIG = {
    chatEndpoint: "https://your-vercel-project.vercel.app/api/chat",
    demoVideoSrc: "",
    demoPosterSrc: "",
    demoEmbedUrl: "",
};
```

Required hosted chat environment variables:

- `LLM_PROVIDER=openrouter` or `LLM_PROVIDER=openai`
- `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` for OpenRouter
- `OPENAI_API_KEY` and `OPENAI_MODEL` for OpenAI
- `PUBLIC_SITE_ORIGIN` with explicit origins only, such as `https://research.autonomous-ai.io`
- `SITE_RATE_LIMIT_PER_MINUTE`

## 8. Verify The Project

Python tests:

```bash
RUNS_DIR="$(mktemp -d)" python -m pytest -q
```

Static site validation:

```bash
npm run test:site
npm run build
```

Vercel chat syntax check:

```bash
cd vercel-chat-api
npm run check
```

Live hosted chat check from the repo root:

```bash
npm run test:live-chat
```

## 9. Safety And Cost

- Every full research run can consume provider credits.
- Set provider-side spending limits before demos or scheduled runs.
- The Docker sandbox disables network access, drops Linux capabilities, runs as a non-root user, uses memory/CPU limits, and caps generated code size. Treat it as risk reduction, not a perfect security boundary for hostile code.
- Generated reports can contain model mistakes. Review sources, code, and conclusions before sharing or citing them.
- Do not commit `.env`, provider keys, run artifacts that contain secrets, or private research data.
