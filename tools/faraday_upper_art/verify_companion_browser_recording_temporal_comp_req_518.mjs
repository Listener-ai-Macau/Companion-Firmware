#!/usr/bin/env node
/* Pixel/temporal oracle for COMP-REQ-518 and COMP-REQ-520. */

import crypto from "node:crypto";
import fs from "node:fs";
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
const url = `http://127.0.0.1:4173/${pageRepoPath}`;

function parseArgs(argv) {
  const values = {};
  for (let index = 0; index < argv.length; index += 2) {
    const name = argv[index];
    const value = argv[index + 1];
    if (!name?.startsWith("--") || value === undefined) {
      throw new Error(`invalid argument near ${name || "<end>"}`);
    }
    values[name.slice(2)] = value;
  }
  for (const required of ["expected-page-sha256", "output"]) {
    if (!values[required]) {
      throw new Error(`missing --${required}`);
    }
  }
  return values;
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function canonical(value) {
  if (Array.isArray(value)) {
    return value.map(canonical);
  }
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
}

function canonicalBytes(value) {
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "ascii");
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
      const module = require(candidate);
      const packagePath = require.resolve(
        candidate === "playwright"
          ? "playwright/package.json"
          : `${candidate}/package.json`,
      );
      return {
        chromium: module.chromium,
        module_path: path.dirname(packagePath).replaceAll("\\", "/"),
        package_sha256: sha256(fs.readFileSync(packagePath)),
        version: JSON.parse(fs.readFileSync(packagePath, "utf8")).version,
      };
    } catch {
      // Continue through locally installed Playwright candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

async function waitForImages(page) {
  await page.waitForFunction(() => {
    const stage = document.querySelector("#overall-viewport");
    return Boolean(
      stage
      && window.__recordingContractState
      && [...stage.querySelectorAll("img")]
        .filter((image) => !image.hidden && !image.closest("[hidden]"))
        .every((image) => image.complete && image.naturalWidth === 200),
    );
  }, null, { timeout: 8000 });
}

async function tap(page, x, y) {
  await page.mouse.move(x, y);
  await page.mouse.down();
  await page.waitForTimeout(28);
  await page.mouse.up();
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const expectedPageSha256 = args["expected-page-sha256"].toUpperCase();
const observedPageSha256 = sha256(fs.readFileSync(pagePath));
const playwright = loadPlaywright();
const errors = [];
let observation = null;
let browser;
try {
  browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "en-US",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { height: 900, width: 1280 },
  });
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.__ownerMediaRequestCount = 0;
    if (
      navigator.mediaDevices
      && typeof navigator.mediaDevices.getUserMedia === "function"
    ) {
      const original = navigator.mediaDevices.getUserMedia.bind(
        navigator.mediaDevices,
      );
      navigator.mediaDevices.getUserMedia = (...values) => {
        window.__ownerMediaRequestCount += 1;
        return original(...values);
      };
    }
  });
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("requestfailed", (request) => (
    errors.push(`requestfailed:${request.url()}`)
  ));
  page.on("response", (response) => {
    if (response.status() >= 400) {
      errors.push(`http:${response.status()}:${response.url()}`);
    }
  });
  await page.goto(url, { waitUntil: "load", timeout: 15000 });
  await page.locator("#enter-expression").click();
  await page.evaluate(() => returnToExpression());
  await waitForImages(page);
  const box = await page.locator("#overall-viewport").boundingBox();
  const x = box.x + 100;
  const y = box.y + 100;
  const pre = await page.evaluate(() => window.__touchContractSnapshot());
  await tap(page, x, y);
  await page.waitForTimeout(120);
  await tap(page, x + 4, y + 3);
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "recording"
  ), null, { timeout: 2000 });

  const faceSamples = [];
  for (let index = 0; index < 18; index += 1) {
    await page.waitForTimeout(100);
    faceSamples.push(await page.evaluate(() => {
      const stage = document.querySelector("#overall-viewport");
      const frame = stage.querySelector(".viewport-frame");
      const gaze = stage.querySelector(".viewport-gaze");
      const recording = window.__recordingContractState();
      return {
        frame: frame.getAttribute("src"),
        gaze: gaze.getAttribute("src"),
        phase: recording.phase,
        sequence: recording.sequence,
      };
    }));
  }
  await page.waitForFunction(() => {
    const trace = window.__recordingContractState().waveTrace;
    return trace.some((row) => row.cycle >= 1);
  }, null, { timeout: 2500 });
  const recording = await page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const indicator = stage.querySelector(".recording-indicator");
    const state = window.__recordingContractState();
    return {
      contract: state,
      indicator: {
        nodes: stage.querySelectorAll(".recording-indicator").length,
        visible: Boolean(
          indicator
          && !indicator.hidden
          && !indicator.closest("[hidden]"),
        ),
      },
      media_requests: window.__ownerMediaRequestCount,
    };
  });
  await tap(page, x, y);
  await page.waitForTimeout(120);
  await tap(page, x + 4, y + 3);
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "expression"
  ), null, { timeout: 2000 });
  await waitForImages(page);
  const returned = await page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const indicator = stage.querySelector(".recording-indicator");
    return {
      indicator_nodes: stage.querySelectorAll(
        ".recording-indicator",
      ).length,
      indicator_visible: Boolean(
        indicator
        && !indicator.hidden
        && !indicator.closest("[hidden]"),
      ),
      recording: window.__recordingContractState(),
      snapshot: window.__touchContractSnapshot(),
    };
  });

  const trace = recording.contract.waveTrace.map((row) => ({
    ...row,
    front_visible: row.front_visible ?? row.ink_pixels > 0,
    lifecycle: row.lifecycle || (
      row.ink_pixels > 0 ? "front" : "absorbed"
    ),
  }));
  const outwardTransitions = [];
  for (let index = 1; index < trace.length; index += 1) {
    const previous = trace[index - 1];
    const current = trace[index];
    if (
      previous.front_visible
      && current.front_visible
      && Number.isFinite(previous.distance_to_listening_point)
      && Number.isFinite(current.distance_to_listening_point)
      && current.distance_to_listening_point
        >= previous.distance_to_listening_point
    ) {
      outwardTransitions.push({
        current: {
          cycle: current.cycle,
          distance: current.distance_to_listening_point,
          step: current.step,
        },
        previous: {
          cycle: previous.cycle,
          distance: previous.distance_to_listening_point,
          step: previous.step,
        },
      });
    }
  }
  const cycles = [...new Set(trace.map((row) => row.cycle))]
    .sort((left, right) => left - right)
    .map((cycle) => {
      const rows = trace.filter((row) => row.cycle === cycle);
      const visible = rows.filter((row) => row.front_visible);
      return {
        absorbed_rows: rows.filter(
          (row) => row.lifecycle === "absorbed" && !row.front_visible,
        ).length,
        cycle,
        distances: visible.map(
          (row) => row.distance_to_listening_point,
        ),
        strictly_inward: visible.every((row, index) => (
          index === 0
          || row.distance_to_listening_point
            < visible[index - 1].distance_to_listening_point
        )),
        visible_front_rows: visible.length,
      };
    });
  const phaseTrace = returned.recording.phaseTrace
    .filter((row) => row.sequence === recording.contract.sequence)
    .map((row) => row.phase);
  observation = {
    cycles,
    face_samples: faceSamples,
    indicator: {
      outside_recording_visible: returned.indicator_visible,
      recording_nodes: recording.indicator.nodes,
      recording_visible: recording.indicator.visible,
    },
    media_requests: recording.media_requests,
    outward_transitions: outwardTransitions,
    phase_trace: phaseTrace,
    recording: recording.contract,
    restore: {
      exact: (
        returned.snapshot.canvasInk === pre.canvasInk
        && returned.snapshot.canvasSignature === pre.canvasSignature
        && returned.snapshot.frame === pre.frame
        && returned.snapshot.gaze === pre.gaze
        && returned.snapshot.gazeTransform === pre.gazeTransform
      ),
      post: returned.snapshot,
      pre,
    },
    unique_recording_face_sources: [
      ...new Set(faceSamples.map((row) => row.frame)),
    ],
    unique_recording_gaze_sources: [
      ...new Set(faceSamples.map((row) => row.gaze)),
    ],
  };
  await context.close();
} finally {
  if (browser) {
    await browser.close();
  }
}

const checks = {
  current_page_identity_exact: observedPageSha256 === expectedPageSha256,
  every_cycle_has_absorption: Boolean(
    observation
    && observation.cycles.filter((cycle) => cycle.absorbed_rows >= 1).length >= 2
    && observation.cycles
      .filter((cycle) => cycle.absorbed_rows >= 1)
      .every((cycle) => cycle.absorbed_rows === 1),
  ),
  every_visible_front_strictly_inward: Boolean(
    observation
    && observation.cycles.every((cycle) => (
      cycle.visible_front_rows >= 2 && cycle.strictly_inward
    )),
  ),
  exact_pre_recording_restore: Boolean(observation?.restore.exact),
  no_microphone_request: observation?.media_requests === 0,
  no_outward_transition_including_wrap:
    observation?.outward_transitions.length === 0,
  one_indicator_only_during_recording: Boolean(
    observation
    && observation.indicator.recording_nodes === 1
    && observation.indicator.recording_visible
    && !observation.indicator.outside_recording_visible
  ),
  one_stable_listening_face_and_gaze: Boolean(
    observation
    && observation.unique_recording_face_sources.length === 1
    && observation.unique_recording_gaze_sources.length === 1
  ),
  stable_listening_phase_contract: Boolean(
    observation
    && JSON.stringify(observation.phase_trace) === JSON.stringify([
      "expression",
      "listening",
      "listening_hold",
      "expression",
    ])
  ),
  zero_page_errors: errors.length === 0,
};
const passed = Object.values(checks).every(Boolean);
const artifact = {
  checks,
  errors,
  expected_page_sha256: expectedPageSha256,
  observation,
  observed_page_sha256: observedPageSha256,
  page: {
    repo_path: pageRepoPath,
    url,
  },
  playwright: {
    module_path: playwright.module_path,
    package_sha256: playwright.package_sha256,
    version: playwright.version,
  },
  requirements: ["COMP-REQ-518", "COMP-REQ-520"],
  schema: "companion.browser-recording-temporal-pixel-oracle.v1",
  side_effect_counters: {
    browser_process: 1,
    hardware: 0,
    microphone_permission_request: observation?.media_requests ?? null,
    owner_prompt: 0,
    production_write: 0,
    server_start: 0,
  },
  status: passed ? "PASS" : "FAIL_RECORDING_TEMPORAL_VISUAL",
};
fs.writeFileSync(outputPath, canonicalBytes(artifact));
console.log(JSON.stringify({
  artifact_sha256: sha256(fs.readFileSync(outputPath)),
  failed_checks: Object.entries(checks)
    .filter(([, value]) => !value)
    .map(([name]) => name),
  status: artifact.status,
}));
process.exitCode = passed ? 0 : 1;
