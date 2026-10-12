# Web Automation Posting Guide

This guide explains how to use Playwright web automation to post to social media platforms **without API keys**.

## Why Web Automation?

✅ **No API costs** - X (Twitter) paid API removed  
✅ **Works with closed APIs** - Stocktwits registration closed  
✅ **No API keys needed** - Just account credentials  
✅ **Always current** - Automatically adapts to UI changes  
✅ **Already installed** - You have Playwright ready to go

## Setup

### 1. Enable Web Automation Posters

Edit `config/config.yaml` and add:

```yaml
web_automation:
  enabled: true
  
  twitter:
    enabled: true
    email: "your_x_email@example.com"
    password: "your_x_password"  # Use app password if 2FA enabled
  
  stocktwits:
    enabled: true
    email: "your_stocktwits_email@example.com"
    password: "your_stocktwits_password"
  
  threads:
    enabled: true
    instagram_username: "your_instagram_username"
    instagram_password: "your_instagram_password"
```

### 2. Add to .env (Recommended)

```bash
# Web Automation - X (Twitter)
WEB_AUTOMATION__TWITTER__ENABLED=true
WEB_AUTOMATION__TWITTER__EMAIL=your_email@example.com
WEB_AUTOMATION__TWITTER__PASSWORD=your_password

# Web Automation - Stocktwits
WEB_AUTOMATION__STOCKTWITS__ENABLED=true
WEB_AUTOMATION__STOCKTWITS__EMAIL=your_email@example.com
WEB_AUTOMATION__STOCKTWITS__PASSWORD=your_password

# Web Automation - Threads
WEB_AUTOMATION__THREADS__ENABLED=true
WEB_AUTOMATION__THREADS__INSTAGRAM_USERNAME=your_username
WEB_AUTOMATION__THREADS__INSTAGRAM_PASSWORD=your_password
```

### 3. Optional: Use App Passwords (Recommended for Security)

Instead of storing your actual passwords, use app-specific passwords:

**X (Twitter):**
1. Go to https://twitter.com/settings/security_and_account
2. Enable 2-Factor Authentication if not already
3. Generate App Password
4. Use the app password in your config

**Instagram/Threads:**
1. Go to https://www.instagram.com/accounts/login/
2. Settings → Security → App Passwords (if available)
3. Or create a separate Instagram account just for posting

**Stocktwits:**
1. Same approach - use a separate password or app password if available

## How It Works

The web posters use Playwright to:

1. **Open a browser** - Headless (invisible) Chromium browser
2. **Authenticate** - Log in with your credentials
3. **Save session** - Store cookies in `./sessions/` for reuse
4. **Post message** - Automate clicking buttons, typing text
5. **Close browser** - Clean up resources

Saved sessions mean you only authenticate once. Subsequent posts reuse the saved session.

## Security Notes

⚠️ **Important:**

- **Never commit credentials** - Add `.env` to `.gitignore`
- **Use app passwords** - Not your main password
- **Separate accounts** - Consider dedicated accounts for posting bots
- **Rate limiting** - Post slowly to avoid detection
- **Keep sessions private** - Sessions stored in `./sessions/`

```bash
# Ensure sessions directory is private
chmod 700 ./sessions
```

## Testing

### Test Individual Platform

```bash
# Test X (Twitter)
python -c "
from src.social.web_posters import WebTwitterPoster
import asyncio

poster = WebTwitterPoster(
    email='your_email@example.com',
    password='your_password'
)

result = asyncio.run(poster.post('Test post from StockTradingSignals! #trading'))
print('✓ Posted!' if result else '✗ Failed')
"

# Test Stocktwits
python -c "
from src.social.web_posters import WebStocktwitsPoster
import asyncio

poster = WebStocktwitsPoster(
    email='your_email@example.com',
    password='your_password'
)

result = asyncio.run(poster.post('Great signal today! \$AAPL', symbol='AAPL'))
print('✓ Posted!' if result else '✗ Failed')
"

# Test Threads
python -c "
from src.social.web_posters import WebThreadsPoster
import asyncio

poster = WebThreadsPoster(
    instagram_username='your_username',
    instagram_password='your_password'
)

result = asyncio.run(poster.post('Trading signals are live! #trading'))
print('✓ Posted!' if result else '✗ Failed')
"
```

### Run Full Test Suite

```bash
cd /home/bear2927/StockTradingSignals
source .venv/bin/activate
python scripts/test_web_posting.py
```

## Troubleshooting

### "Login Failed" Error

**X (Twitter):**
- If 2FA enabled, use [App Password](https://twitter.com/settings/security_and_account) instead
- Check email/password are correct
- Try logging in manually first to clear any blocks

**Stocktwits:**
- Verify email and password
- Check if account needs verification
- Try manual login first

**Threads/Instagram:**
- Make sure account is not restricted
- Check if 2FA is enabled (use app password)
- Verify Instagram account is eligible for Threads

### "Element Not Found" Error

The UI changes frequently. Update selectors in `web_posters.py`:

```python
# Find the correct selector using browser dev tools
# Change this line:
await page.click("[data-testid='SideNav_NewTweet_Button']")
# To the actual current selector
```

### "Session Expired" Error

Sessions expire periodically. The script will automatically re-authenticate:

```bash
# To force fresh authentication, delete saved sessions
rm -rf ./sessions/*.json

# Next post will re-authenticate automatically
```

### Slow Posting / Timeouts

Increase timeouts in `web_posters.py`:

```python
# Change this:
await page.wait_for_timeout(1000)
# To this:
await page.wait_for_timeout(3000)
```

Or add retries:

```python
async def post_with_retry(self, message, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await self.post(message)
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(5)  # Wait 5 seconds between retries
            else:
                raise e
```

## Comparing Approaches

| Feature | Web Automation | API |
|---------|---|---|
| X (Twitter) | ✅ Free | ❌ Paid ($0.50+ per 100K tweets) |
| Stocktwits | ✅ Works | ❌ Closed registration |
| Threads | ✅ Works | ⚠️ Complex setup |
| Speed | ⚠️ Slower | ✅ Faster |
| Reliability | ⚠️ UI changes break | ✅ Stable |
| Maintenance | ⚠️ High | ✅ Low |
| Session management | ✅ Automatic | N/A |

## Advanced: Custom Selectors

If a platform updates its UI, find new selectors:

1. **Open browser dev tools:**
   ```bash
   playwright codegen https://x.com
   ```

2. **Find the element you need** - Right-click → Inspect
3. **Copy the selector** - Use in code
4. **Update web_posters.py** with new selectors

## Hybrid Approach (Recommended)

Use both APIs and web automation:

```python
async def post(self, message: str):
    # Try API first (faster)
    try:
        return await self.api_post(message)
    except Exception:
        # Fall back to web automation if API fails
        return await self.web_post(message)
```

This gives you speed + reliability!

## Next Steps

1. ✅ Update config with credentials
2. ✅ Test each platform manually
3. ✅ Monitor logs for posting activity
4. ✅ Enable in scheduler
5. ✅ Verify posts appear on accounts

Done! You're now posting to social media without any API limitations! 🚀
