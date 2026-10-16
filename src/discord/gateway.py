"""Discord Gateway WebSocket Listener.

Connects to Discord's gateway using a user token (not a bot token) to listen
for messages in target channels. This is a self-bot approach which violates
Discord ToS - use at your own risk.
"""

import asyncio
import json
import logging
import random
import time
from dataclasses import dataclass
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.common.config import get_settings
from src.common.deduplicator import get_deduplicator
from src.common.formatter import SignalFormatter, TradeSignal
from src.common.webhook import get_webhook_sender

logger = logging.getLogger(__name__)


@dataclass
class DiscordMessage:
    """Parsed Discord message."""
    id: str
    channel_id: str
    author_id: str
    author_username: str
    author_bot: bool
    content: str
    timestamp: str
    guild_id: Optional[str] = None


class DiscordGateway:
    """Discord Gateway WebSocket client for user accounts."""

    GATEWAY_URL = "wss://gateway.discord.gg/?v=9&encoding=json"
    HEARTBEAT_INTERVAL = 41250  # Default, will be updated from hello
    MAX_RECONNECT_ATTEMPTS = 10
    BASE_RECONNECT_DELAY = 5

    def __init__(self):
        self._settings = get_settings()
        self._token = self._settings.discord.user_token
        self._target_channels = set(self._settings.discord.target_channel_ids)
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._sequence: Optional[int] = None
        self._session_id: Optional[str] = None
        self._running = False
        self._reconnect_attempts = 0
        self._message_handler: Optional[Callable] = None
        self._token_refresh_callback: Optional[Callable] = None
        self._auth_failure_callback: Optional[Callable] = None

    def set_message_handler(self, handler: Callable[[DiscordMessage], None]) -> None:
        """Set custom message handler."""
        self._message_handler = handler

    def set_token_refresh_callback(self, callback: Callable[[], str]) -> None:
        """Set callback to fetch new token when current one expires."""
        self._token_refresh_callback = callback

    def set_auth_failure_callback(self, callback: Callable[[], None]) -> None:
        """Set callback when auth fails."""
        self._auth_failure_callback = callback

    async def refresh_token(self) -> bool:
        """Refresh token using callback and reconnect."""
        if self._token_refresh_callback:
            try:
                new_token = self._token_refresh_callback()
                if new_token:
                    self._token = new_token
                    # Update settings
                    self._settings.discord.user_token = new_token
                    logger.info("Token refreshed via callback")
                    # Force reconnect with new token
                    self._session_id = None
                    self._sequence = None
                    return True
            except Exception as e:
                logger.error(f"Token refresh callback failed: {e}")
        return False

    async def connect(self) -> None:
        """Connect to Discord gateway with automatic reconnection."""
        self._running = True
        self._reconnect_attempts = 0

        while self._running:
            try:
                await self._run_connection()
            except Exception as e:
                logger.error(f"Gateway connection error: {e}")
                if not await self._handle_reconnect():
                    break

    async def _run_connection(self) -> None:
        """Run a single gateway connection."""
        logger.info("Connecting to Discord gateway...")

        async with websockets.connect(
            self.GATEWAY_URL,
            max_size=2**25,  # 32MB max message size
            ping_interval=None,  # We handle heartbeats manually
            ping_timeout=None,
        ) as ws:
            self._ws = ws
            self._reconnect_attempts = 0
            logger.info("Connected to Discord gateway")

            # Handle incoming messages
            async for message in ws:
                if not self._running:
                    break
                try:
                    await self._handle_message(json.loads(message))
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from gateway")
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

    async def _handle_message(self, data: dict) -> None:
        """Handle incoming gateway message."""
        op = data.get("op")
        event_type = data.get("t")
        self._sequence = data.get("s", self._sequence)

        if op == 10:  # HELLO
            await self._handle_hello(data)
        elif op == 11:  # HEARTBEAT_ACK
            logger.debug("Heartbeat acknowledged")
        elif op == 0:  # DISPATCH
            await self._handle_dispatch(event_type, data)
        elif op == 7:  # RECONNECT
            logger.info("Received RECONNECT opcode, reconnecting...")
            raise WebSocketException("Reconnect requested by server")
        elif op == 9:  # INVALID_SESSION
            logger.warning("Invalid session, will resume" if data.get("d") else "Invalid session, cannot resume")
            if not data.get("d"):
                # Cannot resume - token likely expired
                logger.error("Token expired or invalid (4004) - attempting refresh...")
                if self._auth_failure_callback:
                    self._auth_failure_callback()
                if await self.refresh_token():
                    logger.info("Token refreshed, will reconnect with new token")
                    return  # Will reconnect in the outer loop
                else:
                    logger.error("Token refresh failed - manual intervention required")
            self._session_id = None if not data.get("d") else self._session_id
            raise WebSocketException("Invalid session")
        else:
            logger.debug(f"Unknown opcode: {op}")

    async def _handle_hello(self, data: dict) -> None:
        """Handle HELLO opcode - start heartbeat and authenticate."""
        heartbeat_interval = data["d"]["heartbeat_interval"]
        self.HEARTBEAT_INTERVAL = heartbeat_interval
        logger.debug(f"Heartbeat interval: {heartbeat_interval}ms")

        # Start heartbeat
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        # Authenticate
        await self._authenticate()

    async def _authenticate(self) -> None:
        """Send IDENTIFY or RESUME payload."""
        if self._session_id and self._sequence:
            # Resume existing session
            payload = {
                "op": 6,
                "d": {
                    "token": self._token,
                    "session_id": self._session_id,
                    "seq": self._sequence,
                },
            }
            logger.info("Resuming session...")
        else:
            # New session
            payload = {
                "op": 2,
                "d": {
                    "token": self._token,
                    "properties": {
                        "$os": "linux",
                        "$browser": "chrome",
                        "$device": "pc",
                    },
                    "compress": False,
                    "large_threshold": 250,
                },
            }
            logger.info("Identifying new session...")

        await self._ws.send(json.dumps(payload))

    async def _handle_dispatch(self, event_type: str, data: dict) -> None:
        """Handle DISPATCH events."""
        if event_type == "READY":
            self._session_id = data["d"]["session_id"]
            self._sequence = data["s"]
            logger.info(f"Ready! Session: {self._session_id[:8]}...")

        elif event_type == "MESSAGE_CREATE":
            await self._handle_message_create(data["d"])

        elif event_type == "RESUMED":
            logger.info("Session resumed successfully")

    async def _handle_message_create(self, msg_data: dict) -> None:
        """Process incoming message."""
        # Filter: only target channels, not from bots, has content
        channel_id = str(msg_data.get("channel_id", ""))
        if channel_id not in self._target_channels:
            return

        author = msg_data.get("author", {})
        if author.get("bot", False):
            return

        content = msg_data.get("content", "").strip()
        if not content:
            return

        # Parse message
        message = DiscordMessage(
            id=str(msg_data.get("id", "")),
            channel_id=channel_id,
            author_id=str(author.get("id", "")),
            author_username=author.get("username", "Unknown"),
            author_bot=author.get("bot", False),
            content=content,
            timestamp=msg_data.get("timestamp", ""),
            guild_id=str(msg_data.get("guild_id", "")) if msg_data.get("guild_id") else None,
        )

        # Deduplication
        deduplicator = get_deduplicator()
        dedup_key = f"{channel_id}:{message.id}:{content}"
        is_dup = await deduplicator.is_duplicate(dedup_key, f"discord:{channel_id}")
        if is_dup:
            return

        # Forward immediately to Discord webhook (ALL messages, no format filtering)
        webhook = await get_webhook_sender()
        await webhook.send_signal(
            signal_text=content,
            source="Trading Signal",
            author="Trading Desk",
            channel=channel_id,
        )

        logger.info(f"Posted signal: {content[:50]}...")

        # Queue for social media (delayed) - create signal from raw content
        signal = TradeSignal(
            raw_text=content,
            source="Trading Signal",
            author="Trading Desk",
            channel=channel_id,
        )
        await self._queue_for_social(signal)

        # Call custom handler if set
        if self._message_handler:
            try:
                self._message_handler(message)
            except Exception as e:
                logger.error(f"Custom message handler error: {e}")

    async def _queue_for_social(self, signal: TradeSignal) -> None:
        """Queue signal for delayed social media posting."""
        # Import here to avoid circular imports
        from src.social.queue import get_social_queue

        queue = await get_social_queue()
        await queue.enqueue(
            signal=signal.__dict__,
            source="discord",
            timestamp=time.time(),
        )

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to keep connection alive."""
        try:
            while self._running and self._ws:
                await asyncio.sleep(self.HEARTBEAT_INTERVAL / 1000)
                if not self._running or not self._ws:
                    break
                try:
                    await self._ws.send(json.dumps({"op": 1, "d": self._sequence}))
                    logger.debug("Heartbeat sent")
                except Exception as e:
                    logger.error(f"Heartbeat failed: {e}")
                    break
        except asyncio.CancelledError:
            pass

    async def _handle_reconnect(self) -> bool:
        """Handle reconnection with exponential backoff."""
        if not self._running:
            return False

        self._reconnect_attempts += 1
        if self._reconnect_attempts > self.MAX_RECONNECT_ATTEMPTS:
            logger.error("Max reconnection attempts reached")
            return False

        delay = self.BASE_RECONNECT_DELAY * (2 ** (self._reconnect_attempts - 1))
        delay += random.uniform(0, 1)  # Jitter
        delay = min(delay, 300)  # Cap at 5 minutes

        logger.info(f"Reconnecting in {delay:.1f}s (attempt {self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS})")
        await asyncio.sleep(delay)
        return True

    async def close(self) -> None:
        """Gracefully close the connection."""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        if self._ws:
            await self._ws.close()
        logger.info("Gateway connection closed")


# Convenience function for simple usage
async def start_gateway(message_handler: Optional[Callable] = None) -> None:
    """Start the Discord gateway listener."""
    gateway = DiscordGateway()
    if message_handler:
        gateway.set_message_handler(message_handler)
    await gateway.connect()