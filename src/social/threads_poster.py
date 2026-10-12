"""Threads (Instagram Graph API) poster."""

import logging
from typing import Optional

import aiohttp
from src.common.config import get_settings
from src.common.formatter import TradeSignal

logger = logging.getLogger(__name__)


class ThreadsPoster:
    """Posts to Threads using Instagram Graph API."""

    BASE_URL = "https://graph.threads.net/v1.0"

    def __init__(self):
        self._settings = get_settings()
        self._access_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Threads client."""
        if self._initialized:
            return True

        threads = self._settings.social.threads
        if not threads.enabled:
            logger.info("Threads posting disabled")
            return False

        if not all([threads.app_id, threads.app_secret, threads.user_access_token]):
            logger.warning("Threads credentials incomplete")
            return False

        self._access_token = threads.user_access_token

        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(timeout=timeout)

        # Get user ID
        if await self._get_user_id():
            self._initialized = True
            logger.info(f"Threads client initialized for user {self._user_id}")
            return True

        return False

    async def _get_user_id(self) -> bool:
        """Get Threads user ID from access token."""
        if not self._session:
            return False
        try:
            async with self._session.get(
                f"{self.BASE_URL}/me",
                params={"fields": "id,username", "access_token": self._access_token}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self._user_id = data.get("id")
                    return True
        except Exception as e:
            logger.error(f"Failed to get Threads user ID: {e}")
        return False

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def post(self, text: str, signal: TradeSignal) -> bool:
        """Post a thread."""
        if not self._initialized:
            await self.initialize()

        if not self._session or not self._user_id:
            return False

        try:
            # Step 1: Create media container
            container_id = await self._create_container(text)
            if not container_id:
                return False

            # Step 2: Publish container
            return await self._publish_container(container_id)

        except Exception as e:
            logger.error(f"Threads post error: {e}")
            return False

    async def _create_container(self, text: str) -> Optional[str]:
        """Create media container for Threads post."""
        try:
            payload = {
                "text": text,
                "access_token": self._access_token,
            }

            async with self._session.post(
                f"{self.BASE_URL}/{self._user_id}/threads",
                data=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("id")
                else:
                    error_text = await resp.text()
                    logger.error(f"Container creation failed: {resp.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Create container error: {e}")
            return None

    async def _publish_container(self, container_id: str) -> bool:
        """Publish the media container."""
        try:
            payload = {
                "creation_id": container_id,
                "access_token": self._access_token,
            }

            async with self._session.post(
                f"{self.BASE_URL}/{self._user_id}/threads_publish",
                data=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Threads post published: {data.get('id')}")
                    return True
                else:
                    error_text = await resp.text()
                    logger.error(f"Publish failed: {resp.status} - {error_text}")
                    return False
        except Exception as e:
            logger.error(f"Publish container error: {e}")
            return False

    async def post_carousel(self, texts: list[str], images: list[str], signal: TradeSignal) -> bool:
        """Post a carousel (multiple images with text)."""
        # Threads carousel requires multiple containers
        # This is a simplified implementation
        return await self.post(texts[0], signal)


# Global instance
_threads_poster: Optional[ThreadsPoster] = None


async def get_threads_poster() -> ThreadsPoster:
    """Get or create the global Threads poster."""
    global _threads_poster
    if _threads_poster is None:
        _threads_poster = ThreadsPoster()
    return _threads_poster


async def post_to_threads(text: str, signal: TradeSignal) -> bool:
    """Convenience function to post to Threads."""
    poster = await get_threads_poster()
    return await poster.post(text, signal)