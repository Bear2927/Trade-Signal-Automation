#!/usr/bin/env python3
"""Validate and refresh Messenger session on startup if needed."""

import asyncio
import logging
import sys
import os
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright
    from dotenv import load_dotenv
except ImportError:
    print("Error: playwright or python-dotenv not installed")
    sys.exit(1)

# Load environment variables from .env.local
load_dotenv(Path(__file__).parent.parent / ".env.local")

# Configuration
SESSION_PATH = Path(__file__).parent.parent / "fb_session"
TARGET_CHAT_URL = "https://www.facebook.com/messages/t/1929174430523823"
LOG_FILE = Path(__file__).parent.parent / "logs" / "messenger_session.log"

handlers = [logging.StreamHandler()]

# Try to add file handler, but continue if it fails
try:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(LOG_FILE))
except (PermissionError, OSError):
    print(f"Warning: Cannot write to log file {LOG_FILE}, logging to console only")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=handlers
)
logger = logging.getLogger(__name__)


async def validate_session():
    """Check if existing session is still valid."""
    logger.info("Validating Messenger session...")

    if not SESSION_PATH.exists():
        logger.warning("Session directory not found - needs authentication")
        return False

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_PATH),
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ],
                timeout=30000,
            )

            page = await context.new_page()
            await page.goto(TARGET_CHAT_URL, wait_until='domcontentloaded', timeout=30000)

            # Check if redirected to login (indicates session expired)
            current_url = page.url

            if 'login' in current_url.lower() or 'checkpoint' in current_url.lower():
                logger.warning("Session expired - redirected to login")
                await context.close()
                return False

            # Try to find messages (indicates successful authentication)
            try:
                await page.wait_for_selector(
                    'div[role="grid"], div[aria-label="Messages"], [data-testid="message_thread"]',
                    timeout=10000
                )
                logger.info("✅ Session is valid and authenticated")
                await context.close()
                return True
            except:
                logger.warning("Could not find message elements - session may be invalid")
                await context.close()
                return False

    except Exception as e:
        logger.error(f"Session validation failed: {e}")
        return False


async def refresh_session():
    """Refresh Messenger session with automatic authentication."""
    fb_email = os.getenv("FACEBOOK_EMAIL")
    fb_password = os.getenv("FACEBOOK_PASSWORD")

    logger.info("=" * 60)
    logger.info("Facebook Messenger Session Setup")
    logger.info("=" * 60)
    logger.info(f"Session path: {SESSION_PATH}")
    logger.info(f"Target chat: {TARGET_CHAT_URL}")
    if fb_email and fb_password:
        logger.info("Mode: AUTOMATIC AUTHENTICATION")
    else:
        logger.info("Mode: INTERACTIVE (credentials not configured)")
    logger.info("")

    SESSION_PATH.mkdir(parents=True, exist_ok=True)

    try:
        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir=str(SESSION_PATH),
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-blink-features=AutomationControlled',
                ],
            )

            page = await context.new_page()
            await page.goto(TARGET_CHAT_URL, wait_until='domcontentloaded', timeout=60000)

            # If credentials configured, try automatic login
            if fb_email and fb_password:
                logger.info("Attempting automatic authentication...")
                try:
                    await asyncio.sleep(2)
                    current_url = page.url

                    if 'login' in current_url.lower():
                        logger.info("Login page detected, filling credentials...")

                        # Try to fill email field
                        await page.fill('input[type="email"]', fb_email, timeout=3000)
                        logger.info("✓ Email filled")

                        await asyncio.sleep(0.5)

                        # Fill password
                        await page.fill('input[type="password"]', fb_password, timeout=3000)
                        logger.info("✓ Password filled")

                        # Submit
                        await page.press('input[type="password"]', 'Enter')
                        logger.info("✓ Submitted login form")

                        await asyncio.sleep(4)

                    # Verify messages loaded
                    await page.wait_for_selector(
                        'div[role="grid"], div[aria-label="Messages"], [data-testid="message_thread"]',
                        timeout=15000
                    )
                    logger.info("✅ Automatic authentication successful!")

                except Exception as e:
                    logger.error(f"Automatic authentication failed: {e}")
                    await context.close()
                    return False
            else:
                logger.info("No credentials configured - skipping auto-auth")
                await context.close()
                return False

            await context.close()
            logger.info("✅ Session saved successfully")
            return True

    except Exception as e:
        logger.error(f"Session refresh failed: {e}")
        return False


async def main():
    """Main validation and refresh logic."""
    logger.info(f"Messenger Session Validator - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if session is valid
    is_valid = await validate_session()

    if is_valid:
        logger.info("✅ No action needed - session is authenticated")
        return 0

    # Session is invalid or missing - need to refresh
    logger.warning("Session needs refresh")

    # Try to refresh
    success = await refresh_session()

    if success:
        logger.info("✅ Session refresh completed successfully")
        return 0
    else:
        logger.error("❌ Session refresh failed - credentials may be incorrect or 2FA required")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
