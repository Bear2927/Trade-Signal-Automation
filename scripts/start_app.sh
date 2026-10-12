#!/bin/bash
# Start StockTradingSignals application

APP_DIR="/home/bear2927/StockTradingSignals"
LOG_DIR="$APP_DIR/logs"
VENV="$APP_DIR/.venv"

# Create log directory if it doesn't exist
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="/tmp/stock-trading-signals-logs"
mkdir -p "$LOG_DIR" 2>/dev/null

# Change to app directory
cd "$APP_DIR" || exit 1

# Start Python application if not already running
if ! pgrep -f "python -m src.main" > /dev/null; then
    source "$VENV/bin/activate"
    nohup python -m src.main >> "$LOG_DIR/app.log" 2>&1 &
    echo "$(date): Started Python application (PID: $!)" >> "$LOG_DIR/scheduler.log"
else
    echo "$(date): Python application already running" >> "$LOG_DIR/scheduler.log"
fi

# Start Node.js scraper (trade signals) if not already running
if ! pgrep -f "node src/messenger/scraper.js" > /dev/null; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nohup node src/messenger/scraper.js >> "$LOG_DIR/scraper.log" 2>&1 &
    echo "$(date): Started Node.js scraper (PID: $!)" >> "$LOG_DIR/scheduler.log"
else
    echo "$(date): Node.js scraper already running" >> "$LOG_DIR/scheduler.log"
fi

# Start Don Cristo scraper if not already running
if ! pgrep -f "node src/messenger/don_cristo_scraper.js" > /dev/null; then
    export NVM_DIR="$HOME/.nvm"
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
    nohup node src/messenger/don_cristo_scraper.js >> "$LOG_DIR/don_cristo_scraper.log" 2>&1 &
    echo "$(date): Started Don Cristo scraper (PID: $!)" >> "$LOG_DIR/scheduler.log"
else
    echo "$(date): Don Cristo scraper already running" >> "$LOG_DIR/scheduler.log"
fi
