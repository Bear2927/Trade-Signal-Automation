# StockTradingSignals - Quick Reference

## 🚀 Quick Commands

```bash
# Development
python -m src.main                    # Main app (Discord + Scheduler)
node src/messenger/scraper.js         # Messenger scraper
python scripts/validate_config.py     # Validate config

# Docker
docker-compose -f docker/docker-compose.yml up -d --build
docker-compose -f docker/docker-compose.yml logs -f
docker-compose -f docker/docker-compose.yml down

# Testing
pytest tests/ -v
pytest tests/test_formatter.py -v

# Setup
python scripts/setup_fb_session.py    # Facebook login
python scripts/setup_social_auth.py   # Social OAuth
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `config/config.yaml` | Main configuration |
| `src/main.py` | Entry point |
| `src/discord/gateway.py` | Discord WebSocket listener |
| `src/messenger/scraper.js` | Playwright Messenger scraper |
| `src/social/scheduler.py` | After-hours scheduler |
| `src/social/queue.py` | Redis job queue |
| `src/common/formatter.py` | Signal parsing/formatting |
| `src/common/deduplicator.py` | Deduplication (SETNX) |
| `src/common/webhook.py` | Discord webhook sender |

---

## ⚙️ Config Essentials

```yaml
# Required
discord:
  user_token: "YOUR_TOKEN"
  target_channel_ids: ["123", "456"]
  premium_webhook_url: "https://discord.com/api/webhooks/..."

messenger:
  target_chat_url: "https://www.facebook.com/messages/t/CHAT_ID"
  session_path: "./fb_session"

# Optional (at least one for social posting)
social:
  twitter:
    enabled: true
    api_key: ""
    api_secret: ""
    access_token: ""
    bearer_token: ""
```

---

## 🔑 Credential Sources

| Platform | Where to Get |
|----------|--------------|
| Discord Token | Browser DevTools → Network → WebSocket → Authorization header |
| FB Session | `python scripts/setup_fb_session.py` |
| Twitter | developer.twitter.com → Project → Keys |
| Stocktwits | api.stocktwits.com/developers/apps |
| Threads | developers.facebook.com → Instagram Graph API |
| Reddit | reddit.com/prefs/apps → Create script app |
| Telegram | @BotFather → /newbot |
| LinkedIn | linkedin.com/developers → Create App |
| SendGrid | app.sendgrid.com/settings/api_keys |

---

## 🏗️ Architecture Flow

```
Discord (WS) ──┐
               ├──→ Redis SETNX (30s TTL) ──→ Discord Webhook (IMMEDIATE)
Messenger ─────┘                                    │
                                                    ▼
                                           Redis Queue + Scheduler
                                                    │
                    ┌───────────────────────────────┼───────────────┐
                    ▼                               ▼               ▼
               Twitter (X)                      Stocktwits       Threads
               (Tweepy)                         (REST)           (Graph API)
                    │                               │               │
                    └───────────────────────────────┼───────────────┘
                                                    ▼
                                            Reddit, Telegram,
                                            LinkedIn, Email
```

---

## 📊 Signal Format

```python
TradeSignal(
    raw_text="AAPL long entry 150 target 160 stop 145",
    ticker="AAPL",
    direction="LONG",          # LONG/SHORT
    entry="150",
    target="160",
    stop_loss="145",
    expiry="03/15/24",         # Options
    strike="450",
    option_type="CALL",        # CALL/PUT
    source="Discord#123456",
    author="trader123",
    channel="123456"
)
```

---

## 🎯 Platform Formatting

| Platform | Format | Limit |
|----------|--------|-------|
| Discord | Rich embed | 4096 desc |
| Twitter | Compact | 280 chars |
| Stocktwits | Cashtags + #Bullish | 2000 chars |
| Threads | Visual + emojis | 500 chars |
| Telegram | Markdown | 4096 chars |
| Reddit | Title + body | 40000 chars |
| Email | HTML | Unlimited |

---

## ⏰ Posting Schedule

| Period | Cron | Frequency |
|--------|------|-----------|
| Weekdays | `*/15 16-23,0-9 * * 1-5` | Every 15 min (4PM-9:30AM ET) |
| Weekends | `*/30 * * * 0,6` | Every 30 min |

**Timezone**: US/Eastern (handles DST)

---

## 🔴 Rate Limits (Token Bucket)

| Platform | Rate/sec | Burst |
|----------|----------|-------|
| Twitter | 0.33 | 50 |
| Stocktwits | 0.028 | 10 |
| Threads | 0.055 | 20 |
| Reddit | 1.0 | 10 |
| Telegram | 30 | 30 |

---

## 🐛 Debug Commands

```bash
# Redis inspection
redis-cli KEYS "dedup:signal:*"
redis-cli ZRANGE social:queue 0 -1 WITHSCORES
redis-cli LRANGE social:dead_letter 0 -1

# Queue stats
python -c "
import asyncio
from src.social.queue import get_social_queue
async def main():
    q = await get_social_queue()
    print(await q.get_queue_stats())
asyncio.run(main())
"

# Test signal parsing
python -c "
from src.common.formatter import SignalFormatter
s = SignalFormatter.parse('AAPL long entry 150 target 160')
print(s)
"

# Health check
curl http://localhost:8080/health
curl http://localhost:9090/metrics
```

---

## 📝 Common Patterns

### Parse Signal
```python
from src.common.formatter import SignalFormatter
signal = SignalFormatter.parse(text, source="Discord#123", author="user")
```

### Send Webhook
```python
from src.common.webhook import get_webhook_sender
webhook = await get_webhook_sender()
await webhook.send_signal(signal.raw_text, "Discord#123", "author")
```

### Queue for Social
```python
from src.social.queue import get_social_queue
queue = await get_social_queue()
await queue.enqueue(signal.__dict__, "discord", time.time(), ["twitter"])
```

### Deduplication
```python
from src.common.deduplicator import get_deduplicator
dedup = get_deduplicator()
if not await dedup.is_duplicate(content, "discord:123"):
    # New signal
    pass
```

### Format for Platform
```python
from src.social.formatter import format_for_platform
tweet = format_for_platform(signal, 'twitter')
embed = format_for_platform(signal, 'discord')  # Returns dict
```

---

## 🚨 Common Issues

| Issue | Solution |
|-------|----------|
| Discord 401/4004 | Token expired → Re-extract from browser |
| FB session expired | Run `python scripts/setup_fb_session.py` |
| Rate limited (429) | Check rate limiter config, reduce frequency |
| No signals detected | Check channel IDs, parser confidence threshold |
| Scheduler not posting | Verify timezone (US/Eastern), cron syntax |
| Redis connection failed | Check host/port/password, Docker network |

---

## 🔗 Key URLs

| Service | URL |
|---------|-----|
| Health | `http://localhost:8080/health` |
| Metrics | `http://localhost:9090/metrics` |
| Discord Gateway | `wss://gateway.discord.gg/?v=9&encoding=json` |
| Discord API | `https://discord.com/api/v9` |
| Twitter API v2 | `https://api.twitter.com/2` |
| Stocktwits API | `https://api.stocktwits.com/api/v2` |
| Threads API | `https://graph.threads.net/v1.0` |

---

## 📦 Docker Services

```yaml
redis:      # Port 6379, persistence, healthcheck
app:        # Main Python (Discord + Scheduler)
scheduler:  # Separate scheduler (optional)
messenger:  # Node.js Playwright scraper
```

---

## 🛡️ Security Notes

- ⚠️ Discord user token = Self-bot (ToS violation risk)
- ⚠️ FB scraping = ToS violation risk
- Use dedicated accounts
- Never commit `config/config.yaml` or `.env`
- Use `REDIS_PASSWORD` in production
- Consider official Discord Bot API for owned servers