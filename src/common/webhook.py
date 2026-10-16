"""Discord webhook sender with rate limiting and retry logic."""

import asyncio
import logging
import re
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


# Cross-server mention tokens (role/user/channel IDs, @everyone/@here) are dead
# references in the destination channel and can fire stray pings, so they are
# stripped from any forwarded text.
_MENTION_RE = re.compile(r"<@[!&]?\d+>|<#\d+>|@everyone|@here")


def strip_mentions(text: str) -> str:
    return re.sub(r"[ \t]{2,}", " ", _MENTION_RE.sub("", text)).strip()


# Message routing. Entries and exits are actionable and go to the trade-signals
# channel; watches, partial scale-outs and banter go to the chat channel.
#
# Two contract shapes exist in the wild:
#   full  - "MDB OCT16 425C 1.25"      (Messenger, carries an expiry)
#   short - "$SPY 778C @.30"           (Discord, no expiry)
# The short form requires an UPPERCASE ticker, otherwise prose like
# "Watching 772P's" would read as a contract.
_CONTRACT_FULL = re.compile(
    r"\b[A-Z]{1,5}\s+(?:[A-Z]{3}\s?\d{1,2}|\d{1,2}/\d{1,2}|\d+\s?DTE)\s+\d+(?:\.\d+)?\s*[CP]\b",
    re.IGNORECASE,
)
# The short form must carry a price. Without that, flow commentary such as
# "MS 200C OTM pop and flat" reads as an entry. The full form needs no price
# because its expiry (OCT23, 1DTE, 10/15) is already the signal -- and real
# alerts like "MS OCT23 200C earnings" legitimately omit one.
_CONTRACT_SHORT = re.compile(
    r"\$?\b[A-Z]{1,5}\s+\d+(?:\.\d+)?\s*[CP]\b\s*(?:@\s*)?\.?\d+(?:\.\d+)?\b"
)

# A partial scale-out is an update, not an exit, even though it says "took".
_PARTIAL = re.compile(
    r"\b(?:scale[sd]?|scaling|trim(?:med|ming)?|partial|took\s+(?:some|more))\b",
    re.IGNORECASE,
)
_EXIT = re.compile(
    r"\b(?:stopp?(?:ing|ed)\s+out"
    r"|took\s+the\s+loss"
    r"|full(?:y)?\s+(?:out|closed|exited)"
    r"|all\s+out"
    r"|closed\s+(?:out|it|the)"
    r"|cut\s+(?:it|the))\b",
    re.IGNORECASE,
)


# First ticker in a contract, used to headline the embed.
_TICKER = re.compile(
    r"\$?\b([A-Z]{1,5})\s+(?:[A-Z]{3}\s?\d{1,2}|\d{1,2}/\d{1,2}|\d+\s?DTE|\d+(?:\.\d+)?\s*[CP])"
)


def extract_ticker(text: str) -> Optional[str]:
    m = _TICKER.search(text)
    return m.group(1).upper() if m else None


def classify_message(text: str) -> str:
    """Return 'entry', 'exit', or 'other'."""
    if _CONTRACT_FULL.search(text) or _CONTRACT_SHORT.search(text):
        return "entry"
    if _EXIT.search(text) and not _PARTIAL.search(text):
        return "exit"
    return "other"


class WebhookSender:
    """Sends messages to Discord webhook with rate limiting and retries."""

    def __init__(self):
        self._settings = get_settings()
        self._webhook_url = self._settings.webhook.url
        self._chat_url = self._settings.webhook.chat_url or self._settings.webhook.url
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
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        url: Optional[str] = None,
    ) -> bool:
        """
        Send a message to the Discord webhook.

        Returns True on success, False on failure after retries.
        """
        target = url or self._webhook_url
        if not target:
            logger.warning("Webhook URL not configured, skipping send")
            return False

        if self._session is None:
            await self.initialize()

        payload = WebhookPayload(
            content=content,
            username=username,
            avatar_url=avatar_url,
            embeds=[e.model_dump(exclude_none=True) for e in embeds] if embeds else None,
            allowed_mentions={"parse": []},
        )

        # Rate limiting
        await self._rate_limit_wait()

        # Retry logic
        for attempt in range(self._max_retries + 1):
            try:
                async with self._semaphore:
                    self._last_request_time = asyncio.get_event_loop().time()
                    async with self._session.post(
                        target,
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
        """Route a message to the trade-signals or chat channel by its kind."""
        clean = strip_mentions(signal_text)
        kind = classify_message(clean)

        colors = {"entry": color, "exit": 0xFF5555, "other": 0x95A5A6}
        ticker = extract_ticker(clean) if kind == "entry" else None
        if ticker:
            # Heading markdown renders in descriptions, not titles, so the
            # ticker leads the description with no label in front of it.
            # Drop a leading repeat of the ticker from the body so it does not
            # read "$SPY" twice; a mid-text ticker is left alone.
            body = re.sub(rf"^\$?{re.escape(ticker)}\s+", "", clean, count=1, flags=re.IGNORECASE)
            embed = DiscordEmbed(
                description=f"# ${ticker}\n{body}"[:4096],
                color=colors[kind],
            )
        else:
            titles = {"entry": None, "exit": "Trade Exit", "other": "Chat"}
            embed = DiscordEmbed(
                title=titles[kind],
                description=clean[:4096],
                color=colors[kind],
            )
        target = self._chat_url if kind == "other" else self._webhook_url
        logger.info("Routing %s -> %s: %s", kind,
                    "chat" if kind == "other" else "trade-signals", clean[:60])
        return await self.send(embeds=[embed], url=target)


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