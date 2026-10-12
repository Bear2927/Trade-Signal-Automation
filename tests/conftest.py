"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Use fakeredis for tests
os.environ["FAKEREDIS"] = "1"

# Mock settings before any imports
import src.common.config as config_module

# Create a mock settings object
mock_settings = MagicMock()
mock_settings.discord.user_token = "test_token"
mock_settings.discord.target_channel_ids = ["123456789"]
mock_settings.discord.premium_webhook_url = "https://discord.com/api/webhooks/test"
mock_settings.redis.host = "localhost"
mock_settings.redis.port = 6379
mock_settings.redis.db = 0
mock_settings.redis.password = ""
mock_settings.redis.max_connections = 20
mock_settings.deduplication.ttl_seconds = 30
mock_settings.deduplication.hash_algorithm = "md5"
mock_settings.webhook.url = "https://discord.com/api/webhooks/test"
mock_settings.webhook.rate_limit_per_second = 30
mock_settings.webhook.max_retries = 3
mock_settings.webhook.retry_delay_seconds = 1.0
mock_settings.social.schedule_cron = "*/15 16-23,0-9 * * 1-5"
mock_settings.social.weekend_schedule_cron = "*/30 * * * 0,6"
mock_settings.social.twitter.enabled = False
mock_settings.social.stocktwits.enabled = False
mock_settings.social.threads.enabled = False
mock_settings.social.reddit.enabled = False
mock_settings.social.telegram.enabled = False
mock_settings.social.linkedin.enabled = False
mock_settings.social.email.enabled = False
mock_settings.logging.level = "INFO"
mock_settings.logging.format = "json"
mock_settings.logging.file = "./logs/app.log"
mock_settings.logging.max_bytes = 10485760
mock_settings.logging.backup_count = 5
mock_settings.monitoring.prometheus_port = 9090
mock_settings.monitoring.health_check_port = 8080

# Patch get_settings to return mock
config_module._cached_settings = mock_settings


@pytest.fixture(autouse=True)
def mock_settings_fixture():
    """Auto-use fixture to mock settings for all tests."""
    return mock_settings