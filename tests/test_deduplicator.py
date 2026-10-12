"""Tests for deduplicator module."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.common.deduplicator import Deduplicator, get_deduplicator
from src.common.formatter import TradeSignal


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)  # First call returns True (new)
    redis.exists = AsyncMock(return_value=0)
    redis.delete = AsyncMock(return_value=1)
    redis.scan_iter = AsyncMock(return_value=iter([]))
    return redis


@pytest.fixture
def deduplicator(mock_redis):
    """Create deduplicator with mocked Redis."""
    with patch('src.common.deduplicator.get_redis') as mock_get:
        mock_client = MagicMock()
        mock_client.client = mock_redis
        mock_get.return_value = mock_client
        yield Deduplicator()


class TestDeduplicator:
    """Test deduplication logic."""

    @pytest.mark.asyncio
    async def test_first_message_not_duplicate(self, deduplicator, mock_redis):
        """First message should not be duplicate."""
        mock_redis.set.return_value = True
        result = await deduplicator.is_duplicate("test signal content", "discord:123")
        assert result is False
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_message_is_duplicate(self, deduplicator, mock_redis):
        """Second identical message should be duplicate."""
        mock_redis.set.return_value = False  # Key already exists
        result = await deduplicator.is_duplicate("test signal content", "discord:123")
        assert result is True

    @pytest.mark.asyncio
    async def test_different_content_not_duplicate(self, deduplicator, mock_redis):
        """Different content should not be duplicate."""
        mock_redis.set.return_value = True
        result1 = await deduplicator.is_duplicate("signal 1", "discord:123")
        result2 = await deduplicator.is_duplicate("signal 2", "discord:123")
        assert result1 is False
        assert result2 is False
        assert mock_redis.set.call_count == 2

    @pytest.mark.asyncio
    async def test_hash_consistency(self, deduplicator):
        """Same content should produce same hash."""
        hash1 = deduplicator._hash_content("test content")
        hash2 = deduplicator._hash_content("test content")
        assert hash1 == hash2
        assert len(hash1) == 32  # MD5 hex length

    @pytest.mark.asyncio
    async def test_different_hash_for_different_content(self, deduplicator):
        """Different content should produce different hash."""
        hash1 = deduplicator._hash_content("content 1")
        hash2 = deduplicator._hash_content("content 2")
        assert hash1 != hash2

    @pytest.mark.asyncio
    async def test_check_only(self, deduplicator, mock_redis):
        """Check-only should not modify Redis."""
        mock_redis.exists.return_value = 1
        result = await deduplicator.check_only("test content")
        assert result is True
        mock_redis.exists.assert_called_once()
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_clear(self, deduplicator, mock_redis):
        """Clear should remove deduplication entry."""
        mock_redis.delete.return_value = 1
        result = await deduplicator.clear("test content")
        assert result is True
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_stats(self, deduplicator, mock_redis):
        """Stats should return correct structure."""
        mock_redis.scan_iter = AsyncMock(return_value=iter(["key1", "key2", "key3"]))
        stats = await deduplicator.get_stats()
        assert stats["total_tracked"] == 3
        assert "ttl_seconds" in stats
        assert "hash_algorithm" in stats


class TestDeduplicatorSingleton:
    """Test global deduplicator singleton."""

    def test_get_deduplicator_returns_same_instance(self):
        """get_deduplicator should return same instance."""
        d1 = get_deduplicator()
        d2 = get_deduplicator()
        assert d1 is d2