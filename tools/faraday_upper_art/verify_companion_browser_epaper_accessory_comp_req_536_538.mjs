#!/usr/bin/env node
/* Focused deterministic browser oracle for COMP-REQ-536/537/538. */

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

function canonicalBytes(value) {
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "utf8");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function canonicalTextBytes(value) {
  return Buffer.from(value.toString("utf8").replaceAll("\r\n", "\n"), "utf8");
}

function loadPlaywright() {
  const candidates = [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
  ].filter(Boolean);
  for (const candidate of candidates) {
    try {
      return require(candidate);
    } catch {
      // Continue through bounded local candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

function createStaticServer() {
  return http.createServer((request, response) => {
    const relative = `.${decodeURIComponent(request.url.split("?")[0])}`;
    const target = path.resolve(repoRoot, relative);
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

const server = createStaticServer();
const playwright = loadPlaywright();
let browser;
let observation;
const errors = [];

try {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const address = server.address();
  const runtimeUrl = (
    `http://127.0.0.1:${address.port}/${pageRepoPath}#expression`
  );
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
    errors.push(`request:${request.url()}:${request.failure()?.errorText}`)
  ));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      errors.push(`http:${response.status()}:${response.url()}`);
    }
  });
  await page.goto(runtimeUrl, { timeout: 15000, waitUntil: "load" });
  try {
    await page.waitForFunction(() => (
      window.__idleGlintContractState
      && window.__recordingContractState
      && window.__touchContractSnapshot
      && document.querySelector("#overall-viewport .viewport-frame")
        ?.naturalWidth === 200
    ), null, { timeout: 8000 });
  } catch {
    const diagnostics = await page.evaluate(() => ({
      frame: [...document.querySelectorAll("#overall-viewport img")].map(
        (image) => ({
          complete: image.complete,
          natural_width: image.naturalWidth,
          src: image.getAttribute("src"),
        }),
      ),
      globals: {
        idle: typeof window.__idleGlintContractState,
        recording: typeof window.__recordingContractState,
        snapshot: typeof window.__touchContractSnapshot,
      },
    }));
    throw new Error(
      `page readiness timeout: ${JSON.stringify({ diagnostics, errors })}`,
    );
  }
  await page.waitForTimeout(1500);

  const idleRuns = [];
  for (let run = 0; run < 2; run += 1) {
    const rows = [];
    for (let cadence = 0; cadence < 60; cadence += 1) {
      const step = cadence % 11;
      await page.evaluate(async (value) => {
        await window.__epaperFreezeIdleGlintStep(value);
      }, step);
      rows.push(await page.evaluate((cadenceIndex) => {
        const glint = window.__idleGlintContractState();
        const screen = touchCanvasMetrics();
        return {
          cadence: cadenceIndex,
          full_frame_hash: screen.signature,
          gaze_key: glint.current_key,
          gray_pixels: screen.gray,
          step: glint.step,
        };
      }, cadence));
    }
    idleRuns.push(rows);
  }

  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "overall viewport missing");
  const x = box.x + 100;
  const y = box.y + 100;
  const before = await page.evaluate(() => ({
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
    state_view: window.__expressionStateViewSnapshot(),
    transition_duration: getComputedStyle(
      document.querySelector(".recording-waves"),
    ).transitionDuration,
  }));
  const waveRows = [];
  for (let step = 0; step < 4; step += 1) {
    waveRows.push(await page.evaluate(
      (value) => window.__recordingFreezeWaveStep(value),
      step,
    ));
  }
  const beforeExit = await page.evaluate(() => ({
    frame: document.querySelector("#overall-viewport .viewport-frame").src,
    gaze: document.querySelector("#overall-viewport .viewport-gaze").src,
    natural: window.__naturalExpressionContractState(),
  }));
  await page.mouse.click(x, y, { delay: 25 });
  await page.waitForTimeout(90);
  await page.mouse.click(x, y, { delay: 25 });
  await page.waitForFunction(() => !window.__recordingContractState().active);
  const afterExit = await page.evaluate(() => ({
    frame: document.querySelector("#overall-viewport .viewport-frame").src,
    gaze: document.querySelector("#overall-viewport .viewport-gaze").src,
    natural: window.__naturalExpressionContractState(),
    recording: window.__recordingContractState(),
    state_view: window.__expressionStateViewSnapshot(),
  }));
  const source = pageBytes.toString("utf8");

  const firstCycle = idleRuns[0].slice(0, 11);
  const idleRunSha256 = idleRuns.map((rows) => sha256(canonicalBytes(rows)));
  const checks = {
    accessory_does_not_change_affect: (
      entered.natural.base_affect === before.natural.base_affect
    ),
    accessory_does_not_change_gaze: (
      JSON.stringify(entered.natural.gaze_target)
      === JSON.stringify(before.natural.gaze_target)
    ),
    accessory_only_exit_affect: (
      afterExit.natural.base_affect === beforeExit.natural.base_affect
    ),
    accessory_only_exit_frame: afterExit.frame === beforeExit.frame,
    accessory_only_exit_gaze: afterExit.gaze === beforeExit.gaze,
    accessory_state_view_separate: (
      entered.state_view.accessory_active
      && entered.state_view.mode === entered.natural.mode_override
      && !afterExit.state_view.accessory_active
    ),
    exactly_three_equal_fronts: waveRows.every((row) => (
      row.arc_count === 3
      && row.arcs.every((arc) => (
        arc.geometry.height === 13
        && arc.geometry.width === 6
        && arc.geometry.stroke === 2
      ))
    )),
    idle_baseline_return_exact: (
      firstCycle[10].full_frame_hash === firstCycle[0].full_frame_hash
    ),
    idle_glint_changed_frames_three: (
      firstCycle[8].full_frame_hash !== firstCycle[0].full_frame_hash
      && firstCycle[9].full_frame_hash !== firstCycle[8].full_frame_hash
      && firstCycle[10].full_frame_hash === firstCycle[0].full_frame_hash
    ),
    idle_quiet_hold_stable: (
      new Set(firstCycle.slice(0, 8).map((row) => row.full_frame_hash)).size
      === 1
    ),
    idle_two_runs_equal: idleRunSha256[0] === idleRunSha256[1],
    inward_or_absorb_insert_only: waveRows.slice(1).every((row) => (
      row.transition.moved
        .filter((item) => item.from_slot !== null)
        .every((item) => item.to_slot > item.from_slot)
      && (
        row.transition.inserted.length === 0
        || row.transition.absorbed.length > 0
      )
    )),
    no_css_interpolation: (
      entered.transition_duration === "0s"
      && !source.includes("requestAnimationFrame")
      && !source.includes("Math.random")
    ),
    one_bit_runtime_pixels: (
      idleRuns.flat().every((row) => row.gray_pixels === 0)
      && waveRows.every((row) => row.gray_pixels === 0)
    ),
    recording_is_not_mode_override: (
      entered.recording.interaction_mode === "expression"
      && entered.natural.mode_override === before.natural.mode_override
    ),
    source_page_exact: (
      !args["expected-page-sha256"]
      || pageCanonicalSha256 === args["expected-page-sha256"].toUpperCase()
    ),
    zero_page_or_http_errors: errors.length === 0,
  };
  const failed = Object.entries(checks)
    .filter(([, value]) => !value)
    .map(([name]) => name);
  observation = {
    schema: "companion.comp-req-536-538-focused-oracle.v1",
    status: failed.length ? "NO_GO" : "PASS",
    checks,
    errors,
    failed,
    inputs: {
      page_canonical_sha256: pageCanonicalSha256,
      page_repo_path: pageRepoPath,
    },
    observed: {
      accessory: {
        after_exit: afterExit,
        before,
        before_exit: beforeExit,
        entered,
      },
      idle: {
        cadence_ms: 480,
        run_sha256: idleRunSha256,
        runs: idleRuns,
      },
      waves: waveRows,
    },
    side_effects: {
      hardware: 0,
      microphone_request: 0,
      owner_prompt: 0,
      production_write: 0,
    },
  };
  if (failed.length) throw new Error(`focused checks failed: ${failed}`);
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const bytes = canonicalBytes(observation);
fs.writeFileSync(outputPath, bytes);
console.log(JSON.stringify({
  output: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
  sha256: sha256(bytes),
  status: observation.status,
}));
