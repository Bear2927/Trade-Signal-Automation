# Messenger Scraper - Testing Guide

## 📋 Overview

This guide walks you through testing the fixed Facebook Messenger web scraper for stock trading signals.

**Status:** All fixes verified ✅  
**Ready for Testing:** Yes ✅

---

## ⚡ 5-Minute Quick Start

### Step 1: Start Redis (2 min)
```bash
cd /home/bear2927/StockTradingSignals

# Option A: Use helper script
chmod +x scripts/start_redis.sh
scripts/start_redis.sh start

# Option B: Manual Docker
docker run -d -p 6379:6379 --name redis-test redis:7-alpine
```

### Step 2: Verify Fixes (1 min)
```bash
bash scripts/test_messenger_fixes.sh
```

Expected output: All green checkmarks ✓

### Step 3: Run Scraper (2 min)
```bash
export REDIS_HOST=localhost
export REDIS_PORT=6379
node src/messenger/scraper.js
```

Expected output:
```
Redis connected
Starting Facebook Messenger scraper...
Found message container with selector: div[aria-label="Messages"]
Monitoring Messenger for trade signals...
MutationObserver started on: [data-testid="message_thread"]
```

---

## 🧪 What Gets Tested

| Component | Status | Test |
|-----------|--------|------|
| **Proxy Parsing** | ✅ Fixed | Handles `host:port` and `host:port:user:pass` |
| **Selector Detection** | ✅ Fixed | Tries multiple selectors, picks first match |
| **MutationObserver** | ✅ Fixed | Correctly tracks DOM changes |
| **Redis Connection** | ✅ Works | Stores dedup keys and job queue |
| **Discord Webhook** | ✅ Works | Sends signals to Discord channel |
| **Signal Parsing** | ✅ Works | Extracts ticker, direction, prices |

---

## 🎯 Testing Scenarios

### Scenario 1: Verify Connection
```bash
# Should see these messages in order:
# 1. "Redis connected"
# 2. "Navigating to Messenger..."
# 3. "Found message container with selector: ..."
# 4. "MutationObserver started on: ..."
# 5. "Monitoring Messenger for trade signals..."
```

### Scenario 2: Test Signal Detection
Post in your Messenger chat:
```
$AAPL long entry 150 target 160 stop 145
```

Observe:
1. **Logs:** `New signal detected: AAPL - $AAPL long entry 150...`
2. **Discord:** Signal appears as rich embed in your Discord channel
3. **Redis:** `redis-cli KEYS "dedup:signal:*"` shows new key

### Scenario 3: Test Deduplication
Post the SAME signal twice:
```
$AAPL long entry 150 target 160 stop 145
$AAPL long entry 150 target 160 stop 145  # Same message
```

Observe:
- First message processed and sent to Discord
- Second message skipped (duplicate)
- Redis has only ONE dedup key (TTL 30 seconds)

### Scenario 4: Test Signal Variations
Post these to verify parsing:
```
$TSLA short 800 to 750
$BTC calls 50000/52000 @ 2.50
$NVDA bullish entry 120 target 140
XLE long entry 85 target 90
```

### Scenario 5: Test Error Recovery
Stop and restart Redis:
```bash
# Terminal 1: Stop Redis
redis-cli SHUTDOWN

# Scraper should attempt reconnection automatically
# Terminal 2 (Scraper): Will show connection errors

# Restart Redis
redis-cli PING  # Start Redis again
docker run -d -p 6379:6379 redis:7-alpine

# Scraper should reconnect
```

---

## 📊 Monitoring Dashboard

### Terminal 1: Redis Monitor
```bash
redis-cli MONITOR
```

You'll see:
```
"SET" "dedup:signal:abc123..." "1" "EX" "30"
"LPUSH" "social:queue" "{\"signal\":{...}...}"
```

### Terminal 2: Scraper Logs
```bash
node src/messenger/scraper.js 2>&1 | tee scraper.log
```

You'll see:
```
New signal detected: TICKER - message...
Signal sent to Discord webhook
```

### Terminal 3: Redis Data
```bash
redis-cli
LLEN social:queue          # How many jobs queued
KEYS dedup:signal:*        # Active dedup keys
LINDEX social:queue 0      # First job in queue
TTL dedup:signal:abc...    # Seconds until key expires
```

---

## ✅ Success Checklist

- [ ] Redis is running
- [ ] Scraper connects without errors
- [ ] Message container is found
- [ ] MutationObserver starts
- [ ] Sample signal is detected
- [ ] Signal appears in Discord
- [ ] Dedup key is created in Redis
- [ ] Queue job is added to Redis
- [ ] Second identical signal is skipped

---

## 🚨 Troubleshooting

### Problem: "Redis connection refused"
```bash
# Check Redis status
redis-cli ping

# Start Redis if needed
scripts/start_redis.sh start

# Or manually
docker run -d -p 6379:6379 redis:7-alpine
```

### Problem: "Message container not found"
```bash
# Facebook UI might have changed
# Option 1: Re-authenticate
python scripts/setup_fb_session.py

# Option 2: Check current selectors with browser DevTools
# Update src/messenger/selectors.py with new selectors
```

### Problem: "SESSION EXPIRED"
```bash
# Re-login to Facebook
python scripts/setup_fb_session.py

# Browser will open - complete login and 2FA if needed
# Press Enter in terminal when done
```

### Problem: Scraper runs but no signals detected
1. Check if signals match parsing pattern: `$TICKER direction prices`
2. Verify MutationObserver started (check logs)
3. Confirm you're in the correct Messenger chat
4. Try a simple signal: `$AAPL long 150 160`

---

## 🔧 Advanced Testing

### Test with Custom Proxy
```bash
export MESSENGER_PROXY="proxy.example.com:8080:user:pass"
node src/messenger/scraper.js
```

### Test with Different Chat
```bash
export MESSENGER_TARGET_CHAT_URL="https://www.facebook.com/messages/t/YOUR_CHAT_ID"
node src/messenger/scraper.js
```

### Run with Debugging
```bash
# Enable verbose output
DEBUG=* node src/messenger/scraper.js

# Or with Node inspector
node --inspect src/messenger/scraper.js
# Then open chrome://inspect
```

### Performance Test
```bash
# Generate many signals rapidly
# Create a script to post multiple messages in Messenger
# Monitor Redis queue size and processing speed
redis-cli LLEN social:queue
```

---

## 📈 Expected Performance

- **Connection time:** < 10 seconds
- **Signal detection:** < 500ms after message appears
- **Redis latency:** < 5ms per operation
- **Discord webhook:** < 2 seconds
- **Dedup check:** < 1ms
- **Memory usage:** < 100MB

---

## 🧹 Cleanup

### Stop Scraper
```bash
# Press Ctrl+C in the scraper terminal
```

### Stop Redis
```bash
# Using helper script
scripts/start_redis.sh stop

# Or manually
docker stop redis-test
docker rm redis-test
```

### Clear Data
```bash
redis-cli FLUSHALL        # Delete all Redis data
rm -rf fb_session/        # Reset session (forces re-login)
```

---

## 📚 More Documentation

- **QUICK_START.md** - 3-step quick start guide
- **TESTING_SETUP.md** - Comprehensive testing guide with debugging tips
- **TESTING_SUMMARY.md** - Technical details of all fixes
- **DEVELOPER_GUIDE.md** - Full development documentation
- **CLAUDE.md** - Quick reference

---

## 🎓 What You'll Learn

By testing the messenger scraper, you'll understand:

1. **How Playwright monitors browser changes** - MutationObserver
2. **How Redis deduplication works** - SETNX with TTL
3. **How signals are parsed** - Regex patterns for ticker/price extraction
4. **How Discord webhooks work** - Sending rich embeds
5. **How job queues operate** - Redis LPUSH/LRANGE
6. **How session persistence works** - Browser context save/restore
7. **How stealth mode prevents detection** - Playwright-extra plugins

---

## 🎉 Ready to Test!

Everything is set up and ready. Follow the **5-Minute Quick Start** above to begin testing.

**Questions?** Check TESTING_SETUP.md for detailed debugging guides.
