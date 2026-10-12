"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DiscordSettings(BaseSettings):
    user_token: str = ""
    target_channel_ids: List[str] = Field(default_factory=list)
    premium_webhook_url: str = ""


class MessengerSettings(BaseSettings):
    target_chat_url: str = "https://www.facebook.com/messages/t/"
    session_path: str = "./fb_session"
    headless: bool = True
    proxy: str = ""


class RedisSettings(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    max_connections: int = 20


class DeduplicationSettings(BaseSettings):
    ttl_seconds: int = 30
    hash_algorithm: str = "md5"


class WebhookSettings(BaseSettings):
    url: str = ""
    rate_limit_per_second: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0


class TwitterSettings(BaseSettings):
    enabled: bool = False
    api_key: str = ""
    api_secret: str = ""
    bearer_token: str = ""
    access_token: str = ""
    refresh_token: str = ""
    max_chars: int = 280


class StocktwitsSettings(BaseSettings):
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""
    max_chars: int = 2000


class ThreadsSettings(BaseSettings):
    enabled: bool = False
    app_id: str = ""
    app_secret: str = ""
    user_access_token: str = ""
    max_chars: int = 500


class RedditSettings(BaseSettings):
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    refresh_token: str = ""
    target_subreddits: List[str] = Field(default_factory=lambda: ["wallstreetbets", "stocks", "options"])


class TelegramSettings(BaseSettings):
    enabled: bool = False
    bot_token: str = ""
    chat_ids: List[str] = Field(default_factory=list)


class LinkedInSettings(BaseSettings):
    enabled: bool = False
    client_id: str = ""
    client_secret: str = ""
    access_token: str = ""


class EmailSettings(BaseSettings):
    enabled: bool = False
    sendgrid_api_key: str = ""
    from_email: str = ""
    from_name: str = "StockTradingSignals"
    subscriber_list_id: str = ""
    schedule_cron: str = "0 6 * * 1-5"


class SocialSettings(BaseSettings):
    schedule_cron: str = "*/15 16-23,0-9 * * 1-5"
    weekend_schedule_cron: str = "*/30 * * * 0,6"
    twitter: TwitterSettings = Field(default_factory=TwitterSettings)
    stocktwits: StocktwitsSettings = Field(default_factory=StocktwitsSettings)
    threads: ThreadsSettings = Field(default_factory=ThreadsSettings)
    reddit: RedditSettings = Field(default_factory=RedditSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    linkedin: LinkedInSettings = Field(default_factory=LinkedInSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)


class LoggingSettings(BaseSettings):
    level: str = "INFO"
    format: str = "json"
    file: str = "./logs/app.log"
    max_bytes: int = 10485760
    backup_count: int = 5


class MonitoringSettings(BaseSettings):
    prometheus_port: int = 9090
    health_check_port: int = 8080


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",  # Double underscore for nested config
        extra="ignore",
    )

    discord: DiscordSettings = Field(default_factory=DiscordSettings)
    messenger: MessengerSettings = Field(default_factory=MessengerSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    deduplication: DeduplicationSettings = Field(default_factory=DeduplicationSettings)
    webhook: WebhookSettings = Field(default_factory=WebhookSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    monitoring: MonitoringSettings = Field(default_factory=MonitoringSettings)


# Global cached settings instance
_cached_settings: Settings | None = None


def get_settings() -> Settings:
    """Get cached settings instance."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
    return _cached_settings


def load_config_from_yaml(config_path: str = "config/config.yaml") -> Settings:
    """Load settings from YAML file (overrides env vars)."""
    import yaml

    global _cached_settings

    path = Path(config_path)
    if not path.exists():
        return get_settings()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    # Create nested settings objects from YAML sections
    kwargs = {}

    if "discord" in data:
        kwargs["discord"] = DiscordSettings(**data["discord"])
    if "messenger" in data:
        kwargs["messenger"] = MessengerSettings(**data["messenger"])
    if "redis" in data:
        kwargs["redis"] = RedisSettings(**data["redis"])
    if "deduplication" in data:
        kwargs["deduplication"] = DeduplicationSettings(**data["deduplication"])
    if "webhook" in data:
        kwargs["webhook"] = WebhookSettings(**data["webhook"])
    if "social" in data:
        social_data = data["social"]
        social_kwargs = {}
        for platform in ["twitter", "stocktwits", "threads", "reddit", "telegram", "linkedin", "email"]:
            if platform in social_data:
                platform_class = {
                    "twitter": TwitterSettings,
                    "stocktwits": StocktwitsSettings,
                    "threads": ThreadsSettings,
                    "reddit": RedditSettings,
                    "telegram": TelegramSettings,
                    "linkedin": LinkedInSettings,
                    "email": EmailSettings,
                }[platform]
                social_kwargs[platform] = platform_class(**social_data[platform])
        if "schedule_cron" in social_data:
            social_kwargs["schedule_cron"] = social_data["schedule_cron"]
        if "weekend_schedule_cron" in social_data:
            social_kwargs["weekend_schedule_cron"] = social_data["weekend_schedule_cron"]
        kwargs["social"] = SocialSettings(**social_kwargs)
    if "logging" in data:
        kwargs["logging"] = LoggingSettings(**data["logging"])
    if "monitoring" in data:
        kwargs["monitoring"] = MonitoringSettings(**data["monitoring"])

    # Create settings with YAML data and update cache
    _cached_settings = Settings(**kwargs)
    return _cached_settings