"""
api/server.py — FastAPI backend for the Autonomous AI Researcher.

Provides REST endpoints for starting, streaming, approving, cancelling,
and inspecting research runs.  Uses the RunManager abstraction (Redis in
production, in-memory for local dev) for lifecycle management.
"""

from __future__ import annotations

import asyncio
import hmac
import inspect
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from api.run_manager import create_run_manager
from config import get_settings
from core.agent_loop import run_agent_async
from core.logging_setup import configure_logging, get_logger

# ── Rate limiting (optional dependency) ──────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    _HAS_SLOWAPI = True
except ImportError:
    _HAS_SLOWAPI = False

# ── Logging ──────────────────────────────────────────────────────────────
configure_logging(level=get_settings().log_level)
logger = get_logger(__name__)

# ── App setup ────────────────────────────────────────────────────────────
app = FastAPI(title="Autonomous AI Researcher", version="1.0.0")

if _HAS_SLOWAPI:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:

    class _DummyLimiter:
        """No-op limiter so @limiter.limit() decorators don't crash."""

        def limit(self, *_a, **_kw):
            def decorator(func):
                return func

            return decorator

    limiter = _DummyLimiter()

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_RATE_LIMIT = f"{get_settings().rate_limit_per_minute}/minute"
redis_url = get_settings().redis_url

# RunManager is created via factory — auto-detects Redis availability
run_manager = create_run_manager(redis_url=redis_url)


# ── Lifecycle events ─────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI server starting up")


@app.on_event("shutdown")
async def shutdown_event():
    await run_manager.close()


# ── Security helpers ─────────────────────────────────────────────────────
async def _verify_api_key(request: Request):
    """Constant-time API key verification to prevent timing attacks."""
    expected_key = get_settings().internal_api_key
    if expected_key:
        provided = request.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, expected_key):
            raise HTTPException(status_code=401, detail="Unauthorized")


def _verify_websocket_api_key(websocket: WebSocket) -> None:
    """Apply the same API-key gate to WebSocket streams as REST routes."""
    expected_key = get_settings().internal_api_key
    if expected_key:
        provided = websocket.headers.get("X-API-Key", "")
        if not hmac.compare_digest(provided, expected_key):
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Unauthorized",
            )


def _validate_run_id(run_id: str) -> str:
    """Validate run_id is a UUID to prevent path traversal."""
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid run_id format")
    return run_id


# ── Request / Response models ────────────────────────────────────────────
class ResearchRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="The research question to investigate.",
    )


class ApprovalRequest(BaseModel):
    approved: bool
    feedback: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/research", status_code=202)
@limiter.limit(_RATE_LIMIT)
async def start_research(request: Request, req: ResearchRequest):
    await _verify_api_key(request)

    run_id = str(uuid.uuid4())
    record = await run_manager.create(run_id, req.question)

    # ── Callbacks for the agent loop ─────────────────────────────────
    def on_event(task):
        """Called synchronously by TaskManager._notify()."""
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(
                asyncio.ensure_future,
                run_manager.publish_event(
                    run_id, {"type": "task_update", "task": task.model_dump()}
                ),
            )
        except RuntimeError:
            pass  # no loop — swallow

    def on_token(agent: str, delta: str):
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(
                asyncio.ensure_future,
                run_manager.publish_event(
                    run_id, {"type": "token", "agent": agent, "delta": delta}
                ),
            )
        except RuntimeError:
            pass

    # ── Build kwargs dynamically based on run_agent_async signature ───
    sig = inspect.signature(run_agent_async)
    kwargs: dict = {}
    param_map = {
        "run_id": run_id,
        "on_event": on_event,
        "on_token": on_token,
        "stream_tokens": True,
    }
    for name, value in param_map.items():
        if name in sig.parameters:
            kwargs[name] = value

    async def _run_task():
        try:
            result = await run_agent_async(req.question, **kwargs)
            await run_manager.publish_event(run_id, {"type": "done", "result": result})
            await run_manager.finish(run_id, status="completed")
        except asyncio.CancelledError:
            logger.info("Run %s cancelled", run_id)
        except Exception as e:
            logger.exception("Run %s failed", run_id)
            await run_manager.publish_event(
                run_id, {"type": "error", "error": str(e)}
            )
            await run_manager.finish(run_id, status="error")

    asyncio.create_task(_run_task())
    logger.info("Started research run %s for: %s", run_id, req.question[:120])
    return {"run_id": run_id}


@app.post("/api/research/{run_id}/approve")
async def approve_research(run_id: str, request: Request, req: ApprovalRequest):
    await _verify_api_key(request)
    _validate_run_id(run_id)
    await run_manager.publish_event(f"{run_id}_approval", req.model_dump())
    return {"status": "ok"}


@app.get("/api/runs")
async def list_runs(request: Request):
    await _verify_api_key(request)
    return await run_manager.list_runs()


@app.delete("/api/research/{run_id}")
async def cancel_research(run_id: str, request: Request):
    """Cancel a running research job."""
    await _verify_api_key(request)
    _validate_run_id(run_id)

    success = await run_manager.cancel(run_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Run not found or already completed"
        )
    return {"status": "cancelling", "run_id": run_id}


@app.websocket("/api/research/{run_id}/stream")
async def stream_research(websocket: WebSocket, run_id: str):
    _validate_run_id(run_id)
    _verify_websocket_api_key(websocket)
    await websocket.accept()

    pubsub = await run_manager.subscribe_events(run_id)
    try:
        async for msg in pubsub.listen():
            if msg["type"] == "message":
                data = msg["data"]
                event = json.loads(data) if isinstance(data, str) else data
                await websocket.send_json(event)
                if event.get("type") in ("done", "error", "cancelled"):
                    break
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/research/{run_id}/report")
async def get_report(run_id: str, request: Request):
    await _verify_api_key(request)
    _validate_run_id(run_id)
    report_path = get_settings().run_dir(run_id) / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not found")
    return Response(
        content=report_path.read_text(encoding="utf-8"), media_type="text/markdown"
    )


@app.get("/api/research/{run_id}/status")
async def get_run_status(run_id: str, request: Request):
    """Check the status of a research run."""
    await _verify_api_key(request)
    _validate_run_id(run_id)
    runs = await run_manager.list_runs()
    for run in runs:
        if run["run_id"] == run_id:
            return {"run_id": run_id, "status": run["status"]}

    # Check if a report exists (completed previously)
    report_path = get_settings().run_dir(run_id) / "report.md"
    if report_path.exists():
        return {"run_id": run_id, "status": "completed"}

    return {"run_id": run_id, "status": "not_found"}


# ── Global exception handler ────────────────────────────────────────────
@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
