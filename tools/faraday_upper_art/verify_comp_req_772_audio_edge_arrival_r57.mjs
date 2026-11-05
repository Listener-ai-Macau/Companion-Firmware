import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const root = process.cwd();
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
const artifactRoot = path.join(
  root,
  ".cache/validation/comp-req-772-art-polish-r57"
);
const screenshotRoot = path.join(artifactRoot, "screenshots");
fs.mkdirSync(screenshotRoot, { recursive: true });

const require = createRequire(import.meta.url);
const loadPlaywright = () => {
  for (const name of [
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright"
  ]) {
    try {
      return require(name);
    } catch {}
  }
  throw new Error("Playwright unavailable");
};

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];

const boundsFor = (bits, predicate) => {
  const points = [];
  for (let y = 0; y < 200; y += 1) {
    for (let x = 0; x < 200; x += 1) {
      if (bits[y * 200 + x] && predicate(x, y)) points.push([x, y]);
    }
  }
  if (!points.length) return null;
  const xs = points.map(point => point[0]);
  const ys = points.map(point => point[1]);
  return [
    Math.min(...xs),
    Math.min(...ys),
    Math.max(...xs),
    Math.max(...ys)
  ];
};

let result;
try {
  const page = await browser.newPage({
    viewport: { width: 1500, height: 1000 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq759Contract === "function"
    && typeof window.__compReq760Contract === "function");

  const sample = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const bits = [];
    const rgba = new Set();
    for (let offset = 0; offset < data.length; offset += 4) {
      bits.push(data[offset] < 128 ? 1 : 0);
      rgba.add(
        `${data[offset]},${data[offset + 1]},${data[offset + 2]},${data[offset + 3]}`
      );
    }
    return {
      label,
      bits,
      rgba: [...rgba].sort(),
      data_url: canvas.toDataURL("image/png")
    };
  }, label);

  const captureMode = async mode => {
    await page.evaluate(() => window.__compReq714ClearTrace());
    await page.click(`[data-mode="${mode}"]`);
    const frames = [];
    for (let stage = 0; stage < 5; stage += 1) {
      if (stage > 0) {
        await page.waitForFunction(({ mode, target }) => {
          const commits = window.__compReq599Snapshot().trace.filter(row =>
            row.type === "commit" && row.mode === mode);
          return Math.abs(
            (commits.at(-1)?.envelope?.entry_wave_progress ?? -1) - target
          ) < 0.001;
        }, { mode, target: stage / 4 }, { timeout: 1800, polling: 15 });
      }
      const frame = await sample(`${mode}_${stage}`);
      const commit = await page.evaluate(mode => {
        const commits = window.__compReq599Snapshot().trace.filter(row =>
          row.type === "commit" && row.mode === mode);
        return commits.at(-1);
      }, mode);
      const bodyBounds = mode === "recording"
        ? boundsFor(
            frame.bits,
            (x, y) => x < 42 && y >= 177 && y <= 179
          )
        : boundsFor(
            frame.bits,
            (x, y) => x >= 150 && y >= 158 && y <= 178
              && x < 178 + Math.round((1 - (stage === 0 ? 0.2 : stage / 4)) * 40)
          );
      frames.push({
        ...frame,
        progress: commit?.envelope?.entry_wave_progress ?? null,
        commit_at: commit?.at ?? null,
        body_bounds: bodyBounds
      });
    }
    return frames;
  };

  const recordingFrames = await captureMode("recording");
  await page.click('[data-mode="expression"]');
  const speakerFrames = await captureMode("speaker");
  const recordingContract = await page.evaluate(() => window.__compReq759Contract());
  const speakerContract = await page.evaluate(() => window.__compReq760Contract());

  await page.evaluate(({ recording, speaker }) => {
    document.body.innerHTML =
      "<main><h1>Companion r57 音频饰件慢入场</h1>"
      + "<h2>录音：从左侧进入</h2><section id='recording'></section>"
      + "<h2>扬声器：从右侧进入</h2><section id='speaker'></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    for (const [id, cards] of Object.entries({ recording, speaker })) {
      const section = document.querySelector(`#${id}`);
      Object.assign(section.style, {
        display: "flex",
        gap: "12px",
        marginBottom: "22px"
      });
      for (const card of cards) {
        const figure = document.createElement("figure");
        const image = document.createElement("img");
        const caption = document.createElement("figcaption");
        Object.assign(figure.style, { margin: "0" });
        image.src = card.data_url;
        image.width = 240;
        image.height = 240;
        image.style.imageRendering = "pixelated";
        caption.textContent = `${card.label} · ${card.progress}`;
        figure.append(image, caption);
        section.append(figure);
      }
    }
  }, { recording: recordingFrames, speaker: speakerFrames });
  await page.screenshot({
    path: path.join(screenshotRoot, "audio-edge-arrival-contact-sheet.png"),
    fullPage: true
  });

  const expectedProgress = [0, 0.25, 0.5, 0.75, 1];
  const progressMatches = frames => frames.every((frame, index) =>
    Math.abs(frame.progress - expectedProgress[index]) < 0.001);
  const gaps = frames => frames.slice(1).map((frame, index) =>
    frame.commit_at - frames[index].commit_at);
  const recordingLefts = recordingFrames.map(frame => frame.body_bounds?.[0] ?? null);
  const speakerLefts = speakerFrames.map(frame => frame.body_bounds?.[0] ?? null);
  const recordingGaps = gaps(recordingFrames);
  const speakerGaps = gaps(speakerFrames);
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    strict_1bpp:
      [...recordingFrames, ...speakerFrames].every(frame =>
        frame.rgba.length === 2
        && frame.rgba.includes("0,0,0,255")
        && frame.rgba.includes("255,255,255,255")),
    five_physical_entry_frames:
      progressMatches(recordingFrames) && progressMatches(speakerFrames),
    recording_moves_right_to_lock:
      recordingLefts.every((value, index) =>
        value !== null && (index === 0 || value > recordingLefts[index - 1]))
      && recordingLefts.at(-1) === 29,
    speaker_moves_left_to_lock:
      speakerLefts.every((value, index) =>
        value !== null && (index === 0 || value < speakerLefts[index - 1]))
      && speakerLefts.at(-1) === 158,
    cadence_is_epaper_representable:
      [...recordingGaps, ...speakerGaps].every(gap => gap >= 480 && gap <= 650),
    recording_exit_remains_direct:
      recordingContract.exit.frames === 1
      && recordingContract.exit.timed_retract === false,
    speaker_exit_remains_direct:
      speakerContract.exit.frames === 1
      && speakerContract.exit.timed_retract === false,
    contracts_match_new_arrival:
      recordingContract.entry.microphone ===
        "slides_from_left_edge_to_locked_position"
      && speakerContract.entry.speaker ===
        "slides_from_right_edge_to_locked_position",
    hardware_contact_zero:
      recordingContract.hardware_contact === 0
      && speakerContract.hardware_contact === 0
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    revision: "r57",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    evidence: {
      progress: expectedProgress,
      recording_body_lefts: recordingLefts,
      speaker_body_lefts: speakerLefts,
      recording_commit_gaps_ms: recordingGaps,
      speaker_commit_gaps_ms: speakerGaps,
      browser_errors: browserErrors
    },
    screenshot:
      ".cache/validation/comp-req-772-art-polish-r57/screenshots/"
      + "audio-edge-arrival-contact-sheet.png"
  };
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(artifactRoot, `${result.status}.json`),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
process.exitCode = result.status === "MACHINE_READY" ? 0 : 1;
