from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_RETENTION_DAYS = 30


class ScanJobStore:
    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(self._db_path, check_same_thread=False, timeout=10)
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _init_db(self) -> None:
        conn = self._get_conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                error TEXT,
                result_count INTEGER NOT NULL DEFAULT 0,
                results_json TEXT
            )
            """
        )
        conn.commit()

    def create_job(self, job_id: str, created_at: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO scan_jobs (id, status, created_at) VALUES (?, 'PENDING', ?)",
            (job_id, created_at),
        )
        conn.commit()

    def mark_running(self, job_id: str, started_at: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE scan_jobs SET status='RUNNING', started_at=? WHERE id=?",
            (started_at, job_id),
        )
        conn.commit()

    def mark_failed(self, job_id: str, finished_at: str, error: str) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE scan_jobs SET status='FAILED', finished_at=?, error=?, result_count=0, results_json=NULL WHERE id=?",
            (finished_at, error, job_id),
        )
        conn.commit()

    def mark_completed(self, job_id: str, finished_at: str, results: list[dict[str, Any]]) -> None:
        conn = self._get_conn()
        conn.execute(
            "UPDATE scan_jobs SET status='COMPLETED', finished_at=?, error=NULL, result_count=?, results_json=? WHERE id=?",
            (finished_at, len(results), json.dumps(results, ensure_ascii=False), job_id),
        )
        conn.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute("SELECT * FROM scan_jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def get_latest_completed_job(self) -> dict[str, Any] | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM scan_jobs WHERE status='COMPLETED' ORDER BY finished_at DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def load_results(self, job_id: str) -> list[dict[str, Any]]:
        job = self.get_job(job_id)
        if not job:
            return []
        payload = job.get("results_json")
        if not payload:
            return []
        try:
            parsed = json.loads(payload)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            logger.warning("Sonuc JSON parse hatasi (job_id=%s)", job_id, exc_info=True)
            return []

    def cleanup_old_jobs(self, retention_days: int = _RETENTION_DAYS) -> int:
        cutoff = datetime.now(timezone.utc).isoformat()
        conn = self._get_conn()
        cursor = conn.execute(
            """
            DELETE FROM scan_jobs
            WHERE status IN ('COMPLETED', 'FAILED')
              AND finished_at IS NOT NULL
              AND julianday(?) - julianday(finished_at) > ?
            """,
            (cutoff, retention_days),
        )
        conn.commit()
        deleted = cursor.rowcount
        if deleted > 0:
            logger.info("Eski tarama kayitlari temizlendi: %d adet silindi", deleted)
        return deleted
