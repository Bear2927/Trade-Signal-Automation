# StockTradingSignals - Architecture Documentation

## Overview

StockTradingSignals is a dual-runtime (Python + Node.js) trading signal aggregation service that:
1. **Scrapes** trade ideas from Discord channels (via user-token WebSocket) and Facebook Messenger (via Playwright)
2. **Deduplicates** signals using Redis SETNX with configurable TTL
3. **Forwards immediately** to a premium Discord webhook (real-time)
4. **Queues for delayed posting** to social media platforms after market hours (4PM-9:30AM ET)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STOCKTRADINGSIGNALS                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌──────────────┐                                      │
│  │   Discord    │    │   Facebook   │                                      │
│  │   Gateway    │    │  Messenger   │                                      │
│  │  (Python)    │    │  (Node.js)   │                                      │
│  │              │    │              │                                      │
│  │ • WebSocket  │    │ • Playwright │                                      │
│  │ • User Token │    │ • Stealth    │                                      │
│  │ • Reconnect  │    │ • Mutation   │                                      │
│  │ • Heartbeat  │    │   Observer   │                                      │
│  └──────┬───────┘    └──────┬───────┘                                      │
│         │                   │                                              │
│         └─────────┬─────────┘                                              │
│                   ▼                                                        │
│         ┌───────────────────────┐                                          │
│         │   Redis Deduplication │                                          │
│         │   Layer (SETNX + TTL) │                                          │
│         │   Key: dedup:signal:  │                                          │
│         │   {md5_hash}          │                                          │
│         └───────────┬───────────┘                                          │
│                     │                                                      │
│         ┌───────────┴───────────┐                                          │
│         ▼                       ▼                                          │
│  ┌─────────────────┐   ┌─────────────────┐                                │
│  │  IMMEDIATE PATH │   │   DELAYED PATH  │                                │
│  │  (Real-time)    │   │  (After Hours)  │                                │
│  └────────┬────────┘   └────────┬────────┘                                │
│           │                     │                                          │
│           ▼                     ▼                                          │
│  ┌─────────────────┐   ┌─────────────────┐                                │
│  │  Discord        │   │  Redis Queue +  │                                │
│  │  Webhook        │   │  Scheduler      │                                │
│  │  (Rich Embeds)  │   │  (APScheduler)  │                                │
│  └─────────────────┘   └────────┬────────┘                                │
│                                 │                                         │
│                    ┌────────────┼────────────┐                            │
│                    ▼            ▼            ▼                            │
│             ┌───────────┐ ┌───────────┐ ┌───────────┐                    │
│             │    X      │ │ Stocktwits│ │  Threads  │                    │
│             │ (Tweepy)  │ │  (REST)   │ │(Graph API)│                    │
│             └───────────┘ └───────────┘ └───────────┘                    │
│                    ┌───────────┐ ┌───────────┐ ┌───────────┐             │
│                    │  Reddit   │ │ Telegram  │ │  LinkedIn │             │
│                    │  (PRAW)   │ │  (Bot)    │ │ (REST)    │             │
│                    └───────────┘ └───────────┘ └───────────┘             │
│                    ┌───────────┐                                           │
│                    │  Email    │                                           │
│                    │(SendGrid) │                                           │
│                    └───────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Ingestion Layer

#### Discord Gateway (`src/discord/gateway.py`)
- Connects to `wss://gateway.discord.gg/?v=9&encoding=json` using **user token** (not bot token)
- Implements full Discord Gateway protocol:
  - **Opcode 10 (HELLO)**: Receives heartbeat interval
  - **Opcode 1 (HEARTBEAT)**: Sends sequence number every interval
  - **Opcode 2 (IDENTIFY)**: Authenticates new session
  - **Opcode 6 (RESUME)**: Resumes existing session
  - **Opcode 7 (RECONNECT)**: Server-requested reconnect
  - **Opcode 9 (INVALID_SESSION)**: Session invalid, may need re-auth
  - **Opcode 0 (DISPATCH)**: Events (READY, MESSAGE_CREATE, RESUMED)
- **Auto-reconnection** with exponential backoff (max 10 attempts, capped at 5 min)
- **Token refresh callback** for handling expired tokens
- Filters messages by `target_channel_ids`, ignores bots, requires content

#### Messenger Scraper (`src/messenger/scraper.js`)
- Uses **Playwright + playwright-extra + stealth plugin** for anti-detection
- **Persistent context** saves session (cookies, localStorage) to `./fb_session/`
- **MutationObserver** in page context monitors DOM for new messages in real-time
- Exposes `broadcastSignal()` function to page context for sending detected signals
- Supports residential proxy rotation
- Headless/headful mode configurable

### 2. Deduplication Layer (`src/common/deduplicator.py`)

```
Content → MD5 Hash → Redis Key: dedup:signal:{hash}
                    ↓
              SETNX(key, source, EX=TTL)
                    ↓
            ┌───────┴───────┐
            ▼               ▼
         Returns          Returns
         True (new)      False (dup)
```

- **Algorithm**: MD5 (configurable to SHA256)
- **TTL**: Default 30 seconds (configurable)
- **Atomic**: SETNX ensures no race conditions
- **Key format**: `dedup:signal:{md5_hash}`
- **Value**: Source identifier (e.g., "discord:123456", "messenger")

### 3. Immediate Path - Discord Webhook (`src/common/webhook.py`)

- **Rate limited**: Configurable requests/second (default 30)
- **Retry logic**: Exponential backoff (max 3 retries by default)
- **Handles Discord 429**: Reads `Retry-After` header
- **Rich embeds**: Color-coded by direction (green=long, red=short)
- **Payload structure**:
  ```json
  {
    "embeds": [{
      "title": "📈 Trade Signal from Discord#123",
      "description": "Raw signal text...",
      "color": 0x00FF00,
      "fields": [
        {"name": "Source", "value": "Discord#123", "inline": true},
        {"name": "Author", "value": "trader123", "inline": true},
        {"name": "Direction", "value": "📈 LONG", "inline": true},
        {"name": "Entry", "value": "$150", "inline": true}
      ],
      "footer": {"text": "StockTradingSignals • Automated"}
    }]
  }
  ```

### 4. Delayed Path - Social Media Queue (`src/social/queue.py`)

- **Redis sorted set** for priority queue (`social:queue`)
- **Score = -priority** (negative for max-heap behavior)
- **Job structure**:
  ```python
  SocialJob(
      id="discord:1234567890",
      signal={...},           # TradeSignal dict
      source="discord",
      timestamp=1234567890.123,
      platforms=["twitter", "stocktwits", "threads"],
      priority=0,
      attempts=0,
      max_attempts=3,
      created_at=1234567890.123,
      scheduled_for=None      # For delayed execution
  )
  ```
- **Scheduled jobs**: Separate sorted set `social:sorted` with timestamp score
- **Dead letter queue**: `social:dead_letter` (list) for failed jobs

### 5. Scheduler (`src/social/scheduler.py`)

- **APScheduler** with `AsyncIOScheduler` in US/Eastern timezone
- **Weekday schedule**: `*/15 16-23,0-9 * * 1-5` (every 15 min, 4PM-9:30AM ET Mon-Fri)
- **Weekend schedule**: `*/30 * * * 0,6` (every 30 min weekends)
- **Job processor**: Runs every minute, moves due scheduled jobs to main queue
- **Stats logging**: Every 5 minutes
- **Platform posters**: Called per platform per job
- **Retry logic**: Failed jobs requeued with 5-minute delay

---

## Component Details

### Configuration System (`src/common/config.py`)

Uses **Pydantic Settings** with:
- **YAML file** (`config/config.yaml`) as primary source
- **Environment variables** (`.env`) as override (single underscore delimiter)
- **Nested settings** for each subsystem

```python
Settings(
    discord=DiscordSettings(...),
    messenger=MessengerSettings(...),
    redis=RedisSettings(...),
    deduplication=DeduplicationSettings(...),
    webhook=WebhookSettings(...),
    social=SocialSettings(
        schedule_cron="...",
        weekend_schedule_cron="...",
        twitter=TwitterSettings(...),
        stocktwits=StocktwitsSettings(...),
        threads=ThreadsSettings(...),
        ...
    ),
    logging=LoggingSettings(...),
    monitoring=MonitoringSettings(...)
)
```

### Redis Client (`src/common/redis_client.py`)

- **Connection pooling**: `redis.asyncio.ConnectionPool`
- **Health checks**: Periodic ping (30s interval)
- **Timeouts**: 5s connect, 5s socket
- **Retry on timeout**: Enabled
- **Transaction support**: Async context manager

### Signal Parsing (`src/common/formatter.py` + `src/discord/parser.py`)

Two parsers with similar logic:

1. **SignalFormatter** (common): Used by Discord gateway for webhook
2. **DiscordParser** (discord): More detailed, returns confidence score

**Extracted fields**:
- `ticker`: 1-5 uppercase chars, filtered against false positives
- `direction`: LONG/SHORT from keywords + emojis (🚀📈 / 📉🔻)
- `entry`, `target`, `stop_loss`: Sequential price extraction
- `expiry`, `strike`, `option_type`: Options contract parsing (MM/DD/YY C/P STRIKE)

**Platform formatters**:
- **Discord**: Rich embed
- **Twitter**: Compact, ≤280 chars
- **Stocktwits**: Cashtags + #Bullish/#Bearish
- **Threads**: Visual with emojis, hashtags
- **Telegram**: Markdown formatting
- **Reddit**: (title, body) tuple
- **Email**: (subject, HTML body) tuple

### Rate Limiting (`src/social/rate_limiter.py`)

**Token bucket algorithm** per platform:

| Platform | Rate (req/s) | Burst | Limit Source |
|----------|--------------|-------|--------------|
| Twitter  | 0.33         | 50    | 300/15min    |
| Stocktwits | 0.028      | 10    | ~100/hour    |
| Threads  | 0.055        | 20    | ~200/hour    |
| Reddit   | 1.0          | 10    | 60/min       |
| Telegram | 30.0         | 30    | 30/sec       |

### Social Media Posters

| Platform | Library | Auth | Notes |
|----------|---------|------|-------|
| X/Twitter | Tweepy | OAuth 1.0a + Bearer | API v2, supports threads |
| Stocktwits | aiohttp | Bearer token | Cashtags + symbols |
| Threads | aiohttp | User access token | Instagram Graph API, 2-step (container→publish) |
| Reddit | PRAW | Refresh token | Subreddit targeting |
| Telegram | python-telegram-bot | Bot token | Chat IDs list |
| LinkedIn | linkedin-api | Access token | Share API |
| Email | SendGrid | API key | Contact list, HTML templates |

---

## Deployment Architecture

### Docker Compose Services (`docker/docker-compose.yml`)

```yaml
services:
  redis:          # Redis 7 Alpine, persistence + healthcheck
  app:            # Main Python app (Discord + Scheduler)
  scheduler:      # Separate scheduler process (optional)
  messenger:      # Node.js Messenger scraper
```

**Resource limits**:
- `app`: 2GB RAM, 2 CPUs
- `messenger`: 1GB RAM, 1 CPU
- `redis`: 256MB maxmemory, LRU eviction

**Volumes**:
- `redis_data`: Redis persistence
- `../config`: Read-only config
- `../logs`: Application logs
- `../fb_session`: Messenger session persistence

### Multi-stage Dockerfile

1. **python-base**: Install Python deps
2. **node-base**: Install Node deps + Playwright + Chromium
3. **runtime**: Combine both, create non-root user, copy app code

---

## Key Design Decisions

### 1. Dual Runtime (Python + Node.js)
- **Python**: Async ecosystem (aiohttp, redis.asyncio, apscheduler), rich library support for APIs
- **Node.js**: Playwright has best stealth support in Node, MutationObserver requires browser context

### 2. User Token vs Bot Token (Discord)
- **User token** allows reading DMs and any channel the account has access to
- **Bot token** requires server membership and bot permissions
- **Trade-off**: User tokens violate Discord ToS (self-bot), risk of account ban

### 3. Redis SETNX for Deduplication
- **Atomic**: No race conditions between multiple scraper instances
- **TTL-based**: Automatic cleanup, no manual garbage collection
- **Low latency**: Single Redis round-trip

### 4. Priority Queue with Sorted Sets
- **O(log N)** insertion and retrieval
- **Priority support**: Higher priority = lower score (negative)
- **Scheduled jobs**: Separate sorted set by timestamp

### 5. After-Hours Posting Window
- **Market hours**: 9:30AM-4PM ET (avoid spam during trading)
- **Posting window**: 4PM-9:30AM ET (captures after-hours/pre-market attention)
- **Weekends**: Reduced frequency (every 30 min)

---

## Error Handling & Resilience

### Discord Gateway
- Exponential backoff reconnection (5s → 10s → 20s → ... max 300s)
- Jitter (±1s) to prevent thundering herd
- Session resume on disconnect (preserves sequence)
- Token refresh callback on 4004 (invalid token)

### Messenger Scraper
- Persistent session survives restarts
- Proxy rotation support
- Stealth plugin evades basic detection
- Graceful shutdown on SIGINT

### Social Media Posting
- Per-platform rate limiting (token bucket)
- Retry with exponential backoff (max 3 attempts)
- Dead letter queue for permanent failures
- Platform-specific error handling (429, auth expiry)

### Monitoring
- **Health check**: `GET /health` (port 8080)
- **Prometheus metrics**: `GET /metrics` (port 9090)
- **Structured JSON logging** (structlog)
- **Queue stats**: Logged every 5 minutes

---

## Security Considerations

### Credentials Management
- **Never commit** `config/config.yaml` or `.env`
- Use `.env.example` as template
- Docker: `env_file: ../.env` (not baked into image)
- Consider external secret managers for production

### ToS Compliance
⚠️ **Important**:
- **Discord**: User token self-bot violates ToS
- **Facebook**: Messenger scraping violates ToS
- **Twitter/Stocktwits/Threads**: Official APIs used (compliant)
- **Consider**: Official Discord Bot API for owned servers

### Network Security
- Redis: No auth by default (add password in production)
- Proxy: Residential proxy for Messenger (optional)
- Webhook: Validate Discord signature in production

---

## Scaling Considerations

### Horizontal Scaling
- **Discord Gateway**: Single connection per account (Discord limitation)
- **Messenger**: Multiple scraper instances possible with different sessions
- **Scheduler**: Single leader (APScheduler), or use distributed lock
- **Redis**: Single instance (upgrade to Redis Cluster for HA)

### Performance Tuning
- **Redis connections**: `max_connections: 20` (adjust for load)
- **Webhook rate limit**: 30/sec (Discord allows 30/sec per webhook)
- **Batch processing**: Scheduler dequeues 20 jobs per run
- **Heartbeat**: 41.25s default (Discord gateway)

---

## Adding New Platforms

1. **Create poster** in `src/social/{platform}_poster.py`:
   ```python
   class PlatformPoster:
       async def initialize() -> bool
       async def post(text: str, signal: TradeSignal) -> bool
   ```

2. **Add formatter** in `src/social/formatter.py`:
   ```python
   def format_for_platform(signal, platform): ...
   PLATFORM_CONFIG[platform] = {...}
   ```

3. **Add rate limiter bucket** in `src/social/rate_limiter.py`

4. **Register in scheduler** `platform_posters` dict

5. **Add config section** in `config/config.yaml` and `config.py`

---

## Testing Strategy

### Unit Tests (`tests/`)
- `test_deduplicator.py`: Redis mocking, duplicate detection
- `test_formatter.py`: Signal parsing, platform formatting
- `test_parsers.py`: Discord parser confidence scoring
- `test_social_scheduler.py`: Queue operations, scheduler logic

### Test Commands
```bash
pytest tests/ -v
pytest tests/test_deduplicator.py -v
pytest tests/test_formatter.py -v
```

### Mock Strategy
- Redis: `AsyncMock` for all operations
- HTTP: `aiohttp` responses mocked
- External APIs: Poster functions mocked

---

## Future Enhancements

### Planned
- [ ] Reddit poster implementation
- [ ] Telegram bot poster
- [ ] LinkedIn poster
- [ ] Email digest (SendGrid)
- [ ] Web dashboard for monitoring
- [ ] Signal analytics (win rate tracking)
- [ ] Multi-account Discord support
- [ ] Kubernetes deployment manifests

### Architecture Improvements
- [ ] Distributed scheduler with leader election
- [ ] Redis Cluster support
- [ ] Message persistence (PostgreSQL)
- [ ] Webhook signature verification
- [ ] Rate limit metrics export