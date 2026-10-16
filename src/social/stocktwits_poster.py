"""Stocktwits API poster."""

import logging
from typing import Optional

import aiohttp
from src.common.config import get_settings
from src.common.formatter import TradeSignal

logger = logging.getLogger(__name__)


class StocktwitsPoster:
    """Posts to Stocktwits using their API."""

    BASE_URL = "https://api.stocktwits.com/api/v2"

    def __init__(self):
        self._settings = get_settings()
        self._access_token: Optional[str] = None
        self._relay_url: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Stocktwits client."""
        if self._initialized:
            return True

        st = self._settings.social.stocktwits
        if not st.enabled:
            logger.info("Stocktwits posting disabled")
            return False

        timeout = aiohttp.ClientTimeout(total=30)

        # Relay mode: hand the post to an authorized integration instead of
        # calling the Enterprise-only API directly. No Stocktwits credential
        # lives here; the integration holds the OAuth connection.
        if st.relay_webhook_url:
            self._relay_url = st.relay_webhook_url
            self._session = aiohttp.ClientSession(
                timeout=timeout, headers={"Content-Type": "application/json"}
            )
            self._initialized = True
            logger.info("Stocktwits poster initialized in relay mode")
            return True

        if not st.access_token:
            logger.warning(
                "Stocktwits needs either relay_webhook_url or access_token"
            )
            return False

        self._access_token = st.access_token

        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
        )

        # Verify credentials
        if await self._verify_credentials():
            self._initialized = True
            logger.info("Stocktwits client initialized")
            return True

        return False

    async def _verify_credentials(self) -> bool:
        """Verify access token is valid."""
        if not self._session:
            return False
        try:
            async with self._session.get(f"{self.BASE_URL}/streams/user.json") as resp:
                return resp.status == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def post(self, text: str, signal: TradeSignal) -> bool:
        """Post a message to Stocktwits."""
        if not self._initialized:
            await self.initialize()

        if not self._session:
            return False

        try:
            if self._relay_url:
                # The integration's "Create Post" action takes the body; ticker
                # is passed alongside so the Zap can build a cashtag if wanted.
                async with self._session.post(
                    self._relay_url,
                    json={"body": text, "ticker": signal.ticker or ""},
                ) as resp:
                    if 200 <= resp.status < 300:
                        logger.info("Stocktwits post relayed")
                        return True
                    logger.error(
                        f"Stocktwits relay failed: {resp.status} - "
                        f"{(await resp.text())[:200]}"
                    )
                    return False

            # Stocktwits expects symbols with $ prefix for cashtags
            payload = {
                "body": text,
            }

            # Add symbols if we have a ticker
            if signal.ticker:
                payload["symbols"] = [{"symbol": signal.ticker}]

            async with self._session.post(
                f"{self.BASE_URL}/messages/create.json",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    msg_id = data.get("message", {}).get("id")
                    logger.info(f"Stocktwits post created: {msg_id}")
                    return True
                elif resp.status == 429:
                    logger.warning("Stocktwits rate limited")
                    return False
                else:
                    error_text = await resp.text()
                    logger.error(f"Stocktwits post failed: {resp.status} - {error_text}")
                    return False

        except Exception as e:
            logger.error(f"Stocktwits post error: {e}")
            return False


# Global instance
_stocktwits_poster: Optional[StocktwitsPoster] = None


async def get_stocktwits_poster() -> StocktwitsPoster:
    """Get or create the global Stocktwits poster."""
    global _stocktwits_poster
    if _stocktwits_poster is None:
        _stocktwits_poster = StocktwitsPoster()
    return _stocktwits_poster


async def post_to_stocktwits(text: str, signal: TradeSignal) -> bool:
    """Convenience function to post to Stocktwits."""
    poster = await get_stocktwits_poster()
    return await poster.post(text, signal)