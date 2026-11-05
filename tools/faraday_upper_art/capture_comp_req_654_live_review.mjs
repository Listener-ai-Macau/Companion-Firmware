#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outputDir = path.join(root, ".cache/validation/comp-req-628-status-bar");
const reviewUrl = "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";

function playwright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
  ].filter(Boolean)) {
    try { return require(name); } catch {}
  }
  throw new Error("Playwright unavailable");
}

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex").toUpperCase();
}

const response = await fetch(reviewUrl, { cache: "no-store" });
const liveBytes = Buffer.from(await response.arrayBuffer());
if (!response.ok) throw new Error(`live review HTTP ${response.status}`);

fs.mkdirSync(outputDir, { recursive: true });
const videoDir = path.join(outputDir, "comp-req-660-video");
fs.mkdirSync(videoDir, { recursive: true });

const browser = await playwright().chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 680, height: 790 },
  recordVideo: { dir: videoDir, size: { width: 680, height: 790 } }
});
const page = await context.newPage();
const errors = [];
page.on("pageerror", error => errors.push(error.message));
await page.goto(`${reviewUrl}?comp_req_660=${Date.now()}`, { waitUntil: "load" });
await page.waitForFunction(() => window.__compReq599Ready === true);

const canvas = page.locator("#face");
const box = await canvas.boundingBox();
const center = { x: box.x + box.width / 2, y: box.y + box.height / 2 };
const readCells = () => page.evaluate(() => {
  const context = document.querySelector("#face").getContext("2d");
  return [[88, 28], [104, 28], [88, 44], [104, 44]].map(([x, y]) => {
    const pixels = context.getImageData(x, y, 8, 8).data;
    let black = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] < 128) black += 1;
    }
    return black;
  });
});

const phases = [];
const mark = async name => {
  const phase = {
    name,
    at_ms: Math.round(performance.now()),
    cells: await readCells(),
    menu_ornament_ink: await page.evaluate(() => {
      const pixels = document.querySelector("#face").getContext("2d").getImageData(84, 24, 32, 32).data;
      let ink = 0;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] < 128) ink += 1;
      }
      return ink;
    }),
    active_mode: await page.evaluate(() =>
      [...document.querySelectorAll("[data-mode]")].find(button =>
        button.getAttribute("aria-pressed") === "true")?.dataset.mode || null),
    menu_state: await page.evaluate(() => window.__compReq657MenuState())
  };
  phases.push(phase);
  if (name.startsWith("menu_") && phase.menu_state.active) {
    await canvas.screenshot({ path: path.join(outputDir, `comp-req-660-${name}.png`) });
  }
};

await page.click('[data-mode="expression"]');
await mark("expression_ready");
await page.mouse.move(center.x, center.y);
await page.mouse.down();
await page.waitForTimeout(180);
await mark("single_tap_arbitration_no_menu");
await page.mouse.up();
await page.waitForTimeout(440);
await mark("single_tap_emotion_response");

await page.mouse.click(center.x, center.y);
await page.waitForTimeout(100);
await mark("double_tap_gap_no_menu");
await page.mouse.down();
await page.waitForTimeout(180);
await mark("double_tap_second_down_no_menu");
await page.mouse.up();
await page.waitForTimeout(520);
await mark("double_tap_recording_enter");
await page.waitForTimeout(480);
await mark("recording_wave_motion_a");
await page.waitForTimeout(960);
await mark("recording_wave_motion_b");

await page.mouse.click(center.x, center.y);
await page.waitForTimeout(100);
await page.mouse.click(center.x, center.y);
await page.waitForTimeout(440);
await mark("double_tap_recording_exit");

await page.click('[data-mode="speaker"]');
await mark("speaker_wave_ready");
await page.waitForTimeout(480);
await mark("speaker_wave_motion_a");
await page.waitForTimeout(960);
await mark("speaker_wave_motion_b");
await page.click('[data-mode="expression"]');

await page.click('[data-mode="menu"]');
await mark("menu_clicked_empty");
await page.waitForTimeout(1200);
await mark("menu_idle_1200ms");

await page.mouse.move(center.x, center.y);
await page.mouse.down();
await page.waitForTimeout(1600);
await mark("short_hold_partial");
await page.mouse.up();
await page.waitForTimeout(900);
await mark("short_hold_released");

await page.mouse.move(center.x, center.y);
await page.mouse.down();
await page.waitForTimeout(560);
await page.mouse.move(box.x + box.width * 0.68, center.y);
await page.mouse.up();
await page.waitForTimeout(900);
await mark("drag_cancelled");

await page.mouse.move(center.x, center.y);
await page.mouse.down();
for (const [name, waitMs] of [
  ["full_hold_cell_1", 1550],
  ["full_hold_cell_2", 500],
  ["full_hold_cell_3", 500],
  ["full_hold_cell_4", 500],
  ["menu_home_after_ack", 500]
]) {
  await page.waitForTimeout(waitMs);
  await mark(name);
}
await page.mouse.up();
await page.waitForTimeout(300);
await mark("menu_home_after_release");

await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.42);
await page.waitForTimeout(300);
await mark("menu_device_detail");
await page.mouse.click(box.x + box.width * 0.12, box.y + box.height * 0.12);
await page.waitForTimeout(300);
await mark("menu_home_after_detail_back");
await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.82);
await page.mouse.down();
await page.mouse.move(box.x + box.width * 0.5, box.y + box.height * 0.45, { steps: 6 });
await page.mouse.up();
await page.waitForTimeout(300);
await mark("menu_root_scrolled");
await page.mouse.click(box.x + box.width * 0.5, box.y + box.height * 0.85);
await page.waitForTimeout(300);
await mark("menu_preferences_after_scrolled_tap");
await page.mouse.click(box.x + box.width * 0.12, box.y + box.height * 0.12);
await page.waitForTimeout(300);
await mark("menu_home_before_exit");
await page.mouse.move(box.x + box.width * 0.24, box.y + box.height * 0.55);
await page.mouse.down();
await page.mouse.move(box.x + box.width * 0.7, box.y + box.height * 0.55, { steps: 6 });
await page.mouse.up();
await page.waitForTimeout(480);
await mark("menu_swipe_right_expression_restored");

const video = page.video();
await context.close();
const capturedVideoPath = await video.path();
await browser.close();

const finalVideoPath = path.join(outputDir, "comp-req-660-live-review.webm");
fs.copyFileSync(capturedVideoPath, finalVideoPath);
const result = {
  schema: "companion.comp_req_660.live_review_capture.v1",
  status: errors.length === 0 ? "CAPTURED_FOR_VISUAL_REVIEW" : "NO_GO",
  url: reviewUrl,
  live_http_sha256: sha256(liveBytes),
  cache_control: response.headers.get("cache-control"),
  video_path: path.relative(root, finalVideoPath).replaceAll("\\", "/"),
  video_sha256: sha256(fs.readFileSync(finalVideoPath)),
  phases,
  browser_errors: errors,
  hardware_contact: 0
};
const resultPath = path.join(outputDir, "comp-req-660-live-review-capture.json");
fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result, null, 2));
if (result.status === "NO_GO") process.exitCode = 1;
