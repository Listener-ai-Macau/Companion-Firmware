#!/usr/bin/env node
/* Focused four-family visual and pixel smoke for COMP-REQ-540. */

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
const allFamilies = [
  "calm",
  "curious",
  "warm",
  "playful",
  "sleepy",
  "delighted",
  "bashful",
  "thoughtful",
  "focused",
  "alert",
];

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
  if (!result.output || !result["screenshots-dir"]) {
    throw new Error("missing --output or --screenshots-dir");
  }
  result.families = result.families || "calm,curious,warm,playful";
  result["real-clock-cadences"] = Number(result["real-clock-cadences"] || 0);
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

function pixelDelta(previous, current) {
  const before = Buffer.from(previous, "base64");
  const after = Buffer.from(current, "base64");
  assert.equal(before.length, 5000);
  assert.equal(after.length, 5000);
  let changed = 0;
  let minX = 200;
  let minY = 200;
  let maxX = -1;
  let maxY = -1;
  for (let byteIndex = 0; byteIndex < before.length; byteIndex += 1) {
    let difference = before[byteIndex] ^ after[byteIndex];
    if (!difference) continue;
    const y = Math.floor(byteIndex / 25);
    const byteX = (byteIndex % 25) * 8;
    for (let bit = 0; bit < 8; bit += 1) {
      if (!(difference & (0x80 >> bit))) continue;
      const x = byteX + bit;
      changed += 1;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  return {
    changed_pixels: changed,
    bounds: changed ? { min_x: minX, min_y: minY, max_x: maxX, max_y: maxY } : null,
  };
}

async function packedStage(page) {
  return page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const meter = stage.querySelector(".recording-levels");
    const canvas = document.createElement("canvas");
    canvas.width = 200;
    canvas.height = 200;
    const context = canvas.getContext("2d");
    if (!frame.hidden) context.drawImage(frame, 0, 0);
    if (!gaze.hidden) {
      const transform = getComputedStyle(gaze).transform;
      const matrix = !transform || transform === "none"
        ? { e: 0, f: 0 }
        : new DOMMatrixReadOnly(transform);
      context.drawImage(gaze, Math.round(matrix.e), Math.round(matrix.f));
    }
    if (meter && !meter.hidden) context.drawImage(meter, 0, 0);
    const rgba = context.getImageData(0, 0, 200, 200).data;
    const packed = new Uint8Array(5000);
    let ink = 0;
    let sumX = 0;
    let sumY = 0;
    for (let pixel = 0; pixel < 40000; pixel += 1) {
      if (rgba[pixel * 4] >= 128) continue;
      packed[Math.floor(pixel / 8)] |= 0x80 >> (pixel % 8);
      ink += 1;
      sumX += pixel % 200;
      sumY += Math.floor(pixel / 200);
    }
    let binary = "";
    for (const value of packed) binary += String.fromCharCode(value);
    return {
      base64: btoa(binary),
      ink,
      centroid: {
        x: Number((sumX / ink).toFixed(3)),
        y: Number((sumY / ink).toFixed(3)),
      },
      layer: window.__overallLayerSnapshot(),
      family: window.__familyMicroChoreographyState(),
      recording: window.__recordingContractState(),
    };
  });
}

async function runRealClockTrace(browser, url, family, run, cadenceCount) {
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "zh-CN",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { height: 900, width: 1280 },
  });
  const localErrors = [];
  try {
    const page = await context.newPage();
    page.on("pageerror", (error) => localErrors.push(`page:${error.message}`));
    page.on("requestfailed", (request) => (
      localErrors.push(`request:${request.failure()?.errorText}`)
    ));
    page.on("response", (response) => {
      if (response.status() >= 400) localErrors.push(`http:${response.status()}`);
    });
    await page.goto(url, { timeout: 15000, waitUntil: "load" });
    await page.waitForFunction(() => (
      typeof window.__setFamilyMicroChoreographyFamily === "function"
      && document.querySelector("#overall-viewport .viewport-frame")
        ?.naturalWidth === 200
    ), null, { timeout: 10000 });
    const selected = await page.evaluate(
      (name) => window.__setFamilyMicroChoreographyFamily(name),
      family,
    );
    assert(selected.presented, `${family} run ${run} select failed`);
    const reset = await page.evaluate(() => (
      window.__resetEpaperIdleGlintRealClock()
    ));
    assert(reset.eligible && reset.started, `${family} run ${run} clock inert`);
    await page.waitForFunction(
      (count) => window.__familyMicroChoreographyState().trace.length >= count,
      cadenceCount,
      { timeout: cadenceCount * 480 + 12000 },
    );
    const state = await page.evaluate((count) => {
      window.__interruptEpaperIdleGlint("real_clock_capture");
      const snapshot = window.__familyMicroChoreographyState();
      return {
        current_frame: snapshot.current_frame,
        current_key: snapshot.current_key,
        trace: snapshot.trace.slice(0, count).map((row) => ({
          sequence: row.sequence,
          cycle: row.cycle,
          step: row.step,
          family: row.family,
          story: row.story,
          phase: row.phase,
          frame: row.frame,
          frame_index: row.frame_index,
          key: row.key,
          previous_key: row.previous_key,
          previous_frame: row.previous_frame,
          changed: row.changed,
          refresh_requested: row.refresh_requested,
          components: [...row.components],
          max_component_step_px: row.max_component_step_px,
          source: row.source,
        })),
      };
    }, cadenceCount);
    assert.equal(localErrors.length, 0, `${family} run ${run} browser errors`);
    const bytes = jsonBytes(state.trace);
    return {
      family,
      run,
      trace_sha256: sha256(bytes),
      trace: state.trace,
      current_frame: state.current_frame,
      current_key: state.current_key,
      errors: localErrors,
    };
  } finally {
    await context.close();
  }
}

const args = parseArgs(process.argv.slice(2));
const selectedFamilies = args.families === "all"
  ? [...allFamilies]
  : args.families.split(",").map((item) => item.trim()).filter(Boolean);
assert(
  selectedFamilies.length > 0
  && selectedFamilies.every((family) => allFamilies.includes(family)),
  "invalid family selection",
);
const outputPath = path.resolve(repoRoot, args.output);
const screenshotsDir = path.resolve(repoRoot, args["screenshots-dir"]);
if (
  !outputPath.startsWith(`${repoRoot}${path.sep}`)
  || !screenshotsDir.startsWith(`${repoRoot}${path.sep}`)
) {
  throw new Error("outputs must remain inside repository");
}
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.mkdirSync(screenshotsDir, { recursive: true });

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
const families = [];

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
    typeof window.__setFamilyMicroChoreographyFamily === "function"
    && document.querySelector("#overall-viewport .viewport-frame")
      ?.naturalWidth === 200
  ), null, { timeout: 10000 });

  const interruptionReasons = [
    "tap",
    "drag",
    "registered_blink",
    "recording",
    "menu",
    "upper_state",
  ];
  for (const [familyIndex, family] of selectedFamilies.entries()) {
    const selected = await page.evaluate(
      (name) => window.__setFamilyMicroChoreographyFamily(name),
      family,
    );
    assert(selected.presented, `${family} baseline presentation failed`);
    const phases = [];
    for (const step of [0, 2, 4, 6, 8, 9, 0]) {
      if (step !== 0) {
        const row = await page.evaluate(
          (value) => window.__epaperFreezeIdleGlintStep(value),
          step,
        );
        assert(row, `${family} step ${step} failed`);
      }
      await page.waitForTimeout(40);
      const packed = await packedStage(page);
      const bytes = Buffer.from(packed.base64, "base64");
      phases.push({
        step,
        packed_base64: packed.base64,
        sha256: sha256(bytes),
        ink: packed.ink,
        centroid: packed.centroid,
        layer: packed.layer,
        trace: packed.family.trace.at(-1) || null,
      });
      await page.locator("#overall-viewport").screenshot({
        path: path.join(screenshotsDir, `${family}-step-${step}.png`),
      });
    }
    const baseline = phases[0];
    const returned = phases.at(-1);
    const deltas = phases.slice(1).map((phase, index) => ({
      from_step: phases[index].step,
      to_step: phase.step,
      ...pixelDelta(phases[index].packed_base64, phase.packed_base64),
      centroid_delta: {
        x: Number((phase.centroid.x - phases[index].centroid.x).toFixed(3)),
        y: Number((phase.centroid.y - phases[index].centroid.y).toFixed(3)),
      },
    }));
    assert.equal(returned.sha256, baseline.sha256, `${family} did not return`);
    assert.notEqual(phases[1].sha256, baseline.sha256, `${family} first beat inert`);
    assert.notEqual(phases[2].sha256, phases[1].sha256, `${family} second beat inert`);
    assert(
      phases.slice(1, 3).every((phase) => phase.trace?.components.length >= 2),
      `${family} did not coordinate two component classes`,
    );
    assert(
      phases.slice(1, 3).every((phase) => phase.trace.max_component_step_px <= 2),
      `${family} declared step exceeds two pixels`,
    );
    assert(
      phases.every((phase) => (
        phase.layer.visible_images === 2
        && phase.layer.gaze_nodes === 1
        && phase.layer.recording_indicator_nodes === 0
      )),
      `${family} layer invariant failed`,
    );
    const interruption = await page.evaluate(async ({ reason }) => {
      const before = window.__familyMicroChoreographyState();
      await window.__epaperFreezeIdleGlintStep(2);
      window.__interruptEpaperIdleGlint(reason);
      window.__resumeEpaperIdleGlint(reason);
      const deadline = performance.now() + 3000;
      while (performance.now() < deadline) {
        const current = window.__familyMicroChoreographyState();
        const plan = current.manifest.plans.find(
          (item) => item.state === current.family,
        );
        const story = window.__companionEpaperVisualManifest
          .emotion_choreography.states.find(
            (item) => item.state === current.family,
          );
        if (
          plan
          && story
          && current.current_key
            === window.__companionEpaperVisualManifest.idle_glint.baseline_key
          && current.current_frame
        ) {
          return {
            reason,
            before_interruptions: before.interruptions,
            after_interruptions: current.interruptions,
            family: current.family,
            key: current.current_key,
            frame: current.current_frame,
            baseline_frame_index: plan.baseline_frame,
          };
        }
        await new Promise((resolve) => setTimeout(resolve, 20));
      }
      return null;
    }, {
      reason: interruptionReasons[familyIndex % interruptionReasons.length],
    });
    assert(interruption, `${family} interruption did not resume`);
    assert(
      interruption.after_interruptions > interruption.before_interruptions,
      `${family} interruption was not counted`,
    );
    const interruptionPacked = await packedStage(page);
    assert.equal(
      sha256(Buffer.from(interruptionPacked.base64, "base64")),
      baseline.sha256,
      `${family} interruption did not restore baseline`,
    );
    families.push({
      family,
      selected,
      phases: phases.map(({ packed_base64: _packed, ...phase }) => phase),
      deltas,
      interruption,
      exact_baseline_return: returned.sha256 === baseline.sha256,
    });
  }

  const sequenceSignatures = families.map((family) => (
    family.phases.map((phase) => phase.sha256).join(":")
  ));
  const realClockCadences = args["real-clock-cadences"];
  const realClockRuns = realClockCadences > 0
    ? await Promise.all(selectedFamilies.flatMap((family) => (
      [1, 2].map((run) => (
        runRealClockTrace(
          browser,
          url,
          family,
          run,
          realClockCadences,
        )
      ))
    )))
    : [];
  const realClock = selectedFamilies.map((family) => {
    const runs = realClockRuns.filter((item) => item.family === family);
    if (!runs.length) return { family, runs: [], skipped: true };
    const plan = families.find((item) => item.family === family).selected;
    const tracesEqual = runs[0].trace_sha256 === runs[1].trace_sha256;
    const firstChanged = runs[0].trace.findIndex((row) => row.changed);
    const changedRows = runs[0].trace.filter((row) => row.changed);
    const maxUnchangedRun = runs[0].trace.reduce(
      (state, row) => row.changed
        ? { current: 0, max: Math.max(state.max, state.current) }
        : { current: state.current + 1, max: state.max },
      { current: 0, max: 0 },
    ).max;
    const baselineReturns = runs[0].trace.filter(
      (row) => row.phase === "baseline_return",
    );
    return {
      family,
      runs: runs.map(({ trace, ...run }) => ({
        ...run,
        trace_count: trace.length,
        changed_count: trace.filter((row) => row.changed).length,
        first_changed_cadence: trace.findIndex((row) => row.changed) + 1,
        first_changed_derived_ms: (
          (trace.findIndex((row) => row.changed) + 1) * 480
        ),
      })),
      traces_equal: tracesEqual,
      first_changed_cadence: firstChanged + 1,
      first_changed_derived_ms: (firstChanged + 1) * 480,
      changed_count: changedRows.length,
      component_classes: [...new Set(changedRows.flatMap((row) => row.components))],
      baseline_return_count: baselineReturns.length,
      all_refreshes_source_backed: runs[0].trace.every(
        (row) => row.changed === row.refresh_requested,
      ),
      exact_baseline_returns: baselineReturns.every(
        (row) => (
          row.frame_index === plan.baseline_frame
          && row.key === "1,0,1,0"
        ),
      ),
      minimum_quiet_gap: Math.min(
        ...runs[0].trace
          .map((row, index) => ({ row, index }))
          .filter(({ row }) => row.phase === "baseline_return")
          .map(({ index }) => {
            const next = runs[0].trace
              .slice(index + 1)
              .findIndex((row) => row.changed);
            return next < 0 ? realClockCadences - index - 1 : next;
          }),
      ),
      max_unchanged_run: maxUnchangedRun,
    };
  });
  const recording = await page.evaluate(() => window.__recordingContractState());
  const checks = {
    page_errors_zero: errors.length === 0,
    recording_indicator_source_absent: !fs.readFileSync(pagePath, "utf8")
      .includes("recording-indicator"),
    recording_indicator_dom_zero: recording.indicatorNodes === 0,
    recording_meter_single: recording.levelNodes === 1,
    requested_family_count: families.length === selectedFamilies.length,
    family_sequences_distinct: (
      new Set(sequenceSignatures).size === selectedFamilies.length
    ),
    exact_baseline_return: families.every((family) => family.exact_baseline_return),
    interruption_exact_baseline_return: families.every(
      (family) => family.interruption,
    ),
    two_component_classes: families.every((family) => (
      family.phases.slice(1, 3).every((phase) => phase.trace.components.length >= 2)
    )),
    max_declared_step_two_px: families.every((family) => (
      family.phases.slice(1, 3).every((phase) => phase.trace.max_component_step_px <= 2)
    )),
    real_clock_parallel_contexts: (
      realClockCadences === 0
      || realClockRuns.length === selectedFamilies.length * 2
    ),
    real_clock_120_cadences: (
      realClockCadences === 0
      || realClock.every((family) => family.runs.every(
        (run) => run.trace_count === realClockCadences,
      ))
    ),
    real_clock_two_runs_identical: (
      realClockCadences === 0
      || realClock.every((family) => family.traces_equal)
    ),
    real_clock_first_beat_bounded: (
      realClockCadences === 0
      || realClock.every((family) => family.first_changed_derived_ms <= 960)
    ),
    real_clock_two_component_classes: (
      realClockCadences === 0
      || realClock.every((family) => family.component_classes.length >= 2)
    ),
    real_clock_exact_baseline_return: (
      realClockCadences === 0
      || realClock.every((family) => family.exact_baseline_returns)
    ),
    real_clock_max_unchanged_two_slots: (
      realClockCadences === 0
      || realClock.every((family) => family.max_unchanged_run <= 2)
    ),
    real_clock_no_unregistered_refresh: (
      realClockCadences === 0
      || realClock.every((family) => family.all_refreshes_source_backed)
    ),
  };
  assert(Object.values(checks).every(Boolean), "family choreography checks failed");
  const result = {
    schema: realClockCadences > 0
      ? "companion.family-micro-choreography-full.comp-req-540.v1"
      : "companion.family-micro-choreography-focused.comp-req-540.v1",
    status: "PASS",
    requirements: ["COMP-REQ-540", "COMP-REQ-541"],
    page: {
      path: pageRepoPath,
      canonical_sha256: pageCanonicalSha256,
    },
    viewport: { width: 1280, height: 900, screen: [200, 200] },
    selected_families: selectedFamilies,
    real_clock_cadences: realClockCadences,
    checks,
    errors,
    families,
    real_clock: realClock,
    screenshots: selectedFamilies.flatMap((family) => (
      [0, 2, 3, 4].map((step) => (
        path.relative(repoRoot, path.join(screenshotsDir, `${family}-step-${step}.png`))
          .replaceAll("\\", "/")
      ))
    )),
  };
  const bytes = jsonBytes(result);
  fs.writeFileSync(outputPath, bytes);
  console.log(JSON.stringify({
    status: "PASS",
    result: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
    result_sha256: sha256(bytes),
    page_sha256: pageCanonicalSha256,
    families: families.length,
    screenshots: result.screenshots.length,
  }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
