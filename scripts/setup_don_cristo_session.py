#!/usr/bin/env python3
"""
Facebook session setup for Don Cristo chat (1928478913911863).

Run this script to log into Facebook and save the authenticated session
for the Don Cristo messenger scraper.
"""

import asyncio
import logging
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Error: playwright not installed. Run: pip install playwright && python -m playwright install chromium")
    sys.exit(1)

# Configuration for Don Cristo chat
SESSION_PATH = "./fb_don_cristo_session"
TARGET_CHAT_URL = "https://www.facebook.com/messages/t/1928478913911863"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Main setup function."""
    logger.info("=" * 70)
    logger.info("Facebook Messenger Session Setup - Don Cristo Chat")
    logger.info("=" * 70)
    logger.info(f"Session will be saved to: {SESSION_PATH}")
    logger.info(f"Target chat: {TARGET_CHAT_URL}")
    logger.info("")
    logger.info("INSTRUCTIONS:")
    logger.info("1. A browser window will open to Facebook Messenger")
    logger.info("2. Log in with your Facebook credentials (if not already logged in)")
    logger.info("3. Complete any 2FA (SMS, authenticator app, etc.)")
    logger.info("4. The browser will navigate to the Don Cristo chat")
    logger.info("5. Verify you can see messages in that chat")
    logger.info("6. Return to this terminal and press ENTER")
    logger.info("")

    session_path = Path(SESSION_PATH)
    session_path.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            logger.info("🔓 Opening browser for login...")
            browser = await p.chromium.launch_persistent_context(
                user_data_dir=str(session_path),
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ],
            )

            page = await browser.new_page()
            logger.info("📱 Navigating to Don Cristo chat...")
            await page.goto(TARGET_CHAT_URL)

            # Wait for manual login
            logger.info("")
            logger.info("⏳ Waiting for you to log in...")
            logger.info("   Once logged in, you'll see the Don Cristo chat messages.")
            logger.info("   Then return to this terminal and press Enter.")
            logger.info("")

            # Run input in executor to not block event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input, "👉 Press Enter when logged in and viewing the chat...")

            # Verify login by checking for message elements
            try:
                await page.wait_for_selector('div[role="grid"], div[aria-label="Messages"], [data-testid="message_thread"]', timeout=10000)
                logger.info("✅ Login verified - message interface detected")
            except Exception:
                logger.warning("⚠️  Could not verify message interface, but continuing...")

            # Save cookies and localStorage explicitly
            local_storage = await page.evaluate("() => JSON.stringify(localStorage)")
            storage_file = session_path / "local_storage.json"
            storage_file.write_text(local_storage)
            logger.debug("💾 LocalStorage saved")

            await browser.close()
            logger.info(f"💾 Session saved to {session_path}")

        logger.info("")
        logger.info("=" * 70)
        logger.info("✅ SUCCESS! Don Cristo session created successfully!")
        logger.info("=" * 70)
        logger.info(f"Session saved to: {SESSION_PATH}")
        logger.info("")
        logger.info("You can now run the Don Cristo scraper:")
        logger.info("  node src/messenger/don_cristo_scraper.js")
        logger.info("")

    except KeyboardInterrupt:
        logger.info("\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
