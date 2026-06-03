# User Checklist

Use this checklist before running, demoing, or publishing Autonomous AI Researcher.

## 1. Credentials

- Create or reuse an OpenRouter, OpenAI, or Anthropic account.
- Copy `.env.example` to `.env`.
- Set `LLM_PROVIDER`, `LLM_MODEL`, and the matching provider key.
- Optional: set `TAVILY_API_KEY` for better web search.
- Optional: set `PINECONE_API_KEY`, `PINECONE_INDEX`, and `VECTOR_BACKEND=pinecone` for cloud vector storage.
- Optional: set `INTERNAL_API_KEY` to protect local API routes with `X-API-Key`.
- Confirm `.env` is ignored and not staged.

## 2. Local Install

- Install Python 3.11.
- Create and activate a virtual environment.
- Run `pip install -r requirements.txt`.
- Run `pip install -e .`.
- Install Docker Desktop and confirm `docker run hello-world` works.
- Optional: run `npm install` for static-site tooling.
- Optional on macOS: install WeasyPrint native libraries with `brew install pango cairo` if PDF generation fails.

## 3. Validation

- Run `RUNS_DIR="$(mktemp -d)" python -m pytest -q`.
- Run `npm run test:site`.
- Run `npm run build`.
- Run `cd vercel-chat-api && npm run check`.
- Start the API with `uvicorn api.server:app --port 8000 --reload`.
- Start the UI with `streamlit run ui/app.py`.
- Open `http://localhost:8501` and submit a small test question.
- Confirm the report tab exposes Markdown and PDF downloads after completion.

## 4. Public Demo

- Deploy the static site with GitHub Pages or Vercel root static hosting.
- Deploy the lightweight chat endpoint from `vercel-chat-api/`, or intentionally include the root `api/chat.js` wrapper in a root Vercel deployment.
- Set `PUBLIC_SITE_ORIGIN` to explicit origins only.
- Set a conservative `SITE_RATE_LIMIT_PER_MINUTE`.
- Update `assets/js/config.js` with the hosted `/api/chat` endpoint.
- Run `npm run test:live-chat`.
- Submit a prompt from the deployed site and confirm there are no CORS errors.

## 5. Scheduled Research

- Add GitHub secrets for the provider you use: `LLM_PROVIDER`, `LLM_MODEL`, and the matching API key.
- Optional: add `RESEARCH_QUESTION`.
- Trigger `.github/workflows/scheduled_research.yml` manually or wait for its daily cron.
- Check the workflow summary and uploaded `scheduled-research-runs` artifact.

## 6. Safety And Cost

- Set a provider spending cap before demos or scheduled runs.
- Keep real API keys out of screenshots, browser code, Markdown files, and commits.
- Review generated reports before sharing them.
- Treat the Docker executor as risk reduction, not a perfect sandbox for hostile code.
- Delete or archive old `runs/` artifacts before publishing if they contain private prompts or outputs.
