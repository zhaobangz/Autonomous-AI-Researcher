import uuid, os, asyncio, logging, threading
from typing import Callable, Optional, Dict, Any, TypedDict
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

logger = logging.getLogger(__name__)

# Max reroute attempts — configurable via env var
MAX_REROUTES = int(os.getenv("MAX_REROUTES", "2"))


class ReportBundle(TypedDict, total=False):
    """Serializable result bundle returned by the agent loop."""

    report_md: str
    report_pdf_path: str
    tasks: list[dict]
    usage: dict[str, float]


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
    related_nodes = await asyncio.to_thread(kg.query_related, research_question, 3)
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

            # ── Check exit code and retry on failure ──────────────────
            exec_results = coder_res.get("results", {})
            exit_code = exec_results.get("exit_code", -1)
            stderr = exec_results.get("stderr", "")

            if exit_code != 0:
                logger.warning(
                    "Coder step %s failed (exit_code=%s): %s",
                    task_id, exit_code, stderr[:300],
                )
                # Retry once with stderr feedback
                retry_prompt = (
                    coder_input
                    + f"\n\nPREVIOUS ATTEMPT FAILED (exit_code={exit_code}):\n"
                    + f"stderr:\n{stderr}\n\n"
                    + "Fix the errors and produce a working script."
                )
                coder_res = await coder.run_async(retry_prompt)
                exec_results = coder_res.get("results", {})
                exit_code = exec_results.get("exit_code", -1)

                if exit_code != 0:
                    logger.error("Coder step %s failed after retry", task_id)
                    tm.update(task_id, status="failed", output=coder_res)
                    context["code"] = coder_res.get("code", "")
                    context["results"] = exec_results
                    step_count += 1
                    continue  # skip critic for failed step

            context["code"] = coder_res.get("code", "")
            context["results"] = exec_results
            tm.update(task_id, status="done", output=coder_res)
            step_count += 1
            if step_count >= max_steps:
                break
            crit_id = f"review_{idx}"
            tm.add(Task(id=crit_id, kind="review", input="Review execution", status="running"))
            critique_input = f"Question: {research_question}\nCode: {context['code']}\nResults: {context['results']}"
            report = await critic.run_async(critique_input)
            tm.update(crit_id, status="done", output=report.model_dump())
            if report.confidence_score < 0.4 and reroutes < MAX_REROUTES:
                reroutes += 1
                reroute_id = f"reroute_{idx}"
                tm.add(Task(id=reroute_id, kind="code", input="Fix based on critique", status="running"))
                reroute_prompt = (
                    coder_input
                    + f"\n\nCRITIQUE:\n{report.weaknesses}\n{report.recommendations}"
                )
                coder_res = await coder.run_async(reroute_prompt)

                # Check rerouted code exit code too
                reroute_results = coder_res.get("results", {})
                reroute_exit = reroute_results.get("exit_code", -1)
                if reroute_exit != 0:
                    logger.warning("Reroute %s also failed (exit_code=%s)", reroute_id, reroute_exit)
                    tm.update(reroute_id, status="failed", output=coder_res)
                else:
                    context["code"] = coder_res.get("code", "")
                    context["results"] = reroute_results
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
    await tm.flush()  # ensure all task state is persisted before returning
    usage = {k: planner.llm.usage[k] + researcher.llm.usage[k] + coder.llm.usage[k] + critic.llm.usage[k] + debater.llm.usage[k] for k in ["prompt_tokens", "completion_tokens", "cost_estimate"]}
    return {"report_md": report_paths["report_md"], "report_pdf_path": report_paths["report_pdf_path"], "tasks": [t.model_dump() for t in tm.history()], "usage": usage}


def run_agent(
    research_question: str,
    on_event: Optional[Callable] = None,
    run_id: Optional[str] = None,
    on_token: Optional[Callable[[str, str], None]] = None,
    stream_tokens: bool = False,
) -> ReportBundle:
    """
    Synchronous public entry point required by README/UI integrations.

    Most production paths call ``run_agent_async`` directly (FastAPI), but a
    synchronous wrapper keeps CLI scripts, tests, and simple Streamlit/local
    usage ergonomic. If called while an event loop is already running, execute
    the coroutine in a short-lived background thread to avoid ``asyncio.run``
    nesting errors.
    """

    coro_factory = lambda: run_agent_async(
        research_question,
        run_id=run_id,
        on_event=on_event,
        on_token=on_token,
        stream_tokens=stream_tokens,
    )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro_factory())

    result: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result["value"] = asyncio.run(coro_factory())
        except BaseException as exc:  # propagate after join
            error["value"] = exc

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()
    if error:
        raise error["value"]
    return result["value"]
