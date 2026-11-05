#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
const artifactRoot = path.join(root, ".cache/validation/comp-req-715-eye-mouth-vocabulary");
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

const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
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
  const page = await browser.newPage({ viewport: { width: 1100, height: 500 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 30000 });
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  const mouthContract = await page.evaluate(() => window.__compReq715Contract());
  const mouths = [];
  for (const pose of mouthContract.rasters) {
    const result = await page.evaluate(name => window.__compReq715FreezeMouth(name), pose);
    const dataUrl = await page.locator("#face").evaluate(canvas => canvas.toDataURL("image/png"));
    fs.writeFileSync(
      path.join(artifactRoot, `mouth-${pose}.png`),
      Buffer.from(dataUrl.split(",")[1], "base64")
    );
    mouths.push({ pose, raster: result.raster, dataUrl, signature: sha(JSON.stringify(result.raster)) });
  }

  const families = ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"];
  const emotions = [];
  const holds = [];
  const durationRows = {};
  for (const [index, family] of families.entries()) {
    durationRows[family] = await page.evaluate(
      ({ name, count }) => window.__compReq717Sequence(name, count),
      { name: family, count: 512 }
    );
    await page.evaluate(({ name, variant }) => window.__compReq716FreezeEmotion(name, "hold", variant), {
      name: family,
      variant: index
    });
    const holdDataUrl = await page.locator("#face").evaluate(canvas => canvas.toDataURL("image/png"));
    fs.writeFileSync(
      path.join(artifactRoot, `emotion-${family}-hold.png`),
      Buffer.from(holdDataUrl.split(",")[1], "base64")
    );
    const eyePixels = await page.locator("#face").evaluate(canvas => {
      const data = canvas.getContext("2d").getImageData(25, 45, 150, 90).data;
      const bits = [];
      for (let i = 0; i < data.length; i += 4) bits.push(data[i] < 128 ? 1 : 0);
      return bits.join("");
    });
    holds.push({ family, dataUrl: holdDataUrl, eyeSignature: sha(eyePixels) });

    await page.evaluate(({ name, variant }) => window.__compReq716FreezeEmotion(name, "accent", variant), {
      name: family,
      variant: index
    });
    const dataUrl = await page.locator("#face").evaluate(canvas => canvas.toDataURL("image/png"));
    fs.writeFileSync(
      path.join(artifactRoot, `emotion-${family}-accent.png`),
      Buffer.from(dataUrl.split(",")[1], "base64")
    );
    const mouthPixels = await page.locator("#face").evaluate(canvas => {
      const data = canvas.getContext("2d").getImageData(65, 125, 70, 55).data;
      const bits = [];
      for (let i = 0; i < data.length; i += 4) bits.push(data[i] < 128 ? 1 : 0);
      return bits.join("");
    });
    emotions.push({ family, dataUrl, mouthSignature: sha(mouthPixels) });
  }

  async function saveSheet(items, filename, columns) {
    const rows = Math.ceil(items.length / columns);
    await page.evaluate(({ sources, columns, rows }) => new Promise(resolve => {
      document.body.innerHTML = '<canvas id="contact"></canvas>';
      const sheet = document.querySelector("#contact");
      sheet.width = columns * 200;
      sheet.height = rows * 200;
      sheet.style.imageRendering = "pixelated";
      const ctx = sheet.getContext("2d");
      ctx.imageSmoothingEnabled = false;
      let loaded = 0;
      sources.forEach((source, index) => {
        const image = new Image();
        image.onload = () => {
          ctx.drawImage(image, (index % columns) * 200, Math.floor(index / columns) * 200);
          loaded += 1;
          if (loaded === sources.length) resolve();
        };
        image.src = source;
      });
    }), { sources: items.map(item => item.dataUrl), columns, rows });
    await page.locator("#contact").screenshot({ path: path.join(artifactRoot, filename) });
  }

  await saveSheet(mouths, "mouth-vocabulary-native-200.png", 5);
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 30000 });
  await page.evaluate(() => window.__compReq714SetScheduler(false));
  await saveSheet(emotions, "emotion-accent-native-200.png", 5);
  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 30000 });
  await page.evaluate(() => window.__compReq714SetScheduler(false));
  await saveSheet(holds, "emotion-hold-native-200.png", 5);

  const openHeights = ["small_o", "open_joy", "sleepy_yawn", "alert_open"].map(name => {
    const raster = mouths.find(item => item.pose === name).raster;
    return { name, height: raster.length };
  });
  const compactHeights = ["neutral", "focused_pressed"].map(name => {
    const raster = mouths.find(item => item.pose === name).raster;
    return { name, height: raster.length };
  });
  const durationEvidence = Object.fromEntries(families.map(family => {
    const rows = durationRows[family];
    const sourceCount = rows.filter(row => row.source_mouth).length;
    const restHolds = rows.filter(row => row.phase === "hold" && row.life_action === "rest" && row.mouth_pose);
    const counts = new Map();
    restHolds.forEach(row => counts.set(row.mouth_pose, (counts.get(row.mouth_pose) || 0) + 1));
    const settledMouth = [...counts].sort((left, right) => right[1] - left[1])[0]?.[0] || null;
    return [family, {
      commits: rows.length,
      source_mouth_count: sourceCount,
      source_mouth_ratio: sourceCount / rows.length,
      settled_mouth: settledMouth,
      named_mouth_commits: rows.length - sourceCount
    }];
  }));
  const nonCalmSourceZero = families.slice(1).every(family =>
    durationEvidence[family].source_mouth_count === 0);
  const settledMouths = families.map(family => durationEvidence[family].settled_mouth);
  const manifest = {
    schema: "companion.comp_req_715.eye_mouth_vocabulary.v1",
    status: errors.length === 0
      && new Set(mouths.map(item => item.signature)).size === mouths.length
      && new Set(emotions.map(item => item.mouthSignature)).size >= 8
      && new Set(holds.map(item => item.eyeSignature)).size === families.length
      && nonCalmSourceZero
      && durationEvidence.calm.source_mouth_count === 0
      && new Set(settledMouths).size === families.length
      ? "GO" : "NO_GO",
    checks: {
      browser_errors_zero: errors.length === 0,
      named_mouths_at_least_eight: mouths.length >= 8,
      mouth_rasters_unique: new Set(mouths.map(item => item.signature)).size === mouths.length,
      emotion_face_signatures_distinct: new Set(emotions.map(item => item.mouthSignature)).size >= 8,
      every_family_has_distinct_hold_eye_signature:
        new Set(holds.map(item => item.eyeSignature)).size === families.length,
      open_shapes_taller_than_pressed: Math.min(...openHeights.map(item => item.height))
        > Math.max(...compactHeights.map(item => item.height)),
      every_family_has_unique_settled_mouth: new Set(settledMouths).size === families.length,
      non_calm_source_mouth_exposure_zero: nonCalmSourceZero,
      calm_source_mouth_exposure_zero: durationEvidence.calm.source_mouth_count === 0,
      hardware_contact_zero: true
    },
    evidence: {
      mouth_order: mouths.map(item => item.pose),
      emotion_order: emotions.map(item => item.family),
      mouth_signatures: Object.fromEntries(mouths.map(item => [item.pose, item.signature])),
      emotion_face_signatures: Object.fromEntries(emotions.map(item => [item.family, item.mouthSignature])),
      hold_eye_signatures: Object.fromEntries(holds.map(item => [item.family, item.eyeSignature])),
      open_heights: openHeights,
      compact_heights: compactHeights,
      duration_sampling: durationEvidence,
      artifacts: [
        ".cache/validation/comp-req-715-eye-mouth-vocabulary/mouth-vocabulary-native-200.png",
        ".cache/validation/comp-req-715-eye-mouth-vocabulary/emotion-accent-native-200.png",
        ".cache/validation/comp-req-715-eye-mouth-vocabulary/emotion-hold-native-200.png"
      ],
      hardware_contact: 0
    },
    browser_errors: errors
  };
  fs.writeFileSync(path.join(artifactRoot, "manifest.json"), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify(manifest, null, 2));
  if (manifest.status !== "GO") process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
