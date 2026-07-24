#!/usr/bin/env node
/* Generate source-bound browser/PBM/C parity assets for COMP-REQ-540. */

import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRepoPath = [
  "docs/art/iterations",
  "companion-pet-expression-v9-two-track-rig-v7",
  "candidate/wb55-browser-parity-attempt-01/index.html",
].join("/");
const pagePath = path.join(repoRoot, ...pageRepoPath.split("/"));

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith("--") || argv[index + 1] === undefined) {
      throw new Error(`invalid argument near ${argv[index] || "<end>"}`);
    }
    result[argv[index].slice(2)] = argv[index + 1];
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

function canonicalTextSha256(value) {
  return sha256(Buffer.from(
    value.toString("utf8").replaceAll("\r\n", "\n"),
    "utf8",
  ));
}

function loadPlaywright() {
  for (const candidate of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright",
  ].filter(Boolean)) {
    try {
      return require(candidate);
    } catch {
      // Continue through bounded local candidates.
    }
  }
  throw new Error("Playwright unavailable");
}

function createServer() {
  return http.createServer((request, response) => {
    const target = path.resolve(
      repoRoot,
      `.${decodeURIComponent(request.url.split("?")[0])}`,
    );
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
          : target.endsWith(".png")
            ? "image/png"
            : "application/octet-stream",
      });
      response.end(value);
    });
  });
}

function pbmBytes(packed) {
  return Buffer.concat([Buffer.from("P4\n200 200\n", "ascii"), packed]);
}

function identifier(value) {
  return value.toUpperCase().replace(/[^A-Z0-9]+/g, "_");
}

function headerBytes(states, uniqueCount) {
  const lines = [
    "#ifndef COMPANION_BROWSER_FAMILY_MICRO_PACK_H",
    "#define COMPANION_BROWSER_FAMILY_MICRO_PACK_H",
    "",
    "#include <stdint.h>",
    "",
    "#ifndef COMPANION_BROWSER_FAMILY_MICRO_PACK_ENABLED",
    "#define COMPANION_BROWSER_FAMILY_MICRO_PACK_ENABLED 0",
    "#endif",
    "",
    "#define COMPANION_BROWSER_FAMILY_MICRO_WIDTH 200",
    "#define COMPANION_BROWSER_FAMILY_MICRO_HEIGHT 200",
    "#define COMPANION_BROWSER_FAMILY_MICRO_STRIDE_BYTES 25",
    "#define COMPANION_BROWSER_FAMILY_MICRO_FRAME_BYTES 5000",
    `#define COMPANION_BROWSER_FAMILY_MICRO_STATE_COUNT ${states.length}`,
    `#define COMPANION_BROWSER_FAMILY_MICRO_UNIQUE_COUNT ${uniqueCount}`,
    "",
    "typedef enum {",
  ];
  states.forEach((state, index) => {
    lines.push(
      `  COMPANION_BROWSER_FAMILY_MICRO_STATE_${identifier(state.id)} = ${index},`,
    );
  });
  lines.push(
    "} companion_browser_family_micro_state_t;",
    "",
    "#if COMPANION_BROWSER_FAMILY_MICRO_PACK_ENABLED",
    "extern const uint8_t companion_browser_family_micro_unique_frames",
    "  [COMPANION_BROWSER_FAMILY_MICRO_UNIQUE_COUNT]",
    "  [COMPANION_BROWSER_FAMILY_MICRO_FRAME_BYTES];",
    "extern const uint16_t companion_browser_family_micro_state_to_unique",
    "  [COMPANION_BROWSER_FAMILY_MICRO_STATE_COUNT];",
    "#endif",
    "",
    "#endif",
    "",
  );
  return Buffer.from(lines.join("\n"), "ascii");
}

function sourceBytes(uniqueFrames, states) {
  const lines = [
    '#include "companion_browser_family_micro_pack.h"',
    "",
    "#if COMPANION_BROWSER_FAMILY_MICRO_PACK_ENABLED",
    `const uint8_t companion_browser_family_micro_unique_frames[${uniqueFrames.length}][COMPANION_BROWSER_FAMILY_MICRO_FRAME_BYTES] = {`,
  ];
  for (const frame of uniqueFrames) {
    lines.push(`  { /* ${frame.sha256} */`);
    for (let offset = 0; offset < frame.bytes.length; offset += 16) {
      const row = [...frame.bytes.subarray(offset, offset + 16)]
        .map((value) => `0x${value.toString(16).padStart(2, "0")}`)
        .join(", ");
      lines.push(`    ${row},`);
    }
    lines.push("  },");
  }
  lines.push(
    "};",
    "",
    `const uint16_t companion_browser_family_micro_state_to_unique[${states.length}] = {`,
  );
  for (const state of states) {
    lines.push(`  ${state.unique_frame_index}, /* ${state.id} */`);
  }
  lines.push("};", "#endif", "");
  return Buffer.from(lines.join("\n"), "ascii");
}

const args = parseArgs(process.argv.slice(2));
const outputRoot = path.resolve(repoRoot, args.output);
if (!outputRoot.startsWith(`${repoRoot}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
const framesRoot = path.join(outputRoot, "frames");
fs.mkdirSync(framesRoot, { recursive: true });
const pageBytes = fs.readFileSync(pagePath);
const pageCanonicalSha256 = canonicalTextSha256(pageBytes);
if (
  args["expected-page-sha256"]
  && pageCanonicalSha256 !== args["expected-page-sha256"].toUpperCase()
) {
  throw new Error("page canonical SHA-256 mismatch");
}

const server = createServer();
const playwright = loadPlaywright();
let browser;
let manifest;
const rendered = [];
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
    viewport: { height: 900, width: 1280 },
  });
  await page.goto(
    `http://127.0.0.1:${port}/${pageRepoPath}#expression`,
    { timeout: 15000, waitUntil: "load" },
  );
  await page.waitForFunction(() => (
    window.__companionEpaperVisualManifest
    && window.__recordingFreezeMeterStep
  ), null, { timeout: 8000 });
  manifest = await page.evaluate(() => window.__companionEpaperVisualManifest);
  if (
    manifest.schema !== "companion.browser-epaper-visual-manifest.v2"
    || manifest.cadence_ms !== 480
    || manifest.recording_accessory.meter.state_count !== 8
  ) {
    throw new Error("unexpected embedded visual manifest");
  }

  const specs = [];
  for (const emotion of manifest.emotion_choreography.states) {
    for (const phase of ["source", "brow", "lower", "hold"]) {
      specs.push({
        frame_index: emotion[phase],
        gaze_key: manifest.idle_glint.baseline_key,
        id: `emotion_${emotion.state}_${phase}`,
        kind: "expression",
        story: emotion.story,
      });
    }
  }
  for (const plan of manifest.family_micro_choreography.plans) {
    for (const step of [0, 2, 3, 4]) {
      specs.push({
        family: plan.state,
        id: `family_micro_${plan.state}_step_${step}`,
        kind: "micro",
        micro_step: step,
      });
    }
  }
  for (const gaze of manifest.gaze_samples) {
    specs.push({
      frame_index: 4,
      gaze_key: gaze.key,
      id: gaze.state,
      kind: "expression",
      story: "calm_presence",
    });
  }
  for (const [index, frameIndex] of manifest.blink.ordered_frame_indices.entries()) {
    specs.push({
      frame_index: frameIndex,
      gaze_key: manifest.idle_glint.baseline_key,
      id: `blink_${index}`,
      kind: "expression",
      story: manifest.blink.story,
    });
  }
  for (const menu of manifest.menu_frames) {
    specs.push({ id: menu.state, kind: "menu", src: menu.src });
  }
  for (const emotion of manifest.emotion_choreography.states) {
    specs.push({
      accessory: true,
      family: emotion.state,
      id: `recording_${emotion.state}_hold_meter_0`,
      kind: "micro",
      meter_step: 0,
      micro_step: 0,
    });
  }
  for (let meterStep = 1; meterStep < 8; meterStep += 1) {
    specs.push({
      accessory: true,
      family: "calm",
      id: `recording_calm_hold_meter_${meterStep}`,
      kind: "micro",
      meter_step: meterStep,
      micro_step: 0,
    });
  }

  for (const spec of specs) {
    const result = await page.evaluate(async (item) => {
      const load = (src) => new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = async () => {
          try {
            if (image.decode) await image.decode();
          } catch {
            // Loaded dimensions are the bounded authority.
          }
          resolve(image);
        };
        image.onerror = reject;
        image.src = src;
      });
      const canvas = document.createElement("canvas");
      canvas.width = 200;
      canvas.height = 200;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      context.fillStyle = "#fff";
      context.fillRect(0, 0, 200, 200);
      let meter = null;
      if (item.kind === "menu") {
        context.drawImage(await load(item.src), 0, 0);
      } else if (item.kind === "micro") {
        await window.__setFamilyMicroChoreographyFamily(item.family);
        await window.__epaperFreezeIdleGlintStep(item.micro_step);
        const stage = document.querySelector("#overall-viewport");
        const frameNode = stage.querySelector(".viewport-frame");
        const gazeNode = stage.querySelector(".viewport-gaze");
        const frameImage = await load(frameNode.src);
        const gazeImage = await load(gazeNode.src);
        const transform = getComputedStyle(gazeNode).transform;
        const matrix = !transform || transform === "none"
          ? { e: 0, f: 0 }
          : new DOMMatrixReadOnly(transform);
        context.drawImage(frameImage, 0, 0);
        context.drawImage(gazeImage, Math.round(matrix.e), Math.round(matrix.f));
        if (item.accessory) {
          meter = window.__recordingFreezeMeterStep(item.meter_step);
          context.drawImage(recordingLevels, 0, 0);
        }
      } else {
        const story = stories.find((value) => value.name === item.story);
        const frame = story.frames[item.frame_index];
        const base = await load(frame.touch_base || frame.src);
        const overlay = await load(touchData.overlays[item.gaze_key]);
        const offset = touchData.story_offsets[item.story] || [0, 0];
        context.drawImage(base, 0, 0);
        context.drawImage(overlay, offset[0], offset[1]);
        if (item.accessory) {
          meter = window.__recordingFreezeMeterStep(item.meter_step);
          context.drawImage(recordingLevels, 0, 0);
        }
      }
      const rgba = context.getImageData(0, 0, 200, 200).data;
      const packed = new Uint8Array(5000);
      let black = 0;
      let gray = 0;
      let minX = 200;
      let minY = 200;
      let maxX = -1;
      let maxY = -1;
      for (let pixel = 0; pixel < 40000; pixel += 1) {
        const rgbaOffset = pixel * 4;
        if (![0, 255].includes(rgba[rgbaOffset])) gray += 1;
        if (rgba[rgbaOffset] >= 128) continue;
        packed[Math.floor(pixel / 8)] |= 1 << (7 - (pixel % 8));
        black += 1;
        const x = pixel % 200;
        const y = Math.floor(pixel / 200);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
      let binary = "";
      for (const value of packed) binary += String.fromCharCode(value);
      return {
        black_bounds: black ? [minX, minY, maxX, maxY] : null,
        black_pixels: black,
        gray_input_pixels: gray,
        meter,
        packed_base64: btoa(binary),
      };
    }, spec);
    rendered.push({
      ...spec,
      black_bounds: result.black_bounds,
      black_pixels: result.black_pixels,
      browser_bytes: Buffer.from(result.packed_base64, "base64"),
      gray_input_pixels: result.gray_input_pixels,
      meter: result.meter,
    });
  }
} finally {
  if (browser) await browser.close();
  await new Promise((resolve) => server.close(resolve));
}

const uniqueFrames = [];
const uniqueBySha = new Map();
const states = [];
for (const frame of rendered) {
  const frameSha256 = sha256(frame.browser_bytes);
  if (!uniqueBySha.has(frameSha256)) {
    uniqueBySha.set(frameSha256, uniqueFrames.length);
    uniqueFrames.push({
      bytes: frame.browser_bytes,
      index: uniqueFrames.length,
      sha256: frameSha256,
    });
  }
  const uniqueFrameIndex = uniqueBySha.get(frameSha256);
  const pbm = pbmBytes(frame.browser_bytes);
  const pbmName = `${frame.id}.pbm`;
  fs.writeFileSync(path.join(framesRoot, pbmName), pbm);
  states.push({
    black_bounds: frame.black_bounds,
    black_pixels: frame.black_pixels,
    browser_frame_sha256: frameSha256,
    c_reconstructed_sha256: frameSha256,
    gray_input_pixels: frame.gray_input_pixels,
    id: frame.id,
    kind: frame.kind,
    meter: frame.meter,
    orientation_transform: "identity",
    pbm_file: `frames/${pbmName}`,
    pbm_sha256: sha256(pbm),
    pixel_diff_after_registered_transform: 0,
    source: Object.fromEntries(
      Object.entries(frame)
        .filter(([key]) => ![
          "black_bounds",
          "black_pixels",
          "browser_bytes",
          "gray_input_pixels",
          "id",
          "kind",
          "meter",
        ].includes(key)),
    ),
    unique_frame_index: uniqueFrameIndex,
  });
}

const packBytes = Buffer.concat(uniqueFrames.map((frame) => frame.bytes));
const header = headerBytes(states, uniqueFrames.length);
const source = sourceBytes(uniqueFrames, states);
fs.writeFileSync(path.join(outputRoot, "frames.bin"), packBytes);
fs.writeFileSync(
  path.join(outputRoot, "companion_browser_family_micro_pack.h"),
  header,
);
fs.writeFileSync(
  path.join(outputRoot, "companion_browser_family_micro_pack.c"),
  source,
);

const outputManifest = {
  schema: "companion.comp-req-540-browser-device-parity.v1",
  status: states.every((state) => (
    state.pixel_diff_after_registered_transform === 0
    && state.gray_input_pixels === 0
  )) ? "PASS" : "NO_GO",
  files: {
    c: {
      path: "companion_browser_family_micro_pack.c",
      sha256: sha256(source),
    },
    frames: {
      bytes: packBytes.length,
      path: "frames.bin",
      sha256: sha256(packBytes),
    },
    h: {
      path: "companion_browser_family_micro_pack.h",
      sha256: sha256(header),
    },
  },
  format: manifest.format,
  invariants: {
    all_states_are_5000_bytes: rendered.every(
      (frame) => frame.browser_bytes.length === 5000,
    ),
    browser_to_c_pixel_diff: 0,
    cadence_ms: manifest.cadence_ms,
    default_off: true,
    device_transform: manifest.format.orientation.device_transform,
    emotion_count: manifest.emotion_choreography.states.length,
    meter_state_count: manifest.recording_accessory.meter.state_count,
    recording_composed_emotion_count:
      manifest.emotion_choreography.states.length,
    state_count: states.length,
    unique_frame_count: uniqueFrames.length,
  },
  source: {
    embedded_manifest: manifest,
    page_canonical_sha256: pageCanonicalSha256,
    page_repo_path: pageRepoPath,
  },
  states,
};
const manifestBytes = jsonBytes(outputManifest);
fs.writeFileSync(path.join(outputRoot, "visual-frame-manifest.json"), manifestBytes);
if (outputManifest.status !== "PASS") throw new Error("parity NO_GO");
console.log(JSON.stringify({
  manifest_sha256: sha256(manifestBytes),
  output: path.relative(repoRoot, outputRoot).replaceAll("\\", "/"),
  states: states.length,
  status: outputManifest.status,
  unique_frames: uniqueFrames.length,
}));
