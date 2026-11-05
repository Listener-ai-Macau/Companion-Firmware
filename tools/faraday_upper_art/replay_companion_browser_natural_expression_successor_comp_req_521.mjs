#!/usr/bin/env node
/* Deterministic COMP-REQ-508/518/520/521 replay with pixel/event oracles. */

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
  "docs/validation/companion-browser-natural-expression-successor-comp-req-518-520-521",
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
  "24B5720F14B6793B201C4E74AD8BDB2219EE4F8CC941454983876979DA9ADAB1";
const acceptedCenteredRestPngSha256 =
  "3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31";
const overallUrl =
  "http://127.0.0.1:4173/" + pageRepoPath;
const runtimeUrl = process.env.COMPANION_BROWSER_REPLAY_URL || overallUrl;
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
  natural_bridge_commits: 0,
  natural_bridge_ordered: 0,
  replay_combinations: 0,
  route_recording_entries: 0,
  route_recording_exits: 0,
  recording_negative_checks: 0,
  recording_ordered_phase_traces: 0,
  recording_reentries: 0,
  recording_wave_cycles: 0,
  mic_glyph_pixel_count: 0,
  route_menu_entries: 0,
  scenario_count: 0,
  snapshot_count: 0,
  stale_layer_count: 0,
  stale_pupil_pixel_count: 0,
  stale_pupil_state_count: 0,
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
    let previous = null;
    let stable = null;
    for (let attempt = 0; attempt < 12; attempt += 1) {
      const current = await page.screenshot({
        fullPage: false,
        animations: "disabled",
      });
      if (previous && current.equals(previous)) {
        stable = current;
        break;
      }
      previous = current;
      await sleep(60);
    }
    assert(stable, `${id}: layout did not reach two byte-identical captures`);
    fs.writeFileSync(target, stable);
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
  return page.evaluate(async (freezeAfterSnapshot) => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const menu = stage.querySelector(".integrated-menu-image");
    const menuSurface = stage.querySelector("#integrated-menu");
    const hold = stage.querySelector(".hold-progress");
    const recordingWave = stage.querySelector(".recording-waves");
    const recordingIndicator = stage.querySelector(".recording-indicator");
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
    const facePixels = context.getImageData(0, 0, 200, 200).data;
    const pupilOracle = {
      binary_mismatch_count: 0,
      checked: false,
      stale_center_mask_left_eye: 0,
      stale_center_mask_right_eye: 0,
      stale_center_mask_total: 0,
    };
    if (visible(frame) && visible(gaze)) {
      const overallState = window.__companionViewportStates.overall;
      const sourceBase = overallState.activeFrame?.touch_base
        || overallState.activeFrame?.src
        || overallState.activeBaseSrc;
      const centerSource = touchData.overlays[touchData.center_key];
      const currentSource = gaze.getAttribute("src");
      const load = (source) => new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(
          `pupil oracle image load failed: ${source}`,
        ));
        image.src = source;
      });
      const withRevision = (source) => {
        const resolved = new URL(source, location.href);
        resolved.searchParams.set("review", sourceRevision);
        return resolved.href;
      };
      const [baseImage, centerImage, currentImage] = await Promise.all([
        load(withRevision(sourceBase)),
        load(withRevision(centerSource)),
        load(currentSource),
      ]);
      const centerMask = document.createElement("canvas");
      centerMask.width = 200;
      centerMask.height = 200;
      const centerMaskContext = centerMask.getContext("2d");
      const [tx, ty] = transformOffset(gaze);
      centerMaskContext.drawImage(centerImage, tx, ty, 200, 200);
      centerMaskContext.globalCompositeOperation = "source-in";
      centerMaskContext.fillStyle = "#000";
      centerMaskContext.fillRect(0, 0, 200, 200);
      const expectedCanvas = document.createElement("canvas");
      expectedCanvas.width = 200;
      expectedCanvas.height = 200;
      const expectedContext = expectedCanvas.getContext(
        "2d",
        { willReadFrequently: true },
      );
      expectedContext.fillStyle = "#fff";
      expectedContext.fillRect(0, 0, 200, 200);
      expectedContext.drawImage(baseImage, 0, 0, 200, 200);
      expectedContext.drawImage(centerMask, 0, 0);
      expectedContext.drawImage(currentImage, tx, ty, 200, 200);
      const expectedPixels = expectedContext.getImageData(
        0,
        0,
        200,
        200,
      ).data;
      const maskPixels = centerMaskContext.getImageData(
        0,
        0,
        200,
        200,
      ).data;
      for (let pixel = 0; pixel < 40000; pixel += 1) {
        const index = pixel * 4;
        const actualBlack = (
          facePixels[index] < 128
          && facePixels[index + 1] < 128
          && facePixels[index + 2] < 128
        );
        const expectedBlack = (
          expectedPixels[index] < 128
          && expectedPixels[index + 1] < 128
          && expectedPixels[index + 2] < 128
        );
        if (actualBlack !== expectedBlack) {
          pupilOracle.binary_mismatch_count += 1;
        }
        if (
          !actualBlack
          && expectedBlack
          && maskPixels[index + 3] > 0
        ) {
          pupilOracle.stale_center_mask_total += 1;
          if (pixel % 200 < 100) {
            pupilOracle.stale_center_mask_left_eye += 1;
          } else {
            pupilOracle.stale_center_mask_right_eye += 1;
          }
        }
      }
      pupilOracle.checked = true;
    }
    const micOracle = {
      checked: false,
      current_wave_mask_overlap: 0,
      old_mic_mask_pixels: 0,
      visible_mic_asset_sources: 0,
    };
    if (visible(recordingWave)) {
      const load = (source) => new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => resolve(image);
        image.onerror = () => reject(new Error(
          `microphone oracle image load failed: ${source}`,
        ));
        image.src = source;
      });
      const oldRecording = await load(
        new URL(
          "recording_with_calm-00-recording_input_0.png",
          location.href,
        ).href,
      );
      const sourceCanvas = document.createElement("canvas");
      sourceCanvas.width = 200;
      sourceCanvas.height = 200;
      const sourceContext = sourceCanvas.getContext(
        "2d",
        { willReadFrequently: true },
      );
      sourceContext.fillStyle = "#fff";
      sourceContext.fillRect(0, 0, 200, 200);
      sourceContext.drawImage(oldRecording, 0, 0, 200, 200);
      const sourcePixels = sourceContext.getImageData(
        0,
        0,
        200,
        200,
      ).data;
      const wavePixels = recordingWave.getContext(
        "2d",
        { willReadFrequently: true },
      ).getImageData(0, 0, 200, 200).data;
      const seen = new Uint8Array(40000);
      const micMask = new Uint8Array(40000);
      const isBlack = (index) => (
        sourcePixels[index * 4 + 3] > 0
        && sourcePixels[index * 4] < 128
        && sourcePixels[index * 4 + 1] < 128
        && sourcePixels[index * 4 + 2] < 128
      );
      for (let seed = 0; seed < 40000; seed += 1) {
        if (seen[seed] || !isBlack(seed)) {
          continue;
        }
        const queue = [seed];
        const component = [];
        seen[seed] = 1;
        let minX = 200;
        let minY = 200;
        let maxX = -1;
        let maxY = -1;
        while (queue.length) {
          const current = queue.pop();
          component.push(current);
          const x = current % 200;
          const y = Math.floor(current / 200);
          minX = Math.min(minX, x);
          minY = Math.min(minY, y);
          maxX = Math.max(maxX, x);
          maxY = Math.max(maxY, y);
          for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
            const nx = x + dx;
            const ny = y + dy;
            if (nx < 0 || nx >= 200 || ny < 0 || ny >= 200) {
              continue;
            }
            const next = ny * 200 + nx;
            if (!seen[next] && isBlack(next)) {
              seen[next] = 1;
              queue.push(next);
            }
          }
        }
        if (
          minX >= 150
          && minY >= 80
          && maxY <= 115
          && maxX >= 155
          && component.length >= 3
        ) {
          for (const index of component) {
            micMask[index] = 1;
          }
        }
      }
      for (let index = 0; index < 40000; index += 1) {
        if (!micMask[index]) {
          continue;
        }
        micOracle.old_mic_mask_pixels += 1;
        const offset = index * 4;
        if (
          wavePixels[offset + 3] > 0
          && wavePixels[offset] < 128
          && wavePixels[offset + 1] < 128
          && wavePixels[offset + 2] < 128
        ) {
          micOracle.current_wave_mask_overlap += 1;
        }
      }
      micOracle.visible_mic_asset_sources = [frame, gaze, menu]
        .filter((element) => visible(element))
        .filter((element) => (
          (element.getAttribute("src") || "").includes("recording_with_")
        )).length;
      micOracle.checked = true;
      context.drawImage(recordingWave, 0, 0, 200, 200);
    }
    if (visible(recordingIndicator)) {
      context.drawImage(recordingIndicator, 10, 10, 18, 18);
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
    const recordingContract = window.__recordingContractState();
    const interactionTrace = window.__touchInteractionTrace || [];
    const canonicalWaveTrace = recordingContract.waveTrace
      .filter((row) => row.cycle === 0)
      .filter((row, index, rows) => (
        rows.findIndex((candidate) => (
          candidate.sequence === row.sequence
          && candidate.step === row.step
        )) === index
      ))
      .sort((left, right) => (
        left.sequence - right.sequence || left.step - right.step
      ));
    const faceVisible = visible(frame) ? 1 : 0;
    const gazeVisible = visible(gaze) ? 1 : 0;
    const menuVisible = visible(menu) && visible(menuSurface) ? 1 : 0;
    const waveVisible = visible(recordingWave) ? 1 : 0;
    const indicatorVisible = visible(recordingIndicator) ? 1 : 0;
    const expected = contract.mode === "menu"
      ? {
          face: 0,
          gaze: 0,
          highlight: 0,
          indicator: 0,
          menu: 1,
          wave: 0,
        }
      : {
          face: 1,
          gaze: 1,
          highlight: 1,
          indicator: contract.mode === "recording" ? 1 : 0,
          menu: 0,
          wave: contract.mode === "recording" ? 1 : 0,
        };
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
      ["recording_wave", recordingWave],
      ["recording_indicator", recordingIndicator],
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
        pending_tap_mode: contract.pendingTapMode,
        recording_exits: contract.recordingExits,
        recording_entries: contract.recordingEntries,
        story_paused: contract.storyPaused,
        story_touching: contract.storyTouching,
      },
      dom: {
        conflict_count: menuVisible && (
          faceVisible || gazeVisible || waveVisible || indicatorVisible
        ) ? 1 : 0,
        debug_visible: debugVisible,
        expected,
        face_count: faceVisible,
        gaze_count: gazeVisible,
        gaze_node_count: stage.querySelectorAll(".viewport-gaze").length,
        highlight_layer_count: gazeVisible,
        hold_count: visible(hold) ? 1 : 0,
        menu_count: menuVisible,
        menu_node_count: stage.querySelectorAll(".integrated-menu-image").length,
        recording_indicator_count: indicatorVisible,
        recording_indicator_node_count: stage.querySelectorAll(
          ".recording-indicator",
        ).length,
        recording_wave_count: waveVisible,
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
      events: {
        event_ids: interactionTrace.map((row) => row.event_id),
        kinds: interactionTrace.map((row) => row.kind),
        route_enter_ids: interactionTrace
          .filter((row) => row.kind === "recording_route_enter")
          .map((row) => row.event_id),
        route_exit_ids: interactionTrace
          .filter((row) => row.kind === "recording_route_exit")
          .map((row) => row.event_id),
      },
      media_request_count: window.__ownerMediaRequestCount || 0,
      microphone_oracle: micOracle,
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
      pupil_oracle: pupilOracle,
      recording: {
        active: recordingContract.active,
        consumed_pairs: recordingContract.consumedPairs,
        entries: recordingContract.entries,
        exits: recordingContract.exits,
        indicator_nodes: recordingContract.indicatorNodes,
        indicator_visible: recordingContract.indicatorVisible,
        mic_glyph_present: recordingContract.micGlyphPresent,
        phase: recordingContract.phase,
        phase_trace: recordingContract.phaseTrace,
        sequence: recordingContract.sequence,
        wave_step: recordingContract.active
          ? recordingContract.waveStep
          : null,
        wave_trace: canonicalWaveTrace,
        wave_visible: recordingContract.waveVisible,
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
    + Math.abs(
      snapshot.dom.recording_indicator_count - expected.indicator
    )
    + Math.abs(snapshot.dom.recording_wave_count - expected.wave)
  );
  totals.stale_layer_count += stale;
  totals.stale_pupil_pixel_count += (
    snapshot.pupil_oracle.stale_center_mask_total
  );
  totals.stale_pupil_state_count += (
    snapshot.pupil_oracle.stale_center_mask_total > 0 ? 1 : 0
  );
  totals.conflicting_surface_overlap_count += snapshot.dom.conflict_count;
  totals.outside_black_pixel_count += snapshot.pixel.outside_black_pixels;
  totals.out_of_bounds_count += snapshot.dom.out_of_bounds.length;
  totals.microphone_requests += snapshot.media_request_count;
  totals.mic_glyph_pixel_count += (
    snapshot.microphone_oracle.current_wave_mask_overlap
  );
  assert(snapshot.contract.mode === expectedMode, `${id}: wrong mode`);
  assert(stale === 0, `${id}: stale/duplicate surface layer`);
  assert(snapshot.dom.conflict_count === 0, `${id}: conflicting surfaces`);
  assert(snapshot.dom.primary_screen_count === 1, `${id}: primary screen count`);
  assert(snapshot.dom.gaze_node_count === 1, `${id}: gaze node count`);
  assert(snapshot.dom.menu_node_count === 1, `${id}: menu node count`);
  assert(
    snapshot.dom.recording_indicator_node_count === 1,
    `${id}: recording indicator node count`,
  );
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
  if (expectedMode !== "menu") {
    assert(snapshot.pupil_oracle.checked, `${id}: pupil oracle not checked`);
    assert(
      snapshot.pupil_oracle.binary_mismatch_count === 0
      && snapshot.pupil_oracle.stale_center_mask_total === 0
      && snapshot.pupil_oracle.stale_center_mask_left_eye === 0
      && snapshot.pupil_oracle.stale_center_mask_right_eye === 0,
      `${id}: stale pupil/highlight pixels`,
    );
  }
  if (expectedMode === "recording") {
    assert(
      snapshot.microphone_oracle.checked
      && snapshot.microphone_oracle.old_mic_mask_pixels > 0
      && snapshot.microphone_oracle.current_wave_mask_overlap === 0
      && snapshot.microphone_oracle.visible_mic_asset_sources === 0
      && !snapshot.recording.mic_glyph_present,
      `${id}: microphone glyph/source present`,
    );
  }
  assert(
    new Set(snapshot.events.event_ids).size
      === snapshot.events.event_ids.length,
    `${id}: duplicate interaction event id`,
  );
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
    events: snapshot.events,
    id,
    microphone_oracle: snapshot.microphone_oracle,
    pixel: snapshot.pixel,
    pupil_oracle: snapshot.pupil_oracle,
    recording: snapshot.recording,
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
      const story = storyByName.get(state.storyName);
      const item = story?.frames[0];
      const stage = document.querySelector(
        `[data-viewport-story="${CSS.escape(name)}"]`,
      );
      const frame = stage?.querySelector(".viewport-frame");
      const gaze = stage?.querySelector(".viewport-gaze");
      if (item && frame && gaze) {
        const offset = touchData.story_offsets[state.storyName] || [0, 0];
        state.frameIndex = 1;
        state.activeFrame = item;
        state.activeFrameIndex = 0;
        state.activeBaseSrc = item.touch_base || item.src;
        frame.src = cached(state.activeBaseSrc);
        gaze.src = cached(touchData.overlays[touchData.center_key]);
        gaze.style.transform = `translate(${offset[0]}px,${offset[1]}px)`;
        frame.hidden = false;
        gaze.hidden = false;
        stage.querySelector(".viewport-staging").hidden = true;
      }
    }
  });
}

async function waitForVisibleImages(page) {
  try {
    await page.waitForFunction(() => {
      const stage = document.querySelector("#overall-viewport");
      if (!stage) {
        return false;
      }
      const visible = [...stage.querySelectorAll("img")]
        .filter((image) => !image.hidden && !image.closest("[hidden]"));
      const mode = window.__touchContractState?.().mode;
      const expectedClasses = mode === "menu"
        ? ["integrated-menu-image"]
        : ["viewport-frame", "viewport-gaze"];
      return (
        visible.length === expectedClasses.length
        && expectedClasses.every(
          (className) => visible.some((image) => image.classList.contains(className)),
        )
        && visible.every(
          (image) => image.complete && image.naturalWidth === 200,
        )
      );
    }, null, { timeout: 8000 });
  } catch (error) {
    const imageState = await page.evaluate(() => {
      const stage = document.querySelector("#overall-viewport");
      return [...(stage?.querySelectorAll("img") || [])].map((image) => ({
        class_name: image.className,
        complete: image.complete,
        hidden: image.hidden,
        hidden_ancestor: Boolean(image.closest("[hidden]")),
        natural_height: image.naturalHeight,
        natural_width: image.naturalWidth,
        src: image.getAttribute("src") || "",
      }));
    });
    throw new Error(
      `overall visible image decode timeout: ${JSON.stringify(imageState)}`,
      { cause: error },
    );
  }
  await sleep(60);
}

async function initializeOverallRest(page) {
  await page.evaluate(() => {
    const state = window.__companionViewportStates.overall;
    const storyName = "calm_presence";
    const story = storyByName.get(storyName);
    const item = story.frames[0];
    const offset = touchData.story_offsets[storyName] || [0, 0];

    clearTimeout(state.timer);
    state.timer = 0;
    state.request += 1;
    state.gazeRequest += 1;
    gazeEpoch += 1;
    state.storyName = storyName;
    state.frameIndex = 1;
    state.activeFrame = item;
    state.activeFrameIndex = 0;
    state.activeBaseSrc = item.touch_base || item.src;
    state.activeFrameStartedAt = performance.now();
    state.activeFrameDurationMs = item.duration_ms;
    state.pausedRemainingMs = item.duration_ms;
    state.touching = false;
    touchStoryPaused = false;
    touchResponsePoint = null;
    interactionMode = "expression";
    integratedMenu.hidden = true;
    interactionActions.hidden = true;
    interactionActions.replaceChildren();
    recordingWaves.hidden = true;
    recordingIndicator.hidden = true;
    recordingIndicator.dataset.recordingStatus = "inactive";
    holdProgress.hidden = true;
    holdFill.style.width = "0%";
    overallFrame.dataset.gazeCleared = "true";
    overallFrame.src = cached(state.activeBaseSrc);
    overallGaze.style.transform = `translate(${offset[0]}px,${offset[1]}px)`;
    overallGaze.src = cached(touchData.overlays[touchData.center_key]);
    overallFrame.hidden = false;
    overallGaze.hidden = false;
    overallStaging.hidden = true;
    naturalResetToCalm();
    history.replaceState(null, "", "#expression");
  });
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
  await page.goto(runtimeUrl, { waitUntil: "load", timeout: 30000 });
  await page.locator("#enter-expression").click();
  await page.waitForFunction(() => (
    window.__touchContractState
    && document.body.classList.contains("expression-open")
  ));
  await freezeNonOverallStories(page);
  await initializeOverallRest(page);
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

async function tap(page, type, x, y, pointerId, downMs = 25) {
  await press(page, type, x, y, pointerId);
  await sleep(downMs);
  await release(page, type, x, y, pointerId);
}

async function syntheticRelease(page, type, x, y, pointerId) {
  await pointer(page, type, "pointerup", x, y, pointerId);
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
  await waitForVisibleImages(page);
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
      const pendingNatural = await page.evaluate(() => (
        window.__naturalExpressionContractState()
      ));
      assert(
        pendingNatural.base_affect === "calm"
        && pendingNatural.reaction_phase === "gaze_highlight_lead"
        && pendingNatural.route_count === 0,
        `${id}: first release did not remain orient-only`,
      );
      await sleep(680);
      await waitForVisibleImages(page);
      const committed = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-committed`,
      );
      const traceCount = await page.evaluate(() => (
        window.__v45TouchTrace.filter(
          (row) => row.kind === "single_tap_committed",
        ).length
      ));
      const naturalCommitted = await page.evaluate(() => (
        window.__naturalExpressionContractState()
      ));
      assert(traceCount === 1, `${id}: single tap committed ${traceCount}`);
      assert(
        naturalCommitted.route_count === 1
        && naturalCommitted.bridge?.from === "calm"
        && naturalCommitted.bridge?.to === "curious"
        && naturalCommitted.bridge?.changedFrames === 2,
        `${id}: natural bridge did not commit after discriminator`,
      );
      assert(
        committed.events.kinds.filter(
          (kind) => kind === "pointerdown_consumed",
        ).length === 1
        && committed.events.kinds.filter(
          (kind) => kind === "pointer_release_consumed",
        ).length === 1
        && committed.events.route_enter_ids.length === 0
        && committed.events.route_exit_ids.length === 0,
        `${id}: single tap event consumption`,
      );
      assert(
        committed.contract.recording_entries === 0
        && committed.contract.menu_entries === 0,
        `${id}: single tap activated a route`,
      );
      await sleep(540);
      await waitForVisibleImages(page);
      const settled = assertSnapshot(
        await screenSnapshot(page, true),
        "expression",
        `${id}-settled`,
      );
      const naturalSettled = await page.evaluate(() => (
        window.__naturalExpressionContractState()
      ));
      const routeKinds = naturalSettled.trace
        .filter((row) => row.route_id === "natural-1")
        .map((row) => row.kind);
      assert(
        naturalSettled.base_affect === "curious"
        && naturalSettled.bridge === null
        && routeKinds.join(">")
          === "contextual_edge_selected>brow_reply>lower_face_reply>target_hold"
        && naturalSettled.trace
          .filter((row) => row.route_id === "natural-1" && row.changed_frame)
          .at(-1)?.changed_frame === 3,
        `${id}: natural bridge order/bound is wrong`,
      );
      totals.natural_bridge_commits += 1;
      totals.natural_bridge_ordered += 1;
      await capture(page, `${id}-response`);
      return {
        committed_once: true,
        first_release_orient_only: true,
        gaze_replaced: settled.sources.gaze !== baseline.sources.gaze,
        natural_target: naturalSettled.base_affect,
        ordered_route: routeKinds,
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
      const negativeChecks = [];
      await tap(page, type, x, y, 301, 30);
      await sleep(90);
      await tap(page, type, x + 3, y + 2, 302, 30);
      await page.waitForFunction(() => (
        window.__recordingContractState().phase === "listening_hold"
      ), null, { timeout: 2500 });
      await sleep(520);
      await page.evaluate(() => window.__recordingFreezeWaveStep(3));
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
      assert(
        recording.contract.recording_exits === 0,
        `${id}: recording exited on entry`,
      );
      assert(
        recording.events.kinds.filter(
          (kind) => kind === "pointerdown_consumed",
        ).length === 2
        && recording.events.kinds.filter(
          (kind) => kind === "pointer_release_consumed",
        ).length === 2
        && recording.events.kinds.filter(
          (kind) => kind === "double_tap_pair_consumed",
        ).length === 1
        && recording.events.route_enter_ids.length === 1
        && recording.events.route_exit_ids.length === 0,
        `${id}: recording entry event/route counts`,
      );
      const entryEvidence = await page.evaluate(() => {
        const recording = window.__recordingContractState();
        const trace = window.__touchInteractionTrace;
        const phases = recording.phaseTrace.filter(
          (row) => row.sequence === recording.sequence,
        );
        const cycle = recording.waveTrace.filter(
          (row) => row.sequence === recording.sequence && row.cycle === 0,
        );
        const releaseIds = trace.filter(
          (row) => row.kind === "pointer_release_consumed",
        ).map((row) => row.event_id);
        return {
          consumedPair: recording.consumedPairs.at(-1),
          cycle,
          phases,
          releaseIds,
          singleCommits: window.__v45TouchTrace.filter(
            (row) => row.kind === "single_tap_committed",
          ).length,
        };
      });
      assert(
        entryEvidence.singleCommits === 0,
        `${id}: double tap committed single`,
      );
      assert(
        JSON.stringify(entryEvidence.phases.map((row) => row.phase))
          === JSON.stringify([
            "expression",
            "listening",
            "listening_hold",
          ]),
        `${id}: recording phase order`,
      );
      assert(
        entryEvidence.phases[1].story === "focused_presence"
        && entryEvidence.phases[2].story === "focused_presence"
        && entryEvidence.phases[1].waves_visible
        && entryEvidence.phases[2].waves_visible
        && entryEvidence.phases[2].same_face_as_listening
        && entryEvidence.phases[2].indicator_visible,
        `${id}: stable listening face/indicator sequence`,
      );
      assert(
        entryEvidence.cycle.length >= 4
        && entryEvidence.cycle[0].step === 0
        && entryEvidence.cycle.every((row, index, rows) => (
          index === 0 || row.step === rows[index - 1].step + 1
        ))
        && entryEvidence.cycle.every((row, index, rows) => (
          index === 0
          || row.distance_to_listening_point
            < rows[index - 1].distance_to_listening_point
        )),
        `${id}: inward wave centroid motion`,
      );
      assert(
        JSON.stringify(entryEvidence.consumedPair.release_event_ids)
          === JSON.stringify(entryEvidence.releaseIds),
        `${id}: entry pair event identity`,
      );
      assert(
        recording.microphone_oracle.old_mic_mask_pixels > 0
        && recording.microphone_oracle.current_wave_mask_overlap === 0
        && recording.microphone_oracle.visible_mic_asset_sources === 0,
        `${id}: microphone pixel/source oracle`,
      );
      totals.route_recording_entries += 1;
      totals.recording_ordered_phase_traces += 1;
      totals.recording_wave_cycles += 1;
      await capture(page, `${id}-entry`);
      await page.evaluate(() => window.__recordingResumeWaves());

      const assertNoRecordingToggle = async (label) => {
        await waitForVisibleImages(page);
        await page.evaluate(() => window.__recordingFreezeWaveStep(3));
        const snapshot = assertSnapshot(
          await screenSnapshot(page),
          "recording",
          `${id}-${label}`,
        );
        assert(
          snapshot.recording.entries === 1
          && snapshot.recording.exits === 0
          && snapshot.recording.sequence === 1
          && snapshot.recording.phase === "listening_hold"
          && snapshot.recording.phase_trace.filter(
            (row) => row.sequence === 1,
          ).length === 3
          && snapshot.recording.phase_trace.filter(
            (row) => row.sequence === 1,
          ).slice(1).every((row) => row.story === "focused_presence")
          && snapshot.recording.indicator_nodes === 1
          && snapshot.recording.indicator_visible
          && snapshot.events.route_enter_ids.length === 1
          && snapshot.events.route_exit_ids.length === 0
          && snapshot.contract.menu_entries === 0,
          `${id}-${label}: false toggle or choreography restart`,
        );
        negativeChecks.push({
          event_id: snapshot.events.event_ids.at(-1),
          kind: label,
          route_entries: snapshot.events.route_enter_ids.length,
          route_exits: snapshot.events.route_exit_ids.length,
          sequence: snapshot.recording.sequence,
        });
        totals.recording_negative_checks += 1;
        await page.evaluate(() => window.__recordingResumeWaves());
      };

      await tap(page, type, x, y, 303);
      await sleep(680);
      await assertNoRecordingToggle("single-no-exit");

      await tap(page, type, x, y, 304);
      await sleep(675);
      await tap(page, type, x + 2, y, 305);
      await sleep(680);
      await assertNoRecordingToggle("late-pair-no-exit");

      await tap(page, type, x, y, 306);
      await sleep(80);
      await tap(page, type, x + 50, y, 307);
      await sleep(680);
      await assertNoRecordingToggle("far-pair-no-exit");

      await press(page, type, x, y, 308);
      await sleep(30);
      await move(page, type, x + 60, y, 308);
      await sleep(30);
      await release(page, type, x + 60, y, 308);
      await sleep(80);
      await assertNoRecordingToggle("drag-no-exit");

      await press(page, type, x, y, 309);
      await sleep(730);
      await release(page, type, x, y, 309);
      await sleep(80);
      await assertNoRecordingToggle("hold-no-exit");

      await press(page, type, x, y, 310);
      await sleep(40);
      await page.evaluate((pointerType) => {
        const active = window.__touchContractState().activePointer;
        document.querySelector("#overall-viewport").dispatchEvent(
          new PointerEvent("pointercancel", {
            bubbles: true,
            cancelable: true,
            pointerId: active?.id ?? 310,
            pointerType: active?.type ?? pointerType,
          }),
        );
      }, type);
      if (type === "mouse") {
        await page.mouse.up().catch(() => {});
      }
      await sleep(80);
      await assertNoRecordingToggle("cancel-no-exit");

      await press(page, type, x, y, 311);
      await sleep(40);
      await page.evaluate(() => window.dispatchEvent(new Event("blur")));
      if (type === "mouse") {
        await page.mouse.up().catch(() => {});
      }
      await sleep(80);
      await assertNoRecordingToggle("blur-no-exit");

      await tap(page, type, x, y, 312);
      await syntheticRelease(page, type, x, y, 312);
      await sleep(680);
      await assertNoRecordingToggle("duplicate-release-no-exit");
      const duplicateCount = await page.evaluate(() => (
        window.__touchInteractionTrace.filter(
          (row) => row.kind === "duplicate_release_ignored",
        ).length
      ));
      assert(duplicateCount >= 1, `${id}: duplicate release not observed`);

      await tap(page, type, x, y, 320);
      await sleep(500);
      await tap(page, type, x + 39, y, 321);
      await sleep(80);
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
      assert(
        returned.contract.recording_entries === 1
        && returned.contract.recording_exits === 1
        && returned.events.route_enter_ids.length === 1
        && returned.events.route_exit_ids.length === 1,
        `${id}: recording exit event/route counts`,
      );
      const firstExitEvidence = await page.evaluate(() => {
        const recording = window.__recordingContractState();
        const trace = window.__touchInteractionTrace;
        const pair = recording.consumedPairs.at(-1);
        const releaseIds = trace.filter(
          (row) => row.kind === "pointer_release_consumed",
        ).slice(-2).map((row) => row.event_id);
        return {
          pair,
          releaseIds,
          routeExitIds: trace.filter(
            (row) => row.kind === "recording_route_exit",
          ).map((row) => row.event_id),
        };
      });
      assert(
        firstExitEvidence.pair.action === "exit"
        && JSON.stringify(firstExitEvidence.pair.release_event_ids)
          === JSON.stringify(firstExitEvidence.releaseIds)
        && firstExitEvidence.routeExitIds.length === 1,
        `${id}: exit pair event identity`,
      );
      totals.route_recording_exits += 1;
      await capture(page, `${id}-returned`);

      await tap(page, type, x, y, 330);
      await sleep(500);
      await tap(page, type, x + 39, y, 331);
      await sleep(70);
      await tap(page, type, x + 2, y + 2, 332);
      await page.waitForFunction(() => (
        window.__recordingContractState().phase === "listening_hold"
      ), null, { timeout: 2500 });
      await sleep(680);
      await page.evaluate(() => window.__recordingFreezeWaveStep(3));
      const triple = assertSnapshot(
        await screenSnapshot(page),
        "recording",
        `${id}-triple-no-extra-toggle`,
      );
      assert(
        triple.recording.entries === 2
        && triple.recording.exits === 1
        && triple.recording.sequence === 2
        && triple.recording.phase === "listening_hold"
        && triple.recording.phase_trace.filter(
          (row) => row.sequence === 2,
        ).length === 3
        && triple.recording.phase_trace.filter(
          (row) => row.sequence === 2,
        ).slice(1).every((row) => row.story === "focused_presence")
        && triple.events.route_enter_ids.length === 2
        && triple.events.route_exit_ids.length === 1,
        `${id}: triple input caused an unintended toggle`,
      );
      negativeChecks.push({
        event_id: triple.events.event_ids.at(-1),
        kind: "triple-no-extra-toggle",
        route_entries: triple.events.route_enter_ids.length,
        route_exits: triple.events.route_exit_ids.length,
        sequence: triple.recording.sequence,
      });
      totals.recording_negative_checks += 1;
      totals.recording_ordered_phase_traces += 1;
      totals.recording_reentries += 1;
      totals.route_recording_entries += 1;
      await page.evaluate(() => window.__recordingResumeWaves());

      await tap(page, type, x, y, 340);
      await sleep(90);
      await tap(page, type, x + 3, y + 2, 341);
      await sleep(80);
      await waitForVisibleImages(page);
      const finalReturn = assertSnapshot(
        await screenSnapshot(page),
        "expression",
        `${id}-reentry-returned`,
      );
      assert(
        boolPixelEqual(finalReturn.pixel, baseline.pixel)
        && finalReturn.sources.face === baseline.sources.face
        && finalReturn.sources.gaze === baseline.sources.gaze
        && finalReturn.recording.entries === 2
        && finalReturn.recording.exits === 2
        && finalReturn.events.route_enter_ids.length === 2
        && finalReturn.events.route_exit_ids.length === 2,
        `${id}: re-entry return identity/counts`,
      );
      totals.route_recording_exits += 1;
      return {
        event_ids_unique: true,
        exit_route_activations: 2,
        inward_wave_cycle: entryEvidence.cycle.map((row) => ({
          distance_to_listening_point: row.distance_to_listening_point,
          step: row.step,
        })),
        microphone_requests: recording.media_request_count,
        negative_checks: negativeChecks,
        ordered_phases: entryEvidence.phases.map((row) => row.phase),
        recording_entries: finalReturn.recording.entries,
        recording_exits: finalReturn.recording.exits,
        reentry_count: 1,
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
      await waitForVisibleImages(page);
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
    await session.page.waitForFunction(() => (
      [...document.querySelectorAll(".story-wall .live-viewport img")]
        .filter((image) => !image.hidden && !image.closest("[hidden]"))
        .every((image) => image.complete && image.naturalWidth === 200)
    ), null, { timeout: 12000 });
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
  assert(
    totals.natural_bridge_commits === 6,
    "natural single commits are not 6/6",
  );
  assert(
    totals.natural_bridge_ordered === 6,
    "natural bridge ordering is not 6/6",
  );
  assert(totals.directional_moves === 30, "direction count is not 30");
  assert(totals.route_recording_entries === 12, "recording entries not 12");
  assert(totals.route_recording_exits === 12, "recording exits not 12");
  assert(totals.recording_reentries === 6, "recording reentries not 6");
  assert(
    totals.recording_negative_checks === 54,
    "recording negatives are not 54/54",
  );
  assert(
    totals.recording_ordered_phase_traces === 12,
    "recording phase traces are not 12/12",
  );
  assert(
    totals.recording_wave_cycles === 6,
    "recording inward wave cycles are not 6/6",
  );
  assert(totals.route_menu_entries === 6, "menu count is not 6");
  assert(totals.menu_root_visits === 24, "menu roots are not 24/24");
  assert(
    totals.device_ui_assets_visits === 6,
    "Device > UI assets is not 6/6",
  );
  for (const key of [
    "microphone_requests",
    "mic_glyph_pixel_count",
    "stale_layer_count",
    "stale_pupil_pixel_count",
    "stale_pupil_state_count",
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
    requirements: ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
    schema: "companion.browser-owner-review-screenshots.v3",
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
      microphone_glyph_pixel_count: totals.mic_glyph_pixel_count,
      out_of_bounds_count: totals.out_of_bounds_count,
      outside_black_pixel_count: totals.outside_black_pixel_count,
      primary_screen_count: 1,
      stale_layer_count: totals.stale_layer_count,
      stale_pupil_pixel_count: totals.stale_pupil_pixel_count,
      stale_pupil_state_count: totals.stale_pupil_state_count,
    },
    matrix: matrixRows.sort((a, b) => a.id.localeCompare(b.id)),
    requirements: [
      "COMP-REQ-508",
      "COMP-REQ-518",
      "COMP-REQ-520",
      "COMP-REQ-521",
    ],
    schema: "companion.browser-natural-expression-pixel-dom-route.v1",
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
      successor_page_identity: true,
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
      no_false_recording_toggle_54_of_54: true,
      no_404_overlap_bounds_or_stale: true,
      no_microphone_glyph_pixels: true,
      no_microphone_request: true,
      natural_bridge_ordered_6_of_6: true,
      natural_first_release_orient_6_of_6: true,
      ordered_recording_phases_12_of_12: true,
      recording_double_tap_enter_exit_reenter_6_of_6: true,
      recording_inward_wave_cycle_6_of_6: true,
      route_activation_exactly_once: true,
      single_tap_once_6_of_6: true,
      stale_pupil_oracle_all_expression_states: true,
    },
    page: {
      accepted_sha256: acceptedPageSha256,
      observed_sha256: fileSha256(pagePath),
      repo_path: pageRepoPath,
      runtime_url: runtimeUrl,
      url: overallUrl,
    },
    requirements: [
      "COMP-REQ-440",
      "COMP-REQ-441",
      "COMP-REQ-442",
      "COMP-REQ-471",
      "COMP-REQ-508",
      "COMP-REQ-509",
      "COMP-REQ-510",
      "COMP-REQ-518",
      "COMP-REQ-520",
      "COMP-REQ-521",
    ],
    runtime: {
      browser: "chromium",
      browser_version: browserVersion,
      playwright_module_path: playwright.modulePath,
      playwright_package_sha256: playwright.packageSha256,
      playwright_version: playwright.version,
    },
    schema: "companion.browser-natural-expression-replay.v1",
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
    status: "PASS_BROWSER_NATURAL_EXPRESSION_MACHINE_REPLAY",
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
