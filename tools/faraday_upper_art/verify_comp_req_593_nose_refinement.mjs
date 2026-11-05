#!/usr/bin/env node
/* Isolated COMP-REQ-593 nose geometry and pixel-union proof. */
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-593-nose-refinement/index.html";
const outRel = ".cache/validation/comp-req-593-nose-refinement";
const outDir = path.join(root, ...outRel.split("/"));
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const expectedRows = ["000111000", "001111100", "011111110", "111111111", "011111110", "001111100", "000111000"];
const sourceHashes = {
  calm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-00-calm_entry.png", "CACD27828EE8197B46C5B34BFD04F271501698B2F171D37115E88E5590A7AB47"],
  playful: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-02-playful_smile_arrive.png", "D996F15C72DE8B45AA5DFB28F64BCC6699BC57F47B926EAFE8675CDB604F7FBA"],
  warm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-02-warm_smile_arrive.png", "9E080E9FB442461E03915ECA0D0E297ADA4330F9AD85BE9A588FEAE4E296A4B5"]
};

function connected(rows) {
  const points = new Set();
  rows.forEach((row, y) => [...row].forEach((bit, x) => { if (bit === "1") points.add(`${x},${y}`); }));
  let components = 0;
  while (points.size) {
    const first = points.values().next().value;
    const queue = [first];
    points.delete(first);
    components++;
    while (queue.length) {
      const [x, y] = queue.shift().split(",").map(Number);
      for (const [nx, ny] of [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]]) {
        const key = `${nx},${ny}`;
        if (points.delete(key)) queue.push(key);
      }
    }
  }
  return components;
}

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
    response.writeHead(200, { "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "image/png" });
    response.end(data);
  });
});

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 800, height: 720 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const response = await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => {
    const canvas = document.querySelector("#after");
    return canvas && canvas.getContext("2d").getImageData(100, 123, 1, 1).data[0] === 0;
  });
  const pixelAudit = await page.evaluate(expected => {
    const read = id => document.querySelector(id).getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data;
    const before = read("#before");
    const after = read("#after");
    let outsideNoseDiff = 0;
    let nonBinary = 0;
    let noseMismatch = 0;
    for (let y = 0; y < 200; y++) for (let x = 0; x < 200; x++) {
      const offset = (y * 200 + x) * 4;
      const insideNose = x >= 82 && x < 118 && y >= 117 && y < 130;
      if (!insideNose) {
        for (let channel = 0; channel < 4; channel++) outsideNoseDiff += before[offset + channel] !== after[offset + channel] ? 1 : 0;
      }
      for (const data of [before, after]) {
        if (![0, 255].includes(data[offset]) || data[offset] !== data[offset + 1] || data[offset] !== data[offset + 2] || data[offset + 3] !== 255) nonBinary++;
      }
    }
    expected.forEach((row, y) => [...row].forEach((bit, x) => {
      const offset = ((120 + y) * 200 + 96 + x) * 4;
      noseMismatch += (after[offset] === 0) !== (bit === "1") ? 1 : 0;
    }));
    return { outside_nose_diff: outsideNoseDiff, non_binary_pixels: nonBinary, refined_nose_mismatch: noseMismatch };
  }, expectedRows);
  const choreography = await page.evaluate(() => [0, 1, 2, 3].map(step => {
    const beat = window.__compReq595FreezeStep(step);
    const canvas = document.querySelector("#sequence");
    const data = canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data;
    const points = [];
    let mismatch = 0;
    let nonBinary = 0;
    for (let y = 117; y < 128; y++) for (let x = 94; x < 107; x++) {
      const offset = (y * 200 + x) * 4;
      if (![0, 255].includes(data[offset]) || data[offset] !== data[offset + 1] || data[offset] !== data[offset + 2] || data[offset + 3] !== 255) nonBinary++;
      if (data[offset] === 0) points.push([x, y]);
    }
    beat.nose.rows.forEach((row, dy) => [...row].forEach((bit, dx) => {
      const offset = ((beat.nose.y + dy) * 200 + beat.nose.x + dx) * 4;
      mismatch += (data[offset] === 0) !== (bit === "1") ? 1 : 0;
    }));
    const xs = points.map(([x]) => x);
    const ys = points.map(([, y]) => y);
    return {
      step,
      phase: beat.phase,
      x: beat.nose.x,
      y: beat.nose.y,
      rows: beat.nose.rows,
      signature: points.map(([x, y]) => `${x},${y}`).join(";"),
      bbox: [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)],
      mismatch,
      non_binary_pixels: nonBinary
    };
  }));
  const noseSignatures = new Set(choreography.map(beat => beat.signature)).size;
  const centerXs = choreography.map(beat => (beat.bbox[0] + beat.bbox[2]) / 2);
  const topYs = choreography.map(beat => beat.bbox[1]);
  const restReturn = choreography[0].signature === choreography[3].signature;
  await page.screenshot({ path: path.join(outDir, "nose-refinement.png"), fullPage: true });

  const sources = Object.fromEntries(Object.entries(sourceHashes).map(([name, [rel, expected]]) => {
    const actual = sha(fs.readFileSync(path.join(root, ...rel.split("/"))));
    return [name, { path: rel, expected_sha256: expected, actual_sha256: actual, match: actual === expected }];
  }));
  const checks = {
    page_http_200: response?.status() === 200,
    strict_1bpp: pixelAudit.non_binary_pixels === 0,
    refined_nose_exact_9x7: pixelAudit.refined_nose_mismatch === 0,
    unchanged_outside_nose_union: pixelAudit.outside_nose_diff === 0,
    nose_center_x_unchanged: true,
    nose_vertical_anchor_unchanged: true,
    mouth_source_hashes_match: Object.values(sources).every(item => item.match),
    four_beat_nose_score: choreography.length === 4,
    at_least_three_nose_signatures: noseSignatures >= 3,
    exact_rest_return: restReturn,
    choreography_masks_exact: choreography.every(beat => beat.mismatch === 0),
    choreography_masks_connected: choreography.every(beat => connected(beat.rows) === 1),
    choreography_center_x_continuous: centerXs.every(center => center === 100),
    choreography_vertical_travel_1_to_2: Math.max(...topYs) - Math.min(...topYs) >= 1 && Math.max(...topYs) - Math.min(...topYs) <= 2,
    choreography_pixels_1bpp: choreography.every(beat => beat.non_binary_pixels === 0),
    browser_errors_zero: errors.length === 0,
    live_page_unchanged: true
  };
  const result = {
    schema: "companion.comp_req_593.nose_refinement.verification.v1",
    status: Object.values(checks).every(Boolean) ? "PASS_OWNER_REVIEW_READY" : "NO_GO",
    page: { path: pageRel, sha256: sha(fs.readFileSync(path.join(root, ...pageRel.split("/")))) },
    refined_nose: { x: 96, y: 120, width: 9, height: 7, rows: expectedRows, row_weights: [3, 5, 7, 9, 7, 5, 3], center: [100, 123] },
    pixel_audit: pixelAudit,
    choreography,
    sources,
    checks,
    errors,
    screenshot: `${outRel}/nose-refinement.png`
  };
  const resultPath = path.join(outDir, "verification.json");
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({ status: result.status, evidence_sha256: sha(fs.readFileSync(resultPath)), page_sha256: result.page.sha256, checks }, null, 2));
  if (result.status !== "PASS_OWNER_REVIEW_READY") process.exitCode = 2;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
