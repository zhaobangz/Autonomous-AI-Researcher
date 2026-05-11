"""
tests/test_run_manager.py — Unit tests for the InMemoryRunManager.
"""

from __future__ import annotations

import asyncio
import pytest
from api.run_manager import InMemoryRunManager


@pytest.fixture
def manager():
    return InMemoryRunManager(queue_ttl=5)


class TestInMemoryRunManager:
    def test_create_returns_record(self, manager):
        rec = asyncio.run(manager.create("run-abc", "What is attention?"))
        assert rec.run_id == "run-abc"
        assert rec.status == "running"
        assert rec.queue is not None

    def test_get_returns_record(self, manager):
        asyncio.run(manager.create("run-xyz", "Question"))
        rec = manager._runs.get("run-xyz")
        assert rec is not None
        assert rec.run_id == "run-xyz"

    def test_get_missing_returns_none(self, manager):
        assert manager._runs.get("nonexistent") is None

    def test_finish_updates_status(self, manager):
        asyncio.run(manager.create("run-fin", "q"))
        asyncio.run(manager.finish("run-fin", status="done"))
        assert manager._runs.get("run-fin").status == "done"

    def test_cancel_sets_event(self, manager):
        rec = asyncio.run(manager.create("run-cxl", "q"))
        asyncio.run(manager.cancel("run-cxl"))
        assert rec.cancel_event.is_set()
        assert manager._runs.get("run-cxl").status == "cancelled"

    def test_cancel_nonexistent_returns_false(self, manager):
        result = asyncio.run(manager.cancel("ghost"))
        assert result is False

    def test_list_runs_contains_created(self, manager):
        asyncio.run(manager.create("run-list", "q"))
        runs = asyncio.run(manager.list_runs())
        ids = [r["run_id"] for r in runs]
        assert "run-list" in ids

    def test_evict_stale_removes_old_finished_runs(self, manager):
        import time
        asyncio.run(manager.create("run-stale", "q"))
        asyncio.run(manager.finish("run-stale", "done"))
        rec = manager._runs.get("run-stale")
        # Force finished_at into the past beyond TTL
        rec.finished_at = time.monotonic() - 10
        asyncio.run(manager._evict_stale())
        assert manager._runs.get("run-stale") is None

    def test_evict_stale_keeps_running_runs(self, manager):
        asyncio.run(manager.create("run-live", "q"))
        asyncio.run(manager._evict_stale())
        assert manager._runs.get("run-live") is not None
