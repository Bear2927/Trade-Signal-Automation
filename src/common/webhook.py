"""Discord webhook sender with rate limiting and retry logic."""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

import aiohttp
from pydantic import BaseModel

from src.common.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class WebhookPayload:
    """Discord webhook payload."""
    content: Optional[str] = None
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    embeds: Optional[list] = None
    allowed_mentions: Optional[dict] = None


class DiscordEmbed(BaseModel):
    """Discord embed model."""
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    color: Optional[int] = None
    fields: Optional[list] = None
    footer: Optional[dict] = None
    timestamp: Optional[str] = None
    thumbnail: Optional[dict] = None
    image: Optional[dict] = None
    author: Optional[dict] = None


class WebhookSender:
    """Sends messages to Discord webhook with rate limiting and retries."""

    def __init__(self):
        self._settings = get_settings()
        self._webhook_url = self._settings.webhook.url
        self._rate_limit = self._settings.webhook.rate_limit_per_second
        self._max_retries = self._settings.webhook.max_retries
        self._retry_delay = self._settings.webhook.retry_delay_seconds
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._last_request_time = 0.0

    async def initialize(self) -> None:
        """Initialize HTTP session and rate limiter."""
        if self._session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self._session = aiohttp.ClientSession(timeout=timeout)
            self._semaphore = asyncio.Semaphore(self._rate_limit)
            logger.info("Webhook sender initialized")

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
            logger.info("Webhook sender closed")

    async def _rate_limit_wait(self) -> None:
        """Enforce rate limiting."""
        if self._rate_limit <= 0:
            return
        min_interval = 1.0 / self._rate_limit
        elapsed = asyncio.get_event_loop().time() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)

    async def send(
        self,
        content: Optional[str] = None,
        embeds: Optional[list[DiscordEmbed]] = None,
        username: str = "StockTradingSignals",
        avatar_url: Optional[str] = None,
    ) -> bool:
        """
        Send a message to the Discord webhook.

        Returns True on success, False on failure after retries.
        """
        if not self._webhook_url:
            logger.warning("Webhook URL not configured, skipping send")
            return False

        if self._session is None:
            await self.initialize()

        payload = WebhookPayload(
            content=content,
            username=username,
            avatar_url=avatar_url,
            embeds=[e.model_dump(exclude_none=True) for e in embeds] if embeds else None,
        )

        # Rate limiting
        await self._rate_limit_wait()

        # Retry logic
        for attempt in range(self._max_retries + 1):
            try:
                async with self._semaphore:
                    self._last_request_time = asyncio.get_event_loop().time()
                    async with self._session.post(
                        self._webhook_url,
                        json=payload.__dict__,
                        headers={"Content-Type": "application/json"},
                    ) as response:
                        if response.status == 204:
                            logger.debug("Webhook sent successfully")
                            return True
                        elif response.status == 429:
                            # Rate limited by Discord
                            retry_after = response.headers.get("Retry-After")
                            wait_time = float(retry_after) if retry_after else self._retry_delay * (2 ** attempt)
                            logger.warning(f"Webhook rate limited, waiting {wait_time}s")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            error_text = await response.text()
                            logger.error(f"Webhook failed: {response.status} - {error_text}")

            except asyncio.TimeoutError:
                logger.error(f"Webhook timeout (attempt {attempt + 1}/{self._max_retries + 1})")
            except Exception as e:
                logger.error(f"Webhook error (attempt {attempt + 1}/{self._max_retries + 1}): {e}")

            if attempt < self._max_retries:
                wait_time = self._retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)

        logger.error("Webhook send failed after all retries")
        return False

    async def send_signal(
        self,
        signal_text: str,
        source: str,
        author: str = "Unknown",
        channel: str = "",
        color: int = 0x00FF00,
    ) -> bool:
        """Send a formatted trading signal to Discord."""
        embed = DiscordEmbed(
            title=f"📈 Trade Signal from {source}",
            description=signal_text[:4096],  # Discord embed description limit
            color=color,
            fields=[
                {"name": "Source", "value": source, "inline": True},
                {"name": "Author", "value": author, "inline": True},
            ] + ([{"name": "Channel", "value": channel, "inline": True}] if channel else []),
            footer={"text": "StockTradingSignals • Automated"},
            timestamp=None,  # Could add current time
        )
        return await self.send(embeds=[embed])


# Global instance
_webhook_sender: Optional[WebhookSender] = None


async def get_webhook_sender() -> WebhookSender:
    """Get or create the global webhook sender."""
    global _webhook_sender
    if _webhook_sender is None:
        _webhook_sender = WebhookSender()
        await _webhook_sender.initialize()
    return _webhook_sender


async def close_webhook_sender() -> None:
    """Close the global webhook sender."""
    global _webhook_sender
    if _webhook_sender:
        await _webhook_sender.close()
        _webhook_sender = None