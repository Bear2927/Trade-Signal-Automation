/**
 * Facebook Messenger Scraper using Playwright with Stealth
 *
 * Reads messages from a Messenger thread and forwards trade alerts from a
 * target author to a Discord webhook.
 *
 * Messages are read from the aria-label of Messenger's message rows, which has
 * the form "At <when>, <Author>: <text>". Facebook exposes no stable class names
 * or data-testid attributes for author/body, so aria-label is the only reliable
 * source for attributing a message to its sender.
 */

const { chromium } = require('playwright');
const { addExtra } = require('playwright-extra');
const StealthPlugin = require('puppeteer-extra-plugin-stealth');
const axios = require('axios');
const Redis = require('ioredis');
require('dotenv').config();

const stealth = addExtra(chromium);
stealth.use(StealthPlugin());

function argValue(name) {
  const i = process.argv.indexOf(name);
  return i !== -1 ? process.argv[i + 1] : undefined;
}

// --backfill N posts the N most recent matching messages on startup instead of
// seeding them as already-seen.
const BACKFILL = parseInt(argValue('--backfill') || '0', 10);

// --chat accepts a bare thread id or a full URL, so one process per thread can
// share this single implementation.
const CHAT_ARG = argValue('--chat');
const SESSION_ARG = argValue('--session');

function toChatUrl(v) {
  if (!v) return undefined;
  return /^https?:\/\//.test(v) ? v : `https://www.facebook.com/messages/t/${v}`;
}

// config.yaml is the source of truth the user edits; env vars override it.
// Without this fallback targetChatUrl silently degraded to the generic inbox,
// because MESSENGER__TARGET_CHAT_URL is not set anywhere.
function loadYamlConfig() {
  try {
    const yaml = require('js-yaml');
    const p = require('path').join(__dirname, '..', '..', 'config', 'config.yaml');
    return yaml.load(require('fs').readFileSync(p, 'utf8')) || {};
  } catch (err) {
    console.warn('Could not read config.yaml, relying on env only:', err.message);
    return {};
  }
}

const YAML = loadYamlConfig();
const YM = YAML.messenger || {};
const YR = YAML.redis || {};

const CONFIG = {
  targetChatUrl: toChatUrl(CHAT_ARG) || process.env.MESSENGER__TARGET_CHAT_URL
    || process.env.MESSENGER_TARGET_CHAT_URL || YM.target_chat_url
    || 'https://www.facebook.com/messages/t/',
  sessionPath: SESSION_ARG || process.env.MESSENGER__SESSION_PATH
    || process.env.MESSENGER_SESSION_PATH || YM.session_path || './fb_session',
  headless: (process.env.MESSENGER__HEADLESS || process.env.MESSENGER_HEADLESS
    || String(YM.headless !== undefined ? YM.headless : true)) !== 'false',
  proxy: process.env.MESSENGER__PROXY || process.env.MESSENGER_PROXY || YM.proxy || '',
  redisHost: process.env.REDIS_HOST || YR.host || 'localhost',
  redisPort: parseInt(process.env.REDIS_PORT) || YR.port || 6379,
  redisPassword: process.env.REDIS_PASSWORD || YR.password || '',
  webhookUrl: process.env.DISCORD_WEBHOOK_URL || (YAML.webhook && YAML.webhook.url) || '',
  chatWebhookUrl: process.env.DISCORD_CHAT_WEBHOOK_URL || (YAML.webhook && YAML.webhook.chat_url) || '',
  // Long TTL: the app restarts daily via cron, and a short TTL would repost the
  // whole visible thread on every start.
  dedupTtl: parseInt(process.env.MESSENGER_DEDUP_TTL || '604800', 10),
  pollIntervalMs: parseInt(process.env.MESSENGER_POLL_MS || '3000', 10),
  authors: (process.env.MESSENGER_AUTHORS
    || (Array.isArray(YM.authors) ? YM.authors.join(',') : YM.authors)
    || 'Don Cristo,Macro CEO').split(',').map(s => s.trim()).filter(Boolean),
  // Mirrors get_enabled_platforms() in src/social/queue.py. This used to be
  // hardcoded to [], which made the Python scheduler treat every Messenger job
  // as "nothing to post" and drop it as successful.
  socialPlatforms: (process.env.SOCIAL_PLATFORMS || Object.keys(YAML.social || {})
    .filter(k => YAML.social[k] && typeof YAML.social[k] === 'object'
      && YAML.social[k].enabled === true)
    .join(',')).split(',').map(s => s.trim()).filter(Boolean),
};

const redis = new Redis({
  host: CONFIG.redisHost,
  port: CONFIG.redisPort,
  password: CONFIG.redisPassword || undefined,
  maxRetriesPerRequest: 3,
});

redis.on('error', (err) => console.error('Redis error:', err));
redis.on('connect', () => console.log('Redis connected'));

function hashContent(content) {
  return require('crypto').createHash('md5').update(content).digest('hex');
}

// Returns true if this content was already handled. markOnly skips the "already
// seen" report so startup can seed history without posting it.
async function claimMessage(contentHash) {
  const key = `dedup:messenger:${contentHash}`;
  const result = await redis.set(key, '1', 'NX', 'EX', CONFIG.dedupTtl);
  return result === null;
}

// Contract header: TICKER EXPIRY STRIKE(C|P) with optional @price.
// Expiry is OCT16 | 10/15 | 1DTE.
const CONTRACT_RE = /\b([A-Z]{1,5})\s+((?:[A-Z]{3}\s?\d{1,2})|(?:\d{1,2}\/\d{1,2})|(?:\d+\s?DTE))\s+(\d+(?:\.\d+)?)\s*([CP])\b\s*@?\s*(\d+(?:\.\d+)?)?/gi;

// One Messenger message can carry several trades separated by blank lines, so
// each contract header claims the text up to the next header as its own block.
function parseTrades(text) {
  const headers = [...text.matchAll(CONTRACT_RE)];
  return headers.map((m, i) => {
    const start = m.index + m[0].length;
    const end = i + 1 < headers.length ? headers[i + 1].index : text.length;
    const block = text.slice(start, end);

    const sl = block.match(/s\s*\/\s*l\s*@?\s*(\d+(?:\.\d+)?)/i);
    const pt = block.match(/\bpt\s*@?\s*(\d+(?:\.\d+)?)/i);
    const note = block.split('\n').map(s => s.trim())
      .filter(s => s && !/^(s\s*\/\s*l|pt)\b/i.test(s))
      .join(' ').replace(/s\s*\/\s*l\s*@?\s*[\d.]+/gi, '')
      .replace(/\bpt\s*@?\s*[\d.]+/gi, '').trim();

    return {
      ticker: m[1].toUpperCase(),
      expiry: m[2].toUpperCase().replace(/\s+/g, ''),
      strike: m[3],
      type: m[4].toUpperCase(),
      entry: m[5] !== undefined ? parseFloat(m[5]) : null,
      stoploss: sl ? parseFloat(sl[1]) : null,
      target: pt ? parseFloat(pt[1]) : null,
      note: note.slice(0, 100) || null,
    };
  });
}

// Message routing, kept in step with classify_message() in src/common/webhook.py.
// Entries and exits are actionable and go to the trade-signals channel; watches,
// partial scale-outs and banter go to the chat channel.
//
// Two contract shapes exist: full ("MDB OCT16 425C 1.25", carries an expiry) and
// short ("$SPY 778C @.30", no expiry). The short form demands an UPPERCASE
// ticker, otherwise prose like "Watching 772P's" would read as a contract.
// None of these carry /g: .test() on a global regex is stateful via lastIndex.
const CONTRACT_FULL = /\b[A-Z]{1,5}\s+(?:[A-Z]{3}\s?\d{1,2}|\d{1,2}\/\d{1,2}|\d+\s?DTE)\s+\d+(?:\.\d+)?\s*[CP]\b/i;
// The short form must carry a price, or flow commentary such as
// "MS 200C OTM pop and flat" reads as an entry. The full form needs no price:
// its expiry is already the signal, and "MS OCT23 200C earnings" omits one.
const CONTRACT_SHORT = /\$?\b[A-Z]{1,5}\s+\d+(?:\.\d+)?\s*[CP]\b\s*(?:@\s*)?\.?\d+(?:\.\d+)?\b/;

// A partial scale-out is an update, not an exit, even though it says "took".
const PARTIAL = /\b(?:scale[sd]?|scaling|trim(?:med|ming)?|partial|took\s+(?:some|more))\b/i;
const EXIT = /\b(?:stopp?(?:ing|ed)\s+out|took\s+the\s+loss|full(?:y)?\s+(?:out|closed|exited)|all\s+out|closed\s+(?:out|it|the)|cut\s+(?:it|the))\b/i;

function classifyMessage(text) {
  if (CONTRACT_FULL.test(text) || CONTRACT_SHORT.test(text)) return 'entry';
  if (EXIT.test(text) && !PARTIAL.test(text)) return 'exit';
  return 'other';
}

// A person tag is "@" followed by a letter. Prices also use "@"
// ("$SPY 778C @.30", "took more off @33%"), so only a letter counts as a tag.
// Checked AFTER stripMentions, so @everyone/@here never trip it -- those are
// mass pings, not people.
const PERSON_TAG = /@[A-Za-z]/;

function tagsAPerson(text) {
  return PERSON_TAG.test(text);
}

// Cross-server mention tokens are dead references in the destination channel and
// can fire stray pings, so they are stripped from any forwarded text.
const MENTION_RE = /<@[!&]?\d+>|<#\d+>|@everyone|@here/g;

function stripMentions(text) {
  return text.replace(MENTION_RE, '').replace(/[ \t]{2,}/g, ' ').trim();
}

function tradeEmbed(trade) {
  const fields = [{
    name: 'Contract',
    value: `${trade.strike}${trade.type} ${trade.expiry}`,
    inline: true,
  }];
  if (trade.entry !== null) fields.push({ name: 'Entry', value: `$${trade.entry.toFixed(2)}`, inline: true });
  if (trade.stoploss !== null) fields.push({ name: 'Stop Loss', value: `$${trade.stoploss.toFixed(2)}`, inline: true });
  if (trade.target !== null) fields.push({ name: 'Target Price', value: `$${trade.target.toFixed(2)}`, inline: true });

  if (trade.entry !== null && trade.target !== null) {
    const profit = ((trade.target - trade.entry) / trade.entry) * 100;
    fields.push({ name: 'Profit Target', value: `${profit.toFixed(1)}%`, inline: true });
  }
  if (trade.entry !== null && trade.target !== null && trade.stoploss !== null && trade.entry !== trade.stoploss) {
    const rr = (trade.target - trade.entry) / (trade.entry - trade.stoploss);
    fields.push({ name: 'Risk/Reward', value: `1:${rr.toFixed(2)}`, inline: true });
  }
  if (trade.note) fields.push({ name: 'Note', value: trade.note, inline: false });

  return {
    // The ticker goes in the description, not the title: Discord renders
    // markdown headings in embed descriptions but not in titles, and a heading
    // is the only way to get text larger than the default size.
    description: `# $${trade.ticker}`,
    color: 0x00ff00,
    fields,
  };
}

async function sendToWebhook(rawText, files = []) {
  if (!CONFIG.webhookUrl) {
    console.log('No webhook URL configured, skipping');
    return null;
  }

  const text = stripMentions(rawText);
  const kind = classifyMessage(text);
  const toChat = kind === 'other';
  // Falls back to the signals webhook if no chat webhook is configured, so a
  // missing chat_url drops nothing on the floor.
  const target = toChat ? (CONFIG.chatWebhookUrl || CONFIG.webhookUrl) : CONFIG.webhookUrl;

  const trades = toChat ? [] : parseTrades(text);
  let embeds;
  if (trades.length) {
    embeds = trades.map(t => tradeEmbed(t));
  } else {
    embeds = [{
      title: kind === 'exit' ? 'Trade Exit' : (toChat ? 'Chat' : 'Trade Signal'),
      description: text.slice(0, 4096) || undefined,
      color: kind === 'exit' ? 0xff5555 : (toChat ? 0x95a5a6 : 0x00ff00),
    }];
  }

  // Discord renders one image per embed, so the first lands on the leading
  // embed and any extras get their own.
  if (files.length) {
    embeds[0].image = { url: `attachment://${files[0].name}` };
    for (const f of files.slice(1)) {
      embeds.push({ color: embeds[0].color, image: { url: `attachment://${f.name}` } });
    }
  }

  const batches = [];
  for (let i = 0; i < embeds.length; i += 10) batches.push(embeds.slice(i, i + 10));

  for (let b = 0; b < batches.length; b++) {
    const payload = { embeds: batches[b], allowed_mentions: { parse: [] } };
    try {
      if (b === 0 && files.length) {
        // Multipart: the files must accompany the embed that references them.
        const fd = new FormData();
        fd.append('payload_json', JSON.stringify(payload));
        files.forEach((f, i) => fd.append(`files[${i}]`, new Blob([f.buf], { type: f.type }), f.name));
        const r = await fetch(target, { method: 'POST', body: fd });
        if (!r.ok) { console.error('Webhook error:', r.status, (await r.text()).slice(0, 180)); return null; }
      } else {
        await axios.post(target, payload, {
          headers: { 'Content-Type': 'application/json' },
          timeout: 10000,
        });
      }
    } catch (err) {
      console.error('Webhook error:', err.response ? `${err.response.status} ${JSON.stringify(err.response.data)}` : err.message);
      return null;
    }
  }
  const imgNote = files.length ? `, ${files.length} image(s)` : '';
  console.log(`Routed ${kind} -> ${toChat ? 'chat-room' : 'trade-signals'} (${embeds.length} embed(s)${imgNote})`);
  return kind;
}

// Facebook's CDN URLs are signed and short-lived, so the bytes are pulled
// through the browser context (which carries the session cookies) and
// re-uploaded to Discord, rather than handing Discord a URL it cannot fetch.
const MAX_IMAGE_BYTES = 8 * 1024 * 1024;

const EXT_BY_TYPE = {
  'image/png': 'png', 'image/jpeg': 'jpg', 'image/jpg': 'jpg',
  'image/gif': 'gif', 'image/webp': 'webp',
};

async function downloadImages(page, urls) {
  const files = [];
  for (let i = 0; i < urls.length && files.length < 4; i++) {
    try {
      const resp = await page.request.get(urls[i]);
      if (!resp.ok()) { console.error(`image fetch ${resp.status()}`); continue; }
      const type = (resp.headers()['content-type'] || 'image/jpeg').split(';')[0];
      const body = await resp.body();
      if (body.length > MAX_IMAGE_BYTES) { console.error(`image too large (${body.length}B), skipped`); continue; }
      files.push({ buf: body, type, name: `image${files.length}.${EXT_BY_TYPE[type] || 'jpg'}` });
    } catch (err) {
      console.error('image download failed:', err.message);
    }
  }
  return files;
}

// A stable per-image id: the CDN path without its rotating query signature.
function imageKey(url) {
  return String(url).split('?')[0];
}

// Must match src/social/queue.py SocialJob: a sorted set scored by -priority,
// with seconds-based timestamps.
async function queueForSocial(text, author, trades) {
  const now = Date.now() / 1000;
  const job = {
    id: `messenger:${Math.round(now * 1000)}`,
    signal: { raw_text: text, source: 'Messenger', author, trades },
    source: 'messenger',
    timestamp: now,
    platforms: CONFIG.socialPlatforms,
    priority: 0,
    attempts: 0,
    max_attempts: 3,
    created_at: now,
    scheduled_for: null,
  };
  try {
    await redis.zadd('social:queue', 0, JSON.stringify(job));
  } catch (err) {
    console.error('Social queue error:', err.message);
  }
}

function isTargetAuthor(author) {
  if (!author) return false;
  return CONFIG.authors.some(a => author.toLowerCase().includes(a.toLowerCase()));
}

// Runs in page context. Messenger renders each message row with an aria-label of
// the form "At <when>, <Author>: <text>".
function extractMessagesInPage() {
  // Messenger renders three timestamp shapes:
  //   "At 9:27 AM, Author: text"                      (today)
  //   "At Wednesday 2:59pm, Author: text"             (this week)
  //   "At September 24, 2026, 2:45 PM, Author: text"  (older)
  // Anchoring on the clock time is what makes all three parse. Splitting on the
  // first comma instead reads the colon inside "2:45" as the author delimiter
  // and yields an author of "2026, 2", which silently drops the message.
  // The text group is optional so attachment-only rows still yield an author.
  const re = /^At\s+(.*?\d{1,2}:\d{2}\s*(?:[AaPp]\.?[Mm]\.?)?),\s+([^:]+?)(?::\s*([\s\S]+))?$/;
  const scoped = document.querySelectorAll('div[data-scope="messages_table"][aria-label]');
  const nodes = scoped.length ? scoped : document.querySelectorAll('[aria-label]');
  const seen = new Set();
  const out = [];
  for (const el of nodes) {
    const a = el.getAttribute('aria-label') || '';
    if (seen.has(a)) continue;
    const m = a.match(re);
    if (!m) continue;
    seen.add(a);
    // Content images carry alt="Open photo". Avatars are 100x100 with a person
    // name for alt, and reactions use the emoji itself, so both are excluded.
    const images = [...el.querySelectorAll('img')]
      .filter(i => /^Open photo$/i.test(i.getAttribute('alt') || '') && i.naturalWidth > 150)
      .map(i => i.getAttribute('src'))
      .filter(Boolean);
    out.push({ when: m[1].trim(), author: m[2].trim(), text: (m[3] || '').trim(), images });
  }
  return out;
}

async function handleMessage(msg, { post }, page) {
  if (!isTargetAuthor(msg.author)) return;
  const images = msg.images || [];
  // An image-only message has no text, so the length gate only applies when
  // there is nothing else to forward.
  if (!images.length && (!msg.text || msg.text.trim().length < 3)) return;

  // Image paths belong in the dedup key: every image-only message would
  // otherwise hash to "author|" and only the first would ever post.
  const keyParts = [msg.author, msg.text, ...images.map(imageKey)].join('|');
  const already = await claimMessage(hashContent(keyParts));
  if (already) return;

  // Messages where the author tags someone are a reply to that person, not
  // broadcast content, so they are dropped rather than routed.
  const cleaned = stripMentions(msg.text);
  if (tagsAPerson(cleaned)) {
    console.log(`skipped (tags a person): ${cleaned.slice(0, 70).replace(/\n/g, ' ')}`);
    return;
  }

  const trades = parseTrades(msg.text);
  if (!post) {
    console.log(`seeded (not posted): <${msg.author}> ${(msg.text || '(image only)').slice(0, 60).replace(/\n/g, ' ')}`);
    return;
  }

  const label = msg.text ? msg.text.slice(0, 80).replace(/\n/g, ' ') : `(${images.length} image(s), no text)`;
  console.log(`NEW from ${msg.author}: ${label}`);
  const files = images.length && page ? await downloadImages(page, images) : [];
  const kind = await sendToWebhook(msg.text, files);
  if (kind && kind !== 'other') await queueForSocial(msg.text, msg.author, trades);
}

async function run() {
  console.log('Starting Facebook Messenger scraper...');
  console.log('Chat URL:', CONFIG.targetChatUrl);
  console.log('Session path:', CONFIG.sessionPath);
  console.log('Headless:', CONFIG.headless);
  console.log('Target authors:', CONFIG.authors.join(', '));
  console.log('Backfill:', BACKFILL ? `${BACKFILL} most recent` : 'off (seed only)');

  const launchOptions = {
    headless: CONFIG.headless,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled'],
  };

  if (CONFIG.proxy) {
    const parts = CONFIG.proxy.split(':');
    if (parts.length >= 2) {
      const [host, port, user, pass] = parts;
      const proxyConfig = { server: `http://${host}:${port}` };
      if (user && pass) { proxyConfig.username = user; proxyConfig.password = pass; }
      launchOptions.proxy = proxyConfig;
      console.log(`Proxy configured: ${host}:${port}${user ? ' (with auth)' : ''}`);
    } else {
      console.warn('Invalid proxy format. Expected: host:port or host:port:user:pass');
    }
  }

  const context = await stealth.launchPersistentContext(CONFIG.sessionPath, launchOptions);
  const page = await context.newPage();

  console.log('Navigating to Messenger...');
  await page.goto(CONFIG.targetChatUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

  if (/\/login|\/checkpoint|\/reauth/.test(page.url())) {
    console.error('SESSION EXPIRED: redirected to', page.url());
    console.error('Re-run scripts/setup_fb_session.py to re-authenticate.');
    await context.close();
    process.exit(1);
  }

  let containerFound = false;
  for (const selector of ['div[role="grid"]', 'div[aria-label="Messages"]', '[data-testid="message_thread"]']) {
    try {
      await page.waitForSelector(selector, { timeout: 10000 });
      containerFound = true;
      console.log(`Found message container with selector: ${selector}`);
      break;
    } catch (e) { /* try next */ }
  }
  if (!containerFound) console.log('Warning: could not find message container, continuing...');

  // The thread is virtualized and fills in after load.
  await page.waitForTimeout(8000);

  const initial = await page.evaluate(extractMessagesInPage);
  const mine = initial.filter(m => isTargetAuthor(m.author));
  console.log(`Initial scrape: ${initial.length} message(s) visible, ${mine.length} from target author(s)`);

  const toPost = BACKFILL > 0 ? mine.slice(-BACKFILL) : [];
  const toSeed = mine.filter(m => !toPost.includes(m));
  for (const m of toSeed) await handleMessage(m, { post: false }, page);
  for (const m of toPost) await handleMessage(m, { post: true }, page);

  console.log('Monitoring Messenger for trade signals...');
  console.log('Press Ctrl+C to stop');

  // Polled rather than MutationObserver-driven: mutation records hand back
  // arbitrary nested nodes whose innerText loses the author attribution that the
  // row's aria-label carries.
  let stopped = false;
  const tick = async () => {
    if (stopped) return;
    try {
      const msgs = await page.evaluate(extractMessagesInPage);
      for (const m of msgs) await handleMessage(m, { post: true }, page);
    } catch (err) {
      console.error('Poll error:', err.message);
    }
  };
  const timer = setInterval(tick, CONFIG.pollIntervalMs);

  const shutdown = async () => {
    stopped = true;
    clearInterval(timer);
    console.log('\nShutting down...');
    try { await context.close(); } catch (e) {}
    try { await redis.quit(); } catch (e) {}
    process.exit(0);
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

if (require.main === module) {
  run().catch(err => { console.error('Fatal:', err); process.exit(1); });
}

module.exports = { parseTrades, isTargetAuthor, tradeEmbed, extractMessagesInPage, classifyMessage, stripMentions, tagsAPerson };
