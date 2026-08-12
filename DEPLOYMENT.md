# Deployment Guide

This repository supports three deployment styles:

- GitHub Pages for the static public website.
- Vercel for the lightweight public chat endpoint.
- Local or Docker Compose for the full Streamlit/FastAPI multi-agent app.

GitHub Pages cannot run server code or store provider secrets. The public prompt form must call a separately hosted HTTPS API endpoint.

## Static Website On GitHub Pages

The public website is static:

- `index.html`
- `404.html`
- `assets/css/styles.css`
- `assets/js/config.js`
- `assets/js/app.js`
- `robots.txt`
- `sitemap.xml`

The build command creates `_site/`:

```bash
npm run build
```

The GitHub Pages workflow at `.github/workflows/pages.yml` builds `_site/` and publishes that artifact. It does not publish the full repository.

### GitHub Pages Setup

1. Go to repository `Settings -> Pages`.
2. Set `Build and deployment` source to `GitHub Actions`.
3. Push to `main` or manually run `Deploy GitHub Pages`.
4. Open the Pages URL after the workflow completes.

### Site URL

The site is served from the default project URL:

```text
https://zhaobangz.github.io/Autonomous-AI-Researcher/
```

`robots.txt` and `sitemap.xml` reference that URL.

### Custom Domain (optional)

The repository ships no `CNAME`. To add a custom domain, create the DNS record
first, then set the domain in `Settings -> Pages -> Custom domain`, which writes
`CNAME` for you. For a subdomain:

```text
research CNAME zhaobangz.github.io.
```

Only add the domain in Pages once DNS resolves. Publishing a `CNAME` for a domain
with no DNS record takes the site offline, because Pages redirects the project URL
to a host that cannot be reached. Update the URL in `robots.txt`, `sitemap.xml` and
the `href` in `404.html` at the same time, and add the new origin to
`PUBLIC_SITE_ORIGIN` on the Vercel chat API.

## Public Chat Backend On Vercel

The recommended public prompt backend is in:

```text
vercel-chat-api/
```

It accepts:

```json
{ "prompt": "Research question here" }
```

and returns:

```json
{
  "output": "Rendered answer text",
  "model": "openai/gpt-4o-mini",
  "usage": null
}
```

The endpoint is intentionally lightweight. It returns a concise brief and is instructed not to claim that it ran live searches, downloaded papers, executed code, or performed experiments.

### Deploy The Backend

```bash
cd vercel-chat-api
npx vercel link
npx vercel env add LLM_PROVIDER production
npx vercel env add OPENROUTER_API_KEY production
npx vercel env add OPENROUTER_MODEL production
npx vercel env add OPENROUTER_SITE_URL production
npx vercel env add OPENROUTER_APP_NAME production
npx vercel env add SITE_RATE_LIMIT_PER_MINUTE production
npx vercel env add PUBLIC_SITE_ORIGIN production
npx vercel deploy --prod
```

Recommended OpenRouter values:

```text
LLM_PROVIDER=openrouter
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_SITE_URL=https://research.autonomous-ai.io
OPENROUTER_APP_NAME=Autonomous AI Researcher
SITE_RATE_LIMIT_PER_MINUTE=6
PUBLIC_SITE_ORIGIN=https://research.autonomous-ai.io,https://zhaobangz.github.io
```

For OpenAI instead:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini
SITE_RATE_LIMIT_PER_MINUTE=6
PUBLIC_SITE_ORIGIN=https://your-static-site-origin.example
```

`PUBLIC_SITE_ORIGIN` must contain origins only: scheme, host, and optional port. Do not include paths such as `/Autonomous-AI-Researcher`.

### Connect The Frontend

Edit `assets/js/config.js`:

```js
window.AIR_SITE_CONFIG = {
    chatEndpoint: "https://your-vercel-project.vercel.app/api/chat",
    demoVideoSrc: "",
    demoPosterSrc: "",
    demoEmbedUrl: "",
};
```

Use `demoVideoSrc` for an MP4/WebM file, `demoPosterSrc` for its poster image, or `demoEmbedUrl` for a hosted video embed.

### Verify The Backend

From the repository root:

```bash
npm run test:live-chat
```

From the backend directory:

```bash
cd vercel-chat-api
npm run check
```

## Root Vercel Static Deployment

The repository root contains:

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "_site"
}
```

This lets Vercel host the static frontend from `_site/`.

The root `.vercelignore` excludes the Python app, tests, run artifacts, and most backend files. It intentionally keeps the minimal JavaScript chat handler files:

- `api/chat.js`
- `vercel-chat-api/api/chat.js`

This means a root Vercel deployment can include the same lightweight chat function if you intentionally configure the required environment variables. For the clearest separation, deploy the frontend from the root and deploy the chat API from `vercel-chat-api/`.

Never put `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, or any provider secret in `index.html`, `assets/js/config.js`, or any browser-served file.

## Local Preview

Build and preview the static website:

```bash
npm run build
python3 -m http.server 3000 --directory _site
```

Open:

```text
http://localhost:3000
```

Validate the static site:

```bash
npm run test:site
```

## Full Local App

For the full researcher, deploy or run the Python app, not the static website.

Local terminals:

```bash
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
streamlit run ui/app.py
```

Docker Compose:

```bash
docker compose up --build
```

The full app needs provider keys in `.env`, Docker access for generated-code execution, and optional Redis for run state.

## Post-Deployment Check

After deploying the static site and chat backend:

1. Open the public URL.
2. Confirm CSS and JavaScript load.
3. Submit a prompt of at least 10 characters.
4. Confirm the response panel shows returned text and the status pill shows a model name.
5. Confirm browser developer tools do not show CORS errors.
6. Confirm no provider secret appears in browser source or network responses.
7. If using a custom domain, confirm DNS resolves and GitHub Pages shows the domain as active.
