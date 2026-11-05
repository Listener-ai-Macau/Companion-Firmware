#!/usr/bin/env node
/* Export the current browser renderer into a deterministic STM32 frame pack. */

import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const defaultPage = ".cache/validation/comp-req-628-status-bar/index.html";
const startedAtMs = Date.now();

function args(argv) {
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

function jsonBytes(value) {
  return Buffer.from(`${JSON.stringify(canonical(value), null, 2)}\n`, "utf8");
}

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function textSha256(value) {
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
      if (error) { response.writeHead(404).end(); return; }
      const contentType = target.endsWith(".html")
        ? "text/html; charset=utf-8"
        : target.endsWith(".png") ? "image/png" : "application/octet-stream";
      response.writeHead(200, { "content-type": contentType });
      response.end(value);
    });
  });
}

function pbmBytes(packed) {
  return Buffer.concat([Buffer.from("P4\n200 200\n", "ascii"), packed]);
}

/*
 * The browser renderer authors a complete 200x200 pose for every life beat.
 * Sending those poses verbatim makes eye, brow, mouth and ornament pixels all
 * change on the same SSD1681 activation, which reads as one synchronized face
 * even though the life clock itself is independent from the recording wave.
 *
 * Keep the authored targets, but reveal their component groups on separate
 * beats.  This is an export-time compositor, so WB55 pays no extra internal
 * Flash/RAM and still commits one ordinary frame through the single BUSY line.
 * Every episode converges to the unmodified authored settle frame.
 */
const LIFE_COMPONENT_REGIONS = Object.freeze({
  brows: Object.freeze({ left: 30, top: 60, right: 175, bottom: 93 }),
  eyes: Object.freeze({ left: 35, top: 93, right: 165, bottom: 145 }),
  lower_face: Object.freeze({ left: 25, top: 145, right: 181, bottom: 190 }),
});
const LIFE_ORNAMENT_SOLO_EPISODE = Object.freeze({
  calm: 0,
  curious: 0,
  delighted: 0,
  warm: 6,
  playful: 0,
  bashful: 2,
  thoughtful: 0,
  focused: 8,
  alert: 0,
});

function packedPixel(bytes, x, y) {
  return (bytes[y * 25 + Math.floor(x / 8)] >> (7 - (x % 8))) & 1;
}

function setPackedPixel(bytes, x, y, value) {
  const offset = y * 25 + Math.floor(x / 8);
  const mask = 1 << (7 - (x % 8));
  if (value) bytes[offset] |= mask;
  else bytes[offset] &= ~mask;
}

function copyPackedWhere(target, source, predicate) {
  for (let y = 0; y < 200; y += 1) {
    for (let x = 0; x < 200; x += 1) {
      if (predicate(x, y)) {
        setPackedPixel(target, x, y, packedPixel(source, x, y));
      }
    }
  }
}

function inRegion(x, y, region) {
  return x >= region.left && x < region.right
    && y >= region.top && y < region.bottom;
}

function inOrnamentRegion(x, y) {
  return y >= 16 && y < 93
    && (y < 60 || x < 36 || x >= 164);
}

function packedMetrics(bytes) {
  let black = 0;
  let minX = 200;
  let minY = 200;
  let maxX = -1;
  let maxY = -1;
  for (let y = 0; y < 200; y += 1) {
    for (let x = 0; x < 200; x += 1) {
      if (!packedPixel(bytes, x, y)) continue;
      black += 1;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x);
      maxY = Math.max(maxY, y);
    }
  }
  return {
    black_pixels: black,
    black_bounds: black ? [minX, minY, maxX, maxY] : null,
  };
}

function componentizeLifeFrames(frames) {
  let previous = null;
  let previousFamily = null;
  let previousEpisode = -1;
  for (const frame of frames) {
    if (frame.kind !== "life") continue;
    const { family, state } = frame;
    /* enter_daily seeks only to authored episodes 0..7, and the autonomous
     * family dwell is 16..28 s.  Twelve componentized episodes therefore
     * cover every entry plus the whole visible family residence.  Preserve
     * the exported long tail byte-for-byte so the 512 KiB generation arena
     * remains within its existing product partition. */
    /* Alternate component-solo episodes with whole-pose authored episodes.
     * This prevents a new five-step metronome from becoming as mechanical as
     * the synchronization it replaces.  Any entry episode 0..7 reaches a
     * component-solo episode within one complete story, while sleepy remains
     * an explicit low-power semantic rather than ordinary autonomous life. */
    const componentizedEpisode = family !== "sleepy"
      && ((state.action_episode < 9 && state.action_episode % 2 === 0)
        || (family === "warm" && state.action_episode === 3))
      && !(family === "playful" && state.action_episode === 6);
    const episodeChanged = family !== previousFamily
      || state.action_episode !== previousEpisode;
    const isEpisodeAnchor = state.life_action === "rest" || episodeChanged;
    const raw = frame.bytes;
    let composed = raw;
    let stage = "episode_anchor";
    if (!componentizedEpisode) {
      composed = raw;
      stage = "authored_long_tail";
    } else if (!isEpisodeAnchor && previous) {
      composed = Buffer.from(previous);
      if (state.phase === "orient") {
        copyPackedWhere(
          composed,
          raw,
          (x, y) => inRegion(x, y, LIFE_COMPONENT_REGIONS.eyes),
        );
        stage = "eyes_lead";
      } else if (state.phase === "anticipate") {
        copyPackedWhere(
          composed,
          raw,
          (x, y) => inRegion(x, y, LIFE_COMPONENT_REGIONS.brows),
        );
        stage = "brows_reply";
      } else if (state.phase === "accent") {
        copyPackedWhere(
          composed,
          raw,
          (x, y) => inRegion(x, y, LIFE_COMPONENT_REGIONS.lower_face),
        );
        stage = "lower_face_reply";
      } else if (state.phase === "follow") {
        if (state.action_episode === LIFE_ORNAMENT_SOLO_EPISODE[family]) {
          copyPackedWhere(
            composed,
            raw,
            (x, y) => inOrnamentRegion(x, y),
          );
          stage = "ornament_follow";
        } else {
          stage = "component_hold";
        }
      } else {
        composed = raw;
        stage = "authored_settle";
      }
    }
    const metrics = packedMetrics(composed);
    frame.bytes = composed;
    frame.black_pixels = metrics.black_pixels;
    frame.black_bounds = metrics.black_bounds;
    frame.component_stage = stage;
    previous = composed;
    previousFamily = family;
    previousEpisode = state.action_episode;
  }
}

function cIdentifier(value) {
  return value.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
}

function headerBytes(states, uniqueCount) {
  const lines = [
    "#ifndef COMP_REQ_628_SOURCE_PACK_H",
    "#define COMP_REQ_628_SOURCE_PACK_H",
    "",
    "#include <stdint.h>",
    "",
    "#ifndef COMP_REQ_628_SOURCE_PACK_ENABLED",
    "#define COMP_REQ_628_SOURCE_PACK_ENABLED 0",
    "#endif",
    "",
    "#define COMP_REQ_628_WIDTH 200",
    "#define COMP_REQ_628_HEIGHT 200",
    "#define COMP_REQ_628_STRIDE_BYTES 25",
    "#define COMP_REQ_628_FRAME_BYTES 5000",
    `#define COMP_REQ_628_STATE_COUNT ${states.length}`,
    `#define COMP_REQ_628_UNIQUE_FRAME_COUNT ${uniqueCount}`,
    "",
    "typedef enum {",
  ];
  states.forEach((state, index) => {
    lines.push(`  COMP_REQ_628_STATE_${cIdentifier(state.id)} = ${index},`);
  });
  lines.push(
    "} comp_req_628_state_t;",
    "",
    "#if COMP_REQ_628_SOURCE_PACK_ENABLED",
    "extern const uint8_t comp_req_628_unique_frames",
    "  [COMP_REQ_628_UNIQUE_FRAME_COUNT][COMP_REQ_628_FRAME_BYTES];",
    "extern const uint16_t comp_req_628_state_to_unique",
    "  [COMP_REQ_628_STATE_COUNT];",
    "#endif",
    "",
    "#endif",
    "",
  );
  return Buffer.from(lines.join("\n"), "ascii");
}

function sourceBytes(uniqueFrames, states) {
  const lines = [
    '#include "comp_req_628_source_pack.h"',
    "",
    "#if COMP_REQ_628_SOURCE_PACK_ENABLED",
    `const uint8_t comp_req_628_unique_frames[${uniqueFrames.length}][COMP_REQ_628_FRAME_BYTES] = {`,
  ];
  for (const frame of uniqueFrames) {
    lines.push(`  { /* ${frame.sha256} */`);
    for (let offset = 0; offset < frame.bytes.length; offset += 16) {
      lines.push(`    ${[...frame.bytes.subarray(offset, offset + 16)]
        .map((value) => `0x${value.toString(16).padStart(2, "0")}`).join(", ")},`);
    }
    lines.push("  },");
  }
  lines.push("};", "", `const uint16_t comp_req_628_state_to_unique[${states.length}] = {`);
  for (const state of states) lines.push(`  ${state.unique_frame_index}, /* ${state.id} */`);
  lines.push("};", "#endif", "");
  return Buffer.from(lines.join("\n"), "ascii");
}

const options = args(process.argv.slice(2));
const pointerFollowOption = options["pointer-follow"] || "true";
if (!["true", "false"].includes(pointerFollowOption)) {
  throw new Error("--pointer-follow must be true or false");
}
const includePointerFollow = pointerFollowOption === "true";
const pageRepoPath = options.page || defaultPage;
const knownFamilies = ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"];
const lifeEpisodeCounts = new Map();
if (options["life-families"]) {
  const lifeEpisodes = Number(options["life-episodes"] || 0);
  if (!Number.isInteger(lifeEpisodes) || lifeEpisodes < 1 || lifeEpisodes > 64) {
    throw new Error("--life-episodes must be an integer from 1 through 64");
  }
  for (const family of options["life-families"].split(",").filter(Boolean)) {
    if (!knownFamilies.includes(family)) {
      throw new Error(`unknown --life-families entry: ${family}`);
    }
    lifeEpisodeCounts.set(family, lifeEpisodes);
  }
} else {
  for (const [family, option] of [
    ["calm", "calm-life-episodes"],
    ["curious", "curious-life-episodes"],
    ["delighted", "delighted-life-episodes"],
    ["warm", "warm-life-episodes"],
    ["playful", "playful-life-episodes"],
    ["sleepy", "sleepy-life-episodes"],
    ["bashful", "bashful-life-episodes"],
    ["thoughtful", "thoughtful-life-episodes"],
    ["focused", "focused-life-episodes"],
    ["alert", "alert-life-episodes"],
  ]) {
    const count = Number(options[option] || 0);
    if (!Number.isInteger(count) || count < 0 || count > 64) {
      throw new Error(`--${option} must be an integer from 0 through 64`);
    }
    if (count) lifeEpisodeCounts.set(family, count);
  }
}
const pagePath = path.resolve(repoRoot, pageRepoPath);
const outputRoot = path.resolve(repoRoot, options.output);
if (!pagePath.startsWith(`${repoRoot}${path.sep}`) || !outputRoot.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("page/output must remain inside repository");
}
const pageBytes = fs.readFileSync(pagePath);
const pageSha256 = textSha256(pageBytes);
if (options["expected-page-sha256"] && pageSha256 !== options["expected-page-sha256"].toUpperCase()) {
  throw new Error(`page SHA mismatch: ${pageSha256}`);
}
fs.mkdirSync(path.join(outputRoot, "frames"), { recursive: true });

const specs = [];
for (const family of ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"]) {
  for (const phrase of [0, 1, 2]) {
    for (const phase of ["hold", "orient", "anticipate", "accent", "follow", "settle"]) {
      specs.push({ id: `expression_${family}_v0_${phrase}_${phase}`, kind: "expression", family, phrase, phase, variant: 0 });
    }
  }
}
for (const [family, variant] of [["delighted", 2], ["bashful", 1], ["focused", 2]]) {
  for (const phrase of [0, 1, 2]) {
    for (const phase of ["hold", "orient", "anticipate", "accent", "follow", "settle"]) {
      specs.push({ id: `expression_${family}_v${variant}_${phrase}_${phase}`, kind: "expression", family, phrase, phase, variant });
    }
  }
}
for (const phase of ["open", "closed"]) specs.push({ id: `blink_${phase}`, kind: "blink", phase });
for (const mode of ["charging", "recording", "speaker"]) {
  for (const frame of [0, 1, 2]) specs.push({ id: `${mode}_${frame}`, kind: "mode", mode, frame });
}
for (let timelineTick = 0; timelineTick < 64; timelineTick += 1) {
  specs.push({
    id: `recording_timeline_${String(timelineTick).padStart(2, "0")}`,
    kind: "recording_timeline",
    timelineTick,
  });
}
for (const progress of [0, 0.25, 0.5, 0.75, 1]) {
  specs.push({ id: `menu_progress_${String(progress).replace(".", "_")}`, kind: "menu_progress", progress });
  specs.push({ id: `upgrade_progress_${String(progress).replace(".", "_")}`, kind: "upgrade_progress", progress });
}
for (const frame of [0, 1, 2]) specs.push({ id: `menu_mode_${frame}`, kind: "mode", mode: "menu", frame });

const server = serverForRoot();
const playwright = loadPlaywright();
let browser;
const rendered = [];
try {
  await new Promise((resolve, reject) => { server.once("error", reject); server.listen(0, "127.0.0.1", resolve); });
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
  await page.goto(`http://127.0.0.1:${port}/${pageRepoPath}`, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 15000 });
  const menuHoldMilestones = await page.evaluate(() => {
    const contract = window.__compReq625Contract().menu_hold;
    return Array.from({ length: contract.progress_frames }, (_, index) => {
      // The lead time only reveals the empty badge. Each exported milestone
      // must correspond to one newly filled cell, including the fourth cell at
      // the actual long-press boundary.
      const heldMs = contract.recognition_lead_ms + (index + 1) * contract.cell_step_ms;
      return {
        held_ms: heldMs,
        progress: heldMs / contract.threshold_ms,
      };
    });
  });
  for (const milestone of menuHoldMilestones) {
    specs.push({
      id: `menu_hold_${milestone.held_ms}ms`,
      kind: "menu_progress",
      progress: milestone.progress,
      held_ms: milestone.held_ms,
    });
  }
  for (const [lifeFamily, episodeLimit] of lifeEpisodeCounts) {
    const lifeStates = await page.evaluate(({ family, limit }) => {
      window.__compReq714SetScheduler(false);
      const result = [];
      for (let tick = 0; tick < 1024; tick += 1) {
        const state = runtimeStateAt(family, tick, 0);
        if (state.action_episode >= limit) break;
        if (state.life_action === "rest" && state.action_step !== 0) continue;
        result.push({
          family,
          phrase: state.phrase,
          phase: state.phase,
          variation: state.variation,
          life_action: state.life_action,
          action_step: state.action_step,
          action_episode: state.action_episode,
          dwell_commits: state.life_action === "rest"
            ? state.quiet_dwell_commits
            : state.dwell_commits,
          quiet_dwell_commits: state.quiet_dwell_commits,
          intensity: state.intensity,
          gaze: [...state.gaze],
          recent_actions: [...state.recent_actions],
        });
      }
      return result;
    }, { family: lifeFamily, limit: episodeLimit });
    const exportedEpisodes = new Set(
      lifeStates.map((state) => state.action_episode),
    );
    if (exportedEpisodes.size !== episodeLimit ||
        [...exportedEpisodes].some((episode) => episode < 0 || episode >= episodeLimit)) {
      throw new Error(
        `${lifeFamily} life export did not cover episodes 0..${episodeLimit - 1}`,
      );
    }
    for (const state of lifeStates) {
      specs.push({
        id: `life_${lifeFamily}_e${state.action_episode}_s${state.action_step}_${state.life_action}_${state.phase}`,
        kind: "life",
        family: lifeFamily,
        state,
      });
    }
  }
  const menuModel = await page.evaluate(() => {
    window.__compReq772ResetPracticalMenuState();
    return MENU_SCREEN_NAMES.map((name, screen) => ({
      name,
      rows: menuRowsForScreen(screen).map((row) => ({
        id: row.id,
        kind: row.kind,
      })),
    }));
  });
  const product = (axes) => axes.reduce(
    (rows, axis) => rows.flatMap((row) => axis.values.map((value) => ({
      ...row,
      [axis.key]: value,
    }))),
    [{}],
  );
  const menuVariants = menuModel.map(() => [{}]);
  menuVariants[1] = product([
    { key: "recordingGestureMode", values: ["corner_double_tap", "edge_pull"] },
    { key: "menuRecorderProfile", values: ["voice", "meeting"] },
    { key: "menuRecordingLimitMinutes", values: [30, 15, 60, 0] },
    { key: "menuSilentAutoStop", values: [true, false] },
  ]);
  menuVariants[2] = product([
    { key: "menuClock24Hour", values: [true, false] },
  ]);
  menuVariants[3] = product([
    { key: "menuLinkStatus", values: ["connected", "disconnected"] },
    { key: "menuAutoReconnect", values: [true, false] },
  ]);
  menuVariants[4] = product([
    { key: "menuTimeZoneOffsetMinutes", values: [480, 0, -300] },
    { key: "menuQuietHours", values: ["23-07", "22-08", "off"] },
  ]);
  menuVariants[5] = product([
    { key: "recordingGestureMode", values: ["corner_double_tap", "edge_pull"] },
  ]);
  menuVariants[8] = product([
    { key: "recordingGestureMode", values: ["corner_double_tap", "edge_pull"] },
    { key: "menuInteractionLevel", values: ["standard", "lively", "quiet"] },
    { key: "menuGazeFollow", values: [true, false] },
    { key: "menuNaturalBlink", values: [true, false] },
  ]);
  menuVariants[9] = [
    { menuRecordingCount: 1, menuRecordingStorageKb: 384 },
    { menuRecordingCount: 0, menuRecordingStorageKb: 0 },
  ];
  menuVariants[10] = product([
    { key: "menuAutoSleepMinutes", values: [3, 5, 0, 1] },
  ]);
  menuVariants[11] = [
    { menuRecordingCount: 1, menuRecordingStorageKb: 384 },
    { menuRecordingCount: 0, menuRecordingStorageKb: 0 },
  ];
  for (const locale of ["zh_cn", "en"]) {
    for (let screen = 0; screen < menuModel.length; screen += 1) {
      const rows = menuModel[screen].rows;
      const maxScrollRow = Math.max(0, rows.length - 4);
      for (let variant = 0; variant < menuVariants[screen].length; variant += 1) {
        const variantSuffix = variant === 0 ? "" : `_v${variant}`;
        const practicalState = menuVariants[screen][variant];
        for (let scrollRow = 0; scrollRow <= maxScrollRow; scrollRow += 1) {
          specs.push({
            id: `menu_ui_${locale}_s${screen}_o${scrollRow}_normal${variantSuffix}`,
            kind: "menu_ui",
            locale,
            screen,
            scrollRow,
            phase: "normal",
            menuVariant: variant,
            practicalState,
          });
          for (let visibleRow = 0; visibleRow < 4; visibleRow += 1) {
            const absoluteIndex = scrollRow + visibleRow;
            const row = rows[absoluteIndex];
            if (!row || row.kind === "status") continue;
            const phase = row.kind === "action" ? "processing" : "ack";
            specs.push({
              id: `menu_ui_${locale}_s${screen}_o${scrollRow}_${phase}_i${absoluteIndex}${variantSuffix}`,
              kind: "menu_ui",
              locale,
              screen,
              scrollRow,
              absoluteIndex,
              rowId: row.id,
              rowKind: row.kind,
              phase,
              menuVariant: variant,
              practicalState,
            });
            if (row.kind === "action") {
              specs.push({
                id: `menu_ui_${locale}_s${screen}_o${scrollRow}_result_i${absoluteIndex}${variantSuffix}`,
                kind: "menu_ui",
                locale,
                screen,
                scrollRow,
                absoluteIndex,
                rowId: row.id,
                rowKind: row.kind,
                phase: "result",
                menuVariant: variant,
                practicalState,
              });
            }
          }
        }
      }
    }
  }
  // Batch renderer work inside the browser process. Returning one compact
  // base64 raster per state avoids 1557 CDP round trips and the much larger
  // structured-clone cost of byte arrays.
  const renderBatchSize = 64;
  for (let batchStart = 0; batchStart < specs.length; batchStart += renderBatchSize) {
    const batch = specs.slice(batchStart, batchStart + renderBatchSize);
    const results = await page.evaluate((items) => items.map((item) => {
      if (item.kind === "expression") window.__compReq628FreezePose(item.family, item.phrase, item.phase, item.variant || 0);
      else if (item.kind === "blink") window.__compReq603FreezeBlink(item.phase);
      else if (item.kind === "life") {
        renderPose(
          item.family,
          item.state.phrase,
          item.state.phase,
          null,
          runtimeOrnamentFor(
            item.family,
            item.state.phase,
            item.state.variation,
            false,
            item.state,
          ),
          item.state.variation,
          item.state,
        );
      }
      else if (item.kind === "menu_ui") {
        window.__compReq772ResetPracticalMenuState();
        window.__compReq772SetMenuLocale(item.locale);
        const practical = item.practicalState || {};
        if (Object.hasOwn(practical, "recordingGestureMode")) recordingGestureMode = practical.recordingGestureMode;
        if (Object.hasOwn(practical, "menuRecorderProfile")) menuRecorderProfile = practical.menuRecorderProfile;
        if (Object.hasOwn(practical, "menuRecordingLimitMinutes")) menuRecordingLimitMinutes = practical.menuRecordingLimitMinutes;
        if (Object.hasOwn(practical, "menuSilentAutoStop")) menuSilentAutoStop = practical.menuSilentAutoStop;
        if (Object.hasOwn(practical, "menuClock24Hour")) menuClock24Hour = practical.menuClock24Hour;
        if (Object.hasOwn(practical, "menuLinkStatus")) menuLinkStatus = practical.menuLinkStatus;
        if (Object.hasOwn(practical, "menuAutoReconnect")) menuAutoReconnect = practical.menuAutoReconnect;
        if (Object.hasOwn(practical, "menuTimeZoneOffsetMinutes")) menuTimeZoneOffsetMinutes = practical.menuTimeZoneOffsetMinutes;
        if (Object.hasOwn(practical, "menuQuietHours")) menuQuietHours = practical.menuQuietHours;
        if (Object.hasOwn(practical, "menuInteractionLevel")) menuInteractionLevel = practical.menuInteractionLevel;
        if (Object.hasOwn(practical, "menuGazeFollow")) menuGazeFollow = practical.menuGazeFollow;
        if (Object.hasOwn(practical, "menuNaturalBlink")) menuNaturalBlink = practical.menuNaturalBlink;
        if (Object.hasOwn(practical, "menuRecordingCount")) menuRecordingCount = practical.menuRecordingCount;
        if (Object.hasOwn(practical, "menuRecordingStorageKb")) menuRecordingStorageKb = practical.menuRecordingStorageKb;
        if (Object.hasOwn(practical, "menuAutoSleepMinutes")) menuAutoSleepMinutes = practical.menuAutoSleepMinutes;
        const selectedIndex = item.scrollRow === 0 ? 0 : item.scrollRow + 3;
        window.__compReq657RenderMenuScreen(item.screen, selectedIndex);
        menuScrollOffset = item.scrollRow * MENU_ROW_HEIGHT;
        menuSelectedIndex = item.absoluteIndex ?? selectedIndex;
        clearMenuTapAck();
        menuActionState = null;
        if (item.phase === "ack") {
          menuTapAck = {
            screen: item.screen,
            absoluteIndex: item.absoluteIndex,
            item: item.rowId,
            kind: item.rowKind,
            started_at: performance.now(),
          };
        } else if (item.phase === "processing") {
          menuActionState = {
            screen: item.screen,
            item: item.rowId,
            phase: "processing",
            value: menuText("processing"),
          };
        } else if (item.phase === "result") {
          let value = menuText("ready");
          if (item.rowId === "pair") value = menuText("waiting_device");
          else if (item.rowId === "connection_toggle") value = menuText(menuLinkStatus);
          else if (item.rowId === "reset_name") value = menuText("restored");
          else if (item.rowId === "confirm_clear") value = menuText("cleared");
          else if (item.rowId === "confirm_restore") value = menuText("defaults_restored");
          else if (item.rowId === "sleep_now") value = menuText("entering_sleep");
          menuActionState = {
            screen: item.screen,
            item: item.rowId,
            phase: "result",
            value,
          };
        }
        renderMenuScreen(item.screen, menuSelectedIndex, true);
      }
      else if (item.kind === "recording_timeline") {
        // Export one deterministic recording session through the same
        // procedural face + audio renderer used by the live fixed page.
        window.__compReq628FreezePose("calm", 0, "hold", 0);
        const entryActive = item.timelineTick <= RECORDING_WAVE_ENTRY_STAGES;
        let lifeAction = "recording_wave_entry_hold";
        if (!entryActive) {
          const state = runtimeStateAt(
            "calm", item.timelineTick - RECORDING_WAVE_ENTRY_STAGES - 1, 0,
          );
          renderPose(
            "calm",
            state.phrase,
            state.phase,
            null,
            runtimeOrnamentFor(
              "calm", state.phase, state.variation || 0, false, state,
            ),
            state.variation || 0,
            state,
          );
          lifeAction = state.life_action;
        }
        const envelope = proceduralAudioEnvelopeAt(
          "recording", item.timelineTick, 0,
        );
        renderSpecialPose("recording", envelope.level, {
          ...envelope,
          entry_wave_progress: entryActive
            ? item.timelineTick / RECORDING_WAVE_ENTRY_STAGES
            : 1,
          life_action: lifeAction,
        });
      }
      else {
        // Special-state exports are overlays. Pin their underlying expression
        // so the same browser source always produces the same device pixels.
        window.__compReq628FreezePose("calm", 0, "hold", 0);
        if (item.kind === "mode") window.__compReq625FreezeMode(item.mode, item.frame);
        else if (item.kind === "menu_progress") window.__compReq625FreezeMenuProgress(item.progress);
        else if (item.kind === "upgrade_progress") window.__compReq628FreezeUpgrade(item.progress);
      }
      const canvas = document.querySelector("#face");
      const rgba = canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data;
      const packed = new Uint8Array(5000);
      let black = 0;
      let gray = 0;
      let minX = 200;
      let minY = 200;
      let maxX = -1;
      let maxY = -1;
      for (let pixel = 0; pixel < 40000; pixel += 1) {
        const offset = pixel * 4;
        if (![0, 255].includes(rgba[offset])) gray += 1;
        if (rgba[offset] >= 128) continue;
        packed[Math.floor(pixel / 8)] |= 1 << (7 - (pixel % 8));
        black += 1;
        const x = pixel % 200;
        const y = Math.floor(pixel / 200);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
      return {
        bytes_base64: btoa(String.fromCharCode(...packed)),
        black,
        gray,
        bounds: black ? [minX, minY, maxX, maxY] : null,
      };
    }), batch);
    for (let index = 0; index < results.length; index += 1) {
      const result = results[index];
      const bytes = Buffer.from(result.bytes_base64, "base64");
      rendered.push({
        ...batch[index],
        bytes,
        black_pixels: result.black,
        gray_input_pixels: result.gray,
        black_bounds: result.bounds,
      });
    }
  }
  // Append pointer-response states after the established pack so every
  // existing canonical frame index remains stable. These pixels are rendered
  // by the exact same functions used by commitEmotionTap/renderTouchTransition
  // on the fixed browser page.
  const tapStates = await page.evaluate((exportPointerFollow) => {
    const scenarios = [
      { zone: "center", point: [0.5, 0.58], action: "small_breath", target: "thoughtful" },
      { zone: "up", point: [0.5, 0.2], action: "listen_up", target: "curious" },
      { zone: "down", point: [0.5, 0.8], action: "soften", target: "thoughtful" },
      { zone: "left", point: [0.2, 0.5], action: "notice_left", target: "thoughtful" },
      { zone: "right", point: [0.8, 0.5], action: "notice_right", target: "thoughtful" },
    ];
    const families = [
      "calm", "curious", "delighted", "warm", "playful",
      "sleepy", "bashful", "thoughtful", "focused", "alert",
    ];
    const result = [];
    const capture = () => {
      const canvas = document.querySelector("#face");
      const rgba = canvas.getContext(
        "2d", { willReadFrequently: true },
      ).getImageData(0, 0, 200, 200).data;
      const packed = new Uint8Array(5000);
      let black = 0;
      let gray = 0;
      let minX = 200;
      let minY = 200;
      let maxX = -1;
      let maxY = -1;
      for (let pixel = 0; pixel < 40000; pixel += 1) {
        const offset = pixel * 4;
        if (![0, 255].includes(rgba[offset])) gray += 1;
        if (rgba[offset] >= 128) continue;
        packed[Math.floor(pixel / 8)] |= 1 << (7 - (pixel % 8));
        black += 1;
        const x = pixel % 200;
        const y = Math.floor(pixel / 200);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
      return {
        bytes_base64: btoa(String.fromCharCode(...packed)),
        black,
        gray,
        bounds: black ? [minX, minY, maxX, maxY] : null,
      };
    };
    const resetTapRuntime = (family) => {
      setMainScheduler(false);
      selected = family;
      selectedVariantBias = 0;
      tick = 1;
      modeTick = 0;
      touchTransitionSerial = 0;
      touchTransition = null;
      heldPose = null;
      heldPoseCommitsRemaining = 0;
      naturalBlinkClosedNow = false;
    };
    const localLife = (family, scenario) => {
      const state = runtimeStateAt(family, 1, 0);
      return {
        ...state,
        phase: "orient",
        life_action: scenario.action,
        gaze: [
          Math.round((scenario.point[0] - 0.5) * 4),
          Math.round((scenario.point[1] - 0.5) * 4),
        ],
        interaction: "single_tap_local_response",
      };
    };

    for (const family of families) {
      for (const scenario of scenarios) {
        resetTapRuntime(family);
        const life = localLife(family, scenario);
        renderPose(
          family,
          life.phrase,
          "orient",
          null,
          runtimeOrnamentFor(family, "hold", life.variation || 0),
          life.variation || 0,
          life,
        );
        result.push({
          id: `tap_local_${family}_${scenario.zone}`,
          kind: "tap_local",
          family,
          zone: scenario.zone,
          life_action: scenario.action,
          phase: "orient",
          phrase: life.phrase,
          variation: life.variation,
          ...capture(),
        });
      }
    }

    // Two taps from the boot family cross the browser's evidence threshold.
    // Preserve every route edge and phase; repeated dwell commits are encoded
    // as frame duration by the CEMP manifest generator.
    for (const scenario of scenarios) {
      resetTapRuntime("calm");
      const life = localLife("calm", scenario);
      heldPose = life;
      heldPoseCommitsRemaining = 0;
      startTouchTransition(
        scenario.point[0],
        scenario.point[1],
        scenario.target,
        "accumulated_single_taps",
      );
      let guard = 0;
      while (touchTransition && guard++ < 128) {
        const routeIndex = touchTransition.routeIndex;
        const phaseIndex = touchTransition.phaseIndex;
        const phase = TOUCH_PHASES[phaseIndex];
        const dwellCommits = touchTransition.phaseDwells[phaseIndex];
        const edgeSource = touchTransition.route[routeIndex];
        const edgeTarget =
          touchTransition.route[routeIndex + 1] || touchTransition.target;
        renderTouchTransition();
        result.push({
          id: `tap_transition_${scenario.zone}_e${routeIndex}_${phase}`,
          kind: "tap_transition",
          zone: scenario.zone,
          source_family: edgeSource,
          target_family: edgeTarget,
          final_family: scenario.target,
          route_index: routeIndex,
          phase,
          dwell_commits: dwellCommits,
          ...capture(),
        });
        for (let repeat = 1;
             repeat < dwellCommits && touchTransition;
             repeat += 1) {
          renderTouchTransition();
        }
      }
      if (touchTransition) {
        throw new Error(`tap transition export did not settle: ${scenario.zone}`);
      }
    }

    // Export each browser-authored affect-graph edge once per pointer zone.
    // Later route clips can concatenate these exact edge frames without the
    // firmware inventing pixels, phases, or family transitions.
    for (const [sourceFamily, targets] of Object.entries(AFFECT_GRAPH)) {
      for (const targetFamily of targets) {
        for (const scenario of scenarios) {
          resetTapRuntime(sourceFamily);
          startTouchTransition(
            scenario.point[0],
            scenario.point[1],
            targetFamily,
            "generated_affect_graph_edge",
          );
          if (!touchTransition
              || touchTransition.route.length !== 2
              || touchTransition.route[0] !== sourceFamily
              || touchTransition.route[1] !== targetFamily) {
            throw new Error(
              `tap edge is not direct: ${sourceFamily}->${targetFamily}`,
            );
          }
          let guard = 0;
          while (touchTransition && guard++ < 64) {
            const phaseIndex = touchTransition.phaseIndex;
            const phase = TOUCH_PHASES[phaseIndex];
            const dwellCommits = touchTransition.phaseDwells[phaseIndex];
            renderTouchTransition();
            result.push({
              id: `tap_edge_${sourceFamily}_${targetFamily}_${scenario.zone}_${phase}`,
              kind: "tap_edge",
              zone: scenario.zone,
              source_family: sourceFamily,
              target_family: targetFamily,
              phase,
              dwell_commits: dwellCommits,
              ...capture(),
            });
            for (let repeat = 1;
                 repeat < dwellCommits && touchTransition;
                 repeat += 1) {
              renderTouchTransition();
            }
          }
          if (touchTransition) {
            throw new Error(
              `tap edge export did not settle: ${sourceFamily}->${targetFamily}/${scenario.zone}`,
            );
          }
        }
      }
    }
    // Pointer motion uses the same browser renderer as the live canvas. The
    // panel runtime advances toward one of these 9x9 authored gaze states at
    // the browser's bounded two-pixel cadence. Keeping the grid in CEMP means
    // firmware never redraws or approximates UI pixels.
    if (exportPointerFollow) {
      for (const family of families) {
        resetTapRuntime(family);
        const phrase = runtimeStateAt(family, 1, 0).phrase;
        const ornament = runtimeOrnamentFor(family, "hold", 0);
        for (let gy = -4; gy <= 4; gy += 2) {
          for (let gx = -4; gx <= 4; gx += 2) {
            renderPose(
              family,
              phrase,
              "hold",
              [gx, gy],
              ornament,
              0,
              {
                life_action: "pointer_follow",
                gaze: [0, 0],
                brow_gaze: [gx, gy],
                intensity: 1,
                action_episode: 0,
                action_step: 0,
                interaction: gx === 0 && gy === 0
                  ? "pointer_return"
                  : "pointer_follow",
              },
            );
            result.push({
              id: `pointer_follow_${family}_gx${gx + 4}_gy${gy + 4}`,
              kind: "pointer_follow",
              family,
              gravity_x: gx,
              gravity_y: gy,
              phrase,
              variation: 0,
              ...capture(),
            });
          }
        }
      }
    }
    return result;
  }, includePointerFollow);
  for (const frame of tapStates) {
    rendered.push({
      ...frame,
      bytes: Buffer.from(frame.bytes_base64, "base64"),
      black_pixels: frame.black,
      gray_input_pixels: frame.gray,
      black_bounds: frame.bounds,
    });
  }
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

componentizeLifeFrames(rendered);

const uniqueFrames = [];
const uniqueBySha = new Map();
const states = [];
for (const frame of rendered) {
  const frameSha256 = sha256(frame.bytes);
  if (!uniqueBySha.has(frameSha256)) {
    uniqueBySha.set(frameSha256, uniqueFrames.length);
    uniqueFrames.push({ bytes: frame.bytes, sha256: frameSha256 });
  }
  const uniqueFrameIndex = uniqueBySha.get(frameSha256);
  const pbmName = `${frame.id}.pbm`;
  const pbm = pbmBytes(frame.bytes);
  fs.writeFileSync(path.join(outputRoot, "frames", pbmName), pbm);
  states.push({
    id: frame.id,
    kind: frame.kind,
    ...(frame.kind === "life" ? {
      family: frame.family,
      action_episode: frame.state.action_episode,
      action_step: frame.state.action_step,
      life_action: frame.state.life_action,
      phase: frame.state.phase,
      phrase: frame.state.phrase,
      variation: frame.state.variation,
      dwell_commits: frame.state.dwell_commits,
      quiet_dwell_commits: frame.state.quiet_dwell_commits,
      component_stage: frame.component_stage,
    } : frame.kind === "menu_ui" ? {
      locale: frame.locale,
      screen: frame.screen,
      scroll_row: frame.scrollRow,
      phase: frame.phase,
      absolute_index: frame.absoluteIndex ?? null,
      row_id: frame.rowId ?? null,
      row_kind: frame.rowKind ?? null,
      menu_variant: frame.menuVariant ?? 0,
      practical_state: frame.practicalState ?? {},
    } : frame.kind === "tap_local" ? {
      family: frame.family,
      zone: frame.zone,
      life_action: frame.life_action,
      phase: frame.phase,
      phrase: frame.phrase,
      variation: frame.variation,
    } : frame.kind === "tap_transition" ? {
      zone: frame.zone,
      source_family: frame.source_family,
      target_family: frame.target_family,
      final_family: frame.final_family,
      route_index: frame.route_index,
      phase: frame.phase,
      dwell_commits: frame.dwell_commits,
    } : frame.kind === "tap_edge" ? {
      zone: frame.zone,
      source_family: frame.source_family,
      target_family: frame.target_family,
      phase: frame.phase,
      dwell_commits: frame.dwell_commits,
    } : frame.kind === "pointer_follow" ? {
      family: frame.family,
      gravity_x: frame.gravity_x,
      gravity_y: frame.gravity_y,
      phrase: frame.phrase,
      variation: frame.variation,
    } : frame.kind === "recording_timeline" ? {
      timeline_tick: frame.timelineTick,
      cadence_ms: 480,
    } : {}),
    black_bounds: frame.black_bounds,
    black_pixels: frame.black_pixels,
    gray_input_pixels: frame.gray_input_pixels,
    browser_frame_sha256: frameSha256,
    unique_frame_index: uniqueFrameIndex,
    pbm_file: `frames/${pbmName}`,
    pbm_sha256: sha256(pbm),
  });
}
const pack = Buffer.concat(uniqueFrames.map((frame) => frame.bytes));
const header = headerBytes(states, uniqueFrames.length);
const source = sourceBytes(uniqueFrames, states);
fs.writeFileSync(path.join(outputRoot, "frames.bin"), pack);
fs.writeFileSync(path.join(outputRoot, "comp_req_628_source_pack.h"), header);
fs.writeFileSync(path.join(outputRoot, "comp_req_628_source_pack.c"), source);
const manifest = {
  schema: "companion.comp_req_628.browser_epaper_source_pack.v1",
  status: states.every((state) => state.gray_input_pixels === 0 && state.black_pixels > 0) ? "PASS" : "NO_GO",
  source: {
    page_path: pageRepoPath,
    page_sha256: pageSha256,
    renderer_contract: "window.__compReq625Contract",
    renderer_mode: "browser_canvas_200x200",
    pixel_format: "row_major_msb_first_1_is_white",
  },
  format: { width: 200, height: 200, stride_bytes: 25, frame_bytes: 5000, cadence_ms: 480 },
  files: {
    c: { path: "comp_req_628_source_pack.c", sha256: sha256(source) },
    h: { path: "comp_req_628_source_pack.h", sha256: sha256(header) },
    frames: { path: "frames.bin", bytes: pack.length, sha256: sha256(pack) },
  },
  invariants: {
    state_count: states.length,
    unique_frame_count: uniqueFrames.length,
    life_families: [...lifeEpisodeCounts.keys()],
    life_episode_counts: Object.fromEntries(lifeEpisodeCounts),
    all_states_are_5000_bytes: rendered.every((frame) => frame.bytes.length === 5000),
    all_inputs_binary: rendered.every((frame) => frame.gray_input_pixels === 0),
    all_states_have_black_pixels: rendered.every((frame) => frame.black_pixels > 0),
    affect_graph_edge_count: states.filter((state) => state.kind === "tap_edge").length / 25,
    pointer_follow_state_count: states.filter((state) => state.kind === "pointer_follow").length,
    pointer_follow_grid: [5, 5],
    pointer_follow_source_grid: [9, 9],
    pointer_follow_projection: "browser_authored_even_gravity_cells",
    life_component_choreography:
      "eyes_lead_then_brows_then_lower_face_then_ornament_then_authored_settle",
    life_componentized_episode_ceiling: 9,
    life_componentized_episode_policy:
      "non_sleepy_even_episodes_below_9_plus_warm_soften_e3_minus_redundant_playful_e6",
    life_ornament_solo_policy:
      "one_seeded_visible_follow_episode_per_non_sleepy_family",
  },
  states,
};
const manifestBytes = jsonBytes(manifest);
fs.writeFileSync(path.join(outputRoot, "source-pack-manifest.json"), manifestBytes);
if (manifest.status !== "PASS") throw new Error("source pack contains non-binary or empty frame");
console.log(JSON.stringify({
  status: manifest.status,
  page_sha256: pageSha256,
  manifest_sha256: sha256(manifestBytes),
  output: path.relative(repoRoot, outputRoot).replaceAll("\\", "/"),
  states: states.length,
  unique_frames: uniqueFrames.length,
  frame_bytes: pack.length,
  elapsed_ms: Date.now() - startedAtMs,
}));
