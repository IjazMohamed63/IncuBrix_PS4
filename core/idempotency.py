import asyncio
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, Optional, Tuple
from pydantic import BaseModel, Field

from core.errors import ErrorCode, IncuBrixError
from core.logging import get_logger

logger = get_logger("idempotency")


class IdempotencyRecord(BaseModel):
    key: str
    body_hash: str
    status: str  # processing, completed, failed
    response_status: int = 200
    response_body: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class IdempotencyManager:
    """Provides atomic idempotency locking and result replay with payload collision detection."""

    def __init__(self):
        self._records: Dict[str, IdempotencyRecord] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    def compute_hash(self, payload: Any) -> str:
        """Computes deterministic SHA256 hash of payload."""
        if isinstance(payload, bytes):
            return hashlib.sha256(payload).hexdigest()
        if isinstance(payload, str):
            return hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if isinstance(payload, dict) or isinstance(payload, list):
            serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        serialized = str(payload)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    async def _get_key_lock(self, key: str) -> asyncio.Lock:
        async with self._global_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def acquire_or_replay(
        self,
        key: str,
        payload: Any,
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[asyncio.Lock]]:
        """Atomically checks if request is duplicate, in-flight, or conflicting.

        Returns (is_replayed, cached_response, lock_to_release_on_complete).
        If is_replayed is True, cached_response is the prior result and caller must NOT re-execute.
        If is_replayed is False, lock_to_release_on_complete must be held during execution.
        """
        body_hash = self.compute_hash(payload)
        key_lock = await self._get_key_lock(key)

        await key_lock.acquire()

        record = self._records.get(key)
        if record:
            # Check for body collision
            if record.body_hash != body_hash:
                key_lock.release()
                logger.error(f"Idempotency conflict for key '{key}': body hash mismatch")
                raise IncuBrixError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message=f"Idempotency-Key '{key}' was already used with a different request payload.",
                    status_code=409,
                    details={"idempotency_key": key, "conflict": "payload_mismatch"},
                )

            # Same key and same body: replay
            key_lock.release()
            logger.info(f"Idempotent replay for key '{key}'")
            return True, record.response_body, None

        # New key: create processing record and return lock to caller
        self._records[key] = IdempotencyRecord(
            key=key,
            body_hash=body_hash,
            status="processing",
        )
        return False, None, key_lock

    async def record_completion(
        self,
        key: str,
        response_body: Dict[str, Any],
        response_status: int = 200,
        status_code: Optional[int] = None,
        lock: Optional[asyncio.Lock] = None,
    ) -> None:
        """Stores final response body and releases per-key lock."""
        final_status = status_code if status_code is not None else response_status
        try:
            if key in self._records:
                record = self._records[key]
                record.status = "completed"
                record.response_body = response_body
                record.response_status = final_status
                logger.info(f"Recorded completed response for idempotency key '{key}'")
        finally:
            if lock and lock.locked():
                lock.release()


    async def record_failure(
        self,
        key: str,
        error_dict: Dict[str, Any],
        status_code: int = 500,
        lock: Optional[asyncio.Lock] = None,
    ) -> None:
        """Records failed execution state and releases lock."""
        try:
            if key in self._records:
                record = self._records[key]
                record.status = "failed"
                record.response_body = error_dict
                record.response_status = status_code
        finally:
            if lock and lock.locked():
                lock.release()

    def clear(self) -> None:
        self._records.clear()
        self._locks.clear()


# Global idempotency manager singleton
idempotency_manager = IdempotencyManager()
