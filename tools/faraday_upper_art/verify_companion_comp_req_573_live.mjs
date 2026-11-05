#!/usr/bin/env node
/* Faraday-only live and cold-load closure for the COMP-REQ-573 calm slice. */

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const pageRepoPath = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));
const oldEvidencePath = path.join(repoRoot, ".cache/validation/comp-req-573-fast-slice/perceptible-result.json");

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    if (!argv[i]?.startsWith("--") || argv[i + 1] === undefined) throw new Error(`invalid argument near ${argv[i] || "<end>"}`);
    args[argv[i].slice(2)] = argv[i + 1];
  }
  if (!args.output || !args["expected-page-sha256"]) throw new Error("missing --output or --expected-page-sha256");
  return args;
}

function sha256(value) { return crypto.createHash("sha256").update(value).digest("hex").toUpperCase(); }
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
      response.writeHead(200, { "content-type": type });
      response.end(bytes);
    });
  });
}
function packedStage(page) {
  return page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const canvas = document.createElement("canvas"); canvas.width = 200; canvas.height = 200;
    const ctx = canvas.getContext("2d");
    if (!frame.hidden) ctx.drawImage(frame, 0, 0);
    if (!gaze.hidden) {
      const transform = getComputedStyle(gaze).transform;
      const matrix = !transform || transform === "none" ? { e: 0, f: 0 } : new DOMMatrixReadOnly(transform);
      ctx.drawImage(gaze, Math.round(matrix.e), Math.round(matrix.f));
    }
    const rgba = ctx.getImageData(0, 0, 200, 200).data;
    const packed = new Uint8Array(5000);
    for (let pixel = 0; pixel < 40000; pixel += 1) if (rgba[pixel * 4] < 128) packed[Math.floor(pixel / 8)] |= 0x80 >> (pixel % 8);
    let binary = ""; for (const byte of packed) binary += String.fromCharCode(byte);
    return btoa(binary);
  });
}
function changedPixels(beforeBase64, afterBase64) {
  const before = Buffer.from(beforeBase64, "base64"); const after = Buffer.from(afterBase64, "base64");
  assert.equal(before.length, 5000); assert.equal(after.length, 5000);
  let changed = 0;
  for (let i = 0; i < before.length; i += 1) {
    let bits = before[i] ^ after[i];
    while (bits) { changed += bits & 1; bits >>>= 1; }
  }
  return changed;
}
function addBrowserListeners(page) {
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  page.on("requestfailed", request => errors.push(`request:${request.url()}:${request.failure()?.errorText || "failed"}`));
  page.on("response", response => { if (response.status() >= 400) errors.push(`http:${response.status()}:${response.url()}`); });
  return errors;
}
async function openPage(browser, url) {
  const context = await browser.newContext({ colorScheme: "light", deviceScaleFactor: 1, locale: "zh-CN", reducedMotion: "reduce", timezoneId: "UTC", viewport: { width: 1280, height: 900 } });
  const page = await context.newPage();
  const errors = addBrowserListeners(page);
  await page.goto(url, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => typeof window.__compReq569Snapshot === "function" && typeof window.__compReq569FreezeStep === "function", null, { timeout: 10000 });
  return { context, page, errors };
}
async function coldLoad(browser, url) {
  const { context, page, errors } = await openPage(browser, `${url}?comp_req_573=cold-${Date.now()}#expression`);
  const started = performance.now();
  const samples = [];
  let firstNonEmptyMs = null;
  try {
    while (performance.now() - started < 12000) {
      const snapshot = await page.evaluate(() => window.__compReq569Snapshot());
      const elapsed = Math.round(performance.now() - started);
      const nonempty = Boolean(snapshot.frame && snapshot.gaze && !snapshot.gaze_hidden);
      if (nonempty && firstNonEmptyMs === null) firstNonEmptyMs = elapsed;
      samples.push({ elapsed_ms: elapsed, nonempty, signature: snapshot.canvas?.signature || null, ownership: snapshot.ownership });
      await page.waitForTimeout(240);
    }
    const finalSnapshot = await page.evaluate(() => window.__compReq569Snapshot());
    const signatures = [...new Set(samples.map(sample => sample.signature).filter(Boolean))];
    const ownership = finalSnapshot.ownership;
    const checks = {
      frame_gaze_within_1s: firstNonEmptyMs !== null && firstNonEmptyMs <= 1000,
      nonempty_for_12s: samples.length > 0 && samples.every(sample => sample.nonempty),
      distinct_committed_signatures_at_least_4: signatures.length >= 4,
      console_page_errors_zero: errors.length === 0,
      scheduler_1: ownership.active_scheduler_count === 1,
      writer_owner_1: ownership.writer_owner_count === 1 && ownership.writer_owner_token > 0 && ownership.writer_epoch === ownership.epoch,
      pending_0: ownership.pending_writers === 0,
      stale_0: ownership.stale_family_commits === 0,
    };
    return { duration_ms: Math.round(performance.now() - started), first_nonempty_ms: firstNonEmptyMs, sample_count: samples.length, distinct_signatures: signatures, final: finalSnapshot, errors, checks, status: Object.values(checks).every(Boolean) ? "PASS" : "NO_GO" };
  } finally { await context.close(); }
}
async function liveLoop(browser, url) {
  const { context, page, errors } = await openPage(browser, `${url}?comp_req_573=live-${Date.now()}#expression`);
  try {
    const selected = await page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
    if (!selected?.presented) throw new Error("calm selection did not present");
    const reset = await page.evaluate(() => window.__resetEpaperIdleGlintRealClock());
    const baseline = await page.evaluate(() => window.__compReq569Snapshot());
    const started = performance.now();
    await page.waitForFunction(() => window.__familyMicroChoreographyState().trace.length >= 20, null, { timeout: 13000 });
    const elapsed = Math.round(performance.now() - started);
    const state = await page.evaluate(() => window.__familyMicroChoreographyState());
    const final = await page.evaluate(() => window.__compReq569Snapshot());
    await page.evaluate(() => window.__interruptEpaperIdleGlint("live_evidence_complete"));
    const trace = state.trace.slice(0, 20);
    const checks = {
      reset_started: reset.started === true && reset.cadence_ms === 480,
      real_wall_clock_9_6s: elapsed >= 9000 && elapsed <= 11500,
      twenty_committed_steps: trace.length >= 20 && trace.every(row => row.committed_1bpp !== false),
      changed_beats_present: trace.filter(row => row.changed).length >= 6,
      exact_baseline_return: final.canvas.signature === baseline.canvas.signature && final.choreography.current_key === baseline.choreography.current_key,
      console_page_errors_zero: errors.length === 0,
      ownership_scheduler_1: final.ownership.active_scheduler_count === 1,
      ownership_writer_1: final.ownership.writer_owner_count === 1 && final.ownership.writer_owner_token > 0,
      pending_0: final.ownership.pending_writers === 0,
      stale_0: final.ownership.stale_family_commits === 0,
    };
    return { wall_clock_ms: elapsed, reset, baseline, trace, final, errors, checks, status: Object.values(checks).every(Boolean) ? "PASS" : "NO_GO" };
  } finally { await context.close(); }
}
async function visualRegression(browser, url, oldEvidence) {
  const { context, page, errors } = await openPage(browser, `${url}?comp_req_573=visual-regression-${Date.now()}#expression`);
  try {
    const selected = await page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
    if (!selected?.presented) throw new Error("calm selection did not present");
    const rows = [];
    const base = await packedStage(page);
    for (const step of [0, 2, 5, 8, 11, 14, 17, 19]) {
      await page.evaluate(value => window.__compReq569FreezeStep(value), step);
      rows.push({ step, changed_pixels: changedPixels(base, await packedStage(page)) });
    }
    const expected = new Map((oldEvidence.steps || []).map(row => [row.step, row.total_changed]));
    const checks = { console_page_errors_zero: errors.length === 0, exact_changed_pixel_counts: rows.every(row => expected.get(row.step) === row.changed_pixels) };
    return { rows, expected: Object.fromEntries(expected), errors, checks, status: Object.values(checks).every(Boolean) ? "PASS" : "NO_GO" };
  } finally { await context.close(); }
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) throw new Error("output must remain inside repository");
const expectedPageSha = args["expected-page-sha256"].toUpperCase();
const observedPageSha = sha256(fs.readFileSync(pagePath));
const oldEvidence = JSON.parse(fs.readFileSync(oldEvidencePath, "utf8"));
const server = createServer();
const playwright = loadPlaywright();
let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const port = server.address().port;
  const url = `http://127.0.0.1:${port}/${pageRepoPath}`;
  browser = await playwright.chromium.launch({ headless: true });
  const cold = await coldLoad(browser, url);
  const live = await liveLoop(browser, url);
  const visual = await visualRegression(browser, url, oldEvidence);
  const checks = { page_hash_bound: observedPageSha === expectedPageSha, cold: cold.status === "PASS", live: live.status === "PASS", visual: visual.status === "PASS" };
  const report = { schema: "companion.comp_req_573.live_closure.v1", status: Object.values(checks).every(Boolean) ? "PASS" : "NO_GO", page: { path: pageRepoPath, sha256: observedPageSha }, checks, cold, live, visual, validation_tool: "tools/faraday_upper_art/verify_companion_comp_req_573_live.mjs" };
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, "utf8");
  console.log(JSON.stringify(report, null, 2));
  if (report.status !== "PASS") process.exitCode = 2;
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
