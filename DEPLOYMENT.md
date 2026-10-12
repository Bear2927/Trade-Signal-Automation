# StockTradingSignals - Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Production Deployment](#production-deployment)
5. [Configuration](#configuration)
6. [Credential Setup](#credential-setup)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Scaling](#scaling)
9. [Troubleshooting](#troubleshooting)
10. [Security Hardening](#security-hardening)

---

## Prerequisites

### System Requirements

| Component | Minimum Version | Recommended |
|-----------|----------------|-------------|
| Python | 3.11+ | 3.12 |
| Node.js | 20+ | 20 LTS |
| Redis | 7+ | 7.2+ |
| Docker | 24+ | Latest |
| Docker Compose | 2.20+ | Latest |

### OS Support
- **Linux** (Ubuntu 22.04+, Debian 12+, RHEL 9+)
- **macOS** (13+ Ventura, 14+ Sonoma)
- **Windows** (WSL2 required for full functionality)

---

## Local Development Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd StockTradingSignals
```

### 2. Python Environment

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### 3. Node.js Environment

```bash
# Install Node dependencies
npm install

# Install Playwright browsers (requires system deps)
npx playwright install --with-deps chromium
```

### 4. Redis Server

**Option A: Local Redis**
```bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# macOS
brew install redis
brew services start redis

# Docker (quick)
docker run -d -p 6379:6379 redis:7-alpine
```

**Option B: Docker Compose (recommended)**
```bash
docker-compose -f docker/docker-compose.yml up -d redis
```

### 5. Configuration

```bash
# Copy example configs
cp config/config.example.yaml config/config.yaml
cp .env.example .env  # If exists

# Edit configuration
vim config/config.yaml
```

### 6. Validate Configuration

```bash
python scripts/validate_config.py
```

### 7. Run Services

**Terminal 1 - Main Application (Discord + Scheduler)**
```bash
python -m src.main
```

**Terminal 2 - Messenger Scraper**
```bash
node src/messenger/scraper.js
```

---

## Docker Deployment

### Quick Start

```bash
# Build and start all services
docker-compose -f docker/docker-compose.yml up -d --build

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Stop
docker-compose -f docker/docker-compose.yml down
```

### Services

| Service | Description | Ports |
|---------|-------------|-------|
| `redis` | Redis 7 Alpine | 6379 |
| `app` | Main Python app | - |
| `scheduler` | Social scheduler (optional) | - |
| `messenger` | Node.js Messenger scraper | - |

### Environment File

Create `.env` in project root:

```bash
# Discord
DISCORD_USER_TOKEN=your_user_token_here
DISCORD_TARGET_CHANNEL_IDS=123456789,987654321
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy

# Redis (internal Docker network)
REDIS_HOST=redis
REDIS_PORT=6379

# Messenger
MESSENGER_TARGET_CHAT_URL=https://www.facebook.com/messages/t/CHAT_ID
MESSENGER_SESSION_PATH=/app/fb_session
MESSENGER_HEADLESS=true

# Social Media (examples)
SOCIAL_TWITTER_ENABLED=true
SOCIAL_TWITTER_API_KEY=xxx
SOCIAL_TWITTER_API_SECRET=xxx
SOCIAL_TWITTER_ACCESS_TOKEN=xxx
SOCIAL_TWITTER_BEARER_TOKEN=xxx
```

### Docker Volumes

```yaml
volumes:
  - ../config:/app/config:ro          # Read-only config
  - ../logs:/app/logs                 # Application logs
  - ../fb_session:/app/fb_session     # Messenger session persistence
  - redis_data:/data                  # Redis persistence
```

### Resource Limits

```yaml
deploy:
  resources:
    limits:
      memory: 2G      # app service
      cpus: '2'
    limits:
      memory: 1G      # messenger service
      cpus: '1'
```

---

## Production Deployment

### 1. Server Preparation

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose (if not included)
sudo apt-get install docker-compose-plugin
```

### 2. Directory Structure

```bash
# Create project directory
sudo mkdir -p /opt/stocktrading-signals
cd /opt/stocktrading-signals

# Clone or copy project
git clone <repository-url> .

# Create required directories
mkdir -p config logs fb_session
```

### 3. Production Configuration

```bash
# Copy and edit production config
cp config/config.example.yaml config/config.yaml
vim config/config.yaml

# Create production .env
vim .env
```

**Production config.yaml changes:**
```yaml
redis:
  host: "redis"
  port: 6379
  password: "secure_redis_password"  # Set in docker-compose

logging:
  level: "INFO"
  format: "json"
  file: "./logs/app.log"
  max_bytes: 10485760
  backup_count: 10
```

### 4. Secure Redis

```yaml
# docker/docker-compose.yml
redis:
  command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru --requirepass ${REDIS_PASSWORD}
```

Add to `.env`:
```bash
REDIS_PASSWORD=your_secure_password_here
```

### 5. Systemd Service (Optional)

Create `/etc/systemd/system/stocktrading-signals.service`:

```ini
[Unit]
Description=StockTradingSignals
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/stocktrading-signals
ExecStart=/usr/bin/docker-compose -f docker/docker-compose.yml up -d
ExecStop=/usr/bin/docker-compose -f docker/docker-compose.yml down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable stocktrading-signals
sudo systemctl start stocktrading-signals
```

### 6. Reverse Proxy (Nginx) for Health/Metrics

```nginx
# /etc/nginx/sites-available/stocktrading-signals
server {
    listen 80;
    server_name signals.yourdomain.com;

    location /health {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
    }

    location /metrics {
        proxy_pass http://localhost:9090;
        proxy_set_header Host $host;
        # Restrict access
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        deny all;
    }
}
```

---

## Configuration

### Configuration Priority

1. **YAML file** (`config/config.yaml`) - Primary
2. **Environment variables** (`.env`) - Override
3. **Defaults** - Fallback

### Key Configuration Sections

#### Discord (Required)
```yaml
discord:
  user_token: "your_token"           # From browser devtools
  target_channel_ids:                # Channel IDs to monitor
    - "123456789012345678"
    - "987654321098765432"
  premium_webhook_url: "https://discord.com/api/webhooks/..."
```

#### Messenger (Required)
```yaml
messenger:
  target_chat_url: "https://www.facebook.com/messages/t/CHAT_ID"
  session_path: "./fb_session"
  headless: true
  proxy: "host:port:user:pass"  # Optional residential proxy
```

#### Social Media (At least one required for delayed posting)
```yaml
social:
  schedule_cron: "*/15 16-23,0-9 * * 1-5"      # Weekdays 4PM-9:30AM ET
  weekend_schedule_cron: "*/30 * * * 0,6"      # Weekends every 30min
  
  twitter:
    enabled: true
    api_key: ""
    api_secret: ""
    bearer_token: ""
    access_token: ""
    refresh_token: ""
    max_chars: 280
```

### Environment Variable Mapping

Use single underscore for nested settings:

```bash
# config.yaml: discord.user_token
DISCORD_USER_TOKEN=xxx

# config.yaml: social.twitter.api_key
SOCIAL_TWITTER_API_KEY=xxx

# config.yaml: redis.host
REDIS_HOST=redis
```

---

## Credential Setup

### Discord User Token (Required)

⚠️ **WARNING**: Using user tokens for self-bots violates Discord ToS and can lead to account ban. Use a dedicated account at your own risk.

1. Open Discord in browser (Chrome/Firefox)
2. Press F12 → Network tab
3. Filter "gateway" or "websocket"
4. Send a message or refresh page
5. Click WebSocket connection → Headers → `Authorization`
6. Copy the token value
7. Add to config: `discord.user_token`

### Facebook Messenger Session (Required)

```bash
# Run interactive setup
python scripts/setup_fb_session.py
```

Process:
1. Browser opens to Facebook Messenger
2. Log in manually (handle 2FA)
3. Navigate to target chat/group
4. Verify messages visible
5. Press Enter in terminal
6. Session saved to `./fb_session/`

### Social Media APIs (Optional)

```bash
# Run interactive OAuth setup
python scripts/setup_social_auth.py
```

Guides you through each platform:

| Platform | Setup Steps |
|----------|-------------|
| **X/Twitter** | Developer Portal → Project/App → OAuth 2.0 with PKCE → Callback: `http://localhost:8080/callback` |
| **Stocktwits** | https://api.stocktwits.com/developers/apps → Register app → Callback URL |
| **Threads** | Facebook Developers → Instagram Graph API → Business verification required |
| **Reddit** | https://www.reddit.com/prefs/apps → Create 'script' app |
| **Telegram** | Message @BotFather → `/newbot` → Get token |
| **LinkedIn** | https://www.linkedin.com/developers/ → Create App → "Share on LinkedIn" |
| **Email (SendGrid)** | https://app.sendgrid.com/settings/api_keys → Create API Key |

---

## Monitoring & Health Checks

### Health Check Endpoint

```bash
# Docker health check
curl http://localhost:8080/health

# Response
{"status": "healthy", "redis": "connected", "uptime": 3600}
```

### Prometheus Metrics

```bash
curl http://localhost:9090/metrics
```

Key metrics:
- `stocksignals_signals_processed_total` - Counter
- `stocksignals_signals_duplicated_total` - Counter
- `stocksignals_webhook_sent_total` - Counter
- `stocksignals_webhook_failed_total` - Counter
- `stocksignals_social_posted_total` - Counter by platform
- `stocksignals_queue_size` - Gauge
- `stocksignals_redis_connected` - Gauge (1/0)

### Logging

**Structured JSON logs** (default):
```json
{
  "timestamp": "2024-01-15T20:30:45.123Z",
  "level": "INFO",
  "logger": "src.discord.gateway",
  "message": "New signal detected: AAPL",
  "ticker": "AAPL",
  "source": "Discord#123"
}
```

**Log file**: `./logs/app.log` (rotating, 10MB × 5 files)

### Grafana Dashboard (Example)

Import dashboard with panels for:
- Signals per minute (rate)
- Duplicate rate
- Webhook success/failure rate
- Social posts by platform
- Queue depth
- Redis memory usage
- Gateway reconnections

---

## Scaling

### Horizontal Scaling Strategy

| Component | Scaling Approach |
|-----------|------------------|
| **Discord Gateway** | Single instance per account (Discord limit) |
| **Messenger Scraper** | Multiple instances with different sessions |
| **Scheduler** | Single leader (use distributed lock for HA) |
| **Redis** | Single → Sentinel → Cluster |
| **Webhook Sender** | Stateless, multiple instances OK |

### Docker Swarm / Kubernetes

```yaml
# docker-compose.yml for Swarm
deploy:
  replicas: 1  # gateway
  replicas: 2  # messenger (different sessions)
  replicas: 1  # scheduler (with leader election)
```

**Kubernetes considerations**:
- Use StatefulSet for Messenger (session persistence)
- Redis: Use Operator or external managed Redis
- ConfigMap for config.yaml
- Secret for .env values

### Performance Tuning

```yaml
# Redis connection pool
redis:
  max_connections: 50  # Increase for high load

# Webhook rate limit
webhook:
  rate_limit_per_second: 30  # Discord limit

# Scheduler batch size
# In scheduler.py: dequeue(count=50)  # Increase batch
```

---

## Troubleshooting

### Common Issues

#### Discord Connection Fails

```bash
# Check token validity
curl -H "Authorization: YOUR_TOKEN" https://discord.com/api/v9/users/@me

# Common errors:
# 401 - Token expired/invalid → Re-extract from browser
# 4004 - Invalid session → Token expired, use refresh callback
# Rate limited → Reduce reconnect frequency
```

#### Messenger Scraper Fails

```bash
# Session expired
python scripts/setup_fb_session.py

# Facebook detects automation
# - Use residential proxy
# - Ensure stealth plugin loaded
# - Reduce scraping frequency

# DOM selectors outdated
# Update src/messenger/selectors.py
```

#### Redis Connection Issues

```bash
# Test connection
redis-cli -h localhost -p 6379 ping

# Check Docker networking
docker-compose exec app redis-cli -h redis ping

# Common errors:
# Connection refused → Redis not running
# AUTH failed → Check password
# OOM → Increase maxmemory or reduce TTL
```

#### Social Media Posting Fails

```bash
# Check credentials
python -c "
from src.social.x_poster import get_twitter_poster
import asyncio
async def test():
    p = await get_twitter_poster()
    print(await p.initialize())
asyncio.run(test())
"

# Common errors:
# 401 - Invalid/expired tokens → Re-authenticate
# 429 - Rate limited → Check rate limiter config
# 403 - Permission denied → Check app permissions
```

#### Scheduler Not Posting

```bash
# Check timezone
# Scheduler runs in US/Eastern
# Verify cron expressions

# Check queue
redis-cli ZRANGE social:queue 0 -1 WITHSCORES

# Check dead letter
redis-cli LRANGE social:dead_letter 0 -1
```

### Debug Commands

```bash
# View all Redis keys
redis-cli KEYS "*"

# Monitor Redis commands
redis-cli MONITOR

# Check queue stats
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
```

### Log Analysis

```bash
# Follow logs
docker-compose -f docker/docker-compose.yml logs -f app

# Search for errors
grep -i error logs/app.log

# Signal flow tracking
grep "New signal detected" logs/app.log

# Deduplication stats
grep "Duplicate signal detected" logs/app.log | wc -l
```

---

## Security Hardening

### 1. Credentials Management

**Never commit secrets:**
```bash
# .gitignore
config/config.yaml
.env
fb_session/
logs/
```

**Use external secret manager:**
- AWS Secrets Manager
- HashiCorp Vault
- Doppler
- 1Password CLI

### 2. Network Security

```yaml
# docker-compose.yml - restrict ports
services:
  redis:
    # Don't expose 6379 to host
    # ports: []  # Remove port mapping
    networks:
      - internal

networks:
  internal:
    internal: true
  external:
    # For health checks only
```

### 3. Redis Security

```yaml
redis:
  command: >
    redis-server
    --appendonly yes
    --maxmemory 256mb
    --maxmemory-policy allkeys-lru
    --requirepass ${REDIS_PASSWORD}
    --bind 0.0.0.0
    --protected-mode yes
```

### 4. Container Security

```dockerfile
# Dockerfile - non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# Read-only root filesystem (if possible)
# Add to docker-compose:
# read_only: true
# tmpfs:
#   - /tmp
#   - /var/run
```

### 5. Discord Webhook Security

```python
# In production, verify webhook signatures
# Add to webhook.py:
async def verify_signature(request, signature_header):
    # Verify Discord signature
    pass
```

### 6. Regular Updates

```bash
# Update base images monthly
docker-compose pull
docker-compose build --no-cache
docker-compose up -d

# Update Python packages
pip install --upgrade -r requirements.txt
pip-audit  # Check vulnerabilities

# Update Node packages
npm audit fix
npm update
```

---

## Backup & Recovery

### Redis Backup

```bash
# Manual backup
docker-compose exec redis redis-cli BGSAVE
docker cp stocksignals-redis:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb

# Automated (cron)
0 2 * * * docker-compose exec -T redis redis-cli BGSAVE && docker cp stocksignals-redis:/data/dump.rdb /backups/redis-$(date +\%Y\%m\%d).rdb
```

### Configuration Backup

```bash
# Backup config (excluding secrets)
tar -czf config-backup-$(date +%Y%m%d).tar.gz config/config.yaml docker/
```

### Session Backup

```bash
# Messenger session
tar -czf fb_session-backup-$(date +%Y%m%d).tar.gz fb_session/
```

---

## Maintenance Checklist

### Daily
- [ ] Check health endpoint
- [ ] Review error logs
- [ ] Verify social posts published

### Weekly
- [ ] Check Redis memory usage
- [ ] Review queue depth trends
- [ ] Verify Discord gateway uptime
- [ ] Check Messenger session validity

### Monthly
- [ ] Rotate API tokens where possible
- [ ] Update Docker images
- [ ] Review and prune dead letter queue
- [ ] Check disk space (logs, Redis)
- [ ] Run security scan (`pip-audit`, `npm audit`)

### Quarterly
- [ ] Review ToS compliance
- [ ] Test disaster recovery
- [ ] Update dependencies
- [ ] Review architecture for scaling needs

---

## Rollback Procedure

```bash
# Quick rollback to previous image
docker-compose -f docker/docker-compose.yml down
docker tag stocksignals-app:latest stocksignals-app:rollback
docker-compose -f docker/docker-compose.yml up -d

# Or use specific image tag
docker-compose -f docker/docker-compose.yml up -d --build
# Specify image in compose: image: stocksignals-app:v1.2.3
```

---

## Support

### Logs Location
- Docker: `docker-compose logs -f [service]`
- Local: `./logs/app.log`

### Key Files for Debugging
- `config/config.yaml` - Configuration
- `./logs/app.log` - Application logs
- `./fb_session/` - Messenger session
- `docker-compose.yml` - Service definitions

### Getting Help
1. Check this guide's Troubleshooting section
2. Review GitHub Issues
3. Enable DEBUG logging: `logging.level: "DEBUG"`
4. Check Discord/Facebook API status pages