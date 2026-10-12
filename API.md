# StockTradingSignals - API Reference

## Table of Contents

1. [Configuration API](#configuration-api)
2. [Core Classes](#core-classes)
3. [Discord Gateway](#discord-gateway)
4. [Messenger Scraper](#messenger-scraper)
5. [Signal Formatting](#signal-formatting)
6. [Deduplication](#deduplication)
7. [Discord Webhook](#discord-webhook)
8. [Social Media Queue](#social-media-queue)
9. [Social Scheduler](#social-scheduler)
10. [Social Media Posters](#social-media-posters)
11. [Rate Limiting](#rate-limiting)
12. [Redis Client](#redis-client)
13. [Utility Functions](#utility-functions)

---

## Configuration API

### `src.common.config.Settings`

Main settings class loaded from YAML and environment variables.

```python
from src.common.config import get_settings, load_config_from_yaml

# Get cached settings (loads from .env if not already loaded)
settings = get_settings()

# Load from YAML (overrides .env)
settings = load_config_from_yaml("config/config.yaml")
```

#### Settings Structure

```python
Settings(
    discord: DiscordSettings,
    messenger: MessengerSettings,
    redis: RedisSettings,
    deduplication: DeduplicationSettings,
    webhook: WebhookSettings,
    social: SocialSettings,
    logging: LoggingSettings,
    monitoring: MonitoringSettings
)
```

#### DiscordSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `user_token` | str | `""` | Discord user token from browser |
| `target_channel_ids` | List[str] | `[]` | Channel IDs to monitor |
| `premium_webhook_url` | str | `""` | Webhook for immediate forwarding |

#### MessengerSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `target_chat_url` | str | `"https://www.facebook.com/messages/t/"` | Messenger chat URL |
| `session_path` | str | `"./fb_session"` | Browser session directory |
| `headless` | bool | `True` | Run browser headless |
| `proxy` | str | `""` | Residential proxy `host:port:user:pass` |

#### RedisSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | str | `"localhost"` | Redis host |
| `port` | int | `6379` | Redis port |
| `db` | int | `0` | Database number |
| `password` | str | `""` | Optional password |
| `max_connections` | int | `20` | Connection pool size |

#### DeduplicationSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ttl_seconds` | int | `30` | Duplicate detection window |
| `hash_algorithm` | str | `"md5"` | Hash algorithm (`md5` or `sha256`) |

#### WebhookSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `url` | str | `""` | Discord webhook URL |
| `rate_limit_per_second` | int | `30` | Max requests/second |
| `max_retries` | int | `3` | Retry attempts |
| `retry_delay_seconds` | float | `1.0` | Base retry delay |

#### SocialSettings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `schedule_cron` | str | `"*/15 16-23,0-9 * * 1-5"` | Weekday posting schedule |
| `weekend_schedule_cron` | str | `"*/30 * * * 0,6"` | Weekend posting schedule |
| `twitter` | TwitterSettings | - | X/Twitter config |
| `stocktwits` | StocktwitsSettings | - | Stocktwits config |
| `threads` | ThreadsSettings | - | Threads config |
| `reddit` | RedditSettings | - | Reddit config |
| `telegram` | TelegramSettings | - | Telegram config |
| `linkedin` | LinkedInSettings | - | LinkedIn config |
| `email` | EmailSettings | - | Email config |

#### Platform Settings (Twitter, Stocktwits, Threads, etc.)

Each platform has common fields:

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `False` | Enable platform |
| `max_chars` | int | Platform-specific | Character limit |

**Twitter-specific**: `api_key`, `api_secret`, `bearer_token`, `access_token`, `refresh_token`

**Stocktwits-specific**: `client_id`, `client_secret`, `access_token`

**Threads-specific**: `app_id`, `app_secret`, `user_access_token`

**Reddit-specific**: `client_id`, `client_secret`, `refresh_token`, `target_subreddits`

**Telegram-specific**: `bot_token`, `chat_ids`

**LinkedIn-specific**: `client_id`, `client_secret`, `access_token`

**Email-specific**: `sendgrid_api_key`, `from_email`, `from_name`, `subscriber_list_id`, `schedule_cron`

---

## Core Classes

### `TradeSignal` (src/common/formatter.py)

```python
@dataclass
class TradeSignal:
    raw_text: str           # Original message text
    ticker: Optional[str] = None        # e.g., "AAPL"
    direction: Optional[str] = None     # "LONG" or "SHORT"
    entry: Optional[str] = None         # Entry price as string
    target: Optional[str] = None        # Target price
    stop_loss: Optional[str] = None     # Stop loss price
    expiry: Optional[str] = None        # Option expiry (MM/DD/YY)
    strike: Optional[str] = None        # Option strike
    option_type: Optional[str] = None   # "CALL" or "PUT"
    source: str = ""                    # Source identifier
    author: str = ""                    # Message author
    channel: str = ""                   # Channel/chat identifier
```

### `ParsedSignal` (src/discord/parser.py)

```python
@dataclass
class ParsedSignal:
    ticker: Optional[str] = None
    direction: Optional[str] = None
    entry: Optional[float] = None
    target: Optional[float] = None
    stop_loss: Optional[float] = None
    expiry: Optional[str] = None
    strike: Optional[float] = None
    option_type: Optional[str] = None
    confidence: float = 0.0     # 0-1 confidence score
    raw_text: str = ""
```

### `DiscordMessage` (src/discord/gateway.py)

```python
@dataclass
class DiscordMessage:
    id: str
    channel_id: str
    author_id: str
    author_username: str
    author_bot: bool
    content: str
    timestamp: str
    guild_id: Optional[str] = None
```

### `SocialJob` (src/social/queue.py)

```python
@dataclass
class SocialJob:
    id: str
    signal: Dict[str, Any]
    source: str
    timestamp: float
    platforms: List[str]
    priority: int = 0
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = 0.0
    scheduled_for: Optional[float] = None
```

---

## Discord Gateway

### `DiscordGateway` (src/discord/gateway.py)

Main WebSocket client for Discord user token connection.

#### Constructor

```python
gateway = DiscordGateway()
```

#### Methods

##### `set_message_handler(handler: Callable[[DiscordMessage], None])`
Set custom message handler for incoming messages.

```python
def my_handler(msg: DiscordMessage):
    print(f"New message: {msg.content}")

gateway.set_message_handler(my_handler)
```

##### `set_token_refresh_callback(callback: Callable[[], str])`
Set callback to fetch new token when current expires.

```python
def refresh_token():
    # Reload from config.yaml
    load_config_from_yaml("config/config.yaml")
    return get_settings().discord.user_token

gateway.set_token_refresh_callback(refresh_token)
```

##### `set_auth_failure_callback(callback: Callable[[], None])`
Set callback when authentication fails.

```python
def on_auth_failure():
    logger.warning("Auth failed - token may be expired")

gateway.set_auth_failure_callback(on_auth_failure)
```

##### `async connect() -> None`
Connect to Discord gateway with automatic reconnection. Blocks until shutdown.

```python
await gateway.connect()
```

##### `async close() -> None`
Gracefully close connection.

```python
await gateway.close()
```

#### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `GATEWAY_URL` | `"wss://gateway.discord.gg/?v=9&encoding=json"` | Discord gateway endpoint |
| `HEARTBEAT_INTERVAL` | `41250` | Default heartbeat (ms), updated from HELLO |
| `MAX_RECONNECT_ATTEMPTS` | `10` | Max reconnection attempts |
| `BASE_RECONNECT_DELAY` | `5` | Base delay for exponential backoff (seconds) |

---

## Messenger Scraper

### `src/messenger/scraper.js`

Node.js script - run directly with `node src/messenger/scraper.js`.

#### Configuration (Environment Variables)

| Variable | Default | Description |
|----------|---------|-------------|
| `MESSENGER_TARGET_CHAT_URL` | `https://www.facebook.com/messages/t/` | Target chat URL |
| `MESSENGER_SESSION_PATH` | `./fb_session` | Session directory |
| `MESSENGER_HEADLESS` | `true` | Headless mode |
| `MESSENGER_PROXY` | `""` | Proxy `host:port:user:pass` |
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | `""` | Redis password |
| `DISCORD_WEBHOOK_URL` | `""` | Webhook for immediate forwarding |
| `DEDUP_TTL` | `30` | Deduplication TTL (seconds) |

#### Key Functions

##### `parseSignal(text: string) -> Object`
Parse message text for signal components.

```javascript
const signal = parseSignal("$AAPL long entry 150 target 160");
// Returns: { ticker: "AAPL", direction: "LONG", entry: 150, target: 160, rawText: "..." }
```

##### `hashContent(content: string) -> string`
Generate MD5 hash for deduplication.

##### `isDuplicate(contentHash: string) -> boolean`
Check/set deduplication key in Redis. Returns `true` if duplicate.

##### `sendToWebhook(content, author, source)`
Send signal to Discord webhook immediately.

##### `queueForSocial(signalData)`
Queue signal for delayed social media posting.

##### `setupPage(page)`
Inject `broadcastSignal` function into page context and set up MutationObserver.

#### MutationObserver

Monitors these selectors for new messages:
- `div[role="grid"]`
- `div[aria-label="Messages"]`
- `[data-testid="message_thread"]`

Detects:
- `childList` mutations (new message elements)
- `characterData` mutations (text updates)

---

## Signal Formatting

### `SignalFormatter` (src/common/formatter.py)

#### `parse(text: str, source: str = "", author: str = "", channel: str = "") -> TradeSignal`
Parse raw signal text into structured `TradeSignal`.

```python
signal = SignalFormatter.parse(
    "AAPL long entry 150 target 160 stop 145",
    source="Discord#123",
    author="trader123",
    channel="123456"
)
```

#### `format_discord_embed(signal: TradeSignal) -> dict`
Format as Discord embed object.

```python
embed = SignalFormatter.format_discord_embed(signal)
# Returns dict ready for webhook embeds array
```

#### `format_twitter(signal: TradeSignal, max_chars: int = 280) -> str`
Format for X/Twitter (character limited).

```python
tweet = SignalFormatter.format_twitter(signal)
# "$AAPL | LONG | Entry: $150 | Target: $160 | SL: $145"
```

#### `format_stocktwits(signal: TradeSignal) -> str`
Format for Stocktwits (cashtags + sentiment).

```python
st_text = SignalFormatter.format_stocktwits(signal)
# "$AAPL #Bullish AAPL long entry 150 target 160 stop 145"
```

#### `format_threads(signal: TradeSignal) -> str`
Format for Threads/Instagram (visual with emojis).

```python
threads_text = SignalFormatter.format_threads(signal)
# "📊 $AAPL\n📈 LONG\n💰 Entry: $150\n🎯 Target: $160\n..."
```

#### `format_telegram(signal: TradeSignal) -> str`
Format for Telegram (Markdown).

```python
tg_text = SignalFormatter.format_telegram(signal)
# "*$AAPL*\n📈 *LONG*\n💰 Entry: `$150`\n..."
```

#### `format_reddit(signal: TradeSignal) -> tuple[str, str]`
Format for Reddit (title, body).

```python
title, body = SignalFormatter.format_reddit(signal)
# title: "$AAPL | LONG | Entry $150"
# body: "**Source:** Discord#123\n\nAAPL long entry 150...\n\n---"
```

#### `format_email(signal: TradeSignal) -> tuple[str, str]`
Format for Email (subject, HTML body).

```python
subject, html = SignalFormatter.format_email(signal)
# subject: "Trade Signal - AAPL - LONG"
# html: "<html><body>...</body></html>"
```

#### `is_likely_signal(text: str, min_confidence: float = 0.3) -> bool`
Quick check if text looks like a trade signal.

```python
if SignalFormatter.is_likely_signal(message):
    # Process as signal
```

---

### `DiscordParser` (src/discord/parser.py)

More detailed parser with confidence scoring.

#### `parse(text: str) -> ParsedSignal`
Parse with confidence score (0-1).

```python
signal = DiscordParser.parse("SPY 03/15/24 C 450 entry 5.50 target 8.00")
# signal.confidence > 0.7 for clear signals
```

#### `is_likely_signal(text: str, min_confidence: float = 0.3) -> bool`
Threshold-based signal detection.

---

### `format_for_platform` (src/social/formatter.py)

Unified dispatcher for platform formatting.

```python
from src.social.formatter import format_for_platform

text = format_for_platform(signal, 'twitter')
embed = format_for_platform(signal, 'discord')  # Returns dict
```

#### Supported Platforms

| Platform | Return Type | Description |
|----------|-------------|-------------|
| `discord` | `dict` | Discord embed object |
| `twitter` | `str` | ≤280 chars |
| `stocktwits` | `str` | Cashtags + sentiment |
| `threads` | `str` | Visual with emojis |
| `telegram` | `str` | Markdown |
| `reddit` | `str` | Body only |
| `email` | `str` | HTML body only |

#### `get_platform_config(platform: str) -> dict`
Get platform-specific configuration.

```python
config = get_platform_config('twitter')
# {'max_chars': 280, 'hashtags': ['#trading', '#stocks', '#signals'], ...}
```

#### `optimize_for_platform(text: str, platform: str) -> str`
Apply platform optimizations (hashtags, truncation).

---

## Deduplication

### `Deduplicator` (src/common/deduplicator.py)

#### `is_duplicate(content: str, source: str = "") -> bool`
Check if content is duplicate using Redis SETNX.

```python
dedup = get_deduplicator()
is_dup = await dedup.is_duplicate("signal content", "discord:123")
if not is_dup:
    # New signal, process it
```

**Returns**: `True` if duplicate (already seen), `False` if new.

#### `check_only(content: str) -> bool`
Read-only check without setting key.

```python
exists = await dedup.check_only("signal content")
```

#### `clear(content: str) -> bool`
Manually clear deduplication entry (for testing).

```python
await dedup.clear("signal content")
```

#### `get_stats() -> dict`
Get deduplication statistics.

```python
stats = await dedup.get_stats()
# {'total_tracked': 42, 'ttl_seconds': 30, 'hash_algorithm': 'md5'}
```

#### `get_deduplicator() -> Deduplicator`
Get global singleton instance.

---

## Discord Webhook

### `WebhookSender` (src/common/webhook.py)

#### `async initialize() -> None`
Initialize HTTP session and rate limiter.

```python
webhook = await get_webhook_sender()  # Auto-initializes
```

#### `async close() -> None`
Close HTTP session.

```python
await close_webhook_sender()
```

#### `async send(content, embeds, username, avatar_url) -> bool`
Send generic webhook message.

```python
success = await webhook.send(
    content="Simple message",
    embeds=[embed1, embed2],
    username="Custom Bot",
    avatar_url="https://..."
)
```

#### `async send_signal(signal_text, source, author, channel, color) -> bool`
Send formatted trading signal.

```python
success = await webhook.send_signal(
    signal_text="AAPL long entry 150 target 160",
    source="Discord#123",
    author="trader123",
    channel="123456",
    color=0x00FF00  # Green for long
)
```

#### `get_webhook_sender() -> WebhookSender`
Get global singleton instance.

---

## Social Media Queue

### `SocialQueue` (src/social/queue.py)

#### `async enqueue(signal, source, timestamp, platforms=None, priority=0) -> str`
Add job to queue.

```python
queue = await get_social_queue()
job_id = await queue.enqueue(
    signal=signal.__dict__,
    source="discord",
    timestamp=time.time(),
    platforms=["twitter", "stocktwits"],
    priority=10  # Higher = more urgent
)
```

#### `async dequeue(count=10) -> List[SocialJob]`
Get highest priority jobs.

```python
jobs = await queue.dequeue(count=20)
for job in jobs:
    # Process job
```

#### `async requeue(job: SocialJob, delay: float = 0) -> None`
Requeue job with optional delay.

```python
await queue.requeue(job, delay=300)  # Retry in 5 minutes
```

#### `async move_to_dead_letter(job: SocialJob, reason: str) -> None`
Move failed job to dead letter queue.

#### `async get_queue_stats() -> dict`
Get queue statistics.

```python
stats = await queue.get_queue_stats()
# {'queued': 5, 'processing': 1, 'dead_letter': 2, 'scheduled': 3}
```

#### `async process_scheduled() -> int`
Move due scheduled jobs to main queue. Returns count moved.

```python
moved = await queue.process_scheduled()
```

#### `get_social_queue() -> SocialQueue`
Get global singleton instance.

---

## Social Scheduler

### `SocialScheduler` (src/social/scheduler.py)

#### `start() -> None`
Start scheduler with configured cron jobs.

```python
scheduler = get_social_scheduler()
scheduler.start()
```

#### `stop() -> None`
Stop scheduler.

```python
scheduler.stop()
```

#### `is_posting_window() -> bool`
Check if current time is within posting window.

```python
if scheduler.is_posting_window():
    # Good time to post
```

#### `async trigger_immediate_post(signal, platforms=None) -> None`
Trigger immediate post (bypass scheduler) for testing.

```python
await scheduler.trigger_immediate_post(signal, platforms=["twitter"])
```

#### `get_social_scheduler() -> SocialScheduler`
Get global singleton instance.

#### `async start_scheduler() -> None`
Start global scheduler.

#### `async stop_scheduler() -> None`
Stop global scheduler.

---

## Social Media Posters

### Common Interface

All posters implement:
```python
async def initialize() -> bool    # Returns True if ready
async def post(text: str, signal: TradeSignal) -> bool  # Returns success
async def close() -> None         # Cleanup (where applicable)
```

### Twitter (`src/social/x_poster.py`)

```python
from src.social.x_poster import post_to_twitter, get_twitter_poster

# Convenience function
success = await post_to_twitter(text, signal)

# Or use poster directly
poster = await get_twitter_poster()
await poster.initialize()
success = await poster.post(text, signal)
await poster.post_thread(texts, signal)  # Thread support
```

**Requirements**: `twitter.enabled=true`, `api_key`, `api_secret`, `access_token`, `bearer_token`

### Stocktwits (`src/social/stocktwits_poster.py`)

```python
from src.social.stocktwits_poster import post_to_stocktwits

success = await post_to_stocktwits(text, signal)
```

**Requirements**: `stocktwits.enabled=true`, `access_token`

### Threads (`src/social/threads_poster.py`)

```python
from src.social.threads_poster import post_to_threads

success = await post_to_threads(text, signal)
# Carousel support:
# await poster.post_carousel(texts, images, signal)
```

**Requirements**: `threads.enabled=true`, `app_id`, `app_secret`, `user_access_token`

**Note**: Uses Instagram Graph API two-step process (create container → publish)

---

## Rate Limiting

### `TokenBucket` (src/social/rate_limiter.py)

```python
bucket = TokenBucket(rate=1.0, burst=10)  # 1 token/sec, max 10

wait_time = await bucket.take(tokens=1)  # Returns wait time
await bucket.acquire(tokens=1)  # Blocks until available
```

### `RateLimiter` (src/social/rate_limiter.py)

Manages per-platform token buckets.

```python
limiter = get_rate_limiter()
await limiter.acquire("twitter")  # Wait if rate limited
status = limiter.get_status()
```

#### Default Platform Limits

| Platform | Rate (req/s) | Burst |
|----------|--------------|-------|
| twitter | 0.33 | 50 |
| stocktwits | 0.028 | 10 |
| threads | 0.055 | 20 |
| reddit | 1.0 | 10 |
| telegram | 30.0 | 30 |

---

## Redis Client

### `RedisClient` (src/common/redis_client.py)

#### `async initialize() -> None`
Initialize connection pool.

```python
redis = await get_redis()  # Auto-initializes
```

#### `async health_check() -> bool`
Check connectivity.

```python
healthy = await redis.health_check()
```

#### `client` property
Get raw `redis.asyncio.Redis` client.

```python
await redis.client.set("key", "value")
value = await redis.client.get("key")
```

#### `async close() -> None`
Close all connections.

```python
await close_redis()
```

#### `async transaction()`
Context manager for transactions.

```python
async with redis.transaction() as pipe:
    pipe.set("key1", "value1")
    pipe.set("key2", "value2")
    # Executed atomically
```

---

## Utility Functions

### `src.common.config`

| Function | Description |
|----------|-------------|
| `get_settings()` | Get cached settings |
| `load_config_from_yaml(path)` | Load settings from YAML file |

### `src.common.redis_client`

| Function | Description |
|----------|-------------|
| `get_redis()` | Get global Redis client |
| `close_redis()` | Close global Redis client |

### `src.common.deduplicator`

| Function | Description |
|----------|-------------|
| `get_deduplicator()` | Get global deduplicator |

### `src.common.webhook`

| Function | Description |
|----------|-------------|
| `get_webhook_sender()` | Get global webhook sender |
| `close_webhook_sender()` | Close global webhook sender |

### `src.social.queue`

| Function | Description |
|----------|-------------|
| `get_social_queue()` | Get global social queue |

### `src.social.scheduler`

| Function | Description |
|----------|-------------|
| `get_social_scheduler()` | Get global scheduler |
| `start_scheduler()` | Start global scheduler |
| `stop_scheduler()` | Stop global scheduler |

### `src.social.rate_limiter`

| Function | Description |
|----------|-------------|
| `get_rate_limiter()` | Get global rate limiter |

### `src.social.x_poster`

| Function | Description |
|----------|-------------|
| `get_twitter_poster()` | Get global Twitter poster |
| `post_to_twitter(text, signal)` | Convenience post function |

### `src.social.stocktwits_poster`

| Function | Description |
|----------|-------------|
| `get_stocktwits_poster()` | Get global Stocktwits poster |
| `post_to_stocktwits(text, signal)` | Convenience post function |

### `src.social.threads_poster`

| Function | Description |
|----------|-------------|
| `get_threads_poster()` | Get global Threads poster |
| `post_to_threads(text, signal)` | Convenience post function |

---

## Entry Points

### Main Application (`src/main.py`)

```bash
python -m src.main
```

Runs:
1. Discord Gateway (blocks)
2. Social Scheduler (background)
3. Signal processing pipeline

### Messenger Scraper

```bash
node src/messenger/scraper.js
```

Runs:
1. Playwright browser with stealth
2. MutationObserver for real-time messages
3. Signal detection → webhook + queue

### Scheduler Only (Docker)

```bash
python -m src.social.scheduler
```

Runs only the social media scheduler (for separate scaling).

---

## Scripts

### `scripts/validate_config.py`

```bash
python scripts/validate_config.py [config.yaml]
```

Validates configuration file and reports warnings.

### `scripts/setup_fb_session.py`

```bash
python scripts/setup_fb_session.py
```

Interactive Facebook login to create session.

### `scripts/setup_social_auth.py`

```bash
python scripts/setup_social_auth.py
```

Interactive OAuth setup for all social platforms.

### `scripts/health_server.py`

```bash
python scripts/health_server.py
```

Standalone health check server (ports 8080/9090).

---

## Environment Variables

All settings can be overridden via environment variables (single underscore delimiter):

```bash
DISCORD_USER_TOKEN=your_token
DISCORD_TARGET_CHANNEL_IDS=123,456,789
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
REDIS_HOST=redis
REDIS_PORT=6379
MESSENGER_TARGET_CHAT_URL=https://...
MESSENGER_SESSION_PATH=./fb_session
SOCIAL_TWITTER_ENABLED=true
SOCIAL_TWITTER_API_KEY=...
SOCIAL_TWITTER_API_SECRET=...
# ... etc
```

---

## Error Handling Patterns

### Retry with Exponential Backoff

```python
for attempt in range(max_retries):
    try:
        result = await operation()
        return result
    except Exception as e:
        if attempt < max_retries - 1:
            wait = base_delay * (2 ** attempt)
            await asyncio.sleep(wait)
        else:
            raise
```

### Rate Limit Handling

```python
await limiter.acquire("twitter")
try:
    await poster.post(text, signal)
except RateLimitError:
    # Handled by token bucket
    pass
```

### Graceful Shutdown

```python
shutdown_event = asyncio.Event()

def signal_handler(sig, frame):
    shutdown_event.set()

for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, signal_handler)

await shutdown_event.wait()
await cleanup()
```