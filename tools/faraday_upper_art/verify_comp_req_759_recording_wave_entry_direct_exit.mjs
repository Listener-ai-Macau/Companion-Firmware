#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-759-recording-wave-entry");
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

const hashBytes = bytes => {
  let hash = 2166136261;
  for (const value of bytes) {
    hash ^= value;
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
};

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
    window.__compReq599Ready === true
    && typeof window.__compReq759Contract === "function");
  const box = await page.locator("#face").boundingBox();
  const point = (x, y) => ({
    x: box.x + box.width * x,
    y: box.y + box.height * y
  });
  const tap = async target => {
    await page.mouse.move(target.x, target.y);
    await page.mouse.down();
    await page.waitForTimeout(45);
    await page.mouse.up();
  };
  const sample = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const pixelValues = new Set();
    const waveColumns = new Set();
    let micHash = 2166136261;
    let outsideHash = 2166136261;
    let micInk = 0;
    const mix = (hash, value) => Math.imul(hash ^ value, 16777619) >>> 0;
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const offset = (y * 200 + x) * 4;
        const black = data[offset] < 128 ? 1 : 0;
        pixelValues.add(
          `${data[offset]},${data[offset + 1]},${data[offset + 2]},${data[offset + 3]}`
        );
        if (x >= 2 && x <= 21 && y >= 156 && y < 180 && black) {
          waveColumns.add(x);
        }
        if (x >= 28 && x < 42 && y >= 158 && y < 180) {
          micHash = mix(micHash, black);
          micInk += black;
        }
        if (!(x >= 2 && x < 42 && y >= 156 && y < 180)) {
          outsideHash = mix(outsideHash, black);
        }
      }
    }
    const commits = window.__compReq599Snapshot().trace.filter(row =>
      row.type === "commit" && row.mode === "recording");
    return {
      label,
      data_url: canvas.toDataURL("image/png"),
      pixel_values: [...pixelValues].sort(),
      wave_columns: [...waveColumns].sort((a, b) => a - b),
      mic_hash: micHash.toString(16).padStart(8, "0"),
      outside_hash: outsideHash.toString(16).padStart(8, "0"),
      mic_ink: micInk,
      entry_progress: commits.at(-1)?.envelope?.entry_wave_progress ?? null,
      commit_at: commits.at(-1)?.at ?? null,
      active_mode: window.__compReq753Snapshot().active_mode
    };
  }, label);

  await page.evaluate(() => window.__compReq714ClearTrace());
  const corner = point(0.12, 0.84);
  await tap(corner);
  await page.waitForTimeout(90);
  await tap(corner);
  const stages = [await sample("wave_0")];
  for (let stage = 1; stage <= 3; stage += 1) {
    await page.waitForFunction(target => {
      const commits = window.__compReq599Snapshot().trace.filter(row =>
        row.type === "commit" && row.mode === "recording");
      return (commits.at(-1)?.envelope?.entry_wave_progress ?? -1) >= target;
    }, stage / 3, { timeout: 1800, polling: 20 });
    stages.push(await sample(`wave_${stage}`));
  }
  const entryTrace = await page.evaluate(() => window.__compReq599Snapshot().trace);
  const exitPoint = point(0.72, 0.32);
  await tap(exitPoint);
  await page.waitForTimeout(90);
  await tap(exitPoint);
  await page.waitForTimeout(100);
  const directExit = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true);
  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq753EnterRecording("listener_direct_exit_audit");
  });
  const listenerResult = await page.evaluate(() =>
    window.__compReq753InjectVoiceControl("silence_stop"));
  const listenerExit = await page.evaluate(() => ({
    state: window.__compReq753Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));
  const contract = await page.evaluate(() => window.__compReq759Contract());

  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-759 录音声波渐进场</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "flex",
      flexWrap: "wrap",
      gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = card.data_url;
      image.width = 260;
      image.height = 260;
      image.style.imageRendering = "pixelated";
      caption.textContent =
        `${card.label} · 波宽 ${card.wave_columns.length} · ${card.entry_progress}`;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, stages);
  await page.screenshot({
    path: path.join(screenshotRoot, "recording-wave-entry-stages.png"),
    fullPage: true
  });

  const progress = stages.map(stage => stage.entry_progress);
  const waveWidths = stages.map(stage => stage.wave_columns.length);
  const commitGaps = stages.slice(1).map((stage, index) =>
    stage.commit_at - stages[index].commit_at);
  const micHashes = stages.map(stage => stage.mic_hash);
  const outsideHashes = stages.map(stage => stage.outside_hash);
  const doubleExitTail = directExit.trace.filter(row =>
    row.type === "recording_exit"
    || row.type === "recording_mic_retract_start"
    || row.type === "recording_mic_retract_frame"
    || (row.type === "commit" && row.phase === "recording_exit_restore"));
  const listenerExitTail = listenerExit.trace.filter(row =>
    row.type === "recording_exit"
    || row.type === "recording_mic_retract_start"
    || row.type === "recording_mic_retract_frame"
    || (row.type === "commit" && row.phase === "recording_exit_restore"));
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    entry_progress_exact:
      progress.length === 4
      && progress.every((value, index) =>
        Math.abs(value - [0, 1 / 3, 2 / 3, 1][index]) < 0.001),
    wave_visible_width_strictly_grows:
      waveWidths[0] === 0
      && waveWidths.every((value, index) =>
        index === 0 || value > waveWidths[index - 1]),
    microphone_geometry_stable_during_entry:
      new Set(micHashes).size === 1
      && stages[0].mic_ink > 0,
    non_recording_pixels_stable_during_entry:
      new Set(outsideHashes).size === 1,
    entry_cadence_matches_epaper:
      commitGaps.every(gap => gap >= 470 && gap <= 560),
    entry_occurs_once_then_full_wave_continues:
      entryTrace.filter(row =>
        row.type === "commit"
        && row.mode === "recording"
        && row.envelope?.entry_wave_progress < 1).length === 3,
    double_tap_exit_is_one_direct_restore:
      directExit.state.active_mode === "expression"
      && doubleExitTail.filter(row => row.type === "recording_exit").length === 1
      && doubleExitTail.filter(row =>
        row.type === "commit" && row.phase === "recording_exit_restore").length === 1
      && doubleExitTail.every(row =>
        row.type !== "recording_mic_retract_start"
        && row.type !== "recording_mic_retract_frame"),
    listener_exit_is_one_direct_restore:
      listenerResult.accepted
      && listenerExit.state.active_mode === "expression"
      && listenerExitTail.filter(row => row.type === "recording_exit").length === 1
      && listenerExitTail.filter(row =>
        row.type === "commit" && row.phase === "recording_exit_restore").length === 1
      && listenerExitTail.every(row =>
        row.type !== "recording_mic_retract_start"
        && row.type !== "recording_mic_retract_frame"),
    strict_1bpp:
      stages.every(stage =>
        stage.pixel_values.every(value =>
          ["0,0,0,255", "255,255,255,255"].includes(value))),
    contract_matches:
      contract.entry.stages === 4
      && contract.entry.cadence_ms === 500
      && contract.exit.frames === 1
      && contract.exit.timed_retract === false,
    hardware_contact_zero: contract.hardware_contact === 0
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    checks,
    evidence: {
      progress,
      wave_width_columns: waveWidths,
      commit_gaps_ms: commitGaps.map(value => Math.round(value)),
      mic_hashes: micHashes,
      outside_hashes: outsideHashes,
      browser_errors: browserErrors
    },
    screenshot:
      ".cache/validation/comp-req-759-recording-wave-entry/screenshots/recording-wave-entry-stages.png"
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
