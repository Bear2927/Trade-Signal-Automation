#!/bin/bash
# Test script to verify messenger scraper fixes

set -e

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)

echo "========================================"
echo "Messenger Scraper - Fix Verification"
echo "========================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

pass_test() {
    echo -e "${GREEN}✓${NC} $1"
}

fail_test() {
    echo -e "${RED}✗${NC} $1"
    exit 1
}

warn_test() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Test 1: Check Node.js syntax
echo "Test 1: Checking Node.js syntax..."
if command -v node &> /dev/null; then
    if node -c src/messenger/scraper.js 2>/dev/null; then
        pass_test "Syntax is valid"
    else
        fail_test "Syntax error in scraper.js"
    fi
else
    warn_test "Node.js not found, skipping syntax check"
fi
echo ""

# Test 2: Verify proxy parsing fix
echo "Test 2: Checking proxy parsing implementation..."
if grep -q "parts.length >= 2" src/messenger/scraper.js; then
    pass_test "Proxy parsing validation added"
else
    fail_test "Proxy parsing fix not found"
fi

if grep -q "Invalid proxy format" src/messenger/scraper.js; then
    pass_test "Proxy error message added"
else
    fail_test "Proxy error message not found"
fi
echo ""

# Test 3: Verify selector iteration for waitForSelector
echo "Test 3: Checking waitForSelector fix..."
if grep -q "for (const selector of selectors)" src/messenger/scraper.js; then
    pass_test "Selector iteration for waitForSelector implemented"
else
    fail_test "waitForSelector fix not found"
fi

if grep -q "Found message container with selector" src/messenger/scraper.js; then
    pass_test "Selector feedback logging added"
else
    fail_test "Selector feedback logging not found"
fi
echo ""

# Test 4: Verify querySelector fix in page context
echo "Test 4: Checking querySelector fix..."
if grep -q "let usedSelector = null" src/messenger/scraper.js; then
    pass_test "usedSelector tracking variable added"
else
    fail_test "usedSelector variable not found"
fi

if grep -q "console.log('MutationObserver started on:', usedSelector)" src/messenger/scraper.js; then
    pass_test "MutationObserver logging uses correct variable"
else
    fail_test "MutationObserver logging not fixed"
fi
echo ""

# Test 5: Check .env configuration
echo "Test 5: Checking environment configuration..."
if [ -f ".env" ]; then
    pass_test ".env file exists"

    if grep -q "MESSENGER__TARGET_CHAT_URL" .env || grep -q "MESSENGER_TARGET_CHAT_URL" .env; then
        pass_test "Messenger URL configured"
    else
        warn_test "Messenger URL not configured in .env"
    fi
else
    warn_test ".env file not found"
fi
echo ""

# Test 6: Check Facebook session
echo "Test 6: Checking Facebook session..."
if [ -d "./fb_session" ]; then
    pass_test "Facebook session directory exists"

    if [ -f "./fb_session/Local State" ]; then
        pass_test "Session appears to be initialized"
    else
        warn_test "Session directory exists but may not be initialized"
    fi
else
    warn_test "Facebook session directory not found - will need to run setup_fb_session.py"
fi
echo ""

# Test 7: Check dependencies
echo "Test 7: Checking Node.js dependencies..."
MISSING_DEPS=0
for dep in playwright playwright-extra puppeteer-extra-plugin-stealth axios ioredis dotenv; do
    if [ -d "node_modules/$dep" ]; then
        pass_test "$dep is installed"
    else
        fail_test "$dep is missing (run: npm install)"
        MISSING_DEPS=1
    fi
done
echo ""

# Test 8: Check Python dependencies
echo "Test 8: Checking Python dependencies..."
if command -v python &> /dev/null; then
    source .venv/bin/activate 2>/dev/null || true
    python -c "import redis; print('redis')" &> /dev/null && pass_test "Python redis module installed" || fail_test "Python redis module missing"
else
    warn_test "Python not found"
fi
echo ""

echo "========================================"
echo "Fix Verification Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "1. Start Redis: docker run -d -p 6379:6379 redis:7-alpine"
echo "2. (Optional) Re-authenticate: python scripts/setup_fb_session.py"
echo "3. Run scraper: node src/messenger/scraper.js"
echo ""
