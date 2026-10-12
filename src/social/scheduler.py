"""After-hours social media posting scheduler."""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

import croniter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.common.config import get_settings
from src.social.queue import get_social_queue, SocialJob
from src.social.x_poster import post_to_twitter
from src.social.stocktwits_poster import post_to_stocktwits
from src.social.threads_poster import post_to_threads
from src.social.formatter import format_for_platform
from src.common.formatter import TradeSignal

logger = logging.getLogger(__name__)


class SocialScheduler:
    """Schedules and executes social media posts during configured hours."""

    def __init__(self):
        self._settings = get_settings()
        self._scheduler = AsyncIOScheduler(timezone="US/Eastern")
        self._running = False
        self._platform_posters = {
            "twitter": post_to_twitter,
            "stocktwits": post_to_stocktwits,
            "threads": post_to_threads,
            # Additional platforms will be added
        }

    def start(self) -> None:
        """Start the scheduler with configured cron jobs."""
        if self._running:
            return

        social = self._settings.social

        # Weekday schedule (Mon-Fri 4PM-9:30AM ET)
        self._scheduler.add_job(
            self._process_queue,
            CronTrigger.from_crontab(social.schedule_cron, timezone="US/Eastern"),
            id="weekday_social",
            name="Weekday Social Media Posting",
            max_instances=1,
            coalesce=True,
        )

        # Weekend schedule
        self._scheduler.add_job(
            self._process_queue,
            CronTrigger.from_crontab(social.weekend_schedule_cron, timezone="US/Eastern"),
            id="weekend_social",
            name="Weekend Social Media Posting",
            max_instances=1,
            coalesce=True,
        )

        # Scheduled job processor (runs every minute)
        self._scheduler.add_job(
            self._process_scheduled_jobs,
            CronTrigger.from_crontab("* * * * *", timezone="US/Eastern"),
            id="process_scheduled",
            name="Process Scheduled Jobs",
            max_instances=1,
        )

        # Queue stats logging (every 5 minutes)
        self._scheduler.add_job(
            self._log_queue_stats,
            CronTrigger.from_crontab("*/5 * * * *", timezone="US/Eastern"),
            id="log_stats",
            name="Log Queue Stats",
            max_instances=1,
        )

        self._scheduler.start()
        self._running = True
        logger.info("Social scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=True)
        self._running = False
        logger.info("Social scheduler stopped")

    def is_posting_window(self) -> bool:
        """Check if current time is within posting window."""
        now = datetime.now(timezone.utc).astimezone()
        eastern = now.astimezone(timezone(timedelta(hours=-5)))  # EST
        # Could also use pytz for proper DST handling

        # Check cron iter
        weekday_cron = croniter.croniter(self._settings.social.schedule_cron, eastern)
        weekend_cron = croniter.croniter(self._settings.social.weekend_schedule_cron, eastern)

        # Simple check: if next run is within a few minutes, we're in window
        next_weekday = weekday_cron.get_next(datetime)
        next_weekend = weekend_cron.get_next(datetime)
        next_run = min(next_weekday, next_weekend)

        return (next_run - eastern).total_seconds() < 300  # Within 5 min of scheduled run

    async def _process_queue(self) -> None:
        """Process queued social media jobs."""
        logger.info("Processing social media queue...")

        queue = await get_social_queue()
        jobs = await queue.dequeue(count=20)

        if not jobs:
            logger.debug("No jobs in queue")
            return

        logger.info(f"Processing {len(jobs)} social jobs")

        for job in jobs:
            try:
                await self._process_job(job)
            except Exception as e:
                logger.error(f"Error processing job {job.id}: {e}")
                await queue.requeue(job, delay=60)  # Retry in 1 minute

    async def _process_job(self, job: SocialJob) -> None:
        """Process a single social media job across all platforms."""
        # Reconstruct TradeSignal from dict
        signal = TradeSignal(**job.signal)

        results = {}
        for platform in job.platforms:
            poster = self._platform_posters.get(platform)
            if not poster:
                logger.warning(f"No poster for platform: {platform}")
                results[platform] = False
                continue

            try:
                formatted = format_for_platform(signal, platform)
                success = await poster(formatted, signal)
                results[platform] = success

                if success:
                    logger.info(f"Posted to {platform}: {job.id}")
                else:
                    logger.warning(f"Failed to post to {platform}: {job.id}")

            except Exception as e:
                logger.error(f"Error posting to {platform}: {e}")
                results[platform] = False

        # Check if all succeeded
        all_success = all(results.values())
        if not all_success:
            # Requeue with delay for retry
            queue = await get_social_queue()
            await queue.requeue(job, delay=300)  # 5 min delay
        else:
            logger.debug(f"Job completed successfully: {job.id}")

    async def _process_scheduled_jobs(self) -> None:
        """Move due scheduled jobs to main queue."""
        queue = await get_social_queue()
        moved = await queue.process_scheduled()
        if moved:
            logger.info(f"Moved {moved} scheduled jobs to queue")

    async def _log_queue_stats(self) -> None:
        """Log queue statistics."""
        queue = await get_social_queue()
        stats = await queue.get_queue_stats()
        logger.info(f"Social queue stats: {stats}")

    async def trigger_immediate_post(self, signal: TradeSignal, platforms: Optional[list] = None) -> None:
        """Trigger immediate post (bypass scheduler) for testing."""
        queue = await get_social_queue()
        await queue.enqueue(
            signal=signal.__dict__,
            source="manual",
            timestamp=time.time(),
            platforms=platforms,
            priority=100,  # High priority
        )
        logger.info("Triggered immediate social post")


# Global instance
_social_scheduler: Optional[SocialScheduler] = None


def get_social_scheduler() -> SocialScheduler:
    """Get or create the global social scheduler."""
    global _social_scheduler
    if _social_scheduler is None:
        _social_scheduler = SocialScheduler()
    return _social_scheduler


async def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_social_scheduler()
    scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    global _social_scheduler
    if _social_scheduler:
        _social_scheduler.stop()
        _social_scheduler = None