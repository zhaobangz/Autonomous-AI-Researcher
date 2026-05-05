import asyncio
import os
import uuid
from typing import Dict
from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from pathlib import Path

from core.agent_loop import run_agent_async

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "http://localhost:8501").split(","), 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

active_queues: Dict[str, asyncio.Queue] = {}

async def verify_api_key(request: Request):
    expected_key = os.getenv("INTERNAL_API_KEY")
    if expected_key:
        api_key = request.headers.get("X-API-Key")
        if api_key != expected_key:
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
            queue.put_nowait({"type": "task_update", "task": task.model_dump()})
        except Exception:
            pass

    def on_token(agent: str, delta: str):
        try:
            queue.put_nowait({"type": "token", "agent": agent, "delta": delta})
        except Exception:
            pass

    async def run_task():
        try:
            result = await run_agent_async(
                req.question, 
                run_id=run_id, 
                on_event=on_event, 
                on_token=on_token,
                stream_tokens=True
            )
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
        if run_id in active_queues:
            del active_queues[run_id]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/research/{run_id}/report")
async def get_report(run_id: str, request: Request):
    await verify_api_key(request)
    base = Path(os.getenv("RUNS_DIR", "/app/runs")).resolve()
    report_path = base / run_id / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
        
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(content=content, media_type="text/markdown")
