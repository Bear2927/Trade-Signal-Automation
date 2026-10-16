"""X/Twitter API v2 poster."""

import logging
from typing import Optional

import tweepy
from src.common.config import get_settings
from src.common.formatter import TradeSignal

logger = logging.getLogger(__name__)


class TwitterPoster:
    """Posts to X/Twitter using API v2 with OAuth 2.0."""

    def __init__(self):
        self._settings = get_settings()
        self._client: Optional[tweepy.Client] = None
        self._initialized = False

    async def initialize(self) -> bool:
        """Initialize Twitter client."""
        if self._initialized:
            return True

        twitter = self._settings.social.twitter
        if not twitter.enabled:
            logger.info("Twitter posting disabled")
            return False

        if not all([twitter.api_key, twitter.api_secret, twitter.access_token,
                    twitter.access_token_secret]):
            logger.warning("Twitter credentials incomplete")
            return False

        try:
            self._client = tweepy.Client(
                consumer_key=twitter.api_key,
                consumer_secret=twitter.api_secret,
                access_token=twitter.access_token,
                access_token_secret=twitter.access_token_secret,
                bearer_token=twitter.bearer_token,
                wait_on_rate_limit=True,
            )

            # Verify credentials
            me = self._client.get_me()
            if me.data:
                logger.info(f"Twitter client initialized for @{me.data.username}")
                self._initialized = True
                return True
            else:
                logger.error("Failed to verify Twitter credentials")
                return False

        except Exception as e:
            logger.error(f"Twitter initialization failed: {e}")
            return False

    async def post(self, text: str, signal: TradeSignal) -> bool:
        """Post a tweet."""
        if not self._initialized:
            await self.initialize()

        if not self._client:
            return False

        try:
            # Truncate to max chars
            max_chars = self._settings.social.twitter.max_chars
            if len(text) > max_chars:
                text = text[:max_chars - 3] + "..."

            response = self._client.create_tweet(text=text)

            if response.data:
                tweet_id = response.data["id"]
                logger.info(f"Tweet posted: https://twitter.com/user/status/{tweet_id}")
                return True
            else:
                logger.error(f"Tweet failed: {response.errors}")
                return False

        except tweepy.TooManyRequests as e:
            logger.error(f"Twitter rate limited: {e}")
            return False
        except Exception as e:
            logger.error(f"Twitter post error: {e}")
            return False

    async def post_thread(self, texts: list[str], signal: TradeSignal) -> bool:
        """Post a tweet thread."""
        if not self._initialized:
            await self.initialize()

        if not self._client:
            return False

        try:
            previous_id = None
            for i, text in enumerate(texts):
                max_chars = self._settings.social.twitter.max_chars
                if len(text) > max_chars:
                    text = text[:max_chars - 3] + "..."

                if previous_id:
                    response = self._client.create_tweet(text=text, in_reply_to_tweet_id=previous_id)
                else:
                    response = self._client.create_tweet(text=text)

                if response.data:
                    previous_id = response.data["id"]
                else:
                    logger.error(f"Thread tweet {i+1} failed: {response.errors}")
                    return False

            logger.info(f"Thread posted ({len(texts)} tweets)")
            return True

        except Exception as e:
            logger.error(f"Thread post error: {e}")
            return False


# Global instance
_twitter_poster: Optional[TwitterPoster] = None


async def get_twitter_poster() -> TwitterPoster:
    """Get or create the global Twitter poster."""
    global _twitter_poster
    if _twitter_poster is None:
        _twitter_poster = TwitterPoster()
    return _twitter_poster


async def post_to_twitter(text: str, signal: TradeSignal) -> bool:
    """Convenience function to post to Twitter."""
    poster = await get_twitter_poster()
    return await poster.post(text, signal)