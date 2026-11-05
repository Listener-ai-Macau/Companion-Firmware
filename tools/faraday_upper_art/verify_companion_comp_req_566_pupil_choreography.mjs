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
const CYCLE_STEPS = [0, 2, 3, 4, 5, 6, 7, 8, 9];
const ACTIVE_STEPS = [2, 4, 6, 8];
const GAZES = [["center", "1,0,1,0"], ["left", "-2,0,-6,0"], ["right", "5,0,5,0"], ["up", "1,-3,1,-6"], ["down", "1,4,1,6"]];
const PATTERN = ["01110", "11111", "11111", "11111", "11111", "11111", "01110"];

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}
function loadPlaywright() {
  for (const candidate of [process.env.COMPANION_PLAYWRIGHT_MODULE, "playwright", "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"].filter(Boolean)) {
    try { return require(candidate); } catch { /* bounded candidates */ }
  }
  throw new Error("Playwright unavailable");
}
function bitDiff(base, rendered) {
  const added = [], removed = [];
  for (let index = 0; index < base.length; index++) {
    if (base[index] === 0 && rendered[index] === 1) added.push(index);
    if (base[index] === 1 && rendered[index] === 0) removed.push(index);
  }
  return { added, removed };
}
function patternShape(points) {
  if (points.length !== 31) return false;
  const minX = Math.min(...points.map((index) => index % 200));
  const minY = Math.min(...points.map((index) => Math.floor(index / 200)));
  const set = new Set(points);
  if (Math.max(...points.map((index) => index % 200)) - minX !== 4) return false;
  if (Math.max(...points.map((index) => Math.floor(index / 200))) - minY !== 6) return false;
  for (let y = 0; y < 7; y++) for (let x = 0; x < 5; x++) {
    if ((PATTERN[y][x] === "1") !== set.has((minY + y) * 200 + minX + x)) return false;
  }
  return true;
}
function pupilPoseOracle(sample, centerRendered, expectedDirection) {
  const { added, removed } = bitDiff(sample.base, sample.rendered);
  if (removed.length) return { pass: false, reason: "outer_or_white_pixels_changed", removed: removed.length };
  if (sample.meta?.open_eye_count === 0) return { pass: added.length === 0, reason: added.length ? "closed_frame_has_pupil" : "closed_without_pupil", added: added.length };
  if (sample.meta?.open_eye_count !== 2 || added.length !== 62) return { pass: false, reason: "pupil_count_or_pair_mismatch", added: added.length };
  const left = added.filter((index) => index % 200 < 100);
  const right = added.filter((index) => index % 200 >= 100);
  if (!patternShape(left) || !patternShape(right)) return { pass: false, reason: "authored_5x7_shape_mismatch" };
  const centerAdded = bitDiff(sample.base, centerRendered).added;
  const centerLeft = centerAdded.filter((index) => index % 200 < 100);
  const centerRight = centerAdded.filter((index) => index % 200 >= 100);
  const centroid = (points) => ({ x: points.reduce((sum, index) => sum + index % 200, 0) / points.length, y: points.reduce((sum, index) => sum + Math.floor(index / 200), 0) / points.length });
  const leftShift = { x: centroid(left).x - centroid(centerLeft).x, y: centroid(left).y - centroid(centerLeft).y };
  const rightShift = { x: centroid(right).x - centroid(centerRight).x, y: centroid(right).y - centroid(centerRight).y };
  if (leftShift.x !== rightShift.x || leftShift.y !== rightShift.y) return { pass: false, reason: "paired_pupil_shift_mismatch", leftShift, rightShift };
  const sign = (value) => Math.sign(value);
  if (sign(leftShift.x) !== sign(expectedDirection.dx) || sign(leftShift.y) !== sign(expectedDirection.dy)) return { pass: false, reason: "pupil_direction_inverted", leftShift, expectedDirection };
  return { pass: true, added: added.length, leftShift, rightShift, stale: 0, outer_fixed: true, white_fixed: true };
}
function temporalOracle(rows) {
  const hashes = rows.map((row) => row.face_hash);
  const active = rows.filter((row) => ACTIVE_STEPS.includes(row.step));
  const components = active.every((row) => row.components.some((component) => component !== "pupil"));
  const holds = rows.filter((row) => [3, 5, 7].includes(row.step)).every((row) => row.trace?.changed === false && row.trace?.refresh_requested === false);
  const baselineReturn = hashes[0] === hashes.at(-1);
  return { pass: new Set(hashes).size >= 4 && components && holds && baselineReturn, distinct_face_hashes: new Set(hashes).size, components, holds, baseline_return: baselineReturn };
}
function mutationNegative(sample, centerRendered, expectedDirection, kind) {
  const rendered = [...sample.rendered];
  const diff = bitDiff(sample.base, rendered).added;
  if (kind === "missing_pupil") rendered[diff[0]] = sample.base[diff[0]];
  if (kind === "extra_pupil") {
    const extra = Array.from({ length: 40000 }, (_, index) => index).find((index) => sample.base[index] === 0 && !diff.includes(index) && index % 200 >= 34 && index % 200 < 166 && Math.floor(index / 200) >= 82 && Math.floor(index / 200) < 136);
    rendered[extra] = 1;
  }
  if (kind === "inverted_direction") {
    const left = diff.filter((index) => index % 200 < 100), right = diff.filter((index) => index % 200 >= 100);
    const shift = expectedDirection.dx || expectedDirection.dy;
    const step = shift > 0 ? -2 : 2;
    for (const index of [...left, ...right]) rendered[index] = sample.base[index];
    const minXs = [Math.min(...left.map((index) => index % 200)), Math.min(...right.map((index) => index % 200))];
    for (const [offset, minX] of minXs.entries()) for (let y = 0; y < 7; y++) for (let x = 0; x < 5; x++) if (PATTERN[y][x] === "1") rendered[(Math.floor(diff[offset * 31] / 200) + y) * 200 + minX + x + step] = 1;
  }
  if (kind === "moved_outer_eye") {
    const eyeBlack = Array.from({ length: 40000 }, (_, index) => index).find((index) => sample.base[index] === 1 && index % 200 >= 34 && index % 200 < 166 && Math.floor(index / 200) >= 82 && Math.floor(index / 200) < 136 && !diff.includes(index));
    rendered[eyeBlack] = 0;
  }
  if (kind === "one_eye_only") for (const index of diff.filter((value) => value % 200 >= 100)) rendered[index] = sample.base[index];
  return pupilPoseOracle({ ...sample, rendered }, centerRendered, expectedDirection).pass === false;
}
async function capture(page) {
  return page.evaluate(async () => {
    const frame = document.querySelector("#overall-viewport .viewport-frame");
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    const waitImage = (image) => image.complete ? Promise.resolve() : new Promise((resolve) => image.addEventListener("load", resolve, { once: true }));
    await waitImage(frame); if (!gaze.hidden) await waitImage(gaze);
    const make = (draw) => { const canvas = document.createElement("canvas"); canvas.width = canvas.height = 200; const context = canvas.getContext("2d", { willReadFrequently: true }); draw(context); const data = context.getImageData(0, 0, 200, 200).data; return Array.from({ length: 40000 }, (_, index) => data[index * 4] < 128 ? 1 : 0); };
    return { frame_src: frame.src, gaze_src: gaze.hidden ? "" : gaze.src, base: make((context) => context.drawImage(frame, 0, 0)), rendered: make((context) => { context.drawImage(frame, 0, 0); if (!gaze.hidden) context.drawImage(gaze, 0, 0); }), meta: gaze.hidden ? null : (touchGazeRenderMetaBySrc.get(gaze.src) || null), family: window.__familyMicroChoreographyState(), recording: window.__recordingContractState() };
  });
}
async function screenshot(page, filename) {
  await page.locator("#overall-viewport").screenshot({ path: path.join(screenshotDir, filename) });
  return path.join(screenshotDir, filename);
}
async function makeStrip(browser, entries, filename, columns) {
  const strip = await browser.newPage({ viewport: { width: Math.max(400, columns * 430), height: Math.ceil(entries.length / columns) * 450 } });
  const body = entries.map((entry) => `<figure><img src="data:image/png;base64,${fs.readFileSync(entry.path).toString("base64")}"><figcaption>${entry.label}</figcaption></figure>`).join("");
  await strip.setContent(`<style>body{margin:0;background:#e9e9e5;font:16px Arial;color:#161616}main{display:grid;grid-template-columns:repeat(${columns},400px);gap:20px;padding:14px}figure{margin:0}img{width:400px;height:400px;image-rendering:pixelated;background:#fff}figcaption{height:32px;padding-top:6px;text-align:center}</style><main>${body}</main>`);
  const target = path.join(screenshotDir, filename); await strip.screenshot({ path: target, fullPage: true }); await strip.close(); return target;
}

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) { response.writeHead(403).end(); return; }
  fs.readFile(target, (error, value) => { if (error) { response.writeHead(404).end(); return; } response.writeHead(200, { "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : target.endsWith(".png") ? "image/png" : "application/octet-stream", "cache-control": "no-store" }).end(value); });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });
const port = server.address().port;
const url = `http://127.0.0.1:${port}${PAGE_URL}?rev=comp-req-566#expression`;
const httpErrors = [];
page.on("response", (response) => { if (response.status() >= 400) httpErrors.push({ status: response.status(), url: response.url() }); });
const report = { schema: "companion.comp-req-566.pupil-choreography.machine-ready.v1", requirement: "COMP-REQ-566", base_commit: "f77f3f01e8004baa2b2ca28179ad52b3b110ac82", page_sha256: sha256(fs.readFileSync(pagePath)), screenshot_dir: path.relative(root, screenshotDir).replaceAll("\\", "/"), hardware_contact: 0, production_enable: 0, direct_gaze: {}, families: {}, recording: {}, negatives: {}, http_errors: httpErrors };
const directSamples = {};
try {
  await page.goto(url, { waitUntil: "load" });
  await page.evaluate(() => { document.body.classList.add("expression-open"); const stage = document.querySelector("#overall-viewport"); stage.style.width = "400px"; stage.style.height = "400px"; stage.style.flex = "0 0 400px"; for (const image of stage.querySelectorAll("img")) { image.style.width = "400px"; image.style.height = "400px"; } });
  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("test_freeze"); await window.__epaperFreezeIdleGlintStep(0); });
  const centerProbe = await page.evaluate(() => window.__compReq566PupilProbe("1,0,1,0"));
  const centerSample = await capture(page);
  const gazeRows = [];
  for (const [name, key] of GAZES) {
    await page.evaluate(() => window.__interruptEpaperIdleGlint("test_freeze"));
    const probe = await page.evaluate((value) => window.__compReq566PupilProbe(value), key);
    const sample = await capture(page);
    directSamples[name] = sample;
    const direction = { dx: name === "left" ? -1 : name === "right" ? 1 : 0, dy: name === "up" ? -1 : name === "down" ? 1 : 0 };
    const oracle = pupilPoseOracle(sample, centerSample.rendered, direction);
    assert.equal(probe.presented, true, `${name}: pupil pose not presented`);
    assert.equal(oracle.pass, true, `${name}: direct-gaze oracle failed: ${oracle.reason || "unknown"}`);
    const shot = await screenshot(page, `gaze-${name}.png`);
    gazeRows.push({ name, key, probe, oracle, frame_sha256: sha256(JSON.stringify(sample.rendered)), screenshot: path.relative(root, shot).replaceAll("\\", "/") });
  }
  const centerAgain = await page.evaluate(() => window.__compReq566PupilProbe("1,0,1,0"));
  const centerReturn = await capture(page);
  assert.deepEqual(centerReturn.rendered, centerSample.rendered, "center pupil pose did not return exactly");
  report.direct_gaze = { pass: true, center: centerProbe, rows: gazeRows, exact_center_return: true, owner_scale_strip: path.relative(root, await makeStrip(browser, gazeRows.map((row) => ({ path: path.join(root, row.screenshot), label: row.name })), "gaze-five-direction-strip.png", 5)).replaceAll("\\", "/") };

  const familyStripEntries = [];
  for (const family of FAMILIES) {
    await page.evaluate(async (value) => { await window.__setFamilyMicroChoreographyFamily(value); window.__interruptEpaperIdleGlint("test_freeze"); }, family);
    const rows = [];
    for (const step of CYCLE_STEPS) {
      await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step);
      const sample = await capture(page);
      const state = sample.family;
      const trace = state.trace.at(-1) || {};
      const shot = await screenshot(page, `family-${family}-step-${step}.png`);
      rows.push({ step, frame_src: sample.frame_src, gaze_src: sample.gaze_src, face_hash: sha256(JSON.stringify(sample.rendered)), base_hash: sha256(JSON.stringify(sample.base)), meta: sample.meta, trace, components: trace.components || [], screenshot: path.relative(root, shot).replaceAll("\\", "/") });
    }
    const temporal = temporalOracle(rows);
    assert.equal(temporal.pass, true, `${family}: choreography oracle failed`);
    assert.equal(rows[0].face_hash, rows.at(-1).face_hash, `${family}: baseline did not return`);
    assert(rows.filter((row) => ACTIVE_STEPS.includes(row.step)).every((row) => row.components.some((component) => component !== "pupil")), `${family}: no non-pupil component participated`);
    const strip = await makeStrip(browser, rows.filter((row) => [0, 2, 4, 6, 8, 9].includes(row.step)).map((row) => ({ path: path.join(root, row.screenshot), label: `${family} · ${row.step}` })), `family-${family}-time-strip.png`, 6);
    familyStripEntries.push({ path: strip, label: family });
    report.families[family] = { pass: true, cadence_ms: rows[0].family?.manifest?.cadence_ms || 480, temporal, rows };
  }
  report.families.owner_scale_all_family_strip = path.relative(root, await makeStrip(browser, familyStripEntries, "families-ten-strip-atlas.png", 2)).replaceAll("\\", "/");

  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("test_freeze"); await window.__epaperFreezeIdleGlintStep(0); });
  const off = [];
  for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const row = await capture(page); off.push({ step, face_hash: sha256(JSON.stringify(row.rendered)), frame_src: row.frame_src, gaze_src: row.gaze_src }); }
  const box = await page.locator("#overall-viewport").boundingBox();
  await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(80); await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(40);
  assert.equal((await page.evaluate(() => window.__recordingContractState())).active, true, "recording did not enter");
  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("test_freeze"); });
  const on = [];
  for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const row = await capture(page); on.push({ step, face_hash: sha256(JSON.stringify(row.rendered)), frame_src: row.frame_src, gaze_src: row.gaze_src }); }
  const recordingState = await page.evaluate(() => window.__recordingContractState());
  assert.deepEqual(on.map((row) => row.face_hash), off.map((row) => row.face_hash), "recording changed or froze the underlying face sequence");
  assert.equal(recordingState.indicatorNodes, 0); assert.equal(recordingState.micGlyphPresent, false);
  report.recording = { pass: true, underlying_face_sequence_equal: true, off, on, state: recordingState };
  report.negatives = {
    missing_pupil: mutationNegative(directSamples.right, centerSample.rendered, { dx: 1, dy: 0 }, "missing_pupil"),
    extra_pupil: mutationNegative(directSamples.right, centerSample.rendered, { dx: 1, dy: 0 }, "extra_pupil"),
    inverted_direction: pupilPoseOracle(directSamples.right, centerSample.rendered, { dx: -1, dy: 0 }).pass === false,
    moved_outer_eye: mutationNegative(directSamples.right, centerSample.rendered, { dx: 1, dy: 0 }, "moved_outer_eye"),
    one_eye_only: mutationNegative(directSamples.right, centerSample.rendered, { dx: 1, dy: 0 }, "one_eye_only"),
    frozen_family: temporalOracle([{ face_hash: "same", step: 0, components: ["pupil", "brow"], trace: {} }, { face_hash: "same", step: 2, components: ["pupil", "brow"], trace: {} }, { face_hash: "same", step: 4, components: ["pupil", "brow"], trace: {} }, { face_hash: "same", step: 6, components: ["pupil", "brow"], trace: {} }, { face_hash: "same", step: 8, components: ["pupil", "brow"], trace: {} }, { face_hash: "same", step: 9, components: ["pupil", "brow"], trace: {} }]).pass === false,
    no_non_pupil_participation: temporalOracle([{ face_hash: "a", step: 0, components: ["pupil"], trace: {} }, { face_hash: "b", step: 2, components: ["pupil"], trace: { changed: true, refresh_requested: true } }, { face_hash: "c", step: 4, components: ["pupil"], trace: { changed: true, refresh_requested: true } }, { face_hash: "d", step: 6, components: ["pupil"], trace: { changed: true, refresh_requested: true } }, { face_hash: "e", step: 8, components: ["pupil"], trace: { changed: true, refresh_requested: true } }, { face_hash: "a", step: 9, components: ["pupil"], trace: {} }]).pass === false,
  };
  assert(Object.values(report.negatives).every(Boolean), "a negative fixture was not rejected");
  report.http_errors = httpErrors;
  assert.equal(httpErrors.length, 0, `HTTP errors: ${JSON.stringify(httpErrors)}`);
  report.pass = true;
} finally {
  await browser.close(); server.close();
}
const body = JSON.stringify(report, null, 2) + "\n";
report.report_sha256 = sha256(body);
fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ pass: report.pass === true, page_sha256: report.page_sha256, report_sha256: report.report_sha256, output: path.relative(root, output).replaceAll("\\", "/"), screenshot_dir: report.screenshot_dir, families: Object.keys(report.families).length - 1, direct_gaze: report.direct_gaze.pass, recording: report.recording.pass, negatives: report.negatives }, null, 2));
