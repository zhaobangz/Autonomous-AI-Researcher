# User Checklist — Before You Submit the Project

Tasks Gemini cannot do for you. Work through these in order.

## A. Accounts & API Keys
1. Create or reuse an OpenAI account, generate an API key, and add a small balance ($5 is plenty for testing). Save as `OPENAI_API_KEY`.
2. (Optional but recommended) Create an Anthropic account and generate `ANTHROPIC_API_KEY` so you can demo provider-switching.
3. (Optional) Create a free Tavily account for higher-quality web search and save `TAVILY_API_KEY`.
4. (Optional) If you want to demo the Pinecone path, create an index and save `PINECONE_API_KEY` plus `PINECONE_ENVIRONMENT`.

## B. Local Setup
5. Install Python 3.11 (use `pyenv` or Homebrew on macOS).
6. From the repo root, create and activate a virtual env: `python -m venv .venv && source .venv/bin/activate`.
7. Run `pip install -r requirements.txt` after Gemini finishes Phase 1.
8. Copy `.env.example` to `.env` and fill in the keys from section A.
9. Confirm system libs for `weasyprint` are present (macOS: `brew install pango cairo`; Linux: handled by the Dockerfile).

## C. Verify the Build End-to-End
10. Run `pytest -q` and confirm everything is green.
11. Run `streamlit run ui/app.py` and submit the README example question. Watch the live agent feed populate.
12. Download the generated `.md` and `.pdf` report; spot-check that citations point to real arXiv IDs and the code block actually runs.
13. Try a second, harder question (e.g. "Compare LoRA vs full fine-tuning on small LLMs") to make sure the loop generalizes.
14. Run `docker compose up --build` and confirm the app is reachable at `http://localhost:8501` from a browser.

## D. Hardening Before You Hand It Off
15. Add a `LICENSE` file (MIT is the simplest for a portfolio project).
16. Add a `.gitignore` covering `.env`, `.venv/`, `__pycache__/`, `runs/`, `*.pdf`, `.DS_Store`.
17. Remove the committed `.DS_Store` files: `git rm --cached .DS_Store .git/.DS_Store` and re-commit.
18. Update `README.md` with: a screenshot/GIF of the running UI, a "Limitations" section (sandbox is not a security boundary, costs money to run), and a "Troubleshooting" section.
19. Pin Python version with a `.python-version` file (`3.11`).
20. Add a GitHub Actions workflow at `.github/workflows/ci.yml` that runs `pytest -q` on every push.

## E. Publish & Submit
21. Push the repo to GitHub. Add topics: `agents`, `llm`, `streamlit`, `research-automation`.
22. (Optional) Deploy a public demo on Streamlit Community Cloud or Hugging Face Spaces. Configure the env vars in the host's secrets UI — never commit `.env`.
23. Write a 3–5 sentence project blurb for your submission, naming the multi-agent architecture (Planner / Researcher / Coder / Critic), the tools (arXiv, sandbox executor, vector memory), and one concrete example output.
24. Record a 60–90 second screen capture walking through one full research run; embed in the README.
25. Final review: re-read README.md and ARCHITECTURE.md side-by-side with the code to confirm nothing in the docs is unimplemented.

## F. Cost & Safety Sanity Check
26. Set a hard spending cap on your OpenAI/Anthropic dashboards before any public demo.
27. In the UI, surface the running token counter so you (and graders) can see live cost.
28. Decide whether to leave the executor unsandboxed for ease of demo, or require Docker for any "untrusted" research goal — document the choice in `README.md` under Limitations.
