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

const families = [
  "calm", "curious", "warm", "playful", "sleepy",
  "delighted", "bashful", "thoughtful", "focused", "alert",
];
const steps = [0, 2, 4, 6, 8, 9];
const records = [];

try {
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const port = server.address().port;
  await page.goto(
    `http://127.0.0.1:${port}/${path.relative(root, pagePath).replaceAll("\\", "/")}`,
    { waitUntil: "networkidle" },
  );
  await page.waitForFunction(() => window.__eyeIntegrityPixelProbe);

  const contract = await page.evaluate(() => window.__eyeIntegrityContractState().contract);
  assert.equal(contract.moving_component, "paired_small_sparkles");
  assert.equal(contract.primary_highlight, "fixed");
  assert.equal(contract.eye_body_silhouette, "fixed");
  assert.equal(contract.boundary_inset_px, 1);
  assert.equal(contract.max_sparkle_pixels, 36);
  assert.equal(contract.expected_open_eye_sparkles, 2);

  for (const family of families) {
    const selected = await page.evaluate(
      (value) => window.__setFamilyMicroChoreographyFamily(value),
      family,
    );
    assert(selected.presented, `${family} baseline failed`);
    for (const step of steps) {
      if (step !== 0) {
        assert(
          await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step),
          `${family} step ${step} failed`,
        );
      }
      const probe = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
      assert(probe.pass, `${family} step ${step} eye integrity failed`);
      assert.equal(probe.primary_highlight_mismatch_pixels, 0);
      assert.equal(probe.silhouette_mismatch_pixels, 0);
      assert(probe.changed_pixels <= probe.max_changed_pixels);
      records.push({ family, step, ...probe });
    }
  }

  await page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
  await page.evaluate(() => window.__interruptEpaperIdleGlint("test_freeze"));
  const gazeKeys = await page.evaluate(() => window.__eyeIntegrityGazeKeys());
  for (const key of gazeKeys) {
    const component = await page.evaluate(
      (value) => window.__pairedEyeGazeProbe(value),
      key,
    );
    assert(component.presented, `gaze ${key} presentation failed`);
    assert(component.pass, `gaze ${key} paired-eye integrity failed`);
    assert.equal(component.open_eye_count, 2);
    assert.equal(component.sparkle_components, 2);
    assert(component.eye_rows.every((eye) => eye.sparkle_components === 1));
  }
  for (const key of ["1,0,1,0", "-2,0,-6,0", "1,-3,1,-6", "5,0,5,0", "1,4,1,6"]) {
    assert(
      await page.evaluate((value) => window.__eyeIntegritySetGazeKey(value), key),
      `gaze ${key} presentation failed`,
    );
    const probe = await page.evaluate(
      (value) => window.__pairedEyeGazeProbe(value),
      key,
    );
    assert(probe.pass, `gaze ${key} eye integrity failed`);
    records.push({ family: "calm", step: `gaze:${key}`, ...probe });
  }

  await page.evaluate(async () => {
    const state = document.querySelector("#overall-viewport .viewport-frame");
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    gaze.src = cached(touchData.overlays["1,4,1,6"]);
    gaze.hidden = false;
    await touchGazeImage(gaze.src);
    state.dataset.eyeSilhouette = "unsafe-negative";
  });
  const negative = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
  assert.equal(negative.pass, false, "unsafe full-highlight mutation was accepted");

  await browser.close();
  const pageBytes = Buffer.from(
    fs.readFileSync(pagePath, "utf8").replaceAll("\r\n", "\n"),
    "utf8",
  );
  const report = {
    schema: "companion.comp_req_553.paired_eye_integrity.v1",
    status: "PASS",
    page_sha256: sha256(pageBytes),
    families: families.length,
    family_frames: families.length * steps.length,
    drag_gaze_keys: gazeKeys.length,
    paired_eye_gaze_keys: gazeKeys.length,
    primary_highlight_mismatch_pixels: 0,
    silhouette_mismatch_pixels: 0,
    unsafe_full_highlight_negative_rejected: true,
    contract,
    max_changed_pixels_observed: Math.max(...records.map((item) => item.changed_pixels)),
    checks: records.length,
  };
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify(report));
} finally {
  server.close();
}
