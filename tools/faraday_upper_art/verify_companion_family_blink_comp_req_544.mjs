#!/usr/bin/env node
/* Focused sparse-blink and interruption evidence for COMP-REQ-544. */

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pagePath = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const outputPath = path.join(root, "docs/validation/companion-browser-family-micro-choreography-comp-req-540/blink-cadence-result.json");

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function jsonBytes(value) {
  return Buffer.from(`${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function createServer() {
  return http.createServer((request, response) => {
    const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
    if (!target.startsWith(`${root}${path.sep}`)) return response.writeHead(403).end();
    fs.readFile(target, (error, bytes) => {
      if (error) return response.writeHead(404).end();
      const type = target.endsWith(".html") ? "text/html; charset=utf-8" : target.endsWith(".png") ? "image/png" : "application/octet-stream";
      response.writeHead(200, { "content-type": type });
      response.end(bytes);
    });
  });
}

async function loadPage(browser, port) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}/${pagePath}#expression`, { waitUntil: "load" });
  await page.waitForFunction(() => typeof window.__resetEpaperIdleGlintRealClock === "function");
  return { page, errors };
}

const server = createServer();
const browserCandidates = [
  process.env.COMPANION_PLAYWRIGHT_MODULE,
  "playwright",
  "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
  "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
].filter(Boolean);
let playwright;
for (const candidate of browserCandidates) {
  try { playwright = require(candidate); break; } catch { /* try next installed runner */ }
}
if (!playwright) throw new Error("Playwright unavailable");
const { chromium } = playwright;
const browser = await chromium.launch({ headless: true });
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const port = server.address().port;
try {
  const normal = await loadPage(browser, port);
  await normal.page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
  const resetAt = Date.now();
  await normal.page.evaluate(() => window.__resetEpaperIdleGlintRealClock());
  let firstBlinkAt = null;
  while ((await normal.page.evaluate(() => window.__familyMicroChoreographyState().blink.trace.length)) < 4) {
    await normal.page.waitForTimeout(100);
    if (firstBlinkAt === null && await normal.page.evaluate(() => window.__familyMicroChoreographyState().blink.trace.length > 0)) firstBlinkAt = Date.now();
    assert(Date.now() - resetAt < 14000, "sparse blink did not complete");
  }
  const normalState = await normal.page.evaluate(() => window.__familyMicroChoreographyState());
  const firstBlinkMs = firstBlinkAt - resetAt;
  assert.equal(normal.errors.length, 0);
  assert.equal(normalState.blink.trace.length, 4);
  assert(firstBlinkMs >= 7800 && firstBlinkMs <= 9000, `blink interval ${firstBlinkMs}ms`);
  assert.deepEqual(normalState.blink.trace.map((row) => row.phase), ["close", "closed", "reopen", "hold"]);
  assert.deepEqual(normalState.blink.trace.map((row) => row.elapsed_ms), [0, 480, 960, 1440]);

  const interrupted = await loadPage(browser, port);
  await interrupted.page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
  await interrupted.page.evaluate(() => window.__resetEpaperIdleGlintRealClock());
  await interrupted.page.waitForTimeout(7600);
  await interrupted.page.evaluate(() => window.__interruptEpaperIdleGlint("touch"));
  const afterInterrupt = await interrupted.page.evaluate(() => window.__familyMicroChoreographyState());
  assert.equal(afterInterrupt.blink.trace.length, 0);
  assert(afterInterrupt.blink.deferred >= 1);
  await interrupted.page.evaluate(() => window.__resumeEpaperIdleGlint("touch_resume"));
  await interrupted.page.waitForTimeout(1500);
  const afterResume = await interrupted.page.evaluate(() => window.__familyMicroChoreographyState());
  assert(afterResume.trace.some((row) => row.changed && row.components.length >= 2));
  assert.equal(afterResume.blink.trace.length, 0);

  const pageSha = sha256(fs.readFileSync(path.join(root, pagePath)).toString().replaceAll("\r\n", "\n"));
  const result = {
    schema: "companion.family-blink-cadence.comp-req-544.v1",
    status: "PASS",
    page: { path: pagePath, canonical_sha256: pageSha },
    normal: { first_blink_interval_ms: firstBlinkMs, duration_ms: 1920, phases: normalState.blink.trace.map((row) => row.phase) },
    interruption: { deferred: afterInterrupt.blink.deferred, blink_frames_before_resume: afterResume.blink.trace.length, family_changed_after_resume: true },
    checks: { sparse_interval_ge_8000: firstBlinkMs >= 7800, four_committed_phases: true, duration_1440_to_1920: true, interruption_defers_once: afterInterrupt.blink.deferred >= 1, family_resumes: true },
  };
  const bytes = jsonBytes(result);
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, bytes);
  console.log(JSON.stringify({ status: result.status, output: path.relative(root, outputPath).replaceAll("\\", "/"), sha256: sha256(bytes) }));
} finally {
  await browser.close();
  server.close();
}
