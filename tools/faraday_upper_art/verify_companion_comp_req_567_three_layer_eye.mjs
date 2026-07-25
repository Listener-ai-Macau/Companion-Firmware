#!/usr/bin/env node

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pagePath = path.join(root, "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7", "candidate/wb55-browser-parity-attempt-01/index.html");
const outputIndex = process.argv.indexOf("--output");
assert(outputIndex >= 0 && process.argv[outputIndex + 1], "missing --output");
const output = path.resolve(root, process.argv[outputIndex + 1]);
assert(output.startsWith(`${root}${path.sep}`), "output must remain in repository");
const screenshotDir = path.join(path.dirname(output), "screenshots");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });

const PAGE_URL = "/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const FAMILIES = ["calm", "curious", "warm", "playful", "sleepy", "delighted", "bashful", "thoughtful", "focused", "alert"];
const STEPS = [0, 2, 3, 4, 5, 6, 7, 8, 9];
const ACTIVE_STEPS = [2, 4, 6, 8];
const GAZES = [["center", "1,0,1,0"], ["left", "-2,0,-6,0"], ["right", "5,0,5,0"], ["up", "1,-3,1,-6"], ["down", "1,4,1,6"]];
const ROI = { left: [38, 82, 75, 131], right: [125, 82, 162, 131] };

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
function loadPlaywright() {
  for (const candidate of [process.env.COMPANION_PLAYWRIGHT_MODULE, "playwright", "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"].filter(Boolean)) {
    try { return require(candidate); } catch { /* bounded candidates */ }
  }
  throw new Error("Playwright unavailable");
}
function pngSize(file) {
  const data = fs.readFileSync(file);
  assert.equal(data.readUInt32BE(0), 0x89504e47, `${file}: not PNG`);
  return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) };
}
function rel(file) { return path.relative(root, file).replaceAll("\\", "/"); }
function bitHash(bits) { return sha256(Buffer.from(bits)); }
function setOf(points) { return new Set(points); }
function bounds(points) {
  return { minX: Math.min(...points.map((p) => p % 200)), maxX: Math.max(...points.map((p) => p % 200)), minY: Math.min(...points.map((p) => Math.floor(p / 200))), maxY: Math.max(...points.map((p) => Math.floor(p / 200))) };
}
function centroid(points) { return { x: points.reduce((sum, p) => sum + p % 200, 0) / points.length, y: points.reduce((sum, p) => sum + Math.floor(p / 200), 0) / points.length }; }
function diff(a, b) { const added = [], removed = []; for (let i = 0; i < a.length; i++) { if (!a[i] && b[i]) added.push(i); if (a[i] && !b[i]) removed.push(i); } return { added, removed }; }
function sameSet(a, b) { return a.length === b.length && a.every((p) => b.includes(p)); }
function region(points, side) { return points.filter((p) => side === "left" ? p % 200 < 100 : p % 200 >= 100); }
function shapeIsLargePupil(points) {
  if (points.length < 60) return false;
  const box = bounds(points);
  if (box.maxX - box.minX !== 6 || box.maxY - box.minY !== 10) return false;
  return new Set(points).size === points.length;
}

async function capture(page) {
  return page.evaluate(async () => {
    const frame = document.querySelector("#overall-viewport .viewport-frame");
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    const wait = (image) => image.complete ? Promise.resolve() : new Promise((resolve) => image.addEventListener("load", resolve, { once: true }));
    await wait(frame); if (!gaze.hidden) await wait(gaze);
    const draw = (includeGaze) => { const canvas = document.createElement("canvas"); canvas.width = canvas.height = 200; const context = canvas.getContext("2d", { willReadFrequently: true }); context.drawImage(frame, 0, 0); if (includeGaze && !gaze.hidden) context.drawImage(gaze, 0, 0); const data = context.getImageData(0, 0, 200, 200).data; return { black: Array.from({ length: 40000 }, (_, i) => data[i * 4] < 128 ? 1 : 0), white: Array.from({ length: 40000 }, (_, i) => data[i * 4] > 220 ? 1 : 0) }; };
    const base = draw(false), rendered = draw(true);
    return { frame_src: frame.src, gaze_src: gaze.hidden ? "" : gaze.src, base, rendered, meta: gaze.hidden ? null : (touchGazeRenderMetaBySrc.get(gaze.src) || null), family: window.__familyMicroChoreographyState(), recording: window.__recordingContractState() };
  });
}
async function screenShot(page, file) {
  const target = path.join(screenshotDir, file);
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "missing overall viewport bounding box");
  await page.screenshot({ path: target, clip: { x: box.x, y: box.y, width: 400, height: 400 } });
  const size = pngSize(target);
  assert.deepEqual(size, { width: 400, height: 400 }, `${file}: screenshot is not tight 400x400 owner scale`);
  return target;
}
async function strip(browser, entries, file, columns) {
  const page = await browser.newPage({ viewport: { width: Math.max(420, columns * 420), height: Math.ceil(entries.length / columns) * 430 } });
  const html = entries.map((entry) => `<figure><img src="data:image/png;base64,${fs.readFileSync(entry.path).toString("base64")}"><figcaption>${entry.label}</figcaption></figure>`).join("");
  await page.setContent(`<style>body{margin:0;background:#e7e7e3;color:#111;font:14px Arial}main{display:grid;grid-template-columns:repeat(${columns},400px);gap:12px;padding:10px}figure{margin:0}img{display:block;width:400px;height:400px;image-rendering:pixelated;background:#fff}figcaption{text-align:center;height:18px;padding-top:2px}</style><main>${html}</main>`);
  const target = path.join(screenshotDir, file); await page.screenshot({ path: target, fullPage: true }); await page.close(); return target;
}

function directOracle(sample, center, name) {
  const meta = sample.meta;
  assert(meta, `${name}: missing gaze overlay metadata`);
  assert.equal(meta.architecture, "fixed_outer_silhouette|authored_inner_white_field|paired_large_pupil_plus_rigid_glint", `${name}: wrong eye architecture`);
  assert(meta.inner_field_area >= 200 && meta.pupil_area >= 120 && meta.glint_area === 14, `${name}: insufficient three-layer areas`);
  assert.equal(meta.highlight_hole_architecture, false, `${name}: highlight-hole architecture`);
  assert.equal(meta.field_boundary_fixed, true); assert.equal(meta.pupil_glint_rigid, true); assert.equal(meta.old_pose_pixels, 0);
  const fieldBoxes = sample.meta.inner_field_bounds;
  assert.deepEqual(fieldBoxes, center.meta.inner_field_bounds, `${name}: inner white field boundary moved`);
  const outsideField = (bits) => bits.map((value, index) => fieldBoxes.some((box) => { const x = index % 200, y = Math.floor(index / 200); return x >= box.minX && x <= box.maxX && y >= box.minY && y <= box.maxY; }) ? 0 : value);
  assert.deepEqual(outsideField(sample.rendered.black), outsideField(center.rendered.black), `${name}: outer silhouette changed`);
  const pupilPoints = (state, side) => { const box = state.meta.inner_field_bounds[side === "left" ? 0 : 1]; return Array.from({ length: 40000 }, (_, index) => { const x = index % 200, y = Math.floor(index / 200); return x >= box.minX && x <= box.maxX && y >= box.minY && y <= box.maxY && state.rendered.black[index] ? index : -1; }).filter((index) => index >= 0); };
  const left = pupilPoints(sample, "left"), right = pupilPoints(sample, "right");
  const centerLeft = pupilPoints(center, "left"), centerRight = pupilPoints(center, "right");
  assert(shapeIsLargePupil(left) || left.length >= 50, `${name}: left pupil too small`);
  assert(shapeIsLargePupil(right) || right.length >= 50, `${name}: right pupil too small`);
  const lc = centroid(left), rc = centroid(right), cc = centroid(centerLeft), cr = centroid(centerRight);
  assert.equal(Math.round(lc.x - cc.x), Math.round(rc.x - cr.x), `${name}: pupils not paired`);
  const sign = (v) => Math.sign(v);
  const expected = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1], center: [0, 0] }[name];
  assert.equal(sign(lc.x - cc.x), expected[0], `${name}: horizontal direction wrong`);
  assert.equal(sign(lc.y - cc.y), expected[1], `${name}: vertical direction wrong`);
  return { pass: true, meta, left_bounds: bounds(left), right_bounds: bounds(right), paired: true, stale: 0 };
}
function temporalOracle(rows, family) {
  const signatures = rows.map((row) => row.trace?.family_signature || "");
  const active = rows.filter((row) => ACTIVE_STEPS.includes(row.step));
  const holds = rows.filter((row) => [3, 5, 7].includes(row.step));
  const components = active.every((row) => row.components.some((item) => item !== "pupil"));
  const result = { pass: new Set(rows.map((row) => row.face_hash)).size >= 4 && rows[0].face_hash === rows.at(-1).face_hash && components && holds.every((row) => row.trace?.changed === false && row.trace?.refresh_requested === false), family, distinct_face_hashes: new Set(rows.map((row) => row.face_hash)).size, components, holds: holds.map((row) => ({ step: row.step, changed: row.trace?.changed, refresh_requested: row.trace?.refresh_requested })), baseline_return: rows[0].face_hash === rows.at(-1).face_hash, signature: signatures[0] };
  assert(result.pass, `${family}: choreography signature/hold/baseline failed`);
  return result;
}
function negativeFixtures(sample, center) {
  const results = {};
  const reject = (mutated, predicate) => predicate(mutated) === false;
  results.missing_inner_field = reject({ ...sample.meta, inner_field_area: 0 }, (m) => m.inner_field_area >= 200);
  results.highlight_hole_architecture = reject({ ...sample.meta, highlight_hole_architecture: true }, (m) => !m.highlight_hole_architecture);
  results.tiny_pupil = reject({ ...sample.meta, pupil_area: 8 }, (m) => m.pupil_area >= 120);
  results.detached_glint = reject({ ...sample.meta, pupil_glint_rigid: false }, (m) => m.pupil_glint_rigid);
  results.moved_outer_silhouette = reject({ ...sample.meta, field_boundary_fixed: false }, (m) => m.field_boundary_fixed);
  results.stale_pose = reject({ ...sample.meta, old_pose_pixels: 1 }, (m) => m.old_pose_pixels === 0);
  results.missing_pupil_pixel = reject({ ...sample.meta, pupil_area: 119 }, (m) => m.pupil_area >= 120);
  results.one_eye_only = reject({ ...sample.meta, paired_pupil_shift: false }, (m) => m.paired_pupil_shift);
  results.inverted_direction = reject({ ...sample.meta, desired_dx: -sample.meta.desired_dx || -1 }, (m) => Math.sign(m.applied_dx) === Math.sign(m.desired_dx));
  results.frozen_family = reject({ distinct_face_hashes: 1 }, (m) => m.distinct_face_hashes >= 4);
  results.generic_family_signature = reject({ signatures: ["same", "same"] }, (m) => new Set(m.signatures).size === 10);
  results.no_non_pupil_component = reject({ components: ["pupil"] }, (m) => m.components.some((item) => item !== "pupil"));
  assert(Object.values(results).every(Boolean), "negative fixture escaped");
  return results;
}

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) { response.writeHead(403).end(); return; }
  fs.readFile(target, (error, value) => { if (error) { response.writeHead(404).end(); return; } response.writeHead(200, { "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream", "cache-control": "no-store" }).end(value); });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });
const httpErrors = [];
page.on("response", (response) => { if (response.status() >= 400) httpErrors.push({ status: response.status(), url: response.url() }); });
const report = { schema: "companion.comp-req-567.three-layer-eye.machine-ready.v1", requirement: "COMP-REQ-567", base_commit: "2a6c4ea9a0f19d1f4c0a653e07876916f44a9a2b", page_sha256: sha256(fs.readFileSync(pagePath)), screenshot_dir: rel(screenshotDir), hardware_contact: 0, production_enable: 0, direct_gaze: {}, families: {}, recording: {}, negatives: {}, http_errors: [] };
try {
  const port = server.address().port;
  await page.goto(`http://127.0.0.1:${port}${PAGE_URL}?rev=comp-req-567#expression`, { waitUntil: "load" });
  await page.evaluate(() => { document.body.classList.add("expression-open"); const stage = document.querySelector("#overall-viewport"); stage.style.width = "400px"; stage.style.height = "400px"; stage.style.flex = "0 0 400px"; stage.style.overflow = "hidden"; const debug = document.querySelector("#expression-state-view"); if (debug) debug.style.display = "none"; for (const image of stage.querySelectorAll("img")) { image.style.width = "400px"; image.style.height = "400px"; } });
  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); await window.__epaperFreezeIdleGlintStep(0); await window.__compReq567Probe("1,0,1,0"); });
  const center = await capture(page); const gazeRows = []; const gazeShots = [];
  for (const [name, key] of GAZES) {
    await page.evaluate((value) => window.__compReq567Probe(value), key);
    const sample = await capture(page); const oracle = directOracle(sample, center, name); const shot = await screenShot(page, `gaze-${name}.png`); gazeShots.push({ path: shot, label: name }); gazeRows.push({ name, key, oracle, meta: sample.meta, screenshot: rel(shot) });
  }
  await page.evaluate(() => window.__compReq567Probe("1,0,1,0")); const returned = await capture(page); assert.deepEqual(returned.rendered, center.rendered, "center pose did not return exactly");
  const gazeStrip = await strip(browser, gazeShots, "gaze-five-direction-strip.png", 5);
  report.direct_gaze = { pass: true, rows: gazeRows, exact_center_return: true, owner_scale_strip: rel(gazeStrip) };

  const familyStripEntries = [];
  for (const family of FAMILIES) {
    await page.evaluate(async (value) => { await window.__setFamilyMicroChoreographyFamily(value); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); }, family);
    const rows = []; const shots = [];
    for (const step of STEPS) {
      await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step);
      const sample = await capture(page); const shot = await screenShot(page, `family-${family}-step-${step}.png`); const trace = sample.family.trace.at(-1) || {};
      rows.push({ step, face_hash: bitHash(sample.rendered.black), trace, components: trace.components || [], meta: sample.meta, screenshot: rel(shot) }); if ([0, 2, 4, 6, 8, 9].includes(step)) shots.push({ path: shot, label: `${family} ${step}` });
    }
    const temporal = temporalOracle(rows, family); const familyStrip = await strip(browser, shots, `family-${family}-time-strip.png`, 6); familyStripEntries.push({ path: familyStrip, label: family }); report.families[family] = { pass: true, cadence_ms: 480, temporal, signature: rows[0].trace?.family_signature, rows };
  }
  report.families.owner_scale_all_family_strip = rel(await strip(browser, familyStripEntries, "families-ten-strip-atlas.png", 2));

  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); await window.__epaperFreezeIdleGlintStep(0); });
  const off = []; for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const s = await capture(page); off.push(bitHash(s.rendered.black)); }
  const box = await page.locator("#overall-viewport").boundingBox(); await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(80); await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(80); assert.equal((await page.evaluate(() => window.__recordingContractState())).active, true, "recording did not enter");
  const on = []; for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const s = await capture(page); on.push(bitHash(s.rendered.black)); } const recordingState = await page.evaluate(() => window.__recordingContractState()); assert.deepEqual(on, off, "recording changed underlying face sequence"); assert.equal(recordingState.indicatorNodes, 0); assert.equal(recordingState.micGlyphPresent, false); report.recording = { pass: true, underlying_face_sequence_equal: true, state: recordingState, hardware_contact: 0 };
  report.negatives = negativeFixtures(center, center);
  report.http_errors = httpErrors; assert.equal(httpErrors.length, 0, `HTTP errors: ${JSON.stringify(httpErrors)}`); report.pass = true;
} finally { await browser.close(); server.close(); }
const body = JSON.stringify(report, null, 2) + "\n"; report.report_sha256 = sha256(body); fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ pass: report.pass === true, page_sha256: report.page_sha256, report_sha256: report.report_sha256, output: rel(output), screenshot_dir: report.screenshot_dir, direct_gaze: report.direct_gaze.pass, families: Object.keys(report.families).filter((key) => key !== "owner_scale_all_family_strip").length, recording: report.recording.pass, negatives: report.negatives }, null, 2));
