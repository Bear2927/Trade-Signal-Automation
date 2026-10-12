# StockTradingSignals - CLAUDE.md

## Project Overview
Automated trading signal aggregation service that scrapes from Discord and Facebook Messenger, forwards immediately to Discord webhook, and posts to social media after market hours.

## Key Commands

### Development
```bash
# Validate config
python scripts/validate_config.py

# Setup Facebook session
python scripts/setup_fb_session.py

# Setup social media OAuth
python scripts/setup_social_auth.py

# Run main app (Discord + scheduler)
python -m src.main

# Run Messenger scraper (separate terminal)
node src/messenger/scraper.js
```

### Docker
```bash
# Build and run
docker-compose -f docker/docker-compose.yml up -d --build

# Logs
docker-compose -f docker/docker-compose.yml logs -f app

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Testing
```bash
pytest tests/ -v
pytest tests/test_deduplicator.py -v
```

## Architecture Notes

### Dual Runtime
- **Python**: Discord gateway, Redis, webhook, scheduler, social posters
- **Node.js**: Messenger scraper (Playwright requires Node for best stealth support)

### Data Flow
1. Discord Gateway (WS) + Messenger (Playwright) → Receive messages
2. Deduplicator (Redis SETNX) → Filter duplicates
3. Immediate path → Discord webhook (real-time)
4. Delayed path → Redis queue → Scheduler (after hours) → Social APIs

### Critical Files
- `config/config.yaml` - All configuration
- `src/common/redis_client.py` - Redis connection pool
- `src/common/deduplicator.py` - Deduplication logic
- `src/common/webhook.py` - Discord webhook with retry
- `src/discord/gateway.py` - Discord WS listener
- `src/messenger/scraper.js` - Playwright Messenger scraper
- `src/social/scheduler.py` - After-hours cron scheduler
- `src/social/queue.py` - Redis job queue

## Common Issues

### Discord Connection
- Token expires → Re-extract from browser
- Gateway disconnects → Auto-reconnect with exponential backoff
- Rate limited → 120 events/60s limit, respects heartbeat

### Messenger Scraping
- Session expires → Re-run `setup_fb_session.py`
- FB detects automation → Use residential proxy + stealth
- DOM changes → Update selectors in `src/messenger/selectors.py`

### Social Media Posting
- Rate limits → Token bucket per platform
- OAuth tokens expire → Refresh token flow needed
- Posting window → Only runs 4PM-9:30AM ET weekdays

## Environment Variables
See `.env.example` for all options. Key ones:
- `DISCORD_USER_TOKEN` - User token from browser
- `DISCORD_TARGET_CHANNEL_IDS` - Comma-separated channel IDs
- `DISCORD_WEBHOOK_URL` - Premium channel webhook
- `REDIS_HOST` / `REDIS_PORT` - Redis connection

## Adding New Social Platform
1. Create poster in `src/social/{platform}_poster.py`
2. Add formatter in `src/social/formatter.py`
3. Add rate limiter bucket in `src/social/rate_limiter.py`
4. Register in `src/social/scheduler.py` platform_posters dict
5. Add config section in `config/config.yaml`