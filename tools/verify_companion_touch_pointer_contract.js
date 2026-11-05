const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { chromium } = require('C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright');

const root = path.resolve(__dirname, '..');
const pagePath = path.join(root, 'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html');
const url = process.env.COMPANION_OVERALL_URL || 'http://127.0.0.1:4173/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html';
const outDir = path.resolve(process.argv[2] || path.join(root, '.cache/validation/companion-touch-pointer-contract-20260723'));
const inputEvidenceSha256 = '846B0B1889F2996623CCAFBBE7A8DC348F97A8278A06FEB29E94B0835DACC21A';
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex').toUpperCase();
const fileSha = file => sha256(fs.readFileSync(file));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (condition, message) => { if (!condition) throw new Error(message); };

fs.mkdirSync(outDir, { recursive: true });
const lockPath = path.join(outDir, '.verifier.lock');
let lockFd;
try { lockFd = fs.openSync(lockPath, 'wx'); fs.writeFileSync(lockFd, `${process.pid}\n`); }
catch { console.error(`NO_GO: verifier lock exists: ${lockPath}`); process.exit(2); }

async function snapshot(page) {
  return page.evaluate(() => ({
    contract: window.__touchContractState(),
    pixels: window.__touchContractSnapshot(),
    decision: window.__lastEmotionDecision || null,
    trace: window.__v45TouchTrace.slice(-16),
    errors: window.__touchPageErrors || [],
  }));
}

function assertNoErrors(errors, label) {
  assert(errors.length === 0, `${label} produced page/HTTP errors: ${JSON.stringify(errors)}`);
}

async function openPage(browser, viewport, errors) {
  const page = await browser.newPage({ viewport, hasTouch: viewport.width < 600 });
  page.setDefaultTimeout(5000);
  page.on('pageerror', error => errors.push(`pageerror:${error.message}`));
  page.on('response', response => { if (response.status() >= 400) errors.push(`http:${response.status()}:${response.url()}`); });
  await page.goto(`${url}?touch-review=comp-req-442`, { waitUntil: 'load', timeout: 8000 });
  await page.locator('#enter-expression').click();
  await page.waitForFunction(() => window.__touchContractState && document.querySelector('#overall-viewport .viewport-frame')?.naturalWidth === 200, null, { timeout: 8000 });
  await sleep(80);
  return page;
}

async function box(page) {
  const target = page.locator('#overall-viewport');
  await target.scrollIntoViewIfNeeded();
  const rect = await target.boundingBox();
  assert(rect, 'overall viewport missing');
  return rect;
}

async function layout(browser, viewport) {
  const errors = []; const page = await openPage(browser, viewport, errors);
  try {
    const rect = await box(page);
    const state = await page.evaluate(() => {
      const visible = element => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      };
      const screen = document.querySelector('#overall-viewport').getBoundingClientRect();
      const storyWall = document.querySelector('#story-wall').getBoundingClientRect();
      const debug = ['.screen-meta', '.decision-panel', '#emotion-rule', '#gesture-status', '.authority-source']
        .map(selector => ({ selector, visible: visible(document.querySelector(selector)) }));
      return {
        viewport_width: window.innerWidth,
        screen_center_x: screen.left + screen.width / 2,
        center_delta_px: Math.abs(screen.left + screen.width / 2 - window.innerWidth / 2),
        emotion: document.querySelector('#emotion-current').innerText.trim(),
        owner_text: document.querySelector('.authority-head').innerText.trim(),
        debug,
        story_count: document.querySelectorAll('#story-wall .story-row').length,
        story_below_screen: storyWall.top > screen.bottom,
      };
    });
    assert(rect.width === 200 && rect.height === 200, `${viewport.name} main screen is not 200x200`);
    assert(state.center_delta_px <= 1, `${viewport.name} main screen is not horizontally centered: ${state.center_delta_px}px`);
    assert(state.debug.every(item => !item.visible), `${viewport.name} debug text remains visible: ${JSON.stringify(state.debug)}`);
    assert(state.emotion.length > 0 && state.emotion.length <= 8, `${viewport.name} emotion label is not concise: ${JSON.stringify(state.emotion)}`);
    assert(!/(当前情绪|命中|输出|registered|authority)/i.test(state.owner_text), `${viewport.name} owner surface exposes debug text: ${JSON.stringify(state.owner_text)}`);
    assert(state.story_count === 16 && state.story_below_screen, `${viewport.name} story wall moved or changed`);
    await page.screenshot({ path: path.join(outDir, `${viewport.name}-layout.png`), fullPage: false });
    assertNoErrors(errors, `${viewport.name} layout`);
    return { ...state, errors };
  } finally { await page.close(); }
}

async function pointer(page, type, kind, x, y, id) {
  await page.evaluate(({ type, kind, x, y, id }) => {
    const stage = document.querySelector('#overall-viewport');
    stage.dispatchEvent(new PointerEvent(kind, { bubbles: true, cancelable: true, pointerId: id,
      pointerType: type, isPrimary: true, clientX: x, clientY: y, buttons: kind === 'pointerup' ? 0 : 1 }));
  }, { type, kind, x, y, id });
}

async function press(page, type, x, y, id) {
  if (type === 'mouse') { await page.mouse.move(x, y); await page.mouse.down(); }
  else await pointer(page, type, 'pointerdown', x, y, id);
}

async function release(page, type, x, y, id) {
  if (type === 'mouse') { await page.mouse.move(x, y); await page.mouse.up(); }
  else await pointer(page, type, 'pointerup', x, y, id);
}

async function movePointer(page, type, x, y, id) {
  if (type === 'mouse') await page.mouse.move(x, y);
  else await pointer(page, type, 'pointermove', x, y, id);
}

async function singleTap(browser, viewport, type, screenshots) {
  const errors = [];
  const page = await openPage(browser, viewport, errors);
  try {
    const r = await box(page); const x = r.x + 158; const y = r.y + 82;
    const before = await page.evaluate(() => { const p=window.__touchContractSnapshot(); return { contract: window.__touchContractState(), pixels: { gaze: p.gaze, layers: p.layers } }; });
    await press(page, type, x, y, 20); await sleep(25); await release(page, type, x, y, 20);
    const pendingState = await page.evaluate(() => window.__touchContractState());
    assert(pendingState.mode === 'expression' && pendingState.pendingTap, `${type} tap did not enter pending expression state at ${await page.evaluate(() => Math.round(performance.now()))}ms: ${JSON.stringify(pendingState)}`);
    await sleep(35);
    const pending = await snapshot(page);
    assert(pending.contract.recordingEntries === 0 && pending.contract.menuEntries === 0, `${type} tap entered an exclusive route`);
    assert(pending.pixels.gaze !== before.pixels.gaze, `${type} tap did not respond gaze to contact`);
    await sleep(420);
    const committed = await snapshot(page);
    assert(committed.contract.mode === 'expression' && committed.contract.recordingEntries === 0 && committed.contract.menuEntries === 0, `${type} single tap left expression`);
    assert(!committed.contract.storyPaused && !committed.contract.storyTouching, `${type} single tap left the story paused`);
    assert(committed.decision && committed.decision.input.event === 'touch_tap', `${type} single tap did not commit TOUCH_TAP after double window`);
    assert(committed.trace.some(item => item.kind === 'single_tap_committed'), `${type} single tap commit trace missing`);
    assert(committed.pixels.gaze !== before.pixels.gaze && committed.pixels.layers.image_nodes === before.pixels.layers.image_nodes, `${type} tap layer/pixel contract failed: before=${JSON.stringify(before.pixels.layers)} after=${JSON.stringify(committed.pixels.layers)}`);
    await page.screenshot({ path: path.join(outDir, `${viewport.width}-${type}-single.png`), fullPage: false });
    assertNoErrors(errors, `${viewport.width}/${type} single`);
    return { type, before, pending, committed, errors };
  } finally { await page.close(); }
}

async function doubleTap(browser, viewport, type) {
  const errors = []; const page = await openPage(browser, viewport, errors);
  try {
    const r = await box(page); const x = r.x + 100; const y = r.y + 100;
    await press(page, type, x, y, 21); await sleep(45); await release(page, type, x, y, 21);
    await sleep(90); await press(page, type, x + 3, y + 2, 22); await sleep(45); await release(page, type, x + 3, y + 2, 22); await sleep(120);
    const result = await snapshot(page);
    assert(result.contract.mode === 'recording' && result.contract.recordingEntries === 1, `${type} double tap did not enter recording exactly once`);
    assert(result.contract.menuEntries === 0, `${type} double tap also entered menu`);
    assert(!result.contract.storyPaused && !result.contract.storyTouching, `${type} double tap left the expression story paused`);
    assert(!result.trace.some(item => item.kind === 'single_tap_committed'), `${type} double tap committed a single tap first`);
    assertNoErrors(errors, `${viewport.width}/${type} double`);
    return { type, result, errors };
  } finally { await page.close(); }
}

async function drag(browser, viewport, type) {
  const errors = []; const page = await openPage(browser, viewport, errors);
  try {
    const r = await box(page);
    const at = (x, y) => ({ x: r.x + x, y: r.y + y });
    const oldContact = at(164, 100);
    await press(page, type, oldContact.x, oldContact.y, 30); await sleep(30);
    await release(page, type, oldContact.x, oldContact.y, 30); await sleep(430);
    const before = await snapshot(page);
    const first = at(28, 100);
    await press(page, type, first.x, first.y, 31); await sleep(45);
    const down = await snapshot(page);
    assert(down.pixels.gaze !== before.pixels.gaze, `${type} pointerdown retained the prior gaze`);
    assert(down.pixels.frame === before.pixels.frame, `${type} pointerdown changed the accepted V9 base frame`);
    assert(down.contract.storyPaused && down.contract.storyTouching, `${type} pointerdown did not freeze the expression story`);
    const directions = [
      ['left', 28, 100],
      ['up', 100, 28],
      ['right', 172, 100],
      ['down', 100, 172],
      ['center', 100, 100],
    ];
    const held = [];
    for (const [name, px, py] of directions) {
      const target = at(px, py);
      await movePointer(page, type, target.x, target.y, 31); await sleep(40);
      const current = await snapshot(page);
      assert(current.pixels.frame === down.pixels.frame, `${type}/${name} changed the base frame while held`);
      assert(current.pixels.layers.image_nodes === down.pixels.layers.image_nodes && current.pixels.layers.gaze_nodes === 1 && current.pixels.layers.visible_images === 2, `${type}/${name} changed face/gaze layer count`);
      assert(current.contract.storyPaused && current.contract.storyTouching, `${type}/${name} resumed choreography during follow`);
      held.push({ name, gaze: current.pixels.gaze, signature: current.pixels.canvasSignature, state: current.contract });
      if (name === 'right') await page.screenshot({ path: path.join(outDir, `${viewport.width}-${type}-directional.png`), fullPage: false });
    }
    assert(held.at(-1).state.activePointer && held.at(-1).state.activePointer.moved, `${type} drag did not cancel into gaze mode`);
    assert(!held.at(-1).state.pendingTap && held.at(-1).state.holdProgress === 0, `${type} drag retained tap/hold state`);
    assert(new Set(held.map(item => item.gaze)).size === directions.length, `${type} directional moves did not replace gaze src for every direction`);
    assert(new Set(held.map(item => item.signature)).size === directions.length, `${type} directional moves did not replace rendered pixels for every direction`);
    const center = at(100, 100);
    await release(page, type, center.x, center.y, 31); await sleep(80);
    const released = await snapshot(page);
    assert(released.contract.mode === 'expression' && released.contract.recordingEntries === 0 && released.contract.menuEntries === 0, `${type} drag entered an exclusive route`);
    assert(released.pixels.gaze === held.at(-1).gaze && released.pixels.canvasSignature === held.at(-1).signature, `${type} drag did not return to the held center pixels`);
    assert(released.pixels.layers.image_nodes === before.pixels.layers.image_nodes && released.pixels.layers.gaze_nodes === 1, `${type} drag changed layer count`);
    assert(!released.contract.storyPaused && !released.contract.storyTouching, `${type} drag release did not resume the story`);
    assertNoErrors(errors, `${viewport.width}/${type} drag`);
    return { type, before, down, held, released, errors };
  } finally { await page.close(); }
}

async function hold(browser, viewport, type) {
  const errors = []; const page = await openPage(browser, viewport, errors);
  try {
    const r = await box(page); const x = r.x + 100; const y = r.y + 100;
    await press(page, type, x, y, 41); await sleep(300); const progress = await snapshot(page);
    assert(progress.contract.mode === 'expression' && progress.contract.holdProgress > 0 && progress.contract.holdProgress < 100, `${type} hold progress is not continuous`);
    await sleep(500); const entered = await snapshot(page);
    assert(entered.contract.mode === 'menu' && entered.contract.menuEntries === 1, `${type} hold did not enter menu exactly once`);
    await release(page, type, x, y, 41); await sleep(100);
    const after = await snapshot(page); assert(after.contract.menuEntries === 1 && after.contract.recordingEntries === 0, `${type} hold duplicated or mixed routes`);
    assertNoErrors(errors, `${viewport.width}/${type} hold`);
    return { type, progress, entered, after, errors };
  } finally { await page.close(); }
}

async function cancellation(browser, viewport, eventName) {
  const errors = []; const page = await openPage(browser, viewport, errors);
  try {
    const r = await box(page); const x = r.x + 110; const y = r.y + 100;
    await press(page, 'touch', x, y, 51); await sleep(80);
    if (eventName === 'blur') await page.evaluate(() => window.dispatchEvent(new Event('blur')));
    else await page.evaluate(({ eventName }) => document.querySelector('#overall-viewport').dispatchEvent(new PointerEvent(eventName, { bubbles: true, cancelable: true, pointerId: 51, pointerType: 'touch' })), { eventName });
    await sleep(120); const result = await snapshot(page); await sleep(720); const settled = await snapshot(page);
    assert(result.contract.mode === 'expression' && !result.contract.activePointer && !result.contract.pendingTap && result.contract.holdProgress === 0, `${eventName} did not clear transient state`);
    assert(!result.contract.storyPaused && !result.contract.storyTouching, `${eventName} left the story paused`);
    assert(settled.contract.menuEntries === 0 && settled.contract.recordingEntries === 0, `${eventName} later triggered a route`);
    assert(result.pixels.layers.image_nodes === settled.pixels.layers.image_nodes && result.pixels.layers.gaze_nodes === 1, `${eventName} changed layers`);
    assertNoErrors(errors, `${viewport.width}/${eventName}`);
    return { eventName, result, settled, errors };
  } finally { await page.close(); }
}

async function run() {
  const browser = await chromium.launch({ headless: true, timeout: 10000 });
  const result = { status: 'NO_GO', requirement: 'COMP-REQ-441/442/447/449', input_evidence_sha256: inputEvidenceSha256,
    page: pagePath, page_sha256: fileSha(pagePath), url, layout: {}, scenarios: {}, negatives: {}, errors: [] };
  try {
    for (const viewport of [{ name: 'desktop', width: 1280, height: 900 }, { name: 'mobile', width: 390, height: 844 }]) {
      result.layout[viewport.name] = await layout(browser, viewport);
      result.scenarios[viewport.name] = {
        mouse_single: await singleTap(browser, viewport, 'mouse'),
        touch_single: await singleTap(browser, viewport, 'touch'),
        pen_single: await singleTap(browser, viewport, 'pen'),
        touch_double: await doubleTap(browser, viewport, 'touch'),
        mouse_drag: await drag(browser, viewport, 'mouse'),
        touch_drag: await drag(browser, viewport, 'touch'),
        pen_drag: await drag(browser, viewport, 'pen'),
        mouse_hold: await hold(browser, viewport, 'mouse'),
      };
      for (const eventName of ['pointercancel', 'lostpointercapture', 'blur']) result.scenarios[viewport.name][eventName] = await cancellation(browser, viewport, eventName);
    }
    result.negatives = { centered_owner_surface_without_debug_text: true,
      double_tap_no_single_commit: true, pointerdown_replaces_prior_gaze: true,
      directional_follow_replaces_src_and_pixels: true, pointer_active_base_frame_frozen: true,
      drag_no_menu_or_recording: true, hold_once: true, cancel_lostcapture_blur_reset: true,
      fixed_face_gaze_nodes: true, no_page_errors_or_404: true };
    result.status = 'PASS';
  } finally {
    result.finished_at = new Date().toISOString();
    fs.writeFileSync(path.join(outDir, 'touch-pointer-contract-result.json'), `${JSON.stringify(result, null, 2)}\n`);
    await browser.close();
  }
  return result;
}

run().then(result => console.log(`PASS: touch pointer contract -> ${path.join(outDir, 'touch-pointer-contract-result.json')}\n${JSON.stringify({ status: result.status, page_sha256: result.page_sha256 }, null, 2)}`))
  .catch(error => { console.error(error.stack || error); process.exitCode = 1; })
  .finally(() => { if (lockFd) { try { fs.closeSync(lockFd); } catch {} try { fs.unlinkSync(lockPath); } catch {} } });
