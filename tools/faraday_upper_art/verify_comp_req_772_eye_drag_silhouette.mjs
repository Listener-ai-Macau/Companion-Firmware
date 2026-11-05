#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root, ".cache/validation/comp-req-772-eye-drag-silhouette"
);
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(screenshotRoot, { recursive: true });

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

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({ viewport: { width: 1400, height: 1100 } });
  await page.addInitScript(() => {
    sessionStorage.setItem("companion.comp_req_772.line_style.r15", "fused");
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq761Contract === "function"
    && typeof window.__compReq761DeferBlinkAudit === "function"
    && typeof window.__compReq714Interaction === "function"
  );
  await page.evaluate(() => {
    window.__compReq761ResetRuntime("warm", true);
    window.__compReq714ClearTrace();
  });

  const canvas = page.locator("#face");
  const box = await canvas.boundingBox();
  const point = (x, y) => ({
    x: box.x + box.width * x,
    y: box.y + box.height * y
  });
  const capture = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const image = context.getImageData(0, 0, 200, 200);
    const eyeBounds = window.__compReq761Contract().generated_eye_bounds.warm;
    const black = (x, y) => image.data[(y * 200 + x) * 4] < 128;
    const auditEye = ([left, top, width, height]) => {
      const right = left + width - 1;
      const bottom = top + height - 1;
      const remaining = new Set();
      for (let y = top; y <= bottom; y += 1) {
        for (let x = left; x <= right; x += 1) {
          if (black(x, y)) remaining.add(`${x}:${y}`);
        }
      }
      const components = [];
      while (remaining.size) {
        const first = remaining.values().next().value;
        remaining.delete(first);
        const queue = [first];
        const component = [];
        while (queue.length) {
          const key = queue.pop();
          const [x, y] = key.split(":").map(Number);
          component.push([x, y]);
          for (const [dx, dy] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
            const next = `${x + dx}:${y + dy}`;
            if (remaining.delete(next)) queue.push(next);
          }
        }
        components.push(component);
      }
      const body = components.sort((a, b) => b.length - a.length)[0] || [];
      const bodySet = new Set(body.map(([x, y]) => `${x}:${y}`));
      const xs = body.map(([x]) => x);
      const ys = body.map(([, y]) => y);
      const bodyLeft = Math.min(...xs);
      const bodyRight = Math.max(...xs);
      const bodyTop = Math.min(...ys);
      const bodyBottom = Math.max(...ys);
      const row = y => {
        const values = [];
        for (let x = bodyLeft; x <= bodyRight; x += 1) {
          if (bodySet.has(`${x}:${y}`)) values.push(x);
        }
        return values;
      };
      const column = x => {
        const values = [];
        for (let y = bodyTop; y <= bodyBottom; y += 1) {
          if (bodySet.has(`${x}:${y}`)) values.push(y);
        }
        return values;
      };
      const envelope = {
        rows: Array.from({ length: bodyBottom - bodyTop + 1 }, (_, offset) => {
          const values = row(bodyTop + offset);
          return [Math.min(...values), Math.max(...values)];
        }),
        columns: Array.from({ length: bodyRight - bodyLeft + 1 }, (_, offset) => {
          const values = column(bodyLeft + offset);
          return [Math.min(...values), Math.max(...values)];
        })
      };
      return {
        bounds: [bodyLeft, bodyTop, bodyRight, bodyBottom],
        ink: body.length,
        component_count_in_eye_box: components.length,
        terminal_rows: [
          row(bodyTop).length,
          row(bodyTop + 1).length,
          row(bodyBottom - 1).length,
          row(bodyBottom).length
        ],
        terminal_columns: [
          column(bodyLeft).length,
          column(bodyLeft + 1).length,
          column(bodyRight - 1).length,
          column(bodyRight).length
        ],
        envelope
      };
    };
    return {
      label,
      data_url: canvas.toDataURL("image/png"),
      palette: [...new Set(
        Array.from({ length: 200 * 200 }, (_, index) => image.data[index * 4])
      )].sort((a, b) => a - b),
      eyes: eyeBounds.map(auditEye),
      interaction: window.__compReq714Interaction()
    };
  }, label);

  const targets = [
    ["center", 0.5, 0.5],
    ["right", 0.9, 0.5],
    ["left", 0.1, 0.5],
    ["up", 0.5, 0.1],
    ["down", 0.5, 0.9],
    ["up_left", 0.1, 0.1],
    ["up_right", 0.9, 0.1],
    ["down_left", 0.1, 0.9],
    ["down_right", 0.9, 0.9]
  ];
  const center = point(0.5, 0.5);
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  const frames = [];
  for (const [label, x, y] of targets) {
    const target = point(x, y);
    await page.mouse.move(target.x, target.y, { steps: 10 });
    await page.evaluate(() => window.__compReq761DeferBlinkAudit());
    await page.waitForTimeout(label === "center" ? 620 : 2060);
    frames.push(await capture(label));
  }
  await page.mouse.up();
  const hardwareContact = await page.evaluate(
    () => window.__compReq761Contract().hardware_contact
  );

  const baseline = frames[0].eyes;
  const outlineStable = frames.every(frame =>
    frame.eyes.every((eye, side) =>
      JSON.stringify(eye.bounds) === JSON.stringify(baseline[side].bounds)
      && JSON.stringify(eye.envelope) === JSON.stringify(baseline[side].envelope)
      && eye.ink === baseline[side].ink
    )
  );
  const capsTapered = frames.every(frame =>
    frame.eyes.every(eye =>
      Math.max(eye.terminal_rows[0], eye.terminal_rows[3]) <= 5
      && Math.max(eye.terminal_rows[1], eye.terminal_rows[2]) <= 10
      && Math.max(eye.terminal_columns[0], eye.terminal_columns[3]) <= 5
      && Math.max(eye.terminal_columns[1], eye.terminal_columns[2]) <= 13
      && eye.terminal_rows[0] < eye.terminal_rows[1]
      && eye.terminal_rows[3] < eye.terminal_rows[2]
      && eye.terminal_columns[0] < eye.terminal_columns[1]
      && eye.terminal_columns[3] < eye.terminal_columns[2]
    )
  );

  const spatialOrder = [
    "up_left", "up", "up_right",
    "left", "center", "right",
    "down_left", "down", "down_right"
  ];
  const cards = spatialOrder.map(label => frames.find(frame => frame.label === label));
  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-772 真实拖动九方向眼壳审计</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0", background: "#202426", color: "#fff", fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "18px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid", gridTemplateColumns: "repeat(3, 320px)", gap: "12px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = card.data_url;
      image.width = 320;
      image.height = 320;
      image.style.imageRendering = "pixelated";
      caption.textContent = card.label;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, cards);
  await page.screenshot({
    path: path.join(screenshotRoot, "warm-eye-nine-direction-drag.png"),
    fullPage: true
  });

  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    nine_real_pointer_positions_captured: frames.length === 9,
    strict_1bpp_every_frame:
      frames.every(frame => JSON.stringify(frame.palette) === "[0,255]"),
    eye_body_bounds_ink_and_envelope_stable_during_drag: outlineStable,
    four_direction_eye_caps_tapered_every_frame: capsTapered,
    hardware_contact_zero: hardwareContact === 0
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    frames: frames.map(frame => ({
      label: frame.label,
      palette: frame.palette,
      eyes: frame.eyes,
      pointer_play: frame.interaction.pointer_play
    })),
    browser_errors: browserErrors,
    screenshot:
      ".cache/validation/comp-req-772-eye-drag-silhouette/screenshots/warm-eye-nine-direction-drag.png"
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
  eye_terminals: result.frames.map(frame => ({
    label: frame.label,
    eyes: frame.eyes.map(eye => ({
      rows: eye.terminal_rows,
      columns: eye.terminal_columns,
      ink: eye.ink
    }))
  })),
  screenshot: result.screenshot
}, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
