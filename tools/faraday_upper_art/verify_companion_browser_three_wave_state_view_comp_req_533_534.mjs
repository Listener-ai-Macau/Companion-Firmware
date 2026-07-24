#!/usr/bin/env node
/* Focused pixel, timing, and state-source oracle for COMP-REQ-533/534. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");

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
  for (const required of ["url", "expected-page-sha256", "output"]) {
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
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "utf8");
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
        modulePath: path.dirname(packagePath).replaceAll("\\", "/"),
        packageSha256: sha256(fs.readFileSync(packagePath)),
        version: JSON.parse(fs.readFileSync(packagePath, "utf8")).version,
      };
    } catch {
      // Continue through the bounded local candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

async function fetchBytes(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`page fetch failed: ${response.status}`);
  }
  return Buffer.from(await response.arrayBuffer());
}

function checksFrom(observation, expectedPageSha256, observedPageSha256) {
  const checks = {
    page_identity_exact: observedPageSha256 === expectedPageSha256,
    exactly_three_pixel_arcs_every_step: (
      observation.steps.length > 0
      && observation.steps.every((step) => step.components.length === 3)
    ),
    every_arc_convex_toward_listening_point: (
      observation.steps.length > 0
      && observation.steps.every((step) => (
        step.components.every((component) => component.convex_toward_listening)
      ))
    ),
    every_arc_inside_200x200: observation.steps.every((step) => (
      step.components.every((component) => (
        component.bounds.x_min >= 0
        && component.bounds.y_min >= 0
        && component.bounds.x_max < 200
        && component.bounds.y_max < 200
      ))
    )),
    three_runtime_arc_identities: observation.arcIdentities.length === 3,
    identity_motion_inward_or_absorb_spawn: observation.identityTransitions.every(
      (row) => (
        row.kind === "inward"
          ? row.current_distance < row.previous_distance
          : row.kind === "spawn_after_absorption"
            ? row.previous_lifecycle === "absorbed"
            : false
      ),
    ),
    physical_step_contract_480_ms: observation.contractStepMs === 480,
    no_css_interpolation: observation.canvasTransitionDuration === "0s",
    no_intermediate_visible_frame: observation.preBoundarySignatures.length === 1,
    one_change_at_physical_boundary: observation.postBoundarySignatures.length === 1,
    observed_boundary_not_early: observation.firstObservedChangeMs >= 430,
    observed_boundary_bounded: observation.firstObservedChangeMs <= 650,
    state_view_exists_outside_screen: (
      observation.stateView.exists
      && observation.stateView.outside_screen
      && observation.stateView.visible
    ),
    state_view_uses_single_runtime_source: (
      observation.stateView.source_identity === "naturalState"
      && observation.stateView.affect === observation.naturalState.base_affect
      && observation.stateView.phase === observation.naturalState.reaction_phase
      && observation.stateView.mode === observation.naturalState.mode_override
    ),
    displayed_edge_is_legal: observation.stateView.displayed_edge_legal === true,
    legal_edges_complete: observation.edgeChecks.legal.every((row) => row.allowed),
    forged_edges_rejected: observation.edgeChecks.forged.every((row) => !row.allowed),
    optical_samples_complete: observation.optical.samples.length >= 7,
    optical_centroid_centered: observation.optical.samples.every((sample) => (
      Math.abs(sample.centroid.x - observation.optical.anchor.x)
        <= observation.optical.centroid_tolerance.x
      && Math.abs(sample.centroid.y - observation.optical.anchor.y)
        <= observation.optical.centroid_tolerance.y
    )),
    optical_envelope_centered: observation.optical.samples.every((sample) => (
      Math.abs(sample.envelope_center.x - observation.optical.anchor.x)
        <= observation.optical.envelope_tolerance.x
    )),
    optical_no_clipping: observation.optical.samples.every((sample) => (
      sample.bounds.x_min > 0
      && sample.bounds.y_min > 0
      && sample.bounds.x_max < 199
      && sample.bounds.y_max < 199
    )),
    no_microphone_request: observation.mediaRequestCount === 0,
    no_http_or_page_errors: observation.errors.length === 0,
  };
  return checks;
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
fs.mkdirSync(path.dirname(outputPath), { recursive: true });

const expectedPageSha256 = args["expected-page-sha256"].toUpperCase();
const pageBytes = await fetchBytes(args.url);
const observedPageSha256 = sha256(pageBytes);
const playwright = loadPlaywright();
const errors = [];
let browser;
let observation;

try {
  browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "zh-CN",
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
  await page.goto(`${args.url}#expression`, {
    timeout: 15000,
    waitUntil: "load",
  });
  await page.waitForFunction(() => Boolean(
    window.__recordingContractState
    && window.__recordingFreezeWaveStep,
  ));
  await page.waitForFunction(() => {
    const image = document.querySelector(
      "#overall-viewport .viewport-frame:not([hidden])",
    );
    return image?.complete && image.naturalWidth === 200;
  });
  const stageBox = await page.locator("#overall-viewport").boundingBox();
  if (!stageBox) throw new Error("overall viewport has no bounding box");
  const tapX = stageBox.x + 100;
  const tapY = stageBox.y + 100;
  await page.mouse.click(tapX, tapY, { delay: 24 });
  await page.waitForTimeout(48);
  await page.mouse.click(tapX, tapY, { delay: 24 });
  await page.waitForFunction(() => (
    window.__recordingContractState?.().active === true
  ));

  observation = await page.evaluate(async () => {
    function componentsForCanvas(canvas, listeningPoint) {
      const context = canvas.getContext("2d", { willReadFrequently: true });
      const pixels = context.getImageData(0, 0, 200, 200).data;
      const ink = new Uint8Array(40000);
      for (let index = 0; index < 40000; index += 1) {
        const offset = index * 4;
        ink[index] = (
          pixels[offset + 3] > 0 && pixels[offset] < 128
        ) ? 1 : 0;
      }
      const seen = new Uint8Array(40000);
      const result = [];
      for (let seed = 0; seed < 40000; seed += 1) {
        if (!ink[seed] || seen[seed]) continue;
        const queue = [seed];
        seen[seed] = 1;
        const points = [];
        while (queue.length) {
          const current = queue.pop();
          const x = current % 200;
          const y = Math.floor(current / 200);
          points.push({ x, y });
          for (let dy = -1; dy <= 1; dy += 1) {
            for (let dx = -1; dx <= 1; dx += 1) {
              if (dx === 0 && dy === 0) continue;
              const nx = x + dx;
              const ny = y + dy;
              if (nx < 0 || nx >= 200 || ny < 0 || ny >= 200) continue;
              const next = ny * 200 + nx;
              if (ink[next] && !seen[next]) {
                seen[next] = 1;
                queue.push(next);
              }
            }
          }
        }
        if (points.length < 3) continue;
        const xs = points.map((point) => point.x);
        const ys = points.map((point) => point.y);
        const yMin = Math.min(...ys);
        const yMax = Math.max(...ys);
        const yMid = (yMin + yMax) / 2;
        const centerBand = points.filter((point) => Math.abs(point.y - yMid) <= 2);
        const edgeBand = points.filter((point) => (
          point.y <= yMin + 2 || point.y >= yMax - 2
        ));
        const centerX = centerBand.reduce((sum, point) => sum + point.x, 0)
          / Math.max(1, centerBand.length);
        const edgeX = edgeBand.reduce((sum, point) => sum + point.x, 0)
          / Math.max(1, edgeBand.length);
        result.push({
          bounds: {
            x_max: Math.max(...xs),
            x_min: Math.min(...xs),
            y_max: yMax,
            y_min: yMin,
          },
          centroid: {
            x: Number((
              xs.reduce((sum, value) => sum + value, 0) / points.length
            ).toFixed(3)),
            y: Number((
              ys.reduce((sum, value) => sum + value, 0) / points.length
            ).toFixed(3)),
          },
          closest_distance: Math.min(...xs) - listeningPoint.x,
          convex_toward_listening: centerX < edgeX - 0.75,
          edge_x: Number(edgeX.toFixed(3)),
          center_x: Number(centerX.toFixed(3)),
          ink_pixels: points.length,
        });
      }
      return result.sort((left, right) => (
        right.closest_distance - left.closest_distance
      ));
    }

    async function opticalSample(sample, contract) {
      const image = new Image();
      image.src = sample.src;
      await image.decode();
      const canvas = document.createElement("canvas");
      canvas.width = 200;
      canvas.height = 200;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.drawImage(image, 0, 0);
      const pixels = context.getImageData(0, 0, 200, 200).data;
      const points = [];
      for (let y = contract.face_roi.y_min; y <= contract.face_roi.y_max; y += 1) {
        for (
          let x = contract.face_roi.x_min;
          x <= contract.face_roi.x_max;
          x += 1
        ) {
          const offset = (y * 200 + x) * 4;
          if (pixels[offset + 3] > 0 && pixels[offset] < 128) {
            points.push({ x, y });
          }
        }
      }
      if (!points.length) {
        return { ...sample, missing_ink: true };
      }
      const xs = points.map((point) => point.x);
      const ys = points.map((point) => point.y);
      const bounds = {
        x_max: Math.max(...xs),
        x_min: Math.min(...xs),
        y_max: Math.max(...ys),
        y_min: Math.min(...ys),
      };
      return {
        ...sample,
        bounds,
        centroid: {
          x: Number((
            xs.reduce((sum, value) => sum + value, 0) / points.length
          ).toFixed(3)),
          y: Number((
            ys.reduce((sum, value) => sum + value, 0) / points.length
          ).toFixed(3)),
        },
        envelope_center: {
          x: (bounds.x_min + bounds.x_max) / 2,
          y: (bounds.y_min + bounds.y_max) / 2,
        },
        ink_pixels: points.length,
      };
    }

    const recording = window.__recordingContractState();
    const listeningPoint = recording.waveContract.listening_point;
    const stepCount = (
      recording.waveContract.state_count
      || recording.waveContract.radii?.length
      || 0
    );
    const steps = [];
    for (let step = 0; step < stepCount; step += 1) {
      const runtime = window.__recordingFreezeWaveStep(step);
      const canvas = document.querySelector(".recording-waves");
      steps.push({
        runtime,
        components: componentsForCanvas(canvas, listeningPoint),
        step,
      });
    }

    const stateView = window.__expressionStateViewSnapshot
      ? window.__expressionStateViewSnapshot()
      : {
          affect: null,
          displayed_edge_legal: false,
          exists: false,
          mode: null,
          outside_screen: false,
          phase: null,
          source_identity: null,
          visible: false,
        };
    const naturalState = window.__naturalExpressionContractState();
    const edgeChecks = window.__expressionStateEdgeAudit
      ? window.__expressionStateEdgeAudit()
      : { forged: [], legal: [] };
    const opticalContract = window.__expressionOpticalContractState
      ? window.__expressionOpticalContractState()
      : {
          anchor: { x: 100, y: 135 },
          centroid_tolerance: { x: 0, y: 0 },
          envelope_tolerance: { x: 0, y: 0 },
          face_roi: { x_max: 175, x_min: 25, y_max: 175, y_min: 75 },
          samples: [],
        };
    const opticalSamples = [];
    for (const sample of opticalContract.samples || []) {
      opticalSamples.push(await opticalSample(sample, opticalContract));
    }

    window.__recordingFreezeWaveStep(0);
    const waveCanvas = document.querySelector(".recording-waves");
    const signature = () => {
      const pixels = waveCanvas.getContext(
        "2d",
        { willReadFrequently: true },
      ).getImageData(0, 0, 200, 200).data;
      let value = 2166136261;
      for (let index = 0; index < pixels.length; index += 4) {
        const bit = pixels[index + 3] > 0 && pixels[index] < 128 ? 1 : 0;
        value = Math.imul(value ^ bit, 16777619) >>> 0;
      }
      return value.toString(16).padStart(8, "0");
    };
    const initialSignature = signature();
    window.__recordingResumeWaves?.();
    const startedAt = performance.now();
    const samples = [];
    let firstObservedChangeMs = null;
    for (let index = 0; index < 8; index += 1) {
      await new Promise((resolve) => setTimeout(resolve, 80));
      const elapsed = Math.round(performance.now() - startedAt);
      const value = signature();
      samples.push({ elapsed_ms: elapsed, signature: value });
      if (value !== initialSignature && firstObservedChangeMs === null) {
        firstObservedChangeMs = elapsed;
      }
    }
    const preBoundary = samples.filter((sample) => sample.elapsed_ms < 430);
    const postBoundary = samples.filter((sample) => sample.elapsed_ms >= 430);
    const preBoundarySignatures = [
      ...new Set(preBoundary.map((sample) => sample.signature)),
    ];
    const postBoundarySignatures = [
      ...new Set(
        postBoundary
          .filter((sample) => sample.signature !== initialSignature)
          .map((sample) => sample.signature),
      ),
    ];

    const identities = new Set();
    const identityTransitions = [];
    for (let index = 1; index < steps.length; index += 1) {
      const previous = steps[index - 1].runtime?.arcs || [];
      const current = steps[index].runtime?.arcs || [];
      for (const arc of current) {
        identities.add(arc.arc_id);
        const prior = previous.find((candidate) => (
          candidate.arc_id === arc.arc_id
        ));
        if (!prior) continue;
        identityTransitions.push({
          arc_id: arc.arc_id,
          current_distance: arc.distance_to_listening_point,
          current_lifecycle: arc.lifecycle,
          kind: arc.lifecycle === "spawn"
            ? "spawn_after_absorption"
            : "inward",
          previous_distance: prior.distance_to_listening_point,
          previous_lifecycle: prior.lifecycle,
        });
      }
    }

    return {
      arcIdentities: [...identities].sort(),
      canvasTransitionDuration: getComputedStyle(waveCanvas).transitionDuration,
      contractStepMs: recording.waveContract.step_ms,
      edgeChecks,
      errors: [],
      firstObservedChangeMs: firstObservedChangeMs ?? -1,
      identityTransitions,
      mediaRequestCount: window.__ownerMediaRequestCount,
      naturalState,
      optical: {
        ...opticalContract,
        samples: opticalSamples,
      },
      postBoundarySignatures,
      preBoundarySignatures,
      stateView,
      steps,
      timingSamples: samples,
    };
  });
  observation.errors = errors;
  await context.close();
} finally {
  if (browser) await browser.close();
}

const checks = checksFrom(
  observation,
  expectedPageSha256,
  observedPageSha256,
);
const failedChecks = Object.entries(checks)
  .filter(([, passed]) => !passed)
  .map(([name]) => name);
const artifact = {
  checks,
  failed_checks: failedChecks,
  observed: observation,
  page: {
    expected_sha256: expectedPageSha256,
    observed_sha256: observedPageSha256,
    url: args.url,
  },
  playwright: {
    module_path: playwright.modulePath,
    package_sha256: playwright.packageSha256,
    version: playwright.version,
  },
  runtime_effects: {
    browser_process_started: 1,
    hardware_access: 0,
    microphone_requests: observation.mediaRequestCount,
    owner_prompt_opened: 0,
  },
  schema: "companion.browser_three_wave_state_view_oracle.v1",
  status: failedChecks.length === 0 ? "PASS" : "NO_GO",
};
fs.writeFileSync(outputPath, canonicalBytes(artifact));
console.log(JSON.stringify({
  failed_checks: failedChecks,
  output: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
  output_sha256: sha256(fs.readFileSync(outputPath)),
  status: artifact.status,
}, null, 2));
process.exitCode = failedChecks.length === 0 ? 0 : 1;
