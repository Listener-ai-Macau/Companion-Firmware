#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, '.cache', 'wba-visual-review', 'art');
const pageUrl = process.env.COMPANION_EXPRESSION_ART_URL || 'http://127.0.0.1:8876/art/';
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

const families = [
  'calm', 'curious', 'delighted', 'warm', 'playful',
  'sleepy', 'bashful', 'thoughtful', 'focused', 'alert',
];
const errors = [];
const failedRequests = [];
const assert = (condition, message) => { if (!condition) throw new Error(message); };
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const browser = await playwright.chromium.launch({headless: true});

try {
  const page = await browser.newPage({viewport: {width: 1280, height: 1000}});
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('requestfailed', request => {
    // Rapid face/event state replacement cancels the superseded image fetch in
    // Chromium. Every selected target is separately awaited and decoded below.
    if (request.failure()?.errorText !== 'net::ERR_ABORTED')
      failedRequests.push(`${request.url()} ${request.failure()?.errorText || ''}`);
  });
  page.on('response', response => {
    if (response.status() >= 400) failedRequests.push(`${response.url()} HTTP ${response.status()}`);
  });

  // Keep the production timing relationships while making the browser journey
  // bounded. Playwright's own waits are not affected by this page-local shim.
  await page.addInitScript(() => {
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay = 0, ...args) =>
      nativeSetTimeout(callback, delay > 0 ? Math.max(1, Math.round(delay * 0.05)) : 0, ...args);
  });
  await page.goto(pageUrl, {waitUntil: 'networkidle'});
  await page.locator('#gallery .tile').first().waitFor();
  await page.locator('img').evaluateAll(async images =>
    Promise.all(images.filter(image => image.getAttribute('src')).map(image => image.decode())));

  // Exercise every candidate and event-stage image, including assets that are
  // only assigned to an <img> after a control is used. New candidate-only
  // ornaments may choose their own assetRoot without changing this check.
  const candidateUrls = await page.evaluate(() => {
    const paths = new Set(['reference-v1.png']);
    for (const family of Object.keys(ART.families)) {
      for (const suffix of ['rest', 'react', 'settle', 'closed', 'rest-blink'])
        paths.add(`images/${family}-${suffix}.png`);
      paths.add(`old/${family}.png`);
    }
    for (const story of Object.values(ART.stories))
      for (const [frame] of story.frames) paths.add(`images/${frame}.png`);
    for (const event of EVENTS) {
      const root = String(event.assetRoot || 'events').replace(/\/$/, '');
      for (const layer of Object.values(event.layers)) if (layer) paths.add(`${root}/${layer}`);
    }
    return [...paths].map(value => new URL(value, location.href).href);
  });
  const preloadFailures = await page.evaluate(async urls => {
    const failures = [];
    await Promise.all(urls.map(url => new Promise(resolve => {
      const image = new Image();
      image.onload = async () => {
        try {
          await image.decode();
          if (image.naturalWidth <= 0 || image.naturalHeight <= 0) failures.push(`${url}: empty`);
        } catch (error) { failures.push(`${url}: ${error}`); }
        resolve();
      };
      image.onerror = () => { failures.push(`${url}: load error`); resolve(); };
      image.src = url;
    })));
    return failures;
  }, candidateUrls);
  assert(preloadFailures.length === 0, `candidate image failures:\n${preloadFailures.join('\n')}`);

  const imageHealth = await page.locator('img').evaluateAll(images => images.map(image => ({
    src: image.getAttribute('src'), complete: image.complete,
    width: image.naturalWidth, height: image.naturalHeight,
  })));
  const referencedImages = imageHealth.filter(image => image.src);
  assert(referencedImages.every(image => image.complete && image.width > 0 && image.height > 0),
    `image load failure: ${JSON.stringify(referencedImages.filter(image => !image.complete || image.width <= 0 || image.height <= 0))}`);
  assert((await page.locator('#gallery .tile').count()) === families.length, 'expected ten expression families');

  const desktop = await page.evaluate(() => {
    const screen = document.querySelector('.screen');
    const screenBox = screen.getBoundingClientRect();
    const viewport = document.querySelector('.viewport');
    const thumbs = [...document.querySelectorAll('#gallery .tile img')].map(image => {
      const box = image.getBoundingClientRect();
      return {width: box.width, height: box.height, radius: getComputedStyle(image).borderRadius,
        rendering: getComputedStyle(image).imageRendering};
    });
    return {
      screen: [screenBox.width, screenBox.height],
      radius: getComputedStyle(screen).borderRadius,
      faceRadius: getComputedStyle(document.querySelector('#face')).borderRadius,
      overlayRadius: getComputedStyle(document.querySelector('#overlay')).borderRadius,
      faceRendering: getComputedStyle(document.querySelector('#face')).imageRendering,
      overlayPointerEvents: getComputedStyle(document.querySelector('#overlay')).pointerEvents,
      viewportOverflowX: getComputedStyle(viewport).overflowX,
      thumbs,
    };
  });
  assert(desktop.screen[0] === 400 && desktop.screen[1] === 400,
    `desktop preview is not exact 2x: ${desktop.screen}`);
  assert(desktop.radius === '0px' && desktop.faceRadius === '0px' && desktop.overlayRadius === '0px',
    'screen, face, or overlay is rounded');
  assert(desktop.faceRendering === 'pixelated', `face uses non-pixel rendering: ${desktop.faceRendering}`);
  assert(desktop.overlayPointerEvents === 'none', 'event overlay intercepts pet gestures');
  assert(desktop.thumbs.every(thumb => thumb.width === 200 && thumb.height === 200 &&
    thumb.radius === '0px' && thumb.rendering === 'pixelated'), 'gallery is not native square pixel art');
  assert(await page.locator('#overlay').evaluate(element => element.hidden && getComputedStyle(element).display === 'none'),
    'empty event overlay is still visibly composited');

  await page.locator('[data-scale="1"]').click();
  let box = await page.locator('.screen').boundingBox();
  assert(box.width === 200 && box.height === 200, `1x is not 200x200: ${JSON.stringify(box)}`);
  await page.locator('[data-scale="2"]').click();
  box = await page.locator('.screen').boundingBox();
  assert(box.width === 400 && box.height === 400, `2x is not 400x400: ${JSON.stringify(box)}`);

  await page.locator('#grid').click();
  assert(await page.locator('.screen').evaluate(screen => screen.classList.contains('grid')),
    'pixel grid did not turn on');
  assert(await page.locator('#grid').getAttribute('aria-pressed') === 'true', 'pixel grid state is not exposed');
  await page.locator('#grid').click();
  assert(!(await page.locator('.screen').evaluate(screen => screen.classList.contains('grid'))),
    'pixel grid did not turn off');

  // Every family must blink with its own frame and restore its own rest frame.
  for (const family of families) {
    await page.selectOption('#family', family);
    await page.waitForFunction(expected => document.querySelector('#face').getAttribute('src') === `images/${expected}-rest.png`, family);
    await page.locator('#blink').click();
    await page.waitForFunction(expected => document.querySelector('#face').getAttribute('src') === `images/${expected}-rest-blink.png`, family);
    await page.waitForFunction(expected => document.querySelector('#face').getAttribute('src') === `images/${expected}-rest.png`, family);
  }

  // A functional overlay survives family selection and that family's blink.
  await page.selectOption('#event', 'recording_input');
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-hold.png' && !document.querySelector('#overlay').hidden);
  const recordingHold = await page.locator('#overlay').getAttribute('src');
  await page.selectOption('#family', 'warm');
  assert((await page.locator('#overlay').getAttribute('src')) === recordingHold && !(await page.locator('#overlay').isHidden()),
    'family selection changed or hid the independent recording overlay');
  await page.locator('#blink').click();
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest-blink.png');
  assert((await page.locator('#overlay').getAttribute('src')) === recordingHold && !(await page.locator('#overlay').isHidden()),
    'blink changed or hid the independent recording overlay');
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest.png');

  // One full event journey must change only the overlay source.
  const faceBeforeEvent = await page.locator('#face').getAttribute('src');
  await page.locator('#event-play').click();
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-entered.png');
  assert((await page.locator('#face').getAttribute('src')) === faceBeforeEvent, 'event enter changed the face source');
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-hold.png');
  assert((await page.locator('#face').getAttribute('src')) === faceBeforeEvent, 'event hold changed the face source');
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-exit.png');
  assert((await page.locator('#face').getAttribute('src')) === faceBeforeEvent, 'event exit changed the face source');
  await page.waitForFunction(() => document.querySelector('#overlay').hidden &&
    !document.querySelector('#overlay').hasAttribute('src'));
  assert((await page.locator('#face').getAttribute('src')) === faceBeforeEvent, 'event completion changed the face source');

  // Stop cancels every stale stage timer. A subsequent event selection must
  // remain stable after the old recording timers would have fired.
  await page.selectOption('#event', 'recording_input');
  await page.locator('#event-play').click();
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-entered.png');
  await page.locator('#event-stop').click();
  await page.selectOption('#event', 'curious_question');
  await page.waitForTimeout(220);
  assert((await page.locator('#overlay').getAttribute('src')) === 'events/stages/curious_question-hold.png' &&
    !(await page.locator('#overlay').isHidden()), 'cancelled recording timer overwrote the newer event');

  // The transparent overlay cannot consume the main-screen pet gesture, and a
  // real functional event takes priority over the optional petting heart.
  await page.selectOption('#event', 'recording_input');
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'events/stages/recording_input-hold.png');
  await page.selectOption('#family', 'focused');
  const overlayBeforePet = await page.locator('#overlay').getAttribute('src');
  await page.locator('.screen').click({position: {x: 100, y: 100}});
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-react.png');
  assert((await page.locator('#overlay').getAttribute('src')) === overlayBeforePet,
    'pet gesture replaced the functional recording overlay');

  // With no functional event, the same accepted pet action may show the newly
  // registered candidate heart and must still drive the face story.
  await page.selectOption('#event', '');
  assert(await page.locator('#overlay').evaluate(element => element.hidden && getComputedStyle(element).display === 'none'),
    'cleared overlay is not actually hidden');
  await page.locator('.screen').click({position: {x: 100, y: 100}});
  await page.waitForFunction(() => document.querySelector('#overlay').getAttribute('src') ===
    'emotions/pet_heart-entered.png' && !document.querySelector('#overlay').hidden);
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-react.png');

  await page.selectOption('#family', 'warm');
  await page.selectOption('#event', 'recording_input');
  await page.waitForFunction(() => document.querySelector('#face').getAttribute('src') === 'images/warm-rest.png' &&
    document.querySelector('#overlay').getAttribute('src') === 'events/stages/recording_input-hold.png');
  await page.locator('[data-scale="2"]').click();
  await page.screenshot({path: path.join(out, 'expression-art-desktop.png'), fullPage: true});

  await page.setViewportSize({width: 390, height: 844});
  await page.reload({waitUntil: 'networkidle'});
  await page.locator('#gallery .tile').first().waitFor();
  box = await page.locator('.screen').boundingBox();
  assert(box.width === 200 && box.height === 200, `mobile default is not exact 1x: ${JSON.stringify(box)}`);
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth)), 'mobile page has horizontal overflow');
  await page.locator('[data-scale="2"]').click();
  const mobileZoom = await page.evaluate(() => {
    const viewport = document.querySelector('.viewport');
    const screen = document.querySelector('.screen').getBoundingClientRect();
    return {screen: [screen.width, screen.height], localScroll: viewport.scrollWidth > viewport.clientWidth,
      documentOverflow: document.documentElement.scrollWidth > innerWidth};
  });
  assert(mobileZoom.screen[0] === 400 && mobileZoom.screen[1] === 400 && mobileZoom.localScroll && !mobileZoom.documentOverflow,
    `mobile 2x must scroll locally: ${JSON.stringify(mobileZoom)}`);
  await page.locator('[data-scale="1"]').click();
  await page.screenshot({path: path.join(out, 'expression-art-mobile.png'), fullPage: true});

  assert(errors.length === 0, errors.join('\n'));
  assert(failedRequests.length === 0, `failed requests:\n${failedRequests.join('\n')}`);
  const result = {
    result: 'PASS_WBA_EXPRESSION_ART_UI',
    claim: 'HOST_BROWSER_ONLY',
    pageUrl,
    familiesChecked: families,
    nativeFrame: [200, 200],
    desktopDefaultScale: 2,
    mobileDefaultScale: 1,
    candidateImagesDecoded: candidateUrls.length,
    checks: [
      'square-no-radius-integer-scale', 'all-images-loaded', 'ten-family-selection',
      'per-family-blink-and-restore', 'face-overlay-independence', 'event-enter-hold-exit',
      'event-stop-cancels-stale-timers', 'pixel-grid-toggle', 'overlay-does-not-block-pet',
      'empty-overlay-computed-hidden', 'pet-heart-with-functional-priority',
      'mobile-no-document-overflow', 'mobile-2x-local-scroll',
    ],
    screenshots: ['expression-art-desktop.png', 'expression-art-mobile.png'],
    sourceSha256: {'tools/check_wba_expression_art.mjs': digest(fileURLToPath(import.meta.url))},
    errors,
    failedRequests,
  };
  fs.writeFileSync(path.join(out, 'expression-art-browser-result.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log('PASS_WBA_EXPRESSION_ART_UI: native/integer layout, 10 family blinks, independent event lifecycle, desktop/mobile');
} finally {
  await browser.close();
}
