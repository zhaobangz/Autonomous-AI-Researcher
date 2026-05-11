"""
api/run_manager.py — Run lifecycle management with Redis or in-memory fallback.

Provides two implementations:
  - RedisRunManager: uses Redis Pub/Sub for multi-worker streaming
  - InMemoryRunManager: uses asyncio.Queue for single-process local dev

The factory function `create_run_manager()` tries Redis first and falls
back to in-memory if the connection fails.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

logger = logging.getLogger(__name__)


# ── Shared data types ─────────────────────────────────────────────────────

@dataclass
class RunRecord:
    run_id: str
    question: str
    status: str = "running"
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    queue: Optional[asyncio.Queue] = field(default_factory=asyncio.Queue)
    started_at: float = field(default_factory=time.monotonic)
    finished_at: Optional[float] = None


class RunManagerProtocol(Protocol):
    """Common interface for run managers."""
    async def create(self, run_id: str, question: str) -> RunRecord: ...
    async def publish_event(self, run_id: str, event: dict) -> None: ...
    async def subscribe_events(self, run_id: str) -> Any: ...
    async def cancel(self, run_id: str) -> bool: ...
    async def finish(self, run_id: str, status: str) -> None: ...
    async def list_runs(self) -> List[dict]: ...
    async def close(self) -> None: ...


# ── In-Memory Implementation (local dev / single process) ────────────────

class _InMemoryPubSub:
    """Minimal async iterator over an asyncio.Queue, mimicking Redis PubSub."""

    def __init__(self, queue: asyncio.Queue):
        self._queue = queue

    async def listen(self):
        while True:
            item = await self._queue.get()
            yield {"type": "message", "data": json.dumps(item) if isinstance(item, dict) else item}

    async def unsubscribe(self):
        pass

    async def close(self):
        pass


class InMemoryRunManager:
    """Single-process run manager using asyncio primitives. No Redis needed."""

    def __init__(self, queue_ttl: int = 300) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}
        self._queue_ttl = queue_ttl

    async def create(self, run_id: str, question: str) -> RunRecord:
        record = RunRecord(run_id=run_id, question=question)
        self._runs[run_id] = record
        self._event_queues[run_id] = asyncio.Queue()
        logger.info("InMemoryRunManager | created run %s", run_id)
        return record

    async def publish_event(self, run_id: str, event: dict) -> None:
        q = self._event_queues.get(run_id)
        if q:
            await q.put(event)

    async def subscribe_events(self, run_id: str) -> _InMemoryPubSub:
        if run_id not in self._event_queues:
            self._event_queues[run_id] = asyncio.Queue()
        return _InMemoryPubSub(self._event_queues[run_id])

    async def cancel(self, run_id: str) -> bool:
        rec = self._runs.get(run_id)
        if not rec or rec.status != "running":
            return False
        rec.status = "cancelled"
        rec.cancel_event.set()
        rec.finished_at = time.monotonic()
        await self.publish_event(run_id, {"type": "cancelled", "run_id": run_id})
        logger.info("InMemoryRunManager | cancelled run %s", run_id)
        return True

    async def finish(self, run_id: str, status: str = "done") -> None:
        rec = self._runs.get(run_id)
        if rec and rec.status == "running":
            rec.status = status
            rec.finished_at = time.monotonic()
            logger.info("InMemoryRunManager | finished run %s status=%s", run_id, status)

    async def list_runs(self) -> List[dict]:
        runs = []
        for rec in self._runs.values():
            age = time.monotonic() - rec.started_at
            runs.append({
                "run_id": rec.run_id,
                "question": rec.question[:120],
                "status": rec.status,
                "age_seconds": round(age, 1),
            })
        runs.sort(key=lambda x: x["age_seconds"])
        return runs

    def get(self, run_id: str) -> Optional[RunRecord]:
        return self._runs.get(run_id)

    async def _evict_stale(self) -> None:
        """Remove finished runs older than TTL."""
        now = time.monotonic()
        to_remove = [
            rid for rid, rec in self._runs.items()
            if rec.finished_at and (now - rec.finished_at) > self._queue_ttl
        ]
        for rid in to_remove:
            self._runs.pop(rid, None)
            self._event_queues.pop(rid, None)

    async def close(self) -> None:
        self._runs.clear()
        self._event_queues.clear()


# ── Redis Implementation ─────────────────────────────────────────────────

class RedisRunManager:
    """Redis-backed manager for multi-worker deployments."""

    def __init__(self, redis_url: str = "redis://localhost:6379") -> None:
        import redis.asyncio as aioredis
        self.redis = aioredis.from_url(redis_url, decode_responses=True)
        self._local_cancel_events: Dict[str, asyncio.Event] = {}
        self._cancel_tasks: Dict[str, asyncio.Task] = {}

    async def create(self, run_id: str, question: str) -> RunRecord:
        data = {
            "run_id": run_id,
            "question": question,
            "status": "running",
            "started_at": str(time.time()),
        }
        await self.redis.hset(f"run:{run_id}", mapping=data)
        await self.redis.expire(f"run:{run_id}", 86400 * 7)

        cancel_event = asyncio.Event()
        self._local_cancel_events[run_id] = cancel_event

        task = asyncio.create_task(self._listen_for_cancel(run_id, cancel_event))
        self._cancel_tasks[run_id] = task

        logger.info("RedisRunManager | created run %s", run_id)
        return RunRecord(run_id=run_id, question=question, cancel_event=cancel_event)

    async def publish_event(self, run_id: str, event: dict) -> None:
        try:
            await self.redis.publish(f"run:{run_id}:events", json.dumps(event))
        except Exception as exc:
            logger.warning("RedisRunManager | publish failed for %s: %s", run_id, exc)

    async def _listen_for_cancel(self, run_id: str, cancel_event: asyncio.Event) -> None:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"run:{run_id}:cancel")
        try:
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    cancel_event.set()
                    break
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()

    async def cancel(self, run_id: str) -> bool:
        exists = await self.redis.exists(f"run:{run_id}")
        if not exists:
            return False
        status = await self.redis.hget(f"run:{run_id}", "status")
        if status != "running":
            return False
        await self.redis.hset(f"run:{run_id}", "status", "cancelled")
        await self.redis.hset(f"run:{run_id}", "finished_at", str(time.time()))
        await self.redis.publish(f"run:{run_id}:cancel", "1")
        await self.publish_event(run_id, {"type": "cancelled", "run_id": run_id})
        logger.info("RedisRunManager | cancelled run %s", run_id)
        return True

    async def finish(self, run_id: str, status: str = "done") -> None:
        current = await self.redis.hget(f"run:{run_id}", "status")
        if current == "running":
            await self.redis.hset(f"run:{run_id}", "status", status)
            await self.redis.hset(f"run:{run_id}", "finished_at", str(time.time()))
            logger.info("RedisRunManager | finished run %s status=%s", run_id, status)
        self._local_cancel_events.pop(run_id, None)
        task = self._cancel_tasks.pop(run_id, None)
        if task:
            task.cancel()

    async def list_runs(self) -> List[dict]:
        keys = await self.redis.keys("run:*")
        runs = []
        for k in keys:
            if ":events" in k or ":cancel" in k:
                continue
            data = await self.redis.hgetall(k)
            if data and "run_id" in data:
                started_at = float(data.get("started_at", time.time()))
                age = time.time() - started_at
                runs.append({
                    "run_id": data["run_id"],
                    "question": data.get("question", "")[:120],
                    "status": data.get("status", "unknown"),
                    "age_seconds": round(age, 1),
                })
        runs.sort(key=lambda x: x["age_seconds"])
        return runs

    async def subscribe_events(self, run_id: str):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(f"run:{run_id}:events")
        return pubsub

    async def close(self):
        for task in self._cancel_tasks.values():
            task.cancel()
        await self.redis.close()


# ── Factory ───────────────────────────────────────────────────────────────

def create_run_manager(redis_url: str = "redis://localhost:6379"):
    """
    Try to connect to Redis. If it fails, fall back to InMemoryRunManager.
    This lets developers run locally without Redis installed.
    """
    try:
        import redis.asyncio as aioredis
        # Synchronous ping check to verify connectivity
        import redis as sync_redis
        client = sync_redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        client.close()
        logger.info("Redis available at %s — using RedisRunManager", redis_url)
        return RedisRunManager(redis_url=redis_url)
    except Exception as e:
        logger.warning("Redis unavailable (%s) — falling back to InMemoryRunManager", e)
        return InMemoryRunManager()
