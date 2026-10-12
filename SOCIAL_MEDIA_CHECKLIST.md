# Social Media Setup Checklist

Copy and paste this checklist to track your setup progress.

## ✅ X (Twitter) Setup

- [ ] Create X Developer Account at https://developer.twitter.com/
- [ ] Create an app in Developer Portal
- [ ] Get API Key: `______________________________`
- [ ] Get API Secret: `______________________________`
- [ ] Get Bearer Token: `______________________________`
- [ ] Run auth script: `python scripts/setup_social_auth.py`
- [ ] Get Access Token: `______________________________`
- [ ] Get Refresh Token: `______________________________`
- [ ] Enable posting in config

**Quick Links:**
- https://developer.twitter.com/en/portal/dashboard
- https://developer.twitter.com/en/docs/authentication/oauth-2-0/user-access-token

---

## ✅ Stocktwits Setup

- [ ] Create Stocktwits account (if needed)
- [ ] Go to https://stocktwits.com/developers
- [ ] Create a new app
- [ ] Get Client ID: `______________________________`
- [ ] Get Client Secret: `______________________________`
- [ ] Run auth script: `python scripts/setup_social_auth.py`
- [ ] Get Access Token: `______________________________`
- [ ] Enable posting in config

**Quick Links:**
- https://stocktwits.com/developers
- API Docs: https://api.stocktwits.com/

---

## ✅ Threads Setup

- [ ] Have Instagram account ready
- [ ] Create Meta Business Account at https://business.facebook.com
- [ ] Create app at https://developers.facebook.com/apps
- [ ] Get App ID: `______________________________`
- [ ] Get App Secret: `______________________________`
- [ ] Get User Access Token: `______________________________`
- [ ] Enable posting in config

**Quick Links:**
- https://developers.facebook.com/
- https://business.instagram.com/
- Threads API Docs: https://developers.facebook.com/docs/threads

---

## Configuration Steps

### Option 1: Edit .env File (Easiest)

Edit: `/home/bear2927/StockTradingSignals/.env`

Add these lines (replace with your actual tokens):

```bash
# X (Twitter)
SOCIAL__TWITTER__ENABLED=true
SOCIAL__TWITTER__API_KEY=<YOUR_API_KEY>
SOCIAL__TWITTER__API_SECRET=<YOUR_API_SECRET>
SOCIAL__TWITTER__BEARER_TOKEN=<YOUR_BEARER_TOKEN>
SOCIAL__TWITTER__ACCESS_TOKEN=<YOUR_ACCESS_TOKEN>
SOCIAL__TWITTER__REFRESH_TOKEN=<YOUR_REFRESH_TOKEN>

# Stocktwits
SOCIAL__STOCKTWITS__ENABLED=true
SOCIAL__STOCKTWITS__CLIENT_ID=<YOUR_CLIENT_ID>
SOCIAL__STOCKTWITS__CLIENT_SECRET=<YOUR_CLIENT_SECRET>
SOCIAL__STOCKTWITS__ACCESS_TOKEN=<YOUR_ACCESS_TOKEN>

# Threads
SOCIAL__THREADS__ENABLED=true
SOCIAL__THREADS__APP_ID=<YOUR_APP_ID>
SOCIAL__THREADS__APP_SECRET=<YOUR_APP_SECRET>
SOCIAL__THREADS__USER_ACCESS_TOKEN=<YOUR_ACCESS_TOKEN>
```

### Option 2: Use Interactive Setup Script

```bash
python scripts/setup_social_auth.py
```

This will guide you through authenticating with each platform.

---

## Verify Setup

After configuring credentials:

### Check Configuration
```bash
# View enabled platforms (won't show tokens)
grep -E "ENABLED|__ENABLED" .env
```

### Test Posting
```bash
# Start app
/home/bear2927/StockTradingSignals/scripts/start_app.sh

# Check logs for posting activity
tail -f /var/log/stock-trading-signals/app.log | grep -i "post\|social"
```

### Manual Test
```bash
# Test X posting
python -c "
from src.social.twitter_poster import TwitterPoster
from src.common.config import get_settings
settings = get_settings()
if settings.social.twitter.enabled:
    poster = TwitterPoster()
    print('✓ X/Twitter configured and ready')
else:
    print('✗ X/Twitter not enabled')
"

# Test Stocktwits posting
python -c "
from src.social.stocktwits_poster import StocktwitsPoster
from src.common.config import get_settings
settings = get_settings()
if settings.social.stocktwits.enabled:
    poster = StocktwitsPoster()
    print('✓ Stocktwits configured and ready')
else:
    print('✗ Stocktwits not enabled')
"

# Test Threads posting
python -c "
from src.social.threads_poster import ThreadsPoster
from src.common.config import get_settings
settings = get_settings()
if settings.social.threads.enabled:
    poster = ThreadsPoster()
    print('✓ Threads configured and ready')
else:
    print('✗ Threads not enabled')
"
```

---

## Posting Schedule

After setup, the application will automatically post during:

**Weekdays (Mon-Fri):**
- Every 15 minutes from 4 PM - 11 PM ET
- Every 15 minutes from 12 AM - 9 AM ET

**Weekends (Sat-Sun):**
- Every 30 minutes all day

To customize schedule, edit `config/config.yaml`:
```yaml
social:
  schedule_cron: "*/15 16-23,0-9 * * 1-5"  # Weekday times
  weekend_schedule_cron: "*/30 * * * 0,6"  # Weekend times
```

---

## Need Help?

Detailed setup instructions: `SOCIAL_MEDIA_SETUP.md`
Troubleshooting guide: `SOCIAL_MEDIA_SETUP.md` (Troubleshooting section)
Application logs: `/var/log/stock-trading-signals/app.log`

---

## Once Complete

1. ✅ All tokens configured in `.env`
2. ✅ Platforms enabled in config
3. ✅ Application running: `/home/bear2927/StockTradingSignals/scripts/start_app.sh`
4. ✅ Check logs for posting activity
5. ✅ Verify posts appear on your social media accounts

Done! Your trading signals will now be automatically posted to X, Stocktwits, and Threads! 🚀
