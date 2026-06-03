# Manual Operator Tasks

These tasks require your local machine, cloud accounts, provider keys, or deployment choices. They cannot be completed safely by committing code alone.

## 1. Keep Secrets Local

1. Copy `.env.example` to `.env`.
2. Set only the key for the provider selected by `LLM_PROVIDER`.
3. Use `OPENROUTER_API_KEY` for OpenRouter keys, not `OPENAI_API_KEY`.
4. Use a random value of at least 16 characters for `INTERNAL_API_KEY` if you expose the FastAPI app beyond local development.
5. Run `git status --short` and confirm `.env` is not listed.

## 2. Prepare Local Services

1. Install and start Docker Desktop.
2. Verify Docker with `docker run hello-world`.
3. Optional: start Redis locally, or let the app fall back to in-memory run tracking.
4. Optional on macOS: install PDF dependencies with `brew install pango cairo` if WeasyPrint cannot write PDFs.

## 3. Run The Full App

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

Start with a short question to keep cost and runtime low.

## 4. Run Verification Before Spending Credits

```bash
RUNS_DIR="$(mktemp -d)" python -m pytest -q
npm run test:site
npm run build
cd vercel-chat-api && npm run check
```

These checks do not require real LLM calls.

## 5. Deploy Your Public Prompt Demo

1. Deploy the static site from the repository root or with GitHub Pages.
2. Deploy the public chat endpoint from `vercel-chat-api/`.
3. Add production environment variables in Vercel:
   - `LLM_PROVIDER`
   - `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`, or `OPENAI_API_KEY` and `OPENAI_MODEL`
   - `PUBLIC_SITE_ORIGIN`
   - `SITE_RATE_LIMIT_PER_MINUTE`
4. Update `assets/js/config.js` with the deployed endpoint.
5. Run `npm run test:live-chat`.

## 6. Demo Checklist

Before a live demo:

- Confirm Docker Desktop is running.
- Confirm your provider account has a spending cap.
- Run one small local research question.
- Confirm `report.md` and `report.pdf` appear under `runs/<run_id>/`.
- Confirm the public website returns a concise brief but does not claim it used the full local tools.
- Clear or archive private run artifacts before screen sharing or publishing.
