#!/bin/bash
# Stop StockTradingSignals application

LOG_DIR="/home/bear2927/StockTradingSignals/logs"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp/stock-trading-signals-logs"
mkdir -p "$LOG_DIR" 2>/dev/null

# Stop Python application
if pgrep -f "python -m src.main" > /dev/null; then
    pkill -f "python -m src.main"
    echo "$(date): Stopped Python application" >> "$LOG_DIR/scheduler.log"
    sleep 2
else
    echo "$(date): Python application not running" >> "$LOG_DIR/scheduler.log"
fi

# Stop Node.js scraper (trade signals)
if pgrep -f "node src/messenger/scraper.js" > /dev/null; then
    pkill -f "node src/messenger/scraper.js"
    echo "$(date): Stopped Node.js scraper" >> "$LOG_DIR/scheduler.log"
    sleep 2
else
    echo "$(date): Node.js scraper not running" >> "$LOG_DIR/scheduler.log"
fi

# Stop Don Cristo scraper
if pgrep -f "node src/messenger/don_cristo_scraper.js" > /dev/null; then
    pkill -f "node src/messenger/don_cristo_scraper.js"
    echo "$(date): Stopped Don Cristo scraper" >> "$LOG_DIR/scheduler.log"
    sleep 2
else
    echo "$(date): Don Cristo scraper not running" >> "$LOG_DIR/scheduler.log"
fi
