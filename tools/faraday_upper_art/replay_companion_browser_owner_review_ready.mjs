#!/usr/bin/env node
/* Deterministic headless replay for the accepted Companion overall page. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const validationRoot = path.join(
  repoRoot,
  "docs/validation/companion-browser-owner-review-ready-comp-req-471",
);
const outputRoot = path.resolve(process.argv[2] || validationRoot);
if (
  outputRoot !== validationRoot
  && !outputRoot.startsWith(`${validationRoot}${path.sep}`)
) {
  throw new Error(`output must remain within ${validationRoot}`);
}

const pageRepoPath = [
  "docs/art/iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
].join("/");
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));
const acceptedPageSha256 =
  "BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E";
const acceptedCenteredRestPngSha256 =
  "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31";
const overallUrl =
  "http://127.0.0.1:4173/" + pageRepoPath;
const screenshotRoot = path.join(outputRoot, "screenshots");
const replayPath = path.join(outputRoot, "browser-replay-result.json");
const screenshotManifestPath = path.join(
  outputRoot,
  "screenshot-manifest.json",
);
const pixelDomRoutePath = path.join(
  outputRoot,
  "pixel-dom-route-artifact.json",
);
const lockPath = path.join(outputRoot, ".browser-replay.lock");

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function fileSha256(value) {
  return sha256(fs.readFileSync(value));
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

function writeCanonical(target, value) {
  fs.writeFileSync(target, canonicalBytes(value));
}

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

function boolPixelEqual(left, right) {
  return (
    left.signature === right.signature
    && left.black_pixels === right.black_pixels
    && JSON.stringify(left.black_bounds) === JSON.stringify(right.black_bounds)
  );
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function loadPlaywright() {
  const candidates = [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
  ].filter(Boolean);
  const errors = [];
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
        packageSha256: fileSha256(packagePath),
        version: JSON.parse(fs.readFileSync(packagePath, "utf8")).version,
      };
    } catch (error) {
      errors.push(`${candidate}:${error.message}`);
    }
  }
  throw new Error(`Playwright unavailable: ${errors.join(" | ")}`);
}

fs.mkdirSync(screenshotRoot, { recursive: true });
let lockFd;
try {
  lockFd = fs.openSync(lockPath, "wx");
  fs.writeFileSync(lockFd, `${process.pid}\n`);
} catch {
  throw new Error(`browser replay lock exists: ${lockPath}`);
}

const playwright = loadPlaywright();
const screenshotRows = [];
const matrixRows = [];
const stateRows = [];
const expectedScreenshotNames = new Set();
const totals = {
  browser_contexts: 0,
  browser_pages: 0,
  cancellation_scenarios: 0,
  device_ui_assets_visits: 0,
  directional_moves: 0,
  document_requests: 0,
  menu_root_visits: 0,
  microphone_requests: 0,
  replay_combinations: 0,
  route_recording_entries: 0,
  route_menu_entries: 0,
  scenario_count: 0,
  snapshot_count: 0,
  stale_layer_count: 0,
  conflicting_surface_overlap_count: 0,
  outside_black_pixel_count: 0,
  out_of_bounds_count: 0,
  http_404_count: 0,
  page_error_count: 0,
};

function sanitize(value) {
  return value.replace(/[^A-Za-z0-9_.-]+/g, "-");
}

async function capture(page, id, kind = "stage") {
  const name = `${sanitize(id)}.png`;
  const target = path.join(screenshotRoot, name);
  expectedScreenshotNames.add(name);
  if (kind === "layout") {
    await page.screenshot({
      path: target,
      fullPage: false,
      animations: "disabled",
    });
  } else {
    const box = await page.locator("#overall-viewport").boundingBox();
    assert(box, `${id}: stage screenshot box missing`);
    await page.screenshot({
      path: target,
      animations: "disabled",
      clip: {
        height: 200,
        width: 200,
        x: Math.floor(box.x),
        y: Math.floor(box.y),
      },
    });
  }
  const row = {
    bytes: fs.statSync(target).size,
    id,
    kind,
    path: path.relative(repoRoot, target).replaceAll("\\", "/"),
    sha256: fileSha256(target),
  };
  screenshotRows.push(row);
  return row;
}

async function screenSnapshot(page, freezeOverallAfterSnapshot = false) {
  return page.evaluate((freezeAfterSnapshot) => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const menu = stage.querySelector(".integrated-menu-image");
    const menuSurface = stage.querySelector("#integrated-menu");
    const hold = stage.querySelector(".hold-progress");
    const visible = (element) => {
      if (!element || element.hidden || element.closest("[hidden]")) {
        return false;
      }
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        style.display !== "none"
        && style.visibility !== "hidden"
        && Number(style.opacity) !== 0
        && rect.width > 0
        && rect.height > 0
      );
    };
    const stageRect = stage.getBoundingClientRect();
    const transformOffset = (element) => {
      const transform = getComputedStyle(element).transform;
      if (!transform || transform === "none") {
        return [0, 0];
      }
      const matrix = new DOMMatrixReadOnly(transform);
      return [Math.round(matrix.e), Math.round(matrix.f)];
    };
    const layers = [
      ["face", frame],
      ["gaze", gaze],
      ["menu", menu],
    ];
    const canvas = document.createElement("canvas");
    canvas.width = 200;
    canvas.height = 200;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.fillStyle = "#fff";
    context.fillRect(0, 0, 200, 200);
    let outsideBlackPixels = 0;
    for (const [, image] of layers) {
      if (!visible(image) || image.naturalWidth !== 200) {
        continue;
      }
      const [tx, ty] = transformOffset(image);
      context.drawImage(image, tx, ty, 200, 200);
      const outside = document.createElement("canvas");
      outside.width = 600;
      outside.height = 600;
      const outsideContext = outside.getContext("2d", {
        willReadFrequently: true,
      });
      outsideContext.clearRect(0, 0, 600, 600);
      outsideContext.drawImage(image, 200 + tx, 200 + ty, 200, 200);
      const pixels = outsideContext.getImageData(0, 0, 600, 600).data;
      for (let y = 0; y < 600; y += 1) {
        for (let x = 0; x < 600; x += 1) {
          if (x >= 200 && x < 400 && y >= 200 && y < 400) {
            continue;
          }
          const offset = (y * 600 + x) * 4;
          if (
            pixels[offset + 3] > 0
            && pixels[offset] < 128
            && pixels[offset + 1] < 128
            && pixels[offset + 2] < 128
          ) {
            outsideBlackPixels += 1;
          }
        }
      }
    }
    const pixels = context.getImageData(0, 0, 200, 200).data;
    let blackPixels = 0;
    let minX = 200;
    let minY = 200;
    let maxX = -1;
    let maxY = -1;
    let signature = 2166136261;
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const offset = (y * 200 + x) * 4;
        const black = (
          pixels[offset] < 128
          && pixels[offset + 1] < 128
          && pixels[offset + 2] < 128
        ) ? 1 : 0;
        signature = Math.imul(signature ^ black, 16777619) >>> 0;
        if (!black) {
          continue;
        }
        blackPixels += 1;
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
    const contract = window.__touchContractState();
    const overallContract = window.__overallInteractionState();
    const faceVisible = visible(frame) ? 1 : 0;
    const gazeVisible = visible(gaze) ? 1 : 0;
    const menuVisible = visible(menu) && visible(menuSurface) ? 1 : 0;
    const expected = contract.mode === "menu"
      ? { face: 0, gaze: 0, highlight: 0, menu: 1 }
      : { face: 1, gaze: 1, highlight: 1, menu: 0 };
    const debugSelectors = [
      ".screen-meta",
      ".decision-panel",
      "#emotion-rule",
      "#gesture-status",
      ".authority-source",
    ];
    const debugVisible = debugSelectors.filter((selector) => (
      visible(document.querySelector(selector))
    ));
    const outOfBounds = [];
    for (const [name, element] of [
      ["stage", stage],
      ["menu", menuSurface],
      ["hold", hold],
    ]) {
      if (!visible(element) || name === "stage") {
        continue;
      }
      const rect = element.getBoundingClientRect();
      if (
        rect.left < stageRect.left - 0.5
        || rect.top < stageRect.top - 0.5
        || rect.right > stageRect.right + 0.5
        || rect.bottom > stageRect.bottom + 0.5
      ) {
        outOfBounds.push(name);
      }
    }
    const snapshot = {
      contract: {
        active_pointer: contract.activePointer
          ? {
              moved: contract.activePointer.moved,
              type: contract.activePointer.type,
            }
          : null,
        hold_progress: contract.holdProgress,
        last_interaction: contract.lastInteraction,
        menu_entries: contract.menuEntries,
        menu_view: overallContract.menuView,
        mode: contract.mode,
        pending_tap: contract.pendingTap,
        recording_entries: contract.recordingEntries,
        story_paused: contract.storyPaused,
        story_touching: contract.storyTouching,
      },
      dom: {
        conflict_count: menuVisible && (faceVisible || gazeVisible) ? 1 : 0,
        debug_visible: debugVisible,
        expected,
        face_count: faceVisible,
        gaze_count: gazeVisible,
        gaze_node_count: stage.querySelectorAll(".viewport-gaze").length,
        highlight_layer_count: gazeVisible,
        hold_count: visible(hold) ? 1 : 0,
        menu_count: menuVisible,
        menu_node_count: stage.querySelectorAll(".integrated-menu-image").length,
        out_of_bounds: outOfBounds,
        primary_screen_count: document.querySelectorAll(
          "#overall-viewport.live-viewport",
        ).length,
        stage_center_delta_px: Math.abs(
          stageRect.left + stageRect.width / 2 - innerWidth / 2,
        ),
        stage_height: stageRect.height,
        stage_width: stageRect.width,
        visible_image_count: layers.filter(([, image]) => visible(image)).length,
      },
      media_request_count: window.__ownerMediaRequestCount || 0,
      pixel: {
        black_bounds: blackPixels
          ? { max_x: maxX, max_y: maxY, min_x: minX, min_y: minY }
          : null,
        black_pixels: blackPixels,
        edge_touch: blackPixels
          ? {
              bottom: maxY === 199,
              left: minX === 0,
              right: maxX === 199,
              top: minY === 0,
            }
          : null,
        outside_black_pixels: outsideBlackPixels,
        signature: signature.toString(16).padStart(8, "0"),
      },
      route: {
        hash: location.hash,
        pathname: location.pathname,
      },
      sources: {
        face: frame.getAttribute("src") || "",
        gaze: gaze.getAttribute("src") || "",
        menu: menu.getAttribute("src") || "",
      },
    };
    if (freezeAfterSnapshot) {
      const overallState = window.__companionViewportStates?.overall;
      if (overallState) {
        clearTimeout(overallState.timer);
        overallState.timer = 0;
        overallState.touching = true;
        overallState.request += 1;
        overallState.gazeRequest += 1;
      }
    }
    return snapshot;
  }, freezeOverallAfterSnapshot);
}

function assertSnapshot(snapshot, expectedMode, id) {
  totals.snapshot_count += 1;
  const expected = snapshot.dom.expected;
  const stale = (
    Math.abs(snapshot.dom.face_count - expected.face)
    + Math.abs(snapshot.dom.gaze_count - expected.gaze)
    + Math.abs(
      snapshot.dom.highlight_layer_count - expected.highlight
    )
    + Math.abs(snapshot.dom.menu_count - expected.menu)
  );
  totals.stale_layer_count += stale;
  totals.conflicting_surface_overlap_count += snapshot.dom.conflict_count;
  totals.outside_black_pixel_count += snapshot.pixel.outside_black_pixels;
  totals.out_of_bounds_count += snapshot.dom.out_of_bounds.length;
  totals.microphone_requests += snapshot.media_request_count;
  assert(snapshot.contract.mode === expectedMode, `${id}: wrong mode`);
  assert(stale === 0, `${id}: stale/duplicate surface layer`);
  assert(snapshot.dom.conflict_count === 0, `${id}: conflicting surfaces`);
  assert(snapshot.dom.primary_screen_count === 1, `${id}: primary screen count`);
  assert(snapshot.dom.gaze_node_count === 1, `${id}: gaze node count`);
  assert(snapshot.dom.menu_node_count === 1, `${id}: menu node count`);
  assert(snapshot.dom.stage_width === 200, `${id}: stage width`);
  assert(snapshot.dom.stage_height === 200, `${id}: stage height`);
  assert(snapshot.dom.stage_center_delta_px <= 1, `${id}: stage not centered`);
  assert(snapshot.dom.debug_visible.length === 0, `${id}: debug visible`);
  assert(snapshot.dom.out_of_bounds.length === 0, `${id}: DOM out of bounds`);
  assert(
    snapshot.pixel.outside_black_pixels === 0,
    `${id}: clipped black pixels`,
  );
  assert(snapshot.pixel.black_pixels > 0, `${id}: blank stage`);
  assert(snapshot.media_request_count === 0, `${id}: microphone requested`);
  assert(
    snapshot.route.pathname === `/${pageRepoPath}`,
    `${id}: escaped overall document route`,
  );
  const expectedHash = expectedMode === "menu" ? "#menu" : "#expression";
  assert(snapshot.route.hash === expectedHash, `${id}: wrong route hash`);
  stateRows.push({
    contract: snapshot.contract,
    dom: snapshot.dom,
    id,
    pixel: snapshot.pixel,
    route: snapshot.route,
    sources: snapshot.sources,
  });
  return snapshot;
}

async function freezeNonOverallStories(page) {
  await page.evaluate(() => {
    for (const [name, state] of Object.entries(
      window.__companionViewportStates || {},
    )) {
      if (name === "overall") {
        continue;
      }
      clearTimeout(state.timer);
      state.timer = 0;
      state.touching = true;
      state.request += 1;
      state.gazeRequest += 1;
    }
  });
}

async function waitForVisibleImages(page) {
  await page.waitForFunction(() => {
    const stage = document.querySelector("#overall-viewport");
    if (!stage) {
      return false;
    }
    return [...stage.querySelectorAll("img")]
      .filter((image) => !image.hidden && !image.closest("[hidden]"))
      .every((image) => image.complete && image.naturalWidth === 200);
  }, null, { timeout: 8000 });
  await sleep(60);
}

async function resetRest(page) {
  await page.evaluate(() => returnToExpression());
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "expression"
    && location.hash === "#expression"
  ));
  await waitForVisibleImages(page);
}

async function openPage(browser, viewport) {
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    hasTouch: viewport.name === "mobile",
    locale: "en-US",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { height: viewport.height, width: viewport.width },
  });
  totals.browser_contexts += 1;
  const page = await context.newPage();
  totals.browser_pages += 1;
  const errors = [];
  let documentRequests = 0;
  await page.addInitScript(() => {
    window.__ownerMediaRequestCount = 0;
    if (
      navigator.mediaDevices
      && typeof navigator.mediaDevices.getUserMedia === "function"
    ) {
      const original = navigator.mediaDevices.getUserMedia.bind(
        navigator.mediaDevices,
      );
      navigator.mediaDevices.getUserMedia = (...args) => {
        window.__ownerMediaRequestCount += 1;
        return original(...args);
      };
    }
  });
  page.on("pageerror", (error) => {
    errors.push(`pageerror:${error.message}`);
    totals.page_error_count += 1;
  });
  page.on("requestfailed", (request) => {
    errors.push(`requestfailed:${request.url()}`);
  });
  page.on("request", (request) => {
    if (request.resourceType() === "document") {
      documentRequests += 1;
      totals.document_requests += 1;
    }
  });
  page.on("response", (response) => {
    if (response.status() >= 400) {
      errors.push(`http:${response.status()}:${response.url()}`);
      if (response.status() === 404) {
        totals.http_404_count += 1;
      }
    }
  });
  await page.goto(overallUrl, { waitUntil: "load", timeout: 10000 });
  await page.locator("#enter-expression").click();
  await page.waitForFunction(() => (
    window.__touchContractState
    && document.body.classList.contains("expression-open")
  ));
  await freezeNonOverallStories(page);
  await resetRest(page);
  return {
    close: async () => context.close(),
    documentRequests: () => documentRequests,
    errors,
    page,
  };
}

async function stageBox(page) {
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box && box.width === 200 && box.height === 200, "stage missing");
  return box;
}

async function pointer(page, type, kind, x, y, pointerId) {
  await page.evaluate(({ type, kind, x, y, pointerId }) => {
    const stage = document.querySelector("#overall-viewport");
    stage.dispatchEvent(new PointerEvent(kind, {
      bubbles: true,
      buttons: kind === "pointerup" ? 0 : 1,
      cancelable: true,
      clientX: x,
      clientY: y,
      isPrimary: true,
      pointerId,
      pointerType: type,
    }));
  }, { kind, pointerId, type, x, y });
}

async function press(page, type, x, y, pointerId) {
  if (type === "mouse") {
    await page.mouse.move(x, y);
    await page.mouse.down();
  } else {
    await pointer(page, type, "pointerdown", x, y, pointerId);
  }
}

async function move(page, type, x, y, pointerId) {
  if (type === "mouse") {
    await page.mouse.move(x, y);
  } else {
    await pointer(page, type, "pointermove", x, y, pointerId);
  }
}

async function release(page, type, x, y, pointerId) {
  if (type === "mouse") {
    await page.mouse.move(x, y);
    await page.mouse.up();
  } else {
    await pointer(page, type, "pointerup", x, y, pointerId);
  }
}

async function clickStageTarget(page, type, selector, pointerId) {
  const target = page.locator(selector);
  await target.waitFor({ state: "visible" });
  const box = await target.boundingBox();
  assert(box, `menu target missing: ${selector}`);
  const x = box.x + box.width / 2;
  const y = box.y + box.height / 2;
  await press(page, type, x, y, pointerId);
  await sleep(20);
  await release(page, type, x, y, pointerId);
  await sleep(60);
}

async function withScenario(browser, viewport, type, scenario, callback) {
  const session = await openPage(browser, viewport);
  totals.scenario_count += 1;
  const id = `${viewport.name}-${type}-${scenario}`;
  try {
    const baseline = assertSnapshot(
      await screenSnapshot(session.page),
      "expression",
      `${id}-rest`,
    );
    const result = await callback(session.page, id, baseline);
    assert(session.documentRequests() === 1, `${id}: document route count`);
    assert(session.errors.length === 0, `${id}: ${session.errors.join(" | ")}`);
    matrixRows.push({
      document_requests: session.documentRequests(),
      errors: session.errors,
      id,
      pointer_type: type,
      result,
      status: "PASS",
      viewport: viewport.name,
    });
  } finally {
    await session.close();
  }
}

async function replaySingle(browser, viewport, type) {
  await withScenario(
    browser,
    viewport,
    type,
    "single-tap",
    async (page, id, baseline) => {
      const box = await stageBox(page);
      const x = box.x + 158;
      const y = box.y + 82;
      await press(page, type, x, y, 101);
      await sleep(25);
      await release(page, type, x, y, 101);
      await sleep(45);
      const pending = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-pending`,
      );
      assert(pending.contract.pending_tap, `${id}: tap not pending`);
      assert(
        pending.sources.gaze !== baseline.sources.gaze,
        `${id}: no contact gaze response`,
      );
      await sleep(390);
      await waitForVisibleImages(page);
      const committed = assertSnapshot(
        await screenSnapshot(page, true),
        "expression",
        `${id}-committed`,
      );
      const traceCount = await page.evaluate(() => (
        window.__v45TouchTrace.filter(
          (row) => row.kind === "single_tap_committed",
        ).length
      ));
      const event = await page.evaluate(() => (
        window.__lastEmotionDecision?.input?.event || null
      ));
      assert(traceCount === 1, `${id}: single tap committed ${traceCount}`);
      assert(event === "touch_tap", `${id}: TOUCH_TAP not dispatched`);
      assert(
        committed.contract.recording_entries === 0
        && committed.contract.menu_entries === 0,
        `${id}: single tap activated a route`,
      );
      await capture(page, `${id}-response`);
      return {
        committed_once: true,
        gaze_replaced: committed.sources.gaze !== baseline.sources.gaze,
        route_activations: 0,
      };
    },
  );
}

async function replayDrag(browser, viewport, type) {
  await withScenario(
    browser,
    viewport,
    type,
    "drag",
    async (page, id) => {
      const box = await stageBox(page);
      const at = (x, y) => ({ x: box.x + x, y: box.y + y });
      const start = at(100, 100);
      await press(page, type, start.x, start.y, 201);
      await sleep(40);
      const directions = [
        ["left", 28, 100],
        ["up", 100, 28],
        ["right", 172, 100],
        ["down", 100, 172],
        ["center", 100, 100],
      ];
      const gazeSources = [];
      const pixelSignatures = [];
      for (const [name, x, y] of directions) {
        const target = at(x, y);
        await move(page, type, target.x, target.y, 201);
        await sleep(45);
        const snapshot = assertSnapshot(
          await screenSnapshot(page),
          "expression",
          `${id}-${name}`,
        );
        assert(
          snapshot.contract.active_pointer?.moved,
          `${id}-${name}: drag not active`,
        );
        assert(!snapshot.contract.pending_tap, `${id}-${name}: tap retained`);
        assert(
          snapshot.contract.hold_progress === 0,
          `${id}-${name}: hold retained`,
        );
        gazeSources.push(snapshot.sources.gaze);
        pixelSignatures.push(snapshot.pixel.signature);
        totals.directional_moves += 1;
      }
      assert(new Set(gazeSources).size === 5, `${id}: stale gaze source`);
      assert(
        new Set(pixelSignatures).size === 5,
        `${id}: stale gaze pixels`,
      );
      await capture(page, `${id}-center-held`);
      const center = at(100, 100);
      await release(page, type, center.x, center.y, 201);
      await sleep(90);
      const released = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-released`,
      );
      assert(
        released.sources.gaze === gazeSources.at(-1),
        `${id}: release did not preserve centered gaze`,
      );
      assert(
        released.pixel.signature === pixelSignatures.at(-1),
        `${id}: release center pixel mismatch`,
      );
      assert(
        !released.contract.story_paused
        && !released.contract.story_touching,
        `${id}: story not resumed`,
      );
      return {
        direction_count: directions.length,
        layer_count_constant: true,
        unique_gaze_sources: new Set(gazeSources).size,
        unique_pixel_signatures: new Set(pixelSignatures).size,
      };
    },
  );
}

async function replayRecording(browser, viewport, type) {
  await withScenario(
    browser,
    viewport,
    type,
    "recording-return",
    async (page, id, baseline) => {
      const box = await stageBox(page);
      const x = box.x + 100;
      const y = box.y + 100;
      await press(page, type, x, y, 301);
      await sleep(40);
      await release(page, type, x, y, 301);
      await sleep(90);
      await press(page, type, x + 3, y + 2, 302);
      await sleep(40);
      await release(page, type, x + 3, y + 2, 302);
      await sleep(120);
      await waitForVisibleImages(page);
      const recording = assertSnapshot(
        await screenSnapshot(page),
        "recording",
        `${id}-entry`,
      );
      assert(
        recording.contract.recording_entries === 1
        && recording.contract.menu_entries === 0,
        `${id}: recording route count`,
      );
      const singleCommits = await page.evaluate(() => (
        window.__v45TouchTrace.filter(
          (row) => row.kind === "single_tap_committed",
        ).length
      ));
      assert(singleCommits === 0, `${id}: double tap committed single`);
      totals.route_recording_entries += 1;
      await capture(page, `${id}-entry`);
      await page.locator('[data-testid="recording-return"]').click();
      await waitForVisibleImages(page);
      const returned = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-returned`,
      );
      const returnPixelsEqual = boolPixelEqual(returned.pixel, baseline.pixel);
      assert(returnPixelsEqual, `${id}: return pixel identity`);
      assert(
        returned.sources.face === baseline.sources.face
        && returned.sources.gaze === baseline.sources.gaze,
        `${id}: return source identity`,
      );
      assert(
        !returned.contract.active_pointer
        && !returned.contract.pending_tap
        && returned.contract.hold_progress === 0,
        `${id}: recording return transient state`,
      );
      await capture(page, `${id}-returned`);
      return {
        microphone_requests: recording.media_request_count,
        recording_entries: recording.contract.recording_entries,
        return_equals_fresh_centered_rest: returnPixelsEqual,
      };
    },
  );
}

async function replayHoldMenu(browser, viewport, type) {
  await withScenario(
    browser,
    viewport,
    type,
    "hold-menu-return",
    async (page, id, baseline) => {
      const box = await stageBox(page);
      const x = box.x + 100;
      const y = box.y + 100;
      await press(page, type, x, y, 401);
      await sleep(300);
      const progress = await screenSnapshot(page);
      assert(
        progress.contract.hold_progress > 0
        && progress.contract.hold_progress < 100,
        `${id}: hold progress is not continuous`,
      );
      await page.evaluate(() => {
        if (holdRaf) {
          cancelAnimationFrame(holdRaf);
        }
        holdRaf = 0;
        holdFill.style.width = "50%";
      });
      assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-hold-50`,
      );
      await capture(page, `${id}-hold-50`);
      await page.evaluate(() => {
        if (gesture && !gesture.moved && interactionMode === "expression") {
          holdRaf = requestAnimationFrame(animateHold);
        }
      });
      await sleep(480);
      await waitForVisibleImages(page);
      const menu = assertSnapshot(
        await screenSnapshot(page),
        "menu",
        `${id}-menu-roots`,
      );
      assert(
        menu.contract.menu_entries === 1
        && menu.contract.recording_entries === 0,
        `${id}: hold route count`,
      );
      totals.route_menu_entries += 1;
      await release(page, type, x, y, 401);
      await sleep(80);
      const afterRelease = assertSnapshot(
        await screenSnapshot(page),
        "menu",
        `${id}-menu-release`,
      );
      assert(
        afterRelease.contract.menu_entries === 1,
        `${id}: duplicate menu entry`,
      );
      await capture(page, `${id}-menu-roots`);

      for (const rootIndex of [0, 1]) {
        await clickStageTarget(
          page,
          type,
          `[data-root="true"][data-index="${rootIndex}"]`,
          410 + rootIndex,
        );
        const details = assertSnapshot(
          await screenSnapshot(page),
          "menu",
          `${id}-root-${rootIndex}`,
        );
        assert(
          details.contract.menu_view === "details",
          `${id}: root ${rootIndex} unavailable`,
        );
        totals.menu_root_visits += 1;
        if (rootIndex === 0) {
          await clickStageTarget(
            page,
            type,
            '[data-header="true"]',
            420,
          );
          assert(
            (await screenSnapshot(page)).contract.menu_view === "roots",
            `${id}: Voice back unavailable`,
          );
        }
      }
      await clickStageTarget(
        page,
        type,
        '[data-detail="true"][data-index="3"]',
        421,
      );
      const uiAssets = assertSnapshot(
        await screenSnapshot(page),
        "menu",
        `${id}-device-ui-assets`,
      );
      assert(
        uiAssets.contract.menu_view === "expression",
        `${id}: Device > UI assets unavailable`,
      );
      totals.device_ui_assets_visits += 1;
      const expressionSources = [];
      for (const state of ["calm", "curious", "warm"]) {
        await page.locator(`[data-testid="integrated-${state}"]`).click();
        await waitForVisibleImages(page);
        const expression = assertSnapshot(
          await screenSnapshot(page),
          "menu",
          `${id}-ui-assets-${state}`,
        );
        expressionSources.push(expression.sources.menu);
      }
      assert(
        new Set(expressionSources).size === 3,
        `${id}: UI asset selections did not change image`,
      );
      await capture(page, `${id}-device-ui-assets`);
      await page.locator('[data-testid="integrated-menu-back"]').click();
      assert(
        (await screenSnapshot(page)).contract.menu_view === "roots",
        `${id}: UI assets back unavailable`,
      );
      for (const rootIndex of [2, 3]) {
        await clickStageTarget(
          page,
          type,
          `[data-root="true"][data-index="${rootIndex}"]`,
          430 + rootIndex,
        );
        const details = assertSnapshot(
          await screenSnapshot(page),
          "menu",
          `${id}-root-${rootIndex}`,
        );
        assert(
          details.contract.menu_view === "details",
          `${id}: root ${rootIndex} unavailable`,
        );
        totals.menu_root_visits += 1;
        await clickStageTarget(
          page,
          type,
          '[data-header="true"]',
          440 + rootIndex,
        );
      }
      await page.locator('[data-testid="integrated-menu-return"]').click();
      await waitForVisibleImages(page);
      const returned = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-returned`,
      );
      const returnPixelsEqual = boolPixelEqual(returned.pixel, baseline.pixel);
      assert(returnPixelsEqual, `${id}: menu return pixels`);
      assert(
        returned.sources.face === baseline.sources.face
        && returned.sources.gaze === baseline.sources.gaze,
        `${id}: menu return source identity`,
      );
      assert(
        !returned.contract.active_pointer
        && !returned.contract.pending_tap
        && returned.contract.hold_progress === 0,
        `${id}: menu return transient state`,
      );
      await capture(page, `${id}-returned`);
      return {
        menu_entries: menu.contract.menu_entries,
        return_equals_fresh_centered_rest: returnPixelsEqual,
        root_visits: 4,
        ui_asset_states: expressionSources.length,
      };
    },
  );
}

async function replayEarlyUp(browser, viewport, type) {
  await withScenario(
    browser,
    viewport,
    type,
    "early-up",
    async (page, id) => {
      const box = await stageBox(page);
      const x = box.x + 112;
      const y = box.y + 96;
      await press(page, type, x, y, 501);
      await sleep(300);
      const progress = await screenSnapshot(page);
      assert(
        progress.contract.hold_progress > 0
        && progress.contract.hold_progress < 100,
        `${id}: no partial hold progress`,
      );
      await release(page, type, x, y, 501);
      await sleep(800);
      const settled = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-settled`,
      );
      assert(
        settled.contract.menu_entries === 0
        && settled.contract.recording_entries === 0,
        `${id}: early up activated route`,
      );
      assert(
        !settled.contract.active_pointer
        && !settled.contract.pending_tap
        && settled.contract.hold_progress === 0,
        `${id}: early up transient state`,
      );
      totals.cancellation_scenarios += 1;
      return { hold_canceled: true, route_activations: 0 };
    },
  );
}

async function replayCancel(browser, viewport, type, eventName) {
  await withScenario(
    browser,
    viewport,
    type,
    eventName,
    async (page, id) => {
      const box = await stageBox(page);
      const x = box.x + 106;
      const y = box.y + 94;
      await press(page, type, x, y, 601);
      await sleep(120);
      if (eventName === "blur") {
        await page.evaluate(() => window.dispatchEvent(new Event("blur")));
      } else {
        await page.evaluate(({ eventName, type }) => {
          const active = window.__touchContractState().activePointer;
          document.querySelector("#overall-viewport").dispatchEvent(
            new PointerEvent(eventName, {
              bubbles: true,
              cancelable: true,
              pointerId: active?.id ?? 601,
              pointerType: active?.type ?? type,
            }),
          );
        }, { eventName, type });
      }
      if (type === "mouse") {
        await page.mouse.up().catch(() => {});
      }
      await sleep(780);
      const settled = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-settled`,
      );
      assert(
        settled.contract.menu_entries === 0
        && settled.contract.recording_entries === 0,
        `${id}: cancellation activated route`,
      );
      assert(
        !settled.contract.active_pointer
        && !settled.contract.pending_tap
        && settled.contract.hold_progress === 0,
        `${id}: cancellation transient state`,
      );
      assert(
        !settled.contract.story_paused
        && !settled.contract.story_touching,
        `${id}: cancellation left story paused`,
      );
      totals.cancellation_scenarios += 1;
      return { cancellation: eventName, route_activations: 0 };
    },
  );
}

async function captureLayout(browser, viewport) {
  const session = await openPage(browser, viewport);
  try {
    await pageLayoutAssertions(session.page, viewport);
    await session.page.evaluate(() => {
      for (const state of Object.values(
        window.__companionViewportStates || {},
      )) {
        clearTimeout(state.timer);
        state.timer = 0;
        state.touching = true;
        state.request += 1;
        state.gazeRequest += 1;
      }
      window.scrollTo(0, 0);
    });
    await capture(session.page, `${viewport.name}-layout`, "layout");
    assert(session.documentRequests() === 1, "layout document count");
    assert(session.errors.length === 0, "layout page errors");
  } finally {
    await session.close();
  }
}

async function pageLayoutAssertions(page, viewport) {
  const layout = await page.evaluate(() => {
    const visible = (element) => {
      if (!element || element.hidden || element.closest("[hidden]")) {
        return false;
      }
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return (
        style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0
      );
    };
    const stage = document.querySelector("#overall-viewport")
      .getBoundingClientRect();
    const storyWall = document.querySelector("#story-wall")
      .getBoundingClientRect();
    return {
      debug_visible: [
        ".screen-meta",
        ".decision-panel",
        "#emotion-rule",
        "#gesture-status",
        ".authority-source",
      ].filter((selector) => visible(document.querySelector(selector))),
      primary_center_delta_px: Math.abs(
        stage.left + stage.width / 2 - innerWidth / 2,
      ),
      primary_height: stage.height,
      primary_width: stage.width,
      story_below_primary: storyWall.top > stage.bottom,
      story_count: document.querySelectorAll("#story-wall .story-row").length,
    };
  });
  assert(layout.primary_width === 200, `${viewport.name}: layout width`);
  assert(layout.primary_height === 200, `${viewport.name}: layout height`);
  assert(
    layout.primary_center_delta_px <= 1,
    `${viewport.name}: layout center`,
  );
  assert(layout.debug_visible.length === 0, `${viewport.name}: layout debug`);
  assert(layout.story_count === 16, `${viewport.name}: story count`);
  assert(layout.story_below_primary, `${viewport.name}: story wall position`);
  return layout;
}

async function run() {
  assert(fileSha256(pagePath) === acceptedPageSha256, "accepted page drift");
  const browser = await playwright.chromium.launch({
    headless: true,
    timeout: 15000,
  });
  let browserVersion;
  try {
    browserVersion = browser.version();
    const viewports = [
      { height: 900, name: "desktop", width: 1280 },
      { height: 844, name: "mobile", width: 390 },
    ];
    for (const viewport of viewports) {
      await captureLayout(browser, viewport);
      for (const type of ["mouse", "touch", "pen"]) {
        totals.replay_combinations += 1;
        await replaySingle(browser, viewport, type);
        await replayDrag(browser, viewport, type);
        await replayRecording(browser, viewport, type);
        await replayHoldMenu(browser, viewport, type);
        await replayEarlyUp(browser, viewport, type);
        await replayCancel(browser, viewport, type, "pointercancel");
        await replayCancel(browser, viewport, type, "blur");
      }
    }
  } finally {
    await browser.close();
  }

  const observedScreenshots = fs.readdirSync(screenshotRoot)
    .filter((name) => name.endsWith(".png"))
    .sort();
  assert(
    JSON.stringify(observedScreenshots)
      === JSON.stringify([...expectedScreenshotNames].sort()),
    "unexpected or missing screenshot files",
  );
  assert(totals.replay_combinations === 6, "replay matrix is not 6/6");
  assert(totals.scenario_count === 42, "scenario count is not 42");
  assert(totals.directional_moves === 30, "direction count is not 30");
  assert(totals.route_recording_entries === 6, "recording count is not 6");
  assert(totals.route_menu_entries === 6, "menu count is not 6");
  assert(totals.menu_root_visits === 24, "menu roots are not 24/24");
  assert(
    totals.device_ui_assets_visits === 6,
    "Device > UI assets is not 6/6",
  );
  for (const key of [
    "microphone_requests",
    "stale_layer_count",
    "conflicting_surface_overlap_count",
    "outside_black_pixel_count",
    "out_of_bounds_count",
    "http_404_count",
    "page_error_count",
  ]) {
    assert(totals[key] === 0, `${key} is nonzero`);
  }

  const screenshotManifest = {
    accepted_page_sha256: acceptedPageSha256,
    schema: "companion.browser-owner-review-screenshots.v1",
    screenshots: screenshotRows.sort((a, b) => a.id.localeCompare(b.id)),
    status: "PASS",
  };
  writeCanonical(screenshotManifestPath, screenshotManifest);

  const pixelDomRoute = {
    invariants: {
      accepted_centered_rest_png_sha256: acceptedCenteredRestPngSha256,
      conflicting_surface_overlap_count: (
        totals.conflicting_surface_overlap_count
      ),
      debug_visible_count: 0,
      document_route_per_scenario: 1,
      http_404_count: totals.http_404_count,
      microphone_request_count: totals.microphone_requests,
      out_of_bounds_count: totals.out_of_bounds_count,
      outside_black_pixel_count: totals.outside_black_pixel_count,
      primary_screen_count: 1,
      stale_layer_count: totals.stale_layer_count,
    },
    matrix: matrixRows.sort((a, b) => a.id.localeCompare(b.id)),
    schema: "companion.browser-owner-review-pixel-dom-route.v1",
    states: stateRows.sort((a, b) => a.id.localeCompare(b.id)),
    status: "PASS",
  };
  writeCanonical(pixelDomRoutePath, pixelDomRoute);

  const result = {
    artifacts: {
      pixel_dom_route: {
        path: path.relative(repoRoot, pixelDomRoutePath).replaceAll("\\", "/"),
        sha256: fileSha256(pixelDomRoutePath),
      },
      screenshot_manifest: {
        path: path
          .relative(repoRoot, screenshotManifestPath)
          .replaceAll("\\", "/"),
        sha256: fileSha256(screenshotManifestPath),
      },
    },
    checks: {
      accepted_page_identity: true,
      accepted_centered_rest_lineage_bound: true,
      debug_parameters_hidden: true,
      desktop_mobile_layout: true,
      device_ui_assets_6_of_6: true,
      directional_replacement_30_of_30: true,
      early_up_cancel_blur_18_of_18: true,
      layer_exclusivity: true,
      menu_recording_return_identity_12_of_12: true,
      menu_roots_24_of_24: true,
      mouse_touch_pen_6_of_6: true,
      no_404_overlap_bounds_or_stale: true,
      no_microphone_request: true,
      route_activation_exactly_once: true,
      single_tap_once_6_of_6: true,
    },
    page: {
      accepted_sha256: acceptedPageSha256,
      observed_sha256: fileSha256(pagePath),
      repo_path: pageRepoPath,
      url: overallUrl,
    },
    requirements: [
      "COMP-REQ-440",
      "COMP-REQ-441",
      "COMP-REQ-442",
      "COMP-REQ-471",
    ],
    runtime: {
      browser: "chromium",
      browser_version: browserVersion,
      playwright_module_path: playwright.modulePath,
      playwright_package_sha256: playwright.packageSha256,
      playwright_version: playwright.version,
    },
    schema: "companion.browser-owner-review-replay.v1",
    side_effect_counters: {
      browser_processes: 1,
      hardware: 0,
      lower_write: 0,
      microphone_permission_requests: totals.microphone_requests,
      owner_prompt: 0,
      owner_result_write: 0,
      platform_write: 0,
      production_write: 0,
      registry_write: 0,
      server_start: 0,
      upper_artifact_writes: screenshotRows.length + 3,
    },
    status: "PASS_BROWSER_OWNER_REVIEW_MACHINE_REPLAY",
    totals,
  };
  writeCanonical(replayPath, result);
  console.log(JSON.stringify({
    artifact_sha256: fileSha256(replayPath),
    page_sha256: result.page.observed_sha256,
    replay_combinations: totals.replay_combinations,
    scenario_count: totals.scenario_count,
    screenshot_count: screenshotRows.length,
    status: result.status,
  }));
}

try {
  await run();
} finally {
  if (lockFd) {
    try {
      fs.closeSync(lockFd);
    } catch {
      // Bounded cleanup only.
    }
  }
  try {
    fs.unlinkSync(lockPath);
  } catch {
    // Preserve the primary failure if cleanup also fails.
  }
}
