#!/usr/bin/env python3
"""Health check endpoint for monitoring."""

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from aiohttp import web
from src.common.config import get_settings
from src.common.redis_client import get_redis


async def health_check(request):
    """Health check endpoint."""
    checks = {
        "status": "healthy",
        "service": "stocktrading-signals",
        "checks": {}
    }

    # Check Redis
    try:
        redis = await get_redis()
        await redis.client.ping()
        checks["checks"]["redis"] = "healthy"
    except Exception as e:
        checks["checks"]["redis"] = f"unhealthy: {e}"
        checks["status"] = "degraded"

    # Check config
    try:
        settings = get_settings()
        if settings.discord.user_token:
            checks["checks"]["discord_token"] = "configured"
        else:
            checks["checks"]["discord_token"] = "missing"
            checks["status"] = "degraded"

        if settings.discord.premium_webhook_url:
            checks["checks"]["webhook"] = "configured"
        else:
            checks["checks"]["webhook"] = "missing"
            checks["status"] = "degraded"
    except Exception as e:
        checks["checks"]["config"] = f"error: {e}"
        checks["status"] = "degraded"

    # Check gateway connection (would need access to gateway instance)
    checks["checks"]["gateway"] = "unknown"

    status_code = 200 if checks["status"] == "healthy" else 503
    return web.json_response(checks, status=status_code)


async def metrics(request):
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return web.Response(body=generate_latest(), content_type=CONTENT_TYPE_LATEST)


async def start_health_server():
    """Start health check server."""
    port = int(os.environ.get("HEALTH_CHECK_PORT", 8080))
    app = web.Application()
    app.router.add_get("/health", health_check)
    app.router.add_get("/metrics", metrics)
    app.router.add_get("/", lambda r: web.Response(text="StockTradingSignals - Running"))

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"🏥 Health check server running on port {port}")
    return runner


if __name__ == "__main__":
    asyncio.run(start_health_server())