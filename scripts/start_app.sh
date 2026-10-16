#!/bin/bash
# Start StockTradingSignals application

APP_DIR="/home/bear2927/StockTradingSignals"
LOG_FILE="/tmp/stock_trading_startup.log"
VENV="$APP_DIR/.venv"

# Change to app directory
cd "$APP_DIR" || exit 1

# Load environment variables
if [ -f "$APP_DIR/.env.local" ]; then
    export $(cat "$APP_DIR/.env.local" | grep -v '^#' | xargs)
fi

# Activate virtual environment
source "$VENV/bin/activate"

# Step 1: Refresh Discord token
echo "$(date): Refreshing Discord token..." >> "$LOG_FILE"
python scripts/refresh_discord_token.py >> "$LOG_FILE" 2>&1
echo "$(date): Discord token refresh completed" >> "$LOG_FILE"

# Step 2: Validate/refresh Messenger session
echo "$(date): Validating Messenger session..." >> "$LOG_FILE"
python scripts/validate_messenger_session.py >> "$LOG_FILE" 2>&1
MESSENGER_RESULT=$?
if [ $MESSENGER_RESULT -eq 0 ]; then
    echo "$(date): Messenger session validated/refreshed successfully" >> "$LOG_FILE"
else
    echo "$(date): Messenger session validation had issues (continuing without it)" >> "$LOG_FILE"
fi

# Step 3: Start Python application if not already running
if ! pgrep -u "$(id -u)" -f "python -m src.main" > /dev/null; then
    echo "$(date): Starting Python application..." >> "$LOG_FILE"
    nohup python -m src.main > /tmp/stock_app.log 2>&1 &
    echo "$(date): Started Python application (PID: $!)" >> "$LOG_FILE"
else
    echo "$(date): Python application already running" >> "$LOG_FILE"
fi

# Start one Messenger scraper per chat configured in config/config.yaml.
# A single implementation handles every thread; each gets its own browser
# session directory because Chrome locks a profile to one process.
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

CHATS=$(python - <<'PYEOF'
import yaml
cfg = yaml.safe_load(open('config/config.yaml')) or {}
for ch in (cfg.get('messenger') or {}).get('chats') or []:
    print("%s\t%s" % (ch['id'], ch.get('session', './fb_session')))
PYEOF
)

if [ -z "$CHATS" ]; then
    echo "$(date): No messenger.chats configured, nothing to scrape" >> "$LOG_FILE"
fi

while IFS=$'\t' read -r CHAT_ID SESSION; do
    [ -z "$CHAT_ID" ] && continue
    if pgrep -u "$(id -u)" -f "scraper.js --chat $CHAT_ID" > /dev/null; then
        echo "$(date): Scraper for chat $CHAT_ID already running" >> "$LOG_FILE"
        continue
    fi
    nohup node src/messenger/scraper.js --chat "$CHAT_ID" --session "$SESSION" \
        > "/tmp/stock_scraper_$CHAT_ID.log" 2>&1 &
    echo "$(date): Started scraper for chat $CHAT_ID session $SESSION (PID: $!)" >> "$LOG_FILE"
done <<< "$CHATS"

echo "$(date): StockTradingSignals startup complete" >> "$LOG_FILE"
