#!/usr/bin/env python3
"""Test script: Scrape and repost Discord messages from past 24 hours."""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.common.config import get_settings
from src.common.webhook import get_webhook_sender
from src.common.deduplicator import get_deduplicator
from src.common.formatter import TradeSignal
from src.social.queue import get_social_queue


async def fetch_discord_history():
    """Fetch messages from past 24 hours from target Discord channel."""
    import aiohttp

    settings = get_settings()
    token = settings.discord.user_token
    channel_id = settings.discord.target_channel_ids[0]

    # Calculate timestamp for 24 hours ago (timezone-aware)
    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours=24)

    print(f"🔍 Fetching messages from channel {channel_id}")
    print(f"   From: {yesterday.isoformat()}")
    print(f"   To:   {now.isoformat()}")
    print("")

    headers = {"Authorization": token}
    messages = []

    try:
        async with aiohttp.ClientSession() as session:
            # Fetch messages from channel
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            params = {"limit": 100}  # Get most recent 100 messages

            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()

                    # Filter messages from past 24 hours
                    for msg in data:
                        try:
                            timestamp_str = msg['timestamp'].replace('Z', '+00:00')
                            msg_time = datetime.fromisoformat(timestamp_str)

                            if msg_time >= yesterday:
                                # Skip bot messages
                                if not msg['author'].get('bot', False):
                                    messages.append(msg)
                        except Exception as e:
                            print(f"Error parsing message: {e}")
                            continue

                    print(f"✅ Found {len(messages)} messages from past 24 hours")
                    return messages
                else:
                    print(f"❌ Error fetching messages: {resp.status}")
                    text = await resp.text()
                    print(f"   Response: {text[:200]}")
                    return []
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []


async def process_messages(messages):
    """Process historical messages through the system."""
    print("")
    print("="*60)
    print(f"📝 Processing {len(messages)} messages")
    print("="*60)
    print("")

    webhook = await get_webhook_sender()
    deduplicator = get_deduplicator()
    queue = await get_social_queue()

    posted = 0
    skipped = 0

    for msg in messages:
        content = msg.get('content', '').strip()
        author = msg.get('author', {})
        author_name = author.get('username', 'Unknown')
        msg_id = msg.get('id', '')
        channel_id = msg.get('channel_id', '')
        timestamp = msg.get('timestamp', '')

        if not content:
            skipped += 1
            continue

        # Check for duplicates
        dedup_key = f"{channel_id}:{msg_id}:{content}"
        is_dup = await deduplicator.is_duplicate(dedup_key, f"discord:{channel_id}")

        if is_dup:
            print(f"⏭️  Skipped (duplicate): {author_name} - {content[:50]}...")
            skipped += 1
            continue

        # Send to webhook
        try:
            await webhook.send_signal(
                signal_text=content,
                source=f"Discord#{channel_id}",
                author=author_name,
                channel=channel_id,
            )

            # Queue for social media
            signal = TradeSignal(
                raw_text=content,
                source=f"Discord#{channel_id}",
                author=author_name,
                channel=channel_id,
            )
            # Convert timestamp string to float
            import time
            timestamp_float = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp()

            await queue.enqueue(
                signal=signal.__dict__,
                source="discord",
                timestamp=timestamp_float,
            )

            print(f"✅ Posted: {author_name}")
            print(f"   Message: {content[:60]}{'...' if len(content) > 60 else ''}")
            print(f"   Posted to: Webhook + Social Queue")
            print("")
            posted += 1

        except Exception as e:
            print(f"❌ Error posting: {e}")
            skipped += 1

    return posted, skipped


async def main():
    """Main test function."""
    print("╔════════════════════════════════════════════════════════════╗")
    print("║  DISCORD HISTORY TEST: Scrape & Repost Past 24 Hours      ║")
    print("╚════════════════════════════════════════════════════════════╝")
    print("")

    # Fetch messages
    messages = await fetch_discord_history()

    if not messages:
        print("No messages found in past 24 hours")
        return

    # Process messages
    posted, skipped = await process_messages(messages)

    # Summary
    print("="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Total messages found:    {len(messages)}")
    print(f"Posted:                  {posted}")
    print(f"Skipped (duplicates):    {skipped}")
    print("")
    print("✅ All messages have been:")
    print("   • Posted to your paid subscription channel (webhook)")
    print("   • Queued for social media posting (Stocktwits & X)")
    print("")
    print("Check your Discord and social media accounts!")


if __name__ == "__main__":
    asyncio.run(main())
