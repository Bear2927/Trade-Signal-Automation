#!/bin/bash
# Setup automatic Discord token refresh

APP_DIR="/home/bear2927/StockTradingSignals"

echo "=========================================="
echo "Discord Token Auto-Refresh Setup"
echo "=========================================="
echo ""
echo "This script will refresh your Discord token every 12 hours."
echo ""
echo "You need to provide your Discord credentials:"
echo ""
read -p "Discord Email: " DISCORD_EMAIL
read -sp "Discord Password: " DISCORD_PASSWORD
echo ""
echo ""

# Export credentials for the script
export DISCORD_EMAIL="$DISCORD_EMAIL"
export DISCORD_PASSWORD="$DISCORD_PASSWORD"

# Test the refresh
echo "Testing token refresh..."
cd "$APP_DIR"
source .venv/bin/activate
python scripts/refresh_discord_token.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Token refresh successful!"
    echo ""
    echo "Setting up cron job for automatic refresh every 12 hours..."
    
    # Store credentials securely in a dotenv file (not in git)
    cat > "$APP_DIR/.env.discord" << ENVEOF
export DISCORD_EMAIL="$DISCORD_EMAIL"
export DISCORD_PASSWORD="$DISCORD_PASSWORD"
ENVEOF
    
    chmod 600 "$APP_DIR/.env.discord"
    
    # Create cron job
    CRON_CMD="0 */12 * * * cd $APP_DIR && source .env.discord && source .venv/bin/activate && python scripts/refresh_discord_token.py >> /tmp/discord_token_refresh.log 2>&1"
    
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    
    echo "✅ Cron job configured to refresh token every 12 hours"
    echo ""
    echo "Token refresh log: /tmp/discord_token_refresh.log"
else
    echo ""
    echo "❌ Token refresh failed. Check credentials and try again."
fi
