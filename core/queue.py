from typing import Optional
import redis.asyncio as aioredis
from core.config import get_settings
from core.logging import get_logger

logger = get_logger("queue")
settings = get_settings()


async def check_redis_health() -> bool:
    """Probes the Redis service for health check."""
    client: Optional[aioredis.Redis] = None
    try:
        client = aioredis.from_url(settings.redis_url, socket_connect_timeout=2)
        pong = await client.ping()
        return bool(pong)
    except Exception as e:
        logger.warning(f"Redis health check failed: {str(e)}")
        return False
    finally:
        if client:
            await client.aclose()
