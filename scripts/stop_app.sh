#!/bin/bash
# Stop StockTradingSignals application

LOG_FILE="/tmp/stock_trading_shutdown.log"

# Stop Python application
if pgrep -u "$(id -u)" -f "python -m src.main" > /dev/null; then
    pkill -u "$(id -u)" -f "python -m src.main"
    echo "$(date): Stopped Python application" >> "$LOG_FILE"
    sleep 2
else
    echo "$(date): Python application not running" >> "$LOG_FILE"
fi

# Stop every Messenger scraper instance. The pattern matches all of them
# because each runs as: node src/messenger/scraper.js --chat <id> --session <dir>
if pgrep -u "$(id -u)" -f "src/messenger/scraper.js" > /dev/null; then
    COUNT=$(pgrep -u "$(id -u)" -cf "src/messenger/scraper.js")
    pkill -u "$(id -u)" -f "src/messenger/scraper.js"
    echo "$(date): Stopped $COUNT Messenger scraper(s)" >> "$LOG_FILE"
    sleep 2
else
    echo "$(date): No Messenger scrapers running" >> "$LOG_FILE"
fi

# Legacy single-purpose scraper, superseded by scraper.js --chat
if pgrep -u "$(id -u)" -f "src/messenger/don_cristo_scraper.js" > /dev/null; then
    pkill -u "$(id -u)" -f "src/messenger/don_cristo_scraper.js"
    echo "$(date): Stopped legacy don_cristo scraper" >> "$LOG_FILE"
    sleep 2
fi

echo "$(date): StockTradingSignals stopped" >> "$LOG_FILE"
