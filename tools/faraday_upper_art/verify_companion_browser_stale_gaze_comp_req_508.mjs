#!/usr/bin/env node
/* Pixel-source oracle for COMP-REQ-508 gaze replacement. */

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
        modulePath: path.dirname(packagePath).replaceAll("\\", "/"),
        packageSha256: sha256(fs.readFileSync(packagePath)),
        version: JSON.parse(fs.readFileSync(packagePath, "utf8")).version,
      };
    } catch {
      // Try the next locally installed Playwright package.
    }
  }
  throw new Error("Playwright unavailable");
}

async function waitForStage(page) {
  await page.waitForFunction(() => {
    const stage = document.querySelector("#overall-viewport");
    if (!stage || !window.__touchContractState) {
      return false;
    }
    return [...stage.querySelectorAll("img")]
      .filter((image) => !image.hidden && !image.closest("[hidden]"))
      .every((image) => image.complete && image.naturalWidth === 200);
  }, null, { timeout: 8000 });
  await page.waitForTimeout(80);
}

async function moveDrag(page, x, y) {
  const box = await page.locator("#overall-viewport").boundingBox();
  if (!box) {
    throw new Error("overall viewport unavailable");
  }
  await page.mouse.move(box.x + 100, box.y + 100);
  await page.mouse.down();
  await page.waitForTimeout(45);
  await page.mouse.move(box.x + x, box.y + y);
  await page.waitForTimeout(90);
}

async function measure(page, id) {
  return page.evaluate(async (measurementId) => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const state = window.__companionViewportStates.overall;
    const offsetMatrix = new DOMMatrixReadOnly(
      getComputedStyle(gaze).transform === "none"
        ? undefined
        : getComputedStyle(gaze).transform,
    );
    const offsetX = Math.round(offsetMatrix.e || 0);
    const offsetY = Math.round(offsetMatrix.f || 0);
    const load = (source) => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = () => reject(new Error(`image load failed: ${source}`));
      image.src = source;
    });
    const withRevision = (source) => {
      const resolved = new URL(source, location.href);
      resolved.searchParams.set("review", sourceRevision);
      return resolved.href;
    };
    const sourceBase = state.activeFrame?.touch_base
      || state.activeFrame?.src
      || state.activeBaseSrc;
    const centerSource = touchData.overlays[touchData.center_key];
    const currentSource = gaze.getAttribute("src");
    const [baseImage, centerImage, currentImage] = await Promise.all([
      load(withRevision(sourceBase)),
      load(withRevision(centerSource)),
      load(currentSource),
    ]);

    const makeCanvas = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 200;
      canvas.height = 200;
      return canvas;
    };
    const actual = makeCanvas();
    const actualContext = actual.getContext("2d", {
      willReadFrequently: true,
    });
    actualContext.fillStyle = "#fff";
    actualContext.fillRect(0, 0, 200, 200);
    actualContext.drawImage(frame, 0, 0, 200, 200);
    actualContext.drawImage(gaze, offsetX, offsetY, 200, 200);

    const centerMask = makeCanvas();
    const centerMaskContext = centerMask.getContext("2d");
    centerMaskContext.drawImage(
      centerImage,
      offsetX,
      offsetY,
      200,
      200,
    );
    centerMaskContext.globalCompositeOperation = "source-in";
    centerMaskContext.fillStyle = "#000";
    centerMaskContext.fillRect(0, 0, 200, 200);

    const expected = makeCanvas();
    const expectedContext = expected.getContext("2d", {
      willReadFrequently: true,
    });
    expectedContext.fillStyle = "#fff";
    expectedContext.fillRect(0, 0, 200, 200);
    expectedContext.drawImage(baseImage, 0, 0, 200, 200);
    expectedContext.drawImage(centerMask, 0, 0);
    expectedContext.drawImage(
      currentImage,
      offsetX,
      offsetY,
      200,
      200,
    );

    const actualPixels = actualContext.getImageData(0, 0, 200, 200).data;
    const expectedPixels = expectedContext.getImageData(0, 0, 200, 200).data;
    const maskPixels = centerMaskContext.getImageData(
      0,
      0,
      200,
      200,
    ).data;
    let mismatch = 0;
    let stale = 0;
    let staleLeft = 0;
    let staleRight = 0;
    let minX = 200;
    let minY = 200;
    let maxX = -1;
    let maxY = -1;
    for (let pixel = 0; pixel < 40000; pixel += 1) {
      const index = pixel * 4;
      const actualBlack = (
        actualPixels[index] < 128
        && actualPixels[index + 1] < 128
        && actualPixels[index + 2] < 128
      );
      const expectedBlack = (
        expectedPixels[index] < 128
        && expectedPixels[index + 1] < 128
        && expectedPixels[index + 2] < 128
      );
      if (actualBlack !== expectedBlack) {
        mismatch += 1;
      }
      if (
        !actualBlack
        && expectedBlack
        && maskPixels[index + 3] > 0
      ) {
        const x = pixel % 200;
        const y = Math.floor(pixel / 200);
        stale += 1;
        staleLeft += x < 100 ? 1 : 0;
        staleRight += x >= 100 ? 1 : 0;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
    return {
      active_frame: {
        cue: state.activeFrame?.cue || null,
        source_base: sourceBase,
        story: state.storyName,
      },
      dom: {
        active_200x200_surfaces: document.querySelectorAll(
          "#overall-viewport.live-viewport",
        ).length,
        frame_nodes: stage.querySelectorAll(".viewport-frame").length,
        gaze_nodes: stage.querySelectorAll(".viewport-gaze").length,
        visible_frame_nodes: frame.hidden ? 0 : 1,
        visible_gaze_nodes: gaze.hidden ? 0 : 1,
      },
      id: measurementId,
      pixel: {
        binary_mismatch_count: mismatch,
        stale_center_mask_bounds: stale
          ? { max_x: maxX, max_y: maxY, min_x: minX, min_y: minY }
          : null,
        stale_center_mask_left_eye: staleLeft,
        stale_center_mask_right_eye: staleRight,
        stale_center_mask_total: stale,
      },
      sources: {
        current_gaze: currentSource,
        current_gaze_asset: currentSource.split("/").at(-1).split("?")[0],
        frame: frame.getAttribute("src"),
        frame_is_generated_gaze_base: (
          frame.dataset.gazeCleared === "true"
        ),
      },
    };
  }, id);
}

const args = parseArgs(process.argv.slice(2));
const outputPath = path.resolve(repoRoot, args.output);
const outputParent = path.dirname(outputPath);
if (!outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
fs.mkdirSync(outputParent, { recursive: true });
const screenshotPath = path.join(outputParent, "drag-stale-gaze.png");
const expectedPageSha256 = args["expected-page-sha256"].toUpperCase();
const observedPageSha256 = sha256(fs.readFileSync(pagePath));
const playwright = loadPlaywright();
const errors = [];
let browser;
let measurement = null;
try {
  browser = await playwright.chromium.launch({ headless: true });
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "en-US",
    reducedMotion: "reduce",
    viewport: { height: 900, width: 1280 },
  });
  const page = await context.newPage();
  page.on("pageerror", (error) => errors.push(`pageerror:${error.message}`));
  page.on("requestfailed", (request) => (
    errors.push(`requestfailed:${request.url()}`)
  ));
  await page.goto(url, { waitUntil: "load", timeout: 10000 });
  await page.locator("#enter-expression").click();
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
    returnToExpression();
  });
  await waitForStage(page);
  await moveDrag(page, 172, 100);
  await waitForStage(page);
  measurement = await measure(page, "desktop-mouse-drag-right");
  const box = await page.locator("#overall-viewport").boundingBox();
  await page.screenshot({
    animations: "disabled",
    clip: {
      height: 200,
      width: 200,
      x: Math.floor(box.x),
      y: Math.floor(box.y),
    },
    path: screenshotPath,
  });
  await page.mouse.up();
  await context.close();
} finally {
  if (browser) {
    await browser.close();
  }
}

const checks = {
  current_page_identity_exact: observedPageSha256 === expectedPageSha256,
  exactly_one_dom_frame_and_gaze_node: Boolean(
    measurement
    && measurement.dom.frame_nodes === 1
    && measurement.dom.gaze_nodes === 1
    && measurement.dom.visible_frame_nodes === 1
    && measurement.dom.visible_gaze_nodes === 1
  ),
  exactly_one_primary_surface: Boolean(
    measurement?.dom.active_200x200_surfaces === 1
  ),
  no_page_errors: errors.length === 0,
  stale_center_mask_absent_both_eyes: Boolean(
    measurement
    && measurement.pixel.stale_center_mask_total === 0
    && measurement.pixel.stale_center_mask_left_eye === 0
    && measurement.pixel.stale_center_mask_right_eye === 0
    && measurement.pixel.binary_mismatch_count === 0
  ),
};
const passed = Object.values(checks).every(Boolean);
const artifact = {
  checks,
  errors,
  expected_page_sha256: expectedPageSha256,
  measurement,
  observed_page_sha256: observedPageSha256,
  page: {
    repo_path: pageRepoPath,
    url,
  },
  playwright: {
    module_path: playwright.modulePath,
    package_sha256: playwright.packageSha256,
    version: playwright.version,
  },
  requirement: "COMP-REQ-508",
  schema: "companion.browser-stale-gaze-pixel-oracle.v1",
  screenshot: {
    path: path.relative(repoRoot, screenshotPath).replaceAll("\\", "/"),
    sha256: sha256(fs.readFileSync(screenshotPath)),
  },
  side_effect_counters: {
    browser_process: 1,
    hardware: 0,
    microphone_permission_request: 0,
    owner_prompt: 0,
    production_write: 0,
    server_start: 0,
  },
  status: passed ? "PASS" : "FAIL_STALE_GAZE",
};
fs.writeFileSync(outputPath, canonicalBytes(artifact));
console.log(JSON.stringify({
  artifact_sha256: sha256(fs.readFileSync(outputPath)),
  stale_center_mask_total:
    measurement?.pixel.stale_center_mask_total ?? null,
  status: artifact.status,
}));
process.exitCode = passed ? 0 : 1;
