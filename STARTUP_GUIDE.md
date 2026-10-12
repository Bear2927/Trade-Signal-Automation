# 🚀 Messenger Scraper - Startup Guide

## Ready to Launch!

Your setup is configured and ready to go. Follow these steps to start scraping and posting to Discord.

---

## 📋 Pre-Launch Checklist

Before starting, verify:
- ✅ Redis not running yet (we'll start it)
- ✅ Chat ID confirmed: `1929174430523823`
- ✅ Discord webhook configured
- ✅ Facebook session initialized
- ✅ You can access the Messenger chat

---

## 🚀 Startup Process (10 minutes)

### Phase 1: Start Redis (2 minutes)

**Open Terminal 1:**

```bash
cd /home/bear2927/StockTradingSignals

# Start Redis container
chmod +x scripts/start_redis.sh
scripts/start_redis.sh start
```

**Expected Output:**
```
Starting Redis container...
Creating new Redis container...
✓ Redis is running

Redis connection info:
  Host: localhost
  Port: 6379

Test connection:
  redis-cli ping
```

**Verify Redis is working:**
```bash
redis-cli ping
# Should return: PONG
```

---

### Phase 2: Verify Setup (2 minutes)

**Open Terminal 2:**

```bash
cd /home/bear2927/StockTradingSignals

# Run verification script
bash scripts/test_messenger_fixes.sh
```

**Expected Output:**
```
Test 1: Checking Node.js syntax...
✓ Syntax is valid

Test 2: Checking proxy parsing implementation...
✓ Proxy parsing validation added
✓ Proxy error message added

[... more green checkmarks ...]

✓ Facebook session directory exists
✓ Session appears to be initialized

Fix Verification Complete!
```

All should be green ✓ - If you see errors, let me know!

---

### Phase 3: Start the Scraper (Ongoing)

**Keep Terminal 2 open, start a new Terminal 3:**

```bash
cd /home/bear2927/StockTradingSignals

# Set environment variables
export REDIS_HOST=localhost
export REDIS_PORT=6379
export MESSENGER_HEADLESS=true

# Run the scraper
node src/messenger/scraper.js
```

**Expected Output (in first 5-10 seconds):**
```
Redis connected
Starting Facebook Messenger scraper...
Session path: ./fb_session
Headless: true
Navigating to Messenger...
[Browser loads - may take 5-10 seconds]
Found message container with selector: div[aria-label="Messages"]
Monitoring Messenger for trade signals...
Press Ctrl+C to stop
Using selector for MutationObserver: [data-testid="message_thread"]
MutationObserver started on: [data-testid="message_thread"]
```

**If you see these messages, you're connected! ✅**

---

## 🧪 Phase 4: Test It Works (3 minutes)

### Step 1: Keep Scraper Running

Leave Terminal 3 with the scraper running.

### Step 2: Post a Test Signal

**Open another browser window or tab to Facebook Messenger:**

```
Go to: https://www.facebook.com/messages/t/1929174430523823
(Or just open Messenger and click the chat)
```

**Post this test message in the chat:**
```
$AAPL long entry 150 target 160 stop 145
```

### Step 3: Watch the Scraper

**In Terminal 3 (scraper), you should see:**
```
New signal detected: AAPL - $AAPL long entry 150 target 160 stop 145
Signal sent to Discord webhook
```

### Step 4: Check Discord

**Go to your Discord channel:**
- You should see a rich embed message with:
  - Title: "📈 Trade Signal from Facebook Messenger"
  - Description: The full message text
  - Fields: Source and Author
  - Color: Green

**If you see the message in Discord, it works! 🎉**

---

## 📊 Phase 5: Monitor Real-Time Activity (Optional)

**Open Terminal 4 to watch Redis in real-time:**

```bash
redis-cli MONITOR
```

**You'll see commands like:**
```
SET dedup:signal:abc123def456... 1 EX 30
LPUSH social:queue {"signal":{"ticker":"AAPL",...}}
```

---

## 📈 Phase 6: Keep Running

The scraper will now continuously:

1. **Monitor messages** in your Messenger chat
2. **Detect signals** (messages with $TICKER and trading info)
3. **Deduplicate** (skip duplicate signals within 30 seconds)
4. **Send to Discord** immediately via webhook
5. **Queue for social media** (posted after market hours)

**The scraper will run indefinitely until you stop it.**

---

## 📝 Testing Checklist

- [ ] Redis started successfully
- [ ] Verification script all green ✓
- [ ] Scraper running without errors
- [ ] Message container found
- [ ] MutationObserver started
- [ ] Posted test signal: `$AAPL long entry 150...`
- [ ] Signal appeared in Discord
- [ ] Signal detected in scraper logs

---

## 🛑 If Something Goes Wrong

### Scraper shows "SESSION EXPIRED"

```bash
# In Terminal 3, press Ctrl+C to stop

# Re-authenticate
python scripts/setup_fb_session.py

# Browser will open - complete login
# Press Enter when done

# Restart scraper
node src/messenger/scraper.js
```

### Scraper runs but no "Message container found"

```bash
# Stop scraper (Ctrl+C)

# Clear session and re-authenticate
rm -rf fb_session/
python scripts/setup_fb_session.py

# Restart scraper
node src/messenger/scraper.js
```

### Discord message didn't appear

1. **Check webhook URL** is correct in `.env`
2. **Verify Discord channel** permissions
3. **Check Discord webhook** still exists and is enabled
4. **Check scraper logs** for "Signal sent to Discord webhook" message

### Redis connection refused

```bash
# In Terminal 1, restart Redis
scripts/start_redis.sh restart

# Or stop and start fresh
scripts/start_redis.sh stop
scripts/start_redis.sh start
```

---

## 💡 Tips for Success

1. **Keep all terminals open** - They show different info
2. **Monitor Redis** - `redis-cli MONITOR` shows all activity
3. **Check Discord webhook** - Verify channel has webhook enabled
4. **Post clear signals** - Use format: `$TICKER direction entry target stop`
5. **Don't kill terminals** - Let scraper run continuously

---

## 📊 Real-Time Monitoring Commands

**Check queue size:**
```bash
redis-cli LLEN social:queue
```

**View queued signals:**
```bash
redis-cli LRANGE social:queue 0 -1
```

**Check dedup keys:**
```bash
redis-cli KEYS "dedup:signal:*"
```

**Clear all Redis data:**
```bash
redis-cli FLUSHALL
```

---

## 🎯 Next Steps After Testing

### If everything works:
1. Leave the scraper running
2. Post real trading signals in your Messenger chat
3. Monitor Discord for signals
4. Check Redis queue for social media jobs

### To stop everything:
```bash
# In scraper terminal: Ctrl+C
# In Redis terminal: Ctrl+C
# Stop Redis container:
scripts/start_redis.sh stop
```

---

## 📚 Reference

| Component | Status | Terminal |
|-----------|--------|----------|
| **Redis** | Running | Terminal 1 |
| **Verification** | Passed ✓ | Terminal 2 |
| **Scraper** | Running | Terminal 3 |
| **Monitor** | Optional | Terminal 4 |

---

## 🎉 Success Indicators

✅ **Setup Complete** when you see:
- Redis: "✓ Redis is running"
- Verify: All green checkmarks ✓
- Scraper: "Monitoring Messenger for trade signals..."
- Discord: Test signal appears as rich embed

✅ **Working Correctly** when:
- You post signal in Messenger
- Scraper shows "New signal detected"
- Signal appears in Discord within 2 seconds
- Redis shows dedup key and queue job

---

**You're ready! Follow the startup process above and you'll be up and running in 10 minutes.** 🚀
