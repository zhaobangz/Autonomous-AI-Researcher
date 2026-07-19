# Autonomous AI Researcher — Demo Video Submission Package

> **Target length:** 2–3 minutes | **Tone:** Professional, technical, conversational

---

## PART 1: VIDEO OUTLINE

### Q1 — Why Did You Build This? (0:00 – 0:35)
- Hook: The cost of manual research — hours of searching, reading, second-guessing sources
- The bottleneck: researchers and engineers spend more time *finding* information than *using* it
- Insight: LLMs can reason, but they hallucinate and can't verify their own claims
- The fix: a multi-agent system where agents check each other — not just one LLM, but a team

### Q2 — How Does It Work? (0:35 – 1:40)
- High-level: a "Task-Actor" pipeline orchestrated by a central Task Manager
- Agent walkthrough (live demo or screen recording):
  1. **Planner** — decomposes the question into a structured step roadmap
  2. **Researcher** — runs parallel arXiv searches, parses PDFs, synthesises findings
  3. **Coder** — writes and executes Python experiments inside a sandboxed Docker container
  4. **Critic** — scores confidence (0–1), flags weaknesses, can trigger Coder retry
  5. **Debater** — adversarially challenges the Critic to prevent confirmation bias
  6. **Report Generator** — produces a structured Markdown + PDF report
- Infrastructure callouts: ChromaDB/Pinecone vector memory, knowledge graph, FastAPI + WebSocket streaming, Streamlit UI

### Q3 — Potential Use Cases (1:40 – 2:20)
- Academic researchers: automated literature reviews in minutes vs. days
- ML engineers: rapid hypothesis validation — write a question, get experiment results
- Analysts & journalists: source-aware, structured research briefs on technical topics
- Enterprises: domain-specific research agents (legal, biomedical, financial)
- Impact: democratises rigorous research — anyone with an API key gets a research team

### Q4 — What Would You Add? (2:20 – 2:50)
- Stronger source-quality controls for web search results beyond the current Tavily/DuckDuckGo fallback
- Domain-specific agent profiles for biomedical, legal, and financial reasoning
- Multi-user collaboration — shared run history, threaded annotations
- Better scheduled research reporting on top of the existing GitHub Actions scheduled workflow
- Tool use expansion — SQL databases, code repos, proprietary APIs

---

## PART 2: FULL VIDEO SCRIPT

*(Calibrated for ~100 wpm → ~3:00. Speak naturally; don't rush.)*

---

**[INTRO — 0:00]**

Research is brutally slow. Finding the right papers, cross-checking claims, running experiments — that eats weeks. And even then, a single researcher can miss something, or talk themselves into a conclusion that isn't there.

I built the Autonomous AI Researcher to fix that.

---

**[Q1 — WHY — 0:15]**

The problem: LLMs reason well, but they can't tell when they're wrong. A single model will confidently hallucinate a citation or produce a flawed experiment. So the question wasn't "can AI do research?" — it was "how do you make it *trustworthy*?"

The answer: don't trust a single agent. Build a team.

---

**[Q2 — HOW IT WORKS — 0:32]**

The system is a multi-agent pipeline built around five specialized roles.

You submit a question. The **Planner** breaks it into a structured roadmap — identifying what needs a literature review and what needs experimental validation.

The **Researcher** runs parallel searches across arXiv, parses full PDFs, and synthesises the findings into a structured summary.

From that, the **Coder** generates Python experiments and executes them inside an isolated Docker sandbox — resource-limited and reproducible.

The **Critic** scores the results from 0 to 1, flags weaknesses, and — if confidence is too low — sends the Coder back for another pass.

And here's the part I'm most proud of: the **Debater**. Rather than accepting the Critic's verdict, it actively argues against it — surfacing blind spots and alternative interpretations. Adversarial quality control, built into the loop.

Finally, the Report Generator produces a structured Markdown and PDF report with literature synthesis, code, results, and the full critical review. You watch the whole thing stream live in the Streamlit dashboard.

---

**[Q3 — USE CASES — 1:40]**

Who is this for?

An academic can get a literature synthesis in minutes, not days. An ML engineer can describe a hypothesis and get experiment results — with a confidence-scored critique — before lunch. An analyst gets a structured research brief with sources and risks attached.

Longer term, this is a foundation for domain-specific agents: biomedical, legal, financial — each running the same trusted pipeline, tuned to its domain.

This makes rigorous research accessible to anyone with an API key, not just institutions with large teams.

---

**[Q4 — WHAT'S NEXT — 2:20]**

Three things I'd add with more time.

Stronger source-quality controls — ranking and explaining *why* a source is trustworthy, not just retrieving it. Domain-specific agent profiles — a biomedical Researcher tuned for clinical evidence, a legal one that understands case-law constraints.

And scheduled research: the repo already has a GitHub Actions workflow for recurring runs. The next step is comparison reports that surface what changed since the last run — turning a research tool into a research subscription.

---

**[OUTRO — 2:52]**

Open source, one-command deploy with Docker Compose, built to extend. If you've ever spent a week on a literature review, you know exactly why I built this.

Thanks for watching.

---

## PART 3: SLIDE NOTES

*(Speaker notes mapped to suggested slide beats)*

---

**Slide 1 — Title Slide**
> "Autonomous AI Researcher — end-to-end AI-assisted research"
- Speaker note: Open with confidence. Don't read the title. Pause one beat, then launch into the hook.

---

**Slide 2 — The Problem**
> Headline: "Research is slow. And single-model AI isn't the answer."
- Callout stat or visual: "Hours → days of manual literature review"
- Speaker note: Land the core tension — LLMs reason well but can't self-verify. That's the gap this fills.

---

**Slide 3 — Architecture Diagram**
> Show the pipeline: User → Planner → Researcher → Coder → Critic → Debater → Report
- Speaker note: Don't explain every box. Walk the flow top to bottom in ~20 seconds. Emphasise that each agent is specialized and checks the previous one.

---

**Slide 4 — Live Demo / Screen Recording**
> Streamlit UI — submit a question, watch agents fire in real-time
- Speaker note: Let the demo breathe. Point out: (1) live token streaming, (2) confidence score from Critic, (3) Debater rebuttal, (4) final report download.

---

**Slide 5 — Sample Output**
> Show a real report snippet (e.g., the LoRA vs. full fine-tuning run)
- Speaker note: "This is a real output from the system — literature synthesis, code results, critic score of 0.72, and the Debater's rebuttal." Point out the source context and review sections.

---

**Slide 6 — Use Cases**
> Three columns: Academics | ML Engineers | Analysts & Enterprises
- Speaker note: Keep this fast — one sentence per persona. End on the democratisation point: "a research team for anyone with an API key."

---

**Slide 7 — What's Next**
> Four bullets: Web search | Domain-tuned agents | Multi-user collab | Scheduled research
- Speaker note: Pick the one you're most excited about and give it one extra sentence. The scheduled research angle is the most distinctive — lean into it.

---

**Slide 8 — Closing / Links**
> GitHub repo | Public demo URL | Local full-app instructions
- Speaker note: Short. "Open source, static public demo, and a full local agent workflow. Link in the description." Done.

---

## PART 4: SHOT LIST

| # | Timestamp | What's On Screen | Notes |
|---|---|---|---|
| 1 | 0:00 – 0:18 | Title card or talking head | Clean background; project name visible |
| 2 | 0:18 – 0:38 | Problem slide (text + diagram) | Animate the "bottleneck" concept; keep it simple |
| 3 | 0:38 – 0:55 | Architecture diagram | Highlight each agent box as you mention it |
| 4 | 0:55 – 1:30 | Streamlit UI — live run | Submit a question; show the real-time agent feed streaming in |
| 5 | 1:10 – 1:30 | Zoom: Critic + Debater output | Show the confidence score (0.72) and the Debater rebuttal text |
| 6 | 1:30 – 1:40 | Report download / PDF output | Show the generated report.md or PDF — scroll through it briefly |
| 7 | 1:40 – 2:10 | Use case slide (3 columns) | Static slide OK; can animate columns in |
| 8 | 2:10 – 2:22 | "What's next" slide | Bullet list, one point at a time |
| 9 | 2:22 – 2:48 | Talking head or split: face + screen | Return to camera for the personal close |
| 10 | 2:48 – end | Closing card: GitHub + demo URL | Hold 5 seconds minimum for viewers to read |

---

### Production Tips

- **Record the Streamlit UI live** if possible — watching agents stream in real-time is the most compelling visual in the project.
- **Use the LoRA vs. full fine-tuning run** as your demo question — the output is clean, the results are crisp, and the Debater rebuttal is a great talking point.
- **Confidence score and Debater rebuttal** are your differentiators vs. a basic LLM chatbot — make sure both appear on screen.
- **Keep transitions fast.** At 2–3 minutes there is no slack. Cut anything that isn't either explaining a concept or showing the product working.
