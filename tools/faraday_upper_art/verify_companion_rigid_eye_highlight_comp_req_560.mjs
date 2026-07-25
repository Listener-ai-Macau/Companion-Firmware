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
const pagePath = path.join(
  root,
  "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
);
const outputIndex = process.argv.indexOf("--output");
assert(outputIndex >= 0 && process.argv[outputIndex + 1], "missing --output");
const output = path.resolve(root, process.argv[outputIndex + 1]);
assert(output.startsWith(`${root}${path.sep}`), "output must remain in repository");
const screenshotDir = path.join(path.dirname(output), "screenshots");

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function loadPlaywright() {
  for (const candidate of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
  ].filter(Boolean)) {
    try {
      return require(candidate);
    } catch {
      // Continue through bounded local candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) {
    response.writeHead(403).end();
    return;
  }
  fs.readFile(target, (error, value) => {
    if (error) {
      response.writeHead(404).end();
      return;
    }
    response.writeHead(200, {
      "content-type": target.endsWith(".html")
        ? "text/html; charset=utf-8"
        : target.endsWith(".png") ? "image/png" : "application/octet-stream",
    });
    response.end(value);
  });
});

const directions = [
  ["center", "1,0,1,0"],
  ["left", "-2,0,-6,0"],
  ["up", "1,-3,1,-6"],
  ["right", "5,0,5,0"],
  ["down", "1,4,1,6"],
];
const families = [
  "calm", "curious", "warm", "playful", "sleepy",
  "delighted", "bashful", "thoughtful", "focused", "alert",
];
const familySteps = [0, 2, 4, 6, 8, 9];

try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  const port = server.address().port;
  await page.goto(
    `http://127.0.0.1:${port}/${path.relative(root, pagePath).replaceAll("\\", "/")}#expression`,
    { waitUntil: "networkidle" },
  );
  await page.waitForFunction(() => window.__eyeIntegrityPixelProbe);
  await page.evaluate(() => window.__interruptEpaperIdleGlint("comp_req_560_freeze"));

  const contract = await page.evaluate(() => window.__eyeIntegrityContractState().contract);
  assert.equal(contract.moving_component, "rigid_primary_plus_sparkle_clusters");
  assert.equal(contract.primary_highlight, "rigid_with_sparkle");
  assert.equal(contract.expected_open_eye_clusters, 2);
  assert.equal(contract.components_per_cluster, 2);
  assert.equal(contract.boundary_inset_px, 1);

  let familyChecks = 0;
  for (const family of families) {
    const selected = await page.evaluate(
      (value) => window.__setFamilyMicroChoreographyFamily(value),
      family,
    );
    assert(selected.presented, `${family} baseline presentation failed`);
    for (const step of familySteps) {
      if (step !== 0) {
        assert(
          await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step),
          `${family} step ${step} presentation failed`,
        );
      }
      const probe = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
      assert(probe.pass, `${family} step ${step} rigid highlight probe failed`);
      assert([0, 4].includes(probe.component_count));
      assert.equal(probe.paired_clusters, true);
      if (probe.component_count === 0) assert.equal(probe.closed_eye_cluster_absent, true);
      familyChecks++;
    }
  }
  await page.evaluate(async () => {
    await window.__setFamilyMicroChoreographyFamily("calm");
    window.__interruptEpaperIdleGlint("comp_req_560_direction_freeze");
  });

  fs.mkdirSync(screenshotDir, { recursive: true });
  const records = [];
  const screenshotBuffers = [];
  for (const [name, key] of directions) {
    assert(
      await page.evaluate((value) => window.__eyeIntegritySetGazeKey(value), key),
      `${name} gaze presentation failed`,
    );
    const probe = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
    assert(probe.pass, `${name} rigid highlight probe failed: ${JSON.stringify(probe)}`);
    assert.equal(probe.cluster_count, 2);
    assert.equal(probe.component_count, 4);
    assert.equal(probe.rigid_cluster_mismatch, 0);
    assert.equal(probe.relative_vector_mismatch, 0);
    assert.equal(probe.component_mismatch, 0);
    assert.equal(probe.boundary_mismatch_pixels, 0);
    assert.equal(probe.residual_source_pixels, 0);
    assert.equal(probe.silhouette_mismatch_pixels, 0);
    assert.equal(probe.paired_clusters, true);
    if (name === "center") assert.equal(probe.exact_baseline, true);
    const file = path.join(screenshotDir, `${name}.png`);
    const screenshot = await page.locator("#overall-viewport").screenshot({ path: file });
    screenshotBuffers.push([name, screenshot]);
    records.push({ name, key, ...probe, screenshot: path.relative(root, file) });
  }

  const clamp = await page.evaluate(() => window.__eyeIntegrityClampProbe(80, 80));
  assert.equal(clamp.pass, true);
  assert.equal(clamp.clamped, true);
  assert.equal(clamp.fits, true);
  assert.notDeepEqual(clamp.applied, clamp.requested);

  await page.evaluate(async () => {
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    gaze.src = cached(touchData.overlays["1,4,1,6"]);
    gaze.hidden = false;
    await touchGazeImage(gaze.src);
  });
  const contradictoryNegative = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
  assert.equal(contradictoryNegative.pass, false);

  await page.evaluate(() => window.__epaperFreezeRegisteredBlinkStep(1));
  const closedEye = await page.evaluate(() => ({
    gaze_hidden: document.querySelector("#overall-viewport .viewport-gaze").hidden,
    composition: document.querySelector("#overall-viewport .viewport-frame").dataset.eyeSilhouette,
  }));
  assert.equal(closedEye.gaze_hidden, true);
  assert.equal(closedEye.composition, "whole-registered-frame");

  const sheet = await browser.newPage({ viewport: { width: 1100, height: 310 } });
  await sheet.setContent(
    `<style>body{margin:0;background:#202426;color:white;font:16px sans-serif;display:flex;gap:12px;padding:16px}.cell{width:200px;text-align:center}.cell img{display:block;width:200px;height:200px;object-fit:cover;background:white;margin-bottom:8px}</style>` +
    screenshotBuffers.map(([name, bytes]) =>
      `<div class="cell"><img src="data:image/png;base64,${bytes.toString("base64")}">${name}</div>`,
    ).join(""),
  );
  await sheet.screenshot({ path: path.join(screenshotDir, "contact-sheet.png") });
  await sheet.close();
  assert.deepEqual(errors, []);

  const pageBytes = Buffer.from(
    fs.readFileSync(pagePath, "utf8").replaceAll("\r\n", "\n"),
    "utf8",
  );
  const report = {
    schema: "companion.comp_req_560.rigid_eye_highlight.v1",
    status: "PASS",
    page_sha256: sha256(pageBytes),
    directions: records,
    families: families.length,
    family_steps: familySteps.length,
    family_checks: familyChecks,
    unsafe_displacement_clamp: clamp,
    contradictory_source_negative_rejected: true,
    closed_eye_cluster_absent: true,
    contact_sheet: path.relative(root, path.join(screenshotDir, "contact-sheet.png")),
    page_errors: errors,
    contract,
  };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({ status: report.status, page_sha256: report.page_sha256 }));
  await browser.close();
} finally {
  server.close();
}
