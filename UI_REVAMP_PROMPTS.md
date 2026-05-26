# UI Revamp Prompts

Two prompts for an agentic CLI coding assistant (Claude Code, Codex CLI, etc.).
Paste **Prompt 1** first. If anything in the app stops working after the revamp,
paste **Prompt 2** to repair it without rolling the design back.

---

## Prompt 1 — Full UI / Website Revamp

```
You are working inside a Computer Science class project called "Autonomous AI Researcher".
The repository root is the current working directory. Read the project before touching anything,
then completely revamp BOTH user interfaces so the project feels organized, polished, and
genuinely inviting to a classmate or professor who has never seen it before.

────────────────────────────────────────────────────────────────────────
GOAL
────────────────────────────────────────────────────────────────────────
Redesign every user-facing surface with a single, cohesive, playful but
student-friendly visual identity. The two surfaces share the same brand,
palette, typography, iconography, and component vocabulary so a viewer
instantly recognizes them as parts of one product.

Tone target: warm, modern, curious, a little playful — like a well-made
educational tool, NOT a corporate SaaS dashboard. Friendly without being
childish. Think: rounded corners, soft shadows, generous whitespace,
expressive but readable headings, subtle animation, optional emoji
accents used sparingly and intentionally.

────────────────────────────────────────────────────────────────────────
SURFACES TO REVAMP (all of them)
────────────────────────────────────────────────────────────────────────
A) Static public site (GitHub Pages):
   - index.html
   - 404.html
   - assets/css/styles.css
   - assets/js/app.js      (logic — do NOT remove functionality)
   - assets/js/config.js   (leave the chatEndpoint config behavior intact)

B) Streamlit dashboard (local control plane):
   - ui/app.py
   - ui/components.py

C) Anything else that visibly affects branding:
   - README.md header block / badges (light touch-up only, keep all info)
   - Any favicon, og:image, or meta tags in index.html

DO NOT touch:
   - api/, core/, agents/, memory/, tools/, tests/, config.py, .env*,
     Dockerfile, docker-compose.yml, requirements.txt, pyproject.toml,
     package.json scripts, sitemap.xml/robots.txt/CNAME content.
   The backend API contract is frozen.

────────────────────────────────────────────────────────────────────────
STEP 0 — Read first, design second
────────────────────────────────────────────────────────────────────────
Before writing any code, read these files end-to-end:
   index.html, assets/css/styles.css, assets/js/app.js, assets/js/config.js,
   ui/app.py, ui/components.py, api/server.py, README.md
You must understand every existing function, form field, button, websocket
event, session_state key, and download path so the revamp preserves them all.

────────────────────────────────────────────────────────────────────────
DESIGN SYSTEM (define once, reuse everywhere)
────────────────────────────────────────────────────────────────────────
Create a single visual language and apply it identically to the static site
CSS and the Streamlit st.markdown CSS injection:

• Palette — playful but legible. Pick a primary that is friendly (e.g.
  indigo/violet, teal, or coral) and 3–4 supporting agent-accent colors so
  each agent (Planner / Researcher / Coder / Critic / Debater) has a stable
  hue used consistently in BOTH surfaces.
• Typography — pair a rounded display font (e.g. "Fraunces", "DM Serif
  Display", "Quicksand", or "Nunito") with a clean sans body
  (e.g. "Inter", "Plus Jakarta Sans"). Use Google Fonts via <link> in
  index.html and via st.markdown <link> injection in ui/app.py.
• Shape — radii: 16–20px for cards, 999px for pills/buttons.
• Surface — soft layered backgrounds, subtle gradients, gentle drop
  shadows. Optional decorative element: a soft "blob" SVG or subtle dot
  grid in the hero — keep it tasteful.
• Motion — small, polite animations only: fade-in on load, hover lift,
  pulsing "running" indicator. Respect prefers-reduced-motion.
• Accessibility — WCAG AA contrast, visible focus rings, semantic HTML,
  aria-live on the response area, skip link kept, keyboard nav intact.
• Responsive — mobile (≤560px), tablet (≤860px), desktop. The static site
  must remain usable on a phone.
• Dark mode — add a CSS prefers-color-scheme: dark variant for the static
  site. Streamlit follows the user's Streamlit theme; do not fight it.

Document the chosen palette + fonts as CSS custom properties at the top of
assets/css/styles.css AND mirror the same variables inside the Streamlit
<style> block so both surfaces stay in sync.

────────────────────────────────────────────────────────────────────────
A) STATIC SITE REQUIREMENTS (index.html / styles.css / app.js)
────────────────────────────────────────────────────────────────────────
Rebuild the layout with these sections, in this order:

1. Sticky header with the brand mark + name + a "v2.0 · CS Project" badge,
   plus a GitHub link. Keep the existing skip link.

2. Hero section: short, friendly headline + sub-headline that explains in
   one sentence what the project does. Include the agent pills (Planner /
   Researcher / Critic — or all five if you also show Coder/Debater). Keep
   the existing "signal map" idea OR replace it with a more inviting
   visual (illustrated flow, SVG node graph, etc.) — your call, but it
   must clearly communicate the Planner → Researcher → Critic flow.

3. NEW "How it works" section: 3–4 friendly cards explaining the pipeline
   in plain English. Each card gets an icon/emoji, a one-line title, and
   a two-line description. (This information already exists in README.md.)

4. Prompt workspace (this is THE primary tool — must keep all behavior):
   • <form id="prompt-form"> with:
       - <textarea id="prompt" name="prompt" maxlength="2000" required>
         (default seed text is OK to keep or rewrite into something more
         inviting — keep it ≥10 chars)
       - char counter (#prompt-count) and the .char-bar .char-bar-fill
         progress bar with data-level="safe|warn|danger" levels driven by
         app.js
       - <input id="access-token" name="access-token" type="password">
         labeled "Access code" (still optional, still persists via
         localStorage under key "air_site_access_token")
       - Buttons: #submit-button (primary "Run prompt") and
         #clear-button (.secondary-button)
   • <section class="response-panel"> containing:
       - aria-live="polite", aria-labelledby="response-title"
       - eyebrow "Model response", h2 #response-title "Research Brief"
       - #copy-button (.icon-button) — must still copy #response-output text
       - #status-pill (.status-pill, .error variant) — must still receive
         "Ready" / "Thinking..." / model name / "Error" / "The request
         timed out."
       - <pre id="response-output"> — must still display the streamed
         result or error message
   ALL ELEMENT IDs AND CLASS NAMES LISTED ABOVE MUST REMAIN, because
   assets/js/app.js queries them by exactly those selectors. You may add
   new classes, but do not rename or remove the existing ones.

5. NEW small footer with the existing "Built for CS class · Powered by
   OpenAI" line, a Sitemap link, and optionally a "Made with ♥ for [class
   name]" stamp.

6. 404.html — rebuild with the same design system, a friendly illustration
   or emoji, and a "Back to home" link to "/".

assets/js/app.js — keep ALL current behavior 1:1:
   • Reads window.AIR_SITE_CONFIG.chatEndpoint from config.js.
   • Saves/loads access token from localStorage["air_site_access_token"].
   • On submit: validates prompt length ≥ 10, sets status, sets busy,
     POSTs JSON {prompt} to chatEndpoint with Content-Type and optional
     X-Site-Access-Token header, 30s AbortController timeout, parses
     response.json() → data.output and data.model, handles errors with
     friendly messages.
   • Copy button uses navigator.clipboard.writeText.
   • Clear button resets prompt, output, status, counter, focus.
You may refactor the JS for readability (e.g. extract small helpers, add
JSDoc) but every existing user-visible behavior must still work.

assets/js/config.js — leave the export shape exactly the same:
   window.AIR_SITE_CONFIG = { chatEndpoint: "" };

────────────────────────────────────────────────────────────────────────
B) STREAMLIT DASHBOARD REQUIREMENTS (ui/app.py + ui/components.py)
────────────────────────────────────────────────────────────────────────
The Streamlit app currently has:
   • _init_session_state with keys: tasks, running, result, buffers, run_id
   • _inject_css block
   • _render_hero with "CS Class Project" badge + agent pills
   • Left column "Control Panel":
       - st.text_area "Research Question" (default seed sentence)
       - st.button "▶ Run Research" → httpx.post {api_base_url}/api/research
         with JSON {"question": question}; stores run_id in session_state
       - st.button "Load Knowledge Graph" → uses memory.knowledge_graph
         .KnowledgeGraph().query_related(question, k=3)
   • Right column tabs:
       - "🔴 Live Activity" tab — status bar (Idle / Agents running...),
         task feed via task_event_card(), token streaming via
         _render_token_buffers() with blinking cursor
       - "📄 Report" tab — success banner with cost_estimate, download
         buttons for report.md and report.pdf (when those paths exist on
         disk), expandable Markdown preview
   • _stream_research_events connects to
     {ws_url}/api/research/{run_id}/stream and handles task_update / token
     / done / error / cancelled events.
   • ui/components.py exports task_event_card(task) returning HTML and
     agent_card(name, role, status, tokens, cost) rendering with
     st.markdown(..., unsafe_allow_html=True).

REVAMP REQUIREMENTS:
1. Apply the same playful design language as the static site (same colors,
   same agent accent hues, same rounded shapes, same fonts via Google
   Fonts <link> injected through st.markdown). The hero, agent pills, and
   buttons should feel visually continuous with index.html.
2. Re-organize the layout for clarity:
   • Hero stays at top.
   • Add a tasteful, collapsible "How it works" / "Tips" expander above or
     beside the Control Panel — friendly, short, useful to a first-time
     viewer.
   • Control Panel: clearer grouping with a section heading + caption per
     group. Bigger primary "Run Research" button, gentle hover.
   • Live Activity tab: keep the status bar, task feed cards, token
     streaming card with blinking cursor, but visually upgrade the cards
     to match the new design system. Add a clear empty-state illustration
     or message when there are no tasks yet.
   • Report tab: keep markdown + PDF download buttons, success banner with
     cost, and the in-page Markdown preview. Make the download buttons
     prominent.
3. NEW: a small "Cancel run" button that appears in the Live Activity tab
   ONLY while st.session_state.running is True. Wire it to
       httpx.delete(f"{settings.api_base_url}/api/research/{run_id}")
   (this endpoint already exists in api/server.py). On success, set
   running=False and st.toast a friendly cancellation message.
4. Keep every session_state key, every existing button label's behavior,
   every API call, every download, every websocket event handler. If you
   rename any session_state key, update every reference in the same
   commit.
5. Refactor for readability: split _inject_css into a separate constant or
   helper module if it becomes large; extract repeated st.markdown HTML
   into ui/components.py helpers.

ui/components.py — keep the public function signatures:
   • task_event_card(task: dict) -> str
   • agent_card(name, role, status, tokens, cost) -> None  (renders)
You can add new helpers freely, but those two must still exist and behave
the same way so ui/app.py keeps importing them.

────────────────────────────────────────────────────────────────────────
C) FUNCTIONALITY PRESERVATION CHECKLIST  (must all still work)
────────────────────────────────────────────────────────────────────────
Static site:
  [ ] Char counter updates and progress bar changes color at >80% / >95%
  [ ] Prompt < 10 chars shows the inline error message
  [ ] Submit POSTs JSON to AIR_SITE_CONFIG.chatEndpoint
  [ ] Optional X-Site-Access-Token header included when access code set
  [ ] 30 s timeout with AbortController, friendly "request timed out" text
  [ ] Status pill toggles: Ready / Thinking... / model name / Error
  [ ] Copy button copies #response-output and shows "Copied!" feedback
  [ ] Clear button resets everything and focuses the textarea
  [ ] Access token persists across reloads via localStorage
  [ ] Skip link still jumps to #workspace
  [ ] No console errors on load

Streamlit:
  [ ] App boots with `streamlit run ui/app.py`
  [ ] "▶ Run Research" creates a run via POST /api/research and stores
      run_id in session_state.run_id
  [ ] WebSocket connection to /api/research/{run_id}/stream renders
      task_update events as cards and token events as streaming buffers
  [ ] "done" event populates session_state.result and switches the UI to
      the completed state
  [ ] "error" / "cancelled" events show a Streamlit error/info
  [ ] Report tab shows cost_estimate badge and downloads for report.md /
      report.pdf when those files exist on disk
  [ ] Markdown preview expander still renders the report
  [ ] "Load Knowledge Graph" still queries memory.knowledge_graph and
      renders the result cards
  [ ] NEW Cancel button calls DELETE /api/research/{run_id} and only
      shows while a run is in progress

────────────────────────────────────────────────────────────────────────
DELIVERABLES
────────────────────────────────────────────────────────────────────────
1. Edit the files in place (index.html, 404.html, assets/css/styles.css,
   assets/js/app.js, ui/app.py, ui/components.py, optional README header).
2. After editing, run a quick self-review:
     • Re-read each file you changed.
     • Verify every checklist item above against the new code.
     • Run `python -c "import ui.app, ui.components, api.server"` to catch
       syntax/import errors.
     • If a JS bundler / npm run build exists, run it; otherwise serve
       the static site once with `python3 -m http.server 3000` and read
       the console for errors mentally.
3. Print a short summary of:
     • Which files you touched.
     • The chosen palette (hex), fonts, and headline copy.
     • Anything you intentionally simplified or removed (there should be
       nothing functional in this bucket).
     • Any TODOs you couldn't complete and why.

Begin now. Read the project first; design second; edit third; self-verify
last. Do not ask for approval between phases — just deliver.
```

---

## Prompt 2 — Follow-up "Fix Anything Broken" Prompt

Paste this only if, after running Prompt 1, you spot any UI element that
stopped working (button does nothing, stream doesn't show, download
missing, etc.).

```
The UI revamp you just delivered has functional regressions. Do NOT roll
back the visual design — keep the new look. Repair the functionality so
the new UI behaves identically to the pre-revamp app.

────────────────────────────────────────────────────────────────────────
STEP 1 — Diagnose
────────────────────────────────────────────────────────────────────────
Re-read the same files you touched plus api/server.py. Then, against the
checklist below, verify each item by reading the current code paths.
Treat anything you cannot trace to working code as broken.

Static site (assets/js/app.js + index.html):
  • Element IDs/classes app.js relies on still exist:
      #prompt-form, #prompt, #access-token, #response-output,
      #status-pill, #submit-button, #clear-button, #prompt-count,
      #copy-button, .char-bar-fill
  • TOKEN_STORAGE_KEY "air_site_access_token" still reads/writes
    localStorage.
  • window.AIR_SITE_CONFIG.chatEndpoint is still read from config.js.
  • fetch() still sends POST JSON {prompt} with optional
    X-Site-Access-Token header.
  • AbortController 30 s timeout still wired.
  • setStatus / setBusy / updateCounter / resetCopyButton helpers still
    update the right DOM nodes.
  • Skip link href still targets #workspace.

Streamlit (ui/app.py + ui/components.py):
  • st.session_state keys still initialized: tasks, running, result,
    buffers, run_id.
  • Run button still POSTs to f"{settings.api_base_url}/api/research"
    with JSON {"question": question} and stores response["run_id"].
  • _stream_research_events still opens
    f"{ws_url}/api/research/{run_id}/stream" and handles event types
    "task_update", "token", "done", "error", "cancelled".
  • Token streaming still appends to st.session_state.buffers[agent] and
    renders the blinking cursor.
  • Report tab still reads result["usage"]["cost_estimate"],
    result["report_md"], result["report_pdf_path"] and shows download
    buttons + Markdown preview expander when files exist.
  • "Load Knowledge Graph" still imports memory.knowledge_graph
    .KnowledgeGraph and calls query_related(question, k=3).
  • The new Cancel button only renders while running and calls
    httpx.delete(f"{settings.api_base_url}/api/research/{run_id}").
  • ui/components.py still exports task_event_card(task) -> str and
    agent_card(name, role, status, tokens, cost) -> None.

────────────────────────────────────────────────────────────────────────
STEP 2 — Repair
────────────────────────────────────────────────────────────────────────
For every broken item:
  1. Fix it in place. Do not redesign — match the existing new look.
  2. If a selector was renamed in the HTML, restore the original ID/class
     name OR update app.js to query the new one — pick whichever keeps
     the visual design intact and breaks nothing else.
  3. If a session_state key was renamed, update every reader/writer.
  4. If a Streamlit re-run loop was disrupted, re-add the st.rerun() /
     st.experimental_rerun() call in the right branch.
  5. If CSS now covers a control (e.g. pointer-events: none on a parent),
     remove or scope the rule.

────────────────────────────────────────────────────────────────────────
STEP 3 — Verify
────────────────────────────────────────────────────────────────────────
  • Run `python -c "import ui.app, ui.components, api.server"` — must
    succeed.
  • Open index.html in a headless check: parse it, confirm every required
    ID/class exists exactly once.
  • Re-walk the checklist above and tick each item against the actual
    code paths.
  • Output a short diff summary: what was broken, what you changed to
    fix it, and which checklist items you re-verified.

Do not introduce new features. Do not regress the new design. Only repair.
```

---

### How to use these

1. Open the project in VS Code with your agentic CLI (Claude Code or Codex
   CLI) attached to this repository.
2. Copy **Prompt 1** (everything inside the first code fence) and paste it
   into the CLI as one message.
3. Let the agent finish. Then manually click around the static site and
   run `streamlit run ui/app.py` to sanity-check.
4. If anything is broken, paste **Prompt 2** as a second message.
