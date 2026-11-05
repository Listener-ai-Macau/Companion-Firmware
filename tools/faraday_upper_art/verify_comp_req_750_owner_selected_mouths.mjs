#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root,
  ".cache/validation/comp-req-750-owner-selected-mouths"
);
const screenshotRoot = path.join(artifactRoot, "screenshots");
const sourcePath = path.join(
  artifactRoot,
  "source/owner-selected-09-34-44.png"
);
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
const expectedSourceHash =
  "5AEA9B826AA568E553927ED51840B19895F79A426F87624ABEC516FC78AD1291";
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
const expectedPairs = {
  calm: ["calm_closed_smile", "calm_closed_smile"],
  curious: ["owner_curious_round", "owner_curious_round_open"],
  delighted: ["owner_delighted_open", "owner_delighted_open_wide"],
  warm: ["recovered_gentle_smile", "recovered_wide_smile"],
  playful: ["recovered_side_smile_left", "recovered_side_open_right"],
  sleepy: ["owner_sleepy_rest_arc", "recovered_large_open"],
  bashful: ["owner_bashful_wave", "owner_bashful_wave_deep"],
  thoughtful: ["recovered_thoughtful_left", "owner_thoughtful_deep"],
  focused: ["recovered_pressed_short", "recovered_pressed_long"],
  alert: ["owner_alert_o", "owner_alert_o_tall"]
};
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

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath))
    .digest("hex").toUpperCase();
}

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1180, height: 980 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq750Contract === "function"
    && typeof window.__compReq749FreezeFamilyMouth === "function");
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  const contract = await page.evaluate(() => window.__compReq750Contract());
  const frames = [];
  for (const family of families) {
    for (const phase of ["hold", "accent"]) {
      frames.push(await page.evaluate(({ family, phase }) => {
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
        let nonBinaryPixels = 0;
        for (let index = 0; index < image.data.length; index += 4) {
          const value = image.data[index];
          if ((value !== 0 && value !== 255)
              || image.data[index + 1] !== value
              || image.data[index + 2] !== value
              || image.data[index + 3] !== 255) {
            nonBinaryPixels += 1;
          }
        }
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
          raster_bounds: bounds,
          clear_bounds: pose.mouth_placement.clearBounds,
          ink_pixels: ink.length,
          components,
          non_binary_pixels: nonBinaryPixels,
          face_data_url: canvas.toDataURL("image/png"),
          crop_data_url: crop.toDataURL("image/png")
        };
      }, { family, phase }));
    }
  }

  await page.evaluate(({ cards, sourceUrl }) => {
    document.body.innerHTML = `
      <main>
        <h1>COMP-REQ-750 Owner-selected mouth integration</h1>
        <h2>Selected 09:34 source</h2>
        <img id="source" alt="selected source">
        <h2>Native 200x200 output: hold / accent</h2>
        <section></section>
      </main>`;
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "18px" });
    Object.assign(document.querySelector("#source"), {
      src: sourceUrl,
      width: 1100
    });
    Object.assign(document.querySelector("#source").style, {
      display: "block",
      background: "#fff",
      imageRendering: "pixelated"
    });
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
        minHeight: "36px",
        boxSizing: "border-box",
        padding: "5px",
        background: "#303638",
        color: "#fff",
        fontSize: "11px"
      });
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, {
    cards: frames,
    sourceUrl:
      "/.cache/validation/comp-req-750-owner-selected-mouths/source/owner-selected-09-34-44.png"
  });
  await page.waitForFunction(() => document.querySelector("#source")?.complete);
  await page.screenshot({
    path: path.join(screenshotRoot, "source-and-native-200-comparison.png"),
    fullPage: true
  });

  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-750 enlarged deterministic 1bpp mouths</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "18px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gridTemplateColumns: "repeat(4, 260px)",
      gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      Object.assign(figure.style, {
        margin: "0",
        minHeight: "190px",
        display: "grid",
        placeItems: "center",
        background: "#fff"
      });
      image.src = card.crop_data_url;
      image.width = Math.min(240, (card.raster_bounds.width + 8) * 9);
      image.height = (card.raster_bounds.height + 8) * 9;
      image.style.imageRendering = "pixelated";
      caption.textContent =
        `${card.family} / ${card.phase} / ${card.raster_bounds.width}x${card.raster_bounds.height}`;
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
      document.querySelector("section").append(figure);
    }
  }, frames);
  await page.screenshot({
    path: path.join(screenshotRoot, "enlarged-1bpp-mouths.png"),
    fullPage: true
  });

  const actualPairs = Object.fromEntries(families.map(family => [
    family,
    frames.filter(frame => frame.family === family).map(frame => frame.mouth_pose)
  ]));
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    selected_source_hash_exact:
      sha256(sourcePath) === expectedSourceHash
      && contract.source_sha256 === expectedSourceHash,
    selected_source_registered:
      contract.owner_selection === "today_09_34_first_full_face_mouth_sheet"
      && contract.supersedes_non_calm_source_requirement === "COMP-REQ-749",
    deterministic_manual_1bpp:
      contract.conversion === "manually_cleaned_deterministic_1bpp_rasters"
      && contract.runtime_generated_bitmap_import === false
      && contract.bits_per_pixel === 1,
    ten_family_order_exact:
      JSON.stringify(contract.family_order) === JSON.stringify(families),
    explicit_family_mapping_exact:
      families.every(family =>
        JSON.stringify(actualPairs[family]) === JSON.stringify(expectedPairs[family])),
    non_calm_hold_and_accent_distinct:
      families.slice(1).every(family =>
        actualPairs[family][0] !== actualPairs[family][1]),
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
    calm_mouth_contract_protected:
      contract.calm_guard.hold === "calm_closed_smile"
      && contract.calm_guard.breathing_and_listening === "listening_o"
      && contract.calm_guard.soften === "warm_smile",
    fixed_review_url_unchanged: contract.fixed_review_url === fixedUrl,
    hardware_contact_zero: contract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_750.owner_selected_mouths.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    selected_source: {
      path: path.relative(root, sourcePath).replaceAll("\\", "/"),
      sha256: sha256(sourcePath)
    },
    family_pairs: actualPairs,
    frames: frames.map(({ face_data_url, crop_data_url, ...frame }) => frame),
    screenshots: [
      ".cache/validation/comp-req-750-owner-selected-mouths/screenshots/source-and-native-200-comparison.png",
      ".cache/validation/comp-req-750-owner-selected-mouths/screenshots/enlarged-1bpp-mouths.png"
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
