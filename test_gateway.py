#!/usr/bin/env python3
"""Test Discord gateway with fakeredis (no Redis server needed)."""

import asyncio
import os
import sys

# Use fakeredis
os.environ["FAKEREDIS"] = "1"

# Add src to path
sys.path.insert(0, "/home/bear2927/StockTradingSignals/src")

import fakeredis.aioredis
import redis.asyncio as redis

# Monkey-patch redis to use fakeredis
import src.common.redis_client as redis_client_module
original_init = redis_client_module.RedisClient.initialize

async def fake_initialize(self):
    self._pool = None
    self._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await self.health_check()
    print("✅ Using fakeredis (in-memory)")

redis_client_module.RedisClient.initialize = fake_initialize

# Now import and run the gateway
from src.common.config import load_config_from_yaml, get_settings
load_config_from_yaml("config/config.yaml")

# Debug: Check what token is loaded
s = get_settings()
print(f"DEBUG: Loaded token: {s.discord.user_token[:20]}..." if s.discord.user_token else "DEBUG: Token is EMPTY!")
print(f"DEBUG: Target channels: {s.discord.target_channel_ids}")

from src.discord.gateway import DiscordGateway

async def main():
    print("Starting Discord gateway test with fakeredis...")

    gateway = DiscordGateway()
    print(f"DEBUG: Gateway token: {gateway._token[:20]}..." if gateway._token else "DEBUG: Gateway token is EMPTY!")

    # Override webhook sender to just print
    from src.common import webhook
    original_send = webhook.WebhookSender.send_signal

    async def mock_send_signal(self, signal_text, source, author, channel, color=0x00FF00):
        print(f"\n📤 WOULD SEND TO WEBHOOK:")
        print(f"   Source: {source}")
        print(f"   Author: {author}")
        print(f"   Channel: {channel}")
        print(f"   Text: {signal_text[:200]}...")
        return True

    webhook.WebhookSender.send_signal = mock_send_signal

    # Also mock the social queue
    from src.social import queue
    original_enqueue = queue.SocialQueue.enqueue

    async def mock_enqueue(self, signal, source, timestamp, platforms=None, priority=0):
        print(f"\n📥 QUEUED FOR SOCIAL MEDIA:")
        print(f"   Signal: {signal.get('ticker', 'N/A')} {signal.get('direction', 'N/A')}")
        print(f"   Platforms: {platforms}")
        return "fake-job-id"

    queue.SocialQueue.enqueue = mock_enqueue

    try:
        # Run for a bit
        print("\n🔌 Connecting to Discord gateway...")
        print(f"   Monitoring channel: 1195875428234174614")
        print(f"   Webhook: https://discord.com/api/webhooks/1558359632743759872/***")
        print("\n⏳ Waiting for messages... (Press Ctrl+C to stop)\n")

        await gateway.connect()
    except KeyboardInterrupt:
        print("\n👋 Stopping...")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await gateway.close()

if __name__ == "__main__":
    asyncio.run(main())