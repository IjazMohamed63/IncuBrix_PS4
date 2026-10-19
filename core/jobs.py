import asyncio
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional
import uuid

import httpx

from core.config import get_settings
from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger
from core.manifest_builder import build_output_manifest

logger = get_logger("job_manager")
settings = get_settings()


class PersistentJobManager:
    """Manages durable background jobs with SQLite disk persistence.
    
    Guarantees that job state, progress (0-100), and result links survive API/worker restarts.
    Sends HMAC-SHA256 signed callbacks upon completion.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.settings = get_settings()
        self.db_path = Path(db_path or "data/jobs.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS background_jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT,
                    status TEXT NOT NULL,
                    progress INTEGER NOT NULL DEFAULT 0,
                    payload TEXT,
                    result TEXT,
                    result_links TEXT,
                    manifest TEXT,
                    callback_url TEXT,
                    error_message TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_job(
        self,
        payload: Dict[str, Any],
        idempotency_key: Optional[str] = None,
        callback_url: Optional[str] = None,
    ) -> str:
        """Atomically inserts and persists a new background job."""
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO background_jobs 
                (job_id, idempotency_key, status, progress, payload, result_links, manifest, callback_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    idempotency_key,
                    "queued",
                    0,
                    json.dumps(payload),
                    json.dumps({}),
                    json.dumps(build_output_manifest(settings={"job_id": job_id})),
                    callback_url,
                    now,
                    now,
                ),
            )
            conn.commit()
        logger.info(f"Durable background job '{job_id}' created and persisted to disk.")
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves durable job record by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM background_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            return {
                "job_id": row["job_id"],
                "idempotency_key": row["idempotency_key"],
                "status": row["status"],
                "progress": row["progress"],
                "payload": json.loads(row["payload"] or "{}"),
                "result": json.loads(row["result"] or "{}") if row["result"] else None,
                "result_links": json.loads(row["result_links"] or "{}"),
                "manifest": json.loads(row["manifest"] or "{}") if row["manifest"] else None,
                "callback_url": row["callback_url"],
                "error_message": row["error_message"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def update_progress(self, job_id: str, progress: int, status: str = "running") -> None:
        """Updates progress (0-100) and status."""
        now = datetime.now(timezone.utc).isoformat()
        clamped_progress = max(0, min(100, progress))
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE background_jobs 
                SET progress = ?, status = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (clamped_progress, status, now, job_id),
            )
            conn.commit()
        logger.info(f"Job '{job_id}' progress updated: {clamped_progress}% ({status})")

    async def complete_job(
        self,
        job_id: str,
        result: Dict[str, Any],
        result_links: Optional[Dict[str, Any]] = None,
        manifest: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Marks job succeeded, stores results & links, and triggers signed callback if provided."""
        now = datetime.now(timezone.utc).isoformat()
        final_manifest = manifest or build_output_manifest(
            settings={"job_id": job_id},
            timings={"completed_at": now},
            ai_generated=False,
        )
        links = result_links or {}

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE background_jobs 
                SET status = 'succeeded', progress = 100, result = ?, result_links = ?, manifest = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (json.dumps(result), json.dumps(links), json.dumps(final_manifest), now, job_id),
            )
            conn.commit()

        logger.info(f"Job '{job_id}' completed successfully.")

        # Trigger callback webhook if registered
        job = self.get_job(job_id)
        if job and job.get("callback_url"):
            await self._dispatch_signed_callback(job)

    async def fail_job(self, job_id: str, error_message: str) -> None:
        """Marks job failed, records error, and sends callback."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE background_jobs 
                SET status = 'failed', progress = 100, error_message = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (error_message, now, job_id),
            )
            conn.commit()

        logger.error(f"Job '{job_id}' failed: {error_message}")
        job = self.get_job(job_id)
        if job and job.get("callback_url"):
            await self._dispatch_signed_callback(job)

    async def _dispatch_signed_callback(self, job: Dict[str, Any]) -> None:
        """Dispatches signed HTTP POST callback to callback_url with X-IncuBrix-Signature."""
        callback_url = job.get("callback_url")
        if not callback_url:
            return

        payload_bytes = json.dumps(job, sort_keys=True).encode("utf-8")
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        secret = self.settings.webhook_signing_secret.encode("utf-8")

        # Signature calculated over timestamp + . + body
        sig_data = timestamp.encode("utf-8") + b"." + payload_bytes
        signature = hmac.new(secret, sig_data, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-IncuBrix-Timestamp": timestamp,
            "X-IncuBrix-Signature": f"sha256={signature}",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(callback_url, content=payload_bytes, headers=headers)
                logger.info(f"Signed callback dispatched for job '{job['job_id']}' (HTTP {res.status_code})")
        except Exception as e:
            logger.warning(f"Failed to dispatch callback to '{callback_url}' for job '{job['job_id']}': {e}")


# Singleton job manager instance
job_manager = PersistentJobManager()
