# Things You Still Need To Do

I fixed the code and configuration issues that can be handled without your private credentials. This checklist is for the remaining actions that require **your accounts, API keys, local machine setup, or deployment choices**.

## 1. Add API keys later — do not commit them

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and add your OpenRouter key:
   ```env
   LLM_PROVIDER=openrouter
   LLM_MODEL=openai/gpt-4o-mini
   OPENROUTER_API_KEY=<your real OpenRouter API key>
   ```
   Optional alternate providers:
   ```env
   LLM_PROVIDER=openai
   OPENAI_API_KEY=<your real OpenAI API key>
   ```
   or:
   ```env
   LLM_PROVIDER=anthropic
   ANTHROPIC_API_KEY=<your real Anthropic API key>
   ```
3. Optional keys:
   - `TAVILY_API_KEY` — better web search quality; otherwise DuckDuckGo fallback is used.
   - `PINECONE_API_KEY` + `VECTOR_BACKEND=pinecone` — cloud vector DB; otherwise local ChromaDB is used.
   - `INTERNAL_API_KEY` — protects REST and WebSocket API endpoints with an `X-API-Key` header; use a random value of at least 16 characters.
4. Confirm `.env` is not tracked:
   ```bash
   git status --short
   ```
   `.env` should not appear because it is ignored.

## 2. Install local dependencies

Python:
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Node/static landing page tooling:
```bash
npm install
npm run build
```

## 3. Install and start required local services

1. Install and run Docker Desktop.
2. Verify Docker works:
   ```bash
   docker run hello-world
   ```
3. Optional but recommended for local API run tracking: start Redis, or let the app fall back to the in-memory run manager if Redis is unavailable.
4. For PDF generation on macOS, install WeasyPrint system libraries if PDFs fail:
   ```bash
   brew install pango cairo
   ```

## 4. Verify before using real API credits

Run tests first:
```bash
RUNS_DIR="$(mktemp -d)" python3.12 -m pytest -q
```

Expected result after these fixes:
```text
30 passed, 1 skipped
```

Then smoke-test imports:
```bash
python3.12 -m compileall -q agents api core memory tools ui config.py
python3.12 - <<'PY'
import importlib
for mod in ['config', 'core.llm_client', 'memory.knowledge_graph', 'api.server', 'ui.app']:
    importlib.import_module(mod)
    print(f'import ok: {mod}')
PY
```

## 5. Run the app locally

Terminal 1 — backend:
```bash
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2 — Streamlit UI:
```bash
source .venv/bin/activate
streamlit run ui/app.py
```

Open http://localhost:8501 and submit a small test question first, for example:
```text
Compare LoRA vs full fine-tuning on small language models.
```

## 6. Docker Compose run

After `.env` is filled in and Docker Desktop is running:
```bash
docker compose up --build
```

Open http://localhost:8501.

## 7. Cost and safety tasks

- Set a spending limit in your provider dashboard before long demos.
- Keep Docker Desktop running when using the Coder sandbox.
- Never paste real API keys into source files, README files, screenshots, or commits.
- Review generated reports before sharing; LLM output can contain mistakes.

## 8. Optional project polish

- Add a screenshot or GIF to `README.md` after you successfully run the UI.
- Add a `LICENSE` file if you plan to publish the repository.
- Add GitHub Actions CI once the repo is ready to push.
- Record a short demo video showing one complete research run.
