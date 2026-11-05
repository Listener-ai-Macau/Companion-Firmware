#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-749-recovered-mouths");
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
const referencePath = path.join(
  root,
  ".cache/validation/comp-req-584-mouth-reference/mouth-reference-attempt-04-soft.png"
);
fs.mkdirSync(screenshotRoot, { recursive: true });

function playwright() {
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

const families = [
  "calm",
  "curious",
  "delighted",
  "warm",
  "playful",
  "sleepy",
  "bashful",
  "thoughtful",
  "focused",
  "alert"
];

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1160, height: 980 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() => typeof window.__compReq749Contract === "function");
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  const contract = await page.evaluate(() => window.__compReq749Contract());
  const frames = [];
  for (const family of families) {
    for (const phase of ["hold", "accent"]) {
      const frame = await page.evaluate(({ family, phase }) => {
        const pose = window.__compReq749FreezeFamilyMouth(
          family,
          phase,
          phase === "accent" ? 1 : 0,
          "rest"
        );
        const canvas = document.querySelector("#face");
        const context = canvas.getContext("2d", { willReadFrequently: true });
        const image = context.getImageData(0, 0, 200, 200);
        const bounds = pose.mouth_placement.rasterBounds;
        const isInk = (x, y) => image.data[(y * 200 + x) * 4] < 128;
        const ink = [];
        for (let y = bounds.top; y <= bounds.bottom; y += 1) {
          for (let x = bounds.left; x <= bounds.right; x += 1) {
            if (isInk(x, y)) ink.push([x, y]);
          }
        }
        const pending = new Set(ink.map(([x, y]) => `${x}:${y}`));
        let components = 0;
        while (pending.size) {
          components += 1;
          const seed = pending.values().next().value;
          pending.delete(seed);
          const queue = [seed.split(":").map(Number)];
          while (queue.length) {
            const [x, y] = queue.pop();
            for (let dy = -1; dy <= 1; dy += 1) {
              for (let dx = -1; dx <= 1; dx += 1) {
                if (!dx && !dy) continue;
                const key = `${x + dx}:${y + dy}`;
                if (pending.delete(key)) queue.push([x + dx, y + dy]);
              }
            }
          }
        }
        const rowSegments = [];
        for (let y = bounds.top; y <= bounds.bottom; y += 1) {
          let segments = 0;
          let active = false;
          for (let x = bounds.left; x <= bounds.right; x += 1) {
            const next = isInk(x, y);
            if (next && !active) segments += 1;
            active = next;
          }
          rowSegments.push(segments);
        }
        let nonBinary = 0;
        for (let index = 0; index < image.data.length; index += 4) {
          const red = image.data[index];
          if ((red !== 0 && red !== 255)
              || image.data[index + 1] !== red
              || image.data[index + 2] !== red
              || image.data[index + 3] !== 255) {
            nonBinary += 1;
          }
        }
        const crop = document.createElement("canvas");
        const padding = 4;
        crop.width = bounds.width + padding * 2;
        crop.height = bounds.height + padding * 2;
        crop.getContext("2d").drawImage(
          canvas,
          bounds.left - padding,
          bounds.top - padding,
          crop.width,
          crop.height,
          0,
          0,
          crop.width,
          crop.height
        );
        return {
          family,
          phase,
          mouth_pose: pose.mouth_pose,
          bounds,
          clear_bounds: pose.mouth_placement.clearBounds,
          ink_pixels: ink.length,
          components,
          row_segments: rowSegments,
          non_binary_pixels: nonBinary,
          face_data_url: canvas.toDataURL("image/png"),
          crop_data_url: crop.toDataURL("image/png")
        };
      }, { family, phase });
      frames.push(frame);
    }
  }

  const forced = [];
  for (const poseName of ["recovered_gentle_smile", "recovered_open_smile"]) {
    forced.push(await page.evaluate(poseName => {
      const pose = window.__compReq749FreezeRaster("warm", poseName);
      const data = document.querySelector("#face")
        .getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      return {
        pose: poseName,
        clear_bounds: pose.drawn_placement.clearBounds,
        pixels: Array.from(data)
      };
    }, poseName));
  }
  const union = {
    left: Math.min(...forced.map(item => item.clear_bounds.left)),
    top: Math.min(...forced.map(item => item.clear_bounds.top)),
    right: Math.max(...forced.map(item => item.clear_bounds.right)),
    bottom: Math.max(...forced.map(item => item.clear_bounds.bottom))
  };
  let outsideMouthDifferences = 0;
  for (let y = 0; y < 200; y += 1) {
    for (let x = 0; x < 200; x += 1) {
      if (x >= union.left && x <= union.right && y >= union.top && y <= union.bottom) {
        continue;
      }
      const index = (y * 200 + x) * 4;
      if (forced[0].pixels[index] !== forced[1].pixels[index]) outsideMouthDifferences += 1;
    }
  }

  await page.evaluate(cards => {
    document.body.innerHTML = "<main><h1>COMP-REQ-749 native 200x200 full-face mouth audit</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "18px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gridTemplateColumns: "repeat(5, 200px)",
      gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      Object.assign(figure.style, { margin: "0", background: "#fff" });
      image.src = card.face_data_url;
      image.width = 200;
      image.height = 200;
      image.style.display = "block";
      image.style.imageRendering = "pixelated";
      caption.textContent = `${card.family} / ${card.phase} / ${card.mouth_pose}`;
      Object.assign(caption.style, {
        minHeight: "34px",
        boxSizing: "border-box",
        padding: "5px",
        background: "#303638",
        color: "#fff",
        fontSize: "11px"
      });
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, frames);
  await page.screenshot({
    path: path.join(screenshotRoot, "all-families-hold-accent-native-200.png"),
    fullPage: true
  });

  await page.evaluate(cards => {
    document.querySelector("h1").textContent = "COMP-REQ-749 recovered generated mouth crops";
    const section = document.querySelector("section");
    section.replaceChildren();
    section.style.gridTemplateColumns = "repeat(4, 260px)";
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      Object.assign(figure.style, {
        margin: "0",
        minHeight: "170px",
        display: "grid",
        placeItems: "center",
        background: "#fff"
      });
      image.src = card.crop_data_url;
      image.width = Math.min(230, (card.bounds.width + 8) * 10);
      image.height = (card.bounds.height + 8) * 10;
      image.style.imageRendering = "pixelated";
      caption.textContent =
        `${card.family} / ${card.phase} / ${card.mouth_pose} / ${card.ink_pixels}px`;
      Object.assign(caption.style, {
        alignSelf: "end",
        width: "100%",
        boxSizing: "border-box",
        padding: "6px",
        background: "#303638",
        color: "#fff",
        fontSize: "11px"
      });
      figure.append(image, caption);
      section.append(figure);
    }
  }, frames);
  await page.screenshot({
    path: path.join(screenshotRoot, "recovered-mouth-crops.png"),
    fullPage: true
  });

  await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.evaluate(() => {
    window.__compReq714SetScheduler(false);
    window.__compReq714FreezeLifeAction("warm", "soften", "hold", 0, 0, true);
  });
  const runtimeDataUrl = await page.locator("#face").evaluate(canvas => canvas.toDataURL("image/png"));
  fs.writeFileSync(
    path.join(screenshotRoot, "warm-heart-runtime-native-200.png"),
    Buffer.from(runtimeDataUrl.split(",")[1], "base64")
  );
  await page.screenshot({
    path: path.join(screenshotRoot, "fixed-url-warm-heart-runtime.png"),
    fullPage: true
  });

  const pairRows = families.map(family =>
    frames.filter(frame => frame.family === family));
  const warmRows = frames.filter(frame => frame.family === "warm");
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    recovered_reference_hash_exact:
      crypto.createHash("sha256").update(fs.readFileSync(referencePath)).digest("hex").toUpperCase()
        === "34D958845B489222F86BAAC764744E2A579015DF48BEFD65C5FDBBE08D6526EF",
    deterministic_1bpp_reduction_declared:
      contract.integration === "deterministic_1bpp_reduction_at_generated_face_mouth_anchor"
      && contract.direct_generated_mouth_morph === false,
    recovered_shape_families_complete:
      contract.recovered_rasters.length >= 14
      && ["smile", "open", "pressed", "side", "thoughtful"].every(token =>
        contract.recovered_rasters.some(name => name.includes(token))),
    ten_family_pairs_explicit:
      families.every(family => contract.family_pairs[family]?.hold
        && contract.family_pairs[family]?.accent),
    non_calm_hold_and_accent_distinct:
      pairRows.slice(1).every(([hold, accent]) =>
        hold.mouth_pose !== accent.mouth_pose),
    warm_fork_mouth_removed:
      warmRows[0].mouth_pose === "recovered_gentle_smile"
      && warmRows[1].mouth_pose === "recovered_wide_smile"
      && warmRows.every(frame =>
        frame.components === 1
        && Math.max(...frame.row_segments) <= 2),
    mouth_components_connected:
      frames.every(frame => frame.ink_pixels > 0 && frame.components === 1),
    mouth_bounds_inside_native_face:
      frames.every(frame =>
        frame.clear_bounds.left >= 0
        && frame.clear_bounds.top >= 0
        && frame.clear_bounds.right < 200
        && frame.clear_bounds.bottom < 200),
    strict_1bpp_canvas:
      frames.every(frame => frame.non_binary_pixels === 0),
    non_mouth_pixels_unchanged_between_forced_shapes:
      outsideMouthDifferences === 0,
    calm_mouth_contract_protected:
      contract.calm_guard.hold === "calm_closed_smile"
      && contract.calm_guard.breathing_and_listening === "listening_o"
      && contract.calm_guard.soften === "warm_smile",
    forbidden_symbol_mouths_declared:
      contract.forbidden_shapes.join(",")
        === "generic_w,three_peak,three_prong,fork_symbol",
    hardware_contact_zero: contract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_749.recovered_generated_mouths.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    reference: {
      path: path.relative(root, referencePath).replaceAll("\\", "/"),
      sha256: crypto.createHash("sha256").update(fs.readFileSync(referencePath)).digest("hex").toUpperCase()
    },
    frames: frames.map(({ face_data_url, crop_data_url, ...frame }) => frame),
    non_mouth_audit: {
      union_clear_bounds: union,
      outside_mouth_differences: outsideMouthDifferences
    },
    screenshots: [
      ".cache/validation/comp-req-749-recovered-mouths/screenshots/all-families-hold-accent-native-200.png",
      ".cache/validation/comp-req-749-recovered-mouths/screenshots/recovered-mouth-crops.png",
      ".cache/validation/comp-req-749-recovered-mouths/screenshots/warm-heart-runtime-native-200.png",
      ".cache/validation/comp-req-749-recovered-mouths/screenshots/fixed-url-warm-heart-runtime.png"
    ],
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
  screenshots: result.screenshots
}, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
