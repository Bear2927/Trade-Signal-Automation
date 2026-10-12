#!/usr/bin/env python3
"""
Social media OAuth setup helper.

Run this to authenticate with each social media platform and save tokens.
"""

import asyncio
import logging
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
import threading

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.common.config import get_settings, Settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handle OAuth callbacks."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            query = parse_qs(parsed.query)
            self.server.callback_data = query
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization complete! You can close this window.</h1></body></html>")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default log messages


class SocialAuthSetup:
    """Interactive OAuth setup for social platforms."""

    def __init__(self):
        self.settings = get_settings()
        self.callback_data = {}
        self.server = None
        self.server_thread = None

    def start_callback_server(self, port: int = 8080):
        """Start local callback server."""
        self.server = HTTPServer(("localhost", port), OAuthCallbackHandler)
        self.server.callback_data = {}
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        logger.info(f"Callback server started on http://localhost:{port}")

    def stop_callback_server(self):
        """Stop callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

    def wait_for_callback(self, timeout: int = 300) -> dict:
        """Wait for OAuth callback."""
        import time
        start = time.time()
        while time.time() - start < timeout:
            if hasattr(self.server, 'callback_data') and self.server.callback_data:
                return self.server.callback_data
            time.sleep(0.5)
        raise TimeoutError("OAuth callback timeout")

    async def setup_twitter(self) -> dict:
        """Setup Twitter OAuth 2.0."""
        logger.info("Setting up Twitter/X OAuth...")
        logger.info("1. Go to https://developer.twitter.com/en/portal/dashboard")
        logger.info("2. Create a Project/App if not exists")
        logger.info("3. Enable OAuth 2.0 with PKCE")
        logger.info("4. Add callback URL: http://localhost:8080/callback")
        logger.info("5. Save API Key, API Secret, Bearer Token")
        logger.info("")

        # For user context, we need the user to authorize
        # This is a simplified version - in production use tweepy's OAuth flow
        api_key = input("Enter Twitter API Key: ").strip()
        api_secret = input("Enter Twitter API Secret: ").strip()
        bearer_token = input("Enter Twitter Bearer Token: ").strip()
        access_token = input("Enter Twitter Access Token: ").strip()
        refresh_token = input("Enter Twitter Refresh Token (optional): ").strip()

        return {
            "twitter": {
                "api_key": api_key,
                "api_secret": api_secret,
                "bearer_token": bearer_token,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "enabled": True,
            }
        }

    async def setup_stocktwits(self) -> dict:
        """Setup Stocktwits OAuth."""
        logger.info("Setting up Stocktwits OAuth...")
        logger.info("1. Go to https://api.stocktwits.com/developers/apps")
        logger.info("2. Register new application")
        logger.info("3. Callback URL: http://localhost:8080/callback")
        logger.info("4. Get Client ID and Client Secret")
        logger.info("")

        client_id = input("Enter Stocktwits Client ID: ").strip()
        client_secret = input("Enter Stocktwits Client Secret: ").strip()

        # For Stocktwits, you typically get access token via OAuth flow
        # Simplified here
        access_token = input("Enter Stocktwits Access Token: ").strip()

        return {
            "stocktwits": {
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "enabled": True,
            }
        }

    async def setup_threads(self) -> dict:
        """Setup Threads (Instagram Graph API) OAuth."""
        logger.info("Setting up Threads OAuth...")
        logger.info("1. Go to https://developers.facebook.com/")
        logger.info("2. Create App -> Instagram Graph API")
        logger.info("3. Add callback URL: http://localhost:8080/callback/threads")
        logger.info("4. Business verification required for production")
        logger.info("")

        app_id = input("Enter Threads App ID: ").strip()
        app_secret = input("Enter Threads App Secret: ").strip()
        user_access_token = input("Enter Threads User Access Token: ").strip()

        return {
            "threads": {
                "app_id": app_id,
                "app_secret": app_secret,
                "user_access_token": user_access_token,
                "enabled": True,
            }
        }

    async def setup_reddit(self) -> dict:
        """Setup Reddit OAuth."""
        logger.info("Setting up Reddit OAuth...")
        logger.info("1. Go to https://www.reddit.com/prefs/apps")
        logger.info("2. Create 'script' type app")
        logger.info("3. Callback URL: http://localhost:8080/callback/reddit")
        logger.info("")

        client_id = input("Enter Reddit Client ID: ").strip()
        client_secret = input("Enter Reddit Client Secret: ").strip()
        refresh_token = input("Enter Reddit Refresh Token: ").strip()

        return {
            "reddit": {
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "enabled": True,
            }
        }

    async def setup_telegram(self) -> dict:
        """Setup Telegram Bot."""
        logger.info("Setting up Telegram Bot...")
        logger.info("1. Message @BotFather on Telegram")
        logger.info("2. Send /newbot and follow instructions")
        logger.info("3. Save the bot token")
        logger.info("4. Add bot to your channel/group as admin")
        logger.info("5. Get chat_id (use @userinfobot or similar)")
        logger.info("")

        bot_token = input("Enter Telegram Bot Token: ").strip()
        chat_ids_input = input("Enter Chat IDs (comma-separated): ").strip()
        chat_ids = [c.strip() for c in chat_ids_input.split(",") if c.strip()]

        return {
            "telegram": {
                "bot_token": bot_token,
                "chat_ids": chat_ids,
                "enabled": True,
            }
        }

    async def setup_linkedin(self) -> dict:
        """Setup LinkedIn OAuth."""
        logger.info("Setting up LinkedIn OAuth...")
        logger.info("1. Go to https://www.linkedin.com/developers/")
        logger.info("2. Create App -> Products: 'Share on LinkedIn'")
        logger.info("3. Callback URL: http://localhost:8080/callback/linkedin")
        logger.info("")

        client_id = input("Enter LinkedIn Client ID: ").strip()
        client_secret = input("Enter LinkedIn Client Secret: ").strip()
        access_token = input("Enter LinkedIn Access Token: ").strip()

        return {
            "linkedin": {
                "client_id": client_id,
                "client_secret": client_secret,
                "access_token": access_token,
                "enabled": True,
            }
        }

    async def setup_email(self) -> dict:
        """Setup SendGrid Email."""
        logger.info("Setting up SendGrid Email...")
        logger.info("1. Go to https://app.sendgrid.com/settings/api_keys")
        logger.info("2. Create API Key with 'Mail Send' permission")
        logger.info("3. Verify sender identity (domain or single email)")
        logger.info("")

        api_key = input("Enter SendGrid API Key: ").strip()
        from_email = input("Enter From Email (verified): ").strip()
        subscriber_list_id = input("Enter SendGrid Contact List ID (optional): ").strip()

        return {
            "email": {
                "sendgrid_api_key": api_key,
                "from_email": from_email,
                "subscriber_list_id": subscriber_list_id,
                "enabled": True,
            }
        }

    async def run_interactive(self):
        """Run interactive setup for all platforms."""
        logger.info("=" * 60)
        logger.info("Social Media OAuth Setup")
        logger.info("=" * 60)
        logger.info("This will guide you through setting up each platform.")
        logger.info("Press Ctrl+C to skip any platform.\n")

        updates = {}

        platforms = [
            ("Twitter/X", self.setup_twitter),
            ("Stocktwits", self.setup_stocktwits),
            ("Threads", self.setup_threads),
            ("Reddit", self.setup_reddit),
            ("Telegram", self.setup_telegram),
            ("LinkedIn", self.setup_linkedin),
            ("Email (SendGrid)", self.setup_email),
        ]

        for name, setup_func in platforms:
            try:
                logger.info(f"\n--- {name} ---")
                result = await setup_func()
                updates.update(result)
                logger.info(f"✅ {name} configured")
            except KeyboardInterrupt:
                logger.info(f"⏭️  Skipped {name}")
            except Exception as e:
                logger.error(f"❌ {name} setup failed: {e}")

        # Save to config.yaml
        await self.save_config(updates)

    async def save_config(self, updates: dict):
        """Save configuration to config.yaml."""
        import yaml

        config_path = Path("config/config.yaml")
        config_path.parent.mkdir(exist_ok=True)

        # Load existing
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Merge updates
        def deep_merge(base: dict, update: dict) -> dict:
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    base[key] = deep_merge(base[key], value)
                else:
                    base[key] = value
            return base

        config = deep_merge(config, updates)

        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"\n✅ Configuration saved to {config_path}")


async def main():
    """Main entry point."""
    setup = SocialAuthSetup()
    setup.start_callback_server()

    try:
        await setup.run_interactive()
    finally:
        setup.stop_callback_server()


if __name__ == "__main__":
    asyncio.run(main())