# Gemini Pro 3.1 — Full Project Fix & Completion Prompt

> **How to use this file:** Copy everything from the horizontal rule below to the end of the document and paste it as a single message into Google's Antigravity IDE with Gemini Pro 3.1. The prompt is entirely self-contained — all source context, bug descriptions, and instructions are included.

---

---

## SYSTEM CONTEXT

You are an expert Python engineer and software architect. You have been given the complete source code of a project called **Autonomous AI Researcher**. Your job is to fix every bug, fill every gap, complete every missing connection, and produce a fully working, production-ready codebase. Read every section carefully before writing a single line of code.

---

## 1. PROJECT OVERVIEW

**Autonomous AI Researcher** is a multi-agent AI system that takes a scientific research question from a user, autonomously plans a research strategy, searches academic literature (arXiv), synthesizes papers, writes and executes Python experiments in a sandboxed environment, critiques the results via an adversarial debate loop, and finally generates a polished Markdown + PDF research report.

### 1.1 Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| LLM providers | OpenAI (primary), Anthropic (secondary) |
| Backend API | FastAPI + Uvicorn (port 8000) |
| Real-time events | WebSocket (`/api/research/{run_id}/stream`) |
| Frontend UI | Streamlit (port 8501) |
| Vector memory | ChromaDB (local default) or Pinecone (cloud) |
| Knowledge graph | NetworkX (persistent JSON) |
| Code sandbox | Docker container (`python:3.11-slim`) |
| Embeddings | OpenAI `text-embedding-3-small` or `sentence-transformers/all-MiniLM-L6-v2` |
| PDF generation | WeasyPrint |
| Report format | Markdown + PDF |
| Tests | pytest + pytest-mock |
| Containerisation | Docker + docker-compose |

### 1.2 Full Directory Layout (target state)

```
autonomous-ai-researcher/
├── api/
│   ├── __init__.py
│   └── server.py              ← FastAPI app + WebSocket streaming
├── core/
│   ├── __init__.py
│   ├── llm_client.py          ← Unified LLM wrapper (OpenAI + Anthropic)
│   ├── agent_loop.py          ← Main async orchestrator → run_agent_async()
│   ├── task_manager.py        ← Task state store + pub/sub
│   ├── tool_registry.py       ← Singleton tool registry + ReAct dispatch
│   └── report_generator.py    ← Markdown + PDF report builder
├── agents/
│   ├── __init__.py
│   ├── base_agent.py          ← Abstract async base with ReAct loop
│   ├── planner.py             ← Decomposes question into typed plan steps
│   ├── researcher.py          ← arXiv search + PDF parse + summarize
│   ├── coder.py               ← Writes + executes Python experiments
│   ├── critic.py              ← Structured critique with confidence score
│   └── debater.py             ← Adversarial rebuttal agent
├── tools/
│   ├── __init__.py
│   ├── arxiv_search.py        ← Returns List[ArxivPaper]
│   ├── paper_parser.py        ← PDF URL/path → ParsedPaper
│   ├── web_search.py          ← Tavily / DuckDuckGo fallback
│   └── code_executor.py       ← Docker sandbox executor
├── memory/
│   ├── __init__.py
│   ├── embeddings.py          ← embed() switching OpenAI / sentence-transformers
│   ├── vector_store.py        ← ChromaDB or Pinecone backend
│   └── knowledge_graph.py     ← Cross-run NetworkX graph with cosine edges
├── ui/
│   ├── __init__.py
│   ├── app.py                 ← Streamlit 3-column dashboard
│   └── components.py          ← Reusable agent_card widget
├── tests/
│   ├── __init__.py
│   └── test_agent_loop.py     ← Full smoke test with mocked LLM
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## 2. COMPLETE CURRENT SOURCE CODE

Below is every relevant source file verbatim. Study each one before proceeding.

### `core/llm_client.py`
```python
"""
Unified LLM interface with robust error handling and async streaming.
"""
import os
import json
import httpx
from typing import List, Dict, Any, Type, AsyncGenerator
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

class LLMClient:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.model = os.getenv("LLM_MODEL", "gpt-4o")
        self.usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost_estimate": 0.0}
        self.pricing = {
            "gpt-4o": [0.005, 0.015],
            "gpt-3.5-turbo": [0.0005, 0.0015],
            "claude-3-opus-20240229": [0.015, 0.075],
            "claude-3-sonnet-20240229": [0.003, 0.015],
            "claude-3-haiku-20240307": [0.00025, 0.00125]
        }
        api_key = os.getenv("OPENAI_API_KEY") if self.provider == "openai" else os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise EnvironmentError(f"[LLMClient] {self.provider.upper()}_API_KEY is not configured.")
        if self.provider == "openai":
            import openai
            self.client = openai.OpenAI(api_key=api_key)
        elif self.provider == "anthropic":
            import anthropic
            self.client = anthropic.Anthropic(api_key=api_key)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def _update_usage(self, prompt_tokens, completion_tokens):
        self.usage["prompt_tokens"] += prompt_tokens
        self.usage["completion_tokens"] += completion_tokens
        rates = self.pricing.get(self.model, [0.01, 0.03])
        self.usage["cost_estimate"] += (prompt_tokens * rates[0] / 1000) + (completion_tokens * rates[1] / 1000)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def chat_completion(self, messages, temperature=0.7, max_tokens=4000):
        if self.provider == "openai":
            response = self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature, max_tokens=max_tokens)
            self._update_usage(response.usage.prompt_tokens, response.usage.completion_tokens)
            return response.choices[0].message.content
        elif self.provider == "anthropic":
            system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
            msgs = [m for m in messages if m["role"] != "system"]
            response = self.client.messages.create(model=self.model, messages=msgs, system=system_msg, temperature=temperature, max_tokens=max_tokens)
            self._update_usage(response.usage.input_tokens, response.usage.output_tokens)
            return response.content[0].text

    async def stream_completion_async(self, messages, temperature=0.7, max_tokens=4000):
        async with httpx.AsyncClient() as client:
            if self.provider == "openai":
                headers = {"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}", "Content-Type": "application/json"}
                data = {"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True}
                async with client.stream("POST", "https://api.openai.com/v1/chat/completions", headers=headers, json=data) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            content = line[6:]
                            if content == "[DONE]": break
                            try:
                                chunk = json.loads(content)
                                if chunk["choices"][0]["delta"].get("content"):
                                    yield chunk["choices"][0]["delta"]["content"]
                            except json.JSONDecodeError:
                                pass

    def structured_output(self, messages, schema):
        schema_json = json.dumps(schema.model_json_schema())
        instruction = f"\n\nYou MUST return a raw JSON object matching this schema. No markdown.\nSchema:\n{schema_json}"
        msgs = list(messages)
        if msgs and msgs[0]["role"] == "system":
            msgs[0]["content"] += instruction
        else:
            msgs.append({"role": "system", "content": instruction})
        for attempt in range(2):
            raw_output = self.chat_completion(msgs, temperature=0.1, max_tokens=4000)
            clean = raw_output.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            try:
                return schema.model_validate(json.loads(clean))
            except Exception as e:
                if attempt == 0:
                    msgs.append({"role": "assistant", "content": raw_output})
                    msgs.append({"role": "user", "content": f"Failed: {e}. Return valid JSON only."})
                else:
                    raise Exception(f"structured_output failed after 2 attempts: {e}")
```

### `core/task_manager.py`
```python
import json, os, uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field

class Task(BaseModel):
    id: str
    parent_id: Optional[str] = None
    kind: str
    status: str = "pending"
    input: Any = None
    output: Any = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None

class TaskManager:
    def __init__(self, run_id: str):
        uuid.UUID(run_id)
        self.run_id = run_id
        self.tasks: Dict[str, Task] = {}
        self.callbacks: List[Callable] = []
        BASE_DIR = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        self.run_dir = BASE_DIR / run_id
        os.makedirs(self.run_dir, exist_ok=True)
        self.tasks_file = self.run_dir / "tasks.json"

    def subscribe(self, callback):
        self.callbacks.append(callback)

    def _notify(self, task):
        for cb in self.callbacks:
            cb(task)
        self._save()

    def _save(self):
        with open(self.tasks_file, "w") as f:
            json.dump({tid: t.model_dump() for tid, t in self.tasks.items()}, f, indent=2)

    def add(self, task):
        self.tasks[task.id] = task
        self._notify(task)

    def update(self, task_id, **fields):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for k, v in fields.items():
                setattr(task, k, v)
            if fields.get("status") in ("done", "failed"):
                task.finished_at = datetime.utcnow().isoformat()
            self._notify(task)

    def get(self, task_id):
        return self.tasks.get(task_id)

    def pending(self):
        return [t for t in self.tasks.values() if t.status == "pending"]

    def history(self):
        return list(self.tasks.values())
```

### `core/tool_registry.py`
```python
import json
from typing import Callable, Dict, Any
from pydantic import BaseModel
from tools.arxiv_search import search_arxiv
from tools.web_search import web_search
from tools.paper_parser import parse_pdf
from tools.code_executor import PythonExecutor

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict
    callable: Callable

    class Config:
        arbitrary_types_allowed = True

class ToolRegistry:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.tools = {}
            cls._instance._init_default_tools()
        return cls._instance

    def _init_default_tools(self):
        self.register(ToolDefinition(name="search_arxiv", description="Search arXiv for papers.", input_schema={"type":"object","properties":{"query":{"type":"string"},"max_results":{"type":"integer"}},"required":["query"]}, callable=search_arxiv))
        self.register(ToolDefinition(name="web_search", description="Search the web.", input_schema={"type":"object","properties":{"query":{"type":"string"},"k":{"type":"integer"}},"required":["query"]}, callable=web_search))
        self.register(ToolDefinition(name="parse_pdf", description="Parse a PDF from arxiv URL.", input_schema={"type":"object","properties":{"url_or_path":{"type":"string"}},"required":["url_or_path"]}, callable=parse_pdf))
        executor = PythonExecutor()
        self.register(ToolDefinition(name="run_python_code", description="Run Python in sandbox.", input_schema={"type":"object","properties":{"code":{"type":"string"}},"required":["code"]}, callable=executor.execute))

    def register(self, tool_def):
        self.tools[tool_def.name] = tool_def

    def get_schema_json(self):
        return json.dumps([{"name": t.name, "description": t.description, "parameters": t.input_schema} for t in self.tools.values()], indent=2)

    def execute(self, name, args):
        if name not in self.tools:
            raise ValueError(f"Tool {name} not found.")
        return self.tools[name].callable(**args)
```

### `core/agent_loop.py`
```python
import uuid, os, asyncio
from typing import Callable, Optional, Dict, Any
from core.task_manager import TaskManager, Task
from memory.vector_store import VectorStore
from memory.knowledge_graph import KnowledgeGraph
from core.report_generator import ReportGenerator
from core.tool_registry import ToolRegistry
from agents.planner import Planner
from agents.researcher import Researcher
from agents.coder import Coder
from agents.critic import Critic
from agents.debater import Debater

async def run_agent_async(research_question, run_id=None, on_event=None, on_token=None, stream_tokens=False):
    if not run_id:
        run_id = str(uuid.uuid4())
    tm = TaskManager(run_id)
    if on_event:
        tm.subscribe(on_event)
    vstore = VectorStore(run_id)
    tool_registry = ToolRegistry()
    kg = KnowledgeGraph()
    planner = Planner(memory=vstore, tool_registry=tool_registry)
    researcher = Researcher(memory=vstore, tool_registry=tool_registry)
    coder = Coder(memory=vstore, tool_registry=tool_registry)
    critic = Critic(memory=vstore, tool_registry=tool_registry)
    debater = Debater(memory=vstore, tool_registry=tool_registry)
    tm.add(Task(id="plan_1", kind="plan", input=research_question, status="running"))
    plan = await planner.run_async(research_question, kg=kg)
    tm.update("plan_1", status="done", output=plan.model_dump())
    related_nodes = kg.query_related(research_question, k=3)
    context = {"question": research_question, "plan": plan.model_dump()["steps"], "literature": [f"Past: {r.get('title')} - {r.get('summary')}" for r in related_nodes], "code": "", "results": {}}
    max_steps = int(os.getenv("MAX_STEPS", "12"))
    step_count, reroutes = 0, 0
    search_steps = [s for s in plan.steps if s.kind in ("search", "summarize")]
    other_steps = [s for s in plan.steps if s.kind not in ("search", "summarize")]
    if search_steps:
        async def run_search(idx, step):
            task_id = f"step_search_{idx}"
            tm.add(Task(id=task_id, kind=step.kind, input=step.rationale, status="running"))
            summary = await researcher.run_async(research_question + " " + step.rationale, stream_callback=on_token if stream_tokens else None)
            await kg.add_paper(title=f"Research Module {idx}", url="", summary=summary, run_id=run_id)
            tm.update(task_id, status="done", output=summary)
            return summary
        context["literature"].extend(await asyncio.gather(*[run_search(i, s) for i, s in enumerate(search_steps)]))
        step_count += len(search_steps)
    for idx, step in enumerate(other_steps):
        if step_count >= max_steps:
            break
        task_id = f"step_exec_{idx}_{step.kind}"
        tm.add(Task(id=task_id, kind=step.kind, input=step.rationale, status="running"))
        if step.kind in ("code", "exec"):
            coder_input = "\n\n".join(context["literature"]) + "\n" + step.rationale
            coder_res = await coder.run_async(coder_input)
            context["code"] = coder_res.get("code", "")
            context["results"] = coder_res.get("results", {})
            tm.update(task_id, status="done", output=coder_res)
            step_count += 1
            if step_count >= max_steps:
                break
            crit_id = f"review_{idx}"
            tm.add(Task(id=crit_id, kind="review", input="Review execution", status="running"))
            critique_input = f"Question: {research_question}\nCode: {context['code']}\nResults: {context['results']}"
            report = await critic.run_async(critique_input)
            tm.update(crit_id, status="done", output=report.model_dump())
            if report.confidence_score < 0.4 and reroutes < 1:
                reroutes += 1
                reroute_id = f"reroute_{idx}"
                tm.add(Task(id=reroute_id, kind="code", input="Fix based on critique", status="running"))
                coder_res = await coder.run_async(coder_input + f"\n\nCRITIQUE:\n{report.weaknesses}\n{report.recommendations}")
                context["code"] = coder_res.get("code", "")
                context["results"] = coder_res.get("results", {})
                tm.update(reroute_id, status="done", output=coder_res)
        step_count += 1
    critique_input = f"Question: {research_question}\nCode: {context['code']}\nResults: {context['results']}"
    final_critique = await critic.run_async(critique_input, stream_callback=on_token if stream_tokens else None)
    debate_rebuttal = await debater.run_async(final_critique)
    revised_input = f"{critique_input}\n\nDebater Rebuttal:\n{debate_rebuttal}"
    original_score = final_critique.confidence_score
    final_critique = await critic.run_async(revised_input, stream_callback=on_token if stream_tokens else None)
    final_critique.confidence_score = (original_score + final_critique.confidence_score) / 2
    rg = ReportGenerator(run_id)
    report_paths = await asyncio.to_thread(rg.build, context, final_critique, debate_rebuttal)
    usage = {k: sum(getattr(a.llm.usage, k, a.llm.usage.get(k, 0)) if isinstance(a.llm.usage, dict) else 0 for a in [planner, researcher, coder, critic, debater]) for k in ["prompt_tokens", "completion_tokens", "cost_estimate"]}
    usage = {k: planner.llm.usage[k] + researcher.llm.usage[k] + coder.llm.usage[k] + critic.llm.usage[k] + debater.llm.usage[k] for k in ["prompt_tokens", "completion_tokens", "cost_estimate"]}
    return {"report_md": report_paths["report_md"], "report_pdf_path": report_paths["report_pdf_path"], "tasks": [t.model_dump() for t in tm.history()], "usage": usage}
```

### `core/report_generator.py`
```python
import os, markdown
from pathlib import Path
try:
    from weasyprint import HTML
except OSError:
    HTML = None

class ReportGenerator:
    def __init__(self, run_id):
        self.run_id = run_id
        base = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        self.run_dir = str(base / run_id)
        os.makedirs(self.run_dir, exist_ok=True)
        self.md_path = os.path.join(self.run_dir, "report.md")
        self.pdf_path = os.path.join(self.run_dir, "report.pdf")

    def build(self, context, critique, debate_rebuttal=""):
        question = context.get("question", "Unknown")
        plan = context.get("plan", [])
        literature = context.get("literature", [])
        code = context.get("code", "")
        results = context.get("results", {})
        md = f"# Autonomous Research Report\n\n## 1. Research Question\n{question}\n\n## 2. Research Plan\n"
        for i, step in enumerate(plan, 1):
            kind = step.get('kind', 'unknown') if isinstance(step, dict) else getattr(step, 'kind', 'unknown')
            rationale = step.get('rationale', '') if isinstance(step, dict) else getattr(step, 'rationale', '')
            md += f"{i}. **{kind.upper()}**: {rationale}\n"
        md += "\n## 3. Literature Synthesis\n"
        for lit in literature:
            md += f"- {lit}\n" if isinstance(lit, str) else f"- **{lit.get('title','Unknown')}**: {lit.get('summary','')}\n"
        md += f"\n## 4. Code & Results\n### Generated Code\n```python\n{code}\n```\n\n### Execution Output\n```\n{results.get('stdout','')}\n```\n"
        if results.get("stderr"):
            md += f"\n### Errors\n```\n{results['stderr']}\n```\n"
        if hasattr(critique, "model_dump"):
            critique = critique.model_dump()
        md += f"\n## 5. Critic Review\n- **Strengths**: {critique.get('strengths','')}\n- **Weaknesses**: {critique.get('weaknesses','')}\n- **Confidence**: {critique.get('confidence_score',0)}\n- **Verdict**: {critique.get('final_verdict','')}\n"
        if debate_rebuttal:
            md += f"\n## 6. Adversarial Debate\n{debate_rebuttal}\n"
        with open(self.md_path, "w", encoding="utf-8") as f:
            f.write(md)
        html_content = markdown.markdown(md)
        if HTML:
            HTML(string=html_content).write_pdf(self.pdf_path)
        else:
            with open(self.pdf_path, "wb") as f:
                f.write(b"PDF generation unavailable: install weasyprint system dependencies.")
        return {"report_md": self.md_path, "report_pdf_path": self.pdf_path}
```

### `agents/base_agent.py`
```python
import asyncio, re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from core.llm_client import LLMClient
from core.tool_registry import ToolRegistry

class ToolCallOrResult(BaseModel):
    done: bool
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    result: Optional[str] = None

class BaseAgent(ABC):
    def __init__(self, name, role, system_prompt, memory=None, tool_registry=None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.llm = LLMClient()
        self.history = []
        self.memory = memory
        self.tool_registry = tool_registry
        self.event_queue = []

    def emit(self, event_type, payload):
        self.event_queue.append({"agent": self.name, "type": event_type, "payload": payload})

    def _create_messages(self, user_content):
        return [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": user_content}]

    @abstractmethod
    async def run_async(self, input_data) -> Any:
        pass

    async def generate_response_async(self, prompt):
        messages = self._create_messages(prompt)
        response = await asyncio.to_thread(self.llm.chat_completion, messages)
        self.history.append({"role": "user", "content": prompt})
        self.history.append({"role": "assistant", "content": response})
        return response

    async def react_loop(self, task, max_iterations=6):
        if not self.tool_registry:
            raise ValueError("No tool registry for ReAct loop.")
        schema_json = self.tool_registry.get_schema_json()
        prompt = f"Task: {task}\nAvailable Tools:\n{schema_json}\nRespond with JSON matching ToolCallOrResult schema."
        messages = self._create_messages(prompt)
        for _ in range(max_iterations):
            parsed = await asyncio.to_thread(self.llm.structured_output, messages, ToolCallOrResult)
            if parsed.done:
                return parsed.result or "Done."
            if parsed.tool:
                try:
                    tool_res = await asyncio.to_thread(self.tool_registry.execute, parsed.tool, parsed.args or {})
                    messages.append({"role": "assistant", "content": f"Called {parsed.tool}"})
                    safe = re.sub(r'(?i)(ignore|disregard).{0,40}(instruction|prompt|above)', '[FILTERED]', str(tool_res)[:8000])
                    messages.append({"role": "user", "content": f"[TOOL_OUTPUT]\n{safe}\n[/TOOL_OUTPUT]"})
                except Exception as e:
                    messages.append({"role": "assistant", "content": f"Called {parsed.tool}"})
                    messages.append({"role": "user", "content": f"Tool Error: {e}"})
            else:
                messages.append({"role": "user", "content": "No tool or result. Please provide one."})
        return "Max iterations reached."
```

### `agents/planner.py`
```python
from typing import List
import asyncio
from pydantic import BaseModel, field_validator, Field
from agents.base_agent import BaseAgent

class PlanStep(BaseModel):
    kind: str = Field(description="One of: search, summarize, code, exec, review")
    rationale: str
    expected_output: str

class Plan(BaseModel):
    steps: List[PlanStep]
    @field_validator('steps')
    @classmethod
    def validate_steps(cls, steps):
        kinds = [s.kind for s in steps]
        valid_kinds = {'search', 'summarize', 'code', 'exec', 'review'}
        for k in kinds:
            if k not in valid_kinds:
                raise ValueError(f"Invalid step kind: {k}")
        if 'search' not in kinds:
            raise ValueError("Plan must contain at least one 'search' step.")
        if 'code' not in kinds:
            raise ValueError("Plan must contain at least one 'code' step.")
        return steps

class Planner(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(name="Planner", role="Senior Research Project Manager",
            system_prompt="You are a Senior Research Project Manager. Decompose the research query into a structured roadmap. Include at least one 'search' step and one 'code' step.",
            memory=memory, tool_registry=tool_registry)

    async def run_async(self, query, kg=None):
        if kg:
            related = kg.query_related(query, k=3)
            brief = "\n".join([f"- Run {r.get('run_id')}: {r.get('title')} - {r.get('summary','')[:200]}" for r in related])
            if brief:
                self.system_prompt += f"\n\nPRIOR RESEARCH (do not repeat, build upon):\n{brief}"
        self.emit("status", f"Generating plan for: {query}")
        plan = await asyncio.to_thread(self.llm.structured_output, self._create_messages(query), Plan)
        self.emit("plan_generated", plan.model_dump())
        return plan
```

### `agents/researcher.py`
```python
from agents.base_agent import BaseAgent
from core.tool_registry import ToolRegistry

class Researcher(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        if tool_registry is None:
            tool_registry = ToolRegistry()
        super().__init__(name="Researcher", role="Academic Librarian and Peer-Reviewer",
            system_prompt="You are a technical researcher. Use search_arxiv to find papers, parse_pdf to read them, and web_search as a fallback. When done, set done=true and provide the final summary in the result field.",
            memory=memory, tool_registry=tool_registry)

    async def run_async(self, query, stream_callback=None):
        self.emit("status", f"Starting ReAct research loop for: {query}")
        result = await self.react_loop(query, max_iterations=4)
        if stream_callback:
            messages = self._create_messages(f"Provide a cohesive final narrative of this research context: {result}")
            final_summary = ""
            async for token in self.llm.stream_completion_async(messages):
                stream_callback("Researcher", token)
                final_summary += token
            result = final_summary
        if self.memory:
            self.memory.add(texts=[result], metadatas=[{"source": "researcher_react", "query": query}])
        return result
```

### `agents/coder.py`
```python
from typing import Dict, Any
import asyncio
from agents.base_agent import BaseAgent
from core.tool_registry import ToolRegistry

class Coder(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(name="Coder", role="Research Software Engineer",
            system_prompt="You are a specialist in writing reproducible research experiments. Write a COMPLETE Python script. Output ONLY raw code. Start with `import sys, json, time` and print all final results.",
            memory=memory, tool_registry=tool_registry)

    async def run_async(self, research_summary):
        prompt = f"Translate these research insights into a Python experiment.\nInsights:\n{research_summary}"
        self.emit("status", "Writing Python experiment code")
        registry = self.tool_registry or ToolRegistry()
        for attempt in range(2):
            code = await self.generate_response_async(prompt)
            code = self._clean_code(code)
            if "import sys" not in code:
                code = "import sys, json, time\n" + code
            self.emit("status", "Executing code in sandbox")
            results = await asyncio.to_thread(registry.execute, "run_python_code", {"code": code})
            if results["exit_code"] != 0 and "ModuleNotFoundError" in results.get("stderr", ""):
                if attempt == 0:
                    self.emit("status", "ImportError detected. Retrying.")
                    prompt += f"\n\nPrevious attempt failed:\n{results['stderr']}\nRewrite to NOT use the missing module."
                    continue
            break
        return {"code": code, "results": results}

    def _clean_code(self, code):
        code = code.strip()
        if "```" in code:
            lines, clean_lines, in_block = code.split('\n'), [], False
            for line in lines:
                if line.startswith("```"):
                    in_block = not in_block
                    continue
                if in_block:
                    clean_lines.append(line)
            return '\n'.join(clean_lines) if clean_lines else code
        return code
```

### `agents/critic.py`
```python
from typing import Any
import asyncio
from pydantic import BaseModel, Field
from agents.base_agent import BaseAgent

class CriticReport(BaseModel):
    strengths: str
    weaknesses: str
    bias_check: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    recommendations: str
    final_verdict: str

class Critic(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(name="Critic", role="Scientific Critic",
            system_prompt="You are a Scientific Critic. Evaluate whether the code results align with the initial research goal. Identify biases, errors, and areas for further iteration.",
            memory=memory, tool_registry=tool_registry)

    async def run_async(self, context_summary, stream_callback=None):
        self.emit("status", "Critiquing execution and results.")
        prompt = f"Evaluate this research context and code execution results:\n\n{context_summary}"
        if stream_callback:
            messages = self._create_messages(prompt + "\nProvide your final verdict clearly.")
            verdict = ""
            async for token in self.llm.stream_completion_async(messages):
                stream_callback("Critic", token)
                verdict += token
            messages.append({"role": "assistant", "content": verdict})
            messages.append({"role": "user", "content": "Now map your evaluation into the required JSON schema."})
            report = await asyncio.to_thread(self.llm.structured_output, messages, CriticReport)
            report.final_verdict = verdict
        else:
            messages = self._create_messages(prompt)
            report = await asyncio.to_thread(self.llm.structured_output, messages, CriticReport)
        self.emit("review_generated", report.model_dump())
        return report
```

### `agents/debater.py`
```python
from agents.base_agent import BaseAgent
from agents.critic import CriticReport

class Debater(BaseAgent):
    def __init__(self, memory=None, tool_registry=None):
        super().__init__(name="Debater", role="Scientific Adversary",
            system_prompt="You are a rigorous scientific adversary. Find logical flaws, unsupported conclusions, and overlooked alternative explanations in the Critic's reasoning. Be specific.",
            memory=memory, tool_registry=tool_registry)

    async def run_async(self, critic_report: CriticReport) -> str:
        self.emit("status", "Debating the Critic's review.")
        prompt = f"Critic Review:\n{critic_report.model_dump_json(indent=2)}"
        return await self.generate_response_async(prompt)
```

### `tools/arxiv_search.py`
```python
import arxiv
from pydantic import BaseModel
from typing import List

class ArxivPaper(BaseModel):
    id: str; title: str; authors: List[str]; abstract: str; pdf_url: str; published: str

def search_arxiv(query: str, max_results: int = 5) -> List[ArxivPaper]:
    try:
        client = arxiv.Client()
        search = arxiv.Search(query=query, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance)
        return [ArxivPaper(id=r.get_short_id(), title=r.title, authors=[a.name for a in r.authors], abstract=r.summary, pdf_url=r.pdf_url, published=str(r.published)) for r in client.results(search)]
    except Exception as e:
        print(f"arXiv search error: {e}")
        return []
```

### `tools/web_search.py`
```python
import os
from typing import List, Dict

def web_search(query: str, k: int = 5) -> List[Dict[str, str]]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if tavily_key:
        try:
            from tavily import TavilyClient
            return TavilyClient(api_key=tavily_key).search(query, max_results=k).get("results", [])
        except Exception as e:
            print(f"Tavily error: {e}")
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [{"title": r.get("title",""), "content": r.get("body",""), "url": r.get("href","")} for r in ddgs.text(query, max_results=k)]
    except Exception as e:
        print(f"DDG error: {e}")
        return []
```

### `tools/paper_parser.py`
```python
import io, requests
from typing import Dict, Any, List
from pypdf import PdfReader
from pydantic import BaseModel

class ParsedPaper(BaseModel):
    text: str; chunks: List[str]; metadata: Dict[str, Any]

def parse_pdf(url_or_path: str) -> ParsedPaper:
    try:
        if url_or_path.startswith("http"):
            if not url_or_path.startswith("https://arxiv.org/pdf/"):
                raise ValueError(f"Blocked SSRF: {url_or_path}")
            response = requests.get(url_or_path, timeout=30)
            response.raise_for_status()
            if "pdf" not in response.headers.get("content-type","").lower():
                raise ValueError("Not a PDF")
            if len(response.content) > 50 * 1024 * 1024:
                raise ValueError("PDF too large")
            f = io.BytesIO(response.content)
        else:
            from pathlib import Path
            f = open(Path(url_or_path).resolve(), "rb")
        reader = PdfReader(f)
        text = "".join(p.extract_text() + "\n" for p in reader.pages if p.extract_text())
        if not text.strip():
            from pdfminer.high_level import extract_text as pdfminer_extract
            f.seek(0)
            text = pdfminer_extract(f)
        return ParsedPaper(text=text, chunks=[text[i:i+1000] for i in range(0, len(text), 1000)], metadata={"source": url_or_path})
    except Exception as e:
        return ParsedPaper(text=f"Error: {e}", chunks=[], metadata={"error": str(e)})
```

### `tools/code_executor.py`
```python
import tempfile, time, shutil, docker
from pathlib import Path
from typing import Optional, Dict, Any

class PythonExecutor:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
        except Exception as e:
            raise RuntimeError(f"[PythonExecutor] Docker unavailable: {e}") from e

    def execute(self, code: str, timeout: int = 120, work_dir: Optional[Path] = None) -> Dict[str, Any]:
        tmpdir = tempfile.mkdtemp()
        start_time = time.time()
        try:
            script_path = Path(tmpdir) / "experiment.py"
            script_path.write_text(code)
            container = self.client.containers.run(
                image="python:3.11-slim",
                command=["python", "/code/experiment.py"],
                volumes={tmpdir: {"bind": "/code", "mode": "ro"}},
                network_disabled=True, mem_limit="512m",
                cpu_period=100000, cpu_quota=50000,
                remove=False, stdout=True, stderr=True, detach=True
            )
            try:
                result = container.wait(timeout=timeout)
                exit_code = result["StatusCode"]
                stdout_data = container.logs(stdout=True, stderr=False).decode("utf-8")
                stderr_data = container.logs(stdout=False, stderr=True).decode("utf-8")
            except Exception:
                container.kill()
                raise
            finally:
                container.remove(force=True)
            return {"stdout": stdout_data, "stderr": stderr_data, "exit_code": exit_code, "runtime": time.time()-start_time, "artifacts": [str(p) for p in Path(tmpdir).iterdir() if p.name != "experiment.py" and p.is_file()]}
        except Exception as e:
            return {"stdout": "", "stderr": str(e), "exit_code": -1, "runtime": time.time()-start_time, "artifacts": []}
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
```

### `memory/embeddings.py`
```python
import os
import numpy as np

def embed(texts) -> np.ndarray:
    was_single = isinstance(texts, str)
    if was_single:
        texts = [texts]
    result = None
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        try:
            import openai
            response = openai.OpenAI(api_key=api_key).embeddings.create(input=texts, model="text-embedding-3-small")
            result = np.array([d.embedding for d in response.data])
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
    if result is None:
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(embed, "_model"):
                embed._model = SentenceTransformer("all-MiniLM-L6-v2")
            result = embed._model.encode(texts)
        except Exception as e:
            print(f"SentenceTransformer error: {e}")
            result = np.zeros((len(texts), 384))
    return result[0] if was_single else result
```

### `memory/vector_store.py`
```python
import os, uuid
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel

class Hit(BaseModel):
    id: str; text: str; metadata: Dict[str, Any]; score: float

class VectorStore:
    def __init__(self, run_id):
        self.run_id = run_id
        self.backend = os.getenv("VECTOR_BACKEND", "chroma")
        if self.backend == "chroma":
            import chromadb
            run_chroma_dir = Path(os.getenv("RUNS_DIR", "./runs")).resolve() / run_id / "chroma"
            run_chroma_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(run_chroma_dir))
            self.collection = self.client.get_or_create_collection("research_context")
            self.global_collection = self.client.get_or_create_collection("global_knowledge")
        elif self.backend == "pinecone":
            from pinecone import Pinecone, ServerlessSpec
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            index_name = os.getenv("PINECONE_INDEX", "research-context")
            if index_name not in [i.name for i in pc.list_indexes()]:
                pc.create_index(name=index_name, dimension=1536, metric="cosine", spec=ServerlessSpec(cloud="aws", region="us-east-1"))
            self.index = pc.Index(index_name)

    def add(self, texts, metadatas, ids=None):
        if not texts: return
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
        if self.backend == "chroma":
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
            self.global_collection.add(documents=texts, metadatas=metadatas, ids=ids)
        elif self.backend == "pinecone":
            from memory.embeddings import embed
            embeddings = [embed(t) for t in texts]
            self.index.upsert([{"id": id_, "values": emb.tolist(), "metadata": {**meta, "text": text}} for id_, emb, meta, text in zip(ids, embeddings, metadatas, texts)])

    def query(self, text, k=5):
        if self.backend == "chroma":
            results = self.collection.query(query_texts=[text], n_results=k)
            hits = []
            if results and results.get("documents") and results["documents"][0]:
                for d, m, dist, id_ in zip(results["documents"][0], results["metadatas"][0], results.get("distances", [[0]*k])[0], results["ids"][0]):
                    hits.append(Hit(id=id_, text=d, metadata=m or {}, score=dist))
            return hits
        elif self.backend == "pinecone":
            from memory.embeddings import embed
            response = self.index.query(vector=embed(text).tolist(), top_k=k, include_metadata=True)
            return [Hit(id=m.id, text=m.metadata.get("text",""), metadata=m.metadata, score=m.score) for m in response.matches]
        return []
```

### `memory/knowledge_graph.py`
```python
import os, json, uuid
import asyncio
import networkx as nx
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
from memory.embeddings import embed

class KnowledgeGraph:
    def __init__(self):
        base_dir = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        self.graph_path = base_dir / "global_graph.json"
        self.graph = nx.node_link_graph(json.loads(self.graph_path.read_text())) if self.graph_path.exists() else nx.DiGraph()

    def save(self):
        self.graph_path.write_text(json.dumps(nx.node_link_data(self.graph)))

    async def add_paper(self, title, url, summary, run_id):
        if not summary: return
        node_id = url if url else str(uuid.uuid4())
        new_emb = await asyncio.to_thread(embed, summary)
        def cosine_sim(a, b):
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
        self.graph.add_node(node_id, title=title, url=url, summary=summary, run_id=run_id, embedding=new_emb.tolist())
        for other_id, other_data in list(self.graph.nodes(data=True)):
            if other_id == node_id or "embedding" not in other_data: continue
            score = cosine_sim(new_emb, np.array(other_data["embedding"]))
            if score > 0.75:
                self.graph.add_edge(node_id, other_id, weight=score)
                self.graph.add_edge(other_id, node_id, weight=score)
        await asyncio.to_thread(self.save)

    def query_related(self, text, k=5):
        query_emb = embed(text)
        def cosine_sim(a, b):
            return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10))
        scores = []
        for node_id, data in self.graph.nodes(data=True):
            if "embedding" in data:
                scores.append((cosine_sim(query_emb, np.array(data["embedding"])), node_id, data))
        scores.sort(reverse=True)
        results = []
        for score, node_id, data in scores[:k]:
            out = {k: v for k, v in data.items() if k != "embedding"}
            out["similarity"] = score
            results.append(out)
        return results
```

### `api/server.py`
```python
import asyncio, os, uuid
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from pathlib import Path
from core.agent_loop import run_agent_async

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
active_queues: Dict[str, asyncio.Queue] = {}

async def verify_api_key(request: Request):
    expected_key = os.getenv("INTERNAL_API_KEY")
    if expected_key:
        if request.headers.get("X-API-Key") != expected_key:
            raise HTTPException(status_code=401, detail="Unauthorized")

class ResearchRequest(BaseModel):
    question: str

@app.post("/api/research", status_code=202)
async def start_research(req: ResearchRequest, request: Request):
    await verify_api_key(request)
    run_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    active_queues[run_id] = queue
    def on_event(task):
        try:
            queue.put_nowait({"type": "task_update", "task": task})
        except Exception:
            pass
    def on_token(agent, delta):
        try:
            queue.put_nowait({"type": "token", "agent": agent, "delta": delta})
        except Exception:
            pass
    async def run_task():
        try:
            result = await run_agent_async(req.question, run_id=run_id, on_event=on_event, on_token=on_token, stream_tokens=True)
            await queue.put({"type": "done", "result": result})
        except Exception as e:
            await queue.put({"type": "error", "error": str(e)})
    asyncio.create_task(run_task())
    return {"run_id": run_id}

@app.websocket("/api/research/{run_id}/stream")
async def stream_research(websocket: WebSocket, run_id: str):
    await websocket.accept()
    if run_id not in active_queues:
        await websocket.close(code=1008, reason="Run ID not found")
        return
    queue = active_queues[run_id]
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
            if event["type"] in ["done", "error"]:
                break
    except WebSocketDisconnect:
        pass
    finally:
        active_queues.pop(run_id, None)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/research/{run_id}/report")
async def get_report(run_id: str, request: Request):
    await verify_api_key(request)
    report_path = Path(os.getenv("RUNS_DIR", "./runs")).resolve() / run_id / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(content=report_path.read_text(encoding="utf-8"), media_type="text/markdown")
```

### `ui/app.py`
```python
import streamlit as st
import os, sys, json, asyncio, websockets, httpx
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ui.components import agent_card

st.set_page_config(layout="wide", page_title="Autonomous AI Researcher")
st.title("Autonomous AI Researcher 🔬🤖")
if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    st.header("Control Panel")
    question = st.text_area("Research Question", "Analyze the impact of different activation functions on Transformer convergence speed.")
    if st.button("Run Research", type="primary"):
        st.session_state.running = True
        st.session_state.result = None
        st.session_state.tasks = []
        st.session_state.buffers = {}
        try:
            resp = httpx.post("http://localhost:8000/api/research", json={"question": question})
            resp.raise_for_status()
            st.session_state.run_id = resp.json()["run_id"]
        except Exception as e:
            st.error(f"Failed to start run: {e}")
            st.session_state.running = False
    st.header("Related Past Research")
    if st.button("Load Knowledge Graph"):
        try:
            from memory.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            related = kg.query_related(question, k=3)
            if not related:
                st.info("No prior related research found.")
            else:
                for r in related:
                    st.markdown(f"**Run [{r.get('run_id')}]**\n\n*Summary*: {r.get('summary','')[:100]}...\n\n*Sim*: {r.get('similarity', 0):.2f}")
        except Exception as e:
            st.error(f"Knowledge graph unavailable: {e}")

with col2:
    st.header("Live Agent Activity")
    feed_container = st.empty()
    token_container = st.empty()
    if getattr(st.session_state, "running", False) and "run_id" in st.session_state:
        run_id = st.session_state.run_id
        async def stream_ws():
            uri = f"ws://localhost:8000/api/research/{run_id}/stream"
            try:
                async with websockets.connect(uri) as ws:
                    while True:
                        msg = await ws.recv()
                        data = json.loads(msg)
                        if data["type"] == "task_update":
                            st.session_state.tasks.append(data["task"])
                            with feed_container.container():
                                for t in st.session_state.tasks[-10:]:
                                    st.info(f"**[{t.get('status','?').upper()}]** {t.get('kind','?')}: {str(t.get('input',''))[:100]}...")
                        elif data["type"] == "token":
                            agent = data["agent"]
                            delta = data["delta"]
                            if "buffers" not in st.session_state:
                                st.session_state.buffers = {}
                            st.session_state.buffers[agent] = st.session_state.buffers.get(agent, "") + delta
                            with token_container.container():
                                st.markdown(f"**{agent} (streaming...)**\n{st.session_state.buffers[agent]} ▌")
                        elif data["type"] == "done":
                            st.session_state.result = data["result"]
                            st.session_state.running = False
                            st.rerun()
                            break
            except Exception as e:
                st.error(f"WebSocket Error: {e}")
                st.session_state.running = False
        asyncio.run(stream_ws())
    else:
        with feed_container.container():
            for t in st.session_state.tasks[-10:]:
                st.info(f"**[{t.get('status','?').upper()}]** {t.get('kind','?')}: {str(t.get('input',''))[:100]}...")

with col3:
    st.header("Report")
    res = getattr(st.session_state, "result", None)
    if res:
        st.success(f"Cost Estimate: ${res['usage']['cost_estimate']:.3f}")
        md_path = res.get("report_md")
        pdf_path = res.get("report_pdf_path")
        if md_path and os.path.exists(md_path):
            with open(md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
            st.download_button("Download Markdown", md_content, "report.md", "text/markdown")
            with st.expander("Preview Markdown", expanded=True):
                st.markdown(md_content)
        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            st.download_button("Download PDF", pdf_bytes, "report.pdf", "application/pdf")
```

### `ui/components.py`
```python
import streamlit as st, html

def agent_card(name, role, status, tokens, cost):
    st.markdown(f"""
    <div style="border:1px solid #ddd;padding:10px;border-radius:5px;margin-bottom:10px;">
        <h4>{html.escape(str(name))} <small style="color:gray;">({html.escape(str(role))})</small></h4>
        <p><b>Status:</b> {html.escape(str(status))}</p>
        <p style="font-size:0.8em;color:gray;">Tokens: {tokens} | Cost: ${cost:.3f}</p>
    </div>""", unsafe_allow_html=True)
```

### `tests/test_agent_loop.py`
```python
import pytest, asyncio
from core.agent_loop import run_agent_async

def mock_chat_completion(self, messages, *args, **kwargs):
    system = messages[0]["content"] if messages else ""
    if "Project Manager" in system:
        return '{"steps": [{"kind": "search", "rationale": "Find papers", "expected_output": "list"}, {"kind": "code", "rationale": "Write test", "expected_output": "results"}]}'
    elif "Critic" in system:
        return '{"strengths": "ok", "weaknesses": "none", "bias_check": "none", "confidence_score": 0.9, "recommendations": "none", "final_verdict": "good"}'
    return '{"done": true, "result": "mock result"}'

@pytest.fixture
def mock_llm(mocker):
    mocker.patch("core.llm_client.LLMClient.chat_completion", new=mock_chat_completion)

def test_run_agent(mock_llm, mocker, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", "./runs")
    mocker.patch("tools.arxiv_search.search_arxiv", return_value=[])
    mocker.patch("tools.web_search.web_search", return_value=[{"title": "Test", "content": "Text", "url": "http://test"}])
    mocker.patch("tools.code_executor.PythonExecutor.execute", return_value={"stdout": "hello", "stderr": "", "exit_code": 0, "runtime": 0.1, "artifacts": []})
    mocker.patch("memory.embeddings.embed", return_value=__import__('numpy').zeros(384))
    result = asyncio.run(run_agent_async("Test question"))
    assert "report_md" in result
    assert "report_pdf_path" in result
    assert "tasks" in result
    assert "usage" in result
```

### `.env.example`
```
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
TAVILY_API_KEY=your_tavily_api_key_here
PINECONE_API_KEY=your_key
PINECONE_INDEX=research-context
VECTOR_BACKEND=chroma
MAX_STEPS=12
RUNS_DIR=./runs
INTERNAL_API_KEY=
```

### `Dockerfile`
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 libcairo2 curl docker.io \
    && rm -rf /var/lib/apt/lists/*
RUN useradd -m appuser && usermod -aG docker appuser
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN pip install -e .
RUN chown -R appuser /app
USER appuser
EXPOSE 8501 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl --fail http://localhost:8000/health || exit 1
CMD ["sh", "-c", "uvicorn api.server:app --host 0.0.0.0 --port 8000 & streamlit run ui/app.py --server.address=0.0.0.0"]
```

### `docker-compose.yml`
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
      - "8000:8000"
    volumes:
      - ./runs:/app/runs
      - /var/run/docker.sock:/var/run/docker.sock
    env_file:
      - .env
    environment:
      - RUNS_DIR=/app/runs
    mem_limit: 4g
    cpus: 2.0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### `requirements.txt`
```
openai==1.14.0
anthropic==0.21.3
streamlit==1.32.2
arxiv==2.1.0
feedparser==6.0.10
pypdf==4.1.0
pdfminer.six==20231228
chromadb==0.4.24
sentence-transformers==2.5.1
pydantic>=2.6.3
python-dotenv==1.0.1
tenacity==8.2.3
rich==13.7.1
weasyprint==61.0
duckduckgo-search==5.0.0
tavily-python==0.3.3
pytest==8.1.1
pytest-mock==3.14.0
numpy==1.26.4
fastapi>=0.111.0
uvicorn[standard]>=0.29.0
httpx>=0.27.0
websockets>=12.0
docker>=7.0.0
networkx>=3.3
pinecone-client>=3.0.0
markdown>=3.6
```

---

## 3. COMPREHENSIVE BUG REPORT

Fix **every** bug listed below. Each entry includes the exact file, the problem, and the required fix.

### BUG-01 — `api/server.py`: Task object not JSON-serializable (CRITICAL)
**File:** `api/server.py`, `on_event` callback inside `start_research`
**Problem:** `TaskManager._notify` calls `cb(task)` where `task` is a `Task` Pydantic model object. The `on_event` function puts it directly into an `asyncio.Queue` and later `websocket.send_json(event)` tries to serialize it — but Pydantic models are **not** natively JSON-serializable via `json.dumps`. This causes a `TypeError` on every task update broadcast.
**Fix:** Change `queue.put_nowait({"type": "task_update", "task": task})` to `queue.put_nowait({"type": "task_update", "task": task.model_dump()})`.

### BUG-02 — `api/api_server.py`: Dead duplicate file (CLEANUP)
**File:** `api/api_server.py`
**Problem:** This file is an exact duplicate of `api/server.py`. The `Dockerfile` references `api.server:app`. The duplicate is dead code that will cause confusion during imports.
**Fix:** Delete `api/api_server.py` entirely.

### BUG-03 — `core/base_agent.py` (old file): Stale duplicate causing import confusion (CLEANUP)
**File:** `core/base_agent.py`
**Problem:** This is an older, incomplete version of the base agent (missing `run_async`, `react_loop`, `generate_response_async`). It shadows the correct `agents/base_agent.py`. Any code that accidentally imports `from core.base_agent import BaseAgent` will get the wrong class.
**Fix:** Delete `core/base_agent.py` entirely and confirm all agents import from `agents.base_agent`.

### BUG-04 — `memory/knowledge_graph.py`: `asyncio.Lock` created outside event loop (RUNTIME ERROR)
**File:** `memory/knowledge_graph.py`, `__init__` method
**Problem:** The original code creates `self._lock = asyncio.Lock()` at init time. In Python 3.10+, `asyncio.Lock()` must be created inside a running event loop. `KnowledgeGraph()` is instantiated synchronously inside `run_agent_async` before any `await`, causing a `DeprecationWarning` or `RuntimeError` depending on Python version. Additionally, the fixed version (in the source above) removed the lock but `add_paper` is `async` and calls `asyncio.to_thread(self.save)` — there is still a potential race condition on simultaneous writes.
**Fix:** Remove `asyncio.Lock` from `__init__`. Protect `add_paper` with a module-level `asyncio.Lock` created lazily inside the coroutine: add a class attribute `_lock: Optional[asyncio.Lock] = None` and inside `add_paper` do `if self._lock is None: self._lock = asyncio.Lock()` then `async with self._lock:` for the write section.

### BUG-05 — `ui/app.py`: `asyncio.run()` conflict with Streamlit's event loop (CRITICAL)
**File:** `ui/app.py`, the `stream_ws` coroutine call
**Problem:** Streamlit 1.32+ runs inside a thread that may already have an event loop. Calling `asyncio.run(stream_ws())` raises `RuntimeError: This event loop is already running` in many environments. The WebSocket streaming loop also **blocks** the Streamlit render thread indefinitely, freezing the UI.
**Fix:** Replace `asyncio.run(stream_ws())` with polling via `httpx` against the REST endpoint + Streamlit's `st.rerun()` with a short sleep, OR use `nest_asyncio` to allow nested event loops. The recommended fix that requires zero new dependencies: install and apply `nest_asyncio` at the top of `app.py`:
```python
import nest_asyncio
nest_asyncio.apply()
```
Then wrap the call: `asyncio.get_event_loop().run_until_complete(stream_ws())`. Add `nest_asyncio` to `requirements.txt`.

### BUG-06 — `core/task_manager.py`: `RUNS_DIR` default is `/app/runs` (LOCAL DEV BREAKAGE)
**File:** `core/task_manager.py` and `core/report_generator.py`
**Problem:** The hardcoded default `RUNS_DIR = "/app/runs"` only works inside the Docker container. Local developers running `streamlit run ui/app.py` directly get a `PermissionError` trying to create `/app/runs`.
**Fix:** Change the default in both files from `"/app/runs"` to `"./runs"`. The current source code already shows `"./runs"` — verify this is consistent everywhere and is NOT overridden to `/app/runs` in any non-Docker path. The `docker-compose.yml` correctly sets `RUNS_DIR=/app/runs` as an env override, so Docker will still use `/app/runs`.

### BUG-07 — `tools/code_executor.py`: Docker image has no scientific Python packages (FUNCTIONAL GAP)
**File:** `tools/code_executor.py`, the `execute` method
**Problem:** The sandbox image is `python:3.11-slim` which has **no** numpy, pandas, matplotlib, scipy, or torch. The Coder agent's generated scripts almost always import numpy. The single ImportError retry in `coder.py` is insufficient — the retry just asks the LLM to rewrite without the module, which defeats the purpose of scientific experimentation.
**Fix:** Either (a) pre-build a custom Docker image `researcher-sandbox:latest` with `numpy pandas matplotlib scipy` installed and reference it in `code_executor.py`, or (b) add a `pip install` command before running the script. Option (b) is simpler for portability:
```python
command=["sh", "-c", "pip install numpy pandas matplotlib scipy --quiet && python /code/experiment.py"],
```
Remove `network_disabled=True` or scope it to only apply after the pip install completes. Update the `execute` method signature and logic accordingly.

### BUG-08 — `core/agent_loop.py`: `usage` dict aggregation duplicated/broken (LOGIC ERROR)
**File:** `core/agent_loop.py`, the `usage` dict at the end of `run_agent_async`
**Problem:** The usage aggregation code appears twice — once with a broken dict comprehension using `getattr` that will always return 0, and once with the correct version. The first (broken) version overwrites nothing because of assignment order, but the code is confusing and will break if refactored.
**Fix:** Remove the broken first `usage = {...}` line. Keep only the correct version:
```python
usage = {k: planner.llm.usage[k] + researcher.llm.usage[k] + coder.llm.usage[k] + critic.llm.usage[k] + debater.llm.usage[k] for k in ["prompt_tokens", "completion_tokens", "cost_estimate"]}
```

### BUG-09 — `memory/knowledge_graph.py`: Embedding stored as list but compared as ndarray (TYPE ERROR)
**File:** `memory/knowledge_graph.py`, `add_paper` and `query_related`
**Problem:** In `add_paper`, the embedding is stored as `embedding=new_emb.tolist()` (a Python list) for JSON serializability. In `query_related`, the code does `cosine_sim(query_emb, np.array(other_data["embedding"]))` — this is correct. But `add_paper` was calling `cosine_sim(new_emb, other_data["embedding"])` in the original (un-fixed) code without the `np.array()` wrap, which would fail for list inputs. The fixed source above already wraps it — **verify** this is present and consistent in both methods.
**Fix:** Confirm `np.array(other_data["embedding"])` is used in both `add_paper` (inner loop) and `query_related`.

### BUG-10 — `ui/app.py` + `api/server.py`: CORS allows all origins (SECURITY)
**File:** `api/server.py`, `CORSMiddleware`
**Problem:** `allow_origins=["*"]` with `allow_credentials=True` is explicitly disallowed by the CORS spec and will be rejected by browsers for credentialed requests. It also exposes the API to any origin.
**Fix:** Change to `allow_origins=["http://localhost:8501"]` for local dev, or make it configurable via `ALLOWED_ORIGINS` env var: `allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(",")`.

### BUG-11 — `agents/coder.py`: `Coder` has no `run` method (ABSTRACT METHOD VIOLATION)
**File:** `agents/coder.py`
**Problem:** `BaseAgent` declares `run_async` as abstract (`@abstractmethod`). `Coder` implements `run_async` — this is fine. But the old `core/base_agent.py` declared `run` as abstract. If any code still imports `core/base_agent.BaseAgent` and tries to instantiate `Coder`, it will raise `TypeError: Can't instantiate abstract class Coder`. This is resolved by BUG-03, but must be verified.
**Fix:** Confirm BUG-03 is applied first. After deletion of `core/base_agent.py`, run a grep to confirm no module imports `from core.base_agent import BaseAgent`.

### BUG-12 — `memory/vector_store.py`: Pinecone `.tolist()` missing in add (TYPE ERROR)
**File:** `memory/vector_store.py`, `add` method, Pinecone branch
**Problem:** `embeddings = [embed(t) for t in texts]` returns numpy arrays. Pinecone's `upsert` requires plain Python lists for vector values. The line `self.index.upsert([{"id": id_, "values": emb.tolist(), ...}])` has `.tolist()` in the current source — **verify it is present**.
**Fix:** Confirm `.tolist()` is called on each embedding before passing to Pinecone upsert.

### BUG-13 — Missing `__init__.py` in `api/` package
**File:** `api/__init__.py`
**Problem:** Although the file exists, verify it is not accidentally importing from the deleted `api_server.py`.
**Fix:** Ensure `api/__init__.py` is empty or only contains `# api package`.

---

## 4. COMPLETE FUNCTIONALITY SPECIFICATION

Every feature listed here must be fully implemented, wired, and tested.

### 4.1 Backend API (`api/server.py` on port 8000)

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Returns `{"status": "ok"}`. Used by Docker healthcheck. |
| `/api/research` | POST | Accepts `{"question": str}`. Spawns async research task. Returns `{"run_id": uuid}` with HTTP 202. |
| `/api/research/{run_id}/stream` | WebSocket | Streams events: `task_update`, `token`, `done`, `error` until research completes. |
| `/api/research/{run_id}/report` | GET | Returns the Markdown report for a completed run. |

**Event schema for WebSocket messages:**
- `{"type": "task_update", "task": {id, kind, status, input, output, created_at, finished_at}}` — emitted on every task state change
- `{"type": "token", "agent": str, "delta": str}` — emitted on each streamed token from Critic/Researcher
- `{"type": "done", "result": {report_md, report_pdf_path, tasks, usage}}` — emitted when the run completes
- `{"type": "error", "error": str}` — emitted if the run raises an exception

### 4.2 Orchestration Loop (`core/agent_loop.py`)

The `run_agent_async` function must:
1. Create a `TaskManager` and subscribe the `on_event` callback.
2. Instantiate `VectorStore`, `KnowledgeGraph`, `ToolRegistry`, and all five agents (Planner, Researcher, Coder, Critic, Debater).
3. Run `Planner.run_async(question, kg=kg)` → `Plan`.
4. Run all `search`/`summarize` plan steps **in parallel** with `asyncio.gather`.
5. Run `code`/`exec` plan steps sequentially, immediately followed by a `Critic` review.
6. If `CriticReport.confidence_score < 0.4`, re-run the Coder once with the critique appended (max 1 reroute per step).
7. Run final `Critic` review → `Debater` rebuttal → second `Critic` pass (averaged score).
8. Call `ReportGenerator.build(context, final_critique, debate_rebuttal)`.
9. Return `{report_md, report_pdf_path, tasks, usage}`.

### 4.3 Agent Pipeline

| Agent | Input | Output | LLM mode |
|---|---|---|---|
| Planner | Research question + prior KG context | `Plan` (Pydantic, structured JSON) | structured_output |
| Researcher | Query string | Plain text summary | react_loop (up to 4 iters) + optional stream |
| Coder | Research summary string | `{code: str, results: dict}` | generate_response_async + Docker exec |
| Critic | Context summary string | `CriticReport` (Pydantic) | structured_output + optional stream |
| Debater | `CriticReport` object | Plain text rebuttal | generate_response_async |

### 4.4 Tool Suite (`tools/`)

| Tool | Function signature | Description |
|---|---|---|
| `search_arxiv` | `(query: str, max_results: int = 5) -> List[ArxivPaper]` | arXiv API search |
| `web_search` | `(query: str, k: int = 5) -> List[Dict]` | Tavily → DuckDuckGo fallback |
| `parse_pdf` | `(url_or_path: str) -> ParsedPaper` | pypdf + pdfminer.six fallback |
| `run_python_code` | `(code: str) -> Dict` | Docker sandbox with stdout/stderr/exit_code |

### 4.5 Memory System

**VectorStore** (`memory/vector_store.py`):
- Backend selected by `VECTOR_BACKEND` env var (`chroma` default, `pinecone` optional).
- ChromaDB: persistent at `{RUNS_DIR}/{run_id}/chroma/`.
- Pinecone: uses `PINECONE_API_KEY` + `PINECONE_INDEX`.
- Methods: `add(texts, metadatas, ids?)`, `query(text, k=5) -> List[Hit]`.

**KnowledgeGraph** (`memory/knowledge_graph.py`):
- NetworkX DiGraph, saved as JSON at `{RUNS_DIR}/global_graph.json`.
- Adds nodes with embeddings; connects nodes with cosine similarity > 0.75.
- Methods: `add_paper(title, url, summary, run_id)` (async), `query_related(text, k=5)` (sync).

### 4.6 Frontend UI (`ui/app.py` on port 8501)

Three-column Streamlit layout:

**Column 1 — Control Panel:**
- `st.text_area` for research question input.
- "Run Research" button → POST to `/api/research` → store `run_id` in `st.session_state`.
- "Load Knowledge Graph" button → shows prior related research from the KG.

**Column 2 — Live Agent Activity:**
- `st.empty()` container refreshed by WebSocket events.
- Shows last 10 task updates as `st.info()` cards.
- Shows streaming token output for Researcher and Critic agents.

**Column 3 — Report:**
- Shows cost estimate on completion.
- `st.download_button` for Markdown report.
- `st.download_button` for PDF report.
- `st.expander` preview of the Markdown report.

### 4.7 Report (`core/report_generator.py`)

Output sections in order:
1. Research Question
2. Research Plan (numbered steps with kind + rationale)
3. Literature Synthesis (bullet list)
4. Code & Results (fenced Python block + stdout + stderr if any)
5. Critic Review (strengths, weaknesses, confidence score, final verdict)
6. Adversarial Debate (debater rebuttal)

Both `.md` and `.pdf` saved to `{RUNS_DIR}/{run_id}/`.

---

## 5. FRONTEND ↔ BACKEND WIRING MAP

This section describes **exactly** how the Streamlit frontend communicates with the FastAPI backend. Fix any broken wire.

```
[User clicks "Run Research" in Streamlit]
    │
    ▼
httpx.post("http://localhost:8000/api/research", json={"question": question})
    │   HTTP 202 + {"run_id": "uuid"}
    ▼
st.session_state.run_id = run_id
st.session_state.running = True
    │
    ▼
[Streamlit re-renders → enters WebSocket streaming block]
    │
    ▼
websockets.connect("ws://localhost:8000/api/research/{run_id}/stream")
    │
    │   ←── FastAPI server spawns asyncio.create_task(run_task())
    │   ←── run_task() calls run_agent_async(question, run_id, on_event, on_token)
    │   ←── TaskManager._notify(task) → on_event(task) → queue.put_nowait({type: task_update, task: task.model_dump()})
    │   ←── LLMClient.stream_completion_async → on_token(agent, delta) → queue.put_nowait({type: token, ...})
    │   ←── When done: queue.put_nowait({type: done, result: {...}})
    │
    ▼ [WebSocket receives each event]
    │
    ├── type == "task_update" → append to st.session_state.tasks → update feed_container
    ├── type == "token" → append to st.session_state.buffers[agent] → update token_container
    └── type == "done" → st.session_state.result = data["result"] → st.session_state.running = False → st.rerun()

[After st.rerun(), Column 3 renders the report using paths from st.session_state.result]
    │
    ▼
os.path.exists(report_md_path) → open and render/download
os.path.exists(report_pdf_path) → read bytes and offer download
```

**Critical wiring requirements:**
1. The `on_event` callback in `api/server.py` MUST call `task.model_dump()` before putting the task in the queue (BUG-01).
2. The `asyncio.run()` issue in `ui/app.py` MUST be patched with `nest_asyncio` (BUG-05).
3. `RUNS_DIR` must default to `./runs` so that report file paths are accessible from the Streamlit process (BUG-06).
4. The FastAPI server and Streamlit must run as separate processes sharing the same filesystem (the `CMD` in `Dockerfile` starts both in one container; locally, run them in separate terminals).

---

## 6. WHAT YOU MUST DO — COMPLETE INSTRUCTIONS

Apply every fix in this exact order:

**Phase 1 — Cleanup (no logic changes)**
1. Delete `api/api_server.py`.
2. Delete `core/base_agent.py`.
3. Ensure `api/__init__.py` contains only `# api package` (no imports from deleted files).
4. Confirm all agents import `from agents.base_agent import BaseAgent` (grep for `core.base_agent`).

**Phase 2 — Critical Bug Fixes**
5. Fix BUG-01: `task.model_dump()` in `api/server.py` `on_event`.
6. Fix BUG-04: Lazy `asyncio.Lock` in `memory/knowledge_graph.py`.
7. Fix BUG-05: Add `nest_asyncio` to `requirements.txt` and apply it in `ui/app.py`.
8. Fix BUG-06: Confirm `RUNS_DIR` defaults to `./runs` in both `core/task_manager.py` and `core/report_generator.py`.
9. Fix BUG-07: Update `tools/code_executor.py` Docker command to install numpy, pandas, matplotlib, scipy before running the script.
10. Fix BUG-08: Remove the duplicate broken usage dict line in `core/agent_loop.py`.
11. Fix BUG-10: Scope CORS `allow_origins` to `["http://localhost:8501"]` or env-var-configurable in `api/server.py`.

**Phase 3 — Verification**
12. Verify BUG-09: `np.array(other_data["embedding"])` in both `add_paper` and `query_related` in `memory/knowledge_graph.py`.
13. Verify BUG-12: `.tolist()` on Pinecone embeddings in `memory/vector_store.py`.
14. Verify BUG-11: No `from core.base_agent import` anywhere after Phase 1.
15. Verify BUG-13: `api/__init__.py` is clean.

**Phase 4 — Tests**
16. Confirm `tests/test_agent_loop.py` passes with the mocked LLM. The mock for the ReAct loop (Researcher agent) must return `{"done": true, "result": "mock result"}` — verify this is the case in the mock function. The existing mock returns `'{"dummy": "data"}'` for the default case which will fail to parse as `ToolCallOrResult`. Fix the default return to `'{"done": true, "result": "mock result"}'`.
17. Add `monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")` to the test fixture to prevent `LLMClient.__init__` from raising `EnvironmentError`.

**Phase 5 — Final Review**
18. Read through every file one final time. Confirm: no `asyncio.Lock()` in `__init__` methods, no hardcoded `/app/runs` outside Docker config, no duplicate files, no dead imports.
19. Output the **complete, final, corrected version** of every file that was changed. Do not output unchanged files. Format each file as a code block with its path as a comment on the first line.

---

## 7. DEFINITION OF DONE

The project is complete when all of the following are true:
- `pip install -r requirements.txt && python -m pytest -q` passes with no errors (using mocked LLM calls).
- `uvicorn api.server:app --port 8000` starts without import errors.
- `streamlit run ui/app.py` starts without import errors.
- Submitting the question "Analyze the impact of different activation functions on Transformer convergence speed" via the UI produces a visible agent activity feed, at least one arXiv paper cited in the report, a generated Python experiment, a Critic review, and a downloadable PDF report.
- `docker compose up --build` boots successfully and the app is reachable at `http://localhost:8501`.
