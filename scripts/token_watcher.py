#!/usr/bin/env python3
"""
Token File Watcher - Watches config.yaml for token changes and triggers gateway reconnect.
Run this alongside the main app for hot-reload token updates.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import yaml


class TokenFileWatcher:
    """Watches config.yaml for token changes."""

    def __init__(self, config_path: str = "config/config.yaml", callback=None):
        self.config_path = Path(config_path)
        self.callback = callback
        self.last_mtime = 0
        self.last_token = ""
        self._load_current()

    def _load_current(self):
        """Load current token and mtime."""
        try:
            self.last_mtime = self.config_path.stat().st_mtime
            with open(self.config_path) as f:
                config = yaml.safe_load(f) or {}
            self.last_token = config.get("discord", {}).get("user_token", "")
        except Exception:
            pass

    def check(self) -> bool:
        """Check if token has changed. Returns True if changed."""
        try:
            mtime = self.config_path.stat().st_mtime
            if mtime != self.last_mtime:
                self.last_mtime = mtime
                with open(self.config_path) as f:
                    config = yaml.safe_load(f) or {}
                new_token = config.get("discord", {}).get("user_token", "")
                if new_token != self.last_token and new_token:
                    old_preview = self.last_token[:10] + "..." if self.last_token else "none"
                    new_preview = new_token[:10] + "..." if new_token else "none"
                    print(f"\n🔄 Token changed in config.yaml:")
                    print(f"   Old: {old_preview}")
                    print(f"   New: {new_preview}")
                    self.last_token = new_token
                    if self.callback:
                        self.callback(new_token)
                    return True
        except Exception as e:
            print(f"❌ Watcher error: {e}")
        return False

    async def watch_loop(self, interval: float = 5.0):
        """Watch loop."""
        print(f"👁️  Watching {self.config_path} for token changes (every {interval}s)")
        print("   Edit config.yaml and save to trigger hot-reload")
        print("   Press Ctrl+C to stop\n")

        while True:
            await asyncio.sleep(interval)
            self.check()


def on_token_change(new_token: str):
    """Callback when token changes - would trigger gateway refresh."""
    print(f"⚡ Gateway would reconnect with new token")
    # In real usage, this would call gateway.refresh_token() or similar


async def main():
    watcher = TokenFileWatcher(callback=on_token_change)
    try:
        await watcher.watch_loop()
    except KeyboardInterrupt:
        print("\n👋 Stopped watching")


if __name__ == "__main__":
    asyncio.run(main())