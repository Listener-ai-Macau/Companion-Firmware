#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, '.cache', 'wba-visual-review', 'art', 'screen-v3');
const art = path.join(root, 'docs', 'art', 'iterations', 'companion-wba-screen-art-v3');
const pageUrl = process.env.COMPANION_SCREEN_ART_URL || 'http://127.0.0.1:8876/art/';
const families = ['calm','curious','delighted','warm','playful','sleepy','bashful','thoughtful','focused','alert'];
const require = createRequire(import.meta.url);
let playwright;
for (const source of [process.env.COMPANION_PLAYWRIGHT_MODULE,'playwright','C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright']) {
  if (!source) continue;
  try { playwright = require(source); break; } catch {}
}
if (!playwright) throw new Error('Playwright unavailable');

const assert = (condition, message) => { if (!condition) throw new Error(message); };
const digestBuffer = value => crypto.createHash('sha256').update(value).digest('hex');
const digest = file => digestBuffer(fs.readFileSync(file));
const frames = JSON.parse(fs.readFileSync(path.join(out, 'frames.json'), 'utf8'));
const layout = JSON.parse(fs.readFileSync(path.join(art, 'layout.json'), 'utf8'));
const buildResult = JSON.parse(fs.readFileSync(path.join(out, 'result.json'), 'utf8'));
const rawFor = id => {
  const metadata = frames[id];
  assert(metadata, `missing logical frame ${id}`);
  const raw = fs.readFileSync(path.join(out, 'native', `${metadata.asset}.bin`));
  assert(raw.length === 5000, `${id}: native frame is ${raw.length} bytes`);
  assert(digestBuffer(raw) === metadata.sha256, `${id}: alias SHA does not match native asset`);
  return raw;
};
const differsIn = (left, right, predicate) => {
  let count = 0;
  for (let y = 0; y < 200; y++) for (let x = 0; x < 200; x++) {
    if (!predicate(x, y)) continue;
    const mask = 0x80 >> (x & 7), offset = y * 25 + (x >> 3);
    if ((left[offset] & mask) !== (right[offset] & mask)) count++;
  }
  return count;
};
const blackIn = (raw, predicate) => {
  let count = 0;
  for (let y = 0; y < 200; y++) for (let x = 0; x < 200; x++) {
    if (!predicate(x, y)) continue;
    if (!(raw[y * 25 + (x >> 3)] & (0x80 >> (x & 7)))) count++;
  }
  return count;
};

assert(buildResult.frames === 10850, `expected 10850 logical combinations, got ${buildResult.frames}`);
assert(buildResult.unique_frame_assets < buildResult.frames, 'logical aliases did not reduce physical frame assets');
assert(buildResult.pack.total_bytes <= 2 * 1024 * 1024, `candidate pack exceeds 2MiB: ${buildResult.pack.total_bytes}`);
assert(buildResult.pixel_layer_collisions === 0, 'builder reported a face/ornament/function collision');
assert(buildResult.preview_html_sha256 === digest(path.join(out, 'index.html')), 'preview_html_sha256 is stale');
let logicalMatrixChecked = 0;
for (const family of families) {
  const poses = [...new Set(Object.values(frames).filter(frame => frame.family === family).map(frame => frame.pose))];
  for (const pose of poses) for (let ornament = 0; ornament < 5; ornament++) {
    const idle = `${pose}__orn${ornament}__none__hold`;
    assert(frames[idle]?.ornament_stage === ornament && frames[idle]?.function === 'none', `missing independent idle key ${idle}`);
    logicalMatrixChecked++;
    for (const item of layout.functional_statuses) for (const stage of ['entered','hold','exit']) {
      const id = `${pose}__orn${ornament}__${item.id}__${stage}`;
      assert(frames[id]?.ornament_stage === ornament && frames[id]?.function === item.id && frames[id]?.function_stage === stage, `missing orthogonal function/ornament key ${id}`);
      logicalMatrixChecked++;
    }
  }
}
assert(logicalMatrixChecked === buildResult.frames, `logical matrix checked ${logicalMatrixChecked}, build reports ${buildResult.frames}`);

// Direct framebuffer checks prove the three clocks are independent before UI testing.
const curiousBase = rawFor('curious-rest__orn3__none__hold');
const curiousRecording = rawFor('curious-rest__orn3__recording_input__hold');
const contentDifference = differsIn(curiousBase, curiousRecording, (x, y) => y >= 16 && y < 172);
assert(contentDifference === 0, `recording changed face/ornament content: ${contentDifference} pixels`);
assert(blackIn(curiousRecording, (x, y) => x >= 140 && x <= 170 && y >= 16 && y <= 60) > 0,
  'recording frame lost the curious author ornament');
const ornamentFrames = [1,2,3].map(stage => rawFor(`curious-rest__orn${stage}__recording_input__hold`));
assert(differsIn(ornamentFrames[0], ornamentFrames[1], (x, y) => y >= 16 && y < 60) > 0 &&
  differsIn(ornamentFrames[1], ornamentFrames[2], (x, y) => y >= 16 && y < 60) > 0,
  'curious ornament stages do not advance');
for (let index = 1; index < ornamentFrames.length; index++) {
  assert(differsIn(ornamentFrames[0], ornamentFrames[index], (x, y) => y >= 60 && y < 172) === 0,
    'ornament clock changed face pixels');
  assert(differsIn(ornamentFrames[0], ornamentFrames[index], (x, y) => x >= 2 && x < 42 && y >= 172 && y < 196) === 0,
    'ornament clock advanced or changed the recording wave');
}
const curiousBlink = rawFor('curious-blink__orn3__recording_input__hold');
assert(differsIn(curiousRecording, curiousBlink, (x, y) => x >= 140 && x <= 170 && y >= 16 && y <= 60) === 0,
  'blink cleared or changed the author ornament');

const defaultOrnaments = layout.default_ornaments;
const selectedFrameIds = families.flatMap(family => [
  `${family}-rest__orn${defaultOrnaments[family]}__none__hold`,
  `${family}-rest__orn${defaultOrnaments[family]}__recording_input__hold`,
  `${family}-blink__orn${defaultOrnaments[family]}__none__hold`,
]);
selectedFrameIds.push(...[0,1,2,3,4].map(stage => `curious-rest__orn${stage}__recording_input__hold`));

const errors = [], failedRequests = [];
const browser = await playwright.chromium.launch({headless: true});
try {
  const page = await browser.newPage({viewport: {width: 1280, height: 1100}});
  page.on('pageerror', error => errors.push(`pageerror: ${error.message}`));
  page.on('console', message => { if (message.type() === 'error') errors.push(`console: ${message.text()}`); });
  page.on('requestfailed', request => { if (request.failure()?.errorText !== 'net::ERR_ABORTED') failedRequests.push(`${request.url()} ${request.failure()?.errorText || ''}`); });
  page.on('response', response => { if (response.status() >= 400) failedRequests.push(`${response.url()} HTTP ${response.status()}`); });
  await page.addInitScript(() => {
    const nativeSetTimeout = window.setTimeout.bind(window);
    window.setTimeout = (callback, delay = 0, ...args) => nativeSetTimeout(callback, delay > 0 ? Math.max(1, Math.round(delay * 0.05)) : 0, ...args);
  });
  await page.goto(pageUrl, {waitUntil: 'networkidle'});
  await page.locator('#gallery .tile').first().waitFor();
  assert((await page.evaluate(() => document.baseURI)).endsWith('/art/screen-v3/'), `active art page is not screen-v3: ${await page.evaluate(() => document.baseURI)}`);
  assert((await page.locator('#gallery .tile').count()) === 10, 'expected ten expression families');
  assert((await page.locator('.screen img').count()) === 1, 'screen must be one complete rendered PNG');
  const pageText = await page.locator('main').innerText();
  assert(pageText.includes('表情饰品') && pageText.includes('功能状态'), 'three-track wording is missing');
  assert(!pageText.includes('小事件'), 'emotion ornaments are still described as small functional events');
  assert((await page.locator('details').textContent()).includes('不代表已经复刻完整 generation 21 动作'), 'generation-21 scope warning is missing');

  const pixelChecks = await page.evaluate(async ids => {
    const loadImage = source => new Promise((resolve, reject) => { const image = new Image(); image.onload = async () => { try { await image.decode(); resolve(image); } catch (error) { reject(error); } }; image.onerror = () => reject(new Error(`cannot load ${source}`)); image.src = source; });
    const results = [];
    for (const id of ids) {
      const metadata = ART.frames[id], asset = metadata.asset;
      const imageUrl = new URL(`images/${asset}.png`, document.baseURI).href;
      const binaryUrl = new URL(`native/${asset}.bin`, document.baseURI).href;
      const [image, response] = await Promise.all([loadImage(imageUrl), fetch(binaryUrl)]);
      if (!response.ok) throw new Error(`${binaryUrl}: HTTP ${response.status}`);
      const expected = new Uint8Array(await response.arrayBuffer()), canvas = document.createElement('canvas');
      canvas.width = 200; canvas.height = 200;
      const context = canvas.getContext('2d', {willReadFrequently: true}); context.imageSmoothingEnabled = false; context.drawImage(image, 0, 0);
      const rgba = context.getImageData(0, 0, 200, 200).data, actual = new Uint8Array(5000).fill(0);
      let nonBinaryPixels = 0;
      for (let y = 0; y < 200; y++) for (let x = 0; x < 200; x++) { const offset = (y * 200 + x) * 4, r = rgba[offset], g = rgba[offset + 1], b = rgba[offset + 2], a = rgba[offset + 3]; if (a !== 255 || !((r === 0 && g === 0 && b === 0) || (r === 255 && g === 255 && b === 255))) nonBinaryPixels++; if (r >= 128) actual[y * 25 + (x >> 3)] |= 0x80 >> (x & 7); }
      let differentBytes = Math.abs(expected.length - actual.length); for (let index = 0; index < Math.min(expected.length, actual.length); index++) if (expected[index] !== actual[index]) differentBytes++;
      results.push({id, asset, width: image.naturalWidth, height: image.naturalHeight, binaryBytes: expected.length, differentBytes, nonBinaryPixels});
    }
    return results;
  }, selectedFrameIds);
  assert(pixelChecks.every(check => check.width === 200 && check.height === 200 && check.binaryBytes === 5000 && check.differentBytes === 0 && check.nonBinaryPixels === 0), `PNG/native framebuffer mismatch: ${JSON.stringify(pixelChecks.filter(check => check.width !== 200 || check.height !== 200 || check.binaryBytes !== 5000 || check.differentBytes !== 0 || check.nonBinaryPixels !== 0))}`);

  const desktop = await page.evaluate(() => { const screen = document.querySelector('.screen'), image = document.querySelector('#face'), bounds = screen.getBoundingClientRect(); return {screen:[bounds.width,bounds.height],screenRadius:getComputedStyle(screen).borderRadius,imageRadius:getComputedStyle(image).borderRadius,rendering:getComputedStyle(image).imageRendering,thumbs:[...document.querySelectorAll('#gallery .tile img')].map(item=>{const box=item.getBoundingClientRect();return [box.width,box.height,getComputedStyle(item).borderRadius,getComputedStyle(item).imageRendering];})}; });
  assert(desktop.screen[0] === 400 && desktop.screen[1] === 400, `desktop not exact 2x: ${desktop.screen}`);
  assert(desktop.screenRadius === '0px' && desktop.imageRadius === '0px', 'screen has rounded corners');
  assert(desktop.rendering === 'pixelated' && desktop.thumbs.every(([w,h,r,rendering]) => w === 200 && h === 200 && r === '0px' && rendering === 'pixelated'), 'preview is not integer-scaled square pixel art');
  const waitFrame = id => page.waitForFunction(expected => { const image=document.querySelector('#face'); return image.dataset.frame===expected && image.complete && image.naturalWidth===200; }, id);

  await page.selectOption('#family', 'curious');
  await waitFrame('curious-rest__orn3__none__hold');
  await page.selectOption('#functional', 'recording_input');
  await waitFrame('curious-rest__orn3__recording_input__hold');
  await page.evaluate(async () => { await Promise.all([0,1,2,3,4].map(stage => picture(`curious-rest__orn${stage}__recording_input__hold`))); });
  await page.evaluate(() => { window.__ornamentTrace=[]; const image=document.querySelector('#face'); window.__ornamentObserver?.disconnect(); window.__ornamentObserver=new MutationObserver(()=>window.__ornamentTrace.push({frame:image.dataset.frame,pose:image.dataset.pose,ornament:image.dataset.ornament,functional:image.dataset.functional,functionalStage:image.dataset.functionalStage})); window.__ornamentObserver.observe(image,{attributes:true,attributeFilter:['data-ornament']}); });
  await page.locator('#ornament-play').click();
  await page.waitForTimeout(460);
  const ornamentTrace = await page.evaluate(() => window.__ornamentTrace);
  assert([0,1,2,3,4].every(stage => ornamentTrace.some(item => +item.ornament === stage)), `five-stage ornament trace incomplete: ${JSON.stringify(ornamentTrace)}`);
  assert(ornamentTrace.every(item => item.pose === 'curious-rest' && item.functional === 'recording_input' && item.functionalStage === 'hold'), `ornament clock changed face/function track: ${JSON.stringify(ornamentTrace)}`);

  await page.evaluate(() => { cancelOrnament(); setOrnament(3); });
  await waitFrame('curious-rest__orn3__recording_input__hold');
  await page.locator('#blink').click();
  await waitFrame('curious-blink__orn3__recording_input__hold');
  await waitFrame('curious-rest__orn3__recording_input__hold');
  assert((await page.locator('#face').getAttribute('data-ornament')) === '3', 'blink reset the ornament stage');

  await page.evaluate(() => { cancelOrnament(); setOrnament(2); });
  await waitFrame('curious-rest__orn2__recording_input__hold');
  await page.selectOption('#functional', 'upgrade_progress');
  await waitFrame('curious-rest__orn2__upgrade_progress__hold');
  assert((await page.locator('#face').getAttribute('data-ornament')) === '2', 'non-recording function reset the ornament stage');

  await page.evaluate(() => { window.__cancelTrace=[]; const image=document.querySelector('#face'); window.__cancelObserver?.disconnect(); window.__cancelObserver=new MutationObserver(()=>window.__cancelTrace.push(image.dataset.frame)); window.__cancelObserver.observe(image,{attributes:true,attributeFilter:['data-frame']}); });
  await page.locator('#ornament-play').click();
  await page.waitForTimeout(35);
  await page.locator('#ornament-stop').click();
  const stopped = await page.locator('#face').getAttribute('data-frame');
  await page.waitForTimeout(420);
  assert((await page.locator('#face').getAttribute('data-frame')) === stopped, 'cancelled ornament timer overwrote the restored stage');
  await page.locator('#functional-play').click();
  await page.waitForFunction(() => document.querySelector('#face').dataset.functionalStage === 'entered');
  await page.locator('#functional-stop').click();
  await page.selectOption('#functional', 'saving');
  await page.waitForTimeout(220);
  assert((await page.locator('#face').getAttribute('data-functional')) === 'saving' && (await page.locator('#face').getAttribute('data-functional-stage')) === 'hold', 'cancelled functional timer overwrote the new status');

  // Leave the review image on the clearest three-track example.
  await page.selectOption('#functional', 'recording_input');
  await page.evaluate(() => { cancelFace(); cancelOrnament(); cancelFunctional(); pose='curious-rest'; setOrnament(3); const item=FUNCTIONS.find(value=>value.id==='recording_input'); setFunctionalStage(item,'hold'); });
  await waitFrame('curious-rest__orn3__recording_input__hold');
  await page.locator('[data-scale="1"]').click(); let box=await page.locator('.screen').boundingBox(); assert(box.width===200&&box.height===200,`desktop 1x is not 200x200: ${JSON.stringify(box)}`);
  await page.locator('[data-scale="2"]').click(); box=await page.locator('.screen').boundingBox(); assert(box.width===400&&box.height===400,`desktop 2x is not 400x400: ${JSON.stringify(box)}`);
  await page.screenshot({path:path.join(out,'screen-v3-desktop.png'),fullPage:true});
  await page.locator('.hero').screenshot({path:path.join(out,'screen-v3-three-tracks.png')});
  await page.locator('#gallery').screenshot({path:path.join(out,'screen-v3-gallery.png')});

  await page.setViewportSize({width:390,height:844}); await page.reload({waitUntil:'networkidle'}); await page.locator('#gallery .tile').first().waitFor();
  box=await page.locator('.screen').boundingBox(); assert(box.width===200&&box.height===200,`mobile default is not 1x: ${JSON.stringify(box)}`);
  assert(!(await page.evaluate(() => document.documentElement.scrollWidth>innerWidth)),'mobile page horizontally overflows');
  await page.locator('[data-scale="2"]').click(); const mobile=await page.evaluate(()=>{const viewport=document.querySelector('.viewport'),screen=document.querySelector('.screen').getBoundingClientRect();return {screen:[screen.width,screen.height],localScroll:viewport.scrollWidth>viewport.clientWidth,documentOverflow:document.documentElement.scrollWidth>innerWidth};});
  assert(mobile.screen[0]===400&&mobile.screen[1]===400&&mobile.localScroll&&!mobile.documentOverflow,`mobile 2x must scroll locally: ${JSON.stringify(mobile)}`);
  await page.locator('[data-scale="1"]').click(); await page.screenshot({path:path.join(out,'screen-v3-mobile.png'),fullPage:true});

  assert(errors.length===0,errors.join('\n')); assert(failedRequests.length===0,`failed requests:\n${failedRequests.join('\n')}`);
  const result={result:'PASS_WBA_SCREEN_ART_BROWSER_CHECK',claim:'HOST_C_RENDERED_SCREEN_PREVIEW_ONLY',artAcceptance:'NOT_CLAIMED',hardwareAcceptance:'NOT_RUN',timingScope:'Browser timers accelerated to test logical track independence and cancellation; physical e-paper timing not covered.',pageUrl,logicalFrames:buildResult.frames,logicalFrameMatrixChecked:logicalMatrixChecked,uniqueFrameAssets:buildResult.unique_frame_assets,logicalFrameAliases:buildResult.logical_frame_aliases,candidatePackBytes:buildResult.pack.total_bytes,preview_html_sha256:digest(path.join(out,'index.html')),familiesChecked:families,selectedPixelFrames:selectedFrameIds.length,selectedPixelChecks:pixelChecks,directPixelChecks:{recordingPreservedOrnament:true,ornamentClockKeptFace:true,ornamentClockKeptWave:true,blinkPreservedOrnament:true},checks:['single-complete-screen-image','logical-frame-alias-sha','selected-canvas-png-equals-native','five-stage-author-ornament-with-recording','ornament-clock-does-not-advance-face-or-wave','blink-preserves-ornament','all-functional-states-preserve-current-ornament','timer-cancellation','square-no-radius-integer-scale','mobile-no-document-overflow','mobile-2x-local-scroll'],screenshots:['screen-v3-desktop.png','screen-v3-three-tracks.png','screen-v3-gallery.png','screen-v3-mobile.png'],sourceSha256:{'tools/check_wba_screen_art.mjs':digest(fileURLToPath(import.meta.url)),'tools/wba_screen_art_preview.html':digest(path.join(root,'tools','wba_screen_art_preview.html')),'tools/build_wba_screen_art.py':digest(path.join(root,'tools','build_wba_screen_art.py'))},errors,failedRequests};
  fs.writeFileSync(path.join(out,'screen-browser-result.json'),`${JSON.stringify(result,null,2)}\n`);
  console.log('PASS_WBA_SCREEN_ART_BROWSER_CHECK: three orthogonal tracks, alias/native pixels, timers, desktop/mobile');
} finally { await browser.close(); }
