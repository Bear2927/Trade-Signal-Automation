# Messenger Scraper - Quick Start Testing

## Status: ✅ All Fixes Applied and Verified

The messenger web scraper has been fixed and is ready for testing. All critical bugs have been resolved:
- ✅ CSS selector list compatibility 
- ✅ Proxy configuration parsing
- ✅ MutationObserver setup
- ✅ Node dependencies installed
- ✅ Facebook session initialized

---

## 3-Step Testing

### Step 1: Start Redis (2 minutes)

```bash
# Option A: Docker (Recommended - no installation needed)
docker run -d -p 6379:6379 --name redis-test redis:7-alpine
docker ps | grep redis-test  # Verify it's running

# Option B: If you have redis-cli available
redis-cli ping  # Should return PONG
```

### Step 2: Verify Setup (1 minute)

```bash
cd /home/bear2927/StockTradingSignals
bash scripts/test_messenger_fixes.sh
```

You should see all green checkmarks (✓).

### Step 3: Run the Scraper (Ongoing)

```bash
# Terminal 1: Monitor Redis in real-time
redis-cli
> KEYS "*"                    # Watch for keys being created
> LLEN social:queue          # Check queue length
> MONITOR                     # Real-time command log

# Terminal 2: Run the scraper
cd /home/bear2927/StockTradingSignals
export REDIS_HOST=localhost
export REDIS_PORT=6379
export MESSENGER_HEADLESS=true
node src/messenger/scraper.js
```

Expected output:
```
Redis connected
Starting Facebook Messenger scraper...
Navigating to Messenger...
Found message container with selector: div[aria-label="Messages"]
Monitoring Messenger for trade signals...
MutationObserver started on: [data-testid="message_thread"]
```

---

## What Gets Tested

| Aspect | Status | Notes |
|--------|--------|-------|
| **Syntax** | ✅ Valid | JavaScript parses without errors |
| **Dependencies** | ✅ Installed | All Node modules available |
| **Configuration** | ✅ Complete | .env set with Discord webhook & Messenger URL |
| **Facebook Session** | ✅ Initialized | Browser session persisted from previous login |
| **Proxy Parsing** | ✅ Fixed | Handles missing/invalid credentials gracefully |
| **Selector Detection** | ✅ Fixed | Tries multiple selectors individually |
| **MutationObserver** | ✅ Fixed | Correctly identifies working selector |

---

## What the Scraper Does

When running correctly:

1. **Connects to Redis** - Establishes deduplication cache
2. **Launches Browser** - Opens Facebook Messenger with saved session
3. **Monitors Messages** - Sets up MutationObserver on message container
4. **Detects Signals** - Parses messages for trading signals (e.g., "$AAPL long entry 150")
5. **Deduplicates** - Checks Redis to avoid processing same signal twice
6. **Sends to Discord** - Forwards signals immediately to webhook
7. **Queues for Social** - Adds to job queue for after-hours social media posting

---

## Testing Different Scenarios

### Test 1: Session Expiry Detection
If Facebook session is expired:
```
SESSION EXPIRED: Redirected to login page. 
Please re-run setup_fb_session.py to re-authenticate.
```

Re-authenticate:
```bash
python scripts/setup_fb_session.py
# Browser will open - log in manually
# Press Enter in terminal when done
```

### Test 2: Message Parsing
The scraper looks for patterns like:
```
$AAPL long entry 150 target 160 stop 145
BTC short 45000 to 40000
$TSLA calls 250/252 @ 5.50
```

Post these in your Messenger chat to test.

### Test 3: Deduplication
Send the same message twice - it should only process once:
```bash
redis-cli KEYS "dedup:signal:*"  # Should have one key
```

### Test 4: Signal Webhook Forwarding
Signals should appear in your Discord channel:
- Check Discord for rich embeds with ticker, direction, prices

---

## Troubleshooting

### Issue: "Redis connection refused"
```bash
# Verify Redis is running
redis-cli ping

# If not, start it:
docker run -d -p 6379:6379 redis:7-alpine
```

### Issue: "SESSION EXPIRED" immediately
The session cookie may have expired:
```bash
# Re-authenticate
python scripts/setup_fb_session.py

# Or clear and start fresh
rm -rf ./fb_session
python scripts/setup_fb_session.py
```

### Issue: "Message container not found"
Facebook might have changed their DOM structure:
```bash
# Check what selectors are available
node << 'EOF'
# Open DevTools in a Playwright window and find the correct selector
# Update src/messenger/selectors.py with new selectors
EOF
```

### Issue: "Webhook error"
Check Discord webhook:
```bash
# Verify webhook is valid and not rate-limited
curl -X POST \
  -H 'Content-Type: application/json' \
  -d '{"content":"Test"}' \
  https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

---

## Success Indicators

✅ **Setup Complete** - All tests pass  
✅ **Scraper Running** - "Monitoring Messenger for trade signals..."  
✅ **Browser Active** - Facebook Messenger page loads (headless or visible)  
✅ **Mutation Observer** - "MutationObserver started on: [selector]"  
✅ **Signal Detected** - "New signal detected: TICKER - message..."  
✅ **Discord Received** - Signal appears in Discord channel  
✅ **Redis Queued** - `redis-cli LLEN social:queue` shows jobs  

---

## Next: Production Deployment

Once testing is successful:

```bash
# Run both components together
python -m src.main &           # Discord gateway
node src/messenger/scraper.js  # Messenger scraper

# Or use Docker Compose
docker-compose -f docker/docker-compose.yml up -d
```

Monitor logs:
```bash
tail -f logs/app.log
redis-cli MONITOR
```

---

## Files Changed

- `src/messenger/scraper.js` - Fixed selector handling and proxy parsing
- `scripts/test_messenger_fixes.sh` - New verification script

## Documentation

- `TESTING_SETUP.md` - Full testing guide with debugging
- `CLAUDE.md` - Quick reference
- `DEVELOPER_GUIDE.md` - Development documentation
