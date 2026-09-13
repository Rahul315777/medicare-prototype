"""
Redis Configuration
- Connection Manager
- Session Storage
- Cache
- Rate Limiting
"""

import asyncio
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings


# ==========================================================
# Global Redis Client
# ==========================================================

redis_client: Optional[redis.Redis] = None

# The event loop the current `redis_client` was opened against. A
# redis.asyncio connection is bound to whichever asyncio event loop is
# running when it's created; reusing it from a *different* event loop raises
# "Event loop is closed". In production there's only ever one event loop
# (uvicorn's), so this never matters there — it only matters under test
# runners (pytest-asyncio) that give each test function its own event loop.
_redis_client_loop: Optional[asyncio.AbstractEventLoop] = None


# ==========================================================
# Get Redis Client
# ==========================================================

async def get_redis() -> redis.Redis:
    """
    Return a singleton Redis client, reused within the current event loop.

    Creates the connection only once per event loop and reuses it. If the
    previously-created client belongs to an event loop that isn't the one
    actually running right now (it would raise "Event loop is closed" on
    use), it's discarded and a fresh client is opened against the current
    loop instead.
    """

    global redis_client, _redis_client_loop

    current_loop = asyncio.get_running_loop()

    if redis_client is not None and _redis_client_loop is not current_loop:
        try:
            await redis_client.aclose()
        except Exception:
            pass  # the old loop is already gone; nothing left to clean up
        redis_client = None

    if redis_client is None:

        redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            encoding="utf-8",
        )

        # Verify connection
        await redis_client.ping()
        _redis_client_loop = current_loop

    return redis_client


# ==========================================================
# Close Redis Client
# ==========================================================

async def close_redis() -> None:
    """
    Gracefully close Redis connection.
    """

    global redis_client, _redis_client_loop

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        _redis_client_loop = None