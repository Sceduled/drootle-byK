"""
Redis client configuration.
Provides async Redis client using aioredis.
"""
import logging
import redis.asyncio as redis
from .config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def get_redis():
    """Return the global Redis client instance."""
    return redis_client

async def test_connection() -> bool:
    """Test the Redis connection."""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis connection test failed: {e}")
        return False
