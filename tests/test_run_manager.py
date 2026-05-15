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

    def test_publish_event_is_received_by_subscriber(self, manager):
        async def scenario():
            await manager.create("run-pub", "q")
            pubsub = await manager.subscribe_events("run-pub")
            await manager.publish_event("run-pub", {"type": "token", "data": "hi"})

            async for msg in pubsub.listen():
                return msg

        msg = asyncio.run(scenario())
        assert msg["type"] == "message"
        # InMemory pubsub serializes dict events as JSON
        assert "token" in msg["data"]

    def test_publish_event_to_unknown_run_is_noop(self, manager):
        # Should not raise even with no subscribers / no run
        asyncio.run(manager.publish_event("ghost", {"type": "x"}))

    def test_finish_with_custom_status(self, manager):
        asyncio.run(manager.create("run-fail", "q"))
        asyncio.run(manager.finish("run-fail", status="failed"))
        assert manager._runs.get("run-fail").status == "failed"
        assert manager._runs.get("run-fail").finished_at is not None

    def test_finish_only_transitions_running_runs(self, manager):
        """finish() must not overwrite a terminal status (e.g. cancelled)."""
        asyncio.run(manager.create("run-cxl", "q"))
        asyncio.run(manager.cancel("run-cxl"))
        asyncio.run(manager.finish("run-cxl", status="done"))
        assert manager._runs.get("run-cxl").status == "cancelled"

    def test_cancel_already_finished_returns_false(self, manager):
        asyncio.run(manager.create("run-done", "q"))
        asyncio.run(manager.finish("run-done", status="done"))
        result = asyncio.run(manager.cancel("run-done"))
        assert result is False

    def test_get_returns_record_or_none(self, manager):
        asyncio.run(manager.create("run-get", "q"))
        rec = manager.get("run-get")
        assert rec is not None and rec.run_id == "run-get"
        assert manager.get("nope") is None

    def test_close_clears_all_state(self, manager):
        asyncio.run(manager.create("run-x", "q"))
        asyncio.run(manager.close())
        assert manager._runs == {}
        assert manager._event_queues == {}

    def test_list_runs_truncates_long_questions(self, manager):
        long_q = "x" * 500
        asyncio.run(manager.create("run-trunc", long_q))
        runs = asyncio.run(manager.list_runs())
        rec = next(r for r in runs if r["run_id"] == "run-trunc")
        assert len(rec["question"]) == 120


class TestRunManagerFactory:
    def test_falls_back_to_in_memory_when_redis_unavailable(self, mocker):
        from api.run_manager import InMemoryRunManager, create_run_manager

        # Patch sync redis ping to raise
        fake_client = mocker.MagicMock()
        fake_client.ping.side_effect = Exception("connection refused")
        mocker.patch("redis.from_url", return_value=fake_client)

        mgr = create_run_manager("redis://does-not-exist:6379")
        assert isinstance(mgr, InMemoryRunManager)
