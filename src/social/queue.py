"""Redis-backed job queue for social media posting."""

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any

from src.common.redis_client import get_redis
from src.common.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class SocialJob:
    """Social media posting job."""
    id: str
    signal: Dict[str, Any]
    source: str
    timestamp: float
    platforms: List[str]
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = 0.0
    scheduled_for: Optional[float] = None

    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()


class SocialQueue:
    """Redis-backed priority queue for social media jobs."""

    QUEUE_KEY = "social:queue"
    PROCESSING_KEY = "social:processing"
    DEAD_LETTER_KEY = "social:dead_letter"
    PRIORITY_KEY = "social:priority"

    def __init__(self):
        self._settings = get_settings()

    async def enqueue(
        self,
        signal: Dict[str, Any],
        source: str,
        timestamp: float,
        platforms: Optional[List[str]] = None,
        priority: int = 0,
    ) -> str:
        """Add a job to the queue."""
        redis_client = await get_redis()

        job = SocialJob(
            id=f"{source}:{int(timestamp * 1000)}",
            signal=signal,
            source=source,
            timestamp=timestamp,
            platforms=platforms or self._get_enabled_platforms(),
            priority=priority,
        )

        job_data = json.dumps(asdict(job))

        # Use sorted set for priority queue (score = -priority for max-heap behavior)
        await redis_client.client.zadd(self.QUEUE_KEY, {job_data: -priority})

        logger.debug(f"Enqueued social job: {job.id} for platforms: {job.platforms}")
        return job.id

    def _get_enabled_platforms(self) -> List[str]:
        """Get list of enabled social platforms from config."""
        social = self._settings.social
        platforms = []
        if social.twitter.enabled: platforms.append("twitter")
        if social.stocktwits.enabled: platforms.append("stocktwits")
        if social.threads.enabled: platforms.append("threads")
        if social.reddit.enabled: platforms.append("reddit")
        if social.telegram.enabled: platforms.append("telegram")
        if social.linkedin.enabled: platforms.append("linkedin")
        if social.email.enabled: platforms.append("email")
        return platforms

    async def dequeue(self, count: int = 10) -> List[SocialJob]:
        """Get highest priority jobs from queue."""
        redis_client = await get_redis()

        # Use ZPOPMIN to get highest priority (lowest score = highest priority)
        jobs_data = await redis_client.client.zpopmin(self.QUEUE_KEY, count=count)

        jobs = []
        for job_data, score in jobs_data:
            try:
                job_dict = json.loads(job_data)
                job = SocialJob(**job_dict)
                jobs.append(job)
            except Exception as e:
                logger.error(f"Failed to parse job: {e}")

        return jobs

    async def requeue(self, job: SocialJob, delay: float = 0) -> None:
        """Requeue a job with optional delay."""
        redis_client = await get_redis()

        job.attempts += 1
        if job.attempts >= job.max_attempts:
            await self.move_to_dead_letter(job, "Max attempts exceeded")
            return

        job_data = json.dumps(asdict(job))
        scheduled_score = -(job.priority)  # Keep same priority

        if delay > 0:
            # Schedule for later using a separate sorted set with timestamp score
            scheduled_for = time.time() + delay
            await redis_client.client.zadd("social:scheduled", {job_data: scheduled_for})
        else:
            await redis_client.client.zadd(self.QUEUE_KEY, {job_data: scheduled_score})

    async def move_to_dead_letter(self, job: SocialJob, reason: str) -> None:
        """Move failed job to dead letter queue."""
        redis_client = await get_redis()
        job_data = json.dumps({
            **asdict(job),
            "failure_reason": reason,
            "failed_at": time.time(),
        })
        await redis_client.client.lpush(self.DEAD_LETTER_KEY, job_data)
        logger.warning(f"Job moved to dead letter: {job.id} - {reason}")

    async def get_queue_stats(self) -> Dict[str, int]:
        """Get queue statistics."""
        redis_client = await get_redis()

        queue_len = await redis_client.client.zcard(self.QUEUE_KEY)
        processing_len = await redis_client.client.scard(self.PROCESSING_KEY)
        dead_letter_len = await redis_client.client.llen(self.DEAD_LETTER_KEY)
        scheduled_len = await redis_client.client.zcard("social:scheduled")

        return {
            "queued": queue_len,
            "processing": processing_len,
            "dead_letter": dead_letter_len,
            "scheduled": scheduled_len,
        }

    async def process_scheduled(self) -> int:
        """Move due scheduled jobs to main queue."""
        redis_client = await get_redis()
        now = time.time()

        # Get jobs that are due
        due_jobs = await redis_client.client.zrangebyscore(
            "social:scheduled", 0, now, start=0, num=100
        )

        moved = 0
        for job_data in due_jobs:
            # Remove from scheduled
            await redis_client.client.zrem("social:scheduled", job_data)
            # Add to main queue with priority
            try:
                job_dict = json.loads(job_data)
                priority = job_dict.get("priority", 0)
                await redis_client.client.zadd(self.QUEUE_KEY, {job_data: -priority})
                moved += 1
            except Exception as e:
                logger.error(f"Failed to process scheduled job: {e}")

        return moved


# Global instance
_social_queue: Optional[SocialQueue] = None


async def get_social_queue() -> SocialQueue:
    """Get or create the global social queue."""
    global _social_queue
    if _social_queue is None:
        _social_queue = SocialQueue()
    return _social_queue