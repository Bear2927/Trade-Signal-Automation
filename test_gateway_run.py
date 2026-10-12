#!/usr/bin/env python3
"""Run Discord gateway and wait for messages (with timeout)."""

import asyncio
import os
import sys

# Use fakeredis
os.environ["FAKEREDIS"] = "1"

# Add src to path
sys.path.insert(0, "/home/bear2927/StockTradingSignals/src")

import fakeredis.aioredis
import src.common.redis_client as redis_client_module

async def fake_initialize(self):
    self._pool = None
    self._client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await self.health_check()
    print("✅ Using fakeredis (in-memory)")

redis_client_module.RedisClient.initialize = fake_initialize

# Now import and run the gateway
from src.common.config import load_config_from_yaml, get_settings
load_config_from_yaml("config/config.yaml")

from src.discord.gateway import DiscordGateway

# Track messages received
messages_received = []

async def main():
    print("Starting Discord gateway test with fakeredis...")

    gateway = DiscordGateway()

    # Override webhook sender to track messages
    from src.common import webhook
    async def mock_send_signal(self, signal_text, source, author, channel, color=0x00FF00):
        messages_received.append({
            "source": source,
            "author": author,
            "channel": channel,
            "text": signal_text[:200]
        })
        print(f"\n📤 WEBHOOK SENT:")
        print(f"   Source: {source}")
        print(f"   Author: {author}")
        print(f"   Channel: {channel}")
        print(f"   Text: {signal_text[:200]}...")
        return True
    webhook.WebhookSender.send_signal = mock_send_signal

    # Also mock the social queue
    from src.social import queue
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
        print("\n⏳ Waiting for messages... (will timeout after 30 seconds if no message)\n")

        # Create gateway task with timeout
        gateway_task = asyncio.create_task(gateway.connect())

        # Wait for either a message or timeout
        try:
            await asyncio.wait_for(gateway_task, timeout=30.0)
        except asyncio.TimeoutError:
            print("\n⏱️  Timeout reached - no messages received in 30 seconds")
            print("   Gateway is connected and working!")
            gateway_task.cancel()
            try:
                await gateway_task
            except asyncio.CancelledError:
                pass

    except KeyboardInterrupt:
        print("\n👋 Stopping...")
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await gateway.close()
        print(f"\n✅ Test complete. Messages received: {len(messages_received)}")

if __name__ == "__main__":
    asyncio.run(main())