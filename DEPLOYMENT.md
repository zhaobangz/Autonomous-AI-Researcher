# Deployment Guide — Vercel

This repository now includes a Vercel-ready public site for the **Autonomous AI Researcher** project.

The public deployment is intentionally lightweight:

- `index.html` serves the prompt interface.
- `api/chat.js` calls OpenAI from a server-side Vercel Function.
- `.vercelignore` excludes local Python agent code, run artifacts, virtual environments, and secrets from the Vercel bundle.

The full Streamlit/FastAPI/Docker research loop remains available for local or container deployment, but it is not the public Vercel surface.

## Required Vercel Environment Variables

Set these in **Vercel Project Settings -> Environment Variables**:

| Name | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | Server-side key used by `/api/chat`. Never expose this in browser code. |
| `OPENAI_MODEL` | No | Public prompt endpoint model. Defaults to `gpt-4o-mini`. |
| `SITE_ACCESS_TOKEN` | No | Optional access code to limit public use of paid API calls. |
| `SITE_RATE_LIMIT_PER_MINUTE` | No | Best-effort per-instance rate limit. Defaults to `6`. |
| `PUBLIC_SITE_ORIGIN` | No | Comma-separated allowed origins for custom domains. |

## Recommended Project Name

Use `autonomous-ai-researcher` as the Vercel project name. It matches the project mission directly and should produce a URL in this form when available:

```text
https://autonomous-ai-researcher.vercel.app
```

If Vercel reports that the generated domain is unavailable, use the exact URL printed by the deploy command rather than guessing.

## Deploy

```bash
npx vercel deploy --prod
```

During first-time setup:

- Link the directory to a new Vercel project.
- Use `autonomous-ai-researcher` for the project name.
- Keep the build command as `npm run build`.
- Set `OPENAI_API_KEY` before or immediately after deployment.

## Verify

After deployment:

1. Open the production URL printed by Vercel.
2. Submit a short research prompt.
3. Confirm the response appears and browser devtools do not show `OPENAI_API_KEY` in any client-side source or network payload.
