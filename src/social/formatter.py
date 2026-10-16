"""Platform-specific formatting for social media posts."""

from datetime import datetime
from src.common.formatter import TradeSignal


def _signal_time(signal: TradeSignal) -> datetime:
    """When the alert was posted upstream, falling back to now."""
    if signal.timestamp:
        return datetime.fromtimestamp(signal.timestamp)
    return datetime.now()
from src.social.trade_summarizer import TradeSummarizer
from src.social.social_poster_formatter import SocialMediaFormatter


def format_for_twitter(signal: TradeSignal) -> str:
    """Format signal for X/Twitter (280 chars)."""
    # Use Discord timestamp formatter for Messenger trades
    if signal.source == "Trading Signal" and "s/l" in signal.raw_text:
        return SocialMediaFormatter.format_messenger_trade_for_social(
            signal.raw_text, _signal_time(signal), 'twitter'
        )
    # Use trade summarizer for other sources
    return TradeSummarizer.format_for_social_media(signal.raw_text, 'twitter')


def format_for_stocktwits(signal: TradeSignal) -> str:
    """Format signal for Stocktwits, within the platform's posting limit."""
    from src.common.webhook import classify_message
    from src.social.social_poster_formatter import STOCKTWITS_POST_LIMIT

    # Any recognisable trade goes through the length-aware formatter. Keying
    # off "s/l" alone missed alerts written without a stop, e.g.
    # "MS OCT23 200C earnings".
    if classify_message(signal.raw_text) == "entry":
        return SocialMediaFormatter.format_messenger_trade_for_social(
            signal.raw_text, _signal_time(signal), 'stocktwits'
        )
    # Other sources still need capping; the platform truncates silently.
    return TradeSummarizer.format_for_social_media(
        signal.raw_text, 'stocktwits')[:STOCKTWITS_POST_LIMIT]


def format_for_threads(signal: TradeSignal) -> str:
    """Format signal for Threads/Instagram with Discord timestamp."""
    # Use Discord timestamp formatter for Messenger trades
    if signal.source == "Trading Signal" and "s/l" in signal.raw_text:
        return SocialMediaFormatter.format_messenger_trade_for_social(
            signal.raw_text, _signal_time(signal), 'threads'
        )
    # Use trade summarizer for other sources
    return TradeSummarizer.format_for_social_media(signal.raw_text, 'threads')


def format_for_reddit(signal: TradeSignal) -> tuple[str, str]:
    """Format signal for Reddit (title, body)."""
    from src.common.formatter import SignalFormatter
    return SignalFormatter.format_reddit(signal)


def format_for_telegram(signal: TradeSignal) -> str:
    """Format signal for Telegram (Markdown)."""
    return format_for_platform(signal, 'telegram')


def format_for_linkedin(signal: TradeSignal) -> str:
    """Format signal for LinkedIn."""
    return format_for_platform(signal, 'linkedin')


def format_for_email(signal: TradeSignal) -> tuple[str, str]:
    """Format signal for Email (subject, html_body)."""
    from src.common.formatter import SignalFormatter
    return SignalFormatter.format_email(signal)


# Platform-specific optimizations
PLATFORM_CONFIG = {
    "twitter": {
        "max_chars": 280,
        "hashtags": ["#trading", "#stocks", "#signals"],
        "supports_thread": True,
        "supports_media": True,
    },
    "stocktwits": {
        "max_chars": 2000,
        "hashtags": [],  # Uses cashtags instead
        "supports_thread": False,
        "supports_media": False,
    },
    "threads": {
        "max_chars": 500,
        "hashtags": ["#trading", "#stockmarket", "#investing"],
        "supports_thread": True,
        "supports_media": True,
        "supports_carousel": True,
    },
    "reddit": {
        "max_chars": 40000,
        "hashtags": [],
        "supports_thread": False,
        "supports_media": True,
    },
    "telegram": {
        "max_chars": 4096,
        "hashtags": [],
        "supports_thread": False,
        "supports_media": True,
        "markdown": True,
    },
    "linkedin": {
        "max_chars": 3000,
        "hashtags": ["#trading", "#stockmarket", "#finance"],
        "supports_thread": False,
        "supports_media": True,
        "supports_article": True,
    },
    "email": {
        "max_chars": None,
        "hashtags": [],
        "html": True,
    },
}


def get_platform_config(platform: str) -> dict:
    """Get platform configuration."""
    return PLATFORM_CONFIG.get(platform.lower(), {})


def optimize_for_platform(text: str, platform: str) -> str:
    """Apply platform-specific optimizations."""
    config = get_platform_config(platform)

    # Add hashtags if platform uses them
    if config.get("hashtags") and platform.lower() not in ["stocktwits"]:
        hashtags = " " + " ".join(config["hashtags"])
        if len(text) + len(hashtags) <= config.get("max_chars", 1000):
            text += hashtags

    # Truncate if needed
    max_chars = config.get("max_chars")
    if max_chars and len(text) > max_chars:
        text = text[:max_chars - 3] + "..."

    return text