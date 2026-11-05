#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-760-761-speaker-wave-natural-blink");
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(screenshotRoot, { recursive: true });

function loadPlaywright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
  ].filter(Boolean)) {
    try { return require(name); } catch {}
  }
  throw new Error("Playwright unavailable");
}

const hash = values => {
  let value = 2166136261;
  for (const bit of values) value = Math.imul(value ^ bit, 16777619);
  return (value >>> 0).toString(16).padStart(8, "0");
};

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1050 } });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq760Contract === "function"
    && typeof window.__compReq761Contract === "function");

  const canvasSample = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const bits = [];
    const rgba = new Set();
    for (let offset = 0; offset < data.length; offset += 4) {
      bits.push(data[offset] < 128 ? 1 : 0);
      rgba.add(`${data[offset]},${data[offset + 1]},${data[offset + 2]},${data[offset + 3]}`);
    }
    return {
      label,
      bits,
      rgba: [...rgba].sort(),
      data_url: canvas.toDataURL("image/png")
    };
  }, label);

  await page.evaluate(() => window.__compReq714ClearTrace());
  await page.click('[data-mode="speaker"]');
  const speakerStages = [];
  for (let stage = 0; stage < 4; stage += 1) {
    if (stage > 0) {
      await page.waitForFunction(target => {
        const commits = window.__compReq599Snapshot().trace.filter(row =>
          row.type === "commit" && row.mode === "speaker");
        return (commits.at(-1)?.envelope?.entry_wave_progress ?? -1) >= target;
      }, stage / 3);
    }
    const frame = await canvasSample(`speaker_wave_${stage}`);
    const trace = await page.evaluate(() => window.__compReq599Snapshot().trace);
    const commit = [...trace].reverse().find(row =>
      row.type === "commit" && row.mode === "speaker");
    const waveColumns = [];
    const body = [];
    const outside = [];
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const bit = frame.bits[y * 200 + x];
        if (x >= 178 && x <= 197 && y >= 156 && y < 184 && bit) waveColumns.push(x);
        if (x >= 158 && x <= 175 && y >= 156 && y < 184) body.push(bit);
        if (!(x >= 158 && x <= 197 && y >= 156 && y < 184)) outside.push(bit);
      }
    }
    speakerStages.push({
      ...frame,
      progress: commit?.envelope?.entry_wave_progress ?? null,
      commit_at: commit?.at ?? null,
      wave_columns: [...new Set(waveColumns)].sort((a, b) => a - b),
      body_hash: hash(body),
      outside_hash: hash(outside)
    });
  }
  await page.evaluate(() => window.__compReq761ForceNextBlink());
  await page.waitForTimeout(520);
  const speakerBlinkClosed = await page.evaluate(() => {
    const commits = window.__compReq599Snapshot().trace.filter(row =>
      row.type === "commit" && row.mode === "speaker");
    return commits.at(-1);
  });
  await page.waitForTimeout(520);
  const speakerBlinkOpen = await page.evaluate(() => {
    const commits = window.__compReq599Snapshot().trace.filter(row =>
      row.type === "commit" && row.mode === "speaker");
    return commits.at(-1);
  });

  const blinkContract = await page.evaluate(() => window.__compReq761Contract());
  const speakerContract = await page.evaluate(() => window.__compReq760Contract());
  const familyRows = [];
  for (const family of blinkContract.awake_families) {
    await page.evaluate(family => window.__compReq761FreezeBlink(family, false), family);
    const open = await canvasSample(`${family}_open`);
    await page.evaluate(family => window.__compReq761FreezeBlink(family, true), family);
    const closed = await canvasSample(`${family}_closed`);
    const bounds = blinkContract.generated_eye_bounds[family];
    const differences = [];
    for (let index = 0; index < open.bits.length; index += 1) {
      if (open.bits[index] !== closed.bits[index]) {
        differences.push([index % 200, Math.floor(index / 200)]);
      }
    }
    const insideEyes = ([x, y]) => bounds.some(([bx, by, width, height]) =>
      x >= bx - 2 && x < bx + width + 2 && y >= by - 2 && y < by + height + 2);
    const eyeInk = bounds.map(([bx, by, width, height]) => {
      let ink = 0;
      for (let y = by - 2; y < by + height + 2; y += 1) {
        for (let x = bx - 2; x < bx + width + 2; x += 1) {
          if (x >= 0 && x < 200 && y >= 0 && y < 200) ink += closed.bits[y * 200 + x];
        }
      }
      return ink;
    });
    familyRows.push({
      family,
      open,
      closed,
      difference_count: differences.length,
      differences_only_in_eyes: differences.length > 0 && differences.every(insideEyes),
      closed_eye_ink: eyeInk
    });
  }

  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq761ResetRuntime("curious", true);
  });
  await page.waitForTimeout(Math.max(...blinkContract.interval_ms) + 1200);
  const runtimeBlink = await page.evaluate(() =>
    window.__compReq599Snapshot().trace.filter(row => row.type === "commit"));
  const closedIndex = runtimeBlink.findIndex(row => row.blink === true);
  const runtimeClosed = closedIndex >= 0 ? runtimeBlink[closedIndex] : null;
  const runtimeOpen = closedIndex >= 0 ? runtimeBlink[closedIndex + 1] : null;
  const runtimeStart = runtimeBlink[0] || null;

  await page.evaluate(() => {
    window.__compReq752EnterSleep("comp_req_761_deep_sleep_audit");
    window.__compReq714ClearTrace();
  });
  await page.waitForTimeout(1200);
  const deepSleep = await page.evaluate(() => ({
    state: window.__compReq752Snapshot(),
    trace: window.__compReq599Snapshot().trace
  }));

  const cards = [
    ...speakerStages.map(row => ({
      title: `${row.label} · 波宽 ${row.wave_columns.length}`,
      data_url: row.data_url
    })),
    ...familyRows.map(row => ({
      title: `${row.family} · 自然闭眼`,
      data_url: row.closed.data_url
    }))
  ];
  await page.evaluate(cards => {
    document.body.innerHTML = "<main><h1>COMP-REQ-760/761 扬声器渐出与自然眨眼</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0", background: "#202426", color: "#fff", fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid", gridTemplateColumns: "repeat(4, 260px)", gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = card.data_url;
      image.width = 260;
      image.height = 260;
      image.style.imageRendering = "pixelated";
      caption.textContent = card.title;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, cards);
  const screenshotPath = path.join(screenshotRoot, "speaker-wave-and-natural-blinks.png");
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const progress = speakerStages.map(row => row.progress);
  const widths = speakerStages.map(row => row.wave_columns.length);
  const gaps = speakerStages.slice(1).map((row, index) =>
    row.commit_at - speakerStages[index].commit_at);
  const firstColumns = speakerStages.map(row => row.wave_columns[0] ?? null);
  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    speaker_entry_progress_exact: progress.every((value, index) =>
      Math.abs(value - [0, 1 / 3, 2 / 3, 1][index]) < 0.001),
    speaker_wave_width_strictly_grows: widths[0] === 0
      && widths.every((value, index) => index === 0 || value > widths[index - 1]),
    speaker_wave_grows_from_inner_endpoint_outward:
      firstColumns[0] === null && firstColumns.slice(1).every(value => value === 178),
    speaker_body_stable_during_entry:
      new Set(speakerStages.map(row => row.body_hash)).size === 1,
    non_speaker_pixels_stable_during_entry:
      new Set(speakerStages.map(row => row.outside_hash)).size === 1,
    speaker_entry_cadence_matches_epaper:
      gaps.every(value => value >= 470 && value <= 560),
    speaker_blinks_after_entry_and_opens_next_commit:
      speakerBlinkClosed?.blink === true
      && speakerBlinkClosed?.envelope?.entry_wave_progress === 1
      && speakerBlinkOpen?.blink === false,
    all_awake_families_have_eye_only_blink:
      familyRows.length === 9
      && familyRows.every(row =>
        row.differences_only_in_eyes
        && row.closed_eye_ink.every(value => value > 5)),
    runtime_blink_occurs_in_human_interval:
      runtimeStart && runtimeClosed
      && runtimeClosed.at - runtimeStart.at >= blinkContract.first_interval_ms - 80
      && runtimeClosed.at - runtimeStart.at <= blinkContract.first_interval_ms + 540,
    runtime_closed_one_commit_then_open:
      runtimeClosed?.blink === true && runtimeOpen?.blink === false,
    deep_sleep_never_blinks_or_schedules_life:
      deepSleep.state.locked
      && !deepSleep.state.scheduler_active
      && deepSleep.trace.every(row => row.blink !== true),
    strict_1bpp:
      [...speakerStages, ...familyRows.flatMap(row => [row.open, row.closed])]
        .every(row => row.rgba.every(value =>
          ["0,0,0,255", "255,255,255,255"].includes(value))),
    contracts_match:
      speakerContract.entry.stages === 4
      && speakerContract.entry.cadence_ms === 500
      && speakerContract.entry.direction === "from_speaker_mouth_outward_right"
      && blinkContract.closed_commits === 1
      && blinkContract.exact_open_next_commit
      && Math.min(...blinkContract.interval_ms) >= 5200
      && Math.max(...blinkContract.interval_ms) <= 9200,
    hardware_contact_zero:
      speakerContract.hardware_contact === 0 && blinkContract.hardware_contact === 0
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    checks,
    evidence: {
      speaker_progress: progress,
      speaker_wave_width_columns: widths,
      speaker_first_visible_columns: firstColumns,
      speaker_commit_gaps_ms: gaps.map(value => Math.round(value)),
      awake_blink_families: familyRows.map(row => ({
        family: row.family,
        difference_count: row.difference_count,
        differences_only_in_eyes: row.differences_only_in_eyes,
        closed_eye_ink: row.closed_eye_ink
      })),
      runtime_blink_interval_ms:
        runtimeStart && runtimeClosed ? Math.round(runtimeClosed.at - runtimeStart.at) : null,
      browser_errors: browserErrors
    },
    screenshot:
      ".cache/validation/comp-req-760-761-speaker-wave-natural-blink/screenshots/speaker-wave-and-natural-blinks.png"
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
