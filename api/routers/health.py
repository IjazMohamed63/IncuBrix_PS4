from fastapi import APIRouter, Response, status
from core.database import check_database_health
from core.queue import check_redis_health
from core.storage import storage
from core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """Liveness probe confirming the HTTP server is responsive."""
    return {"status": "pass"}


@router.get("/ready")
async def readiness_check(response: Response):
    """Deep readiness probe verifying database, redis queue, and S3 object storage."""
    db_ok = await check_database_health()
    redis_ok = await check_redis_health()
    storage_ok = storage.check_health()

    all_ready = db_ok and redis_ok and storage_ok

    if not all_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if all_ready else "not_ready",
        "simulation_mode": settings.simulation_mode,
        "checks": {
            "database": "up" if db_ok else "down",
            "queue": "up" if redis_ok else "down",
            "storage": "up" if storage_ok else "down",
        },
    }
