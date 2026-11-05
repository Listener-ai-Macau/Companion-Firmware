#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-748-pointer-interrupt");
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(screenshotRoot, { recursive: true });

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

async function canvasState(page, label) {
  return page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const boxes = [
      [72, 41, 9, 7],
      [96, 34, 9, 7],
      [120, 41, 9, 7]
    ];
    const dotInk = boxes.map(([left, top, width, height]) => {
      let ink = 0;
      for (let y = top; y < top + height; y += 1) {
        for (let x = left; x < left + width; x += 1) {
          if (data[(y * 200 + x) * 4] < 128) ink += 1;
        }
      }
      return ink;
    });
    return {
      label,
      family: document.querySelector("#familyLabel").textContent,
      dot_ink: dotInk,
      data_url: canvas.toDataURL("image/png"),
      snapshot: window.__compReq599Snapshot()
    };
  }, label);
}

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1200, height: 900 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  const box = await page.locator("#face").boundingBox();
  const center = {
    x: box.x + box.width * 0.5,
    y: box.y + box.height * 0.55
  };
  await page.mouse.move(center.x, center.y);

  const frames = [];
  frames.push(await canvasState(page, "stable_before"));
  await page.mouse.down();
  await page.waitForTimeout(40);
  frames.push(await canvasState(page, "stable_down"));
  await page.mouse.up();
  await page.waitForTimeout(90);
  await page.mouse.down();
  await page.waitForTimeout(40);
  await page.mouse.up();
  await page.waitForTimeout(560);
  frames.push(await canvasState(page, "transition_before_second"));
  await page.mouse.down();
  await page.waitForTimeout(40);
  frames.push(await canvasState(page, "interrupted_second_down"));
  await page.mouse.move(center.x + box.width * 0.18, center.y, { steps: 4 });
  frames.push(await canvasState(page, "interrupted_drag"));
  await page.mouse.up();
  await page.waitForTimeout(40);
  frames.push(await canvasState(page, "second_up"));

  const rebase = frames[3].snapshot.trace
    .filter(item => item.type === "touch_transition_rebased_on_pointer_down")
    .at(-1);

  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-748 连续按压中断验证</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gridTemplateColumns: "repeat(3, 300px)",
      gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = card.data_url;
      image.width = 300;
      image.height = 300;
      image.style.imageRendering = "pixelated";
      caption.textContent =
        `${card.label} · ${card.family} · 三点墨 ${card.dot_ink.join("/")}`;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, frames);
  await page.screenshot({
    path: path.join(screenshotRoot, "real-pointer-interrupt.png"),
    fullPage: true
  });

  const gesturePage = await browser.newPage({
    viewport: { width: 1000, height: 820 },
    deviceScaleFactor: 1
  });
  gesturePage.on("console", message => {
    if (message.type() === "error") browserErrors.push(`gesture-console:${message.text()}`);
  });
  gesturePage.on("pageerror", error =>
    browserErrors.push(`gesture-page:${error.message}`));
  await gesturePage.goto(fixedUrl, { waitUntil: "networkidle" });
  await gesturePage.waitForFunction(() => window.__compReq599Ready === true);
  await gesturePage.evaluate(() =>
    window.__compReq743SetRecordingGesture("edge_pull"));
  const gestureBox = await gesturePage.locator("#face").boundingBox();

  await gesturePage.mouse.move(
    gestureBox.x + gestureBox.width * 0.1,
    gestureBox.y + gestureBox.height * 0.9
  );
  await gesturePage.mouse.down();
  await gesturePage.waitForTimeout(540);
  await gesturePage.mouse.move(
    gestureBox.x + gestureBox.width * 0.48,
    gestureBox.y + gestureBox.height * 0.9,
    { steps: 8 }
  );
  await gesturePage.waitForTimeout(120);
  const recordingEntered =
    (await gesturePage.evaluate(() =>
      document.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode))
    === "recording";
  await gesturePage.mouse.up();
  await gesturePage.waitForTimeout(80);
  const recordingHeldAfterRelease =
    (await gesturePage.evaluate(() =>
      document.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode))
    === "recording";
  const silenceExit = await gesturePage.evaluate(() =>
    window.__compReq753InjectVoiceControl("silence_stop"));
  await gesturePage.waitForFunction(() =>
    document.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode
      === "expression",
    null,
    { timeout: 3500 });
  const recordingRetracted =
    (await gesturePage.evaluate(() =>
      document.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode))
    === "expression";

  await gesturePage.mouse.move(
    gestureBox.x + gestureBox.width * 0.5,
    gestureBox.y + gestureBox.height * 0.55
  );
  await gesturePage.mouse.down();
  await gesturePage.waitForTimeout(3400);
  const menuEntered =
    (await gesturePage.evaluate(() =>
      document.querySelector('[data-mode][aria-pressed="true"]')?.dataset.mode))
    === "menu";
  await gesturePage.mouse.up();

  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    calm_dots_preserved_during_press:
      frames[0].dot_ink.every(value => value > 0)
      && frames[1].dot_ink.every(value => value > 0)
      && frames[0].dot_ink.join(",") === frames[1].dot_ink.join(","),
    transition_hides_old_calm_dots:
      frames[2].dot_ink.every(value => value === 0),
    interrupted_press_does_not_restore_old_calm_dots:
      frames[3].dot_ink.every(value => value === 0)
      && frames[4].dot_ink.every(value => value === 0),
    interrupted_press_rebases_to_target:
      frames[3].snapshot.selected !== "calm"
      && rebase?.from === "calm"
      && rebase?.target === frames[3].snapshot.selected
      && rebase?.old_emotion_ornament_restored === false,
    recording_edge_pull_preserved:
      recordingEntered
      && recordingHeldAfterRelease
      && silenceExit.accepted
      && recordingRetracted,
    menu_three_second_hold_preserved: menuEntered,
    hardware_contact_zero:
      (await gesturePage.evaluate(() =>
        window.__compReq715Contract().hardware_contact)) === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_748.pointer_interrupt_no_calm_dots.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    frame_summary: frames.map(frame => ({
      label: frame.label,
      family: frame.family,
      selected: frame.snapshot.selected,
      dot_ink: frame.dot_ink
    })),
    rebase,
    screenshot:
      ".cache/validation/comp-req-748-pointer-interrupt/screenshots/real-pointer-interrupt.png",
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
