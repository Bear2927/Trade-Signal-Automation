#!/usr/bin/env python3
"""Test script: Find and post Macro CEO's last message with an image."""

import asyncio
import aiohttp
from playwright.async_api import async_playwright
from pathlib import Path
import time

# Configuration
SESSION_PATH = "./fb_don_cristo_session"
TARGET_CHAT_URL = "https://www.facebook.com/messages/t/1928478913911863"
WEBHOOK_URL = "https://discord.com/api/webhooks/1559282693194260612/MXQVMSqXDvFenpHjZruYFFW236lcshWgPTSLYHAhloV_TLQMRSZSlJUPAtDnXHQEoBgG"

async def test_image_scraping():
    """Test image scraping from Messenger with improved detection."""

    print("=" * 70)
    print("MACRO CEO IMAGE SCRAPING TEST (IMPROVED)")
    print("=" * 70)
    print("")
    print(f"Session: {SESSION_PATH}")
    print(f"Chat URL: {TARGET_CHAT_URL}")
    print("")

    # Check if session exists
    if not Path(SESSION_PATH).exists():
        print("❌ Session not found. Please run setup_don_cristo_session.py first")
        return

    try:
        async with async_playwright() as p:
            print("🔓 Opening authenticated browser session...")

            browser = await p.chromium.launch_persistent_context(
                user_data_dir=SESSION_PATH,
                headless=False,
            )

            page = await browser.new_page()
            print("📱 Navigating to Macro CEO chat...")
            await page.goto(TARGET_CHAT_URL, wait_until="domcontentloaded")

            # Wait for messages to load
            await asyncio.sleep(3)

            print("🔍 Searching for messages with images from Macro CEO...")
            print("")

            # Extract all messages and look for ones with images - IMPROVED DETECTION
            messages_data = await page.evaluate("""() => {
              const messages = [];

              // Get all message containers
              const messageElements = document.querySelectorAll('[data-testid="message"], [role="article"]');

              for (const el of messageElements) {
                // Try to get author
                const authorEl = el.querySelector('[data-testid="AuthorName"]') ||
                                el.querySelector('span[aria-label*="sent by"]');
                const author = authorEl ? authorEl.textContent.trim() : null;

                // Get text content
                const text = el.innerText || el.textContent;

                // Look for images - IMPROVED detection
                const allImages = el.querySelectorAll('img');
                const images = [];

                for (const img of allImages) {
                  const src = img.src || img.getAttribute('data-src');

                  // Skip if no src
                  if (!src) continue;

                  // Skip data URIs
                  if (src.includes('data:')) continue;

                  // Skip tiny images (likely avatars/icons) - reduced threshold
                  if (img.width < 50 || img.height < 50) continue;

                  // Skip images with avatar/icon-like names
                  if (src.includes('avatar') || src.includes('icon') || src.includes('emoji') || src.includes('profile')) continue;

                  images.push(src);
                }

                if (author && text && images.length > 0) {
                  messages.push({
                    author: author,
                    text: text.substring(0, 500),
                    images: images,
                    hasImage: true
                  });
                }
              }

              return messages;
            }""")

            await browser.close()

            if not messages_data:
                print("❌ No messages with images found")
                print("")
                print("Possible reasons:")
                print("  • Don Cristo hasn't posted images in this chat yet")
                print("  • Images may be in a different format than expected")
                print("  • Try sending a test image to the chat")
                return

            print(f"✅ Found {len(messages_data)} message(s) with images")
            print("")

            # Process the last message with an image
            last_message = messages_data[-1]

            print("Last message with image:")
            print("-" * 70)
            print(f"Author: {last_message['author']}")
            print(f"Message: {last_message['text'][:100]}...")
            print(f"Images: {len(last_message['images'])}")
            print(f"Image URL: {last_message['images'][0][:80]}...")
            print("-" * 70)
            print("")

            # Post to Discord
            print("📤 Posting to Discord webhook...")

            payload = {
                "username": "Macro CEO",
                "avatar_url": "",
                "embeds": [{
                    "description": last_message['text'][:2000],
                    "image": {
                        "url": last_message['images'][0],
                    },
                    "color": 0x5865F2,  # Discord blue
                    "footer": {
                        "text": "Image from Messenger",
                    },
                }]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status == 204:
                        print("✅ SUCCESS! Message with image posted to Discord")
                        print("")
                        print("=" * 70)
                        print("Macro CEO's image has been sent to Discord!")
                        print("=" * 70)
                    else:
                        print(f"❌ Failed - HTTP {resp.status}")
                        print(f"Response: {await resp.text()}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_image_scraping())
