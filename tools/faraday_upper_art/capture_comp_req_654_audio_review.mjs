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

const response = await fetch(reviewUrl, { cache: "no-store" });
const liveBytes = Buffer.from(await response.arrayBuffer());
const browser = await playwright().chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 680, height: 790 } });
const errors = [];
page.on("pageerror", error => errors.push(error.message));
await page.goto(`${reviewUrl}?comp_req_658_audio=${Date.now()}`, { waitUntil: "load" });
await page.waitForFunction(() => window.__compReq599Ready === true);

const screenshots = [];
for (const mode of ["recording", "speaker"]) {
  await page.click(`[data-mode="${mode}"]`);
  for (let index = 0; index < 18; index += 1) {
    const target = path.join(outputDir, `comp-req-658-${mode}-${index}.png`);
    await page.locator("#face").screenshot({ path: target });
    screenshots.push(path.relative(root, target).replaceAll("\\", "/"));
    await page.waitForTimeout(480);
  }
}
await browser.close();

const result = {
  schema: "companion.comp_req_658.audio_visual_capture.v1",
  status: errors.length === 0 ? "CAPTURED_FOR_VISUAL_REVIEW" : "NO_GO",
  live_http_sha256: crypto.createHash("sha256").update(liveBytes).digest("hex").toUpperCase(),
  screenshots,
  browser_errors: errors,
  hardware_contact: 0
};
fs.writeFileSync(
  path.join(outputDir, "comp-req-658-audio-visual-capture.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
if (result.status === "NO_GO") process.exitCode = 1;
