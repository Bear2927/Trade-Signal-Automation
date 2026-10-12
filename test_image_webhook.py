#!/usr/bin/env python3
"""Test posting an image to Discord webhook."""

import asyncio
import aiohttp

WEBHOOK_URL = "https://discord.com/api/webhooks/1559282693194260612/MXQVMSqXDvFenpHjZruYFFW236lcshWgPTSLYHAhloV_TLQMRSZSlJUPAtDnXHQEoBgG"

async def test_image_webhook():
    """Test posting image embed to Discord."""

    print("=" * 70)
    print("IMAGE WEBHOOK TEST")
    print("=" * 70)
    print("")

    # Sample message with image
    message_text = "Check out this chart pattern I found - looking bullish 📈"
    image_url = "https://via.placeholder.com/600x400?text=Chart+Pattern"

    print(f"📝 Message: {message_text}")
    print(f"🖼️  Image: {image_url}")
    print("")
    print("Posting to Discord webhook...")
    print("")

    payload = {
        "username": "Macro CEO",
        "avatar_url": "",
        "embeds": [{
            "description": message_text,
            "image": {
                "url": image_url,
            },
            "color": 0x5865F2,  # Discord blue
            "footer": {
                "text": "Image from Messenger",
            },
        }]
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK_URL,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 204:
                    print("✅ SUCCESS!")
                    print("")
                    print("=" * 70)
                    print("Image posting to Discord is working correctly!")
                    print("=" * 70)
                    print("")
                    print("When Macro CEO posts a message with an image,")
                    print("it will appear in your Discord chatroom like this.")
                else:
                    print(f"❌ Failed - HTTP {resp.status}")
                    print(f"Response: {await resp.text()}")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_image_webhook())
