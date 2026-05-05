"""
Core orchestration workflow leveraging asyncio for parallelism.
"""
import uuid
import os
import asyncio
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

async def run_agent_async(
    research_question: str, 
    run_id: Optional[str] = None, 
    on_event: Optional[Callable] = None,
    on_token: Optional[Callable] = None,
    stream_tokens: bool = False
) -> Dict[str, Any]:
    
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
    
    related_nodes = kg.query_related(research_question, k=3) if kg.graph.number_of_nodes() > 0 else []
    past_contexts = [f"Past Research [{r.get('run_id')}]: {r.get('title')} - {r.get('summary')}" for r in related_nodes]
    
    context = {
        "question": research_question,
        "plan": plan.model_dump()["steps"],
        "literature": past_contexts,
        "code": "",
        "results": {}
    }
    
    max_steps = int(os.getenv("MAX_STEPS", "12"))
    step_count = 0
    reroutes = 0
    
    search_steps = [s for s in plan.steps if s.kind in ("search", "summarize")]
    other_steps = [s for s in plan.steps if s.kind not in ("search", "summarize")]
    
    if search_steps:
        async def run_search(idx, step):
            task_id = f"step_search_{idx}"
            tm.add(Task(id=task_id, kind=step.kind, input=step.rationale, status="running"))
            summary = await researcher.run_async(
                research_question + " " + step.rationale, 
                stream_callback=on_token if stream_tokens else None
            )
            
            await kg.add_paper(title=f"Research Module {idx}", url="", summary=summary, run_id=run_id)
            tm.update(task_id, status="done", output=summary)
            return summary

        tasks = [run_search(i, s) for i, s in enumerate(search_steps)]
        summaries = await asyncio.gather(*tasks)
        context["literature"].extend(summaries)
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
                
            crit_task_id = f"review_{idx}"
            tm.add(Task(id=crit_task_id, kind="review", input="Review execution", status="running"))
            
            critique_input = f"Question: {research_question}\nCode: {context['code']}\nResults: {context['results']}"
            report = await critic.run_async(critique_input)
            tm.update(crit_task_id, status="done", output=report.model_dump())
            
            if report.confidence_score < 0.4 and reroutes < 1:
                reroutes += 1
                tm.add(Task(id=f"reroute_{idx}", kind="code", input="Fix based on critique", status="running"))
                coder_input += f"\n\nCRITIQUE to fix:\n{report.weaknesses}\n{report.recommendations}"
                coder_res = await coder.run_async(coder_input)
                context["code"] = coder_res.get("code", "")
                context["results"] = coder_res.get("results", {})
                tm.update(f"reroute_{idx}", status="done", output=coder_res)
                
                report = await critic.run_async(f"Question: {research_question}\nCode: {context['code']}\nResults: {context['results']}")
                
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
    
    usage = {
        "prompt_tokens": planner.llm.usage["prompt_tokens"] + researcher.llm.usage["prompt_tokens"] + coder.llm.usage["prompt_tokens"] + critic.llm.usage["prompt_tokens"] + debater.llm.usage["prompt_tokens"],
        "completion_tokens": planner.llm.usage["completion_tokens"] + researcher.llm.usage["completion_tokens"] + coder.llm.usage["completion_tokens"] + critic.llm.usage["completion_tokens"] + debater.llm.usage["completion_tokens"],
        "cost_estimate": planner.llm.usage["cost_estimate"] + researcher.llm.usage["cost_estimate"] + coder.llm.usage["cost_estimate"] + critic.llm.usage["cost_estimate"] + debater.llm.usage["cost_estimate"],
    }
    
    return {
        "report_md": report_paths["report_md"],
        "report_pdf_path": report_paths["report_pdf_path"],
        "tasks": [t.model_dump() for t in tm.history()],
        "usage": usage
    }
