#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-747-calm-breath");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(path.join(artifactRoot, "screenshots"), { recursive: true });

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

function hasExactPeriod(values, maximum = 32) {
  for (let period = 1; period <= Math.min(maximum, Math.floor(values.length / 2)); period += 1) {
    if (values.every((value, index) => index < period || value === values[index - period])) {
      return true;
    }
  }
  return false;
}

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1365, height: 980 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq747FreezeCalmBreath === "function"
    && typeof window.__compReq747CalmBreathSequence === "function");

  const motionSequence = await page.evaluate(() =>
    window.__compReq747CalmBreathSequence(256));
  const samples = [];
  for (let tick = 0; tick < 256; tick += 1) {
    samples.push(await page.evaluate(value => {
      const state = window.__compReq747FreezeCalmBreath(value);
      const data = document.querySelector("#face")
        .getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      const black = (x, y) => data[(y * 200 + x) * 4] < 128;
      const contract = window.__compReq772Contract();
      const spread = contract.calm_dot_spread_x;
      const offset = contract.calm_dot_offset;
      const components = state.component_boxes.map((box, index) => {
        const region = {
          left: box.left + spread[index] + offset[0],
          top: box.top + offset[1],
          right: box.right + spread[index] + offset[0],
          bottom: box.bottom + offset[1]
        };
        const points = [];
        for (let y = region.top; y <= region.bottom; y += 1) {
          for (let x = region.left; x <= region.right; x += 1) {
            if (black(x, y)) points.push([x, y]);
          }
        }
        const pending = new Set(points.map(([x, y]) => `${x}:${y}`));
        let connectedParts = 0;
        while (pending.size) {
          connectedParts += 1;
          const seed = pending.values().next().value;
          pending.delete(seed);
          const queue = [seed.split(":").map(Number)];
          while (queue.length) {
            const [x, y] = queue.shift();
            for (const [nx, ny] of [
              [x - 1, y],
              [x + 1, y],
              [x, y - 1],
              [x, y + 1]
            ]) {
              const key = `${nx}:${ny}`;
              if (pending.delete(key)) queue.push([nx, ny]);
            }
          }
        }
        const xs = points.map(([x]) => x);
        const ys = points.map(([, y]) => y);
        const left = Math.min(...xs);
        const top = Math.min(...ys);
        const right = Math.max(...xs);
        const bottom = Math.max(...ys);
        return {
          pixels: points.length,
          connected_parts: connectedParts,
          bounds: [left, top, right, bottom],
          center: [(left + right) / 2, (top + bottom) / 2]
        };
      });
      const palette = new Set();
      for (let at = 0; at < data.length; at += 4) palette.add(data[at]);
      return {
        tick: value,
        levels: [...state.motion.local_dot_levels],
        duration: state.motion.duration,
        components,
        palette: [...palette].sort((left, right) => left - right),
        data_url: tickForReview(value)
          ? document.querySelector("#face").toDataURL("image/png")
          : null
      };

      function tickForReview(candidate) {
        return [0, 6, 14, 25, 39, 58, 81, 107].includes(candidate);
      }
    }, tick));
  }

  const protectedContract = await page.evaluate(() => {
    const calm = window.__compReq643FreezeLife("calm", 0, 0);
    return {
      calm_mouth: calm.face_motion?.mouth || null,
      hardware_contact: window.__compReq715Contract().hardware_contact,
      ornament_intent:
        window.__compReq625Contract().emotion_ornaments.calm.intent
    };
  });

  const reviewCards = samples.filter(sample => sample.data_url);
  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-747 平静呼吸三点局部编舞</h1>"
      + "<p>固定锚点 · 三点常驻 · 非周期错峰体量</p><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gridTemplateColumns: "repeat(4, 400px)",
      gap: "16px"
    });
    for (const card of cards) {
      const article = document.createElement("article");
      const image = document.createElement("img");
      const label = document.createElement("div");
      image.src = card.data_url;
      image.width = 400;
      image.height = 400;
      Object.assign(image.style, {
        imageRendering: "pixelated",
        display: "block"
      });
      label.textContent =
        `tick ${card.tick} · 点体量 ${card.levels.join("/")} · hold ${card.duration}`;
      Object.assign(label.style, {
        padding: "8px 0",
        textAlign: "center",
        fontSize: "18px"
      });
      article.append(image, label);
      document.querySelector("section").append(article);
    }
  }, reviewCards);
  await page.setViewportSize({ width: 1680, height: 960 });
  const screenshotPath = path.join(
    artifactRoot,
    "screenshots",
    "calm-breath-local-choreography.png"
  );
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const centerBaseline = samples[0].components.map(component => component.center);
  const componentCentersFixed = samples.every(sample =>
    sample.components.length === 3
    && sample.components.every((component, index) =>
      Math.abs(component.center[0] - centerBaseline[index][0]) <= 0.5
      && Math.abs(component.center[1] - centerBaseline[index][1]) <= 0.5));
  const componentVolumes = [0, 1, 2].map(index =>
    [...new Set(samples.map(sample => sample.components[index]?.pixels).filter(Boolean))]);
  const profileSequence = motionSequence.map(item => item.local_dot_levels.join(""));
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    strict_1bit_canvas:
      samples.every(sample =>
        sample.palette.length === 2
        && sample.palette[0] === 0
        && sample.palette[1] === 255),
    three_components_always_visible:
      samples.every(sample =>
        sample.components.length === 3
        && sample.components.every(component =>
          component.pixels >= 5 && component.connected_parts === 1)),
    component_centers_fixed: componentCentersFixed,
    each_dot_has_three_visible_volumes:
      componentVolumes.every(volumes => volumes.length === 3),
    nonperiodic_staggered_profiles:
      new Set(profileSequence).size >= 5
      && new Set(motionSequence.map(item => item.duration)).size >= 3
      && !hasExactPeriod(profileSequence, 32),
    local_motion_only:
      motionSequence.every(item =>
        item.motion_kind === "staggered_local_dot_breath"
        && item.local_component_centers_fixed === true
        && item.angle_deg === 0
        && item.scale === 1),
    safe_vertical_separation:
      samples.every(sample => sample.components.every(component =>
        component.bounds[1] >= 32 && component.bounds[3] <= 48)),
    dots_are_outside_face_above_brows:
      samples.every(sample => sample.components.every(component =>
        component.bounds[3] < 54)),
    calm_mouth_protected:
      protectedContract.calm_mouth === "guarded_calm_closed_smile",
    calm_ornament_semantics:
      protectedContract.ornament_intent === "calm_breath_dots",
    hardware_contact_zero: protectedContract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_747.calm_breath_ornament.verification.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    component_centers: centerBaseline,
    component_volumes: componentVolumes,
    profile_count: new Set(profileSequence).size,
    duration_count: new Set(motionSequence.map(item => item.duration)).size,
    screenshot:
      ".cache/validation/comp-req-747-calm-breath/screenshots/calm-breath-local-choreography.png",
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
  screenshot: result.screenshot
}, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
