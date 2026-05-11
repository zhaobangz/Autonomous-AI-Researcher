# core/task_manager.py
"""
Manages async execution tracking with debounced persistence.

Instead of writing tasks.json on every add()/update(), mutations set a
dirty flag and schedule a single flush after a short delay.  This coalesces
rapid-fire state changes (e.g. parallel research steps) into one write
while still guaranteeing data hits disk within `flush_delay_seconds`.
"""
import json
import os
import uuid
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field


class Task(BaseModel):
    id: str
    parent_id: Optional[str] = None
    kind: str # plan, search, summarize, code, exec, review
    status: str = "pending" # pending, running, done, failed
    input: Any = None
    output: Any = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    finished_at: Optional[str] = None


class TaskManager:
    """Async-safe task state manager with debounced file persistence."""

    def __init__(self, run_id: str, flush_delay_seconds: float = 0.5):
        uuid.UUID(run_id)  # raises ValueError if invalid
        self.run_id = run_id
        self.tasks: Dict[str, Task] = {}
        self.callbacks: List[Callable] = []

        BASE_DIR = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        self.run_dir = BASE_DIR / run_id
        os.makedirs(self.run_dir, exist_ok=True)
        self.tasks_file = self.run_dir / "tasks.json"

        # Debounce state
        self._dirty = False
        self._flush_delay = flush_delay_seconds
        self._flush_task: Optional[asyncio.Task] = None

    def subscribe(self, callback: Callable):
        self.callbacks.append(callback)

    def _notify(self, task: Task):
        for cb in self.callbacks:
            cb(task)
        self._mark_dirty()

    def _mark_dirty(self):
        """Set dirty flag and schedule a debounced flush."""
        self._dirty = True
        # If a flush is already scheduled, let it pick up the new changes
        if self._flush_task is None or self._flush_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._flush_task = loop.create_task(self._debounced_flush())
            except RuntimeError:
                # No running event loop (e.g. sync tests) — flush immediately
                self._sync_save()

    async def _debounced_flush(self):
        """Wait for the debounce window, then write if still dirty."""
        await asyncio.sleep(self._flush_delay)
        if self._dirty:
            await asyncio.to_thread(self._sync_save)

    def _sync_save(self):
        """Thread-safe synchronous file write (atomic on POSIX)."""
        data = {tid: task.model_dump() for tid, task in self.tasks.items()}
        tmp_path = self.tasks_file.with_suffix(".tmp")
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
        tmp_path.replace(self.tasks_file)  # atomic rename
        self._dirty = False

    async def flush(self):
        """Force an immediate flush. Call before returning final results."""
        if self._dirty:
            await asyncio.to_thread(self._sync_save)

    def add(self, task: Task):
        self.tasks[task.id] = task
        self._notify(task)

    def update(self, task_id: str, **fields):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for k, v in fields.items():
                setattr(task, k, v)
            if fields.get("status") in ("done", "failed"):
                task.finished_at = datetime.now(timezone.utc).isoformat()
            self._notify(task)

    def get(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def pending(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == "pending"]

    def history(self) -> List[Task]:
        return list(self.tasks.values())
