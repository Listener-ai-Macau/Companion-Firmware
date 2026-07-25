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

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });
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
      "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "image/png",
      "cache-control": "no-store",
    });
    response.end(value);
  });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));

const { chromium } = loadPlaywright();
const browser = await chromium.launch({
  headless: true,
  executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
});
const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });
const port = server.address().port;
const rows = [
  ["center", "1,0,1,0"],
  ["left", "-2,0,-6,0"],
  ["right", "5,0,5,0"],
  ["up", "1,-3,1,-6"],
  ["down", "1,4,1,6"],
];
const probes = [];

try {
  await page.goto(
    `http://127.0.0.1:${port}/${path.relative(root, pagePath).replaceAll("\\", "/")}#expression`,
    { waitUntil: "load" },
  );
  await page.evaluate(async () => {
    document.body.classList.add("expression-open");
    await window.__setFamilyMicroChoreographyFamily("calm");
    window.__interruptEpaperIdleGlint("test_freeze");
  });

  for (const [name, key] of rows) {
    const probe = await page.evaluate(async (gazeKey) => {
      window.__interruptEpaperIdleGlint("test_freeze");
      const presented = await window.__eyeIntegritySetGazeKey(gazeKey);
      return { presented, ...(await window.__eyeIntegrityPixelProbe()) };
    }, key);
    assert.equal(probe.presented, true, `${name}: pose was not presented`);
    assert.equal(probe.pass, true, `${name}: pixel oracle failed`);
    assert.equal(probe.open_eye_count, 2, `${name}: both eyes required`);
    assert.equal(probe.eye_pose_count, 2, `${name}: two complete poses required`);
    assert.equal(probe.paired_eye_shift, true, `${name}: paired shift required`);
    assert.equal(probe.pose_shape_mismatch_pixels, 0, `${name}: shape changed`);
    assert.equal(probe.residual_source_pixels, 0, `${name}: stale eye pixels`);
    assert.equal(probe.non_eye_mismatch_pixels, 0, `${name}: non-eye pixels changed`);
    assert.equal(probe.primary_highlight_fixed_within_pose, true);
    assert.equal(probe.direction_match, true, `${name}: gaze direction inverted`);
    probes.push({ name, key, ...probe });
    await page.locator("#overall-viewport").screenshot({
      path: path.join(screenshotDir, `${name}.png`),
    });
  }

  const byName = Object.fromEntries(probes.map((probe) => [probe.name, probe]));
  assert.deepEqual(
    byName.center.eye_rows.map((row) => row.source_black_pixels),
    byName.left.eye_rows.map((row) => row.source_black_pixels),
  );
  assert.equal(byName.center.changed_pixels, 0, "center must be the exact baseline");
  assert(byName.left.applied_dx < 0 && byName.left.applied_dy === 0);
  assert(byName.right.applied_dx > 0 && byName.right.applied_dy === 0);
  assert(byName.up.applied_dy < 0 && byName.up.applied_dx === 0);
  assert(byName.down.applied_dy > 0 && byName.down.applied_dx === 0);

  const clamp = await page.evaluate(() => window.__eyeIntegrityClampProbe(99, -99));
  assert.deepEqual(clamp.applied, { dx: 4, dy: -3 });
  assert.equal(clamp.clamped, true);
  assert.equal(clamp.fits, true);

  const staleNegative = await page.evaluate(async () => {
    await window.__eyeIntegritySetGazeKey("5,0,5,0");
    const state = overallController.state;
    const pose = await touchWholeEyePoseSource(state.activeFrame, state.storyName);
    const current = overallGaze.src;
    const meta = { ...touchGazeRenderMetaBySrc.get(current) };
    const image = await touchGazeImage(current);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 200;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    const data = context.getImageData(0, 0, 200, 200);
    const shifted = new Set(pose.eyes.flatMap((eye) => eye.points.map(
      (index) => (Math.floor(index / 200) + meta.applied_dy) * 200
        + (index % 200 + meta.applied_dx),
    )));
    const stale = pose.eyes.flatMap((eye) => eye.points).find((index) => !shifted.has(index));
    data.data[stale * 4] = data.data[stale * 4 + 1] = data.data[stale * 4 + 2] = 0;
    data.data[stale * 4 + 3] = 255;
    context.putImageData(data, 0, 0);
    const tampered = canvas.toDataURL("image/png");
    touchGazeRenderMetaBySrc.set(tampered, meta);
    overallGaze.src = tampered;
    await touchGazeImage(tampered);
    return window.__eyeIntegrityPixelProbe();
  });
  assert.equal(staleNegative.pass, false, "stale old-eye pixel must fail");
  assert(staleNegative.residual_source_pixels > 0);

  const missingEyeNegative = await page.evaluate(async () => {
    await window.__eyeIntegritySetGazeKey("5,0,5,0");
    const state = overallController.state;
    const pose = await touchWholeEyePoseSource(state.activeFrame, state.storyName);
    const current = overallGaze.src;
    const meta = { ...touchGazeRenderMetaBySrc.get(current) };
    const image = await touchGazeImage(current);
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 200;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    const data = context.getImageData(0, 0, 200, 200);
    const index = pose.eyes[1].points[0];
    const shifted = (Math.floor(index / 200) + meta.applied_dy) * 200
      + (index % 200 + meta.applied_dx);
    data.data[shifted * 4 + 3] = 0;
    context.putImageData(data, 0, 0);
    const tampered = canvas.toDataURL("image/png");
    touchGazeRenderMetaBySrc.set(tampered, meta);
    overallGaze.src = tampered;
    await touchGazeImage(tampered);
    return window.__eyeIntegrityPixelProbe();
  });
  assert.equal(missingEyeNegative.pass, false, "missing eye pixel must fail");
  assert(missingEyeNegative.pose_shape_mismatch_pixels > 0);

  const directionNegative = await page.evaluate(async () => {
    await window.__eyeIntegritySetGazeKey("-2,0,-6,0");
    const meta = touchGazeRenderMetaBySrc.get(overallGaze.src);
    meta.desired_dx = 4;
    return window.__eyeIntegrityPixelProbe();
  });
  assert.equal(directionNegative.pass, false, "inverted direction must fail");
  assert.equal(directionNegative.direction_match, false);

  await page.evaluate(async () => {
    await window.__eyeIntegritySetGazeKey("1,0,1,0");
  });
  const returned = await page.evaluate(() => window.__eyeIntegrityPixelProbe());
  assert.equal(returned.pass, true);
  assert.equal(returned.exact_baseline, true);
  assert.equal(returned.changed_pixels, 0);
} finally {
  await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const screenshots = Object.fromEntries(
  fs.readdirSync(screenshotDir).sort().map((name) => [
    name,
    sha256(fs.readFileSync(path.join(screenshotDir, name))),
  ]),
);
const result = {
  schema: "companion.whole-eye-pose.comp-req-563.v1",
  status: "PASS",
  page_sha256: sha256(fs.readFileSync(pagePath)),
  checks: {
    five_directions: probes.length === 5,
    complete_paired_eye_poses: probes.every((probe) => probe.eye_pose_count === 2),
    exact_shape: probes.every((probe) => probe.pose_shape_mismatch_pixels === 0),
    no_stale_or_non_eye_change: probes.every(
      (probe) => probe.residual_source_pixels === 0 && probe.non_eye_mismatch_pixels === 0,
    ),
    correct_direction: probes.every((probe) => probe.direction_match),
    exact_center_return: probes[0].changed_pixels === 0,
    clamp_negative: true,
    stale_pixel_negative: true,
    missing_eye_negative: true,
    inverted_direction_negative: true,
  },
  probes,
  screenshots,
  side_effects: {
    hardware: 0,
    programmer: 0,
    serial: 0,
    write: 0,
    reset: 0,
    refresh: 0,
    popup: 0,
    microphone: 0,
    production: 0,
    push: 0,
  },
};
fs.writeFileSync(output, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({
  status: result.status,
  page_sha256: result.page_sha256,
  output_sha256: sha256(fs.readFileSync(output)),
  screenshots: Object.keys(screenshots).length,
}));
