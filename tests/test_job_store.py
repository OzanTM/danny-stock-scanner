from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from scanner.job_store import ScanJobStore


@pytest.fixture
def store(tmp_path: Path) -> ScanJobStore:
    return ScanJobStore(tmp_path / "test_jobs.sqlite3")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TestCreateAndGetJob:
    def test_create_and_retrieve(self, store: ScanJobStore):
        ts = _now_iso()
        store.create_job("job1", ts)
        job = store.get_job("job1")
        assert job is not None
        assert job["id"] == "job1"
        assert job["status"] == "PENDING"
        assert job["created_at"] == ts

    def test_get_nonexistent(self, store: ScanJobStore):
        assert store.get_job("nonexistent") is None


class TestMarkRunning:
    def test_mark_running(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        ts = _now_iso()
        store.mark_running("job1", ts)
        job = store.get_job("job1")
        assert job["status"] == "RUNNING"
        assert job["started_at"] == ts


class TestMarkCompleted:
    def test_mark_completed(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        store.mark_running("job1", _now_iso())
        results = [{"ticker": "AAPL", "signal": "Bullish"}]
        ts = _now_iso()
        store.mark_completed("job1", ts, results)
        job = store.get_job("job1")
        assert job["status"] == "COMPLETED"
        assert job["result_count"] == 1
        assert job["finished_at"] == ts
        assert job["error"] is None


class TestMarkFailed:
    def test_mark_failed(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        store.mark_running("job1", _now_iso())
        ts = _now_iso()
        store.mark_failed("job1", ts, "Network error")
        job = store.get_job("job1")
        assert job["status"] == "FAILED"
        assert job["error"] == "Network error"
        assert job["result_count"] == 0


class TestGetLatestCompleted:
    def test_returns_latest(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        store.mark_running("job1", _now_iso())
        store.mark_completed("job1", "2024-01-01T00:00:00+00:00", [{"a": 1}])

        store.create_job("job2", _now_iso())
        store.mark_running("job2", _now_iso())
        store.mark_completed("job2", "2024-06-01T00:00:00+00:00", [{"b": 2}])

        latest = store.get_latest_completed_job()
        assert latest is not None
        assert latest["id"] == "job2"

    def test_returns_none_when_empty(self, store: ScanJobStore):
        assert store.get_latest_completed_job() is None

    def test_ignores_failed(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        store.mark_running("job1", _now_iso())
        store.mark_failed("job1", _now_iso(), "fail")
        assert store.get_latest_completed_job() is None


class TestLoadResults:
    def test_load_results(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        store.mark_running("job1", _now_iso())
        data = [{"ticker": "GARAN.IS", "signal": "Bullish"}]
        store.mark_completed("job1", _now_iso(), data)
        loaded = store.load_results("job1")
        assert loaded == data

    def test_load_nonexistent(self, store: ScanJobStore):
        assert store.load_results("nope") == []

    def test_load_pending_job(self, store: ScanJobStore):
        store.create_job("job1", _now_iso())
        assert store.load_results("job1") == []


class TestCleanupOldJobs:
    def test_cleanup_removes_old(self, store: ScanJobStore):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        store.create_job("old_job", old_ts)
        store.mark_running("old_job", old_ts)
        store.mark_completed("old_job", old_ts, [])

        recent_ts = _now_iso()
        store.create_job("new_job", recent_ts)
        store.mark_running("new_job", recent_ts)
        store.mark_completed("new_job", recent_ts, [{"data": True}])

        deleted = store.cleanup_old_jobs(retention_days=30)
        assert deleted == 1
        assert store.get_job("old_job") is None
        assert store.get_job("new_job") is not None

    def test_cleanup_keeps_recent(self, store: ScanJobStore):
        ts = _now_iso()
        store.create_job("job1", ts)
        store.mark_running("job1", ts)
        store.mark_completed("job1", ts, [])
        deleted = store.cleanup_old_jobs(retention_days=30)
        assert deleted == 0
        assert store.get_job("job1") is not None
