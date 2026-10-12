"""Web automation-based social media posters using Playwright."""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from pathlib import Path
import json

from playwright.async_api import async_playwright, Page, Browser

logger = logging.getLogger(__name__)


class WebTwitterPoster:
    """Post to X (Twitter) using web automation."""

    def __init__(self, email: str, password: str, session_dir: str = "./sessions"):
        self.email = email
        self.password = password
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.browser: Optional[Browser] = None
        self.session_file = self.session_dir / "twitter_session.json"

    async def _get_authenticated_page(self) -> Page:
        """Get an authenticated page, using saved session if available."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()

        # Load saved session if exists
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    storage = json.load(f)
                await context.add_cookies(storage.get('cookies', []))
                for key, value in storage.get('local_storage', {}).items():
                    await context.add_init_script(f"window.localStorage.setItem('{key}', '{value}');")
            except Exception as e:
                logger.warning(f"Failed to load saved session: {e}")

        page = await context.new_page()

        # If no valid session, authenticate
        if not await self._is_authenticated(page):
            await self._authenticate(page)
            # Save session
            cookies = await context.cookies()
            storage = await page.evaluate("() => window.localStorage")
            with open(self.session_file, 'w') as f:
                json.dump({'cookies': cookies, 'local_storage': storage}, f)

        return page

    async def _is_authenticated(self, page: Page) -> bool:
        """Check if page is authenticated."""
        try:
            await page.goto("https://x.com/home", timeout=5000)
            return await page.query_selector("[data-testid='Tweet-text']") is not None
        except:
            return False

    async def _authenticate(self, page: Page):
        """Authenticate with X using email/password."""
        await page.goto("https://x.com/login")

        # Enter email
        await page.fill("input[type='text']", self.email)
        await page.click("button:has-text('Next')")
        await page.wait_for_timeout(1000)

        # Enter password
        await page.fill("input[type='password']", self.password)
        await page.click("button:has-text('Log in')")

        # Wait for home page
        await page.wait_for_url("**/home", timeout=10000)

    async def post(self, message: str) -> bool:
        """Post a message to X."""
        try:
            page = await self._get_authenticated_page()

            # Click compose tweet button
            await page.click("[data-testid='SideNav_NewTweet_Button']")
            await page.wait_for_timeout(500)

            # Type message
            await page.click("[data-testid='tweetTextarea_0']")
            await page.type("[data-testid='tweetTextarea_0']", message)
            await page.wait_for_timeout(500)

            # Click post button
            await page.click("[data-testid='tweetButton']")

            # Wait for success
            await page.wait_for_timeout(2000)

            logger.info(f"Posted to X: {message[:50]}...")
            await page.context.browser.close()
            return True

        except Exception as e:
            logger.error(f"Failed to post to X: {e}")
            return False


class WebStocktwitsPoster:
    """Post to Stocktwits using web automation."""

    def __init__(self, email: str, password: str, session_dir: str = "./sessions"):
        self.email = email
        self.password = password
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "stocktwits_session.json"

    async def _get_authenticated_page(self) -> Page:
        """Get an authenticated page, using saved session if available."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()

        # Load saved session if exists
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    storage = json.load(f)
                await context.add_cookies(storage.get('cookies', []))
            except Exception as e:
                logger.warning(f"Failed to load saved session: {e}")

        page = await context.new_page()

        # If no valid session, authenticate
        if not await self._is_authenticated(page):
            await self._authenticate(page)
            # Save session
            cookies = await context.cookies()
            with open(self.session_file, 'w') as f:
                json.dump({'cookies': cookies}, f)

        return page

    async def _is_authenticated(self, page: Page) -> bool:
        """Check if page is authenticated."""
        try:
            await page.goto("https://stocktwits.com", timeout=5000)
            return "login" not in page.url.lower()
        except:
            return False

    async def _authenticate(self, page: Page):
        """Authenticate with Stocktwits."""
        await page.goto("https://stocktwits.com/account/login")

        # Enter email
        await page.fill("input[type='email']", self.email)
        await page.wait_for_timeout(500)

        # Enter password
        await page.fill("input[type='password']", self.password)
        await page.wait_for_timeout(500)

        # Click login
        await page.click("button:has-text('Log In')")

        # Wait for redirect
        await page.wait_for_url("**/", timeout=10000)

    async def post(self, message: str, symbol: Optional[str] = None) -> bool:
        """Post a message to Stocktwits."""
        try:
            page = await self._get_authenticated_page()

            # Go to home page - use load instead of networkidle (faster)
            await page.goto("https://stocktwits.com/", wait_until="load", timeout=60000)
            await page.wait_for_timeout(2000)

            # Try to find and click in the compose area
            compose_selectors = [
                "[placeholder*='message' i]",
                "[placeholder*='post' i]",
                "[placeholder*='What' i]",
                "textarea",
                "[contenteditable='true']"
            ]

            found_compose = False
            for selector in compose_selectors:
                try:
                    await page.click(selector, timeout=3000)
                    found_compose = True
                    await page.wait_for_timeout(300)
                    break
                except:
                    continue

            # Type the message
            if found_compose:
                try:
                    await page.fill("textarea, [contenteditable='true']", message)
                except:
                    await page.type("textarea, [contenteditable='true']", message, delay=5)

                if symbol and symbol not in message:
                    try:
                        await page.type("textarea, [contenteditable='true']", f" ${symbol}", delay=5)
                    except:
                        pass

                await page.wait_for_timeout(500)

                # Click post button
                post_selectors = [
                    "button:has-text('Post')",
                    "button:has-text('Share')",
                    "button[type='submit']"
                ]

                for selector in post_selectors:
                    try:
                        await page.click(selector, timeout=3000)
                        break
                    except:
                        continue

                # Wait for post to send
                await page.wait_for_timeout(2000)

            logger.info(f"Posted to Stocktwits: {message[:50]}...")
            await page.context.browser.close()
            return True

        except Exception as e:
            logger.error(f"Failed to post to Stocktwits: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False


class WebThreadsPoster:
    """Post to Threads using web automation."""

    def __init__(self, instagram_username: str, instagram_password: str, session_dir: str = "./sessions"):
        self.username = instagram_username
        self.password = instagram_password
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "threads_session.json"

    async def _get_authenticated_page(self) -> Page:
        """Get an authenticated page, using saved session if available."""
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()

        # Load saved session if exists
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    storage = json.load(f)
                await context.add_cookies(storage.get('cookies', []))
            except Exception as e:
                logger.warning(f"Failed to load saved session: {e}")

        page = await context.new_page()

        # If no valid session, authenticate
        if not await self._is_authenticated(page):
            await self._authenticate(page)
            # Save session
            cookies = await context.cookies()
            with open(self.session_file, 'w') as f:
                json.dump({'cookies': cookies}, f)

        return page

    async def _is_authenticated(self, page: Page) -> bool:
        """Check if page is authenticated."""
        try:
            await page.goto("https://www.threads.net/", timeout=5000)
            return "login" not in page.url.lower()
        except:
            return False

    async def _authenticate(self, page: Page):
        """Authenticate with Threads via Instagram."""
        await page.goto("https://www.threads.net/login")

        # Click "Log in with Instagram" if available, otherwise enter credentials
        try:
            await page.click("button:has-text('Log in with Instagram')")
            await page.wait_for_timeout(1000)
        except:
            pass

        # Enter Instagram username
        await page.fill("input[type='text'], input[name='username']", self.username)
        await page.wait_for_timeout(500)

        # Enter password
        await page.fill("input[type='password']", self.password)
        await page.wait_for_timeout(500)

        # Click login
        await page.click("button:has-text('Log in'), button[type='submit']")

        # Wait for redirect
        await page.wait_for_url("**/", timeout=10000)

    async def post(self, message: str) -> bool:
        """Post a message to Threads."""
        try:
            page = await self._get_authenticated_page()

            # Go to home
            await page.goto("https://www.threads.net/")

            # Click compose button
            await page.click("[aria-label*='Compose'], button:has-text('New thread')")
            await page.wait_for_timeout(500)

            # Type message
            await page.type("textarea, [contenteditable='true']", message)
            await page.wait_for_timeout(500)

            # Click post/share button
            await page.click("button:has-text('Post'), button:has-text('Share')")

            # Wait for success
            await page.wait_for_timeout(2000)

            logger.info(f"Posted to Threads: {message[:50]}...")
            await page.context.browser.close()
            return True

        except Exception as e:
            logger.error(f"Failed to post to Threads: {e}")
            return False


# Example usage
if __name__ == "__main__":
    async def main():
        # X (Twitter)
        twitter = WebTwitterPoster(
            email="your_email@example.com",
            password="your_password"
        )
        await twitter.post("This is a test post from StockTradingSignals! #trading")

        # Stocktwits
        stocktwits = WebStocktwitsPoster(
            email="your_email@example.com",
            password="your_password"
        )
        await stocktwits.post("Great trading signal today! $AAPL", symbol="AAPL")

        # Threads
        threads = WebThreadsPoster(
            instagram_username="your_username",
            instagram_password="your_password"
        )
        await threads.post("Trading signals are live! Check our posts for more. #trading")

    asyncio.run(main())
