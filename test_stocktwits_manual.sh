#!/bin/bash
# Manual test for Stocktwits web automation posting

cd /home/bear2927/StockTradingSignals
source .venv/bin/activate

echo "🔄 Testing Stocktwits Web Automation Posting"
echo "=============================================="
echo ""
echo "Email: Barretthiltabrand@yahoo.com"
echo "Password: [configured]"
echo ""
echo "This will:"
echo "  1. Launch a headless browser"
echo "  2. Log in to your Stocktwits account"
echo "  3. Post a test message"
echo "  4. Close browser and save session"
echo ""
echo "⏳ Starting... (this takes 30-60 seconds)"
echo ""

timeout 120 python << 'EOF'
import asyncio
from src.social.web_posters import WebStocktwitsPoster
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

async def test():
    poster = WebStocktwitsPoster(
        email="Barretthiltabrand@yahoo.com",
        password="Urlacher2229!"
    )

    test_message = "Test post from StockTradingSignals! 🚀 #trading #stocks"

    print(f"📝 Message: {test_message}\n")
    print("⏳ Posting... (browser launching)")

    result = await poster.post(test_message)

    print("\n" + "="*50)
    if result:
        print("✅ SUCCESS! Stocktwits posting works!")
        print("\nNext steps:")
        print("  1. Check https://stocktwits.com to see your post")
        print("  2. Restart the app to enable automatic posting")
        print("  3. Posts will be sent during market hours")
    else:
        print("❌ Posting failed")
        print("Check logs above for details")
    print("="*50)

asyncio.run(test())
EOF
