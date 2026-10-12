"""Main entry point for StockTradingSignals."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.common.config import get_settings, load_config_from_yaml
from src.common.redis_client import get_redis, close_redis
from src.common.webhook import get_webhook_sender, close_webhook_sender
from src.discord.gateway import DiscordGateway
from src.social.scheduler import start_scheduler, stop_scheduler

# Configure logging
def setup_logging():
    settings = get_settings()
    log_format = settings.logging.format
    log_level = getattr(logging, settings.logging.level.upper())

    if log_format == "json":
        import structlog
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer()
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(settings.logging.file) if settings.logging.file else logging.NullHandler(),
        ]
    )


async def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("StockTradingSignals Starting")
    logger.info("=" * 60)

    # Load config from YAML
    load_config_from_yaml("config/config.yaml")
    settings = get_settings()

    # Initialize Redis
    redis = await get_redis()
    logger.info("Redis connected")

    # Initialize webhook
    webhook = await get_webhook_sender()
    logger.info("Webhook sender initialized")

    # Start social scheduler
    await start_scheduler()
    logger.info("Social scheduler started")

    # Start Discord gateway
    gateway = DiscordGateway()

    # Token refresh callback - reloads from config.yaml
    def refresh_token_callback():
        load_config_from_yaml("config/config.yaml")
        return get_settings().discord.user_token

    def auth_failure_callback():
        logger.warning("Auth failure detected - will attempt token refresh on next reconnect")

    gateway.set_token_refresh_callback(refresh_token_callback)
    gateway.set_auth_failure_callback(auth_failure_callback)

    # Handle shutdown signals
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown_event.set()

    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal_handler)

    # Run gateway (this blocks until shutdown)
    try:
        gateway_task = asyncio.create_task(gateway.connect())
        await shutdown_event.wait()
        logger.info("Shutdown signal received, stopping...")
        await gateway.close()
        gateway_task.cancel()
        try:
            await gateway_task
        except asyncio.CancelledError:
            pass
    except Exception as e:
        logger.error(f"Gateway error: {e}")
        raise
    finally:
        # Cleanup
        await stop_scheduler()
        await close_webhook_sender()
        await close_redis()
        logger.info("StockTradingSignals stopped")


if __name__ == "__main__":
    asyncio.run(main())