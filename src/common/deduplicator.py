"""Deduplication using Redis SETNX with TTL."""

import hashlib
import logging
from typing import Optional

from src.common.redis_client import get_redis
from src.common.config import get_settings

logger = logging.getLogger(__name__)


class Deduplicator:
    """Handles content deduplication using Redis SETNX with TTL."""

    def __init__(self):
        self._settings = get_settings()
        self._prefix = "dedup:signal:"

    def _hash_content(self, content: str) -> str:
        """Generate hash of content for deduplication."""
        algorithm = self._settings.deduplication.hash_algorithm
        if algorithm == "md5":
            return hashlib.md5(content.encode("utf-8")).hexdigest()
        elif algorithm == "sha256":
            return hashlib.sha256(content.encode("utf-8")).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")

    async def is_duplicate(self, content: str, source: str = "") -> bool:
        """
        Check if content is a duplicate.

        Returns True if duplicate (already seen), False if new.
        Uses SETNX for atomic check-and-set.
        """
        redis_client = await get_redis()
        content_hash = self._hash_content(content)
        key = f"{self._prefix}{content_hash}"
        ttl = self._settings.deduplication.ttl_seconds

        # SETNX returns True if key was set (new), False if key existed (duplicate)
        is_new = await redis_client.client.set(key, source, nx=True, ex=ttl)

        if is_new:
            logger.debug(f"New signal registered: {content_hash[:8]}... (source: {source})")
            return False
        else:
            logger.debug(f"Duplicate signal detected: {content_hash[:8]}... (source: {source})")
            return True

    async def check_only(self, content: str) -> bool:
        """Check if content exists without setting (read-only)."""
        redis_client = await get_redis()
        content_hash = self._hash_content(content)
        key = f"{self._prefix}{content_hash}"
        exists = await redis_client.client.exists(key)
        return bool(exists)

    async def clear(self, content: str) -> bool:
        """Manually clear a deduplication entry (for testing)."""
        redis_client = await get_redis()
        content_hash = self._hash_content(content)
        key = f"{self._prefix}{content_hash}"
        result = await redis_client.client.delete(key)
        return bool(result)

    async def get_stats(self) -> dict:
        """Get deduplication statistics."""
        redis_client = await get_redis()
        pattern = f"{self._prefix}*"
        keys = []
        async for key in redis_client.client.scan_iter(match=pattern):
            keys.append(key)
        return {
            "total_tracked": len(keys),
            "ttl_seconds": self._settings.deduplication.ttl_seconds,
            "hash_algorithm": self._settings.deduplication.hash_algorithm,
        }


# Global instance
_deduplicator: Optional[Deduplicator] = None


def get_deduplicator() -> Deduplicator:
    """Get or create the global deduplicator."""
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = Deduplicator()
    return _deduplicator