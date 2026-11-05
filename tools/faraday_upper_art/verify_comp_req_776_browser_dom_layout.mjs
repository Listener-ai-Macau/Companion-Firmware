#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const outputArgument = process.argv[2] === "--output" ? process.argv[3] : null;
if (process.argv.length > 2 && !outputArgument) {
  throw new Error("usage: verify_comp_req_776_browser_dom_layout.mjs [--output <path>]");
}
const output = outputArgument
  ? path.resolve(root, outputArgument)
  : path.join(root, ".cache/validation/comp775-browser-parity-audit-20260812/DOM_LAYOUT.json");
if (output !== root && !output.startsWith(`${root}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
let fixedUrl;
const contractPath = path.join(
  root,
  "cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos/generated/companion_browser_interaction_contract.json"
);
const contract = JSON.parse(fs.readFileSync(contractPath, "utf8"));

function loadPlaywright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
  ].filter(Boolean)) {
    try {
      return require(name);
    } catch {}
  }
  throw new Error("Playwright unavailable");
}

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex").toUpperCase();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

const { chromium } = loadPlaywright();
const mime = {
  ".html": "text/html; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".pbm": "image/x-portable-bitmap",
  ".js": "text/javascript; charset=utf-8"
};
const staticServer = http.createServer((request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
    const target = path.resolve(root, pathname.replace(/^\/+/, ""));
    if (target !== root && !target.startsWith(`${root}${path.sep}`)) {
      response.writeHead(403).end("forbidden");
      return;
    }
    const body = fs.readFileSync(target);
    response.writeHead(200, {
      "Content-Type": mime[path.extname(target).toLowerCase()] || "application/octet-stream",
      "Content-Length": body.length,
      "Cache-Control": "no-store"
    });
    response.end(body);
  } catch {
    response.writeHead(404).end("not found");
  }
});
await new Promise((resolve, reject) => {
  staticServer.once("error", reject);
  staticServer.listen(0, "127.0.0.1", resolve);
});
const address = staticServer.address();
if (!address || typeof address === "string") throw new Error("temporary static server failed");
fixedUrl = `http://127.0.0.1:${address.port}/.cache/validation/comp-req-628-status-bar/index.html`;
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
const cases = [];

try {
  for (const viewport of [
    { name: "desktop", width: 1100, height: 900, expectedCss: 400 },
    { name: "mobile", width: 390, height: 900, expectedCss: 200 }
  ]) {
    const page = await browser.newPage({ viewport });
    page.on("pageerror", error => browserErrors.push(`${viewport.name}: pageerror: ${String(error)}`));
    page.on("console", message => {
      if (message.type() === "error") browserErrors.push(`${viewport.name}: console: ${message.text()}`);
    });
    const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
    assert(response, `${viewport.name}: missing HTTP response`);
    const body = await response.body();
    assert(response.status() === 200, `${viewport.name}: HTTP ${response.status()}`);
    assert(sha256(body) === contract.page_sha256, `${viewport.name}: page identity drift`);
    await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 15000 });
    await page.evaluate(() => window.__compReq599Restore());
    const geometry = await page.evaluate(() => {
      const canvas = document.querySelector("canvas#face");
      if (!canvas) throw new Error("canvas#face missing");
      const rect = canvas.getBoundingClientRect();
      const ancestors = [];
      let node = canvas.parentElement;
      let clipped = false;
      while (node) {
        const style = getComputedStyle(node);
        const bounds = node.getBoundingClientRect();
        const clipsX = ["hidden", "clip", "scroll", "auto"].includes(style.overflowX);
        const clipsY = ["hidden", "clip", "scroll", "auto"].includes(style.overflowY);
        const violates = (clipsX && (rect.left < bounds.left || rect.right > bounds.right))
          || (clipsY && (rect.top < bounds.top || rect.bottom > bounds.bottom));
        clipped ||= violates;
        ancestors.push({
          tag: node.tagName,
          id: node.id || null,
          class_name: node.className || null,
          overflow_x: style.overflowX,
          overflow_y: style.overflowY,
          clips_x: clipsX,
          clips_y: clipsY,
          violates
        });
        node = node.parentElement;
      }
      const style = getComputedStyle(canvas);
      return {
        intrinsic_width: canvas.width,
        intrinsic_height: canvas.height,
        css_width: rect.width,
        css_height: rect.height,
        css_display: style.display,
        image_rendering: style.imageRendering,
        left: rect.left,
        right: rect.right,
        top: rect.top,
        bottom: rect.bottom,
        within_document_x: rect.left >= 0 && rect.right <= document.documentElement.scrollWidth,
        within_document_y: rect.top >= 0 && rect.bottom <= document.documentElement.scrollHeight,
        ancestor_clip_violation: clipped,
        ancestors
      };
    });
    assert(geometry.intrinsic_width === 200 && geometry.intrinsic_height === 200,
      `${viewport.name}: intrinsic canvas is not 200x200`);
    assert(geometry.css_width === viewport.expectedCss && geometry.css_height === viewport.expectedCss,
      `${viewport.name}: CSS scaling changed`);
    assert(geometry.within_document_x && geometry.within_document_y,
      `${viewport.name}: canvas exceeds document geometry`);
    assert(!geometry.ancestor_clip_violation, `${viewport.name}: ancestor clips canvas`);
    const screenshot = path.join(path.dirname(output), `dom-layout-${viewport.name}.png`);
    await page.locator("canvas#face").screenshot({ path: screenshot });
    cases.push({
      viewport,
      http_status: response.status(),
      body_sha256: sha256(body),
      geometry,
      screenshot: path.relative(root, screenshot).replaceAll("\\", "/"),
      screenshot_sha256: sha256(fs.readFileSync(screenshot))
    });
    await page.close();
  }
  assert(browserErrors.length === 0, browserErrors.join(" | "));
  const report = {
    schema: "companion.comp_req_776.browser_dom_layout.v1",
    status: "MACHINE_READY",
    fixed_url: fixedUrl,
    behavior_page_sha256: contract.page_sha256,
    cases,
    browser_errors: browserErrors,
    hardware_contact: 0
  };
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  process.stdout.write(`MACHINE_READY ${output}\n`);
} catch (error) {
  const report = {
    schema: "companion.comp_req_776.browser_dom_layout.v1",
    status: "NO_GO",
    fixed_url: fixedUrl,
    behavior_page_sha256: contract.page_sha256,
    cases,
    browser_errors: browserErrors,
    error: String(error?.stack || error),
    hardware_contact: 0
  };
  fs.writeFileSync(output, `${JSON.stringify(report, null, 2)}\n`);
  process.stderr.write(`${report.error}\n`);
  process.exitCode = 1;
} finally {
  await browser.close();
  await new Promise(resolve => staticServer.close(resolve));
}
