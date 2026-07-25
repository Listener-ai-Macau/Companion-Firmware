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
const screenshotsIndex = process.argv.indexOf("--screenshots-dir");
assert(outputIndex >= 0 && process.argv[outputIndex + 1], "missing --output");
assert(screenshotsIndex >= 0 && process.argv[screenshotsIndex + 1], "missing --screenshots-dir");
const output = path.resolve(root, process.argv[outputIndex + 1]);
const screenshotsDir = path.resolve(root, process.argv[screenshotsIndex + 1]);
for (const target of [output, screenshotsDir]) {
  assert(target.startsWith(`${root}${path.sep}`), "output must remain in repository");
}

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

async function tap(page, x, y) {
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.waitForTimeout(24);
  await page.mouse.up();
}

async function doubleTap(page, x, y) {
  await tap(page, x, y);
  await page.waitForTimeout(90);
  await tap(page, x, y);
}

async function faceState(page) {
  return page.evaluate(async () => {
    const frame = document.querySelector("#overall-viewport .viewport-frame");
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    const family = window.__familyMicroChoreographyState();
    const recording = window.__recordingContractState();
    const eye = await window.__eyeIntegrityPixelProbe();
    return {
      frame: frame.src,
      gaze: gaze.hidden ? "" : gaze.src,
      family_step: family.step,
      family_cycle: family.cycle,
      family_active: family.active,
      recording_active: recording.active,
      recording_level_nodes: recording.levelNodes,
      meter_step: recording.meterStep,
      eye,
    };
  });
}

async function freezeCycle(page, mode, steps) {
  await page.evaluate(() => window.__setFamilyMicroChoreographyFamily("calm"));
  const rows = [];
  for (const step of steps) {
    if (step !== 0) {
      assert(await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step));
    }
    const state = await faceState(page);
    assert(state.eye.pass, `${mode} step ${step} eye integrity`);
    assert.equal(state.eye.open_eye_count, 2);
    assert.equal(state.eye.sparkle_components, 2);
    assert(state.eye.eye_rows.every((eye) => eye.sparkle_components === 1));
    const screenshot = path.join(screenshotsDir, `${mode}-step-${step}.png`);
    await page.locator("#overall-viewport").screenshot({ path: screenshot });
    rows.push({
      mode,
      step,
      face_sha256: sha256(`${state.frame}\n${state.gaze}`),
      screenshot: path.relative(root, screenshot).replaceAll("\\", "/"),
      screenshot_sha256: sha256(fs.readFileSync(screenshot)),
      ...state,
      frame: undefined,
      gaze: undefined,
    });
  }
  return rows;
}

try {
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.mkdirSync(screenshotsDir, { recursive: true });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { chromium } = loadPlaywright();
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });
  const port = server.address().port;
  await page.goto(
    `http://127.0.0.1:${port}/${path.relative(root, pagePath).replaceAll("\\", "/")}#expression`,
    { waitUntil: "networkidle" },
  );
  await page.waitForFunction(() => window.__eyeIntegrityPixelProbe);
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "viewport missing");
  const center = [box.x + 100, box.y + 100];
  const steps = [0, 2, 4, 6, 8, 9];

  const off = await freezeCycle(page, "idle", steps);
  assert(new Set(off.map((row) => row.face_sha256)).size >= 4, "idle face choreography is not visible");
  assert.equal(off[0].face_sha256, off.at(-1).face_sha256, "idle baseline did not return");

  await page.evaluate(() => window.__resetEpaperIdleGlintRealClock());
  const liveIdle = [];
  for (let index = 0; index < 10; index++) {
    await page.waitForTimeout(520);
    const state = await faceState(page);
    assert(state.family_active);
    assert(state.eye.pass);
    const screenshot = path.join(screenshotsDir, `idle-live-${index}.png`);
    await page.locator("#overall-viewport").screenshot({ path: screenshot });
    liveIdle.push({
      mode: "日常实时时钟",
      step: index,
      face_sha256: sha256(`${state.frame}\n${state.gaze}`),
      screenshot: path.relative(root, screenshot).replaceAll("\\", "/"),
      screenshot_sha256: sha256(fs.readFileSync(screenshot)),
      family_step: state.family_step,
      family_cycle: state.family_cycle,
    });
  }
  assert(new Set(liveIdle.map((row) => row.face_sha256)).size >= 4);
  assert(liveIdle.some((row) => row.family_cycle >= 1), "idle live cycle did not complete");

  await doubleTap(page, center[0], center[1]);
  await page.waitForFunction(() => window.__recordingContractState().active);
  const liveRecording = [];
  for (let index = 0; index < 6; index++) {
    await page.waitForTimeout(520);
    const state = await faceState(page);
    assert(state.recording_active);
    assert(state.family_active, "recording entry did not resume face choreography");
    assert(state.eye.pass);
    const screenshot = path.join(screenshotsDir, `recording-live-${index}.png`);
    await page.locator("#overall-viewport").screenshot({ path: screenshot });
    liveRecording.push({
      mode: "录音实时时钟",
      step: index,
      face_sha256: sha256(`${state.frame}\n${state.gaze}`),
      screenshot: path.relative(root, screenshot).replaceAll("\\", "/"),
      screenshot_sha256: sha256(fs.readFileSync(screenshot)),
      meter_step: state.meter_step,
      family_step: state.family_step,
    });
  }
  assert(new Set(liveRecording.map((row) => row.face_sha256)).size >= 3);
  assert(new Set(liveRecording.map((row) => row.meter_step)).size >= 3);

  const on = await freezeCycle(page, "recording", steps);
  assert(on.every((row) => row.recording_active), "recording dropped during choreography");
  assert(on.every((row) => row.recording_level_nodes === 1), "recording meter layer count drift");
  assert.deepEqual(
    on.map((row) => row.face_sha256),
    off.map((row) => row.face_sha256),
    "recording changed or froze the underlying face sequence",
  );
  assert(new Set(on.map((row) => row.meter_step)).size >= 1);

  await doubleTap(page, center[0], center[1]);
  await page.waitForFunction(() => !window.__recordingContractState().active);
  const exit = await page.evaluate(() => window.__recordingContractState());
  assert.equal(exit.levelNodes, 1);
  assert.equal(exit.levelsVisible, false);

  const contact = await browser.newPage({ viewport: { width: 1240, height: 500 } });
  const imageRows = [
    ["日常空闲", off],
    ["日常实时时钟", liveIdle],
    ["录音实时时钟", liveRecording],
    ["录音逐拍比对", on],
  ].map(([label, rows]) => (
    `<section><strong>${label}</strong><div>${
      rows.map((row) => `<figure><img src="data:image/png;base64,${
        fs.readFileSync(path.join(root, row.screenshot)).toString("base64")
      }"><figcaption>${row.step}</figcaption></figure>`).join("")
    }</div></section>`
  )).join("");
  await contact.setContent(`<style>
    body{margin:8px;background:#ddd;font:16px Arial;color:#111}
    section{margin:0 0 10px}strong{display:block;margin-bottom:4px}
    section>div{display:flex;gap:4px}figure{margin:0;background:#fff}
    img{display:block;width:190px;height:190px;image-rendering:pixelated}
    figcaption{text-align:center;padding:2px}
  </style>${imageRows}`);
  const contactPath = path.join(screenshotsDir, "idle-recording-contact.png");
  await contact.screenshot({ path: contactPath, fullPage: true });
  await browser.close();

  const report = {
    schema: "companion.comp_req_553_554.coordinated_face_recording.v1",
    status: "PASS",
    page_sha256: sha256(Buffer.from(fs.readFileSync(pagePath, "utf8").replaceAll("\r\n", "\n"))),
    cadence_ms: 480,
    steps,
    idle_distinct_face_hashes: new Set(off.map((row) => row.face_sha256)).size,
    idle_live_distinct_face_hashes: new Set(
      liveIdle.map((row) => row.face_sha256),
    ).size,
    recording_live_distinct_face_hashes: new Set(
      liveRecording.map((row) => row.face_sha256),
    ).size,
    recording_live_distinct_meter_steps: new Set(
      liveRecording.map((row) => row.meter_step),
    ).size,
    recording_underlying_face_sequence_equal: true,
    paired_eye_steps: on.filter((row) => row.eye.paired_sparkles).length,
    recording_meter_layers: 1,
    recording_exit_meter_visible: false,
    off,
    live_idle: liveIdle,
    live_recording: liveRecording,
    on,
    contact_sheet: path.relative(root, contactPath).replaceAll("\\", "/"),
    contact_sheet_sha256: sha256(fs.readFileSync(contactPath)),
  };
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  console.log(JSON.stringify({
    status: report.status,
    page_sha256: report.page_sha256,
    idle_distinct_face_hashes: report.idle_distinct_face_hashes,
    idle_live_distinct_face_hashes: report.idle_live_distinct_face_hashes,
    recording_live_distinct_face_hashes: report.recording_live_distinct_face_hashes,
    recording_live_distinct_meter_steps: report.recording_live_distinct_meter_steps,
    paired_eye_steps: report.paired_eye_steps,
    recording_underlying_face_sequence_equal: true,
    contact_sheet_sha256: report.contact_sheet_sha256,
  }));
} finally {
  server.close();
}
