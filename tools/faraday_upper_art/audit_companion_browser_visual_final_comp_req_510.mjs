#!/usr/bin/env node
/* Final owner-facing visual audit for the COMP-REQ-508/509/510 successor. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const scriptPath = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(scriptPath), "../..");
const outputRoot = path.join(
  repoRoot,
  "docs/validation/companion-browser-visual-final-audit-comp-req-510",
);
const screenshotRoot = path.join(outputRoot, "screenshots");
const artifactPath = path.join(outputRoot, "visual-final-audit.json");
const staleOraclePath = path.join(outputRoot, "stale-gaze-final.json");
const pageRepoPath = [
  "docs/art/iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
].join("/");
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));
const machineReadyPath = path.join(
  repoRoot,
  "docs/validation/companion-browser-owner-review-ready-comp-req-508",
  "MACHINE_READY.json",
);
const replayPath = path.join(
  repoRoot,
  "docs/validation/companion-browser-owner-review-ready-comp-req-508",
  "browser-replay-result.json",
);
const pixelDomRoutePath = path.join(
  repoRoot,
  "docs/validation/companion-browser-owner-review-ready-comp-req-508",
  "pixel-dom-route-artifact.json",
);
const overallUrl = `http://127.0.0.1:4173/${pageRepoPath}`;
const expected = {
  machine_ready_sha256:
    "94962CA64121D0BBE9BF69D45BAA6D20D4EEE4B54C8C7F6CB8868C69DB6BA911",
  page_sha256:
    "9990C4316AF8F4D656F2C2B057AB789846A10CD21E18367336FC6BD277631EB7",
  pixel_dom_route_sha256:
    "91E6793F01B8368933E61115E93AD7280B435A9A1429D4B2DE743B61878BD1F3",
  replay_sha256:
    "8FCAD0AC4C5370EFBBBC6C3785B6E115AA1E77C69EA81C0E137207AC1D33721C",
};

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

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
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
        module_path: path.dirname(packagePath).replaceAll("\\", "/"),
        package_sha256: fileSha256(packagePath),
        version: JSON.parse(fs.readFileSync(packagePath, "utf8")).version,
      };
    } catch (error) {
      errors.push(`${candidate}:${error.message}`);
    }
  }
  throw new Error(`Playwright unavailable: ${errors.join(" | ")}`);
}

async function waitForImages(page) {
  await page.waitForFunction(() => {
    const stage = document.querySelector("#overall-viewport");
    return Boolean(
      stage
      && window.__touchContractState
      && [...stage.querySelectorAll("img")]
        .filter((image) => !image.hidden && !image.closest("[hidden]"))
        .every((image) => image.complete && image.naturalWidth === 200),
    );
  }, null, { timeout: 8000 });
  await sleep(50);
}

async function stageBox(page) {
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box && box.width === 200 && box.height === 200, "200x200 stage missing");
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

async function tap(page, type, x, y, pointerId, downMs = 28) {
  await press(page, type, x, y, pointerId);
  await sleep(downMs);
  await release(page, type, x, y, pointerId);
}

async function snapshot(page) {
  return page.evaluate(() => {
    const stage = document.querySelector("#overall-viewport");
    const frame = stage.querySelector(".viewport-frame");
    const gaze = stage.querySelector(".viewport-gaze");
    const waves = stage.querySelector(".recording-waves");
    const menu = stage.querySelector("#integrated-menu");
    const visible = (element) => Boolean(
      element && !element.hidden && !element.closest("[hidden]"),
    );
    const state = window.__touchContractState();
    const recording = window.__recordingContractState();
    const canvas = window.__touchContractSnapshot();
    const rect = stage.getBoundingClientRect();
    const visibleDebugText = [...document.querySelectorAll(
      ".decision-panel,.screen-meta,.gesture-status,.emotion-rule,.authority-source",
    )].filter((element) => {
      const style = getComputedStyle(element);
      return (
        style.display !== "none"
        && style.visibility !== "hidden"
        && element.getClientRects().length > 0
      );
    }).map((element) => element.textContent.trim()).filter(Boolean);
    const trace = window.__touchInteractionTrace.map((row) => ({ ...row }));
    return {
      canvas: {
        ink: canvas.canvasInk,
        signature: canvas.canvasSignature,
      },
      contract: state,
      dom: {
        frame_nodes: stage.querySelectorAll(".viewport-frame").length,
        gaze_nodes: stage.querySelectorAll(".viewport-gaze").length,
        main_200x200_surfaces: document.querySelectorAll(
          "#overall-viewport.live-viewport",
        ).length,
        menu_visible: visible(menu),
        recording_wave_nodes: stage.querySelectorAll(
          ".recording-waves",
        ).length,
        visible_debug_text: visibleDebugText,
        visible_frame_nodes: visible(frame) ? 1 : 0,
        visible_gaze_nodes: visible(gaze) ? 1 : 0,
        visible_wave_nodes: visible(waves) ? 1 : 0,
      },
      recording,
      route: {
        hash: location.hash,
        recording_entry_ids: trace.filter(
          (row) => row.kind === "recording_route_enter",
        ).map((row) => row.event_id),
        recording_exit_ids: trace.filter(
          (row) => row.kind === "recording_route_exit",
        ).map((row) => row.event_id),
      },
      sources: {
        frame: frame.getAttribute("src"),
        frame_gaze_cleared: frame.dataset.gazeCleared === "true",
        gaze: gaze.getAttribute("src"),
        gaze_transform: getComputedStyle(gaze).transform,
      },
      stage: {
        height: rect.height,
        left: rect.left,
        top: rect.top,
        width: rect.width,
      },
      trace,
    };
  });
}

async function capture(page, viewport, id, kind = "stage") {
  const name = `${viewport}-${id}.png`;
  const target = path.join(screenshotRoot, name);
  if (kind === "layout") {
    await page.screenshot({ path: target, fullPage: false });
  } else {
    const box = await stageBox(page);
    await page.screenshot({
      path: target,
      clip: {
        height: 200,
        width: 200,
        x: Math.floor(box.x),
        y: Math.floor(box.y),
      },
    });
  }
  return {
    bytes: fs.statSync(target).size,
    id,
    kind,
    path: path.relative(repoRoot, target).replaceAll("\\", "/"),
    sha256: fileSha256(target),
    viewport,
  };
}

async function cancelPointer(page, type, pointerId) {
  await page.evaluate(({ type, pointerId }) => {
    const active = window.__touchContractState().activePointer;
    document.querySelector("#overall-viewport").dispatchEvent(
      new PointerEvent("pointercancel", {
        bubbles: true,
        cancelable: true,
        pointerId: active?.id ?? pointerId,
        pointerType: active?.type ?? type,
      }),
    );
  }, { pointerId, type });
  if (type === "mouse") {
    await page.mouse.up().catch(() => {});
  }
}

async function assertExpressionNoRecording(page, label) {
  const current = await snapshot(page);
  assert(current.contract.mode === "expression", `${label}: left expression`);
  assert(current.recording.entries === 0, `${label}: false recording entry`);
  assert(
    current.route.recording_entry_ids.length === 0,
    `${label}: false recording route`,
  );
  return {
    label,
    mode: current.contract.mode,
    recording_entries: current.recording.entries,
    route_entries: current.route.recording_entry_ids.length,
  };
}

async function runViewport(browser, config, screenshotRows) {
  const errors = [];
  let documentRequests = 0;
  const context = await browser.newContext({
    colorScheme: "light",
    deviceScaleFactor: 1,
    hasTouch: config.pointer_type === "touch",
    isMobile: config.pointer_type === "touch",
    locale: "en-US",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: config.viewport,
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
      navigator.mediaDevices.getUserMedia = (...args) => {
        window.__ownerMediaRequestCount += 1;
        return original(...args);
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
  page.on("request", (request) => {
    if (request.resourceType() === "document") {
      documentRequests += 1;
    }
  });
  await page.goto(overallUrl, { waitUntil: "load", timeout: 15000 });
  await page.locator("#enter-expression").click();
  await page.waitForFunction(() => (
    window.__touchContractState
    && document.body.classList.contains("expression-open")
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
    returnToExpression();
  });
  await waitForImages(page);

  const box = await stageBox(page);
  const at = (x, y) => ({ x: box.x + x, y: box.y + y });
  const center = at(100, 100);
  const type = config.pointer_type;
  let pointerId = type === "mouse" ? 1 : 1000;
  const nextId = () => {
    pointerId += 1;
    return pointerId;
  };
  const negativeChecks = [];

  await tap(page, type, center.x, center.y, nextId());
  await sleep(710);
  negativeChecks.push(
    await assertExpressionNoRecording(page, `${config.name}-single`),
  );

  await tap(page, type, center.x, center.y, nextId());
  await sleep(675);
  await tap(page, type, center.x + 2, center.y, nextId());
  await sleep(710);
  negativeChecks.push(
    await assertExpressionNoRecording(page, `${config.name}-late`),
  );

  await tap(page, type, center.x, center.y, nextId());
  await sleep(110);
  await tap(page, type, center.x + 50, center.y, nextId());
  await sleep(710);
  negativeChecks.push(
    await assertExpressionNoRecording(page, `${config.name}-far`),
  );

  const dragId = nextId();
  await press(page, type, center.x, center.y, dragId);
  await sleep(45);
  await move(page, type, center.x + 62, center.y, dragId);
  await sleep(45);
  await release(page, type, center.x + 62, center.y, dragId);
  await sleep(120);
  negativeChecks.push(
    await assertExpressionNoRecording(page, `${config.name}-drag`),
  );

  const cancelId = nextId();
  await press(page, type, center.x, center.y, cancelId);
  await sleep(45);
  await cancelPointer(page, type, cancelId);
  await sleep(120);
  negativeChecks.push(
    await assertExpressionNoRecording(page, `${config.name}-cancel`),
  );

  const holdId = nextId();
  await press(page, type, center.x, center.y, holdId);
  await sleep(740);
  await release(page, type, center.x, center.y, holdId);
  await sleep(100);
  let current = await snapshot(page);
  assert(current.contract.mode === "menu", `${config.name}: hold missed menu`);
  assert(current.recording.entries === 0, `${config.name}: hold entered recording`);
  negativeChecks.push({
    label: `${config.name}-hold-menu-only`,
    menu_entries: current.contract.menuEntries,
    mode: current.contract.mode,
    recording_entries: current.recording.entries,
  });
  await page.locator('[data-testid="integrated-menu-return"]').click();
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "expression"
  ));
  await waitForImages(page);

  screenshotRows.push(
    await capture(page, config.name, "layout", "layout"),
  );
  const restShot = await capture(page, config.name, "rest");
  screenshotRows.push(restShot);

  const visualDragId = nextId();
  await press(page, type, center.x, center.y, visualDragId);
  await sleep(55);
  await move(page, type, box.x + 172, center.y, visualDragId);
  await sleep(95);
  const dragRight = await snapshot(page);
  screenshotRows.push(
    await capture(page, config.name, "drag-right"),
  );
  await move(page, type, center.x, center.y, visualDragId);
  await sleep(95);
  const dragCenter = await snapshot(page);
  screenshotRows.push(
    await capture(page, config.name, "drag-center"),
  );
  await release(page, type, center.x, center.y, visualDragId);
  await sleep(110);
  const dragReleased = await snapshot(page);
  assert(
    dragRight.sources.frame_gaze_cleared
    && dragCenter.sources.frame_gaze_cleared,
    `${config.name}: drag did not use gaze-cleared base`,
  );
  assert(
    dragRight.sources.gaze !== dragCenter.sources.gaze,
    `${config.name}: gaze source did not replace`,
  );

  const preRecording = await snapshot(page);
  const preShot = await capture(page, config.name, "pre-recording");
  screenshotRows.push(preShot);
  await tap(page, type, center.x, center.y, nextId());
  await sleep(120);
  await tap(page, type, center.x + 4, center.y + 3, nextId());
  await page.waitForFunction(() => (
    window.__recordingContractState().phase === "listening"
  ), null, { timeout: 2000 });
  await sleep(70);
  const listening = await snapshot(page);
  screenshotRows.push(
    await capture(page, config.name, "listening"),
  );
  await page.waitForFunction(() => (
    window.__recordingContractState().phase === "thoughtful_listening"
  ), null, { timeout: 2000 });
  await page.waitForFunction(() => {
    const recording = window.__recordingContractState();
    return recording.waveTrace.filter(
      (row) => row.sequence === recording.sequence && row.cycle === 0,
    ).some((row) => row.step === 3);
  }, null, { timeout: 2000 });
  const thoughtful = await snapshot(page);
  screenshotRows.push(
    await capture(page, config.name, "thoughtful-listening"),
  );

  await tap(page, type, center.x, center.y, nextId());
  await sleep(710);
  const recordingSingle = await snapshot(page);
  assert(
    recordingSingle.contract.mode === "recording"
    && recordingSingle.recording.exits === 0,
    `${config.name}: recording single tap falsely exited`,
  );
  const recordingDragId = nextId();
  await press(page, type, center.x, center.y, recordingDragId);
  await sleep(45);
  await move(page, type, center.x + 62, center.y, recordingDragId);
  await sleep(45);
  await release(page, type, center.x + 62, center.y, recordingDragId);
  await sleep(120);
  const recordingDrag = await snapshot(page);
  assert(
    recordingDrag.contract.mode === "recording"
    && recordingDrag.recording.exits === 0,
    `${config.name}: recording drag falsely exited`,
  );

  await tap(page, type, center.x, center.y, nextId());
  await sleep(120);
  await tap(page, type, center.x + 4, center.y + 3, nextId());
  await page.waitForFunction(() => (
    window.__touchContractState().mode === "expression"
  ), null, { timeout: 2000 });
  await waitForImages(page);
  const restored = await snapshot(page);
  const restoredShot = await capture(page, config.name, "restored");
  screenshotRows.push(restoredShot);

  const sequence = thoughtful.recording.sequence;
  const waveCycle = thoughtful.recording.waveTrace.filter(
    (row) => row.sequence === sequence && row.cycle === 0,
  );
  const waveSteps = [...new Map(
    waveCycle.map((row) => [row.step, row]),
  ).values()].sort((left, right) => left.step - right.step);
  assert(
    waveSteps.length === 4
    && waveSteps.every((row, index) => (
      index === 0
      || row.distance_to_listening_point
        < waveSteps[index - 1].distance_to_listening_point
    )),
    `${config.name}: wave centroids did not move inward`,
  );
  const phaseTrace = thoughtful.recording.phaseTrace
    .filter((row) => row.sequence === sequence)
    .map((row) => row.phase);
  assert(
    JSON.stringify(phaseTrace)
      === JSON.stringify(["expression", "listening", "thoughtful_listening"]),
    `${config.name}: recording phase order`,
  );
  const finalPhaseTrace = restored.recording.phaseTrace
    .filter((row) => row.sequence === sequence)
    .map((row) => row.phase);
  assert(
    JSON.stringify(finalPhaseTrace) === JSON.stringify([
      "expression",
      "listening",
      "thoughtful_listening",
      "expression",
    ]),
    `${config.name}: restored phase order`,
  );
  assert(
    restored.canvas.signature === preRecording.canvas.signature
    && restored.canvas.ink === preRecording.canvas.ink
    && restored.sources.frame === preRecording.sources.frame
    && restored.sources.gaze === preRecording.sources.gaze
    && restored.sources.gaze_transform === preRecording.sources.gaze_transform,
    `${config.name}: pre-recording state was not restored exactly`,
  );
  assert(
    restoredShot.sha256 === preShot.sha256,
    `${config.name}: restored screenshot differs from pre-recording`,
  );

  const allStates = [
    dragRight,
    dragCenter,
    dragReleased,
    listening,
    thoughtful,
    restored,
  ];
  assert(
    allStates.every((row) => (
      row.dom.main_200x200_surfaces === 1
      && row.dom.frame_nodes === 1
      && row.dom.gaze_nodes === 1
      && row.dom.recording_wave_nodes === 1
      && row.dom.visible_frame_nodes === 1
      && row.dom.visible_gaze_nodes === 1
      && row.dom.visible_debug_text.length === 0
      && row.stage.width === 200
      && row.stage.height === 200
    )),
    `${config.name}: layer/layout/debug invariant`,
  );
  assert(
    listening.dom.visible_wave_nodes === 1
    && thoughtful.dom.visible_wave_nodes === 1
    && restored.dom.visible_wave_nodes === 0,
    `${config.name}: wave visibility invariant`,
  );
  assert(
    !listening.recording.micGlyphPresent
    && !thoughtful.recording.micGlyphPresent,
    `${config.name}: microphone glyph present`,
  );
  assert(
    listening.recording.entries === 1
    && thoughtful.recording.entries === 1
    && restored.recording.entries === 1
    && restored.recording.exits === 1
    && restored.route.recording_entry_ids.length === 1
    && restored.route.recording_exit_ids.length === 1,
    `${config.name}: recording route count`,
  );
  const mediaRequests = await page.evaluate(() => (
    window.__ownerMediaRequestCount
  ));
  assert(mediaRequests === 0, `${config.name}: microphone requested`);
  assert(documentRequests === 1, `${config.name}: route duplicated`);
  assert(errors.length === 0, `${config.name}: ${errors.join(" | ")}`);

  const row = {
    checks: {
      double_tap_entry_exactly_once: listening.recording.entries === 1,
      double_tap_exit_exactly_once: restored.recording.exits === 1,
      drag_atomic_cleared_base: (
        dragRight.sources.frame_gaze_cleared
        && dragCenter.sources.frame_gaze_cleared
      ),
      exact_pre_recording_restore: restoredShot.sha256 === preShot.sha256,
      inward_wave_centroids: true,
      no_false_entry: negativeChecks.every(
        (check) => check.recording_entries === 0,
      ),
      no_false_exit: (
        recordingSingle.recording.exits === 0
        && recordingDrag.recording.exits === 0
      ),
      no_microphone_glyph_or_request: mediaRequests === 0,
      one_face_one_gaze: true,
      ordered_choreography: true,
    },
    document_requests: documentRequests,
    errors,
    name: config.name,
    negative_checks: negativeChecks,
    phase_trace: finalPhaseTrace,
    pointer_type: type,
    recording_event_ids: {
      entry: restored.route.recording_entry_ids,
      exit: restored.route.recording_exit_ids,
    },
    restore: {
      canvas_signature: restored.canvas.signature,
      screenshot_sha256: restoredShot.sha256,
      source_identity_equal: true,
    },
    wave_centroids: waveSteps.map((entry) => ({
      centroid: entry.centroid,
      distance_to_listening_point: entry.distance_to_listening_point,
      step: entry.step,
    })),
  };
  await context.close();
  return row;
}

fs.mkdirSync(screenshotRoot, { recursive: true });
const observed = {
  machine_ready_sha256: fileSha256(machineReadyPath),
  page_sha256: fileSha256(pagePath),
  pixel_dom_route_sha256: fileSha256(pixelDomRoutePath),
  replay_sha256: fileSha256(replayPath),
};
assert(
  JSON.stringify(observed) === JSON.stringify(expected),
  `accepted source identity drift: ${JSON.stringify(observed)}`,
);
assert(fs.existsSync(staleOraclePath), "fresh stale-gaze oracle is missing");
const staleOracle = JSON.parse(fs.readFileSync(staleOraclePath, "utf8"));
assert(staleOracle.status === "PASS", "fresh stale-gaze oracle did not pass");
assert(
  staleOracle.observed_page_sha256 === expected.page_sha256
  && staleOracle.measurement.pixel.stale_center_mask_total === 0,
  "fresh stale-gaze oracle identity/count mismatch",
);

const response = await fetch(overallUrl);
assert(response.status === 200, `4173 returned ${response.status}`);
const responseBytes = Buffer.from(await response.arrayBuffer());
const responseSha256 = sha256(responseBytes);
assert(
  responseSha256 === expected.page_sha256,
  `4173 page drift: ${responseSha256}`,
);

const playwright = loadPlaywright();
const screenshotRows = [];
const viewportRows = [];
let browser;
try {
  browser = await playwright.chromium.launch({ headless: true });
  for (const config of [
    {
      name: "desktop-mouse",
      pointer_type: "mouse",
      viewport: { height: 900, width: 1280 },
    },
    {
      name: "mobile-touch",
      pointer_type: "touch",
      viewport: { height: 852, width: 393 },
    },
  ]) {
    viewportRows.push(await runViewport(browser, config, screenshotRows));
  }
} finally {
  if (browser) {
    await browser.close();
  }
}

const checks = {
  accepted_machine_identity_unchanged:
    observed.machine_ready_sha256 === expected.machine_ready_sha256,
  accepted_page_identity_unchanged:
    observed.page_sha256 === expected.page_sha256,
  all_owner_visible_checks_pass: viewportRows.every(
    (row) => Object.values(row.checks).every(Boolean),
  ),
  desktop_and_mobile_audited: viewportRows.length === 2,
  fresh_stale_pupil_oracle_pass:
    staleOracle.measurement.pixel.stale_center_mask_total === 0,
  no_browser_errors_or_404: viewportRows.every(
    (row) => row.errors.length === 0,
  ),
  no_microphone_request: viewportRows.every(
    (row) => row.checks.no_microphone_glyph_or_request,
  ),
  no_owner_prompt: true,
  runtime_page_matches_source:
    responseSha256 === expected.page_sha256,
  screenshot_groups_complete: screenshotRows.length === 16,
};
assert(Object.values(checks).every(Boolean), "visual-final checks failed");

const artifact = {
  accepted_machine_ready: {
    path: path.relative(repoRoot, machineReadyPath).replaceAll("\\", "/"),
    sha256: observed.machine_ready_sha256,
    status: JSON.parse(fs.readFileSync(machineReadyPath, "utf8")).status,
  },
  checks,
  expected_identities: expected,
  observed_identities: observed,
  owner_boundary: {
    owner_pass_claimed: false,
    owner_prompt_opened: false,
    remaining_gate: "one future owner visual review only",
  },
  page: {
    repo_path: pageRepoPath,
    runtime_response_sha256: responseSha256,
    runtime_status: response.status,
    url: overallUrl,
  },
  playwright: {
    module_path: playwright.module_path,
    package_sha256: playwright.package_sha256,
    version: playwright.version,
  },
  requirement: ["COMP-REQ-508", "COMP-REQ-509", "COMP-REQ-510"],
  schema: "companion.browser-visual-final-audit.v1",
  screenshots: screenshotRows,
  side_effect_counters: {
    browser_process: 1,
    hardware: 0,
    microphone_permission_request: 0,
    owner_prompt: 0,
    page_write: 0,
    production_write: 0,
    server_start: 0,
  },
  stale_gaze_oracle: {
    path: path.relative(repoRoot, staleOraclePath).replaceAll("\\", "/"),
    sha256: fileSha256(staleOraclePath),
    stale_center_mask_left_eye:
      staleOracle.measurement.pixel.stale_center_mask_left_eye,
    stale_center_mask_right_eye:
      staleOracle.measurement.pixel.stale_center_mask_right_eye,
    stale_center_mask_total:
      staleOracle.measurement.pixel.stale_center_mask_total,
    status: staleOracle.status,
  },
  status: "PASS_VISUAL_FINAL_AUDIT_MACHINE_OBSERVED",
  viewports: viewportRows,
};
fs.writeFileSync(artifactPath, canonicalBytes(artifact));
console.log(JSON.stringify({
  artifact_sha256: fileSha256(artifactPath),
  screenshot_count: screenshotRows.length,
  status: artifact.status,
  viewports: viewportRows.map((row) => row.name),
}));
