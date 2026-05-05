# Your Manual Task Checklist
### Tasks Gemini cannot do — work through these in order

These are the steps only you can perform because they require your accounts, credentials, local machine, and real running services. Complete them in the order listed.

---

## SECTION A — Get Your API Keys

These go into a `.env` file at the root of the project. Gemini will not touch this file.

**Task 1 — OpenAI API Key (REQUIRED)**
1. Go to https://platform.openai.com/api-keys
2. Click "Create new secret key" — name it "AI Researcher".
3. Copy the key immediately (it is shown only once).
4. Add a minimum balance of $5 at https://platform.openai.com/settings/billing (the system uses GPT-4o by default; $5 covers many test runs).
5. Save the key — you will paste it in Section C.

**Task 2 — Anthropic API Key (OPTIONAL — enables provider switching)**
1. Go to https://console.anthropic.com/keys
2. Click "Create Key".
3. Copy the key.
4. Save it for Section C.

**Task 3 — Tavily API Key (OPTIONAL — better web search quality)**
1. Go to https://app.tavily.com
2. Create a free account and copy your API key from the dashboard.
3. Save it for Section C.

**Task 4 — Pinecone API Key (OPTIONAL — only needed if you want cloud vector DB)**
1. Go to https://app.pinecone.io
2. Create a free Starter project.
3. Create an index named `research-context`, dimension `1536`, metric `cosine`.
4. Copy your API key from the dashboard.
5. Save it for Section C. (If you skip this, ChromaDB is used locally — perfectly fine.)

---

## SECTION B — Set Up Your Local Machine

**Task 5 — Install Python 3.11**
- macOS (recommended method):
  ```bash
  brew install pyenv
  pyenv install 3.11.9
  pyenv global 3.11.9
  python --version   # should show Python 3.11.9
  ```
- Windows: Download the installer from https://www.python.org/downloads/release/python-3119/ and check "Add Python to PATH".
- Linux: `sudo apt install python3.11 python3.11-venv`

**Task 6 — Install Docker Desktop**
The code executor runs Python experiments inside a Docker container for safety. Docker must be running whenever you use the app.
1. Download Docker Desktop from https://www.docker.com/products/docker-desktop
2. Install and launch it.
3. Confirm it works:
   ```bash
   docker run hello-world
   ```
   You should see "Hello from Docker!".

**Task 7 — Install WeasyPrint system dependencies (for PDF generation)**
- macOS:
  ```bash
  brew install pango cairo
  ```
- Ubuntu/Debian:
  ```bash
  sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
  ```
- Windows: WeasyPrint on Windows requires GTK. Follow the guide at https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows

---

## SECTION C — Configure Environment Variables

This is where you wire your API keys into the project.

**Task 8 — Create your `.env` file**
After Gemini finishes its work, open a terminal in the project root folder and run:
```bash
cp .env.example .env
```
Then open `.env` in any text editor and fill in the values:

```env
# REQUIRED — paste your OpenAI key here
OPENAI_API_KEY=sk-...your-key-here...

# OPTIONAL — paste Anthropic key if you got one in Task 2
ANTHROPIC_API_KEY=sk-ant-...your-key-here...

# Which LLM provider to use: "openai" or "anthropic"
LLM_PROVIDER=openai

# Which model to use
LLM_MODEL=gpt-4o

# OPTIONAL — paste Tavily key if you got one in Task 3
TAVILY_API_KEY=tvly-...your-key-here...

# OPTIONAL — Pinecone (leave blank to use local ChromaDB)
PINECONE_API_KEY=
PINECONE_INDEX=research-context

# Vector database backend: "chroma" (local) or "pinecone" (cloud)
VECTOR_BACKEND=chroma

# Max agent reasoning steps per run
MAX_STEPS=12

# Where run outputs are stored (leave as ./runs for local dev)
RUNS_DIR=./runs

# Optional API key to protect the backend (leave blank for local dev)
INTERNAL_API_KEY=
```

**Important:** Never commit `.env` to Git. It is already in `.gitignore`.

---

## SECTION D — Install Dependencies and Verify the Build

**Task 9 — Create a virtual environment and install packages**
Run these commands from the project root folder:
```bash
python -m venv .venv
source .venv/bin/activate       # macOS/Linux
# OR
.venv\Scripts\activate          # Windows

pip install -r requirements.txt
pip install -e .
```

**Task 10 — Run the test suite**
```bash
pytest -q
```
All tests should pass. If you see an error about a missing module, run `pip install <module-name>` and retry.

**Task 11 — Pull the Docker sandbox image**
The code executor downloads `python:3.11-slim` on first use, which can be slow. Pre-pull it now:
```bash
docker pull python:3.11-slim
```

---

## SECTION E — Run the App Locally

**Task 12 — Start the backend API server**
Open Terminal window #1:
```bash
source .venv/bin/activate
uvicorn api.server:app --host 0.0.0.0 --port 8000 --reload
```
You should see: `Uvicorn running on http://0.0.0.0:8000`

**Task 13 — Start the Streamlit frontend**
Open Terminal window #2:
```bash
source .venv/bin/activate
streamlit run ui/app.py
```
Your browser should open automatically at http://localhost:8501.

**Task 14 — Run a test research question end-to-end**
In the browser UI:
1. Paste this question into the text area: `Analyze the impact of different activation functions on Transformer convergence speed.`
2. Click "Run Research".
3. Watch the Live Agent Activity feed in the center column populate with task updates.
4. Wait for the report to appear in the right column (typically 3–8 minutes depending on your OpenAI plan).
5. Click "Download Markdown" and "Download PDF" — open both and spot-check them.

**Task 15 — Test a second question to confirm generalization**
Try: `Compare LoRA vs full fine-tuning on small language models.`

---

## SECTION F — Build and Run with Docker

**Task 16 — Build and launch the full Docker stack**
```bash
docker compose up --build
```
Wait for the healthcheck to pass (about 60 seconds on first build). Then visit http://localhost:8501.

**Task 17 — Confirm Docker-in-Docker works**
Submit a research question via the UI while running in Docker. The code executor needs access to the Docker socket (already wired in `docker-compose.yml` via `/var/run/docker.sock`). If the Coder step fails with a Docker error, confirm that Docker Desktop is running and that the socket path is correct for your OS.

---

## SECTION G — Harden the Project Before Sharing

**Task 18 — Remove stale files Git shouldn't track**
```bash
git rm --cached .DS_Store 2>/dev/null || true
find . -name ".DS_Store" -exec git rm --cached {} \; 2>/dev/null || true
```

**Task 19 — Set a spending cap on your API dashboard**
Before any public demo, go to https://platform.openai.com/settings/billing and set a monthly spending limit (e.g., $20). This prevents surprise charges if the app is left running.

**Task 20 — Add a `.python-version` file**
```bash
echo "3.11" > .python-version
```

**Task 21 — (Optional) Deploy a public demo**
If you want others to try the app without running it locally:
1. Go to https://share.streamlit.io
2. Connect your GitHub repo.
3. Set `ui/app.py` as the main file.
4. Add all your API keys as Secrets in the Streamlit Cloud dashboard (Settings → Secrets) — do NOT put them in the repo.
5. Note: the Docker sandbox executor will not work on Streamlit Cloud. Before deploying publicly, add a fallback in `tools/code_executor.py` that runs the Python script in a local subprocess instead of Docker when `DOCKER_AVAILABLE=false` env var is set.

**Task 22 — Set up GitHub Actions CI (strongly recommended)**
Create the file `.github/workflows/ci.yml` with this content:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pytest -q
        env:
          OPENAI_API_KEY: sk-fake-key-for-tests
          RUNS_DIR: ./runs
```
Push this file to GitHub. The CI will run `pytest` automatically on every push.

---

## SECTION H — Final Checklist Before Submission / Demo

- [ ] `.env` file is filled in with real API keys
- [ ] Docker Desktop is running
- [ ] `pytest -q` passes
- [ ] `uvicorn api.server:app --port 8000` starts cleanly
- [ ] `streamlit run ui/app.py` opens in browser
- [ ] One full research run completes and produces a downloadable PDF
- [ ] `docker compose up --build` boots and is accessible at http://localhost:8501
- [ ] `.env` is NOT committed to Git (check with `git status`)
- [ ] Spending cap is set on your OpenAI dashboard
- [ ] README has a screenshot or GIF of the running UI
