"""Tests for social media scheduler."""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from src.social.queue import SocialQueue, SocialJob, get_social_queue
from src.social.scheduler import SocialScheduler, get_social_scheduler
from src.common.formatter import TradeSignal


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.zadd = AsyncMock(return_value=1)
    redis.zpopmin = AsyncMock(return_value=[])
    redis.zcard = AsyncMock(return_value=0)
    redis.scard = AsyncMock(return_value=0)
    redis.llen = AsyncMock(return_value=0)
    redis.zrem = AsyncMock(return_value=1)
    redis.zrangebyscore = AsyncMock(return_value=[])
    redis.lpush = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def social_queue(mock_redis):
    """Create social queue with mocked Redis."""
    with patch('src.social.queue.get_redis') as mock_get:
        mock_client = MagicMock()
        mock_client.client = mock_redis
        mock_get.return_value = mock_client
        yield SocialQueue()


@pytest.fixture
def sample_signal():
    """Create a sample trade signal."""
    return TradeSignal(
        raw_text="AAPL long entry 150 target 160 stop 145",
        ticker="AAPL",
        direction="LONG",
        entry="150",
        target="160",
        stop_loss="145",
        source="Discord#123",
        author="trader123",
    )


class TestSocialQueue:
    """Test social media job queue."""

    @pytest.mark.asyncio
    async def test_enqueue_creates_job(self, social_queue, mock_redis, sample_signal):
        """Enqueue should create and store job."""
        job_id = await social_queue.enqueue(
            signal=sample_signal.__dict__,
            source="discord",
            timestamp=time.time(),
            platforms=["twitter", "stocktwits"],
            priority=10,
        )

        assert job_id.startswith("discord:")
        mock_redis.zadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_dequeue_returns_jobs(self, social_queue, mock_redis, sample_signal):
        """Dequeue should return jobs from queue."""
        job_data = {
            "id": "test:123",
            "signal": sample_signal.__dict__,
            "source": "discord",
            "timestamp": time.time(),
            "platforms": ["twitter"],
            "priority": 0,
            "attempts": 0,
            "max_attempts": 3,
            "created_at": time.time(),
        }
        import json
        mock_redis.zpopmin.return_value = [(json.dumps(job_data), 0)]

        jobs = await social_queue.dequeue(count=5)

        assert len(jobs) == 1
        assert jobs[0].id == "test:123"
        assert jobs[0].platforms == ["twitter"]

    @pytest.mark.asyncio
    async def test_requeue_increments_attempts(self, social_queue, mock_redis, sample_signal):
        """Requeue should increment attempt counter."""
        job = SocialJob(
            id="test:123",
            signal=sample_signal.__dict__,
            source="discord",
            timestamp=time.time(),
            platforms=["twitter"],
            attempts=1,
            max_attempts=3,
        )

        await social_queue.requeue(job, delay=60)

        # Should be added to scheduled queue with delay
        mock_redis.zadd.assert_called()

    @pytest.mark.asyncio
    async def test_max_attempts_moves_to_dead_letter(self, social_queue, mock_redis, sample_signal):
        """Job exceeding max attempts should go to dead letter."""
        job = SocialJob(
            id="test:123",
            signal=sample_signal.__dict__,
            source="discord",
            timestamp=time.time(),
            platforms=["twitter"],
            attempts=3,
            max_attempts=3,
        )

        await social_queue.requeue(job)

        # Should go to dead letter, not requeue
        mock_redis.lpush.assert_called()

    @pytest.mark.asyncio
    async def test_get_queue_stats(self, social_queue, mock_redis):
        """Get queue stats."""
        mock_redis.zcard.return_value = 5
        mock_redis.scard.return_value = 1
        mock_redis.llen.return_value = 2
        mock_redis.zcard.return_value = 3  # For scheduled

        stats = await social_queue.get_queue_stats()

        assert stats["queued"] == 5
        assert stats["processing"] == 1
        assert stats["dead_letter"] == 2


class TestSocialScheduler:
    """Test social media scheduler."""

    def test_scheduler_initialization(self):
        """Scheduler should initialize with platform posters."""
        scheduler = SocialScheduler()

        assert "twitter" in scheduler._platform_posters
        assert "stocktwits" in scheduler._platform_posters
        assert "threads" in scheduler._platform_posters

    def test_posting_window_check(self):
        """Posting window check should work."""
        scheduler = SocialScheduler()
        # Just verify it runs without error
        result = scheduler.is_posting_window()
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_process_job_calls_posters(self, sample_signal):
        """Process job should call platform posters."""
        with patch('src.social.scheduler.post_to_twitter', new_callable=AsyncMock) as mock_twitter:
            with patch('src.social.scheduler.post_to_stocktwits', new_callable=AsyncMock) as mock_st:
                with patch('src.social.scheduler.post_to_threads', new_callable=AsyncMock) as mock_threads:
                    with patch('src.social.scheduler.get_social_queue') as mock_get_queue:
                        mock_queue = AsyncMock()
                        mock_get_queue.return_value = mock_queue

                        mock_twitter.return_value = True
                        mock_st.return_value = True
                        mock_threads.return_value = True

                        scheduler = SocialScheduler()
                        job = SocialJob(
                            id="test:123",
                            signal=sample_signal.__dict__,
                            source="discord",
                            timestamp=time.time(),
                            platforms=["twitter", "stocktwits", "threads"],
                        )

                        await scheduler._process_job(job)

                        mock_twitter.assert_called_once()
                        mock_st.assert_called_once()
                        mock_threads.assert_called_once()

    @pytest.mark.asyncio
    async def test_failed_post_triggers_requeue(self, sample_signal):
        """Failed post should trigger requeue."""
        with patch('src.social.scheduler.post_to_twitter', new_callable=AsyncMock) as mock_twitter:
            with patch('src.social.scheduler.get_social_queue') as mock_get_queue:
                mock_queue = AsyncMock()
                mock_get_queue.return_value = mock_queue

                mock_twitter.return_value = False  # Simulate failure

                scheduler = SocialScheduler()
                job = SocialJob(
                    id="test:123",
                    signal=sample_signal.__dict__,
                    source="discord",
                    timestamp=time.time(),
                    platforms=["twitter"],
                )

                await scheduler._process_job(job)

                mock_queue.requeue.assert_called_once()


class TestSocialSchedulerSingleton:
    """Test global scheduler singleton."""

    def test_get_social_scheduler_returns_same_instance(self):
        """get_social_scheduler should return same instance."""
        s1 = get_social_scheduler()
        s2 = get_social_scheduler()
        assert s1 is s2