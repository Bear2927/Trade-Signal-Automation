"""Redis connection management with connection pooling and health checks."""

import logging
from contextlib import asynccontextmanager
from typing import Optional

import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

from src.common.config import get_settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Manages Redis connections with pooling and health monitoring."""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._settings = get_settings()

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._pool is not None:
            return

        self._pool = ConnectionPool(
            host=self._settings.redis.host,
            port=self._settings.redis.port,
            db=self._settings.redis.db,
            password=self._settings.redis.password or None,
            max_connections=self._settings.redis.max_connections,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        self._client = redis.Redis(connection_pool=self._pool)
        await self.health_check()
        logger.info("Redis connection pool initialized")

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        try:
            if self._client:
                await self._client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False
        return False

    @property
    def client(self) -> redis.Redis:
        """Get the Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not initialized. Call initialize() first.")
        return self._client

    async def close(self) -> None:
        """Close all connections."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        logger.info("Redis connections closed")

    @asynccontextmanager
    async def transaction(self):
        """Context manager for Redis transactions."""
        async with self._client.pipeline(transaction=True) as pipe:
            try:
                yield pipe
                await pipe.execute()
            except Exception:
                await pipe.reset()
                raise


# Global instance
_redis_client: Optional[RedisClient] = None


async def get_redis() -> RedisClient:
    """Get or create the global Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.initialize()
    return _redis_client


async def close_redis() -> None:
    """Close the global Redis client."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None