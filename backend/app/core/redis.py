"""
Redis Configuration
- Connection Manager
- Session Storage
- Cache
- Rate Limiting
"""

from typing import Optional

import redis.asyncio as redis

from app.core.config import settings


# ==========================================================
# Global Redis Client
# ==========================================================

redis_client: Optional[redis.Redis] = None


# ==========================================================
# Get Redis Client
# ==========================================================

async def get_redis() -> redis.Redis:
    """
    Return a singleton Redis client.

    Creates the connection only once and
    reuses it throughout the application.
    """

    global redis_client

    if redis_client is None:

        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8",
        )

        # Verify connection
        await redis_client.ping()

    return redis_client


# ==========================================================
# Close Redis Client
# ==========================================================

async def close_redis() -> None:
    """
    Gracefully close Redis connection.
    """

    global redis_client

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None