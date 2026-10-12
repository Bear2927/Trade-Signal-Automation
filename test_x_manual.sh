#!/bin/bash
# Manual test for X (Twitter) web automation posting

cd /home/bear2927/StockTradingSignals
source .venv/bin/activate

echo "🔄 Testing X (Twitter) Web Automation Posting"
echo "=============================================="
echo ""
echo "Email: bear2927@yahoo.com"
echo "Password: [configured]"
echo ""
echo "This will:"
echo "  1. Launch a headless browser"
echo "  2. Log in to your X account"
echo "  3. Post a test message"
echo "  4. Close browser and save session"
echo ""
echo "⏳ Starting... (this takes 30-60 seconds)"
echo ""

timeout 120 python << 'EOF'
import asyncio
from src.social.web_posters import WebTwitterPoster
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

async def test():
    poster = WebTwitterPoster(
        email="bear2927@yahoo.com",
        password="Bigdick99!"
    )

    test_message = "Test post from StockTradingSignals! 🚀 #trading #stocks"

    print(f"📝 Message: {test_message}\n")
    print("⏳ Posting... (browser launching)")

    result = await poster.post(test_message)

    print("\n" + "="*50)
    if result:
        print("✅ SUCCESS! X posting works!")
        print("\nNext steps:")
        print("  1. Check https://x.com/home to see your post")
        print("  2. Restart the app to enable automatic posting")
        print("  3. Posts will be sent during market hours")
    else:
        print("❌ Posting failed")
        print("Check logs above for details")
    print("="*50)

asyncio.run(test())
EOF
