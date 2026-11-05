#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-756-757-758");
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(screenshotRoot, { recursive: true });

function loadPlaywright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright"
  ].filter(Boolean)) {
    try {
      return require(name);
    } catch {}
  }
  throw new Error("Playwright unavailable");
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1120, height: 900 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));

  async function loadFresh() {
    const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
    await page.waitForFunction(() =>
      window.__compReq599Ready === true
      && typeof window.__compReq756Contract === "function"
      && typeof window.__compReq757Contract === "function"
      && typeof window.__compReq758Contract === "function");
    const box = await page.locator("#face").boundingBox();
    return { response, box };
  }

  function at(box, x, y) {
    return { x: box.x + box.width * x, y: box.y + box.height * y };
  }

  async function shortTap(point) {
    await page.mouse.move(point.x, point.y);
    await page.mouse.down();
    await page.waitForTimeout(45);
    await page.mouse.up();
  }

  const firstLoad = await loadFresh();
  const fixedResponseOk =
    firstLoad.response?.status() === 200 && firstLoad.response.url() === fixedUrl;
  const corner = at(firstLoad.box, 0.12, 0.84);
  await page.evaluate(() => window.__compReq714ClearTrace());
  const familyBeforeSingle = await page.evaluate(() =>
    window.__compReq758InteractionState().selected);
  await shortTap(corner);
  await page.waitForTimeout(900);
  const cornerSingle = await page.evaluate(() => ({
    state: window.__compReq758InteractionState(),
    recording: window.__compReq753Snapshot()
  }));

  const centerLoad = await loadFresh();
  const center = at(centerLoad.box, 0.52, 0.52);
  await page.evaluate(() => window.__compReq714ClearTrace());
  await shortTap(center);
  await page.waitForTimeout(90);
  await shortTap(center);
  await page.waitForTimeout(120);
  const centerDouble = await page.evaluate(() => ({
    state: window.__compReq758InteractionState(),
    recording: window.__compReq753Snapshot()
  }));

  const crossLoad = await loadFresh();
  await page.evaluate(() => window.__compReq714ClearTrace());
  await shortTap(at(crossLoad.box, 0.12, 0.84));
  await page.waitForTimeout(90);
  await shortTap(at(crossLoad.box, 0.5, 0.5));
  await page.waitForTimeout(500);
  const crossZone = await page.evaluate(() => ({
    state: window.__compReq758InteractionState(),
    recording: window.__compReq753Snapshot()
  }));

  const recordLoad = await loadFresh();
  const recordCorner = at(recordLoad.box, 0.12, 0.84);
  await page.evaluate(() => window.__compReq714ClearTrace());
  await shortTap(recordCorner);
  await page.waitForTimeout(90);
  await shortTap(recordCorner);
  await page.waitForTimeout(120);
  const entered = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));
  await shortTap(recordCorner);
  await page.waitForTimeout(430);
  const afterThirdTap = await page.evaluate(() => window.__compReq753Snapshot());
  const exitPoint = at(recordLoad.box, 0.78, 0.3);
  await shortTap(exitPoint);
  await page.waitForTimeout(90);
  await shortTap(exitPoint);
  await page.waitForFunction(() =>
    window.__compReq753Snapshot().active_mode === "expression",
    null,
    { timeout: 3500 });
  const exited = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));

  const contracts = await page.evaluate(() => ({
    recording: window.__compReq756Contract(),
    rhythm: window.__compReq757Contract(),
    interaction: window.__compReq758Contract(),
    lowPower: window.__compReq752Contract(),
    menu: window.__compReq743FreezeRecordingGestureMenu()
  }));
  await page.screenshot({
    path: path.join(screenshotRoot, "default-left-corner-double-tap-menu.png"),
    fullPage: true
  });

  const lifeAudit = await page.evaluate(() => {
    const families = [
      "calm", "curious", "delighted", "warm", "playful",
      "bashful", "thoughtful", "focused", "alert"
    ];
    return Object.fromEntries(families.map(family => {
      const sequence = window.__compReq751LifeSequence(family, 512);
      return [family, {
        quiet: [...new Set(sequence
          .filter(row => row.life_action === "rest")
          .map(row => row.quiet_dwell_commits))],
        actionDwells: [...new Set(sequence
          .filter(row => row.life_action !== "rest")
          .map(row => row.dwell_commits))]
      }];
    }));
  });

  const cadenceLoad = await loadFresh();
  await page.evaluate(() => window.__compReq714ClearTrace());
  await shortTap(at(cadenceLoad.box, 0.5, 0.5));
  await page.waitForTimeout(1550);
  await shortTap(at(cadenceLoad.box, 0.5, 0.5));
  await page.waitForTimeout(1600);
  const cadenceTrace = await page.evaluate(() =>
    window.__compReq599Snapshot().trace.filter(row => row.type === "commit"));
  const commitGaps = cadenceTrace.slice(1).map((row, index) =>
    row.at - cadenceTrace[index].at);
  const transitionCommits = cadenceTrace.filter(row =>
    row.interaction_intent === "accumulated_single_taps");
  const transitionGaps = transitionCommits.slice(1).map((row, index) =>
    row.at - transitionCommits[index].at);

  const entryEvents = entered.trace.filter(row => row.type === "recording_enter");
  const exitEvents = exited.trace.filter(row => row.type === "recording_exit");
  const retractProgress = exited.trace
    .filter(row => row.type === "recording_mic_retract_frame")
    .map(row => row.progress);
  const singleCommits = cornerSingle.state.trace.filter(row =>
    row.type === "single_tap_commit");
  const checks = {
    fixed_url_http_200: fixedResponseOk,
    browser_errors_zero: browserErrors.length === 0,
    default_is_left_corner_double_tap:
      contracts.recording.default_mode === "corner_double_tap"
      && contracts.recording.current_mode === "corner_double_tap"
      && contracts.menu.default,
    left_corner_single_does_not_record:
      cornerSingle.recording.active_mode === "expression"
      && cornerSingle.state.selected === familyBeforeSingle
      && singleCommits.length === 1
      && singleCommits[0].family_switch === false,
    other_position_double_does_not_record:
      centerDouble.recording.active_mode !== "recording"
      && centerDouble.state.trace.every(row => row.type !== "recording_enter"),
    cross_zone_double_does_not_record:
      crossZone.recording.active_mode !== "recording"
      && crossZone.state.trace.every(row => row.type !== "recording_enter"),
    left_corner_double_starts_once:
      entered.state.active_mode === "recording"
      && entryEvents.length === 1
      && entryEvents[0].source === "lower_left_double_tap",
    third_tap_does_not_toggle_again:
      afterThirdTap.active_mode === "recording",
    anywhere_double_exits_once:
      exited.state.active_mode === "expression"
      && exitEvents.length === 1
      && exitEvents[0].source === "anywhere_double_tap",
    exit_restores_in_one_commit_without_timed_retract:
      retractProgress.length === 0
      && exited.trace.filter(row =>
        row.type === "commit" && row.phase === "recording_exit_restore").length === 1,
    awake_choreography_ceiling_is_2s:
      contracts.rhythm.awake_visible_change_ceiling_ms === 2000
      && Object.values(lifeAudit).every(row =>
        row.quiet.every(value => value >= 2 && value <= 4)
        && row.actionDwells.every(value => value >= 1 && value <= 4)),
    awake_rhythm_is_not_fixed:
      Object.values(lifeAudit).every(row =>
        row.quiet.length >= 3 && row.actionDwells.length >= 2),
    deep_low_power_remains_frozen:
      contracts.rhythm.low_power_exception
        === "deep_sleep_stable_frame_scheduler_stopped"
      && contracts.lowPower.main_scheduler === "stopped_while_locked",
    first_tap_never_switches_family:
      contracts.interaction.first_tap_family_switch === false
      && contracts.interaction.family_switch_threshold === 2,
    visible_pointer_commits_follow_epaper_cadence:
      contracts.interaction.visible_input_commit_cadence_ms === 480
      && commitGaps.length >= 5
      && commitGaps.every(gap => gap >= 430),
    emotion_transition_commits_follow_epaper_cadence:
      transitionCommits.length >= 2
      && transitionGaps.every(gap => gap >= 430),
    hardware_contact_zero:
      contracts.recording.hardware_contact === 0
      && contracts.rhythm.hardware_contact === 0
      && contracts.interaction.hardware_contact === 0
  };

  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    checks,
    evidence: {
      commit_gaps_ms: commitGaps.map(value => Math.round(value)),
      transition_commit_gaps_ms: transitionGaps.map(value => Math.round(value)),
      retract_progress: retractProgress,
      life_audit: lifeAudit,
      browser_errors: browserErrors
    },
    screenshot:
      ".cache/validation/comp-req-756-757-758/screenshots/default-left-corner-double-tap-menu.png"
  };
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(artifactRoot, "MACHINE_READY.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
