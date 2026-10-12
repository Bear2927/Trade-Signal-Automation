"""Rate limiting for social media APIs."""

import asyncio
import time
from collections import deque
from typing import Dict, Optional

from src.common.config import get_settings

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, burst: int):
        """
        Args:
            rate: Tokens per second
            burst: Maximum bucket size
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def take(self, tokens: int = 1) -> float:
        """Take tokens from bucket, blocking until available.

        Returns:
            Time waited in seconds
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.burst, self.tokens + elapsed * self.rate)
            self.last_update = now

            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0

            # Need to wait
            wait_time = (tokens - self.tokens) / self.rate
            self.tokens = 0
            return wait_time

    async def acquire(self, tokens: int = 1) -> None:
        """Acquire tokens, waiting if necessary."""
        wait_time = await self.take(tokens)
        if wait_time > 0:
            await asyncio.sleep(wait_time)


class RateLimiter:
    """Manages rate limiters for multiple platforms."""

    def __init__(self):
        self._settings = get_settings()
        self._buckets: Dict[str, TokenBucket] = {}
        self._initialize_buckets()

    def _initialize_buckets(self) -> None:
        """Initialize token buckets for each platform."""
        social = self._settings.social

        # X/Twitter: 300 requests per 15 min = 0.33/sec, burst 50
        if social.twitter.enabled:
            self._buckets["twitter"] = TokenBucket(rate=0.33, burst=50)

        # Stocktwits: ~100/hour = 0.028/sec, burst 10
        if social.stocktwits.enabled:
            self._buckets["stocktwits"] = TokenBucket(rate=0.028, burst=10)

        # Threads: ~200/hour = 0.055/sec, burst 20
        if social.threads.enabled:
            self._buckets["threads"] = TokenBucket(rate=0.055, burst=20)

        # Reddit: 60/min = 1/sec, burst 10
        if social.reddit.enabled:
            self._buckets["reddit"] = TokenBucket(rate=1.0, burst=10)

        # Telegram: 30/sec, burst 30
        if social.telegram.enabled:
            self._buckets["telegram"] = TokenBucket(rate=30.0, burst=30)

    async def acquire(self, platform: str, tokens: int = 1) -> None:
        """Acquire rate limit token for platform."""
        bucket = self._buckets.get(platform.lower())
        if bucket:
            await bucket.acquire(tokens)
        else:
            # No rate limit configured, allow
            pass

    def get_status(self) -> Dict[str, dict]:
        """Get current rate limiter status."""
        return {
            platform: {
                "tokens_available": bucket.tokens,
                "rate_per_sec": bucket.rate,
                "burst": bucket.burst,
            }
            for platform, bucket in self._buckets.items()
        }


# Global instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter