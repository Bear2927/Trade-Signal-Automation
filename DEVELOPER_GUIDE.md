# StockTradingSignals - Developer Guide

## Table of Contents

1. [Project Structure](#project-structure)
2. [Development Workflow](#development-workflow)
3. [Code Style & Standards](#code-style--standards)
4. [Testing](#testing)
5. [Adding New Social Platforms](#adding-new-social-platforms)
6. [Extending Signal Parsing](#extending-signal-parsing)
7. [Adding New Data Sources](#adding-new-data-sources)
8. [Debugging](#debugging)
9. [Contributing](#contributing)

---

## Project Structure

```
StockTradingSignals/
├── config/
│   ├── config.yaml              # Your configuration (gitignored)
│   └── config.example.yaml      # Template
├── src/
│   ├── common/                  # Shared utilities
│   │   ├── __init__.py
│   │   ├── config.py            # Pydantic settings management
│   │   ├── redis_client.py      # Redis connection pooling
│   │   ├── deduplicator.py      # MD5 + SETNX deduplication
│   │   ├── webhook.py           # Discord webhook sender
│   │   ├── formatter.py         # Signal parsing & formatting
│   │   └── proxy.py             # Proxy rotation (stub)
│   ├── discord/
│   │   ├── __init__.py
│   │   ├── gateway.py           # WebSocket gateway listener
│   │   └── parser.py            # Discord message parser
│   ├── messenger/
│   │   ├── __init__.py
│   │   ├── scraper.js           # Playwright scraper (Node.js)
│   │   ├── session.py           # Session management
│   │   └── selectors.py         # DOM selectors
│   ├── social/
│   │   ├── __init__.py
│   │   ├── scheduler.py         # After-hours cron scheduler
│   │   ├── queue.py             # Redis job queue
│   │   ├── x_poster.py          # X/Twitter API v2
│   │   ├── stocktwits_poster.py # Stocktwits API
│   │   ├── threads_poster.py    # Threads (Instagram Graph API)
│   │   ├── formatter.py         # Platform formatting
│   │   └── rate_limiter.py      # Token bucket rate limiting
│   └── main.py                  # Entry point
├── scripts/
│   ├── setup_fb_session.py      # Interactive FB login
│   ├── setup_social_auth.py     # OAuth helper
│   ├── validate_config.py       # Config validation
│   ├── health_server.py         # Health/metrics server
│   ├── token_watcher.py         # Token monitoring
│   ├── refresh_token.py         # Token refresh
│   └── generate_env.py          # Env file generator
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_parsers.py          # Discord/Messenger parser tests
│   ├── test_formatter.py        # Formatter tests
│   ├── test_deduplicator.py     # Deduplication tests
│   └── test_social_scheduler.py # Scheduler/queue tests
├── docker/
│   ├── Dockerfile               # Multi-stage build
│   └── docker-compose.yml       # Service orchestration
├── requirements.txt             # Python dependencies
├── requirements-dev.txt         # Dev dependencies
├── package.json                 # Node.js dependencies
├── pytest.ini                   # Pytest config
└── README.md
```

---

## Development Workflow

### 1. Setup Development Environment

```bash
# Clone and enter
cd StockTradingSignals

# Python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Node.js
npm install
npx playwright install --with-deps chromium

# Redis (for tests)
docker run -d -p 6379:6379 redis:7-alpine

# Pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

### 2. Configuration for Development

```bash
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with test credentials or use mocks
```

### 3. Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_deduplicator.py -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Watch mode (requires pytest-watch)
ptw tests/
```

### 4. Running Services Locally

```bash
# Terminal 1: Main app
python -m src.main

# Terminal 2: Messenger scraper
node src/messenger/scraper.js

# Terminal 3: Health server (optional)
python scripts/health_server.py
```

### 5. Code Quality Checks

```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
ruff format src/

# All checks
ruff check src/ && mypy src/ && pytest tests/
```

---

## Code Style & Standards

### Python Style Guide

- **Formatter**: Ruff (replaces Black, isort, flake8)
- **Type hints**: Required for all public functions
- **Docstrings**: Google style for classes/functions
- **Line length**: 100 characters
- **Imports**: Absolute imports from `src.`

```python
# Good
from src.common.config import get_settings
from src.common.formatter import TradeSignal

# Avoid
from common.config import get_settings
import src.common.formatter
```

### Type Hints

```python
# Required for public APIs
async def process_signal(signal: TradeSignal) -> bool:
    """Process a trade signal.
    
    Args:
        signal: Parsed trade signal
        
    Returns:
        True if processed successfully
    """
    ...

# Use Optional for nullable
from typing import Optional

def parse(text: str) -> Optional[TradeSignal]:
    ...
```

### Async Patterns

```python
# Use asyncio for concurrent operations
async def process_multiple(signals: list[TradeSignal]) -> list[bool]:
    tasks = [process_signal(s) for s in signals]
    return await asyncio.gather(*tasks)

# Use async context managers for resources
async with redis.transaction() as pipe:
    pipe.set("key", "value")
    await pipe.execute()

# Proper error handling
try:
    result = await risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

### Logging

```python
import logging
import structlog

# Module logger
logger = logging.getLogger(__name__)

# Structured logging (when JSON format enabled)
logger.info("Signal processed", ticker="AAPL", direction="LONG", latency_ms=45)

# Levels
logger.debug("Detailed debug info")
logger.info("General information")
logger.warning("Warning, but continuing")
logger.error("Error occurred", exc_info=True)
```

### Configuration Access

```python
# Always use get_settings() - returns cached singleton
from src.common.config import get_settings

def some_function():
    settings = get_settings()
    token = settings.discord.user_token
    redis_host = settings.redis.host
```

### Redis Key Naming Convention

```
dedup:signal:{hash}           # Deduplication
social:queue                  # Main job queue (sorted set)
social:scheduled              # Scheduled jobs (sorted set)
social:processing             # Currently processing (set)
social:dead_letter            # Failed jobs (list)
social:priority               # Priority index (sorted set)
```

---

## Testing

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_parsers.py          # Parser unit tests
├── test_formatter.py        # Formatter unit tests
├── test_deduplicator.py     # Deduplication tests
└── test_social_scheduler.py # Scheduler/queue tests
```

### Fixtures (conftest.py)

```python
@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=0)
    redis.delete = AsyncMock(return_value=1)
    redis.scan_iter = AsyncMock(return_value=iter([]))
    redis.zadd = AsyncMock(return_value=1)
    redis.zpopmin = AsyncMock(return_value=[])
    redis.zcard = AsyncMock(return_value=0)
    redis.scard = AsyncMock(return_value=0)
    redis.llen = AsyncMock(return_value=0)
    redis.zrem = AsyncMock(return_value=1)
    redis.zrangebyscore = AsyncMock(return_value=[])
    redis.lpush = AsyncMock(return_value=1)
    return redis
```

### Writing Tests

```python
# test_example.py
import pytest
from src.common.formatter import SignalFormatter, TradeSignal

class TestSignalFormatter:
    """Test signal parsing and formatting."""
    
    def test_parse_basic_signal(self):
        """Parse a basic trade signal."""
        text = "AAPL long entry 150 target 160 stop 145"
        signal = SignalFormatter.parse(text)
        
        assert signal.ticker == "AAPL"
        assert signal.direction == "LONG"
        assert signal.entry == "150"
    
    @pytest.mark.asyncio
    async def test_async_operation(self, mock_redis):
        """Test async function with mocked Redis."""
        from src.common.deduplicator import Deduplicator
        
        with patch('src.common.deduplicator.get_redis') as mock_get:
            mock_client = MagicMock()
            mock_client.client = mock_redis
            mock_get.return_value = mock_client
            
            dedup = Deduplicator()
            result = await dedup.is_duplicate("test", "source")
            assert result is False
```

### Running Specific Tests

```bash
# By marker
pytest -m "not slow" tests/

# By keyword
pytest -k "twitter" tests/

# Verbose with output
pytest tests/test_formatter.py::TestSignalFormatter::test_parse_basic_signal -v -s
```

---

## Adding New Social Platforms

### 1. Create Poster Module

Create `src/social/{platform}_poster.py`:

```python
"""{Platform} API poster."""

import logging
from typing import Optional
import aiohttp
from src.common.config import get_settings
from src.common.formatter import TradeSignal

logger = logging.getLogger(__name__)


class {Platform}Poster:
    """Posts to {Platform} using their API."""
    
    BASE_URL = "https://api.{platform}.com/v1"
    
    def __init__(self):
        self._settings = get_settings()
        self._access_token: Optional[str] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._initialized = False
    
    async def initialize(self) -> bool:
        """Initialize {Platform} client."""
        if self._initialized:
            return True
        
        platform_config = self._settings.social.{platform}
        if not platform_config.enabled:
            logger.info("{Platform} posting disabled")
            return False
        
        # Validate required credentials
        if not all([platform_config.field1, platform_config.field2]):
            logger.warning("{Platform} credentials incomplete")
            return False
        
        self._access_token = platform_config.access_token
        
        timeout = aiohttp.ClientTimeout(total=30)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            }
        )
        
        # Verify credentials
        if await self._verify_credentials():
            self._initialized = True
            logger.info("{Platform} client initialized")
            return True
        
        return False
    
    async def _verify_credentials(self) -> bool:
        """Verify access token is valid."""
        if not self._session:
            return False
        try:
            async with self._session.get(f"{self.BASE_URL}/me") as resp:
                return resp.status == 200
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def post(self, text: str, signal: TradeSignal) -> bool:
        """Post a message to {Platform}."""
        if not self._initialized:
            await self.initialize()
        
        if not self._session:
            return False
        
        try:
            payload = {"text": text}
            
            async with self._session.post(
                f"{self.BASE_URL}/posts",
                json=payload
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"{Platform} post created: {data.get('id')}")
                    return True
                elif resp.status == 429:
                    logger.warning("{Platform} rate limited")
                    return False
                else:
                    error_text = await resp.text()
                    logger.error(f"{Platform} post failed: {resp.status} - {error_text}")
                    return False
                    
        except Exception as e:
            logger.error(f"{Platform} post error: {e}")
            return False


# Global instance
_{platform}_poster: Optional[{Platform}Poster] = None


async def get_{platform}_poster() -> {Platform}Poster:
    """Get or create the global {Platform} poster."""
    global _{platform}_poster
    if _{platform}_poster is None:
        _{platform}_poster = {Platform}Poster()
    return _{platform}_poster


async def post_to_{platform}(text: str, signal: TradeSignal) -> bool:
    """Convenience function to post to {Platform}."""
    poster = await get_{platform}_poster()
    return await poster.post(text, signal)
```

### 2. Add Platform Configuration

In `src/common/config.py`, add platform settings class:

```python
class {Platform}Settings(BaseSettings):
    enabled: bool = False
    field1: str = ""
    field2: str = ""
    access_token: str = ""
    max_chars: int = 1000
```

Add to `SocialSettings`:

```python
class SocialSettings(BaseSettings):
    ...
    {platform}: {Platform}Settings = Field(default_factory={Platform}Settings)
```

Update `load_config_from_yaml` to handle new platform.

### 3. Add Formatter

In `src/social/formatter.py`:

```python
def format_for_{platform}(signal: TradeSignal) -> str:
    """Format signal for {Platform}."""
    # Custom formatting logic
    parts = []
    if signal.ticker:
        parts.append(f"${signal.ticker}")
    if signal.direction:
        parts.append(signal.direction)
    # ...
    return " | ".join(parts)


# Add to PLATFORM_CONFIG
PLATFORM_CONFIG = {
    ...
    "{platform}": {
        "max_chars": 1000,
        "hashtags": ["#trading", "#stocks"],
        "supports_thread": False,
        "supports_media": False,
    },
}


# Add to format_for_platform dispatcher
def format_for_platform(signal: TradeSignal, platform: str, max_chars: Optional[int] = None) -> str:
    formatter_map = {
        ...
        '{platform}': format_for_{platform},
    }
    ...
```

### 4. Add Rate Limiter

In `src/social/rate_limiter.py`:

```python
def _initialize_buckets(self) -> None:
    ...
    if social.{platform}.enabled:
        self._buckets["{platform}"] = TokenBucket(rate=X.XX, burst=YY)
```

Check platform's API docs for rate limits.

### 5. Register in Scheduler

In `src/social/scheduler.py`:

```python
from src.social.{platform}_poster import post_to_{platform}

class SocialScheduler:
    def __init__(self):
        ...
        self._platform_posters = {
            ...
            "{platform}": post_to_{platform},
        }
```

### 6. Add Config Example

In `config/config.example.yaml`:

```yaml
social:
  ...
  {platform}:
    enabled: false
    field1: ""
    field2: ""
    access_token: ""
    max_chars: 1000
```

### 7. Write Tests

```python
# tests/test_{platform}_poster.py
import pytest
from unittest.mock import AsyncMock, patch
from src.social.{platform}_poster import {Platform}Poster, post_to_{platform}
from src.common.formatter import TradeSignal

@pytest.mark.asyncio
async def test_{platform}_post_success():
    with patch('src.social.{platform}_poster.aiohttp.ClientSession') as mock_session:
        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.json = AsyncMock(return_value={"id": "123"})
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_resp
        
        poster = {Platform}Poster()
        poster._initialized = True
        poster._session = mock_session.return_value.__aenter__.return_value
        
        signal = TradeSignal(raw_text="test", ticker="AAPL")
        result = await poster.post("test message", signal)
        
        assert result is True
```

---

## Extending Signal Parsing

### Adding New Signal Patterns

#### 1. Extend Regex Patterns

In `src/common/formatter.py` or `src/discord/parser.py`:

```python
class SignalFormatter:
    # Add new patterns
    CRYPTO_PATTERN = re.compile(r'\$([A-Z]{2,10})(?:USDT?|PERP)?\b')
    FOREX_PATTERN = re.compile(r'([A-Z]{3})/([A-Z]{3})')
    FUTURES_PATTERN = re.compile(r'([A-Z]{1,2})([FGHJKMNQUVXZ])(\d{2})')
    
    @classmethod
    def parse(cls, text: str, ...) -> TradeSignal:
        ...
        # Add crypto detection
        crypto_match = cls.CRYPTO_PATTERN.search(text.upper())
        if crypto_match:
            signal.ticker = crypto_match.group(1)
            signal.asset_class = "CRYPTO"
        
        # Add forex detection
        forex_match = cls.FOREX_PATTERN.search(text.upper())
        if forex_match:
            signal.ticker = f"{forex_match.group(1)}/{forex_match.group(2)}"
            signal.asset_class = "FOREX"
```

#### 2. Add New Fields to TradeSignal

```python
@dataclass
class TradeSignal:
    ...
    asset_class: Optional[str] = None      # STOCK, OPTION, CRYPTO, FOREX, FUTURES
    timeframe: Optional[str] = None        # SCALP, SWING, POSITION
    leverage: Optional[str] = None         # e.g., "10x", "20x"
    risk_reward: Optional[float] = None    # Calculated R:R ratio
```

#### 3. Add Confidence Scoring Rules

```python
@classmethod
def parse(cls, text: str, ...) -> TradeSignal:
    ...
    # Boost confidence for specific patterns
    if signal.asset_class == "OPTION" and signal.expiry and signal.strike:
        signal.confidence += 0.2  # Complete option contract
    
    if signal.asset_class == "CRYPTO" and "leverage" in text_lower:
        signal.confidence += 0.15
    
    # Risk/reward calculation
    if signal.entry and signal.target and signal.stop_loss:
        try:
            entry = float(signal.entry)
            target = float(signal.target)
            stop = float(signal.stop_loss)
            if signal.direction == "LONG":
                rr = (target - entry) / (entry - stop)
            else:
                rr = (entry - target) / (stop - entry)
            signal.risk_reward = round(rr, 2)
            if rr > 2:
                signal.confidence += 0.1
        except (ValueError, ZeroDivisionError):
            pass
```

### Custom Parsers

Create domain-specific parsers:

```python
# src/common/parsers/crypto_parser.py
class CryptoParser:
    """Specialized parser for crypto signals."""
    
    LEVERAGE_PATTERN = re.compile(r'(\d+)x')
    PERP_PATTERN = re.compile(r'PERP|PERPETUAL')
    
    @classmethod
    def parse(cls, text: str) -> TradeSignal:
        signal = SignalFormatter.parse(text)
        # Add crypto-specific parsing
        return signal
```

---

## Adding New Data Sources

### 1. Create Source Module

Create `src/{source}/` directory:

```
src/
├── telegram/
│   ├── __init__.py
│   ├── client.py          # Telegram client
│   ├── parser.py          # Message parser
│   └── handler.py         # Event handler
```

### 2. Implement Base Interface

```python
# src/telegram/client.py
from abc import ABC, abstractmethod

class SignalSource(ABC):
    """Base interface for signal sources."""
    
    @abstractmethod
    async def start(self) -> None:
        """Start listening for signals."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop listening."""
        pass
    
    @abstractmethod
    def set_signal_handler(self, handler: Callable[[TradeSignal], None]) -> None:
        """Set callback for new signals."""
        pass
```

### 3. Implement Source

```python
# src/telegram/client.py
import logging
from telethon import TelegramClient, events
from src.common.formatter import TradeSignal, SignalFormatter
from src.common.deduplicator import get_deduplicator
from src.common.webhook import get_webhook_sender
from src.social.queue import get_social_queue

logger = logging.getLogger(__name__)


class TelegramSource(SignalSource):
    """Telegram channel monitor."""
    
    def __init__(self, api_id: int, api_hash: str, channel_ids: list[int]):
        self._api_id = api_id
        self._api_hash = api_hash
        self._channel_ids = channel_ids
        self._client: TelegramClient = None
        self._signal_handler: Callable = None
        self._running = False
    
    async def start(self) -> None:
        self._client = TelegramClient('session', self._api_id, self._api_hash)
        await self._client.start()
        
        @self._client.on(events.NewMessage(chats=self._channel_ids))
        async def handler(event):
            await self._process_message(event.message)
        
        self._running = True
        logger.info("Telegram source started")
    
    async def stop(self) -> None:
        self._running = False
        if self._client:
            await self._client.disconnect()
        logger.info("Telegram source stopped")
    
    def set_signal_handler(self, handler: Callable[[TradeSignal], None]) -> None:
        self._signal_handler = handler
    
    async def _process_message(self, message) -> None:
        text = message.text or ""
        if not text.strip():
            return
        
        # Deduplication
        dedup = get_deduplicator()
        dedup_key = f"telegram:{message.chat_id}:{message.id}:{text}"
        if await dedup.is_duplicate(dedup_key, f"telegram:{message.chat_id}"):
            return
        
        # Parse signal
        signal = SignalFormatter.parse(
            text,
            source=f"Telegram#{message.chat_id}",
            author=str(message.sender_id),
            channel=str(message.chat_id),
        )
        
        # Immediate webhook
        webhook = await get_webhook_sender()
        await webhook.send_signal(
            signal_text=signal.raw_text,
            source=f"Telegram#{message.chat_id}",
            author=str(message.sender_id),
        )
        
        # Queue for social
        queue = await get_social_queue()
        await queue.enqueue({
            "signal": signal.__dict__,
            "source": "telegram",
            "timestamp": message.date.timestamp(),
        })
        
        # Call custom handler
        if self._signal_handler:
            self._signal_handler(signal)
```

### 4. Integrate with Main App

```python
# src/main.py
from src.telegram.client import TelegramSource

async def main():
    ...
    
    # Start Telegram source
    telegram = TelegramSource(
        api_id=settings.telegram.api_id,
        api_hash=settings.telegram.api_hash,
        channel_ids=settings.telegram.channel_ids,
    )
    await telegram.start()
    
    try:
        # Run gateway (blocks)
        await gateway.connect()
    finally:
        await telegram.stop()
        ...
```

### 5. Add Configuration

```python
# src/common/config.py
class TelegramSourceSettings(BaseSettings):
    enabled: bool = False
    api_id: int = 0
    api_hash: str = ""
    channel_ids: List[int] = Field(default_factory=list)

class Settings(BaseSettings):
    ...
    telegram_source: TelegramSourceSettings = Field(default_factory=TelegramSourceSettings)
```

---

## Debugging

### 1. Enable Debug Logging

```yaml
# config/config.yaml
logging:
  level: "DEBUG"
  format: "text"  # Human-readable for development
```

```bash
# Or via environment
LOGGING_LEVEL=DEBUG python -m src.main
```

### 2. Debug Discord Gateway

```python
# Add debug logging to gateway.py
logger.setLevel(logging.DEBUG)

# Log all gateway messages
async def _handle_message(self, data: dict) -> None:
    logger.debug(f"Gateway message: op={data.get('op')}, t={data.get('t')}, s={data.get('s')}")
    ...
```

### 3. Debug Messenger Scraper

```javascript
// In scraper.js - add debug logging
console.log('DEBUG: Page loaded, URL:', page.url());

// Debug MutationObserver
await page.evaluate(() => {
    window._debugObserver = true;
    // Log all mutations
    const originalCallback = callback;
    callback = (mutations) => {
        console.log('DEBUG: Mutations:', mutations.length);
        mutations.forEach(m => console.log('  ', m.type, m.target.tagName));
        originalCallback(mutations);
    };
});
```

### 4. Inspect Redis State

```bash
# Connect to Redis
redis-cli

# Check deduplication keys
KEYS dedup:signal:*

# Check queue
ZRANGE social:queue 0 -1 WITHSCORES

# Check scheduled
ZRANGE social:scheduled 0 -1 WITHSCORES

# Check dead letter
LRANGE social:dead_letter 0 -1

# Monitor commands in real-time
MONITOR
```

### 5. Debug Social Posting

```python
# Test poster in isolation
python -c "
import asyncio
from src.social.x_poster import get_twitter_poster
from src.common.formatter import TradeSignal

async def test():
    poster = await get_twitter_poster()
    print('Init:', await poster.initialize())
    signal = TradeSignal(raw_text='test', ticker='AAPL', direction='LONG')
    print('Post:', await poster.post('Test tweet \$AAPL LONG', signal))

asyncio.run(test())
"
```

### 6. Debug Scheduler

```python
# Check scheduler state
python -c "
from src.social.scheduler import get_social_scheduler
s = get_social_scheduler()
print('Running:', s._running)
print('Jobs:', s._scheduler.get_jobs())
for job in s._scheduler.get_jobs():
    print(f'  {job.id}: {job.next_run_time}')
"
```

### 7. Common Debug Commands

```bash
# Check running processes
ps aux | grep -E "(python|node)"

# Check ports
netstat -tlnp | grep -E "(6379|8080|9090)"

# Check Docker containers
docker ps -a
docker logs stocksignals-app

# Python debugger
python -m debugpy --listen 5678 --wait-for-client -m src.main
# Then attach VS Code debugger
```

---

## Contributing

### 1. Branch Strategy

```
main                    # Production-ready
├── develop             # Integration branch
│   ├── feature/xyz     # New features
│   ├── fix/abc         # Bug fixes
│   └── docs/...        # Documentation
```

### 2. Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code restructuring
- `test`: Tests
- `chore`: Maintenance

Example:
```
feat(social): add LinkedIn poster

- Implement LinkedIn API integration
- Add rate limiting for LinkedIn
- Add platform formatter
- Update configuration schema

Closes #123
```

### 3. Pull Request Process

1. Fork repository
2. Create feature branch from `develop`
3. Make changes with tests
4. Run full test suite
5. Update documentation
6. Submit PR to `develop`
7. Code review
8. Merge after approval

### 4. Code Review Checklist

- [ ] Tests pass
- [ ] Type hints added
- [ ] Docstrings updated
- [ ] No hardcoded secrets
- [ ] Error handling implemented
- [ ] Logging added for key operations
- [ ] Configuration updated if needed
- [ ] Documentation updated

### 5. Release Process

```bash
# Version bump
# Update version in pyproject.toml / package.json

# Tag release
git tag -a v1.2.0 -m "Release v1.2.0"
git push origin v1.2.0

# CI/CD builds Docker image
# Deploy to staging
# Verify
# Deploy to production
```

---

## Architecture Decisions Log

### ADR 001: Dual Runtime (Python + Node.js)
**Date**: 2024-01
**Status**: Accepted
**Context**: Need both Discord gateway (async Python) and Messenger scraping (Playwright)
**Decision**: Use Python for Discord/API/scheduler, Node.js for Playwright
**Consequences**: Two runtimes, shared Redis for communication

### ADR 002: Redis SETNX for Deduplication
**Date**: 2024-01
**Status**: Accepted
**Context**: Need fast, atomic deduplication across multiple sources
**Decision**: Use Redis SETNX with TTL
**Consequences**: Simple, automatic expiry, single point of failure (Redis)

### ADR 003: User Token vs Bot Token (Discord)
**Date**: 2024-01
**Status**: Accepted (with ToS warning)
**Context**: Need to read messages from channels not owned
**Decision**: Use user token (self-bot) for flexibility
**Consequences**: ToS violation risk, account ban possible

### ADR 004: After-Hours Posting Window
**Date**: 2024-01
**Status**: Accepted
**Context**: Avoid spam during market hours, capture after-hours attention
**Decision**: 4PM-9:30AM ET weekdays, reduced weekends
**Consequences**: Signals delayed up to 17.5 hours

### ADR 005: Priority Queue with Redis Sorted Sets
**Date**: 2024-01
**Status**: Accepted
**Context**: Need priority-based job processing with scheduling
**Decision**: Use Redis sorted sets (ZSET) with negative priority scores
**Consequences**: O(log N) operations, no native priority queue in Redis

---

## Performance Profiling

### CPU Profiling

```bash
# Python
python -m cProfile -o profile.stats -m src.main
# Analyze: python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Node.js
node --prof src/messenger/scraper.js
# Analyze: node --prof-process isolate-*.log > processed.txt
```

### Memory Profiling

```bash
# Python
pip install memory-profiler
python -m memory_profiler src/main.py

# Node.js
node --inspect src/messenger/scraper.js
# Connect Chrome DevTools
```

### Redis Performance

```bash
# Redis INFO
redis-cli INFO memory
redis-cli INFO stats

# Slowlog
redis-cli SLOWLOG GET 10

# Latency monitoring
redis-cli --latency-history -i 1
```

---

## Useful Snippets

### Quick Signal Test

```python
# test_signal.py
from src.common.formatter import SignalFormatter

test_signals = [
    "AAPL long entry 150 target 160 stop 145",
    "TSLA short 250/230/260",
    "SPY 03/15/24 C 450 entry 5.50 target 8.00",
    "$NVDA 🚀 calls entry 450",
    "QQQ 04/19/24 P 380 buy 4.20",
]

for text in test_signals:
    signal = SignalFormatter.parse(text)
    print(f"Text: {text}")
    print(f"  Ticker: {signal.ticker}, Dir: {signal.direction}")
    print(f"  Entry: {signal.entry}, Target: {signal.target}, SL: {signal.stop_loss}")
    print(f"  Option: {signal.expiry} {signal.strike}{signal.option_type}")
    print()
```

### Manual Queue Inspection

```python
# inspect_queue.py
import asyncio
import json
from src.social.queue import get_social_queue

async def main():
    queue = await get_social_queue()
    
    # Stats
    stats = await queue.get_queue_stats()
    print("Stats:", stats)
    
    # Peek queue (without removing)
    import redis.asyncio as redis
    from src.common.config import get_settings
    s = get_settings()
    r = redis.Redis(host=s.redis.host, port=s.redis.port, decode_responses=True)
    
    jobs = await r.zrange("social:queue", 0, 9, withscores=True)
    for job_data, score in jobs:
        job = json.loads(job_data)
        print(f"Priority: {-score}, ID: {job['id']}, Platforms: {job['platforms']}")
        print(f"  Signal: {job['signal']['raw_text'][:80]}...")

asyncio.run(main())
```

### Load Test Webhook

```python
# load_test_webhook.py
import asyncio
import aiohttp
from src.common.config import get_settings

async def load_test():
    settings = get_settings()
    url = settings.webhook.url
    
    async with aiohttp.ClientSession() as session:
        tasks = []
        for i in range(100):
            payload = {
                "embeds": [{
                    "title": f"Test Signal {i}",
                    "description": "Load test",
                    "color": 0x00FF00,
                }]
            }
            tasks.append(session.post(url, json=payload))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if not isinstance(r, Exception) and r.status == 204)
        print(f"Success: {success}/100")

asyncio.run(load_test())
```

---

## Resources

### Documentation
- [Discord Gateway API](https://discord.com/developers/docs/topics/gateway)
- [Playwright Documentation](https://playwright.dev/)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [Redis Commands](https://redis.io/commands/)
- [Tweepy (Twitter API)](https://docs.tweepy.org/)
- [Stocktwits API](https://api.stocktwits.com/developers/docs/api)
- [Instagram Graph API (Threads)](https://developers.facebook.com/docs/instagram-api)
- [PRAW (Reddit)](https://praw.readthedocs.io/)
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [SendGrid API](https://docs.sendgrid.com/api-reference)

### Internal References
- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API.md)
- [Deployment Guide](DEPLOYMENT.md)
- [README](README.md)