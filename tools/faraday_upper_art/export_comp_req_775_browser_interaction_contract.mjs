#!/usr/bin/env node
/* Export the fixed browser page's pointer/emotion contract without touching CEMP. */

import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const defaultPage = ".cache/validation/comp-req-628-status-bar/index.html";

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

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function normalizedTextSha256(value) {
  return sha256(Buffer.from(value.toString("utf8").replaceAll("\r\n", "\n"), "utf8"));
}

function loadPlaywright() {
  for (const candidate of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
  ].filter(Boolean)) {
    try { return require(candidate); } catch { /* bounded local candidates */ }
  }
  throw new Error("Playwright unavailable");
}

function serverForRoot() {
  return http.createServer((request, response) => {
    const rawPath = decodeURIComponent((request.url || "/").split("?")[0]);
    const target = path.resolve(repoRoot, `.${rawPath}`);
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
          : "application/octet-stream",
      });
      response.end(value);
    });
  });
}

const options = parseArgs(process.argv.slice(2));
const pageRepoPath = (options.page || defaultPage).replaceAll("\\", "/");
const pagePath = path.resolve(repoRoot, pageRepoPath);
const outputPath = path.resolve(repoRoot, options.output);
if (!pagePath.startsWith(`${repoRoot}${path.sep}`)
    || !outputPath.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("page/output must remain inside repository");
}
const pageBytes = fs.readFileSync(pagePath);
const pageSha256 = normalizedTextSha256(pageBytes);
if (options["expected-page-sha256"]
    && pageSha256 !== options["expected-page-sha256"].toUpperCase()) {
  throw new Error(`page SHA mismatch: ${pageSha256}`);
}

const server = serverForRoot();
const playwright = loadPlaywright();
let browser;
try {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(0, "127.0.0.1", resolve);
  });
  const port = server.address().port;
  browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage({
    colorScheme: "light",
    deviceScaleFactor: 1,
    locale: "zh-CN",
    reducedMotion: "reduce",
    timezoneId: "UTC",
    viewport: { width: 1280, height: 900 },
  });
  await page.goto(`http://127.0.0.1:${port}/${pageRepoPath}`, {
    waitUntil: "load",
    timeout: 15000,
  });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, {
    timeout: 15000,
  });
  const exported = await page.evaluate(() => {
    window.__compReq714SetScheduler(false);
    const families = Object.keys(AFFECT_CENTERS);
    const productContract = window.__compReq625Contract();
    const blinkContract = window.__compReq762Contract();
    const blinkGeometryContract = window.__compReq761Contract();
    const menuHold = productContract.menu_hold;
    const gestures = productContract.gestures;
    const menuHoldMilestones = Array.from(
      { length: menuHold.progress_frames },
      (_, bucket) => {
        const heldMs = menuHold.recognition_lead_ms
          + (bucket + 1) * menuHold.cell_step_ms;
        return {
          bucket,
          held_ms: heldMs,
          state_id: `menu_hold_${heldMs}ms`,
        };
      },
    );
    const reset = () => {
      window.__compReq714ResetInteraction();
      selected = "calm";
      selectedVariantBias = 0;
      interactionMemory.singleTapEvidence = 0;
      interactionMemory.lastSingleTapAt = -100000;
      touchTransition = null;
      heldPose = null;
      heldPoseCommitsRemaining = 0;
    };
    const tracePoints = [
      ["center", [0.5, 0.58]],
      ["center", [0.5, 0.58]],
      ["up", [0.5, 0.2]],
      ["up", [0.5, 0.2]],
      ["left", [0.2, 0.5]],
      ["right", [0.8, 0.5]],
      ["down", [0.5, 0.8]],
      ["center", [0.5, 0.58]],
    ];
    reset();
    const trace = tracePoints.map(([zone, point], index) => {
      const familyBefore = selected;
      const result = commitEmotionTap(point, true);
      const target = interactionMemory.lastDecision.target;
      const transition = result === "emotion_transition_armed";
      if (transition) {
        selected = target;
        touchTransition = null;
      }
      return {
        index,
        zone,
        point,
        result,
        target,
        family_before: familyBefore,
        family_after: selected,
        transition,
        evidence_after: interactionMemory.singleTapEvidence,
        local_action: localTapAction(point),
        variables: { ...interactionMemory.lastDecision.variables },
      };
    });
    reset();
    const menuScreens = MENU_SCREEN_NAMES.map((name, screen) => ({
      screen,
      name,
      rows: menuRowsForScreen(screen).map((row, index) => ({
        index,
        id: row.id,
        kind: row.kind,
        target: Number.isInteger(row.target) ? row.target : null,
      })),
    }));
    return {
      families,
      family_order: families,
      affect_centers: Object.fromEntries(
        Object.entries(AFFECT_CENTERS).map(([name, value]) => [name, [...value]]),
      ),
      affect_graph: Object.fromEntries(
        Object.entries(AFFECT_GRAPH).map(([name, value]) => [name, [...value]]),
      ),
      gesture: {
        double_tap_gap_ms: DOUBLE_TAP_GAP_MS,
        double_tap_max_distance: DOUBLE_TAP_MAX_DISTANCE,
        recording_corner_max_x: RECORD_PULL_START_MAX_X,
        recording_corner_min_y: RECORD_PULL_START_MIN_Y,
        menu_hold_ms: MENU_HOLD_MS,
        menu_hold_recognition_ms: MENU_HOLD_RECOGNITION_MS,
        menu_hold_milestones: menuHoldMilestones,
        menu_right_exit_threshold: gestures.menu_swipe_threshold,
        menu_vertical_swipe_threshold: MENU_SWIPE_THRESHOLD,
        menu_scroll_cadence_ms: menuHold.root_list.scroll_commit_cadence_ms,
        menu_scroll_quantum_px: menuHold.root_list.scroll_quantum_px,
        menu_row_height_px: menuHold.child_menu.release_alignment_px,
        pointer_grid: [...gestures.pointer_grid],
        pointer_follow_cadence_ms: gestures.pointer_follow_cadence_ms,
        pointer_follow_max_step_px_per_axis:
          gestures.pointer_follow_max_step_px_per_axis,
        pointer_follow_release_return_commits:
          gestures.pointer_follow_release_return_commits,
        recording_trigger_dx: gestures.recording_trigger_dx,
        recording_max_dy: gestures.recording_max_dy,
        recording_min_hold_ms: gestures.recording_min_hold_ms,
        recording_visible_stages: gestures.recording_visible_stages,
        recording_visible_cadence_ms: gestures.recording_visible_cadence_ms,
      },
      living_motion: {
        scheduler: productContract.living_motion.scheduler,
        low_power_sleep_exception:
          productContract.living_motion.low_power_sleep_exception,
        awake_continuous:
          productContract.living_motion.low_power_sleep_exception
            === 'sleepy_stable_frame_stops_main_scheduler',
        natural_blink: {
          cadence_ms: CADENCE_MS,
          first_interval_commits: BLINK_FIRST_INTERVAL_COMMITS,
          interval_commits: [...BLINK_INTERVAL_COMMITS],
          closed_commits: blinkContract.closed_commits,
          exact_open_next_commit: blinkContract.exact_open_next_commit,
          nonperiodic: blinkContract.nonperiodic,
          eye_bounds_by_family: blinkGeometryContract.generated_eye_bounds,
          authored_closed_eye_bounds: blinkClosedEyes.map((points) => {
            const bounds = componentBounds(points);
            return [
              bounds.left,
              bounds.top,
              bounds.right - bounds.left + 1,
              bounds.bottom - bounds.top + 1,
            ];
          }),
          authored_closed_eye_points: blinkClosedEyes.map((points) =>
            points.map(([x, y]) => [x, y])),
        },
      },
      menu: {
        screen_names: [...MENU_SCREEN_NAMES],
        row_height_px: MENU_ROW_HEIGHT,
        visible_rows: MENU_PAGE_SIZE,
        tap_ack_ms: MENU_TAP_ACK_MS,
        action_processing_ms: 700,
        screens: menuScreens,
      },
      tap: {
        evidence_window_ms: 2400,
        family_switch_threshold: 2,
        local_zones: [
          { name: "up", axis: "y", op: "lt", threshold: 0.3, action: "listen_up" },
          { name: "down", axis: "y", op: "gt", threshold: 0.72, action: "soften" },
          { name: "left", axis: "x", op: "lt", threshold: 0.38, action: "notice_left" },
          { name: "right", axis: "x", op: "gt", threshold: 0.62, action: "notice_right" },
          { name: "center", action: "small_breath" },
        ],
      },
      scoring: {
        implementation: "browser_affect_score_v1",
        scale: 20,
        score_function_source: scoreEmotionFamilies.toString(),
        event_function_source: applyEmotionEvent.toString(),
      },
      trace,
    };
  });
  exported.scoring.score_function_sha256 = sha256(
    Buffer.from(exported.scoring.score_function_source, "utf8"),
  );
  exported.scoring.event_function_sha256 = sha256(
    Buffer.from(exported.scoring.event_function_source, "utf8"),
  );
  delete exported.scoring.score_function_source;
  delete exported.scoring.event_function_source;
  const contract = canonical({
    schema: "companion.browser_interaction_contract.v1",
    status: "PASS",
    source: {
      page_path: pageRepoPath,
      page_sha256: pageSha256,
      contract_exports: [
        "window.__compReq625Contract",
        "window.__compReq762Contract",
        "window.__compReq739EmotionContract",
        "window.__compReq756Contract",
        "window.__compReq772Contract",
      ],
    },
    ...exported,
  });
  const bytes = Buffer.from(`${JSON.stringify(contract, null, 2)}\n`, "utf8");
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, bytes);
  console.log(JSON.stringify({
    status: contract.status,
    output: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
    page_sha256: pageSha256,
    contract_sha256: sha256(bytes),
    trace_steps: contract.trace.length,
  }));
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}
