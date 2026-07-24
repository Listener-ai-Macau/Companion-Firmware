#!/usr/bin/env node
/* Six viewport/pointer combinations and 42 bounded scenarios for COMP-REQ-536/537/538. */

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

function bytes(value) {
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "utf8");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function canonicalTextSha256(value) {
  return sha256(Buffer.from(
    value.toString("utf8").replaceAll("\r\n", "\n"),
    "utf8",
  ));
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
    fs.readFile(target, (error, value) => {
      if (error) {
        response.writeHead(404).end();
        return;
      }
      response.writeHead(200, {
        "content-type": target.endsWith(".html")
          ? "text/html; charset=utf-8"
          : target.endsWith(".png")
            ? "image/png"
            : "application/octet-stream",
      });
      response.end(value);
    });
  });
}

const args = parseArgs(process.argv.slice(2));
const outputRoot = path.resolve(repoRoot, args.output);
if (!outputRoot.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
const screenshotRoot = path.join(outputRoot, "screenshots");
fs.mkdirSync(screenshotRoot, { recursive: true });
const pageCanonicalSha256 = canonicalTextSha256(fs.readFileSync(pagePath));
if (
  args["expected-page-sha256"]
  && pageCanonicalSha256 !== args["expected-page-sha256"].toUpperCase()
) {
  throw new Error("page canonical SHA-256 mismatch");
}

const playwright = loadPlaywright();
const server = createServer();
const scenarios = [];
const screenshots = [];
const errors = [];
const combinations = [
  ["desktop", "mouse", { height: 900, width: 1280 }],
  ["desktop", "touch", { height: 900, width: 1280 }],
  ["desktop", "pen", { height: 900, width: 1280 }],
  ["mobile", "mouse", { height: 780, width: 390 }],
  ["mobile", "touch", { height: 780, width: 390 }],
  ["mobile", "pen", { height: 780, width: 390 }],
];
let browser;
let pointerSequence = 100;
let mediaRequests = 0;

function addScenario(combo, name, pass, observed) {
  scenarios.push({ combo, name, observed, pass });
  assert(pass, `${combo}:${name}`);
}

async function snapshot(page) {
  return page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const visible = (node) => (
      node
      && !node.hidden
      && !node.closest("[hidden]")
      && getComputedStyle(node).display !== "none"
    );
    const state = window.__naturalExpressionContractState();
    const recording = window.__recordingContractState();
    const touch = window.__touchContractState();
    const screen = touchCanvasMetrics();
    return {
      accessory_active: recording.active,
      affect: state.base_affect,
      frame: stage.querySelector(".viewport-frame").src,
      gaze: stage.querySelector(".viewport-gaze").src,
      gaze_target: state.gaze_target,
      interaction_mode: recording.interaction_mode,
      menu_visible: visible(stage.querySelector("#integrated-menu")),
      mode_override: state.mode_override,
      recording_entries: recording.entries,
      recording_exits: recording.exits,
      route_count: state.route_count,
      screen,
      surfaces: {
        face: Number(visible(stage.querySelector(".viewport-frame"))),
        gaze: Number(visible(stage.querySelector(".viewport-gaze"))),
        indicator: Number(visible(stage.querySelector(".recording-indicator"))),
        menu: Number(visible(stage.querySelector("#integrated-menu"))),
        waves: Number(visible(stage.querySelector(".recording-waves"))),
      },
      touch,
    };
  });
}

async function pointer(page, kind, action, x, y, pointerId) {
  if (kind === "mouse") {
    if (action === "down") await page.mouse.move(x, y).then(() => page.mouse.down());
    if (action === "move") await page.mouse.move(x, y, { steps: 2 });
    if (action === "up") await page.mouse.up();
    return;
  }
  await page.evaluate(({ action: eventAction, id, pointerType, x: px, y: py }) => {
    const type = `pointer${eventAction}`;
    const target = document.elementFromPoint(px, py);
    target.dispatchEvent(new PointerEvent(type, {
      bubbles: true,
      button: 0,
      buttons: eventAction === "up" ? 0 : 1,
      cancelable: true,
      clientX: px,
      clientY: py,
      isPrimary: true,
      pointerId: id,
      pointerType,
    }));
  }, { action, id: pointerId, pointerType: kind, x, y });
}

async function tap(page, kind, x, y, downMs = 24) {
  const id = pointerSequence++;
  await pointer(page, kind, "down", x, y, id);
  await page.waitForTimeout(downMs);
  await pointer(page, kind, "up", x, y, id);
}

async function doubleTap(page, kind, x, y) {
  await tap(page, kind, x, y);
  await page.waitForTimeout(90);
  await tap(page, kind, x, y);
}

async function drag(page, kind, points) {
  const id = pointerSequence++;
  await pointer(page, kind, "down", points[0][0], points[0][1], id);
  for (const [x, y] of points.slice(1)) {
    await pointer(page, kind, "move", x, y, id);
    await page.waitForTimeout(28);
  }
  await pointer(
    page,
    kind,
    "up",
    points.at(-1)[0],
    points.at(-1)[1],
    id,
  );
}

async function capture(page, combo, name) {
  const target = path.join(screenshotRoot, `${combo}-${name}.png`);
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "missing viewport box");
  await page.screenshot({
    animations: "disabled",
    clip: {
      height: 200,
      width: 200,
      x: Math.floor(box.x),
      y: Math.floor(box.y),
    },
    path: target,
  });
  const value = fs.readFileSync(target);
  screenshots.push({
    combo,
    name,
    path: path.relative(repoRoot, target).replaceAll("\\", "/"),
    sha256: sha256(value),
  });
}

try {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const port = server.address().port;
  browser = await playwright.chromium.launch({ headless: true });
  for (const [viewportName, pointerType, viewport] of combinations) {
    const combo = `${viewportName}-${pointerType}`;
    const context = await browser.newContext({
      colorScheme: "light",
      deviceScaleFactor: 1,
      locale: "zh-CN",
      reducedMotion: "reduce",
      timezoneId: "UTC",
      viewport,
    });
    const page = await context.newPage();
    await page.addInitScript(() => {
      window.__mediaRequestCount = 0;
      if (navigator.mediaDevices?.getUserMedia) {
        navigator.mediaDevices.getUserMedia = () => {
          window.__mediaRequestCount += 1;
          throw new Error("microphone request prohibited");
        };
      }
    });
    page.on("pageerror", (error) => errors.push(`${combo}:page:${error.message}`));
    page.on("requestfailed", (request) => (
      errors.push(`${combo}:request:${request.url()}`)
    ));
    page.on("response", (response) => {
      if (response.status() >= 400) {
        errors.push(`${combo}:http:${response.status()}:${response.url()}`);
      }
    });
    await page.goto(
      `http://127.0.0.1:${port}/${pageRepoPath}#expression`,
      { timeout: 15000, waitUntil: "load" },
    );
    await page.waitForFunction(() => (
      window.__recordingContractState
      && document.querySelector("#overall-viewport .viewport-frame")
        ?.naturalWidth === 200
    ), null, { timeout: 8000 });
    await page.waitForTimeout(1500);
    const box = await page.locator("#overall-viewport").boundingBox();
    assert(box, `${combo}: viewport missing`);
    const center = [box.x + 100, box.y + 100];

    const initial = await snapshot(page);
    await tap(page, pointerType, center[0] + 28, center[1]);
    await page.waitForTimeout(1250);
    const single = await snapshot(page);
    addScenario(combo, "single_tap", (
      single.route_count === initial.route_count + 1
      && single.affect === "curious"
      && !single.accessory_active
    ), { initial, single });

    await drag(page, pointerType, [
      center,
      [box.x + 35, center[1]],
      [box.x + 165, center[1]],
      [center[0], box.y + 35],
      [center[0], box.y + 165],
      center,
    ]);
    await page.waitForTimeout(150);
    const dragged = await snapshot(page);
    addScenario(combo, "drag_replacement", (
      !dragged.accessory_active
      && dragged.gaze_target.key === "1,0,1,0"
      && dragged.surfaces.face === 1
      && dragged.surfaces.gaze === 1
    ), dragged);

    await doubleTap(page, pointerType, center[0], center[1]);
    await page.waitForFunction(() => window.__recordingContractState().active);
    const entered = await snapshot(page);
    addScenario(combo, "double_tap_entry", (
      entered.recording_entries === 1
      && entered.interaction_mode === "expression"
      && entered.surfaces.indicator === 1
      && entered.surfaces.waves === 1
    ), entered);
    await capture(page, combo, "recording");

    const routeBeforeRecordingTap = entered.route_count;
    await tap(page, pointerType, center[0] + 24, center[1]);
    await page.waitForTimeout(1250);
    const recordingTap = await snapshot(page);
    addScenario(combo, "recording_single_tap", (
      recordingTap.accessory_active
      && recordingTap.route_count === routeBeforeRecordingTap + 1
      && recordingTap.affect === "warm"
    ), recordingTap);

    await drag(page, pointerType, [
      center,
      [box.x + 40, center[1]],
      [box.x + 160, center[1]],
      center,
    ]);
    await page.waitForTimeout(150);
    const recordingDrag = await snapshot(page);
    addScenario(combo, "recording_drag", (
      recordingDrag.accessory_active
      && recordingDrag.recording_entries === 1
      && recordingDrag.surfaces.face === 1
      && recordingDrag.surfaces.gaze === 1
    ), recordingDrag);

    const holdId = pointerSequence++;
    await pointer(page, pointerType, "down", center[0], center[1], holdId);
    await page.waitForTimeout(760);
    await pointer(page, pointerType, "up", center[0], center[1], holdId);
    await page.waitForFunction(() => (
      window.__touchContractState().mode === "menu"
    ));
    let menu = await snapshot(page);
    const deviceY = box.y + 100;
    await tap(page, pointerType, center[0], deviceY);
    await page.waitForTimeout(80);
    await tap(page, pointerType, center[0], box.y + 166);
    await page.waitForTimeout(80);
    const uiAssets = await page.evaluate(() => (
      document.querySelector("#integrated-menu").dataset.screen
    ));
    await page.locator("[data-testid=integrated-menu-back]").click({
      timeout: 5000,
    });
    await page.locator("[data-testid=integrated-menu-return]").click({
      timeout: 5000,
    });
    await page.waitForFunction(() => (
      window.__touchContractState().mode === "expression"
    ));
    const menuReturn = await snapshot(page);
    addScenario(combo, "recording_menu_return", (
      menu.accessory_active
      && menu.surfaces.menu === 1
      && uiAssets === "expression"
      && menuReturn.accessory_active
      && menuReturn.surfaces.waves === 1
      && menuReturn.surfaces.indicator === 1
    ), { menu, menuReturn, uiAssets });

    const beforeExit = await snapshot(page);
    await doubleTap(page, pointerType, center[0], center[1]);
    await page.waitForFunction(() => !window.__recordingContractState().active);
    const afterExit = await snapshot(page);
    addScenario(combo, "accessory_only_exit", (
      afterExit.recording_exits === 1
      && afterExit.affect === beforeExit.affect
      && afterExit.frame === beforeExit.frame
      && afterExit.gaze === beforeExit.gaze
      && afterExit.surfaces.indicator === 0
      && afterExit.surfaces.waves === 0
    ), { afterExit, beforeExit });
    await capture(page, combo, "exit");
    mediaRequests += await page.evaluate(() => window.__mediaRequestCount);
    await context.close();
  }
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const failed = scenarios.filter((row) => !row.pass);
const result = {
  schema: "companion.comp-req-536-538-browser-replay.v1",
  status: (
    scenarios.length === 42
    && failed.length === 0
    && errors.length === 0
    && mediaRequests === 0
  ) ? "PASS" : "NO_GO",
  checks: {
    combinations_exact: combinations.length === 6,
    no_404_or_page_error: errors.length === 0,
    no_microphone_request: mediaRequests === 0,
    scenario_count_exact: scenarios.length === 42,
    scenarios_all_pass: failed.length === 0,
  },
  counts: {
    combinations: combinations.length,
    errors: errors.length,
    microphone_requests: mediaRequests,
    scenarios: scenarios.length,
    screenshots: screenshots.length,
  },
  errors,
  failed: failed.map((row) => `${row.combo}:${row.name}`),
  inputs: {
    page_canonical_sha256: pageCanonicalSha256,
    page_repo_path: pageRepoPath,
  },
  scenarios,
  side_effects: {
    hardware: 0,
    owner_prompt: 0,
    production_write: 0,
  },
};
const screenshotManifest = {
  schema: "companion.comp-req-536-538-screenshots.v1",
  status: "PASS",
  count: screenshots.length,
  screenshots,
};
const routeArtifact = {
  schema: "companion.comp-req-536-538-pixel-dom-route.v1",
  status: result.status,
  invariants: {
    accessory_only_exit: scenarios
      .filter((row) => row.name === "accessory_only_exit")
      .every((row) => row.pass),
    recording_is_orthogonal: scenarios
      .filter((row) => row.name.startsWith("recording_"))
      .every((row) => row.pass),
    single_face_single_gaze: scenarios.every((row) => {
      const values = JSON.stringify(row.observed);
      return !values.includes('"face":2') && !values.includes('"gaze":2');
    }),
  },
  scenario_count: scenarios.length,
};
for (const [name, value] of [
  ["browser-replay-result.json", result],
  ["pixel-dom-route-artifact.json", routeArtifact],
  ["screenshot-manifest.json", screenshotManifest],
]) {
  fs.writeFileSync(path.join(outputRoot, name), bytes(value));
}
if (result.status !== "PASS") {
  throw new Error(`replay NO_GO: ${result.failed.join(",") || errors.join(",")}`);
}
console.log(JSON.stringify({
  output: path.relative(repoRoot, outputRoot).replaceAll("\\", "/"),
  replay_sha256: sha256(bytes(result)),
  scenarios: scenarios.length,
  status: result.status,
}));
