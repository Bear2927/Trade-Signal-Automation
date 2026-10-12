# Social Media Setup Guide

This guide walks you through setting up posting to Stocktwits, X (Twitter), and Threads.

## 1. X (Twitter) Setup

### Step 1: Create Developer Account
1. Go to https://developer.twitter.com/
2. Sign in with your X account (create one if needed)
3. Click "Create an app" → Choose a name like "StockTradingSignals"
4. Select "Free" plan

### Step 2: Get API Keys
1. Go to your app's **Settings** tab
2. Under "Keys and tokens", generate:
   - **API Key** (api_key in config)
   - **API Secret Key** (api_secret in config)

### Step 3: Enable OAuth 2.0
1. In Settings, scroll to "User authentication settings"
2. Click "Edit" and enable OAuth 2.0
3. Under "Type of App", select: **Web App, Automated App or Bot**
4. Set **Callback URLs** to: `http://localhost:8000/callback`
5. Under **App Permissions**, select:
   - ✅ Read and write tweets
   - ✅ Read user profile
6. Save settings

### Step 4: Get Access Tokens
1. Go to **Keys and Tokens** tab
2. Generate a new **Bearer Token** (bearer_token in config)
3. For OAuth 2.0 tokens, you need to authenticate:
   ```bash
   python scripts/setup_social_auth.py
   ```
   This will guide you through the X OAuth flow to get:
   - access_token
   - refresh_token

### Step 5: Update Configuration
```bash
# Edit .env or config/config.yaml
SOCIAL__TWITTER__ENABLED=true
SOCIAL__TWITTER__API_KEY=your_api_key
SOCIAL__TWITTER__API_SECRET=your_api_secret
SOCIAL__TWITTER__BEARER_TOKEN=your_bearer_token
SOCIAL__TWITTER__ACCESS_TOKEN=your_access_token
SOCIAL__TWITTER__REFRESH_TOKEN=your_refresh_token
```

---

## 2. Stocktwits Setup

### Step 1: Create App
1. Go to https://stocktwits.com/developers
2. Sign in with your Stocktwits account
3. Click "Create App"
4. Fill in app details:
   - Name: "StockTradingSignals"
   - Description: "Automated trading signal posting"
   - Redirect URI: `http://localhost:8000/callback`

### Step 2: Get Credentials
After creating the app, you'll get:
- **Client ID** (client_id in config)
- **Client Secret** (client_secret in config)

### Step 3: Get Access Token
Run the auth script to get your access token:
```bash
python scripts/setup_social_auth.py
```

Or manually authenticate at:
```
https://api.stocktwits.com/oauth/authorize?client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8000/callback&response_type=code
```

Then exchange the code for an access token.

### Step 4: Update Configuration
```bash
SOCIAL__STOCKTWITS__ENABLED=true
SOCIAL__STOCKTWITS__CLIENT_ID=your_client_id
SOCIAL__STOCKTWITS__CLIENT_SECRET=your_client_secret
SOCIAL__STOCKTWITS__ACCESS_TOKEN=your_access_token
```

---

## 3. Threads Setup

### Step 1: Create Meta Business Account
1. Go to https://business.facebook.com
2. Create a Business Account (if you don't have one)
3. Add your Instagram account as a Page

### Step 2: Create App
1. Go to https://developers.facebook.com/apps
2. Click "Create App"
3. Choose **Business** as the app type
4. Fill in details and create

### Step 3: Get Credentials
1. Go to your app settings
2. Get your **App ID** (app_id in config)
3. Go to Settings → Basic to get **App Secret** (app_secret in config)
4. Copy the **App ID** and **App Secret**

### Step 4: Get Access Token
1. Go to **Tools** → **Graph API Explorer**
2. Select your app from the dropdown
3. Get a User Access Token with these permissions:
   - `threads_basic_access`
   - `threads_content_publish`
   - `user_posts`

Or run the auth script:
```bash
python scripts/setup_social_auth.py
```

### Step 5: Update Configuration
```bash
SOCIAL__THREADS__ENABLED=true
SOCIAL__THREADS__APP_ID=your_app_id
SOCIAL__THREADS__APP_SECRET=your_app_secret
SOCIAL__THREADS__USER_ACCESS_TOKEN=your_access_token
```

---

## Configuration Methods

### Method 1: Update .env (Recommended)
Edit `/home/bear2927/StockTradingSignals/.env` and add/update:

```bash
# X (Twitter)
SOCIAL__TWITTER__ENABLED=true
SOCIAL__TWITTER__API_KEY=your_api_key
SOCIAL__TWITTER__API_SECRET=your_api_secret
SOCIAL__TWITTER__BEARER_TOKEN=your_bearer_token
SOCIAL__TWITTER__ACCESS_TOKEN=your_access_token
SOCIAL__TWITTER__REFRESH_TOKEN=your_refresh_token

# Stocktwits
SOCIAL__STOCKTWITS__ENABLED=true
SOCIAL__STOCKTWITS__CLIENT_ID=your_client_id
SOCIAL__STOCKTWITS__CLIENT_SECRET=your_client_secret
SOCIAL__STOCKTWITS__ACCESS_TOKEN=your_access_token

# Threads
SOCIAL__THREADS__ENABLED=true
SOCIAL__THREADS__APP_ID=your_app_id
SOCIAL__THREADS__APP_SECRET=your_app_secret
SOCIAL__THREADS__USER_ACCESS_TOKEN=your_access_token
```

### Method 2: Update config.yaml
Edit `config/config.yaml`:

```yaml
social:
  twitter:
    enabled: true
    api_key: "your_api_key"
    api_secret: "your_api_secret"
    bearer_token: "your_bearer_token"
    access_token: "your_access_token"
    refresh_token: "your_refresh_token"
    max_chars: 280

  stocktwits:
    enabled: true
    client_id: "your_client_id"
    client_secret: "your_client_secret"
    access_token: "your_access_token"
    max_chars: 2000

  threads:
    enabled: true
    app_id: "your_app_id"
    app_secret: "your_app_secret"
    user_access_token: "your_access_token"
    max_chars: 500
```

---

## Automated OAuth Setup

Run this script to interactively get OAuth tokens:

```bash
python scripts/setup_social_auth.py
```

This will prompt you to authenticate with each service and save the tokens.

---

## Testing Setup

### Test Social Media Posting
```bash
# Run the test script
python scripts/test_social_posting.py

# Or manually test one platform
python -c "
from src.social.twitter_poster import TwitterPoster
poster = TwitterPoster()
result = poster.post('Test message from StockTradingSignals #trading')
print(f'Posted: {result}')
"
```

### View Posting Schedule
The application posts during these times:
- **Weekdays**: Every 15 minutes from 4 PM - 11 PM ET, then 12 AM - 9 AM ET
- **Weekends**: Every 30 minutes all day

Edit `config/config.yaml` to customize posting schedule:
```yaml
social:
  schedule_cron: "*/15 16-23,0-9 * * 1-5"  # Weekdays
  weekend_schedule_cron: "*/30 * * * 0,6"  # Weekends
```

---

## Troubleshooting

### "Access token expired" error
- **X/Twitter**: Tokens expire, refresh with refresh_token
- **Stocktwits**: Get a new access token
- **Threads**: Get a new user access token from Graph API Explorer

### "Invalid credentials" error
- Double-check you copied the credentials correctly
- Make sure spaces or special characters weren't accidentally included
- Verify the credentials are still valid on the platform

### Posts not appearing
1. Check app is running: `ps aux | grep python`
2. Check logs: `tail -f /var/log/stock-trading-signals/app.log`
3. Verify posting is enabled in config
4. Check if posting window is active (see schedule above)

### Rate limit errors
The app respects platform rate limits. If you hit limits:
- Stocktwits: Wait 15 minutes before next post
- X/Twitter: Wait as specified by API
- Threads: Wait as specified by API

---

## Character Limits

Each platform has different character limits. The app auto-truncates:

| Platform | Limit | Setting |
|----------|-------|---------|
| X (Twitter) | 280 chars | `max_chars: 280` |
| Stocktwits | 2000 chars | `max_chars: 2000` |
| Threads | 500 chars | `max_chars: 500` |

To change limits, edit `config/config.yaml`:
```yaml
twitter:
  max_chars: 280
```

---

## Security Notes

⚠️ **Never commit credentials to git!**

- Keep `.env` and `.gitignore` configured properly
- Use environment variables for production
- Rotate tokens regularly
- Use least-privilege API scopes

---

## Next Steps

1. Get API credentials for each platform
2. Run `python scripts/setup_social_auth.py` or manually update `.env`
3. Test with `python scripts/test_social_posting.py`
4. Restart the application
5. Monitor logs for posting activity
