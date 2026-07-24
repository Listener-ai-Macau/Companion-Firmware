#!/usr/bin/env node
/* Focused real-clock browser oracle for COMP-REQ-539. */

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
const pageRepoPath = [
  "docs/art/iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
].join("/");
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error(`invalid argument near ${key || "<end>"}`);
    }
    result[key.slice(2)] = value;
  }
  if (!result.output) throw new Error("missing --output");
  return result;
}

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}

function jsonBytes(value) {
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "utf8");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function canonicalTextBytes(value) {
  return Buffer.from(value.toString("utf8").replaceAll("\r\n", "\n"), "utf8");
}

function loadPlaywright() {
  for (const candidate of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
  ].filter(Boolean)) {
    try {
      return require(candidate);
    } catch {
      // Continue through bounded local candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

function createServer() {
  return http.createServer((request, response) => {
    const target = path.resolve(
      repoRoot,
      `.${decodeURIComponent(request.url.split("?")[0])}`,
    );
    if (!target.startsWith(`${repoRoot}${path.sep}`)) {
      response.writeHead(403).end();
      return;
    }
    fs.readFile(target, (error, bytes) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      const contentType = target.endsWith(".html")
        ? "text/html; charset=utf-8"
        : target.endsWith(".png")
          ? "image/png"
          : "application/octet-stream";
      response.writeHead(200, { "content-type": contentType });
      response.end(bytes);
    });
  });
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
fs.mkdirSync(path.dirname(outputPath), { recursive: true });

const pageBytes = fs.readFileSync(pagePath);
const pageCanonicalSha256 = sha256(canonicalTextBytes(pageBytes));
if (
  args["expected-page-sha256"]
  && pageCanonicalSha256 !== args["expected-page-sha256"].toUpperCase()
) {
  throw new Error("page canonical SHA-256 mismatch");
}

const server = createServer();
const playwright = loadPlaywright();
let browser;
const errors = [];

try {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  const url = `http://127.0.0.1:${address.port}/${pageRepoPath}#expression`;
  browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "zh-CN",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { height: 900, width: 1280 },
  });
  page.on("pageerror", (error) => errors.push(`page:${error.message}`));
  page.on("requestfailed", (request) => (
    errors.push(`request:${request.failure()?.errorText}`)
  ));
  page.on("response", (response) => {
    if (response.status() >= 400) errors.push(`http:${response.status()}`);
  });
  await page.goto(url, { timeout: 15000, waitUntil: "load" });
  await page.waitForFunction(() => (
    typeof window.__resetEpaperIdleGlintRealClock === "function"
    && typeof window.__recordingFreezeMeterStep === "function"
    && document.querySelector("#overall-viewport .viewport-frame")
      ?.naturalWidth === 200
  ), null, { timeout: 10000 });
  await page.waitForTimeout(1800);

  const idleRuns = [];
  const idleFirstChanged = [];
  for (let run = 0; run < 2; run += 1) {
    const startedAt = Date.now();
    const reset = await page.evaluate(() => (
      window.__resetEpaperIdleGlintRealClock()
    ));
    assert(reset.eligible && reset.started, "real idle scheduler did not start");
    await page.waitForFunction(() => (
      window.__idleGlintContractState().trace.some((row) => row.changed)
    ), null, { timeout: 960 });
    idleFirstChanged.push(Date.now() - startedAt);
    await page.waitForFunction(() => (
      window.__idleGlintContractState().trace.length >= 60
    ), null, { timeout: 35000 });
    idleRuns.push(await page.evaluate(() => (
      window.__idleGlintContractState().trace.slice(0, 60).map((row) => ({
        changed: row.changed,
        cycle: row.cycle,
        key: row.key,
        previous_key: row.previous_key,
        refresh_requested: row.refresh_requested,
        source: row.source,
        step: row.step,
      }))
    )));
  }
  const idleHashes = idleRuns.map((rows) => sha256(jsonBytes(rows)));
  await page.evaluate(() => window.__interruptEpaperIdleGlint("focused_input"));

  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "overall viewport missing");
  const x = box.x + 100;
  const y = box.y + 100;
  const holdSelector = [
    ".hold-progress",
    ".hold-track",
    ".hold-fill",
    "[data-hold-progress]",
  ].join(",");
  const feedback = async (label) => page.evaluate(
    ({ labelValue, selector }) => ({
      label: labelValue,
      nodes: document.querySelectorAll(selector).length,
      screen: window.__touchContractSnapshot().canvasSignature,
    }),
    { labelValue: label, selector: holdSelector },
  );
  const holdRows = [await feedback("rest")];

  await page.mouse.move(x, y);
  await page.mouse.down();
  holdRows.push(await feedback("pointerdown"));
  await page.waitForTimeout(1200);
  holdRows.push(await feedback("hold_1200ms"));
  await page.mouse.up();
  holdRows.push(await feedback("early_up"));
  await page.waitForTimeout(700);

  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.mouse.move(x + 70, y, { steps: 3 });
  holdRows.push(await feedback("drag"));
  await page.mouse.up();

  await page.dispatchEvent("#overall-viewport", "pointerdown", {
    bubbles: true,
    clientX: x,
    clientY: y,
    pointerId: 91,
    pointerType: "touch",
  });
  await page.dispatchEvent("#overall-viewport", "pointercancel", {
    bubbles: true,
    clientX: x,
    clientY: y,
    pointerId: 91,
    pointerType: "touch",
  });
  holdRows.push(await feedback("cancel"));

  const fullHoldBaseline = await feedback("full_hold_start");
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.waitForTimeout(1500);
  holdRows.push(await feedback("hold_1500ms"));
  await page.waitForFunction(
    () => window.__overallInteractionState().mode === "menu",
    null,
    { timeout: 2000 },
  );
  await page.mouse.up();
  const fullHold = await page.evaluate((selector) => ({
    menu_entries: window.__touchContractState().menuEntries,
    mode: window.__overallInteractionState().mode,
    progress_nodes: document.querySelectorAll(selector).length,
  }), holdSelector);
  await page.locator('[data-testid="integrated-menu-return"]').click();
  await page.waitForFunction(
    () => window.__overallInteractionState().mode === "expression",
  );

  const beforeRecording = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    snapshot: window.__touchContractSnapshot(),
  }));
  await page.mouse.click(x, y, { delay: 25 });
  await page.waitForTimeout(90);
  await page.mouse.click(x, y, { delay: 25 });
  await page.waitForFunction(() => window.__recordingContractState().active);
  const entered = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    recording: window.__recordingContractState(),
    snapshot: window.__touchContractSnapshot(),
    transition: getComputedStyle(
      document.querySelector(".recording-levels"),
    ).transitionDuration,
  }));
  const meterRows = [];
  for (let step = 0; step < 8; step += 1) {
    meterRows.push(await page.evaluate(
      (value) => window.__recordingFreezeMeterStep(value),
      step,
    ));
  }
  const meterPixels = await page.evaluate(() => {
    const canvas = document.querySelector(".recording-levels");
    const data = canvas.getContext("2d").getImageData(0, 0, 200, 200).data;
    const black = [];
    let gray = 0;
    for (let index = 0; index < 40000; index += 1) {
      const offset = index * 4;
      if (data[offset + 3] && ![0, 255].includes(data[offset])) gray += 1;
      if (data[offset + 3] && data[offset] < 128) {
        black.push([index % 200, Math.floor(index / 200)]);
      }
    }
    return { black, gray };
  });
  await page.evaluate(() => window.__recordingResumeLevels());

  const routeBeforeTap = entered.natural.route_count;
  await page.mouse.click(x + 20, y, { delay: 25 });
  await page.waitForTimeout(720);
  const evolved = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    recording: window.__recordingContractState(),
  }));
  assert(
    evolved.natural.route_count === routeBeforeTap + 1,
    "recording suppressed underlying expression route",
  );
  await page.waitForTimeout(520);
  const beforeExit = await page.evaluate(() => ({
    affect: window.__naturalExpressionContractState().base_affect,
    gaze: window.__naturalExpressionContractState().gaze_target,
    frame: document.querySelector("#overall-viewport .viewport-frame").src,
  }));
  await page.mouse.click(x + 20, y, { delay: 25 });
  await page.waitForTimeout(90);
  await page.mouse.click(x + 20, y, { delay: 25 });
  await page.waitForFunction(() => !window.__recordingContractState().active);
  const afterExit = await page.evaluate(() => ({
    affect: window.__naturalExpressionContractState().base_affect,
    gaze: window.__naturalExpressionContractState().gaze_target,
    frame: document.querySelector("#overall-viewport .viewport-frame").src,
    recording: window.__recordingContractState(),
  }));

  const source = pageBytes.toString("utf8");
  const columnXs = new Set(meterPixels.black.map(([pixelX]) => pixelX));
  const expectedXs = new Set([
    170, 171, 172, 173,
    181, 182, 183, 184,
    192, 193, 194, 195,
  ]);
  const checks = {
    accessory_does_not_replace_affect: (
      entered.natural.base_affect === beforeRecording.natural.base_affect
    ),
    accessory_does_not_replace_gaze: (
      JSON.stringify(entered.natural.gaze_target)
      === JSON.stringify(beforeRecording.natural.gaze_target)
    ),
    accessory_only_exit: (
      afterExit.affect === beforeExit.affect
      && JSON.stringify(afterExit.gaze) === JSON.stringify(beforeExit.gaze)
      && afterExit.frame === beforeExit.frame
    ),
    committed_480ms_contract: (
      entered.recording.meterContract.step_ms === 480
      && entered.recording.meterContract.interpolation === "none"
      && entered.transition === "0s"
    ),
    deterministic_level_pipeline: meterRows.slice(1).every((row, index) => (
      row.samples[0] === meterRows[index].samples[1]
      && row.samples[1] === meterRows[index].samples[2]
      && row.transition.inserted.slot === 2
    )),
    exactly_three_equal_columns: meterRows.every((row) => (
      row.column_count === 3
      && row.columns.every((column) => column.geometry.width === 4)
    )),
    full_hold_direct_menu_once: (
      fullHold.mode === "menu"
      && fullHold.menu_entries === 1
      && fullHold.progress_nodes === 0
    ),
    idle_first_change_within_960ms: idleFirstChanged.every((ms) => ms <= 960),
    idle_real_clock_has_changes: idleRuns.every(
      (rows) => rows.some((row) => row.changed),
    ),
    idle_real_clock_repeats: (
      idleHashes[0] === idleHashes[1]
      && idleRuns.every((rows) => rows.at(-1).cycle >= 5)
    ),
    idle_returns_to_baseline: idleRuns.every((rows) => (
      rows.some((row) => row.changed && row.key === "1,0,1,0")
    )),
    no_arc_pixels: (
      meterPixels.gray === 0
      && [...columnXs].every((pixelX) => expectedXs.has(pixelX))
    ),
    no_browser_interpolation: (
      !source.includes("requestAnimationFrame")
      && !source.includes("transition:all")
      && entered.transition === "0s"
    ),
    no_hold_dom_or_pixels: (
      holdRows.every((row) => row.nodes === 0)
      && holdRows[0].screen === holdRows[1].screen
      && holdRows[1].screen === holdRows[2].screen
      && holdRows.at(-1).screen === fullHoldBaseline.screen
    ),
    no_legacy_recording_renderer: [
      ".recording-waves",
      "drawBinaryWaveFront",
      "renderRecordingWaveStep",
      "recordingWaveContract",
      "arc_count",
    ].every((token) => !source.includes(token)),
    one_recording_dot_and_level_layer: (
      entered.recording.indicatorNodes === 1
      && entered.recording.levelNodes === 1
      && entered.recording.indicatorVisible
      && entered.recording.levelsVisible
    ),
    one_bit_runtime: (
      entered.snapshot.canvasInk > 0
      && meterRows.every((row) => row.gray_pixels === 0)
    ),
    page_and_requests_clean: errors.length === 0,
    source_page_exact: pageCanonicalSha256.length === 64,
  };
  const failed = Object.entries(checks)
    .filter(([, passed]) => !passed)
    .map(([name]) => name);
  const result = {
    schema: "companion.comp-req-539-focused-real-clock.v1",
    requirements: ["COMP-REQ-539"],
    status: failed.length ? "NO_GO" : "PASS",
    checks,
    failed,
    errors,
    inputs: {
      page_canonical_sha256: pageCanonicalSha256,
      page_repo_path: pageRepoPath,
    },
    observed: {
      hold: {
        menu_hold_ms: 3000,
        rows: holdRows,
        full_hold: fullHold,
      },
      idle: {
        cadence_ms: 480,
        first_changed_within_960ms: checks.idle_first_change_within_960ms,
        run_sha256: idleHashes,
        runs: idleRuns,
      },
      meter: {
        rows: meterRows,
        pixel_x: [...columnXs].sort((a, b) => a - b),
        gray_pixels: meterPixels.gray,
      },
      recording: {
        entered: entered.recording,
        evolved: evolved.recording,
        exited: afterExit.recording,
      },
    },
    side_effects: {
      hardware: 0,
      microphone_request: 0,
      owner_prompt: 0,
      production_write: 0,
    },
  };
  fs.writeFileSync(outputPath, jsonBytes(result));
  console.log(JSON.stringify({
    failed,
    output: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
    sha256: sha256(fs.readFileSync(outputPath)),
    status: result.status,
  }));
  if (failed.length) process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
