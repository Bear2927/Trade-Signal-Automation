#!/usr/bin/env python3
"""Generate .env file from config.yaml for Docker."""

import yaml
from pathlib import Path

def generate_env():
    config_path = Path("config/config.yaml")
    env_path = Path(".env")

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    lines = [
        "# StockTradingSignals Environment Variables",
        "# Auto-generated from config.yaml - DO NOT EDIT MANUALLY",
        f"# Run: python scripts/generate_env.py to regenerate",
        "",
    ]

    # Discord
    d = config.get("discord", {})
    lines.append("# Discord")
    lines.append(f"DISCORD_USER_TOKEN={d.get('user_token', '')}")
    lines.append(f"DISCORD_TARGET_CHANNEL_IDS={','.join(d.get('target_channel_ids', []))}")
    lines.append(f"DISCORD_PREMIUM_WEBHOOK_URL={d.get('premium_webhook_url', '')}")
    lines.append("")

    # Messenger
    m = config.get("messenger", {})
    lines.append("# Facebook Messenger")
    lines.append(f"MESSENGER_TARGET_CHAT_URL={m.get('target_chat_url', 'https://www.facebook.com/messages/t/')}")
    lines.append(f"MESSENGER_SESSION_PATH=/app/fb_session")
    lines.append(f"MESSENGER_HEADLESS={str(m.get('headless', True)).lower()}")
    lines.append(f"MESSENGER_PROXY={m.get('proxy', '')}")
    lines.append("")

    # Redis
    r = config.get("redis", {})
    lines.append("# Redis")
    lines.append(f"REDIS_HOST={r.get('host', 'redis')}")
    lines.append(f"REDIS_PORT={r.get('port', 6379)}")
    lines.append(f"REDIS_DB={r.get('db', 0)}")
    lines.append(f"REDIS_PASSWORD={r.get('password', '')}")
    lines.append(f"REDIS_MAX_CONNECTIONS={r.get('max_connections', 20)}")
    lines.append("")

    # Deduplication
    dedup = config.get("deduplication", {})
    lines.append("# Deduplication")
    lines.append(f"DEDUP_TTL={dedup.get('ttl_seconds', 30)}")
    lines.append("")

    # Webhook
    w = config.get("webhook", {})
    lines.append("# Discord Webhook")
    lines.append(f"DISCORD_WEBHOOK_URL={w.get('url', '')}")
    lines.append("")

    # Social Media
    s = config.get("social", {})
    lines.append("# Social Media - Twitter/X")
    tw = s.get("twitter", {})
    lines.append(f"TWITTER_ENABLED={str(tw.get('enabled', False)).lower()}")
    lines.append(f"TWITTER_API_KEY={tw.get('api_key', '')}")
    lines.append(f"TWITTER_API_SECRET={tw.get('api_secret', '')}")
    lines.append(f"TWITTER_BEARER_TOKEN={tw.get('bearer_token', '')}")
    lines.append(f"TWITTER_ACCESS_TOKEN={tw.get('access_token', '')}")
    lines.append(f"TWITTER_REFRESH_TOKEN={tw.get('refresh_token', '')}")
    lines.append("")

    lines.append("# Social Media - Stocktwits")
    st = s.get("stocktwits", {})
    lines.append(f"STOCKTWITS_ENABLED={str(st.get('enabled', False)).lower()}")
    lines.append(f"STOCKTWITS_CLIENT_ID={st.get('client_id', '')}")
    lines.append(f"STOCKTWITS_CLIENT_SECRET={st.get('client_secret', '')}")
    lines.append(f"STOCKTWITS_ACCESS_TOKEN={st.get('access_token', '')}")
    lines.append("")

    lines.append("# Social Media - Threads")
    th = s.get("threads", {})
    lines.append(f"THREADS_ENABLED={str(th.get('enabled', False)).lower()}")
    lines.append(f"THREADS_APP_ID={th.get('app_id', '')}")
    lines.append(f"THREADS_APP_SECRET={th.get('app_secret', '')}")
    lines.append(f"THREADS_USER_ACCESS_TOKEN={th.get('user_access_token', '')}")
    lines.append("")

    lines.append("# Social Media - Reddit")
    rd = s.get("reddit", {})
    lines.append(f"REDDIT_ENABLED={str(rd.get('enabled', False)).lower()}")
    lines.append(f"REDDIT_CLIENT_ID={rd.get('client_id', '')}")
    lines.append(f"REDDIT_CLIENT_SECRET={rd.get('client_secret', '')}")
    lines.append(f"REDDIT_REFRESH_TOKEN={rd.get('refresh_token', '')}")
    lines.append("")

    lines.append("# Social Media - Telegram")
    tg = s.get("telegram", {})
    lines.append(f"TELEGRAM_ENABLED={str(tg.get('enabled', False)).lower()}")
    lines.append(f"TELEGRAM_BOT_TOKEN={tg.get('bot_token', '')}")
    lines.append(f"TELEGRAM_CHAT_IDS={','.join(tg.get('chat_ids', []))}")
    lines.append("")

    lines.append("# Social Media - LinkedIn")
    li = s.get("linkedin", {})
    lines.append(f"LINKEDIN_ENABLED={str(li.get('enabled', False)).lower()}")
    lines.append(f"LINKEDIN_CLIENT_ID={li.get('client_id', '')}")
    lines.append(f"LINKEDIN_CLIENT_SECRET={li.get('client_secret', '')}")
    lines.append(f"LINKEDIN_ACCESS_TOKEN={li.get('access_token', '')}")
    lines.append("")

    lines.append("# Social Media - Email (SendGrid)")
    em = s.get("email", {})
    lines.append(f"EMAIL_ENABLED={str(em.get('enabled', False)).lower()}")
    lines.append(f"SENDGRID_API_KEY={em.get('sendgrid_api_key', '')}")
    lines.append(f"EMAIL_FROM_EMAIL={em.get('from_email', '')}")
    lines.append(f"EMAIL_SUBSCRIBER_LIST_ID={em.get('subscriber_list_id', '')}")
    lines.append("")

    # Logging
    lg = config.get("logging", {})
    lines.append("# Logging")
    lines.append(f"LOG_LEVEL={lg.get('level', 'INFO')}")
    lines.append(f"LOG_FORMAT={lg.get('format', 'json')}")
    lines.append(f"LOG_FILE=/app/logs/app.log")
    lines.append("")

    # Monitoring
    mon = config.get("monitoring", {})
    lines.append("# Monitoring")
    lines.append(f"PROMETHEUS_PORT={mon.get('prometheus_port', 9090)}")
    lines.append(f"HEALTH_CHECK_PORT={mon.get('health_check_port', 8080)}")

    env_path.write_text("\n".join(lines))
    print(f"✅ Generated {env_path}")

if __name__ == "__main__":
    generate_env()