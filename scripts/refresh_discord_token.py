#!/usr/bin/env python3
"""Automatically refresh Discord user token daily."""

import asyncio
import json
import logging
import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env.local
from dotenv import load_dotenv
env_file = Path(__file__).parent.parent / '.env.local'
load_dotenv(env_file)

# Discord credentials from environment
DISCORD_EMAIL = os.environ.get('DISCORD_EMAIL', '')
DISCORD_PASSWORD = os.environ.get('DISCORD_PASSWORD', '')
CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'config.yaml'

async def refresh_discord_token():
    """Refresh Discord user token using headless browser."""

    logger.info("Starting Discord token refresh...")

    if not DISCORD_EMAIL or not DISCORD_PASSWORD:
        logger.error("❌ DISCORD_EMAIL and DISCORD_PASSWORD environment variables not set")
        return False

    captured_token = None

    async def capture_token(route):
        """Intercept API requests to capture Authorization token."""
        nonlocal captured_token
        try:
            headers = route.request.headers
            if 'authorization' in headers:
                auth = headers['authorization']
                if auth and auth != 'Bearer undefined' and len(auth) > 20:
                    captured_token = auth.replace('Bearer ', '')
        except:
            pass
        await route.continue_()

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            logger.info("🔓 Opening Discord in headless browser...")

            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # Intercept API requests
            await page.route('https://discord.com/api/**', capture_token)

            # Navigate to Discord
            logger.info("📱 Navigating to Discord...")
            await page.goto('https://discord.com/login', wait_until='domcontentloaded')

            await asyncio.sleep(2)

            # Fill in credentials
            logger.info("🔑 Entering credentials...")
            try:
                await page.fill('input[name="email"]', DISCORD_EMAIL, timeout=5000)
                await page.fill('input[name="password"]', DISCORD_PASSWORD, timeout=5000)
                await page.click('button[type="submit"]', timeout=5000)
            except Exception as e:
                logger.warning(f"Could not fill form: {e}")
                await browser.close()
                return False

            # Wait for authentication
            logger.info("⏳ Waiting for authentication...")
            try:
                await page.wait_for_url('https://discord.com/channels/**', timeout=60000)
            except:
                current_url = page.url()
                if '2fa' in current_url.lower() or 'verify' in current_url.lower():
                    logger.error("❌ 2FA is enabled on this Discord account")
                    logger.info("Please disable 2FA in Discord settings to use this script")
                    await browser.close()
                    return False
                logger.warning(f"URL timeout, current: {current_url}")
                await browser.close()
                return False

            # Wait for API calls
            await asyncio.sleep(3)

            # Try to get token from localStorage if not captured
            if not captured_token:
                logger.info("🔎 Trying to extract from localStorage...")
                try:
                    token_data = await page.evaluate("() => localStorage.getItem('token')")
                    if token_data:
                        captured_token = token_data.strip('"')
                except:
                    pass

            await browser.close()

            if not captured_token:
                logger.error("❌ Could not extract token from Discord")
                logger.info("Troubleshooting:")
                logger.info("  1. Disable 2FA in Discord settings")
                logger.info("  2. Verify email and password are correct")
                logger.info("  3. Check if Discord has changed their auth flow")
                return False

            logger.info(f"✅ Token extracted: {captured_token[:20]}...")

            # Update config with new token
            logger.info("📝 Updating config...")
            update_config(captured_token)

            # Restart gateway
            logger.info("🔄 Restarting Discord gateway...")
            restart_gateway()

            logger.info("✅ Token refresh completed successfully")
            return True

    except ImportError:
        logger.error("❌ playwright not installed")
        return False
    except Exception as e:
        logger.error(f"❌ Error refreshing token: {e}")
        import traceback
        traceback.print_exc()
        return False


def update_config(token):
    """Update config.yaml with new token."""
    import yaml

    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)

        config['discord']['user_token'] = token

        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        logger.info("✅ Config updated with new token")
        return True
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return False


def restart_gateway():
    """Restart the Discord gateway."""
    try:
        # Kill existing gateway
        subprocess.run(['pkill', '-f', 'python -m src.main'], check=False)

        import time
        time.sleep(2)

        # Start new gateway
        subprocess.Popen(
            ['python', '-m', 'src.main'],
            cwd=str(Path(__file__).parent.parent),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        logger.info("✅ Gateway restarted")
        return True
    except Exception as e:
        logger.error(f"Error restarting gateway: {e}")
        return False


async def main():
    """Main entry point."""
    success = await refresh_discord_token()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
