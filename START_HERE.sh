#!/bin/bash
# Quick startup script for messenger scraper

set -e

PROJECT_DIR="/home/bear2927/StockTradingSignals"
cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Stock Trading Signals - Messenger Scraper Startup         ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"
echo ""

# Check if Redis script exists
if [ ! -f "scripts/start_redis.sh" ]; then
    echo -e "${YELLOW}⚠ scripts/start_redis.sh not found${NC}"
    exit 1
fi

# Check .env file
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    exit 1
fi

# Show current configuration
CHAT_ID=$(grep MESSENGER__TARGET_CHAT_URL .env | cut -d'/' -f7 | tr -d '\r')
WEBHOOK=$(grep DISCORD_WEBHOOK_URL .env | cut -d'=' -f2 | head -c 30)...

echo -e "${GREEN}✓ Configuration Found:${NC}"
echo "  Chat ID: $CHAT_ID"
echo "  Webhook: $WEBHOOK"
echo ""

# Ask user what to do
echo "What would you like to do?"
echo "  1) Start Redis + Run scraper (recommended)"
echo "  2) Just start Redis"
echo "  3) Just run scraper"
echo "  4) Run verification tests"
echo "  5) Exit"
echo ""

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo -e "${BLUE}Starting Redis...${NC}"
        chmod +x scripts/start_redis.sh
        scripts/start_redis.sh start
        
        echo ""
        echo -e "${BLUE}Waiting for Redis to be ready...${NC}"
        sleep 3
        
        # Verify Redis
        if redis-cli ping > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Redis is ready${NC}"
        else
            echo -e "${YELLOW}⚠ Redis may not be ready yet${NC}"
        fi
        
        echo ""
        echo -e "${BLUE}Starting Messenger Scraper...${NC}"
        echo "Press Ctrl+C to stop"
        echo ""
        
        export REDIS_HOST=localhost
        export REDIS_PORT=6379
        export MESSENGER_HEADLESS=true
        
        node src/messenger/scraper.js
        ;;
        
    2)
        echo ""
        echo -e "${BLUE}Starting Redis...${NC}"
        chmod +x scripts/start_redis.sh
        scripts/start_redis.sh start
        
        echo ""
        echo "Redis is running. In another terminal, run:"
        echo "  export REDIS_HOST=localhost REDIS_PORT=6379"
        echo "  node src/messenger/scraper.js"
        ;;
        
    3)
        echo ""
        echo -e "${BLUE}Starting Messenger Scraper...${NC}"
        echo "Note: Make sure Redis is running!"
        echo "Press Ctrl+C to stop"
        echo ""
        
        export REDIS_HOST=localhost
        export REDIS_PORT=6379
        export MESSENGER_HEADLESS=true
        
        node src/messenger/scraper.js
        ;;
        
    4)
        echo ""
        echo -e "${BLUE}Running verification tests...${NC}"
        bash scripts/test_messenger_fixes.sh
        ;;
        
    5)
        echo "Goodbye!"
        exit 0
        ;;
        
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
