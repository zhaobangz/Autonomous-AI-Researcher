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
- Infrastructure callouts: ChromaDB vector memory, FastAPI + WebSocket streaming, Streamlit UI

### Q3 — Potential Use Cases (1:40 – 2:20)
- Academic researchers: automated literature reviews in minutes vs. days
- ML engineers: rapid hypothesis validation — write a question, get experiment results
- Analysts & journalists: fact-checked, cited research briefs on any topic
- Enterprises: domain-specific research agents (legal, biomedical, financial)
- Impact: democratises rigorous research — anyone with an API key gets a research team

### Q4 — What Would You Add? (2:20 – 2:50)
- Real-time web search (Tavily) alongside arXiv for broader coverage
- Fine-tuned domain-specific agents (biomedical, legal, financial reasoning)
- Multi-user collaboration — shared run history, threaded annotations
- Autonomous scheduling — recurring research loops triggered on a cadence
- Tool use expansion — SQL databases, code repos, proprietary APIs

---

## PART 2: FULL VIDEO SCRIPT

*(Words at ~130 wpm → ~2:40. Adjust pacing to hit your target.)*

---

**[INTRO — 0:00]**

Research is one of the most valuable things humans do. But it's also brutally slow. Finding the right papers, reading them, cross-checking claims, running experiments to validate them — that process eats weeks. And even then, a single researcher might miss something, or convince themselves of a conclusion that isn't really there.

I built the Autonomous AI Researcher to fix that bottleneck.

---

**[Q1 — WHY — 0:18]**

The core problem I kept running into: LLMs are incredible at reasoning, but terrible at knowing when they're wrong. A single model can confidently produce a hallucinated citation or a flawed experiment. So the question wasn't "can AI do research?" — it was "how do you make AI research *trustworthy*?"

The answer is: you don't trust a single agent. You build a team.

---

**[Q2 — HOW IT WORKS — 0:38]**

The system is a multi-agent pipeline built around five specialized roles.

You submit a research question. The **Planner** decomposes it into a structured step-by-step roadmap — identifying what needs a literature review and what needs experimental validation.

The **Researcher** then runs parallel searches across arXiv, fetches and parses full PDFs, and synthesises the key findings into a structured summary.

From that summary, the **Coder** generates Python experiments and executes them inside an isolated Docker sandbox — resource-limited, no network access, reproducible.

The **Critic** reviews the results, assigns a confidence score from 0 to 1, identifies weaknesses, and — if confidence is too low — sends the Coder back for another iteration.

Here's the part I'm most proud of: the **Debater**. Rather than just accepting the Critic's verdict, the Debater actively argues against it — challenging assumptions, surfacing alternative interpretations. It's adversarial quality control, built into the loop.

Finally, a Report Generator assembles everything into a structured Markdown and PDF report — with citations, code, results, and the full critical review.

The whole thing runs on a FastAPI backend with WebSocket streaming, so you watch it think in real time through a Streamlit dashboard. And a long-term memory layer using ChromaDB means the system learns across research runs — no redundant searches.

---

**[Q3 — USE CASES — 1:48]**

Who is this for?

An academic researcher can get a literature synthesis in minutes instead of days, with citations they can actually verify. An ML engineer can describe a hypothesis and receive experiment results — including code and a confidence-scored critique — before lunch. An analyst or journalist gets a cited, structured research brief on any topic.

And longer term, this is a foundation for domain-specific agents — a biomedical research assistant, a legal research tool, a financial intelligence system — each running the same trusted pipeline, tuned to its domain.

The broader impact is real: this makes rigorous, peer-reviewed-style research accessible to anyone with an API key, not just institutions with large teams.

---

**[Q4 — WHAT'S NEXT — 2:22]**

A few things I'd add with more time.

First, real-time web search alongside arXiv — so the system isn't limited to academic papers but can pull live information. Second, fine-tuned domain agents — a biomedical Researcher trained on PubMed, a legal Coder that understands case law. Third, multi-user collaboration — shared run history, threaded comments, team annotations.

And the one I'm most excited about: autonomous scheduled research. You define a question and a cadence, and the system runs weekly, surfaces changes, and flags when the answer has evolved. Not just a research tool — a research *subscription*.

---

**[OUTRO — 2:48]**

The Autonomous AI Researcher is open source, deployable in one command, and built to be extended. If you've ever spent a week on a literature review, you'll understand exactly why I built it.

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
- Speaker note: "This is a real output from the system — literature synthesis, code results, critic score of 0.72, and the Debater's rebuttal." Point out the citations.

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
> GitHub repo | Public demo URL | Contact
- Speaker note: Short. "Open source, one-command deploy. Link in the description." Done.

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
