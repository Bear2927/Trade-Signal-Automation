#!/bin/bash
# Alternative startup for WSL environment

PROJECT_DIR="/home/bear2927/StockTradingSignals"
cd "$PROJECT_DIR"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     Stock Trading Signals - WSL Startup Helper               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Check if Windows node is available
if command -v node.exe &> /dev/null; then
    NODE_CMD="node.exe"
    echo "✓ Found Windows Node.js"
elif command -v node &> /dev/null; then
    NODE_CMD="node"
    echo "✓ Found Linux Node.js"
else
    echo "✗ Node.js not found in WSL PATH"
    echo ""
    echo "Solution 1: Add Windows Node to PATH:"
    echo "  export PATH=\"/mnt/c/Program Files/nodejs:\$PATH\""
    echo ""
    echo "Solution 2: Install Node.js in WSL (requires apt):"
    echo "  curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "  sudo apt-get install -y nodejs"
    echo ""
    exit 1
fi

echo ""
echo "Project: $PROJECT_DIR"
echo "Chat ID: 1929174430523823"
echo ""
echo "Starting Messenger Scraper..."
echo "Press Ctrl+C to stop"
echo ""

# Set environment
export REDIS_HOST=localhost
export REDIS_PORT=6379
export MESSENGER_HEADLESS=true

# Run with found node
$NODE_CMD src/messenger/scraper.js
