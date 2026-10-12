/**
 * Facebook Messenger Scraper for Don Cristo messages
 *
 * Monitors a specific Messenger chat for messages from Don Cristo
 * and posts them immediately to a Discord chatroom webhook
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

// Configuration
const CONFIG = {
  // Chat ID for Don Cristo: 1928478913911863
  targetChatUrl: 'https://www.facebook.com/messages/t/1928478913911863',
  sessionPath: process.env.MESSENGER__DONT_CRISTO_SESSION_PATH || './fb_don_cristo_session',
  headless: (process.env.MESSENGER__HEADLESS || process.env.MESSENGER_HEADLESS || 'true') !== 'false',
  proxy: process.env.MESSENGER__PROXY || process.env.MESSENGER_PROXY || '',
  redisHost: process.env.REDIS_HOST || 'localhost',
  redisPort: parseInt(process.env.REDIS_PORT) || 6379,
  redisPassword: process.env.REDIS_PASSWORD || '',
  // Chatroom webhook for Don Cristo messages
  chatroomWebhookUrl: process.env.DISCORD_CHATROOM_WEBHOOK_URL || 'https://discord.com/api/webhooks/1559282693194260612/MXQVMSqXDvFenpHjZruYFFW236lcshWgPTSLYHAhloV_TLQMRSZSlJUPAtDnXHQEoBgG',
  dedupTtl: parseInt(process.env.DEDUP_TTL || process.env.DEDUPLICATION__TTL_SECONDS) || 30,
};

const redis = new Redis({
  host: CONFIG.redisHost,
  port: CONFIG.redisPort,
  password: CONFIG.redisPassword || undefined,
  maxRetriesPerRequest: 3,
});

redis.on('error', (err) => console.error('Redis error:', err));
redis.on('connect', () => console.log('Redis connected for Don Cristo scraper'));

async function hashContent(content) {
  const crypto = require('crypto');
  return crypto.createHash('md5').update(content).digest('hex');
}

async function isDuplicate(contentHash) {
  const key = `dedup:don_cristo:${contentHash}`;
  const result = await redis.set(key, '1', 'NX', 'EX', CONFIG.dedupTtl);
  return result === null; // null means key already existed (duplicate)
}

async function sendToChatroomWebhook(content, author, imageUrl = null) {
  if (!CONFIG.chatroomWebhookUrl) {
    console.log('No chatroom webhook URL configured, skipping');
    return;
  }

  const payload = {
    username: author,
    avatar_url: '',
  };

  // If there's an image, create an embed with the message and image
  if (imageUrl) {
    payload.embeds = [{
      description: content.substring(0, 2000),
      image: {
        url: imageUrl,
      },
      color: 0x5865F2, // Discord blue
    }];
  } else {
    // Text only
    payload.content = content.substring(0, 2000);
  }

  try {
    await axios.post(CONFIG.chatroomWebhookUrl, payload, {
      headers: { 'Content-Type': 'application/json' },
      timeout: 10000,
    });
    if (imageUrl) {
      console.log(`✅ Posted to Discord chatroom: "${author}" (with image)`);
    } else {
      console.log(`✅ Posted to Discord chatroom: "${author}"`);
    }
  } catch (err) {
    console.error('Webhook error:', err.message);
  }
}

async function setupPage(page) {
  // Expose function to process messages with author detection
  await page.exposeFunction('processDonCristoMessage', async (text, author, imageUrl = null) => {
    if (!text || text.trim().length < 1) return;

    // Only process messages from Don Cristo
    if (author !== 'Don Cristo') {
      return;
    }

    console.log(`📨 Message from Macro CEO: ${text.substring(0, 50)}${imageUrl ? ' (with image)' : ''}...`);

    const contentHash = await hashContent(text + (imageUrl || ''));
    const duplicate = await isDuplicate(contentHash);
    if (duplicate) {
      console.log('⏭️  Duplicate message, skipping');
      return;
    }

    // Post immediately to Discord chatroom
    await sendToChatroomWebhook(text, 'Macro CEO', imageUrl);
  });
}

async function run() {
  console.log('Starting Don Cristo Messenger scraper...');
  console.log('Chat URL:', CONFIG.targetChatUrl);
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
    }
  }

  const context = await stealth.launchPersistentContext(CONFIG.sessionPath, launchOptions);
  const page = await context.newPage();

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

  // Wait for chat to load
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

  // Setup message processing
  await setupPage(page);

  // Inject MutationObserver to monitor new messages with author detection
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
              // Try to extract author and message from the DOM structure
              const messageText = node.innerText || node.textContent;

              // Look for author name in common Messenger DOM patterns
              let author = 'Unknown';

              // Try to find author in nearby elements
              const authorElement = node.querySelector('[data-testid="AuthorName"]') ||
                                   node.querySelector('span[aria-label*="sent by"]') ||
                                   node.querySelector('[class*="author"]');

              if (authorElement) {
                author = authorElement.textContent.trim();
              }

              // Also check parent nodes for author info
              if (author === 'Unknown' && node.parentElement) {
                const parentAuthor = node.parentElement.querySelector('[data-testid="AuthorName"]') ||
                                    node.parentElement.querySelector('span[aria-label*="sent by"]');
                if (parentAuthor) {
                  author = parentAuthor.textContent.trim();
                }
              }

              // Try to extract image from the message - improved detection for POSTED images
              let imageUrl = null;

              // Look for all images in the message node
              const allImages = node.querySelectorAll('img');

              // Sort by size (descending) to find the largest image first (likely the posted content)
              const imagesBySize = Array.from(allImages)
                .map(img => ({
                  img: img,
                  src: img.src || img.getAttribute('data-src'),
                  size: (img.width || 0) * (img.height || 0)
                }))
                .sort((a, b) => b.size - a.size);

              for (const item of imagesBySize) {
                const src = item.src;
                const img = item.img;

                // Skip if no src
                if (!src) continue;

                // Skip data URIs
                if (src.includes('data:')) continue;

                // Skip very tiny images (avatars, emojis, icons)
                if ((img.width || 0) < 100 && (img.height || 0) < 100) continue;

                // Skip images with avatar/icon/emoji-like names
                if (src.includes('avatar') || src.includes('icon') || src.includes('emoji') ||
                    src.includes('t1.6435') || src.includes('profile')) continue;

                // Found the largest suitable image candidate
                imageUrl = src;
                break;
              }

              if (messageText && messageText.trim().length > 0) {
                window.processDonCristoMessage(messageText.trim(), author, imageUrl);
              }
            }
          }
        }
      }
    };

    const observer = new MutationObserver(callback);
    observer.observe(targetNode, config);
    console.log('MutationObserver started on:', usedSelector);
    window._signalObserver = observer;
  });

  console.log('Monitoring Messenger for Don Cristo messages...');
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
