#!/bin/bash
# Setup cron jobs for automatic scheduling
# Stock trading hours: 9:30 AM - 8:00 PM ET (Eastern Time)
# System timezone: America/Chicago (CDT/CST) - 1 hour behind ET
# Adjusted times: 8:00 AM - 7:00 PM CT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRON_START="0 8 * * 1-5 $SCRIPT_DIR/start_app.sh"
CRON_STOP="0 19 * * 1-5 $SCRIPT_DIR/stop_app.sh"

# Get current crontab or create empty one
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# Check if jobs already exist
if echo "$CURRENT_CRON" | grep -q "start_app.sh"; then
    echo "Cron jobs already configured"
    crontab -l 2>/dev/null | grep -E "start_app|stop_app"
    exit 0
fi

# Add new jobs
(echo "$CURRENT_CRON"; echo ""; echo "# StockTradingSignals - Auto start/stop"; echo "$CRON_START"; echo "$CRON_STOP") | crontab -

echo "✓ Cron jobs configured successfully!"
echo ""
echo "Start job: $CRON_START"
echo "Stop job:  $CRON_STOP"
echo ""
echo "Schedule:"
echo "  - Monday-Friday at 8:00 AM CT (9:00 AM ET): Start application"
echo "  - Monday-Friday at 7:00 PM CT (8:00 PM ET): Stop application"
echo ""
echo "Current crontab:"
crontab -l
