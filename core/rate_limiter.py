import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple
from core.errors import ErrorCode, IncuBrixError, PlatformRateLimitError, PlatformUnavailableError
from core.logging import get_logger

logger = get_logger("rate_limiter")


class RateLimiterAndCircuitBreaker:
    """Manages token-bucket rate limits, backoff windows on 429, and 5-failure circuit breaking."""

    def __init__(self):
        # Key -> next allowed epoch datetime
        self._blocked_until: Dict[str, datetime] = {}
        # Key -> consecutive failure count
        self._consecutive_failures: Dict[str, int] = {}
        # Concurrency lock
        self._lock = asyncio.Lock()

    async def record_429_backoff(
        self,
        key: str,
        retry_after_seconds: int = 30,
    ) -> datetime:
        """Persists a backoff block window for a destination or connector key."""
        async with self._lock:
            now = datetime.now(timezone.utc)
            reset_at = now + timedelta(seconds=retry_after_seconds)
            self._blocked_until[key] = reset_at
            logger.warning(
                f"Rate limit 429 recorded for '{key}'. Block window active until {reset_at.isoformat()} ({retry_after_seconds}s)"
            )
            return reset_at

    async def check_availability(self, key: str) -> None:
        """Verifies if key is allowed to make requests.

        Raises PlatformRateLimitError if blocked by backoff window,
        or PlatformUnavailableError if circuit-breaker is tripped.
        """
        async with self._lock:
            now = datetime.now(timezone.utc)

            # 1. Check active 429 backoff window
            blocked_until = self._blocked_until.get(key)
            if blocked_until:
                if now < blocked_until:
                    remaining = int((blocked_until - now).total_seconds())
                    logger.info(f"Call blocked for '{key}': rate limit window active ({remaining}s remaining)")
                    raise PlatformRateLimitError(
                        message=f"Rate limit backoff active for '{key}'. Try again in {remaining}s.",
                        retry_after=remaining,
                    )
                else:
                    # Window elapsed
                    del self._blocked_until[key]

            # 2. Check circuit-breaker (5 consecutive failures)
            failures = self._consecutive_failures.get(key, 0)
            if failures >= 5:
                logger.error(f"Circuit breaker OPEN for '{key}' ({failures} consecutive failures). Disallowing requests.")
                raise PlatformUnavailableError(
                    message=f"Circuit breaker tripped for '{key}' after {failures} consecutive failures.",
                    consecutive_failures=failures,
                )

    async def record_failure(self, key: str) -> int:
        """Increments consecutive failure count towards circuit-breaker limit."""
        async with self._lock:
            count = self._consecutive_failures.get(key, 0) + 1
            self._consecutive_failures[key] = count
            logger.warning(f"Failure count for '{key}' is now {count}/5")
            return count

    async def record_success(self, key: str) -> None:
        """Resets consecutive failure count upon successful platform interaction."""
        async with self._lock:
            if key in self._consecutive_failures:
                del self._consecutive_failures[key]

    async def reset(self, key: Optional[str] = None) -> None:
        """Clears rate limiter and circuit breaker state."""
        async with self._lock:
            if key:
                self._blocked_until.pop(key, None)
                self._consecutive_failures.pop(key, None)
            else:
                self._blocked_until.clear()
                self._consecutive_failures.clear()


# Global rate limiter and circuit breaker singleton
rate_limiter = RateLimiterAndCircuitBreaker()
