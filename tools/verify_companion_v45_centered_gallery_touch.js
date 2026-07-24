const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright');

const root = path.resolve(__dirname, '..');
const pagePath = path.join(root, 'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html');
const outDir = path.resolve(process.argv[2] || path.join(root, '.cache/validation/companion-v45-centered-gallery-r1-20260723/browser'));
fs.mkdirSync(outDir, { recursive: true });
const sha256 = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex').toUpperCase();
const lockPath = path.join(outDir, '.verifier.lock');
let lockFd;
try {
  lockFd = fs.openSync(lockPath, 'wx');
  fs.writeFileSync(lockFd, `${process.pid}\n`, 'utf8');
} catch (error) {
  console.error(`NO_GO: verifier already running or lock is present: ${lockPath}`);
  process.exitCode = 2;
}

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
async function withTimeout(promise, ms, label) {
  let timer;
  try {
    return await Promise.race([
      promise,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error(`${label} timed out after ${ms} ms`)), ms); }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function snapshot(page, phase) {
  return page.evaluate(phaseName => {
    const main = document.querySelector('#overall-viewport');
    const frame = main.querySelector('.viewport-frame');
    const staging = main.querySelector('.viewport-staging');
    const gaze = main.querySelector('.viewport-gaze');
    const target = document.querySelector('.story-row[data-story="warm_presence"] .live-viewport');
    const targetFrame = target && target.querySelector('.viewport-frame');
    const targetStaging = target && target.querySelector('.viewport-staging');
    const targetGaze = target && target.querySelector('.viewport-gaze');
    const states = Object.fromEntries(Object.entries(window.__companionViewportStates).map(([name, value]) => [name, {
      storyName: value.storyName, frameIndex: value.frameIndex, activeFrameIndex: value.activeFrameIndex,
      activeFrameCue: value.activeFrame ? value.activeFrame.cue : null, activeBaseSrc: value.activeBaseSrc,
      touching: value.touching, traceLength: value.trace.length,
      activeFrameElapsedMs: value.activeFrameStartedAt ? Math.round(performance.now() - value.activeFrameStartedAt) : 0,
      framePresentCount: value.framePresentCount,
    }]));
    return {
      phase: phaseName,
      decision: window.__lastEmotionDecision,
      overall: window.__v45TouchState(),
      main: { src: frame.src, hidden: frame.hidden, complete: frame.complete, naturalWidth: frame.naturalWidth,
        stagingHidden: staging.hidden, gazeHidden: gaze.hidden, gazeSrc: gaze.src, gazeTransform: getComputedStyle(gaze).transform },
      targetMain: targetFrame ? { src: targetFrame.src, hidden: targetFrame.hidden, complete: targetFrame.complete,
        naturalWidth: targetFrame.naturalWidth, naturalHeight: targetFrame.naturalHeight,
        stagingHidden: targetStaging.hidden, gazeHidden: targetGaze.hidden, gazeSrc: targetGaze.src,
        gazeTransform: getComputedStyle(targetGaze).transform } : null,
      stories: states,
      storyCount: document.querySelectorAll('.story-row').length,
      viewports: document.querySelectorAll('.story-row .live-viewport').length,
      viewportImages: [...document.querySelectorAll('.story-row .viewport-frame')].map(img => ({ width: img.naturalWidth, height: img.naturalHeight })),
      traceTail: window.__v45TouchTrace.slice(-8),
    };
  }, phase);
}

async function shot(page, name, fullPage = false) {
  const file = path.join(outDir, name);
  await page.screenshot({ path: file, fullPage });
  return { path: file, sha256: sha256(file) };
}

async function viewportShot(page, selector, name) {
  const file = path.join(outDir, name);
  const target = page.locator(selector);
  await target.scrollIntoViewIfNeeded();
  const box = await target.boundingBox();
  if (!box || Math.round(box.width) !== 200 || Math.round(box.height) !== 200) {
    throw new Error(`viewport is not exact 200x200: ${selector} -> ${JSON.stringify(box)}`);
  }
  await page.screenshot({ path: file, animations: 'disabled', scale: 'css',
    clip: { x: Math.round(box.x), y: Math.round(box.y), width: 200, height: 200 } });
  return { path: file, sha256: sha256(file) };
}

async function waitReady(page) {
  await page.waitForFunction(() => {
    const state = window.__v45TouchState && window.__v45TouchState();
    const frame = document.querySelector('#overall-viewport .viewport-frame');
    return state && state.active_frame_cue && frame && !frame.hidden && frame.complete && frame.naturalWidth === 200 &&
      window.__lastEmotionDecision && document.querySelectorAll('.story-row').length === 16;
  }, null, { timeout: 8000 });
}

async function runViewportBody(name, viewport, browser) {
  const page = await browser.newPage({ viewport });
  page.setDefaultTimeout(5000);
  page.setDefaultNavigationTimeout(8000);
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(`file://${pagePath.replace(/\\/g, '/')}?review=v45-authority-wall-r1`, { waitUntil: 'load' });
  try {
    await waitReady(page);
  } catch (error) {
    const diagnostic = await page.evaluate(() => {
      const frame = document.querySelector('#overall-viewport .viewport-frame');
      return { hasState: !!window.__v45TouchState, decision: window.__lastEmotionDecision || null,
        frame: frame ? { hidden: frame.hidden, complete: frame.complete, naturalWidth: frame.naturalWidth, src: frame.src } : null };
    }).catch(e => ({ evaluateError: String(e) }));
    throw new Error(`${error.message}; pageErrors=${JSON.stringify(errors)}; diagnostic=${JSON.stringify(diagnostic)}`);
  }
  const initial = await snapshot(page, 'initial');
  const screenshots = { gallery: await shot(page, `${name}-authority-wall-initial-full.png`, true) };

  const overallSelector = '#overall-viewport';
  const overall = page.locator(overallSelector);
  await overall.scrollIntoViewIfNeeded();
  let box = await overall.boundingBox();
  if (!box) throw new Error('missing overall viewport box');
  await page.mouse.move(box.x + 100, box.y + 100);
  await page.mouse.down();
  await page.waitForTimeout(80);
  await page.mouse.up();
  try {
    await page.waitForFunction(() => window.__lastEmotionDecision && window.__lastEmotionDecision.input.event === 'touch_tap' &&
      window.__v45TouchTrace.some(item => item.kind === 'gesture_classified' && item.event === 'TOUCH_TAP'));
  } catch (error) {
    throw new Error(`${error.message}; tapDiagnostic=${JSON.stringify(await snapshot(page, 'tap_timeout'))}; pageErrors=${JSON.stringify(errors)}`);
  }
  const decisionWarm = await snapshot(page, 'real_touch_tap');
  screenshots.tapMain = await viewportShot(page, overallSelector, `${name}-overall-real-tap-main.png`);

  await overall.scrollIntoViewIfNeeded();
  box = await overall.boundingBox();
  await page.mouse.move(box.x + 100, box.y + 100);
  await page.mouse.down();
  await page.waitForTimeout(60);
  await page.mouse.move(box.x + 170, box.y + 100, { steps: 3 });
  await page.waitForTimeout(80);
  await page.mouse.up();
  await page.waitForFunction(() => window.__lastEmotionDecision && window.__lastEmotionDecision.input.event === 'touch_swipe' &&
    window.__lastEmotionDecision.input.attention === 'right' &&
    window.__v45TouchTrace.some(item => item.kind === 'gesture_classified' && item.event === 'TOUCH_SWIPE' && item.attention === 'right'));
  const decisionSwipe = await snapshot(page, 'real_touch_swipe_right');
  screenshots.swipeMain = await viewportShot(page, overallSelector, `${name}-overall-real-swipe-right-main.png`);

  const beforeAdvance = await snapshot(page, 'before_story_advance');
  await page.waitForTimeout(500);
  const afterAdvance = await snapshot(page, 'after_story_advance');

  const storyName = 'warm_presence';
  const stage = page.locator(`.story-row[data-story="${storyName}"] .live-viewport`);
  await stage.scrollIntoViewIfNeeded();
  box = await stage.boundingBox();
  if (!box) throw new Error(`missing viewport box for ${storyName}`);
  await page.mouse.move(box.x + 100, box.y + 100);
  const targetSelector = `.story-row[data-story="${storyName}"] .live-viewport`;
  await page.mouse.down();
  const heldBeforeMove = await snapshot(page, 'held_before_move');
  const screenshotsBeforeHeld = await viewportShot(page, targetSelector, `${name}-story-warm-before-hold-main.png`);
  await page.waitForTimeout(120);
  await page.mouse.move(box.x + 164, box.y + 54, { steps: 3 });
  await page.waitForTimeout(80);
  const held = await snapshot(page, 'held_drag');
  screenshots.heldMain = await viewportShot(page, targetSelector, `${name}-story-warm-held-drag-main.png`);
  await page.mouse.up();
  await page.waitForTimeout(120);
  const released = await snapshot(page, 'release');
  screenshots.releaseMain = await viewportShot(page, targetSelector, `${name}-story-warm-release-main.png`);
  screenshots.release = await shot(page, `${name}-story-warm-release-full.png`, true);
  screenshots.beforeHeldMain = screenshotsBeforeHeld;
  const parity = await page.evaluate(() => {
    const domains = window.__companionAuthorityDomains;
    const range = value => Array.isArray(value) ? value : [value.min, value.max];
    const valenceRange = range(domains.valence);
    const arousalRange = range(domains.arousal);
    const affinityRange = range(domains.affinity);
    const memoryRange = range(domains.interaction_memory);
    const events = window.__companionAuthorityDebug.authority.events;
    const inputs = [];
    for (const event of events) for (const energy of ['low', 'normal', 'high'])
      for (let valence = valenceRange[0]; valence <= valenceRange[1]; valence++)
        for (let arousal = arousalRange[0]; arousal <= arousalRange[1]; arousal++)
          for (let affinity = affinityRange[0]; affinity <= affinityRange[1]; affinity++)
            for (let interaction_memory = memoryRange[0]; interaction_memory <= memoryRange[1]; interaction_memory++)
              inputs.push({ event, energy, valence, arousal, affinity, interaction_memory });
    const outputs = inputs.map(input => window.__companionAuthorityDecide(input));
    return { cases: inputs.length, outputs };
  });
  await page.close();
  return { viewport, errors, initial, decisionWarm, decisionSwipe, beforeAdvance, afterAdvance, heldBeforeMove, held, released, screenshots, parity };
}

async function runViewport(name, viewport) {
  let browser;
  try {
    browser = await withTimeout(chromium.launch({ headless: true, timeout: 10000 }), 15000, `${name} browser launch`);
    return await withTimeout(runViewportBody(name, viewport, browser), 45000, `${name} verifier`);
  } finally {
    if (browser) {
      try { await withTimeout(browser.close(), 3000, `${name} browser close`); } catch (error) { console.error(`WARN: ${name} browser close: ${error.message}`); }
    }
  }
}

(async () => {
  if (!lockFd) return;
  const result = await withTimeout((async () => ({
    page: pagePath,
    page_sha256: sha256(pagePath),
    viewports: {
      desktop: await runViewport('desktop', { width: 1280, height: 900 }),
      mobile: await runViewport('mobile', { width: 390, height: 844 }),
    },
  }))(), 105000, 'authority-wall verifier');
  const report = path.join(outDir, 'playwright-result.json');
  fs.writeFileSync(report, `${JSON.stringify(result, null, 2)}\n`, 'utf8');
  console.log(`PASS: authority wall Playwright evidence -> ${report}`);
})().catch(error => {
  console.error(error.stack || error);
  process.exitCode = 1;
}).finally(() => {
  if (lockFd) {
    try { fs.closeSync(lockFd); } catch {}
    try { fs.unlinkSync(lockPath); } catch {}
  }
});
