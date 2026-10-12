/**
 * Facebook Messenger Session Setup (Node.js version)
 * Uses the same Playwright setup as the scraper for consistency.
 */

const { chromium } = require('playwright');
const { addExtra } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const fs = require('fs');
const path = require('path');
const readline = require('readline');

// Add stealth plugin
const stealth = addExtra(chromium);
stealth.use(StealthPlugin());

// Configuration
const SESSION_PATH = process.env.MESSENGER__SESSION_PATH || process.env.MESSENGER_SESSION_PATH || './fb_session';
const TARGET_CHAT_URL = process.env.MESSENGER__TARGET_CHAT_URL || process.env.MESSENGER_TARGET_CHAT_URL || 'https://www.facebook.com/messages/t/1929174430523823';
const IS_HEADLESS = process.env.HEADLESS === 'true';

// Check if we have a TTY for interactive input
const HAS_TTY = process.stdin.isTTY;

let rl;
if (!IS_HEADLESS && HAS_TTY) {
  rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });
}

function question(prompt) {
  if (IS_HEADLESS || !HAS_TTY) {
    console.log(prompt);
    console.log('Running in non-interactive mode - waiting 180 seconds for manual login...');
    console.log('Complete login in the browser window, then wait for timeout.');
    return new Promise(resolve => setTimeout(resolve, 180000));
  }
  return new Promise(resolve => rl.question(prompt, resolve));
}

async function main() {
  console.log('='.repeat(60));
  console.log('Facebook Messenger Session Setup');
  console.log('='.repeat(60));
  console.log(`Session will be saved to: ${SESSION_PATH}`);
  console.log(`Target chat URL: ${TARGET_CHAT_URL}`);
  console.log(`Mode: ${IS_HEADLESS ? 'headless' : 'headed'}`);
  console.log(`Interactive: ${HAS_TTY ? 'yes' : 'no (timeout mode)'}`);
  console.log('');
  console.log('INSTRUCTIONS:');
  console.log('1. A browser window will open to Facebook Messenger');
  console.log('2. Log in with your Facebook credentials');
  console.log('3. Complete any 2FA (SMS, authenticator app, etc.)');
  console.log('4. Navigate to the target chat/group you want to monitor');
  console.log(`   Target: ${TARGET_CHAT_URL}`);
  console.log('5. Verify you can see messages in that chat');
  if (HAS_TTY && !IS_HEADLESS) {
    console.log('6. Return to this terminal and press ENTER');
  } else {
    console.log('6. Wait for the timeout (180 seconds) to complete');
  }
  console.log('');

  // Ensure session directory exists
  fs.mkdirSync(SESSION_PATH, { recursive: true });

  const launchOptions = {
    headless: IS_HEADLESS,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-blink-features=AutomationControlled',
      '--disable-dev-shm-usage',
    ],
  };

  console.log('Starting interactive Facebook login...');
  console.log('A browser window will open. Please log in to Facebook Messenger.');

  const context = await stealth.launchPersistentContext(SESSION_PATH, launchOptions);
  const page = await context.newPage();

  // Navigate directly to target chat URL
  await page.goto(TARGET_CHAT_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });

  console.log('');
  console.log('Waiting for login to complete...');
  if (HAS_TTY && !IS_HEADLESS) {
    console.log('Press Enter in this terminal AFTER you have successfully logged in and can see your messages.');
  } else {
    console.log('Waiting 180 seconds for manual login...');
  }

  await question('Press Enter when logged in and on the target chat...');

  // Verify login by checking for message elements
  try {
    await page.waitForSelector('div[role="grid"], div[aria-label="Messages"], [data-testid="message_thread"]', { timeout: 10000 });
    console.log('Login verified - message interface detected');
  } catch (e) {
    console.log('Warning: Could not verify message interface, but continuing...');
  }

  // Save localStorage explicitly
  try {
    const localStorage = await page.evaluate(() => JSON.stringify(localStorage));
    const storageFile = path.join(SESSION_PATH, 'local_storage.json');
    fs.writeFileSync(storageFile, localStorage);
    console.log('LocalStorage saved');
  } catch (e) {
    console.log('Warning: Failed to save localStorage:', e.message);
  }

  await context.close();
  console.log('');
  console.log('✅ Session created successfully!');
  console.log(`Session saved to: ${SESSION_PATH}`);
  console.log('');
  console.log('You can now run the Messenger scraper:');
  console.log('  docker compose -f docker/docker-compose.yml up -d messenger');

  if (rl) rl.close();
  process.exit(0);
}

main().catch(err => {
  console.error('Setup failed:', err);
  if (rl) rl.close();
  process.exit(1);
});