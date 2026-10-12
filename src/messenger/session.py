"""Facebook Messenger session management for Playwright."""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)


class MessengerSession:
    """Manages Facebook Messenger browser session persistence."""

    def __init__(self, session_path: str = "./fb_session"):
        self.session_path = Path(session_path)
        self.session_path.mkdir(parents=True, exist_ok=True)

    async def create_session(self, headless: bool = False, target_url: str = "https://www.facebook.com/messages/") -> None:
        """Interactive login to create persistent session."""
        logger.info("Starting interactive Facebook login...")
        logger.info("A browser window will open. Please log in to Facebook Messenger.")
        logger.info("Handle any 2FA prompts. The session will be saved automatically.")

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(self.session_path),
                headless=headless,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ],
            )

            page = await browser.new_page()
            await page.goto(target_url)

            # Wait for manual login
            logger.info("Waiting for login to complete...")
            logger.info("Press Enter in this terminal AFTER you have successfully logged in and can see your messages.")

            # Run input in executor to not block event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input, "Press Enter when logged in...")

            # Verify login by checking for message elements
            try:
                await page.wait_for_selector('div[role="grid"], div[aria-label="Messages"], [data-testid="message_thread"]', timeout=10000)
                logger.info("Login verified - message interface detected")
            except Exception:
                logger.warning("Could not verify message interface, but continuing...")

            # Save cookies and localStorage explicitly
            await self._save_storage_state(page)

            await browser.close()
            logger.info(f"Session saved to {self.session_path}")

    async def _save_storage_state(self, page) -> None:
        """Save cookies and localStorage to session directory."""
        # Cookies are saved automatically by persistent context
        # But we can also save localStorage manually
        try:
            local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
            storage_file = self.session_path / "local_storage.json"
            storage_file.write_text(local_storage)
            logger.debug("LocalStorage saved")
        except Exception as e:
            logger.warning(f"Failed to save localStorage: {e}")

    def session_exists(self) -> bool:
        """Check if session directory exists with cookies."""
        cookies_file = self.session_path / "cookies.json"
        return self.session_path.exists() and cookies_file.exists()

    def get_session_path(self) -> str:
        """Get session path for Playwright."""
        return str(self.session_path)

    async def validate_session(self) -> bool:
        """Validate that saved session still works."""
        if not self.session_exists():
            return False

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(self.session_path),
                    headless=True,
                    args=['--no-sandbox', '--disable-setuid-sandbox'],
                )
                page = await browser.new_page()
                await page.goto("https://www.facebook.com/messages/", timeout=30000)

                # Check if we're logged in (not redirected to login)
                await page.wait_for_load_state("networkidle", timeout=10000)
                url = page.url

                await browser.close()

                if "login" in url.lower() or "checkpoint" in url.lower():
                    logger.warning("Session expired - redirected to login")
                    return False

                logger.info("Session validated successfully")
                return True

        except Exception as e:
            logger.error(f"Session validation failed: {e}")
            return False

    async def clear_session(self) -> None:
        """Clear saved session (force re-login)."""
        import shutil
        if self.session_path.exists():
            shutil.rmtree(self.session_path)
            logger.info("Session cleared")