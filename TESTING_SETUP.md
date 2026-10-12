# Messenger Scraper Testing Setup Guide

## Quick Start (5 minutes)

### 1. Environment Setup

```bash
# Navigate to project
cd /home/bear2927/StockTradingSignals

# Activate Python venv
source .venv/bin/activate

# Create a local testing .env file
cat > .env.test << 'EOF'
# For local testing with localhost Redis
REDIS_HOST=localhost
REDIS_PORT=6379
MESSENGER_TARGET_CHAT_URL=https://www.facebook.com/messages/t/1929174430523823
MESSENGER_SESSION_PATH=./fb_session
MESSENGER_HEADLESS=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/1558359632743759872/SfAaCmqa6JkfS7axYOmnJtZQLUw0parj4DAVyBnCQ80RFMaDSeaywFWPlogU41HzgOT0
DEDUP_TTL=30
EOF
```

### 2. Check Prerequisites

```bash
# Check Node.js
which node npm  # Should show Node.js paths

# Check Python 
python --version  # Should be 3.11+

# Check Redis status
redis-cli ping  # Should return PONG (or give connection error if not running)
```

### 3. Start Redis (Required)

**Option A: Docker (Recommended)**
```bash
# Start Redis container
docker run -d -p 6379:6379 --name redis-test redis:7-alpine
docker logs redis-test

# To stop later:
# docker stop redis-test && docker rm redis-test
```

**Option B: System Redis**
```bash
# If Redis is installed system-wide
redis-server &
```

**Option C: Manual Installation (if needed)**
```bash
# Install Redis (requires sudo, so you'd need to do this yourself)
apt-get install redis-server
redis-server &
```

### 4. Install Playwright Browsers

```bash
# Install Chromium and dependencies for Playwright
npx playwright install --with-deps chromium
```

### 5. Verify Facebook Session

```bash
# Check if session exists
ls -la ./fb_session/

# If session doesn't exist or is expired, re-authenticate:
python scripts/setup_fb_session.py
# This will open a browser where you can manually log into Facebook Messenger
```

---

## Running the Scraper

### Basic Test Run

```bash
# Load the test environment
export $(cat .env.test | xargs)

# Test 1: Quick syntax check
node -c src/messenger/scraper.js
echo "✓ Syntax check passed"

# Test 2: Run scraper in headless mode (10 seconds, then Ctrl+C)
timeout 10 node src/messenger/scraper.js || true
```

### Full Test with Monitoring

**Terminal 1: Start Redis**
```bash
redis-cli FLUSHALL  # Clear any old data
redis-cli MONITOR   # Watch Redis commands in real-time
```

**Terminal 2: Start the scraper**
```bash
cd /home/bear2927/StockTradingSignals
source .venv/bin/activate
export $(cat .env.test | xargs)
node src/messenger/scraper.js
```

**Terminal 3: Monitor signals (in another window)**
```bash
# Watch for deduplication keys being set
redis-cli KEYS "dedup:signal:*"

# Watch for social queue messages
redis-cli LRANGE "social:queue" 0 -1 | head -20

# Check specific signal hash
redis-cli GET "dedup:signal:abc123..."
```

---

## Testing Checklist

### ✓ Connection Tests
- [ ] Redis connects successfully
- [ ] Facebook session is valid (not redirected to login)
- [ ] Playwright browser launches without errors
- [ ] Message container selector is found

### ✓ Message Detection
- [ ] Scraper detects "Message container with selector" in logs
- [ ] MutationObserver starts successfully
- [ ] New messages trigger signal detection

### ✓ Signal Processing
- [ ] Signals are deduplicated (check Redis)
- [ ] Webhook sends to Discord (check webhook logs)
- [ ] Social queue receives jobs (check Redis LRANGE)

### ✓ Error Handling
- [ ] Graceful shutdown on Ctrl+C
- [ ] Proxy parsing shows appropriate messages
- [ ] Session expiry is detected and reported

---

## Debugging Commands

### View Scraper Logs
```bash
# Run with increased visibility
node src/messenger/scraper.js 2>&1 | tee scraper.log

# Or check in Docker if running in container
docker logs stocksignals-messenger -f
```

### Check Redis State
```bash
# Connect to Redis CLI
redis-cli

# Inside redis-cli:
> KEYS "*"                           # All keys
> KEYS "dedup:signal:*"              # Dedup keys
> LLEN "social:queue"                # Queue length
> LRANGE "social:queue" 0 -1         # View queue items
> TTL "dedup:signal:xxxx"            # Check key expiration
> FLUSHALL                           # Clear everything
```

### Monitor Network
```bash
# Watch network requests
tcpdump -i any 'tcp port 6379'  # Monitor Redis connections
```

### Test Signal Parsing
```bash
# Test directly in Node
node << 'EOF'
const parseSignal = (text) => {
  const signal = { rawText: text };
  const tickerMatch = text.match(/\$?([A-Z]{1,5})\b/);
  const longKeywords = ['long', 'buy', 'bullish'];
  for (const kw of longKeywords) {
    if (text.toLowerCase().includes(kw)) { 
      signal.direction = 'LONG'; 
      break; 
    }
  }
  if (tickerMatch) signal.ticker = tickerMatch[1];
  return signal;
};

console.log(parseSignal("$AAPL long entry 150 target 160"));
// Output: { rawText: '...', ticker: 'AAPL', direction: 'LONG' }
EOF
```

---

## Expected Output

When running successfully, you should see:

```
Redis connected
Starting Facebook Messenger scraper...
Session path: ./fb_session
Headless: true
Navigating to Messenger...
Found message container with selector: div[aria-label="Messages"]
Proxy configured: (none)
Monitoring Messenger for trade signals...
Press Ctrl+C to stop
Using selector for MutationObserver: [data-testid="message_thread"]
MutationObserver started on: [data-testid="message_thread"]
New signal detected: AAPL - $AAPL long entry 150...
Signal sent to Discord webhook
```

---

## Troubleshooting

### "Redis connection refused"
```bash
# Start Redis:
docker run -d -p 6379:6379 redis:7-alpine

# Or check if it's already running:
ps aux | grep redis
```

### "SESSION EXPIRED: Redirected to login"
```bash
# Re-authenticate:
python scripts/setup_fb_session.py
# Follow browser prompts to log in
```

### "Message container not found"
- Facebook UI may have changed
- Try updating selectors in `src/messenger/selectors.py`
- Check browser DevTools to find current selectors

### "MutationObserver started but no signals detected"
- Messages may not match parsing patterns
- Test with a message like: "$AAPL long entry 150 target 160"
- Check if selector is correctly monitoring the message area

### Node/npm not found
```bash
# Check PATH
echo $PATH

# May need to install Node.js first (requires sudo)
# You can download portable Node.js instead:
# https://nodejs.org/en/download/
```

---

## Next Steps

After successful testing:

1. **Run the full application:**
   ```bash
   python -m src.main &        # Discord gateway (background)
   node src/messenger/scraper.js  # Messenger scraper (foreground)
   ```

2. **Monitor in production:**
   ```bash
   tail -f logs/app.log
   redis-cli MONITOR
   ```

3. **Deploy with Docker:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

---

## Support

Check these files for more info:
- `CLAUDE.md` - Quick reference
- `DEVELOPER_GUIDE.md` - Full development guide
- `API.md` - API reference
