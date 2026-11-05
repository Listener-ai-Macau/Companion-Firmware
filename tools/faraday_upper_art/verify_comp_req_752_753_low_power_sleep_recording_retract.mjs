#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root,
  ".cache/validation/comp-req-752-753-low-power-recording-retract"
);
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

async function canvasSample(page, label) {
  return page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const values = new Set();
    for (let offset = 0; offset < data.length; offset += 4) {
      values.add(`${data[offset]},${data[offset + 1]},${data[offset + 2]},${data[offset + 3]}`);
    }
    return {
      label,
      data_url: canvas.toDataURL("image/png"),
      pixel_values: [...values].sort(),
      frame_signature: window.__compReq753Snapshot().frame_signature
    };
  }, label);
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1180, height: 900 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq752EnterSleep === "function"
    && typeof window.__compReq753InjectVoiceControl === "function"
    && typeof window.__compReq755EnterDrowsy === "function");

  const drowsyStart = await page.evaluate(() => {
    window.__compReq714ClearTrace();
    return {
      start: window.__compReq755EnterDrowsy("machine_drowsy_entry"),
      plans: window.__compReq755DrowsyPlan(16),
      contract: window.__compReq755Contract()
    };
  });
  const drowsyFrames = [];
  for (const stage of [1, 2, 3]) {
    await page.waitForFunction(expected =>
      window.__compReq752Snapshot().drowsy_stage === expected,
      stage,
      { timeout: 3000 });
    drowsyFrames.push(await page.evaluate(stage => {
      const canvas = document.querySelector("#face");
      const data = canvas.getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      let hash = 2166136261;
      for (let y = 0; y < 200; y += 1) {
        for (let x = 0; x < 200; x += 1) {
          if (x >= 0 && x < 100 && y >= 14 && y < 90) continue;
          hash ^= data[(y * 200 + x) * 4] < 128 ? 1 : 0;
          hash = Math.imul(hash, 16777619) >>> 0;
        }
      }
      return {
        stage,
        label: `drowsy_stage_${stage}`,
        data_url: canvas.toDataURL("image/png"),
        outside_ornament_signature: hash.toString(16).padStart(8, "0"),
        frame_signature: window.__compReq753Snapshot().frame_signature
      };
    }, stage));
  }
  await page.waitForFunction(() =>
    window.__compReq752Snapshot().locked
    && !window.__compReq752Snapshot().drowsy_active,
    null,
    { timeout: 3500 });
  const drowsySettled = await page.evaluate(() => ({
    snapshot: window.__compReq752Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));

  const sleepStart = await page.evaluate(() =>
    window.__compReq752EnterSleep("machine_sleep_event"));
  const sleepFrame = await canvasSample(page, "low_power_sleep_stable");
  await page.waitForTimeout(2100);
  const sleepLater = await page.evaluate(() => window.__compReq752Snapshot());
  const sleepContract = await page.evaluate(() => window.__compReq752Contract());
  const wakeIntervals = await page.evaluate(() => ({
    first: window.__compReq754WakeIntervals(16),
    second: window.__compReq754WakeIntervals(16),
    contract: window.__compReq754Contract()
  }));
  const wake = await page.evaluate(() =>
    window.__compReq752Wake("calm", "owner_touch_wake"));
  const wakeTrace = await page.evaluate(() =>
    window.__compReq599Snapshot().trace.filter(row =>
      row.type === "low_power_sleep_wake"));

  await page.evaluate(() => {
    window.__compReq714SetScheduler(false);
    for (let step = 0; step < 120; step += 1) {
      const state = window.__compReq728StepTransition();
      if (!state.active) break;
    }
  });
  const wakeSettled = await page.evaluate(() => window.__compReq599Snapshot());

  const autoSleepStart = await page.evaluate(() => {
    window.__compReq714ClearTrace();
    const sleep = window.__compReq752EnterSleep("machine_autonomous_sleep");
    const compressed = window.__compReq754ScheduleCompressedWake(900);
    return { sleep, compressed };
  });
  await page.waitForTimeout(420);
  const autoSleepWaiting = await page.evaluate(() => window.__compReq752Snapshot());
  await page.waitForFunction(() =>
    window.__compReq752Snapshot().rtc_wake_count > 0
    && window.__compReq752Snapshot().transition_active,
    null,
    { timeout: 1800 });
  const autonomousWake = await page.evaluate(() => ({
    snapshot: window.__compReq752Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));
  await page.evaluate(() => {
    window.__compReq714SetScheduler(false);
    for (let step = 0; step < 120; step += 1) {
      const state = window.__compReq728StepTransition();
      if (!state.active) break;
    }
  });

  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq753EnterRecording();
  });
  const retractFrames = [];
  for (const progress of [1, 0.75, 0.5, 0.25, 0]) {
    const geometry = await page.evaluate(progress =>
      window.__compReq753RenderRetractProgress(progress), progress);
    retractFrames.push({
      progress,
      geometry,
      ...(await canvasSample(page, `retract_${progress}`))
    });
  }

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true);
  await page.evaluate(() => window.__compReq743SetRecordingGesture("edge_pull"));
  const box = await page.locator("#face").boundingBox();
  const entryStart = {
    x: box.x + box.width * 0.1,
    y: box.y + box.height * 0.86
  };
  await page.mouse.move(entryStart.x, entryStart.y);
  await page.mouse.down();
  await page.waitForTimeout(540);
  await page.mouse.move(
    entryStart.x + box.width * 0.24,
    entryStart.y,
    { steps: 8 }
  );
  await page.waitForTimeout(80);
  const realPullLocked = await page.evaluate(() => window.__compReq753Snapshot());
  await page.mouse.up();
  await page.waitForTimeout(100);
  const realPullReleased = await page.evaluate(() => window.__compReq753Snapshot());

  const retractStart = {
    x: box.x + box.width * 0.15,
    y: box.y + box.height * 0.84
  };
  await page.mouse.move(retractStart.x, retractStart.y);
  await page.mouse.down();
  await page.mouse.move(
    box.x + box.width * 0.01,
    retractStart.y,
    { steps: 6 }
  );
  await page.mouse.up();
  await page.waitForFunction(() =>
    window.__compReq753Snapshot().active_mode === "expression",
    null,
    { timeout: 3500 });
  const realReverseSettled = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));

  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq753EnterRecording();
  });
  const silenceAccepted = await page.evaluate(() =>
    window.__compReq753InjectVoiceControl("silence_stop"));
  await page.mouse.move(
    box.x + box.width * 0.5,
    box.y + box.height * 0.5
  );
  await page.mouse.down();
  await page.waitForTimeout(180);
  await page.mouse.up();
  await page.waitForFunction(() =>
    window.__compReq753Snapshot().active_mode === "expression",
    null,
    { timeout: 3500 });
  const silenceSettled = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));
  const recordingContract = await page.evaluate(() => window.__compReq753Contract());

  await page.evaluate(({ sleep, retract }) => {
    document.body.innerHTML =
      "<main><h1>低功耗睡眠与麦克风反向收回</h1><section id='sleep'></section><section id='retract'></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    for (const [target, rows] of [
      ["#sleep", sleep],
      ["#retract", retract]
    ]) {
      const section = document.querySelector(target);
      Object.assign(section.style, {
        display: "flex",
        flexWrap: "wrap",
        gap: "14px",
        marginBottom: "20px"
      });
      for (const row of rows) {
        const figure = document.createElement("figure");
        const image = document.createElement("img");
        const caption = document.createElement("figcaption");
        image.src = row.data_url;
        image.width = 240;
        image.height = 240;
        image.style.imageRendering = "pixelated";
        caption.textContent = row.label;
        figure.append(image, caption);
        section.append(figure);
      }
    }
  }, { sleep: [...drowsyFrames, sleepFrame], retract: retractFrames });
  await page.screenshot({
    path: path.join(screenshotRoot, "sleep-and-reverse-path.png"),
    fullPage: true
  });

  const reverseProgress = rows => rows
    .filter(row => row.type === "recording_mic_retract_frame")
    .map(row => row.progress);
  const realReverseProgress = reverseProgress(realReverseSettled.trace);
  const silenceProgress = reverseProgress(silenceSettled.trace);
  const blockedRetractInputs = silenceSettled.trace.filter(row =>
    row.type === "recording_retract_input_blocked");
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    sleep_is_one_static_1bpp_frame:
      sleepFrame.pixel_values.every(value =>
        ["0,0,0,255", "255,255,255,255"].includes(value)),
    drowsy_then_deep_sleep_order_is_one_shot:
      drowsySettled.trace
        .filter(row => row.type === "drowsy_sleep_stage")
        .map(row => row.label)
        .join(",") === "drowsy_entry,z_rise_1,z_rise_2"
      && drowsySettled.trace.filter(row =>
        row.type === "low_power_sleep_locked").length === 1,
    drowsy_z_moves_while_face_stays_stable:
      new Set(drowsyFrames.map(row => row.frame_signature)).size === 3
      && new Set(drowsyFrames.map(row =>
        row.outside_ornament_signature)).size === 1,
    drowsy_timing_is_non_equal_and_replayable:
      drowsyStart.plans.every(plan =>
        plan.length === 3
        && new Set(plan).size === 3
        && plan[0] >= 850 && plan[0] <= 1350
        && plan[1] >= 1150 && plan[1] <= 1850
        && plan[2] >= 1450 && plan[2] <= 2300),
    sleepy_mouths_are_semantic_and_not_rejected_wave:
      drowsyStart.contract.drowsy_mouth === "owner_sleepy_breath_o"
      && drowsyStart.contract.low_power_mouth === "owner_sleepy_rest_arc"
      && drowsyStart.contract.rejected_mouth === "owner_sleepy_wave"
      && drowsySettled.trace.filter(row =>
        row.type === "drowsy_sleep_stage").every(row =>
          row.mouth_pose === "owner_sleepy_breath_o")
      && sleepContract?.stable_mouth !== "owner_sleepy_wave",
    sleep_stops_main_scheduler:
      sleepStart.locked
      && !sleepStart.scheduler_active
      && !sleepLater.scheduler_active
      && sleepStart.rtc_wake_pending
      && sleepStart.rtc_wake_interval_ms >= 12000
      && sleepStart.rtc_wake_interval_ms <= 28000,
    sleep_pixels_and_tick_do_not_change:
      sleepStart.frame_signature === sleepLater.frame_signature
      && sleepStart.tick === sleepLater.tick
      && sleepStart.stable_commits === sleepLater.stable_commits,
    sleep_ornament_and_body_are_fixed:
      sleepContract.stable_ornament === "sleepy_stage_3_fixed_static"
      && sleepContract.main_scheduler === "stopped_while_locked",
    one_wake_restores_one_scheduler_and_transition:
      wake.scheduler_active
      && wake.transition_active
      && wakeTrace.length === 1
      && wakeTrace[0].cancelled_pending_rtc_wake === true
      && wakeSettled.selected === "calm",
    rtc_wake_intervals_are_replayable_and_nonperiodic:
      JSON.stringify(wakeIntervals.first) === JSON.stringify(wakeIntervals.second)
      && wakeIntervals.first.every(value => value >= 12000 && value <= 28000)
      && new Set(wakeIntervals.first).size >= 8
      && wakeIntervals.first.every((value, index, rows) =>
        index === 0 || value !== rows[index - 1]),
    no_touch_autonomous_wake_restores_life:
      !autoSleepStart.compressed.scheduler_active
      && autoSleepStart.compressed.pending_count === 1
      && autoSleepWaiting.locked
      && !autoSleepWaiting.scheduler_active
      && autoSleepWaiting.frame_signature
        === autoSleepStart.sleep.frame_signature
      && autonomousWake.snapshot.scheduler_active
      && autonomousWake.snapshot.transition_active
      && autonomousWake.trace.filter(row =>
        row.type === "low_power_rtc_wake").length === 1,
    retract_geometry_is_exact_reverse:
      retractFrames.map(row => row.geometry.origin[0]).join(",")
        === "19,9,0,-10,-20",
    real_pull_release_retains_recording:
      realPullLocked.active_mode === "recording"
      && realPullReleased.active_mode === "recording"
      && realPullReleased.pull_active,
    real_reverse_drag_returns_to_expression:
      realReverseSettled.state.active_mode === "expression"
      && realReverseProgress.every((value, index, rows) =>
        index === 0 || value <= rows[index - 1]),
    silence_event_exits_without_timed_reverse_path:
      silenceAccepted.accepted
      && silenceAccepted.source === "voice_activation.auto_stop_silence"
      && silenceProgress.length === 0
      && silenceSettled.trace.filter(row =>
        row.type === "commit" && row.phase === "recording_exit_restore").length === 1,
    direct_exit_has_no_retract_reentry_window:
      blockedRetractInputs.length === 0
      && !silenceSettled.state.retract_active,
    listener_boundary_not_browser_vad:
      recordingContract.shared_voice_control.browser_vad === false
      && recordingContract.shared_voice_control.microphone_permission === false
      && recordingContract.shared_voice_control.listener_silence_stop_ms === 1800
      && recordingContract.shared_voice_control.listener_tail_ms === 350,
    restore_happens_in_one_exit_commit:
      silenceSettled.state.active_mode === "expression"
      && !silenceSettled.state.retract_active
      && recordingContract.exit_path.stages === 1
      && recordingContract.exit_path.cadence_ms === 0,
    hardware_contact_zero:
      sleepContract.hardware_contact === 0
      && recordingContract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_752_753.low_power_recording_retract.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    sleep: {
      drowsy_frames: drowsyFrames,
      drowsy_plan: drowsyStart,
      start: sleepStart,
      later: sleepLater,
      contract: sleepContract,
      wake,
      wake_trace_count: wakeTrace.length
    },
    recording: {
      contract: recordingContract,
      retract_origins: retractFrames.map(row => row.geometry.origin),
      real_reverse_progress: realReverseProgress,
      silence_reverse_progress: silenceProgress
    },
    screenshot:
      ".cache/validation/comp-req-752-753-low-power-recording-retract/screenshots/sleep-and-reverse-path.png",
    hardware_contact: 0
  };
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(artifactRoot, "MACHINE_READY.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify({
  status: result.status,
  checks: result.checks,
  screenshot: result.screenshot
}, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
