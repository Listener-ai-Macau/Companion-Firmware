#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
const artifactRoot = path.join(root, ".cache/validation/comp-req-718-live-runtime");
fs.mkdirSync(artifactRoot, { recursive: true });

function playwright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright"
  ].filter(Boolean)) {
    try { return require(name); } catch {}
  }
  throw new Error("Playwright unavailable");
}

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) return response.writeHead(403).end();
  fs.readFile(target, (error, data) => {
    if (error) return response.writeHead(404).end();
    const type = target.endsWith(".html") ? "text/html; charset=utf-8"
      : target.endsWith(".png") ? "image/png"
        : "application/octet-stream";
    response.writeHead(200, { "content-type": type, "cache-control": "no-store" });
    response.end(data);
  });
});

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1700, height: 900 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const url = `http://127.0.0.1:${server.address().port}/${pageRel}?comp_req_718=${Date.now()}`;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 30000 });

  const families = ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"];
  const rows = [];
  for (const family of families) {
    await page.locator(`[data-family="${family}"]`).first().click();
    const frames = [];
    for (let index = 0; index < 12; index += 1) {
      await page.waitForTimeout(index === 0 ? 80 : 510);
      const sample = await page.locator("#face").evaluate(canvas => {
        const context = canvas.getContext("2d", { willReadFrequently: true });
        const image = context.getImageData(0, 0, 200, 200);
        const black = (x, y) => image.data[(y * 200 + x) * 4] < 128;
        const mouthBits = [];
        for (let y = 125; y < 182; y += 1) {
          for (let x = 65; x < 135; x += 1) mouthBits.push(black(x, y) ? "1" : "0");
        }
        const boundary = [];
        for (let y = 14; y < 200; y += 1) {
          if (black(0, y)) boundary.push([0, y]);
          if (black(199, y)) boundary.push([199, y]);
        }
        for (let x = 0; x < 200; x += 1) {
          if (black(x, 199)) boundary.push([x, 199]);
        }
        return {
          dataUrl: canvas.toDataURL("image/png"),
          mouthBits: mouthBits.join(""),
          boundaryCount: boundary.length,
          boundary: boundary.slice(0, 12),
          snapshot: window.__compReq599Snapshot()
        };
      });
      const file = `${family}-${String(index).padStart(2, "0")}.png`;
      fs.writeFileSync(path.join(artifactRoot, file), Buffer.from(sample.dataUrl.split(",")[1], "base64"));
      frames.push({ ...sample, file });
    }
    rows.push({ family, frames });
  }
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  await page.evaluate(({ rows }) => new Promise(resolve => {
    document.body.innerHTML = '<canvas id="atlas"></canvas>';
    const atlas = document.querySelector("#atlas");
    atlas.width = 12 * 200;
    atlas.height = rows.length * 200;
    const context = atlas.getContext("2d");
    context.imageSmoothingEnabled = false;
    let loaded = 0;
    const total = rows.reduce((sum, row) => sum + row.frames.length, 0);
    rows.forEach((row, rowIndex) => row.frames.forEach((frame, columnIndex) => {
      const image = new Image();
      image.onload = () => {
        context.drawImage(image, columnIndex * 200, rowIndex * 200);
        loaded += 1;
        if (loaded === total) resolve();
      };
      image.src = frame.dataUrl;
    }));
  }), { rows });
  await page.locator("#atlas").screenshot({ path: path.join(artifactRoot, "live-runtime-atlas.png") });

  const manifest = {
    schema: "companion.comp_req_718.live_runtime.diagnostic.v1",
    url,
    browser_errors: errors,
    families: Object.fromEntries(rows.map(row => [row.family, {
      unique_mouth_frames: new Set(row.frames.map(frame => frame.mouthBits)).size,
      boundary_touch_frames: row.frames.filter(frame => frame.boundaryCount > 0).map(frame => ({
        file: frame.file,
        count: frame.boundaryCount,
        sample: frame.boundary
      })),
      snapshots: row.frames.map(frame => frame.snapshot)
    }]))
  };
  fs.writeFileSync(path.join(artifactRoot, "diagnostic.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify({
    browser_errors: errors,
    families: Object.fromEntries(Object.entries(manifest.families).map(([family, row]) => [family, {
      unique_mouth_frames: row.unique_mouth_frames,
      boundary_touch_frames: row.boundary_touch_frames.length
    }]))
  }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
