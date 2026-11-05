#!/usr/bin/env node
/* Isolated COMP-REQ-591 proof: exact V9 mouth sources, no live-page import. */
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-586-mouth-manual-concepts/index.html";
const manifestRel = ".cache/validation/comp-req-586-mouth-manual-concepts/v9-lineage-manifest.json";
const outRel = ".cache/validation/comp-req-591-v9-mouth-lineage";
const outDir = path.join(root, ...outRel.split("/"));
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const sources = [
  ["focused", "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-02-focused_mouth_arrive.png", "472456F0A242C1C8B4BD9DAE69C4FFC8B4A052E2EA938AC1B37EB61FE557864B"],
  ["playful", "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-02-playful_smile_arrive.png", "D996F15C72DE8B45AA5DFB28F64BCC6699BC57F47B926EAFE8675CDB604F7FBA"],
  ["warm", "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-02-warm_smile_arrive.png", "9E080E9FB442461E03915ECA0D0E297ADA4330F9AD85BE9A588FEAE4E296A4B5"]
];

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

function server() {
  return http.createServer((request, response) => {
    const pathname = decodeURIComponent(request.url.split("?")[0]);
    const target = path.resolve(root, `.${pathname}`);
    if (!target.startsWith(`${root}${path.sep}`)) return response.writeHead(403).end();
    fs.readFile(target, (error, data) => {
      if (error) return response.writeHead(404).end();
      const type = target.endsWith(".html") ? "text/html; charset=utf-8"
        : target.endsWith(".png") ? "image/png"
          : target.endsWith(".json") ? "application/json"
            : "application/octet-stream";
      response.writeHead(200, { "content-type": type });
      response.end(data);
    });
  });
}

const srv = server();
let browser;
try {
  fs.mkdirSync(outDir, { recursive: true });
  await new Promise(resolve => srv.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1200, height: 720 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const url = `http://127.0.0.1:${srv.address().port}/${pageRel}?verify=comp-req-591`;
  const response = await page.goto(url, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => document.querySelectorAll("#grid canvas:not(.crop)").length === 5);
  const pixels = await page.evaluate(async () => {
    const baseline = await new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = "../comp-req-581-mouth-main-replay/ordinary-step-08.png";
    });
    const reference = document.createElement("canvas");
    reference.width = reference.height = 200;
    const referenceContext = reference.getContext("2d", { willReadFrequently: true });
    referenceContext.drawImage(baseline, 0, 0);
    const original = referenceContext.getImageData(0, 0, 200, 200).data;
    const faces = [...document.querySelectorAll("#grid canvas:not(.crop)")];
    return faces.map(canvas => {
      const data = canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data;
      let outsideMouthDiff = 0;
      let nonBinaryPixels = 0;
      let mouthBlackPixels = 0;
      for (let y = 0; y < 200; y++) for (let x = 0; x < 200; x++) {
        const offset = (y * 200 + x) * 4;
        const inside = x >= 80 && x < 120 && y >= 128 && y < 157;
        if (!inside) {
          for (let channel = 0; channel < 4; channel++) outsideMouthDiff += data[offset + channel] !== original[offset + channel] ? 1 : 0;
        }
        if (![0, 255].includes(data[offset]) || data[offset] !== data[offset + 1] || data[offset] !== data[offset + 2] || data[offset + 3] !== 255) nonBinaryPixels++;
        if (inside && data[offset] === 0) mouthBlackPixels++;
      }
      return { outside_mouth_diff: outsideMouthDiff, non_binary_pixels: nonBinaryPixels, mouth_black_pixels: mouthBlackPixels };
    });
  });
  await page.screenshot({ path: path.join(outDir, "v9-mouth-lineage.png"), fullPage: true });

  const manifest = JSON.parse(fs.readFileSync(path.join(root, ...manifestRel.split("/")), "utf8"));
  const sourceChecks = Object.fromEntries(sources.map(([name, rel, expected]) => {
    const actual = sha(fs.readFileSync(path.join(root, ...rel.split("/"))));
    return [name, { path: rel, expected_sha256: expected, actual_sha256: actual, match: actual === expected }];
  }));
  const checks = {
    page_http_200: response?.status() === 200,
    five_exact_v9_faces: pixels.length === 5,
    non_mouth_pixels_unchanged: pixels.every(item => item.outside_mouth_diff === 0),
    rendered_pixels_are_1bpp: pixels.every(item => item.non_binary_pixels === 0),
    every_mouth_is_visible: pixels.every(item => item.mouth_black_pixels > 0),
    source_hashes_match: Object.values(sourceChecks).every(item => item.match),
    generated_art_imported_false: manifest.generated_art_imported === false,
    generated_art_rejected: manifest.generated_art_disposition === "REJECTED_PROVENANCE_ONLY",
    exact_v9_policy: manifest.lineage_policy === "EXACT_ACCEPTED_V9_SOURCE_MASKS_ONLY",
    live_page_unmodified: manifest.live_page_modified === false,
    browser_errors_zero: errors.length === 0
  };
  const result = {
    schema: "companion.comp_req_591.v9_mouth_lineage.verification.v1",
    status: Object.values(checks).every(Boolean) ? "PASS_OWNER_REVIEW_READY" : "NO_GO",
    page: { path: pageRel, sha256: sha(fs.readFileSync(path.join(root, ...pageRel.split("/")))) },
    manifest: { path: manifestRel, sha256: sha(fs.readFileSync(path.join(root, ...manifestRel.split("/")))) },
    sources: sourceChecks,
    pixels,
    checks,
    errors,
    screenshot: `${outRel}/v9-mouth-lineage.png`
  };
  const resultPath = path.join(outDir, "verification.json");
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({ status: result.status, evidence_sha256: sha(fs.readFileSync(resultPath)), checks }, null, 2));
  if (result.status !== "PASS_OWNER_REVIEW_READY") process.exitCode = 2;
} finally {
  await browser?.close();
  await new Promise(resolve => srv.close(resolve));
}
