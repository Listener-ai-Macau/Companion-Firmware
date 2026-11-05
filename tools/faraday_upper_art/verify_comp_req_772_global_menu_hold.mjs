#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-772-global-menu-hold");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(artifactRoot, { recursive: true });

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

function hash(values) {
  return crypto.createHash("sha256").update(Uint8Array.from(values)).digest("hex");
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const browserErrors = [];
page.on("pageerror", error => browserErrors.push(String(error)));
page.on("console", message => {
  if (message.type() === "error") browserErrors.push(message.text());
});

let result;
try {
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq625SetMode === "function"
    && typeof window.__compReq657MenuState === "function"
    && typeof window.__compReq752Snapshot === "function");
  const canvas = page.locator("#face");
  const box = await canvas.boundingBox();
  if (!box) throw new Error("face canvas has no bounding box");
  const point = (x, y) => ({
    x: box.x + box.width * x / 200,
    y: box.y + box.height * y / 200
  });
  const hold = point(100, 108);
  const sampleStableArea = () => page.evaluate(() => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const bits = [];
    for (let y = 14; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        if (x >= 144 && x < 176 && y >= 22 && y < 54) continue;
        bits.push(data[(y * 200 + x) * 4] < 128 ? 1 : 0);
      }
    }
    return bits;
  });

  const modes = ["expression", "charging", "upgrading", "recording", "speaker"];
  const samples = [];
  for (const mode of modes) {
    await page.evaluate(value => window.__compReq625SetMode(value), mode);
    await page.waitForTimeout(120);
    await page.mouse.move(hold.x, hold.y);
    await page.mouse.down();
    await page.waitForTimeout(20);
    const before = await sampleStableArea();
    await page.waitForTimeout(1620);
    const during = await sampleStableArea();
    await page.waitForTimeout(1700);
    await page.mouse.up();
    await page.waitForTimeout(260);
    const entered = await page.evaluate(() => window.__compReq657MenuState());
    const swipeStart = point(48, 112);
    const swipeEnd = point(154, 112);
    await page.mouse.move(swipeStart.x, swipeStart.y);
    await page.mouse.down();
    await page.mouse.move(swipeEnd.x, swipeEnd.y, { steps: 6 });
    await page.mouse.up();
    await page.waitForTimeout(160);
    const restored = await page.evaluate(() => window.__compReq752Snapshot().active_mode);
    samples.push({
      mode,
      stable_hash_before: hash(before),
      stable_hash_during_progress: hash(during),
      base_preserved_outside_progress_badge: hash(before) === hash(during),
      entered,
      restored
    });
  }

  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    all_visible_modes_accept_real_long_press:
      samples.every(sample => sample.entered.active && sample.entered.screen === "home"),
    progress_overlay_preserves_each_source_frame:
      samples.every(sample => sample.base_preserved_outside_progress_badge),
    right_swipe_restores_each_source_mode:
      samples.every(sample => sample.restored === sample.mode),
    hardware_contact_zero: true
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    samples,
    browser_errors: browserErrors
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
