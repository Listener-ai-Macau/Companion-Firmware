#!/usr/bin/env node
/* Focused browser oracle for the COMP-REQ-521 natural tap bridge. */

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
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonical(value[key])]),
    );
  }
  return value;
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
      // Continue through the installed candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

async function dispatch(page, kind, point, pointerId) {
  await page.evaluate(({ kind, point, pointerId }) => {
    const stage = document.querySelector("#overall-viewport");
    const rect = stage.getBoundingClientRect();
    stage.dispatchEvent(new PointerEvent(kind, {
      bubbles: true,
      buttons: kind === "pointerup" ? 0 : 1,
      cancelable: true,
      clientX: rect.left + point.x,
      clientY: rect.top + point.y,
      isPrimary: true,
      pointerId,
      pointerType: "mouse",
    }));
  }, { kind, point, pointerId });
}

async function tap(page, point, pointerId, downMs = 24) {
  await dispatch(page, "pointerdown", point, pointerId);
  await page.waitForTimeout(downMs);
  await dispatch(page, "pointerup", point, pointerId);
}

async function doubleTap(page, point, firstPointerId) {
  await tap(page, point, firstPointerId);
  await page.waitForTimeout(95);
  await tap(page, point, firstPointerId + 1);
}

function check(errors, name, condition, observed) {
  if (!condition) errors.push({ check: name, observed });
}

const args = parseArgs(process.argv.slice(2));
const expectedPageSha256 = args["expected-page-sha256"].toUpperCase();
const outputPath = path.resolve(repoRoot, args.output);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
const observedPageSha256 = sha256(fs.readFileSync(pagePath));
const playwright = loadPlaywright();
const errors = [];
const observations = {};
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
    if (navigator.mediaDevices?.getUserMedia) {
      const original = navigator.mediaDevices.getUserMedia.bind(
        navigator.mediaDevices,
      );
      navigator.mediaDevices.getUserMedia = (...values) => {
        window.__ownerMediaRequestCount += 1;
        return original(...values);
      };
    }
  });
  const pageErrors = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto(url, { waitUntil: "load", timeout: 15000 });
  await page.locator("#enter-expression").click();
  await page.waitForFunction(() => Boolean(
    window.__naturalExpressionContractState
    && window.__recordingContractState
    && document.body.classList.contains("expression-open"),
  ));
  await page.evaluate(() => {
    for (const [name, state] of Object.entries(
      window.__companionViewportStates || {},
    )) {
      if (name !== "overall") {
        clearTimeout(state.timer);
        state.timer = 0;
        state.touching = true;
        state.request += 1;
        state.gazeRequest += 1;
      }
    }
  });
  await page.waitForTimeout(120);

  const firstPoint = { x: 156, y: 72 };
  await tap(page, firstPoint, 100);
  await page.waitForTimeout(80);
  observations.firstRelease = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    touch: window.__touchContractState(),
  }));
  check(
    errors,
    "first_release_orients_without_commit",
    observations.firstRelease.touch.pendingTap
      && observations.firstRelease.natural.base_affect === "calm"
      && observations.firstRelease.natural.reaction_phase
        === "gaze_highlight_lead"
      && observations.firstRelease.natural.route_count === 0,
    observations.firstRelease,
  );

  await page.waitForTimeout(610);
  observations.singleCommitted = await page.evaluate(() => (
    window.__naturalExpressionContractState()
  ));
  check(
    errors,
    "single_commits_only_after_650ms",
    observations.singleCommitted.route_count === 1
      && observations.singleCommitted.bridge?.from === "calm"
      && observations.singleCommitted.bridge?.to === "curious"
      && observations.singleCommitted.bridge?.changedFrames === 2,
    observations.singleCommitted,
  );

  await page.waitForTimeout(540);
  observations.firstSettled = await page.evaluate(() => (
    window.__naturalExpressionContractState()
  ));
  const firstKinds = observations.firstSettled.trace.map((row) => row.kind);
  check(
    errors,
    "ordered_natural_bridge",
    observations.firstSettled.base_affect === "curious"
      && observations.firstSettled.bridge === null
      && firstKinds.indexOf("source_hold")
        < firstKinds.indexOf("gaze_highlight_lead")
      && firstKinds.indexOf("gaze_highlight_lead")
        < firstKinds.indexOf("brow_reply")
      && firstKinds.indexOf("brow_reply")
        < firstKinds.indexOf("lower_face_reply")
      && firstKinds.indexOf("lower_face_reply")
        < firstKinds.indexOf("target_hold")
      && observations.firstSettled.trace
        .filter((row) => row.route_id === "natural-1" && row.changed_frame)
        .at(-1)?.changed_frame <= 3,
    observations.firstSettled,
  );

  for (const [point, expected, pointerId] of [
    [{ x: 50, y: 80 }, "warm", 110],
    [{ x: 145, y: 130 }, "playful", 120],
    [{ x: 100, y: 45 }, "playful", 130],
  ]) {
    await tap(page, point, pointerId);
    await page.waitForTimeout(1220);
    const state = await page.evaluate(() => (
      window.__naturalExpressionContractState()
    ));
    observations[`tapTo${expected}${pointerId}`] = state;
    check(
      errors,
      `contextual_or_same_state_${pointerId}`,
      state.base_affect === expected
        && state.bridge === null
        && state.coalesced_pending === null,
      state,
    );
  }
  const lastSelection = observations.tapToplayful130.trace
    .filter((row) => row.kind === "contextual_edge_selected").at(-1);
  check(
    errors,
    "unsupported_tap_is_same_state_ack",
    lastSelection?.classification === "same_state_ack"
      && lastSelection?.from === "playful"
      && lastSelection?.to === "playful",
    lastSelection,
  );

  const beforeCancel = observations.tapToplayful130.route_count;
  await tap(page, { x: 35, y: 45 }, 140);
  await page.waitForTimeout(100);
  await page.evaluate(() => window.dispatchEvent(new Event("blur")));
  await page.waitForTimeout(700);
  observations.cancel = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    touch: window.__touchContractState(),
  }));
  check(
    errors,
    "cancel_prevents_delayed_commit",
    observations.cancel.natural.route_count === beforeCancel
      && observations.cancel.natural.pending_orient === null
      && !observations.cancel.touch.pendingTap,
    observations.cancel,
  );

  const preRecording = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    snapshot: window.__touchContractSnapshot(),
  }));
  await doubleTap(page, { x: 148, y: 70 }, 150);
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "recording"
  ));
  const processingWhileRecording = await page.evaluate(() => (
    window.__dispatchPostRecordingProcessing()
  ));
  await page.waitForTimeout(980);
  observations.recording = await page.evaluate(() => ({
    mediaRequests: window.__ownerMediaRequestCount,
    natural: window.__naturalExpressionContractState(),
    recording: window.__recordingContractState(),
    snapshot: window.__touchContractSnapshot(),
  }));
  const activePhases = observations.recording.recording.phaseTrace
    .filter((row) => row.sequence === observations.recording.recording.sequence);
  check(
    errors,
    "recording_is_stable_listening_only",
    !processingWhileRecording
      && observations.recording.recording.active
      && observations.recording.recording.phase === "listening_hold"
      && activePhases.map((row) => row.phase).join(">")
        === "expression>listening>listening_hold"
      && new Set(activePhases.slice(1).map((row) => row.story)).size === 1
      && !activePhases.some((row) => (
        row.phase.includes("thoughtful") || row.story === "thoughtful_presence"
      ))
      && observations.recording.natural.mode_override === "recording"
      && observations.recording.mediaRequests === 0,
    observations.recording,
  );

  await tap(page, { x: 148, y: 70 }, 160);
  await page.waitForTimeout(700);
  const recordingAfterSingle = await page.evaluate(() => (
    window.__recordingContractState()
  ));
  check(
    errors,
    "recording_single_does_not_exit",
    recordingAfterSingle.active && recordingAfterSingle.exits === 0,
    recordingAfterSingle,
  );
  await doubleTap(page, { x: 148, y: 70 }, 170);
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "expression"
  ));
  await page.waitForTimeout(80);
  observations.restored = await page.evaluate(() => ({
    natural: window.__naturalExpressionContractState(),
    recording: window.__recordingContractState(),
    snapshot: window.__touchContractSnapshot(),
  }));
  check(
    errors,
    "recording_exit_exact_restore",
    observations.restored.recording.exits === 1
      && observations.restored.natural.base_affect
        === preRecording.natural.base_affect
      && observations.restored.natural.reaction_phase
        === preRecording.natural.reaction_phase
      && observations.restored.snapshot.canvasSignature
        === preRecording.snapshot.canvasSignature
      && observations.restored.snapshot.frame === preRecording.snapshot.frame
      && observations.restored.snapshot.gaze === preRecording.snapshot.gaze,
    { preRecording, restored: observations.restored },
  );

  observations.contract = await page.evaluate(() => ({
    contract: window.__naturalExpressionContractState().contract,
    edges: ["calm", "curious", "warm", "playful", "puzzled", "alert"]
      .map((source) => window.__naturalSelectTapEdge(source, 2)),
    processingAfterRecording: window.__dispatchPostRecordingProcessing(),
  }));
  check(
    errors,
    "bounded_contract_and_explicit_processing",
    observations.contract.contract.tapDiscriminatorMs === 650
      && observations.contract.contract.bridgeWindowMs === 480
      && observations.contract.contract.maxPostSourceChangedFrames === 3
      && observations.contract.contract.maxCoalescedPending === 1
      && observations.contract.processingAfterRecording
      && observations.contract.edges
        .filter((edge) => ["puzzled", "alert"].includes(edge.from))
        .every((edge) => edge.kind === "same_state_ack"),
    observations.contract,
  );
  check(errors, "no_page_errors", pageErrors.length === 0, pageErrors);
  await context.close();
} catch (error) {
  errors.push({ check: "runtime", observed: error.stack || error.message });
} finally {
  if (browser) await browser.close();
}

check(
  errors,
  "page_identity",
  observedPageSha256 === expectedPageSha256,
  { expectedPageSha256, observedPageSha256 },
);
const result = {
  contract: "COMP-REQ-521",
  errors,
  observations,
  page: {
    path: pageRepoPath,
    expected_sha256: expectedPageSha256,
    observed_sha256: observedPageSha256,
    url,
  },
  playwright: {
    module_path: playwright.modulePath,
    package_sha256: playwright.packageSha256,
    version: playwright.version,
  },
  side_effect_counters: {
    browser_pages: 1,
    hardware: 0,
    microphone_requests: observations.recording?.mediaRequests ?? null,
    owner_prompt: 0,
    server_start: 0,
  },
  status: errors.length ? "NO_GO" : "PASS",
};
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
const bytes = Buffer.from(
  `${JSON.stringify(canonical(result), null, 2)}\n`,
  "ascii",
);
fs.writeFileSync(outputPath, bytes);
console.log(JSON.stringify({
  artifact_sha256: sha256(bytes),
  failed_checks: errors.map((row) => row.check),
  status: result.status,
}));
if (errors.length) process.exitCode = 1;
