#!/usr/bin/env node
/* Six viewport/pointer combinations and 42 scenarios for COMP-REQ-540. */

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRepoPath = [
  "docs/art/iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
].join("/");
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith("--") || argv[index + 1] === undefined) {
      throw new Error(`invalid argument near ${argv[index] || "<end>"}`);
    }
    result[argv[index].slice(2)] = argv[index + 1];
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
const pageCanonicalSha256 = sha256(Buffer.from(
  fs.readFileSync(pagePath).toString("utf8").replaceAll("\r\n", "\n"),
));
if (
  args["expected-page-sha256"]
  && pageCanonicalSha256 !== args["expected-page-sha256"].toUpperCase()
) {
  throw new Error("page canonical SHA-256 mismatch");
}

const allCombinations = [
  ["desktop", "mouse", { height: 900, width: 1280 }],
  ["desktop", "touch", { height: 900, width: 1280 }],
  ["desktop", "pen", { height: 900, width: 1280 }],
  ["mobile", "mouse", { height: 780, width: 390 }],
  ["mobile", "touch", { height: 780, width: 390 }],
  ["mobile", "pen", { height: 780, width: 390 }],
];
const combinations = args.only
  ? allCombinations.filter(([viewportName, pointerType]) => (
      `${viewportName}-${pointerType}` === args.only
    ))
  : allCombinations;
if (!combinations.length) throw new Error(`unknown --only combination: ${args.only}`);
const server = createServer();
const playwright = loadPlaywright();
const scenarios = [];
const screenshots = [];
const errors = [];
let browser;
let pointerId = 100;
let microphoneRequests = 0;

function addScenario(combo, name, pass, observed) {
  scenarios.push({ combo, name, observed, pass });
}

async function pointer(page, pointerType, action, x, y, id) {
  if (pointerType === "mouse") {
    if (action === "down") {
      await page.mouse.move(x, y);
      await page.mouse.down();
    } else if (action === "move") {
      await page.mouse.move(x, y, { steps: 2 });
    } else if (action === "up") {
      await page.mouse.up();
    } else if (action === "cancel") {
      await page.evaluate(({ xValue, yValue }) => {
        document.elementFromPoint(xValue, yValue).dispatchEvent(new PointerEvent(
          "pointercancel",
          {
            bubbles: true,
            button: 0,
            buttons: 0,
            cancelable: true,
            clientX: xValue,
            clientY: yValue,
            isPrimary: true,
            pointerId: 1,
            pointerType: "mouse",
          },
        ));
      }, { xValue: x, yValue: y });
      await page.mouse.up();
    }
    return;
  }
  await page.evaluate(({ actionValue, idValue, pointerTypeValue, xValue, yValue }) => {
    const target = document.elementFromPoint(xValue, yValue);
    target.dispatchEvent(new PointerEvent(`pointer${actionValue}`, {
      bubbles: true,
      button: 0,
      buttons: actionValue === "up" || actionValue === "cancel" ? 0 : 1,
      cancelable: true,
      clientX: xValue,
      clientY: yValue,
      isPrimary: true,
      pointerId: idValue,
      pointerType: pointerTypeValue,
    }));
  }, {
    actionValue: action,
    idValue: id,
    pointerTypeValue: pointerType,
    xValue: x,
    yValue: y,
  });
}

async function tap(page, pointerType, x, y) {
  const id = pointerId++;
  await pointer(page, pointerType, "down", x, y, id);
  await page.waitForTimeout(24);
  await pointer(page, pointerType, "up", x, y, id);
}

async function doubleTap(page, pointerType, x, y) {
  await tap(page, pointerType, x, y);
  await page.waitForTimeout(90);
  await tap(page, pointerType, x, y);
}

async function drag(page, pointerType, points) {
  const id = pointerId++;
  await pointer(page, pointerType, "down", points[0][0], points[0][1], id);
  for (const point of points.slice(1)) {
    await pointer(page, pointerType, "move", point[0], point[1], id);
    await page.waitForTimeout(24);
  }
  await pointer(page, pointerType, "up", points.at(-1)[0], points.at(-1)[1], id);
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
    const natural = window.__naturalExpressionContractState();
    const recording = window.__recordingContractState();
    const touch = window.__touchContractState();
    return {
      accessory_active: recording.active,
      affect: natural.base_affect,
      frame: stage.querySelector(".viewport-frame").src,
      gaze: stage.querySelector(".viewport-gaze").src,
      gaze_target: natural.gaze_target,
      interaction_mode: recording.interaction_mode,
      menu_visible: visible(stage.querySelector("#integrated-menu")),
      progress_nodes: stage.querySelectorAll(
        ".hold-progress,.hold-track,.hold-fill,[data-hold-progress]",
      ).length,
      recording_entries: recording.entries,
      recording_exits: recording.exits,
      route_count: natural.route_count,
      surfaces: {
        face: Number(visible(stage.querySelector(".viewport-frame"))),
        gaze: Number(visible(stage.querySelector(".viewport-gaze"))),
        indicator: Number(visible(stage.querySelector(".recording-indicator"))),
        levels: Number(visible(stage.querySelector(".recording-levels"))),
        menu: Number(visible(stage.querySelector("#integrated-menu"))),
      },
      touch,
    };
  });
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
  screenshots.push({
    combo,
    name,
    path: path.relative(repoRoot, target).replaceAll("\\", "/"),
    sha256: sha256(fs.readFileSync(target)),
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
      errors.push(`${combo}:request:${request.failure()?.errorText}`)
    ));
    page.on("response", (response) => {
      if (response.status() >= 400) {
        errors.push(`${combo}:http:${response.status()}`);
      }
    });
    await page.goto(
      `http://127.0.0.1:${port}/${pageRepoPath}#expression`,
      { timeout: 15000, waitUntil: "load" },
    );
    await page.waitForFunction(() => (
      typeof window.__recordingContractState === "function"
      && document.querySelector("#overall-viewport .viewport-frame")
        ?.naturalWidth === 200
    ), null, { timeout: 10000 });
    await page.waitForTimeout(1800);
    await page.evaluate(() => window.__interruptEpaperIdleGlint("replay"));
    const box = await page.locator("#overall-viewport").boundingBox();
    assert(box, `${combo}: viewport missing`);
    const center = [box.x + 100, box.y + 100];

    const initial = await snapshot(page);
    await tap(page, pointerType, center[0] + 28, center[1]);
    await page.waitForTimeout(720);
    const single = await snapshot(page);
    addScenario(combo, "single_tap_no_progress", (
      single.route_count === initial.route_count + 1
      && single.progress_nodes === 0
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
    await page.waitForTimeout(120);
    const dragged = await snapshot(page);
    addScenario(combo, "drag_replacement_no_progress", (
      dragged.gaze_target.key === "1,0,1,0"
      && dragged.surfaces.face === 1
      && dragged.surfaces.gaze === 1
      && dragged.progress_nodes === 0
    ), dragged);

    const cancelId = pointerId++;
    await pointer(page, pointerType, "down", center[0], center[1], cancelId);
    await page.waitForTimeout(100);
    await pointer(page, pointerType, "cancel", center[0], center[1], cancelId);
    const canceled = await snapshot(page);
    addScenario(combo, "cancel_no_progress", (
      canceled.progress_nodes === 0
      && canceled.interaction_mode === "expression"
      && canceled.touch.activePointer === null
    ), canceled);

    await doubleTap(page, pointerType, center[0], center[1]);
    await page.waitForFunction(() => window.__recordingContractState().active);
    const entered = await snapshot(page);
    addScenario(combo, "double_tap_meter_entry", (
      entered.recording_entries === 1
      && entered.surfaces.indicator === 0
      && entered.surfaces.levels === 1
      && entered.progress_nodes === 0
    ), entered);
    await capture(page, combo, "recording");

    const routeBefore = entered.route_count;
    await tap(page, pointerType, center[0] + 24, center[1]);
    await page.waitForTimeout(720);
    await drag(page, pointerType, [
      center,
      [box.x + 40, center[1]],
      [box.x + 160, center[1]],
      center,
    ]);
    await page.waitForTimeout(120);
    const recordingInteraction = await snapshot(page);
    addScenario(combo, "recording_underlying_interaction", (
      recordingInteraction.accessory_active
      && recordingInteraction.route_count === routeBefore + 1
      && recordingInteraction.surfaces.face === 1
      && recordingInteraction.surfaces.gaze === 1
      && recordingInteraction.surfaces.levels === 1
    ), recordingInteraction);

    const holdId = pointerId++;
    await pointer(page, pointerType, "down", center[0], center[1], holdId);
    await page.waitForTimeout(1500);
    const midHold = await snapshot(page);
    await page.waitForFunction(
      () => window.__touchContractState().mode === "menu",
      null,
      { timeout: 2000 },
    );
    await pointer(page, pointerType, "up", center[0], center[1], holdId);
    const menu = await snapshot(page);
    await tap(page, pointerType, center[0], box.y + 100);
    await page.waitForTimeout(80);
    await tap(page, pointerType, center[0], box.y + 166);
    await page.waitForTimeout(80);
    const uiAssets = await page.evaluate(() => (
      document.querySelector("#integrated-menu").dataset.screen
    ));
    await page.locator("[data-testid=integrated-menu-back]").click();
    await page.locator("[data-testid=integrated-menu-return]").click();
    await page.waitForFunction(
      () => window.__touchContractState().mode === "expression",
    );
    const menuReturn = await snapshot(page);
    addScenario(combo, "hold_menu_ui_assets_return", (
      midHold.progress_nodes === 0
      && menu.progress_nodes === 0
      && menu.surfaces.menu === 1
      && uiAssets === "expression"
      && menuReturn.accessory_active
      && menuReturn.surfaces.levels === 1
    ), { menu, menuReturn, midHold, uiAssets });

    const beforeExit = await snapshot(page);
    await doubleTap(page, pointerType, center[0], center[1]);
    const exited = await page.waitForFunction(
      () => !window.__recordingContractState().active,
      null,
      { timeout: 1500 },
    ).then(() => true).catch(() => false);
    const afterExit = await snapshot(page);
    const exitTrace = await page.evaluate(() => window.__touchInteractionTrace.slice(-12));
    addScenario(combo, "accessory_only_exit", (
      exited
      &&
      afterExit.recording_exits === 1
      && afterExit.affect === beforeExit.affect
      && afterExit.frame === beforeExit.frame
      && afterExit.gaze === beforeExit.gaze
      && afterExit.surfaces.indicator === 0
      && afterExit.surfaces.levels === 0
      && afterExit.progress_nodes === 0
    ), { afterExit, beforeExit, exited, exitTrace });
    await capture(page, combo, "exit");
    microphoneRequests += await page.evaluate(() => window.__mediaRequestCount);
    await context.close();
  }
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const failed = scenarios.filter((row) => !row.pass);
const status = (
  scenarios.length === 42
  && failed.length === 0
  && errors.length === 0
  && microphoneRequests === 0
) ? "PASS" : "NO_GO";
const result = {
  schema: "companion.comp-req-540-browser-replay.v1",
  requirements: ["COMP-REQ-539", "COMP-REQ-540", "COMP-REQ-541"],
  status,
  checks: {
    combinations_exact: combinations.length === 6,
    no_404_or_page_error: errors.length === 0,
    no_microphone_request: microphoneRequests === 0,
    scenario_count_exact: scenarios.length === 42,
    scenarios_all_pass: failed.length === 0,
  },
  counts: {
    combinations: combinations.length,
    errors: errors.length,
    microphone_requests: microphoneRequests,
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
  schema: "companion.comp-req-540-screenshots.v1",
  status,
  count: screenshots.length,
  screenshots,
};
const routeArtifact = {
  schema: "companion.comp-req-540-pixel-dom-route.v1",
  status,
  scenario_count: scenarios.length,
  invariants: {
    accessory_only_exit: scenarios
      .filter((row) => row.name === "accessory_only_exit")
      .every((row) => row.pass),
    progress_nodes_zero: scenarios.every(
      (row) => !JSON.stringify(row.observed).includes('"progress_nodes":1'),
    ),
    recording_indicator_zero: scenarios
      .filter((row) => row.name === "double_tap_meter_entry")
      .every((row) => row.pass),
    recording_is_orthogonal: scenarios
      .filter((row) => row.name === "recording_underlying_interaction")
      .every((row) => row.pass),
    single_face_single_gaze: scenarios.every((row) => (
      !JSON.stringify(row.observed).includes('"face":2')
      && !JSON.stringify(row.observed).includes('"gaze":2')
    )),
  },
};
for (const [name, value] of [
  ["browser-replay-result.json", result],
  ["pixel-dom-route-artifact.json", routeArtifact],
  ["screenshot-manifest.json", screenshotManifest],
]) {
  fs.writeFileSync(path.join(outputRoot, name), bytes(value));
}
console.log(JSON.stringify({
  failed: result.failed,
  result_sha256: sha256(fs.readFileSync(
    path.join(outputRoot, "browser-replay-result.json"),
  )),
  scenarios: scenarios.length,
  status,
}));
if (status !== "PASS") process.exitCode = 1;
