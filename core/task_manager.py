# core/task_manager.py
"""
Manages async execution tracking safely over absolute paths.
"""
import json
import os
import uuid
from datetime import datetime
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
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None

class TaskManager:
    def __init__(self, run_id: str):
        uuid.UUID(run_id)  # raises ValueError if invalid
        self.run_id = run_id
        self.tasks: Dict[str, Task] = {}
        self.callbacks: List[Callable] = []
        
        BASE_DIR = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        self.run_dir = BASE_DIR / run_id
        os.makedirs(self.run_dir, exist_ok=True)
        self.tasks_file = self.run_dir / "tasks.json"

    def subscribe(self, callback: Callable):
        self.callbacks.append(callback)

    def _notify(self, task: Task):
        for cb in self.callbacks:
            cb(task)
        self._save()

    def _save(self):
        data = {tid: task.model_dump() for tid, task in self.tasks.items()}
        with open(self.tasks_file, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, task: Task):
        self.tasks[task.id] = task
        self._notify(task)

    def update(self, task_id: str, **fields):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            for k, v in fields.items():
                setattr(task, k, v)
            if fields.get("status") in ("done", "failed"):
                task.finished_at = datetime.utcnow().isoformat()
            self._notify(task)

    def get(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def pending(self) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == "pending"]

    def history(self) -> List[Task]:
        return list(self.tasks.values())
