# StockTradingSignals

Automated trading signal aggregation service that scrapes trade ideas from Discord channels and Facebook Messenger chats, then forwards them immediately to a premium Discord webhook and posts to social media platforms after market hours.

## Features

- **Real-time Discord scraping** - User-token WebSocket gateway listener (self-bot)
- **Facebook Messenger scraping** - Playwright + Stealth headless browser with session persistence
- **Smart deduplication** - Redis SETNX with configurable TTL (default 30s)
- **Immediate Discord forwarding** - Rich embeds to your premium channel
- **Delayed social media posting** - After market hours (4PM-9:30AM ET)
- **Multi-platform support** - X/Twitter, Stocktwits, Threads, Reddit, Telegram, LinkedIn, Email
- **Production ready** - Docker deployment, monitoring, graceful shutdown

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│  Discord Gateway │     │  FB Messenger   │
│  (User Token)    │     │  (Playwright)   │
└────────┬──────────┘     └────────┬────────┘
         │                         │
         ▼                         ▼
┌─────────────────────────────────────────┐
│         Redis Deduplication Layer       │
│    SETNX(content_hash, 30s TTL)         │
└──────────────────┬──────────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
┌──────────────────┐  ┌──────────────────┐
│  IMMEDIATE PATH  │  │  DELAYED PATH    │
│  (Discord Sub)   │  │  (Social Media)  │
└────────┬─────────┘  └────────┬─────────┘
         │                     │
         ▼                     ▼
┌──────────────────┐  ┌──────────────────┐
│ Discord Webhook  │  │ Redis Queue +    │
│ (Real-time)      │  │ Scheduler        │
└──────────────────┘  │ (After Hours)    │
                      └────────┬─────────┘
                               │
                    ┌──────────┼──────────┐
                    ▼          ▼          ▼
               ┌─────────┐ ┌─────────┐ ┌─────────┐
               │    X    │ │Stocktwits│ │ Threads │
               │ (Tweet) │ │ (Post)  │ │ (Post)  │
               └─────────┘ └─────────┘ └─────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Redis 7+
- Docker (optional, for production)

### Installation

```bash
# Clone and navigate
cd StockTradingSignals

# Python dependencies
pip install -r requirements.txt

# Node.js dependencies (for Messenger scraper)
npm install

# Install Playwright browsers
npx playwright install --with-deps chromium
```

### Configuration

1. Copy example config:
```bash
cp config/config.example.yaml config/config.yaml
cp .env.example .env
```

2. Edit `config/config.yaml` with your credentials (see [Credential Setup](#credential-setup))

3. Validate config:
```bash
python scripts/validate_config.py
```

### Credential Setup

#### Discord User Token (Required)
1. Open Discord in browser (desktop app works too)
2. F12 → Network tab → filter "gateway"
3. Send a message or refresh
4. Click websocket connection → Headers → `Authorization`
5. Add to config: `discord.user_token`

⚠️ **WARNING**: Using user tokens for self-bots violates Discord ToS and can lead to account ban. Use a dedicated account at your own risk.

#### Facebook Messenger Session (Required)
```bash
python scripts/setup_fb_session.py
```
- Browser opens → log in manually (handle 2FA)
- Navigate to target chat
- Press Enter in terminal when done
- Session saved to `./fb_session/`

#### Social Media APIs (Optional)
```bash
python scripts/setup_social_auth.py
```
Guides you through OAuth for each platform.

### Running

#### Development (separate terminals)

Terminal 1 - Discord scraper + API:
```bash
python -m src.main
```

Terminal 2 - Messenger scraper:
```bash
node src/messenger/scraper.js
```

#### Production (Docker)

```bash
# Build and start
docker-compose -f docker/docker-compose.yml up -d

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop
docker-compose -f docker/docker-compose.yml down
```

## Configuration Reference

### Discord
```yaml
discord:
  user_token: ""           # Your user token
  target_channel_ids: []   # Channel IDs to monitor
  premium_webhook_url: ""  # Webhook for immediate forwarding
```

### Messenger
```yaml
messenger:
  target_chat_url: "https://www.facebook.com/messages/t/"
  session_path: "./fb_session"
  headless: true
  proxy: ""  # host:port:user:pass for residential proxy
```

### Social Media (Delayed/After-Hours)
```yaml
social:
  schedule_cron: "*/15 16-23,0-9 * * 1-5"  # Weekdays 4PM-9:30AM ET
  weekend_schedule_cron: "*/30 * * * 0,6"  # Weekends every 30min
  
  twitter:
    enabled: false
    api_key: ""
    api_secret: ""
    bearer_token: ""
    access_token: ""
    refresh_token: ""
```

## Social Media Scheduling

| Platform | Posting Window | Optimal Time |
|----------|---------------|--------------|
| X/Twitter | 4PM-9:30AM ET | 4-6 PM ET |
| Stocktwits | 4PM-9:30AM ET | 4-5 PM ET |
| Threads | 4PM-9:30AM ET | 7-9 PM ET |
| Reddit | 4PM-9:30AM ET | 8-10 PM ET |
| Telegram | 4PM-9:30AM ET | 4 PM + 8 AM ET |
| Email Digest | Weekdays 6 AM ET | Morning |

## Recommended Additional Platforms

| Platform | Audience | Best For |
|----------|----------|----------|
| **Telegram** | Crypto/forex traders | Instant delivery, large communities |
| **Reddit** | Retail traders (WSB, stocks, options) | Viral potential |
| **Email Digest** | Paid subscribers | Highest conversion, owned audience |

## Project Structure

```
StockTradingSignals/
├── config/
│   ├── config.yaml          # Your configuration
│   └── config.example.yaml  # Template
├── src/
│   ├── common/              # Shared utilities
│   │   ├── config.py        # Configuration management
│   │   ├── redis_client.py  # Redis connection pooling
│   │   ├── deduplicator.py  # MD5 + SETNX deduplication
│   │   ├── webhook.py       # Discord webhook sender
│   │   ├── formatter.py     # Signal parsing & formatting
│   │   └── proxy.py         # Proxy rotation
│   ├── discord/
│   │   ├── gateway.py       # WebSocket gateway listener
│   │   └── parser.py        # Message parsing
│   ├── messenger/
│   │   ├── scraper.js       # Playwright scraper (Node.js)
│   │   ├── session.py       # Session management
│   │   └── selectors.py     # DOM selectors
│   ├── social/
│   │   ├── scheduler.py     # After-hours scheduler
│   │   ├── queue.py         # Redis job queue
│   │   ├── x_poster.py      # X/Twitter API v2
│   │   ├── stocktwits_poster.py
│   │   ├── threads_poster.py
│   │   ├── formatter.py     # Platform formatting
│   │   └── rate_limiter.py  # Token bucket rate limiting
│   └── main.py              # Entry point
├── scripts/
│   ├── setup_fb_session.py  # Interactive FB login
│   ├── setup_social_auth.py # OAuth helper
│   └── validate_config.py   # Config validation
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── requirements.txt
├── package.json
└── .env.example
```

## Legal/ToS Notice

⚠️ **IMPORTANT**: 
- **Discord**: User tokens for self-bots violate ToS (can lead to account ban)
- **Facebook**: Scraping Messenger violates ToS; automated access prohibited
- **Consider official APIs** where available (Discord bot API for owned servers)
- This implementation is for educational/research purposes
- Use at your own risk

## Monitoring

- Health check: `http://localhost:8080/health`
- Prometheus metrics: `http://localhost:9090/metrics`
- Logs: `./logs/app.log` (JSON format)

## Testing

```bash
# Run tests
pytest tests/

# Test deduplication
python -m pytest tests/test_deduplicator.py -v

# Test formatters
python -m pytest tests/test_formatter.py -v
```

## License

MIT License - Use at your own risk.