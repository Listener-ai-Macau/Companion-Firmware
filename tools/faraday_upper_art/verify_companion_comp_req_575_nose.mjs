#!/usr/bin/env node
/* Faraday-only nose geometry, exclusion and calm timing oracle for COMP-REQ-575. */

import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRepoPath = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));
const oldDir = ".cache/validation/comp-req-573-fast-slice";
const oldSteps = new Map([[0, 0], [1, 0], [2, 2], [3, 2], [4, 2], [5, 5], [6, 5], [7, 5], [8, 8], [9, 8], [10, 8], [11, 11], [12, 11], [13, 11], [14, 14], [15, 14], [16, 14], [17, 17], [18, 17], [19, 19]]);

function sha256(value) { return crypto.createHash("sha256").update(value).digest("hex").toUpperCase(); }
function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith("--") || argv[i + 1] === undefined) throw new Error(`invalid argument near ${argv[i] || "<end>"}`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  if (!args.output || !args["expected-page-sha256"]) throw new Error("missing --output or --expected-page-sha256");
  return args;
}
function loadPlaywright() {
  for (const candidate of [process.env.COMPANION_PLAYWRIGHT_MODULE, "playwright", "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright", "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright"].filter(Boolean)) {
    try { return require(candidate); } catch { /* bounded local candidates */ }
  }
  throw new Error("Playwright unavailable");
}
function createServer() {
  return http.createServer((request, response) => {
    const target = path.resolve(repoRoot, `.${decodeURIComponent(request.url.split("?")[0])}`);
    if (!target.startsWith(`${repoRoot}${path.sep}`)) return response.writeHead(403).end();
    fs.readFile(target, (error, bytes) => {
      if (error) return response.writeHead(404).end();
      const type = target.endsWith(".html") ? "text/html; charset=utf-8" : target.endsWith(".png") ? "image/png" : "application/octet-stream";
      response.writeHead(200, { "content-type": type }); response.end(bytes);
    });
  });
}
function dataUrlBytes(dataUrl) { return Buffer.from(dataUrl.slice(dataUrl.indexOf(",") + 1), "base64"); }
function addErrors(page) {
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  page.on("requestfailed", request => errors.push(`request:${request.url()}:${request.failure()?.errorText || "failed"}`));
  page.on("response", response => { if (response.status() >= 400) errors.push(`http:${response.status()}:${response.url()}`); });
  return errors;
}
async function openPage(browser, url) {
  const context = await browser.newContext({ colorScheme: "light", deviceScaleFactor: 1, locale: "zh-CN", reducedMotion: "reduce", timezoneId: "UTC", viewport: { width: 1280, height: 900 } });
  const page = await context.newPage(); const errors = addErrors(page);
  await page.goto(url, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => typeof window.__compReq575NoseContract === "function" && typeof window.__compReq569FreezeStep === "function", null, { timeout: 10000 });
  return { context, page, errors };
}
async function inspectStep(page, oldUrl, box, scale) {
  return page.evaluate(async ({ oldUrl, box, scale }) => {
    const load = src => new Promise((resolve, reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = src; });
    const stage = document.querySelector("#overall-viewport"), frame = stage.querySelector(".viewport-frame"), gaze = stage.querySelector(".viewport-gaze");
    const current = document.createElement("canvas"); current.width = current.height = 200; const currentContext = current.getContext("2d");
    if (!frame.hidden) currentContext.drawImage(frame, 0, 0);
    if (!gaze.hidden) { const transform = getComputedStyle(gaze).transform; const matrix = !transform || transform === "none" ? { e: 0, f: 0 } : new DOMMatrixReadOnly(transform); currentContext.drawImage(gaze, Math.round(matrix.e), Math.round(matrix.f)); }
    const old = await load(oldUrl), oldCanvas = document.createElement("canvas"); oldCanvas.width = oldCanvas.height = 200; oldCanvas.getContext("2d").drawImage(old, 0, 0);
    const currentPixels = currentContext.getImageData(0, 0, 200, 200).data, oldPixels = oldCanvas.getContext("2d").getImageData(0, 0, 200, 200).data, historicalSameContext = new Uint8ClampedArray(currentPixels);
    const contract = window.__compReq575NoseContract(), [bx, by, bw, bh] = contract.mask.exclusion;
    const expected = (x, y) => { const dx = x - contract.mask.x, dy = y - contract.mask.y; return dx >= 0 && dx < contract.mask.width && dy >= 0 && dy < contract.mask.height && contract.mask.rows[dy][dx] === "1"; };
    for (let y = by; y < by + bh; y++) for (let x = bx; x < bx + bw; x++) { const index = (y * 200 + x) * 4; for (let channel = 0; channel < 4; channel++) historicalSameContext[index + channel] = oldPixels[index + channel]; }
    let noseMismatch = 0, outsideDiff = 0, insideDiff = 0, oldBlack = 0, actualMaskBlack = 0, diffMinX = 200, diffMinY = 200, diffMaxX = -1, diffMaxY = -1;
    for (let y = by; y < by + bh; y++) for (let x = bx; x < bx + bw; x++) { const actual = currentPixels[(y * 200 + x) * 4] < 128; if (actual) actualMaskBlack++; if (actual !== expected(x, y)) noseMismatch++; }
    for (let pixel = 0; pixel < 40000; pixel++) { const x = pixel % 200, y = Math.floor(pixel / 200), currentBit = currentPixels[pixel * 4] < 128, oldBit = historicalSameContext[pixel * 4] < 128; if (oldPixels[pixel * 4] < 128 && x >= bx && x < bx + bw && y >= by && y < by + bh) oldBlack++; if (currentBit !== oldBit) { if (x >= bx && x < bx + bw && y >= by && y < by + bh) insideDiff++; else { outsideDiff++; diffMinX=Math.min(diffMinX,x); diffMinY=Math.min(diffMinY,y); diffMaxX=Math.max(diffMaxX,x); diffMaxY=Math.max(diffMaxY,y); } } }
    const connected = (() => { const points = []; for (let y = 0; y < contract.mask.height; y++) for (let x = 0; x < contract.mask.width; x++) if (contract.mask.rows[y][x] === "1") points.push([x, y]); const seen = new Set(), components = []; for (const point of points) { const key = point.join(","); if (seen.has(key)) continue; const queue = [point], component = []; seen.add(key); while (queue.length) { const [x, y] = queue.shift(); component.push([x, y]); for (const next of [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]]) { const nkey = next.join(","); if (next[0] >= 0 && next[0] < contract.mask.width && next[1] >= 0 && next[1] < contract.mask.height && contract.mask.rows[next[1]][next[0]] === "1" && !seen.has(nkey)) { seen.add(nkey); queue.push(next); } } } components.push(component); } return { count: components.length, area: points.length, top_body_width: contract.mask.rows[1].replaceAll("0", "").length, lower_point_rows: contract.mask.rows.slice(6).join("").replaceAll("0", "").length }; })();
    const crop = document.createElement("canvas"); crop.width = box[2] * scale; crop.height = box[3] * scale; const cropContext = crop.getContext("2d"); cropContext.imageSmoothingEnabled = false; cropContext.drawImage(current, box[0], box[1], box[2], box[3], 0, 0, crop.width, crop.height);
    return { crop: crop.toDataURL("image/png"), full: current.toDataURL("image/png"), nose_mismatch: noseMismatch, actual_mask_black: actualMaskBlack, old_black_in_exclusion: oldBlack, inside_nose_diff: insideDiff, outside_nose_diff: outsideDiff, outside_diff_bounds: outsideDiff ? { min_x: diffMinX, min_y: diffMinY, max_x: diffMaxX, max_y: diffMaxY } : null, connected, write_audit: contract.write_audit, registered_once: contract.registered_once };
  }, { oldUrl, box, scale });
}
async function buildPairAndStrip(page, oldUrl, currentCrops, box, scale, outputDir) {
  const result = await page.evaluate(async ({ oldUrl, currentCrops, box, scale }) => {
    const load = src => new Promise((resolve, reject) => { const image = new Image(); image.onload = () => resolve(image); image.onerror = reject; image.src = src; });
    const old = await load(oldUrl), pair = document.createElement("canvas"); pair.width = box[2] * scale * 2 + 2; pair.height = box[3] * scale; const pairContext = pair.getContext("2d"); pairContext.imageSmoothingEnabled = false; pairContext.drawImage(old, box[0], box[1], box[2], box[3], 0, 0, box[2] * scale, box[3] * scale); const current = await load(currentCrops[0]); pairContext.drawImage(current, box[2] * scale + 2, 0);
    const columns = 5, rows = Math.ceil(currentCrops.length / columns), strip = document.createElement("canvas"); strip.width = columns * box[2] * scale; strip.height = rows * box[3] * scale; const stripContext = strip.getContext("2d"); stripContext.imageSmoothingEnabled = false; stripContext.fillStyle = "#fff"; stripContext.fillRect(0, 0, strip.width, strip.height); for (let i = 0; i < currentCrops.length; i++) { const image = await load(currentCrops[i]); stripContext.drawImage(image, (i % columns) * box[2] * scale, Math.floor(i / columns) * box[3] * scale); }
    return { pair: pair.toDataURL("image/png"), strip: strip.toDataURL("image/png") };
  }, { oldUrl, currentCrops, box, scale });
  fs.writeFileSync(path.join(outputDir, "nose-old-new-zoom.png"), dataUrlBytes(result.pair));
  fs.writeFileSync(path.join(outputDir, "nose-beat-crop-strip.png"), dataUrlBytes(result.strip));
}
async function liveTiming(page) {
  const selected = await page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
  if (!selected?.presented) throw new Error("calm selection failed");
  const reset = await page.evaluate(() => window.__resetEpaperIdleGlintRealClock()); const baseline = await page.evaluate(() => window.__compReq569Snapshot()); const start = performance.now();
  await page.waitForFunction(() => window.__familyMicroChoreographyState().trace.length >= 20, null, { timeout: 13000 });
  const elapsed = Math.round(performance.now() - start), final = await page.evaluate(() => window.__compReq569Snapshot());
  const state = await page.evaluate(() => window.__familyMicroChoreographyState()); await page.evaluate(() => window.__interruptEpaperIdleGlint("nose_evidence_complete"));
  return { wall_clock_ms: elapsed, trace_count: state.trace.length, reset, baseline_return: final.canvas.signature === baseline.canvas.signature && final.choreography.current_key === baseline.choreography.current_key, ownership: final.ownership };
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output); if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) throw new Error("output must remain inside repository");
const outputDir = path.dirname(outputPath); fs.mkdirSync(outputDir, { recursive: true });
const observedPageSha = sha256(fs.readFileSync(pagePath)); const expectedPageSha = args["expected-page-sha256"].toUpperCase();
const server = createServer(); const playwright = loadPlaywright(); let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve)); const port = server.address().port; const baseUrl = `http://127.0.0.1:${port}`; const url = `${baseUrl}/${pageRepoPath}?comp_req_575=${Date.now()}#expression`; browser = await playwright.chromium.launch({ headless: true });
  const { context, page, errors } = await openPage(browser, url); const box = [93, 119, 15, 15], scale = 10; const contract = await page.evaluate(() => window.__compReq575NoseContract());
  const crops = [], rows = [];
  try {
    for (let step = 0; step < 20; step++) { await page.evaluate(value => window.__compReq569FreezeStep(value), step); const row = await inspectStep(page, `${baseUrl}/${oldDir}/calm-step-${String(oldSteps.get(step)).padStart(2, "0")}.png`, box, scale); if(step===0)fs.writeFileSync(path.join(outputDir,"nose-new-step-00.png"),dataUrlBytes(row.full)); crops.push(row.crop); rows.push({ step, ...row, crop: undefined, full: undefined }); }
    await buildPairAndStrip(page, `${baseUrl}/${oldDir}/calm-step-00.png`, crops, box, scale, outputDir);
    const live = await liveTiming(page);
    const outside = rows.map(row => row.outside_nose_diff); const checks = {
      page_hash_bound: observedPageSha === expectedPageSha,
      registered_once: contract.registered_once === true,
      one_connected_component: rows.every(row => row.connected.count === 1 && row.connected.top_body_width >= 3 && row.connected.lower_point_rows >= 3),
      exact_new_mask_every_step: rows.every(row => row.nose_mismatch === 0),
      mouth_cheek_protected: rows.every(row => row.write_audit.written_protected_pixels === 0),
      outside_nose_diff_zero: Math.max(...outside) === 0,
      current_nose_pixel_count_stable: new Set(rows.map(row => row.actual_mask_black)).size === 1,
      live_9_6s: live.wall_clock_ms >= 9000 && live.wall_clock_ms <= 11500 && live.trace_count >= 20,
      scheduler_writer_clean: live.ownership.active_scheduler_count === 1 && live.ownership.writer_owner_count === 1 && live.ownership.pending_writers === 0 && live.ownership.stale_family_commits === 0,
      errors_zero: errors.length === 0,
    };
    const report = { schema: "companion.comp_req_575.nose_refinement.v1", status: Object.values(checks).every(Boolean) ? "PASS" : "NO_GO", page: { path: pageRepoPath, sha256: observedPageSha }, contract, rows, outside_nose_diff: { max: Math.max(...outside), total: outside.reduce((sum, value) => sum + value, 0) }, live, errors, checks, artifacts: { old_new_zoom: ".cache/validation/comp-req-575-nose/nose-old-new-zoom.png", beat_crop_strip: ".cache/validation/comp-req-575-nose/nose-beat-crop-strip.png" }, validation_tool: "tools/faraday_upper_art/verify_companion_comp_req_575_nose.mjs" };
    fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8"); console.log(JSON.stringify({ status: report.status, page_sha256: observedPageSha, checks, outside_nose_diff: report.outside_nose_diff, live_wall_clock_ms: live.wall_clock_ms, nose_mask_sha256: sha256(Buffer.from(JSON.stringify(contract.mask))) }, null, 2)); if (report.status !== "PASS") process.exitCode = 2;
  } finally { await context.close(); }
} finally { if (browser) await browser.close(); await new Promise(resolve => server.close(resolve)); }
