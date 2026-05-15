"""
tests/test_task_manager.py — Unit tests for the debounced TaskManager.
"""

from __future__ import annotations

import asyncio
import json
import uuid

import pytest

from core.task_manager import Task, TaskManager


def _new_run_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture
def manager(tmp_path, monkeypatch):
    monkeypatch.setenv("RUNS_DIR", str(tmp_path))
    return TaskManager(_new_run_id(), flush_delay_seconds=0.05)


class TestInitialization:
    def test_invalid_run_id_raises_value_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        with pytest.raises(ValueError):
            TaskManager("not-a-uuid")

    def test_creates_run_directory(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        run_id = _new_run_id()
        TaskManager(run_id)
        assert (tmp_path / run_id).is_dir()


class TestAddAndGet:
    def test_add_stores_task(self, manager):
        task = Task(id="t1", kind="plan")
        manager.add(task)
        assert manager.get("t1") is task

    def test_get_unknown_returns_none(self, manager):
        assert manager.get("missing") is None

    def test_history_returns_all_tasks(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        manager.add(Task(id="t2", kind="search"))
        history = manager.history()
        assert {t.id for t in history} == {"t1", "t2"}


class TestUpdate:
    def test_update_changes_field(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        manager.update("t1", output="result")
        assert manager.get("t1").output == "result"

    def test_update_done_sets_finished_at(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        manager.update("t1", status="done")
        assert manager.get("t1").finished_at is not None

    def test_update_failed_sets_finished_at(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        manager.update("t1", status="failed")
        assert manager.get("t1").finished_at is not None

    def test_update_running_does_not_set_finished_at(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        manager.update("t1", status="running")
        assert manager.get("t1").finished_at is None

    def test_update_unknown_id_is_noop(self, manager):
        manager.update("ghost", status="done")
        assert manager.get("ghost") is None


class TestPending:
    def test_returns_only_pending(self, manager):
        manager.add(Task(id="a", kind="search", status="pending"))
        manager.add(Task(id="b", kind="search", status="running"))
        manager.add(Task(id="c", kind="search", status="done"))
        ids = {t.id for t in manager.pending()}
        assert ids == {"a"}


class TestSubscribe:
    def test_callback_invoked_on_add(self, manager):
        seen: list = []
        manager.subscribe(seen.append)
        task = Task(id="t1", kind="plan")
        manager.add(task)
        assert seen == [task]

    def test_callback_invoked_on_update(self, manager):
        seen: list = []
        manager.add(Task(id="t1", kind="plan"))
        manager.subscribe(seen.append)
        manager.update("t1", status="done")
        assert len(seen) == 1
        assert seen[0].id == "t1"


class TestPersistence:
    def test_sync_save_writes_json_file(self, manager):
        """Outside an event loop, _mark_dirty falls through to a sync write."""
        manager.add(Task(id="t1", kind="plan", input="hello"))
        # File should exist immediately because _mark_dirty fell through to _sync_save
        assert manager.tasks_file.exists()
        data = json.loads(manager.tasks_file.read_text())
        assert "t1" in data
        assert data["t1"]["kind"] == "plan"
        assert data["t1"]["input"] == "hello"

    def test_atomic_write_does_not_leave_tmp_file(self, manager):
        manager.add(Task(id="t1", kind="plan"))
        tmp_path = manager.tasks_file.with_suffix(".tmp")
        assert not tmp_path.exists()

    def test_debounced_flush_persists_within_window(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        run_id = _new_run_id()

        async def scenario():
            tm = TaskManager(run_id, flush_delay_seconds=0.05)
            tm.add(Task(id="a", kind="plan"))
            tm.add(Task(id="b", kind="search"))
            await asyncio.sleep(0.15)  # > flush window
            return tm

        tm = asyncio.run(scenario())
        data = json.loads(tm.tasks_file.read_text())
        assert {"a", "b"} <= set(data.keys())

    def test_explicit_flush_writes_immediately(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RUNS_DIR", str(tmp_path))
        run_id = _new_run_id()

        async def scenario():
            tm = TaskManager(run_id, flush_delay_seconds=10.0)
            tm.add(Task(id="x", kind="plan"))
            # Without an explicit flush, we'd be waiting 10s; flush() short-circuits.
            await tm.flush()
            return tm

        tm = asyncio.run(scenario())
        data = json.loads(tm.tasks_file.read_text())
        assert "x" in data
