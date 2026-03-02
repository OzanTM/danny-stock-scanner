from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import threading
import uuid

from .job_store import ScanJobStore
from .service import StockScannerService

logger = logging.getLogger(__name__)


class ScanJobRunner:
    def __init__(self, service: StockScannerService, store: ScanJobStore) -> None:
        self._service = service
        self._store = store
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._lock = threading.Lock()
        self._active_job_id: str | None = None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def enqueue_scan(self) -> tuple[str, bool]:
        with self._lock:
            if self._active_job_id:
                active = self._store.get_job(self._active_job_id)
                if active and active.get("status") in {"PENDING", "RUNNING"}:
                    logger.info("Tarama zaten calisiyor: %s", self._active_job_id)
                    return self._active_job_id, False
                self._active_job_id = None

            job_id = uuid.uuid4().hex
            self._store.create_job(job_id, self._now())
            self._active_job_id = job_id
            self._executor.submit(self._run_job, job_id)
            logger.info("Yeni tarama baslatildi: %s", job_id)
            return job_id, True

    def _run_job(self, job_id: str) -> None:
        self._store.mark_running(job_id, self._now())
        logger.info("Tarama calisiyor: %s", job_id)
        try:
            results, error = self._service.run_scan()
            if error:
                self._store.mark_failed(job_id, self._now(), error)
                logger.warning("Tarama basarisiz bitti: %s | hata=%s", job_id, error)
            else:
                self._store.mark_completed(job_id, self._now(), results)
                logger.info("Tarama tamamlandi: %s | sonuc_sayisi=%d", job_id, len(results))
        except Exception as exc:
            logger.exception("Tarama basarisiz (job_id=%s): %s", job_id, exc)
            self._store.mark_failed(job_id, self._now(), f"Beklenmeyen hata: {exc}")
        finally:
            with self._lock:
                if self._active_job_id == job_id:
                    self._active_job_id = None

    def get_job(self, job_id: str) -> dict | None:
        return self._store.get_job(job_id)

    def get_latest_completed_results(self) -> tuple[str | None, list[dict]]:
        latest = self._store.get_latest_completed_job()
        if not latest:
            return None, []
        job_id = latest["id"]
        return job_id, self._store.load_results(job_id)
