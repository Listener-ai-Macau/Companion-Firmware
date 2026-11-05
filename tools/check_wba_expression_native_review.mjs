#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, '.cache', 'wba-visual-review', 'art', 'native-v2');
const pageUrl = process.env.COMPANION_NATIVE_REVIEW_URL || 'http://127.0.0.1:8876/art/';
const families = [
  'calm', 'curious', 'delighted', 'warm', 'playful',
  'sleepy', 'bashful', 'thoughtful', 'focused', 'alert',
];
const require = createRequire(import.meta.url);
let playwright;
for (const source of [
  process.env.COMPANION_PLAYWRIGHT_MODULE,
  'playwright',
  'C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright',
]) {
  if (!source) continue;
  try { playwright = require(source); break; } catch {}
}
if (!playwright) throw new Error('Playwright unavailable');

const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const errors = [];
const failedRequests = [];
const browser = await playwright.chromium.launch({headless: true});

try {
  const page = await browser.newPage({viewport: {width: 1280, height: 1000}});
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('requestfailed', request => {
    // Replacing a face or overlay cancels the superseded image fetch. Every
    // actual target below is separately decoded and dimension-checked.
    if (request.failure()?.errorText !== 'net::ERR_ABORTED')
      failedRequests.push(`${request.url()} ${request.failure()?.errorText || ''}`);
  });
  page.on('response', response => {
    if (response.status() >= 400) failedRequests.push(`${response.url()} HTTP ${response.status()}`);
  });
  await page.addInitScript(() => {
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay = 0, ...args) =>
      nativeSetTimeout(callback, delay > 0 ? Math.max(1, Math.round(delay * 0.08)) : 0, ...args);
  });
  await page.goto(pageUrl, {waitUntil: 'networkidle'});
  await page.locator('#gallery .tile').first().waitFor();
  assert((await page.evaluate(() => document.baseURI)).endsWith('/art/native-v2/'),
    `active review does not resolve through native-v2: ${await page.evaluate(() => document.baseURI)}`);
  assert((await page.locator('#gallery .tile').count()) === 10, 'expected ten native families');

  const inventory = await page.evaluate(() => {
    const paths = new Set();
    for (const family of Object.keys(ART.families)) {
      paths.add(`images/${family}-rest.png`);
      paths.add(`images/${family}-rest-blink.png`);
      paths.add(`old/${family}.png`);
      for (const [frame] of ART.motions[family]) paths.add(`images/${frame}.png`);
    }
    for (const event of EVENTS) {
      const assetRoot = String(event.assetRoot).replace(/\/$/, '');
      for (const layer of Object.values(event.layers)) if (layer) paths.add(`${assetRoot}/${layer}`);
    }
    return {
      urls: [...paths].map(value => new URL(value, document.baseURI).href),
      motions: ART.motions,
    };
  });
  const preload = await page.evaluate(async urls => {
    const failures = [];
    await Promise.all(urls.map(url => new Promise(resolve => {
      const image = new Image();
      image.onload = async () => {
        try {
          await image.decode();
          if (image.naturalWidth !== 200 || image.naturalHeight !== 200)
            failures.push(`${url}: ${image.naturalWidth}x${image.naturalHeight}`);
        } catch (error) { failures.push(`${url}: decode ${error}`); }
        resolve();
      };
      image.onerror = () => { failures.push(`${url}: load error`); resolve(); };
      image.src = url;
    })));
    return failures;
  }, inventory.urls);
  assert(preload.length === 0, `native image failures:\n${preload.join('\n')}`);

  // Browser-side canvas is the independent restoration check requested here:
  // every displayed rest frame must equal its retained old frame below the
  // 16-pixel status rail. This is a source restoration check, not art approval.
  const pixelDiffs = await page.evaluate(async checkedFamilies => {
    const load = source => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = async () => {
        try { await image.decode(); resolve(image); } catch (error) { reject(error); }
      };
      image.onerror = () => reject(new Error(`cannot load ${source}`));
      image.src = source;
    });
    const pixels = image => {
      const canvas = document.createElement('canvas');
      canvas.width = 200; canvas.height = 200;
      const context = canvas.getContext('2d', {willReadFrequently: true});
      context.imageSmoothingEnabled = false;
      context.drawImage(image, 0, 0);
      return context.getImageData(0, 0, 200, 200).data;
    };
    const result = {};
    for (const family of checkedFamilies) {
      const [rest, old] = await Promise.all([
        load(new URL(`images/${family}-rest.png`, document.baseURI).href),
        load(new URL(`old/${family}.png`, document.baseURI).href),
      ]);
      const a = pixels(rest), b = pixels(old);
      let changed = 0;
      for (let y = 16; y < 200; y++) for (let x = 0; x < 200; x++) {
        const offset = (y * 200 + x) * 4;
        if (a[offset] !== b[offset] || a[offset + 1] !== b[offset + 1] ||
            a[offset + 2] !== b[offset + 2] || a[offset + 3] !== b[offset + 3]) changed++;
      }
      result[family] = changed;
    }
    return result;
  }, families);
  assert(Object.values(pixelDiffs).every(value => value === 0),
    `restored rest differs below status rail: ${JSON.stringify(pixelDiffs)}`);

  const desktop = await page.evaluate(() => {
    const screen = document.querySelector('.screen');
    const bounds = screen.getBoundingClientRect();
    const thumbs = [...document.querySelectorAll('#gallery .tile img')].map(image => {
      const box = image.getBoundingClientRect();
      return [box.width, box.height, getComputedStyle(image).borderRadius, getComputedStyle(image).imageRendering];
    });
    return {
      screen: [bounds.width, bounds.height], radius: getComputedStyle(screen).borderRadius,
      faceRadius: getComputedStyle(document.querySelector('#face')).borderRadius,
      faceRendering: getComputedStyle(document.querySelector('#face')).imageRendering,
      overlayPointerEvents: getComputedStyle(document.querySelector('#overlay')).pointerEvents,
      thumbs,
    };
  });
  assert(desktop.screen[0] === 400 && desktop.screen[1] === 400,
    `desktop is not exact 2x: ${desktop.screen}`);
  assert(desktop.radius === '0px' && desktop.faceRadius === '0px', 'native screen is rounded');
  assert(desktop.faceRendering === 'pixelated', 'native screen does not use pixel rendering');
  assert(desktop.overlayPointerEvents === 'none', 'overlay blocks screen pet action');
  assert(desktop.thumbs.every(([width, height, radius, rendering]) =>
    width === 200 && height === 200 && radius === '0px' && rendering === 'pixelated'),
    'gallery is not native 200x200 square pixel art');

  await page.locator('[data-scale="1"]').click();
  let box = await page.locator('.screen').boundingBox();
  assert(box.width === 200 && box.height === 200, `desktop 1x is not 200x200: ${JSON.stringify(box)}`);
  await page.locator('[data-scale="2"]').click();
  box = await page.locator('.screen').boundingBox();
  assert(box.width === 400 && box.height === 400, `desktop 2x is not 400x400: ${JSON.stringify(box)}`);

  // All safe native motions must visit their declared original frames and
  // return to the exact family rest path.
  for (const family of families) {
    await page.selectOption('#family', family);
    await page.waitForFunction(expected => document.querySelector('#face').getAttribute('src') ===
      `images/${expected}-rest.png`, family);
    await page.locator('#react').click();
    for (const [frame] of inventory.motions[family]) {
      await page.waitForFunction(expected => {
        const image = document.querySelector('#face');
        return image.getAttribute('src') === `images/${expected}.png` && image.complete && image.naturalWidth === 200;
      }, frame);
    }
    await page.waitForFunction(expected => document.querySelector('#face').getAttribute('src') ===
      `images/${expected}-rest.png`, family);
  }

  // Trace the face src so a pet action cannot silently jump to warm or any
  // other family between the observed blink and the final restore.
  await page.selectOption('#family', 'focused');
  await page.evaluate(() => {
    window.__nativeFaceTrace = [];
    const face = document.querySelector('#face');
    window.__nativeFaceObserver?.disconnect();
    window.__nativeFaceObserver = new MutationObserver(() => window.__nativeFaceTrace.push(face.getAttribute('src')));
    window.__nativeFaceObserver.observe(face, {attributes: true, attributeFilter: ['src']});
  });
  await page.locator('.screen').click({position: {x: 100, y: 100}});
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/focused-rest-blink.png');
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/focused-rest.png');
  const petTrace = await page.evaluate(() => window.__nativeFaceTrace);
  assert(petTrace.length >= 2 && petTrace.every(source => source.startsWith('images/focused-')),
    `pet action changed family: ${JSON.stringify(petTrace)}`);

  // Functional state wins over pet decoration and persists through family
  // selection, blink, and pet interaction.
  await page.selectOption('#event', 'recording_input');
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-hold.png');
  const recordingOverlay = await page.locator('#overlay').getAttribute('src');
  await page.selectOption('#family', 'warm');
  assert((await page.locator('#overlay').getAttribute('src')) === recordingOverlay, 'family switch lost recording overlay');
  await page.locator('#blink').click();
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest-blink.png');
  assert((await page.locator('#overlay').getAttribute('src')) === recordingOverlay, 'blink lost recording overlay');
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest.png');
  await page.locator('.screen').click({position: {x: 100, y: 100}});
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest-blink.png');
  assert((await page.locator('#overlay').getAttribute('src')) === recordingOverlay,
    'pet action replaced functional recording overlay');
  assert((await page.locator('#event').inputValue()) === 'recording_input', 'pet action changed functional event selection');
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest.png');

  // Original frames already contain these three ornaments. The independent
  // overlay must hide with a clear explanation, then reappear on another face
  // at the same tracked stage. Stop clears the stage so later family changes
  // cannot resurrect it.
  for (const [family, eventId] of [
    ['curious', 'curious_question'], ['alert', 'alert_exclamation'], ['playful', 'delight_star'],
  ]) {
    await page.selectOption('#family', family);
    await page.selectOption('#event', eventId);
    assert(await page.locator('#overlay').evaluate(element =>
      element.hidden && getComputedStyle(element).display === 'none' && !element.hasAttribute('src')),
      `${family} duplicates its embedded ${eventId}`);
    assert((await page.locator('#event-label').textContent()).includes('原稿已有该饰品'),
      `${family} lacks embedded-ornament explanation`);
    await page.selectOption('#family', 'calm');
    assert(!(await page.locator('#overlay').isHidden()), `${eventId} stage was not restored on a compatible face`);
    await page.locator('#event-stop').click();
    await page.selectOption('#family', 'warm');
    assert(await page.locator('#overlay').evaluate(element =>
      element.hidden && getComputedStyle(element).display === 'none' && !element.hasAttribute('src')),
      `stopped ${eventId} revived after family switch`);
  }

  // Cancelling an in-flight event must prevent its delayed hold/exit/clear
  // callbacks from stealing the next event's state.
  await page.selectOption('#event', 'recording_input');
  await page.locator('#event-play').click();
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-entered.png');
  await page.locator('#event-stop').click();
  await page.selectOption('#event', 'upgrade_progress');
  await page.waitForTimeout(320);
  assert((await page.locator('#overlay').getAttribute('src')) === 'events/stages/upgrade_progress-hold.png',
    'cancelled event timer overwrote the newer event');

  await page.selectOption('#family', 'calm');
  await page.selectOption('#event', 'recording_input');
  await page.locator('[data-scale="2"]').click();
  await page.screenshot({path: path.join(out, 'native-desktop.png'), fullPage: true});
  await page.setViewportSize({width: 1280, height: 2600});
  await page.evaluate(() => scrollTo(0, 0));
  const comparisonHeading = await page.getByRole('heading', {name: '原稿与当前画面'}).boundingBox();
  const comparisonFigures = await page.locator('.compare figure').evaluateAll(items => items.map(item => {
    const bounds = item.getBoundingClientRect();
    return {x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height};
  }));
  assert(comparisonHeading && comparisonFigures.length === 2, 'restoration comparison region is missing');
  const comparisonFrames = {
    x: comparisonFigures[0].x,
    y: Math.min(...comparisonFigures.map(item => item.y)),
    width: comparisonFigures[1].x + comparisonFigures[1].width - comparisonFigures[0].x,
    height: Math.max(...comparisonFigures.map(item => item.y + item.height)) -
      Math.min(...comparisonFigures.map(item => item.y)),
  };
  const comparisonClip = {
    x: Math.max(0, comparisonFrames.x - 4),
    y: Math.max(0, comparisonHeading.y - 6),
    width: Math.ceil(comparisonFrames.width + 8),
    height: Math.ceil(comparisonFrames.y + comparisonFrames.height - comparisonHeading.y + 12),
  };
  await page.screenshot({path: path.join(out, 'native-restoration-comparison.png'), clip: comparisonClip});

  await page.setViewportSize({width: 390, height: 844});
  await page.reload({waitUntil: 'networkidle'});
  await page.locator('#gallery .tile').first().waitFor();
  box = await page.locator('.screen').boundingBox();
  assert(box.width === 200 && box.height === 200, `mobile default is not exact 1x: ${JSON.stringify(box)}`);
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'mobile page horizontally overflows');
  await page.locator('[data-scale="2"]').click();
  const mobile = await page.evaluate(() => {
    const viewport = document.querySelector('.viewport');
    const screen = document.querySelector('.screen').getBoundingClientRect();
    return {screen: [screen.width, screen.height], localScroll: viewport.scrollWidth > viewport.clientWidth,
      documentOverflow: document.documentElement.scrollWidth > innerWidth};
  });
  assert(mobile.screen[0] === 400 && mobile.screen[1] === 400 && mobile.localScroll && !mobile.documentOverflow,
    `mobile 2x must scroll locally: ${JSON.stringify(mobile)}`);
  await page.locator('[data-scale="1"]').click();
  await page.screenshot({path: path.join(out, 'native-mobile.png'), fullPage: true});

  assert(errors.length === 0, errors.join('\n'));
  assert(failedRequests.length === 0, `failed requests:\n${failedRequests.join('\n')}`);
  const result = {
    result: 'PASS_NATIVE_SOURCE_RESTORATION_BROWSER_CHECK',
    claim: 'HOST_BROWSER_SOURCE_RESTORATION_ONLY',
    artAcceptance: 'NOT_CLAIMED',
    hardwareAcceptance: 'NOT_RUN',
    pageUrl,
    nativeFrame: [200, 200],
    decodedImageCount: inventory.urls.length,
    familiesChecked: families,
    restPixelDiffBelowStatus: pixelDiffs,
    checks: [
      'ten-rest-below-y16-zero-pixel-diff', 'all-referenced-images-decode-200x200',
      'native-motion-declared-frames-and-rest-return', 'pet-keeps-selected-family',
      'functional-overlay-across-family-blink-pet', 'embedded-ornament-no-duplicate',
      'event-stage-restores-across-compatible-family', 'stop-clears-event-stage',
      'cancelled-timer-cannot-steal-new-event', 'square-no-radius-integer-scale',
      'mobile-no-document-overflow', 'mobile-2x-local-scroll',
    ],
    screenshots: ['native-desktop.png', 'native-mobile.png', 'native-restoration-comparison.png'],
    sourceSha256: {'tools/check_wba_expression_native_review.mjs': digest(fileURLToPath(import.meta.url))},
    errors,
    failedRequests,
  };
  fs.writeFileSync(path.join(out, 'native-browser-result.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log('PASS_NATIVE_SOURCE_RESTORATION_BROWSER_CHECK: exact rest pixels, native motions, independent events, desktop/mobile');
} finally {
  await browser.close();
}
