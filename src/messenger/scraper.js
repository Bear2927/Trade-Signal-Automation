/**
 * Facebook Messenger Scraper using Playwright with Stealth
 *
 * This runs as a Node.js script to leverage Playwright's stealth capabilities
 * and MutationObserver for real-time DOM monitoring.
 */

const { chromium } = require('playwright');
const { addExtra } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const axios = require('axios');
const Redis = require('ioredis');
require('dotenv').config();

// Add stealth plugin to playwright
const stealth = addExtra(chromium);
stealth.use(StealthPlugin());

// Configuration from environment (supports both single and double underscore for compatibility)
const CONFIG = {
  targetChatUrl: process.env.MESSENGER__TARGET_CHAT_URL || process.env.MESSENGER_TARGET_CHAT_URL || 'https://www.facebook.com/messages/t/',
  sessionPath: process.env.MESSENGER__SESSION_PATH || process.env.MESSENGER_SESSION_PATH || './fb_session',
  headless: (process.env.MESSENGER__HEADLESS || process.env.MESSENGER_HEADLESS || 'true') !== 'false',
  proxy: process.env.MESSENGER__PROXY || process.env.MESSENGER_PROXY || '',
  redisHost: process.env.REDIS_HOST || 'localhost',
  redisPort: parseInt(process.env.REDIS_PORT) || 6379,
  redisPassword: process.env.REDIS_PASSWORD || '',
  webhookUrl: process.env.DISCORD_WEBHOOK_URL || '',
  dedupTtl: parseInt(process.env.DEDUP_TTL || process.env.DEDUPLICATION__TTL_SECONDS) || 30,
};

const redis = new Redis({
  host: CONFIG.redisHost,
  port: CONFIG.redisPort,
  password: CONFIG.redisPassword || undefined,
  maxRetriesPerRequest: 3,
});

redis.on('error', (err) => console.error('Redis error:', err));
redis.on('connect', () => console.log('Redis connected'));

async function hashContent(content) {
  const crypto = require('crypto');
  return crypto.createHash('md5').update(content).digest('hex');
}

async function isDuplicate(contentHash) {
  const key = `dedup:signal:${contentHash}`;
  const result = await redis.set(key, '1', 'NX', 'EX', CONFIG.dedupTtl);
  return result === null; // null means key already existed (duplicate)
}

async function sendToWebhook(content, author, source) {
  if (!CONFIG.webhookUrl) {
    console.log('No webhook URL configured, skipping');
    return;
  }

  const payload = {
    embeds: [{
      title: `📈 Trade signal from MacroPulse CEO`,
      description: content.substring(0, 4096),
      color: 0x00FF00,
    }],
  };

  try {
    await axios.post(CONFIG.webhookUrl, payload, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });
    console.log('Signal sent to Discord webhook');
  } catch (err) {
    console.error('Webhook error:', err.message);
  }
}

async function queueForSocial(signalData) {
  await redis.lpush('social:queue', JSON.stringify({
    signal: signalData,
    source: 'messenger',
    timestamp: Date.now(),
  }));
}

function parseSignal(text) {
  const signal = { rawText: text };
  const textLower = text.toLowerCase();

  // Ticker extraction
  const tickerMatch = text.match(/\$?([A-Z]{1,5})\b/);
  const falsePositives = new Set(['THE', 'AND', 'FOR', 'ARE', 'YOU', 'THIS', 'THAT', 'WITH', 'FROM', 'HAVE', 'BEEN', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'WHEN', 'WHERE', 'WHAT', 'WHY', 'HOW', 'ALL', 'ANY', 'SOME', 'ONE', 'TWO', 'NEW', 'OLD', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'VOL', 'VOLUME', 'PRICE', 'TRADE', 'SIGNAL', 'ALERT', 'UPDATE', 'ENTRY', 'EXIT', 'TARGET', 'STOP', 'LOSS', 'GAIN', 'PROFIT', 'RISK', 'REWARD', 'SPY', 'QQQ', 'IWM', 'DIA', 'VIX', 'UVXY', 'SVXY', 'TLT', 'GLD', 'SLV', 'USO', 'UNG', 'XLE', 'XLF', 'XLK', 'XLI', 'XLP', 'XLU', 'XLV', 'XLY']);
  if (tickerMatch && !falsePositives.has(tickerMatch[1]) && tickerMatch[1].length <= 5) {
    signal.ticker = tickerMatch[1];
  }

  // Direction
  const longKeywords = ['long', 'buy', 'bullish', 'calls', 'call', 'going up', 'moon', '🚀', '📈'];
  const shortKeywords = ['short', 'sell', 'bearish', 'puts', 'put', 'going down', 'tank', '📉', '🔻'];
  for (const kw of longKeywords) {
    if (textLower.includes(kw)) { signal.direction = 'LONG'; break; }
  }
  if (!signal.direction) {
    for (const kw of shortKeywords) {
      if (textLower.includes(kw)) { signal.direction = 'SHORT'; break; }
    }
  }

  // Prices
  const prices = text.match(/\$?(\d+(?:\.\d+)?)\s*[kK]?\b/g);
  if (prices) {
    const priceVals = prices.map(p => parseFloat(p.replace('$', '')));
    if (priceVals.length >= 1) signal.entry = priceVals[0];
    if (priceVals.length >= 2) signal.target = priceVals[1];
    if (priceVals.length >= 3) signal.stopLoss = priceVals[2];
  }

  // Options
  const optionMatch = text.match(/(\d{1,2}\/\d{1,2}(?:\/\d{2,4})?)\s*([CPcp])\s*(\d+(?:\.\d+)?)/);
  if (optionMatch) {
    signal.expiry = optionMatch[1];
    signal.optionType = optionMatch[2].toUpperCase();
    signal.strike = parseFloat(optionMatch[3]);
  }

  return signal;
}

async function setupPage(page) {
  // Expose function to send signals from page context
  await page.exposeFunction('broadcastSignal', async (text) => {
    if (!text || text.trim().length < 10) return;

    // Validate trade format: TICKER MMMDD STRIKEC/P ENTRY s/l STOPLOSS pt PROFITTARGET
    // Example: MDB OCT16 425C 1.25 s/l 0.70 pt 2.10
    const tradeFormatPattern = /^([A-Z]{1,5})\s+([A-Z]{3}\d{1,2})\s+(\d+)\s*([CP])\s+([\d.]+)\s+s\/l\s+([\d.]+)\s+pt\s+([\d.]+)/i;
    const tradeMatch = text.match(tradeFormatPattern);

    if (!tradeMatch) {
      console.log('Message does not match trade format, skipping:', text.substring(0, 50));
      return;
    }

    const contentHash = await hashContent(text);
    const duplicate = await isDuplicate(contentHash);
    if (duplicate) return;

    const signal = parseSignal(text);
    console.log('✅ Valid trade detected:', signal.ticker, '-', text.substring(0, 100));

    // Send immediately to Discord
    await sendToWebhook(text, 'Trading Desk', 'Trading Signal');

    // Queue for social media
    await queueForSocial(signal);
  });
}

async function run() {
  console.log('Starting Facebook Messenger scraper...');
  console.log('Session path:', CONFIG.sessionPath);
  console.log('Headless:', CONFIG.headless);

  const launchOptions = {
    headless: CONFIG.headless,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
    ],
  };

  if (CONFIG.proxy) {
    const parts = CONFIG.proxy.split(':');
    if (parts.length >= 2) {
      const host = parts[0];
      const port = parts[1];
      const user = parts[2] || undefined;
      const pass = parts[3] || undefined;

      const proxyConfig = { server: `http://${host}:${port}` };
      if (user && pass) {
        proxyConfig.username = user;
        proxyConfig.password = pass;
      }
      launchOptions.proxy = proxyConfig;
      console.log(`Proxy configured: ${host}:${port}${user ? ' (with auth)' : ''}`);
    } else {
      console.warn('Invalid proxy format. Expected: host:port or host:port:user:pass');
    }
  }

  const context = await stealth.launchPersistentContext(CONFIG.sessionPath, launchOptions);
  const page = await context.newPage();

  // Stealth is automatically applied via playwright-extra

  // Navigate to Messenger
  console.log('Navigating to Messenger...');
  await page.goto(CONFIG.targetChatUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  // Check if we were redirected to login
  const currentUrl = page.url();
  if (currentUrl.includes('/login') || currentUrl.includes('/checkpoint') || currentUrl.includes('/reauth')) {
    console.error('SESSION EXPIRED: Redirected to login page. Please re-run setup_fb_session.py to re-authenticate.');
    console.error('Current URL:', currentUrl);
    await context.close();
    process.exit(1);
  }

  // Wait for chat to load - try selectors individually
  const selectors = ['div[role="grid"]', 'div[aria-label="Messages"]', '[data-testid="message_thread"]'];
  let containerFound = false;
  for (const selector of selectors) {
    try {
      await page.waitForSelector(selector, { timeout: 10000 });
      containerFound = true;
      console.log(`Found message container with selector: ${selector}`);
      break;
    } catch (e) {
      // Try next selector
    }
  }
  if (!containerFound) {
    console.log('Warning: Could not find message container, continuing...');
  }

  // Setup signal broadcasting
  await setupPage(page);

  // Inject MutationObserver to monitor new messages
  await page.evaluate(() => {
    const selectors = ['div[role="grid"]', 'div[aria-label="Messages"]', '[data-testid="message_thread"]'];
    let targetNode = null;
    let usedSelector = null;

    for (const selector of selectors) {
      targetNode = document.querySelector(selector);
      if (targetNode) {
        usedSelector = selector;
        console.log(`Using selector for MutationObserver: ${selector}`);
        break;
      }
    }

    if (!targetNode) {
      console.log('Message container not found');
      return;
    }

    const config = { childList: true, subtree: true, characterData: true };

    const callback = (mutationsList) => {
      for (const mutation of mutationsList) {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
          for (const node of mutation.addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE) {
              const text = node.innerText || node.textContent;
              if (text && text.trim().length > 10) {
                window.broadcastSignal(text.trim());
              }
            }
          }
        } else if (mutation.type === 'characterData') {
          const text = mutation.target.textContent;
          if (text && text.trim().length > 10) {
            window.broadcastSignal(text.trim());
          }
        }
      }
    };

    const observer = new MutationObserver(callback);
    observer.observe(targetNode, config);
    console.log('MutationObserver started on:', usedSelector);

    // Store observer globally to prevent garbage collection
    window._signalObserver = observer;
  });

  console.log('Monitoring Messenger for trade signals...');
  console.log('Press Ctrl+C to stop');

  // Keep running
  process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    await context.close();
    await redis.quit();
    process.exit(0);
  });
}

run().catch(console.error);