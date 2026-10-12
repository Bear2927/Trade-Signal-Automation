# How to Connect to Your Specific Messenger Chat

## Current Configuration

Your `.env` file is currently set to:
```
MESSENGER__TARGET_CHAT_URL=https://www.facebook.com/messages/t/1929174430523823
```

This connects to the chat with ID: **1929174430523823**

---

## Find Your Chat ID

### Method 1: From Facebook Messenger URL (Easiest)

1. **Open Facebook Messenger** in your browser
2. **Click on the group/chat** you want to scrape from
3. **Look at the URL bar** - it will show something like:
   ```
   https://www.facebook.com/messages/t/1929174430523823/
   ```
4. **Copy the ID** at the end: `1929174430523823`

### Method 2: From Mobile Messenger

If you're on mobile and the URL isn't visible:

1. Open the chat you want
2. Click the group name at the top
3. Look for any settings/info that shows the conversation ID
4. Or check your browser history for the chat URL

### Method 3: Extract from Current Session

Your saved Facebook session already has chat history:
```bash
# Look at your session files
ls -la fb_session/Default/

# The URLs visited are in history
# Look for conversations you've accessed
```

---

## How to Update Your Chat URL

### Option 1: Edit .env File Directly

```bash
# Open .env and find this line:
nano .env

# Change this line:
MESSENGER__TARGET_CHAT_URL=https://www.facebook.com/messages/t/1929174430523823

# To your chat (replace with YOUR_CHAT_ID):
MESSENGER__TARGET_CHAT_URL=https://www.facebook.com/messages/t/YOUR_CHAT_ID
```

Save with `Ctrl+X` then `Y` then `Enter`

### Option 2: Update via Environment Variable

```bash
# Set for current session only
export MESSENGER__TARGET_CHAT_URL="https://www.facebook.com/messages/t/YOUR_CHAT_ID"

# Then run scraper
node src/messenger/scraper.js
```

### Option 3: Update .env.test File

If you created a test environment:
```bash
# Edit the test config
nano .env.test

# Add or update:
MESSENGER_TARGET_CHAT_URL=https://www.facebook.com/messages/t/YOUR_CHAT_ID
```

---

## Verify You're Connected to the Right Chat

### Step 1: Start the Scraper

```bash
cd /home/bear2927/StockTradingSignals
export REDIS_HOST=localhost
export REDIS_PORT=6379
node src/messenger/scraper.js
```

### Step 2: Check the Logs

When the scraper starts, it should show:
```
Navigating to Messenger...
https://www.facebook.com/messages/t/YOUR_CHAT_ID
Found message container with selector: div[aria-label="Messages"]
```

### Step 3: Test with a Message

Post a test message in your Messenger chat:
```
$AAPL long entry 150 target 160
```

### Step 4: Verify Detection

Check if the scraper logs:
```
New signal detected: AAPL - $AAPL long entry 150...
Signal sent to Discord webhook
```

If you see this, you're connected to the right chat! ✅

---

## Different Chat Types

### Group Chat
```
https://www.facebook.com/messages/t/1929174430523823
```
URL format is the same - the ID points to the group

### Direct Message (1-on-1)
```
https://www.facebook.com/messages/t/USER_ID
```
Also uses the same format - can be a person's ID

### Facebook Page Message
```
https://www.facebook.com/messages/t/PAGE_ID
```
Same URL structure

---

## Troubleshooting

### Problem: "Session Expired" immediately after updating URL

**Cause:** The chat URL isn't accessible with your current session

**Solution:**
```bash
# Re-authenticate to ensure you have access
python scripts/setup_fb_session.py

# Your browser will open - navigate to the chat you want
# Make sure you can see messages in the group/chat
# Press Enter in the terminal when done
```

### Problem: Scraper runs but shows different chat

**Cause:** .env file wasn't updated, or environment variable wasn't set

**Solution:**
```bash
# Verify which URL is being used
grep MESSENGER__TARGET_CHAT_URL .env

# If it's wrong, update it:
nano .env

# Then restart the scraper
node src/messenger/scraper.js
```

### Problem: "Cannot access this conversation"

**Cause:** Your Facebook account doesn't have access to this chat

**Solution:**
1. Check if you're a member of the group/chat
2. Verify the chat ID is correct
3. Make sure you can access it in Facebook Messenger manually
4. Re-authenticate with `python scripts/setup_fb_session.py`

### Problem: Can't find the chat ID

**Cause:** URL doesn't show chat ID (sometimes happens on mobile)

**Solution:**
1. Open Messenger on desktop browser
2. Click the chat you want
3. Look at address bar for the ID
4. Or use the session check method above

---

## Quick Reference

| Task | Command |
|------|---------|
| View current chat | `grep MESSENGER.*TARGET .env` |
| Update chat | `nano .env` then find MESSENGER__TARGET_CHAT_URL |
| Test with new chat | `export MESSENGER_TARGET_CHAT_URL=https://www.facebook.com/messages/t/YOUR_ID && node src/messenger/scraper.js` |
| Re-authenticate | `python scripts/setup_fb_session.py` |
| Clear session | `rm -rf fb_session/` then re-authenticate |

---

## Examples

### Example 1: Scraping from a Group Chat

**Group Name:** Trading Signals  
**URL:** `https://www.facebook.com/messages/t/1929174430523823`  
**Chat ID:** `1929174430523823`

Update:
```bash
MESSENGER__TARGET_CHAT_URL=https://www.facebook.com/messages/t/1929174430523823
```

### Example 2: Scraping from a 1-on-1 Chat

**Contact Name:** John Trader  
**URL:** `https://www.facebook.com/messages/t/987654321`  
**Chat ID:** `987654321`

Update:
```bash
MESSENGER__TARGET_CHAT_URL=https://www.facebook.com/messages/t/987654321
```

### Example 3: Temporary Override via Environment

```bash
# Set for this session only
export MESSENGER_TARGET_CHAT_URL="https://www.facebook.com/messages/t/555666777"

# Run scraper with this chat
node src/messenger/scraper.js

# Chat URL goes back to .env value when you close terminal
```

---

## Advanced: Multiple Chats

The current scraper monitors ONE chat at a time. To monitor multiple chats:

**Option 1: Run multiple instances**
```bash
# Terminal 1: Monitor chat A
export MESSENGER_TARGET_CHAT_URL="https://www.facebook.com/messages/t/111"
node src/messenger/scraper.js

# Terminal 2: Monitor chat B  
export MESSENGER_TARGET_CHAT_URL="https://www.facebook.com/messages/t/222"
node src/messenger/scraper.js
```

**Option 2: Modify the scraper (advanced)**
```javascript
// In src/messenger/scraper.js, you could:
// 1. Read multiple URLs from env
// 2. Create multiple browser contexts
// 3. Run MutationObserver on all simultaneously
```

---

## Summary

**Current Setup:**
- ✅ Connected to: `1929174430523823`
- ✅ Session persisted: Yes
- ✅ Can access: Depends on your permissions

**To Change:**
1. Find your chat ID from the URL
2. Edit `.env` or set environment variable
3. Re-run the scraper
4. Test with a message

**Verify Success:**
- Scraper logs show "Found message container..."
- You post a test signal
- Scraper detects and sends to Discord

---

**Need help?** Check the logs when running the scraper - they'll tell you exactly what URL it's trying to access!
