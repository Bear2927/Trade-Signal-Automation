#!/usr/bin/env python3
"""Test script: Post a message to Discord chatroom webhook to verify integration."""

import asyncio
import aiohttp
from datetime import datetime

# Chatroom webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1559282693194260612/MXQVMSqXDvFenpHjZruYFFW236lcshWgPTSLYHAhloV_TLQMRSZSlJUPAtDnXHQEoBgG"

async def test_webhook():
    """Test posting to the Discord chatroom webhook."""

    # Sample message (replace with actual Don Cristo message if needed)
    test_message = """Looking at the charts right now, we're seeing some interesting patterns forming.
The momentum is building in the tech sector. Keep an eye on NVDA and AAPL - they're setting up for a potential breakout.
Market conditions are favorable for the next 2-3 days."""

    payload = {
        "content": test_message,
        "username": "Don Cristo",
        "avatar_url": "",
    }

    print("=" * 70)
    print("DISCORD CHATROOM WEBHOOK TEST")
    print("=" * 70)
    print("")
    print(f"📨 Author: Don Cristo")
    print(f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"💬 Message:")
    print(f"{test_message}")
    print("")
    print("Sending to Discord webhook...")
    print("")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 204:
                    print("✅ SUCCESS! Message posted to Discord chatroom")
                    print("")
                    print("The webhook is working correctly!")
                    print("Don Cristo's messages will now be posted to your chatroom channel.")
                elif resp.status == 429:
                    print("⚠️  RATE LIMITED - webhook is being called too frequently")
                    print(f"Response: {await resp.text()}")
                else:
                    print(f"❌ FAILED - HTTP {resp.status}")
                    print(f"Response: {await resp.text()}")
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook())
