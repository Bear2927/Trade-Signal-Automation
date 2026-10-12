#!/usr/bin/env python3
"""Debug script: Show all messages and images found in the chat."""

import asyncio
from playwright.async_api import async_playwright
from pathlib import Path

# Configuration
SESSION_PATH = "./fb_don_cristo_session"
TARGET_CHAT_URL = "https://www.facebook.com/messages/t/1928478913911863"

async def debug_messages():
    """Debug what messages and images are in the chat."""

    print("=" * 70)
    print("MACRO CEO CHAT DEBUG - SHOW ALL MESSAGES")
    print("=" * 70)
    print("")

    # Check if session exists
    if not Path(SESSION_PATH).exists():
        print("❌ Session not found")
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
            await asyncio.sleep(5)

            print("📊 Analyzing chat content...\n")

            # Get ALL data from the page
            page_data = await page.evaluate("""() => {
              const data = {
                totalMessageElements: 0,
                messagesWithText: [],
                allImages: [],
                messagesWithImages: []
              };

              // Count all message-like elements
              const messageElements = document.querySelectorAll('[data-testid="message"], [role="article"], [class*="message"]');
              data.totalMessageElements = messageElements.length;

              // Get all images on page
              const allImgs = document.querySelectorAll('img');
              for (const img of allImgs) {
                data.allImages.push({
                  src: img.src ? img.src.substring(0, 100) : 'no-src',
                  width: img.width,
                  height: img.height,
                  alt: img.alt,
                  title: img.title
                });
              }

              // Analyze message elements
              for (const el of messageElements) {
                const text = el.innerText || el.textContent;
                const cleanText = text ? text.substring(0, 100).trim() : '';

                if (cleanText.length > 0) {
                  const imgElements = el.querySelectorAll('img');
                  const hasImages = imgElements.length > 0;

                  data.messagesWithText.push({
                    text: cleanText,
                    imageCount: imgElements.length,
                    hasImages: hasImages
                  });

                  if (hasImages) {
                    for (const img of imgElements) {
                      data.messagesWithImages.push({
                        messagePreview: cleanText.substring(0, 50),
                        imageSrc: img.src ? img.src.substring(0, 100) : 'no-src',
                        width: img.width,
                        height: img.height
                      });
                    }
                  }
                }
              }

              return data;
            }""")

            print(f"Total message elements found: {page_data['totalMessageElements']}")
            print(f"Messages with text: {len(page_data['messagesWithText'])}")
            print(f"Messages with images: {len(page_data['messagesWithImages'])}")
            print(f"Total images on page: {len(page_data['allImages'])}")
            print("")

            if page_data['messagesWithText']:
                print("=" * 70)
                print("RECENT MESSAGES:")
                print("=" * 70)
                for i, msg in enumerate(page_data['messagesWithText'][-10:], 1):
                    image_indicator = "🖼️ " if msg['hasImages'] else "   "
                    print(f"{image_indicator}Message {i}: {msg['text']}")
                    if msg['hasImages']:
                        print(f"           └─ Contains {msg['imageCount']} image(s)")
                print("")

            if page_data['messagesWithImages']:
                print("=" * 70)
                print("MESSAGES WITH IMAGES:")
                print("=" * 70)
                for i, item in enumerate(page_data['messagesWithImages'], 1):
                    print(f"Image {i}:")
                    print(f"  Message: {item['messagePreview']}")
                    print(f"  Size: {item['width']}x{item['height']}")
                    print(f"  URL: {item['imageSrc']}")
                    print("")
            else:
                print("❌ No images found in messages")
                print("")
                if page_data['allImages']:
                    print("However, found these images on the page:")
                    for img in page_data['allImages'][:5]:
                        print(f"  • {img['width']}x{img['height']}: {img['src']}")

            await browser.close()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_messages())
