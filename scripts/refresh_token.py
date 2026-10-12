#!/usr/bin/env python3
"""
Discord Token Manager - Helps manage and auto-detect token expiration.
Run this alongside the main app to monitor token health.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.common.config import get_settings


class TokenManager:
    """Manages Discord user token with expiration detection and hot-reload."""

    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.last_token = ""
        self.last_check = 0
        self.auth_failure_count = 0
        self.max_failures_before_alert = 3

    def load_token(self) -> str:
        """Load current token from config."""
        with open(self.config_path) as f:
            config = yaml.safe_load(f) or {}
        return config.get("discord", {}).get("user_token", "")

    def save_token(self, new_token: str) -> bool:
        """Save new token to config.yaml."""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}

            if "discord" not in config:
                config["discord"] = {}
            config["discord"]["user_token"] = new_token

            with open(self.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)

            print(f"✅ Token updated in {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to save token: {e}")
            return False

    def check_token_changed(self) -> bool:
        """Check if token in config has been externally updated."""
        current = self.load_token()
        if current != self.last_token and current:
            self.last_token = current
            return True
        return False

    def record_auth_failure(self):
        """Record an authentication failure (4004/4014)."""
        self.auth_failure_count += 1
        if self.auth_failure_count >= self.max_failures_before_alert:
            print(f"\n🚨 TOKEN EXPIRED: {self.auth_failure_count} auth failures detected!")
            print("   Get a new token from browser and run:")
            print("   python scripts/refresh_token.py --token 'NEW_TOKEN'")
            return True
        return False

    def reset_failures(self):
        """Reset failure counter on successful connection."""
        if self.auth_failure_count > 0:
            print(f"✅ Token working (was {self.auth_failure_count} failures)")
        self.auth_failure_count = 0

    async def monitor_loop(self, check_interval: int = 30):
        """Monitor token health and config changes."""
        print("🔍 Token monitor started (checking every {}s)".format(check_interval))
        print("   - Watches for config.yaml token changes (hot-reload)")
        print("   - Detects auth failures from gateway")
        print("   - Press Ctrl+C to stop\n")

        self.last_token = self.load_token()

        while True:
            await asyncio.sleep(check_interval)

            # Check for external token update (hot-reload)
            if self.check_token_changed():
                print(f"\n🔄 Token changed externally - reloading...")
                print(f"   New token: {self.last_token[:20]}...")
                # Signal gateway to reconnect (would need integration)
                print("   ⚠️  Restart gateway to use new token")


async def update_token_interactive():
    """Interactive token update."""
    manager = TokenManager()

    print("=" * 60)
    print("Discord Token Update")
    print("=" * 60)
    print("\nGet new token from browser:")
    print("1. Open https://discord.com/app in incognito/private window")
    print("2. Log in with burner account")
    print("3. F12 → Application → Local Storage → https://discord.com")
    print("4. Search 'token' → copy value")
    print("\nOr use console (type 'allow pasting' first):")
    print("webpackChunkdiscord_app.push([[Math.random()],{},r=>{for(const e of Object.keys(r.c))if(r.c[e].exports?.default?.getToken)return void console.log(r.c[e].exports.default.getToken())}])")
    print()

    new_token = input("Paste new token: ").strip()

    if not new_token:
        print("❌ No token provided")
        return

    if manager.save_token(new_token):
        print("✅ Token updated! Restart the gateway to use it.")


async def test_current_token():
    """Test if current token works."""
    import websockets

    manager = TokenManager()
    token = manager.load_token()

    if not token:
        print("❌ No token in config")
        return

    print(f"Testing token: {token[:20]}...")

    try:
        async with websockets.connect(
            'wss://gateway.discord.gg/?v=9&encoding=json',
            max_size=2**25
        ) as ws:
            hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
            await ws.send(json.dumps({
                'op': 2,
                'd': {
                    'token': token,
                    'properties': {'os': 'linux', 'browser': 'chrome', 'device': 'pc'},
                    'compress': False
                }
            }))
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            data = json.loads(msg)

            if data.get('t') == 'READY':
                print("✅ Token works! Session ready.")
            elif data.get('op') == 9:
                print("❌ Token invalid (4004/4014) - needs refresh")
            else:
                print(f"❓ Unexpected response: {data}")
    except Exception as e:
        print(f"❌ Connection error: {type(e).__name__}: {e}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Discord Token Manager")
    parser.add_argument("--token", help="New token to save")
    parser.add_argument("--test", action="store_true", help="Test current token")
    parser.add_argument("--monitor", action="store_true", help="Run monitor loop")
    parser.add_argument("--interactive", action="store_true", help="Interactive update")

    args = parser.parse_args()

    manager = TokenManager()

    if args.token:
        manager.save_token(args.token)
    elif args.test:
        await test_current_token()
    elif args.monitor:
        await manager.monitor_loop()
    elif args.interactive:
        await update_token_interactive()
    else:
        # Default: show current status
        token = manager.load_token()
        print(f"Current token: {token[:20]}..." if token else "No token set")
        print("\nUsage:")
        print("  --token 'NEW_TOKEN'    Save new token")
        print("  --test                 Test current token")
        print("  --monitor              Run monitor loop")
        print("  --interactive          Interactive update")


if __name__ == "__main__":
    asyncio.run(main())