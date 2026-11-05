#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-762-764-blink-pointer-follow");
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
  const page = await browser.newPage({ viewport: { width: 1400, height: 960 } });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq762Contract === "function"
    && typeof window.__compReq763Contract === "function"
    && typeof window.__compReq764Contract === "function");

  const box = await page.locator("#face").boundingBox();
  const point = (x, y) => ({ x: box.x + box.width * x, y: box.y + box.height * y });
  const frame = label => page.evaluate(label => ({
    label,
    data_url: document.querySelector("#face").toDataURL("image/png"),
    state: window.__compReq714Interaction()
  }), label);

  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq761ResetRuntime("calm", true);
  });
  const authoredBlink = await page.evaluate(() => window.__compReq762Contract());
  const blinkStart = await page.evaluate(() => window.__compReq763BlinkState());
  await page.waitForTimeout(520);
  await page.click('[data-family="curious"]');
  const blinkAfterCurious = await page.evaluate(() => window.__compReq763BlinkState());
  await page.waitForTimeout(520);
  await page.click('[data-family="warm"]');
  const blinkAfterWarm = await page.evaluate(() => window.__compReq763BlinkState());
  await page.waitForTimeout(authoredBlink.first_visible_blink_ms + 700);
  const switchTrace = await page.evaluate(() =>
    window.__compReq599Snapshot().trace.filter(row =>
      row.type === "commit" && row.changed));
  const switchClosedIndex = switchTrace.findIndex(row => row.blink === true);
  const switchClosed = switchClosedIndex >= 0 ? switchTrace[switchClosedIndex] : null;
  const switchOpen = switchClosedIndex >= 0 ? switchTrace[switchClosedIndex + 1] : null;

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true);
  await page.evaluate(() => {
    window.__compReq761ResetRuntime("warm", true);
    window.__compReq714ClearTrace();
  });
  const center = point(0.5, 0.5);
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  await page.mouse.move(point(0.9, 0.5).x, point(0.9, 0.5).y, { steps: 8 });
  await page.waitForTimeout(1560);
  const rightFrame = await frame("right_target");
  await page.mouse.move(point(0.1, 0.5).x, point(0.1, 0.5).y, { steps: 10 });
  await page.waitForTimeout(2040);
  const leftFrame = await frame("left_target");
  await page.mouse.move(point(0.85, 0.85).x, point(0.85, 0.85).y, { steps: 10 });
  await page.waitForTimeout(2040);
  const diagonalFrame = await frame("diagonal_target");
  await page.evaluate(() => window.__compReq761ForceNextBlink());
  await page.waitForTimeout(520);
  const pointerBlinkFrame = await frame("pointer_blink_closed");
  await page.waitForTimeout(520);
  const followTrace = await page.evaluate(() => window.__compReq599Snapshot().trace);
  await page.mouse.up();

  const followRows = followTrace.filter(row => row.type === "tease_follow_commit");
  const followCommits = followTrace.filter(row =>
    row.type === "commit" && row.life_action === "pointer_follow");
  const boundedSteps = followRows.every(row =>
    row.per_axis_step_px.every(value => Math.abs(value) <= 2));
  const noOvershoot = followRows.every(row =>
    row.target_error.every((error, axis) => {
      const previousError = row.target_gravity[axis] - row.previous_gravity[axis];
      return error === 0 || Math.sign(error) === Math.sign(previousError);
    }));
  const groups = [];
  for (const row of followRows) {
    const key = row.target_gravity.join(":");
    if (!groups.length || groups.at(-1).key !== key) groups.push({ key, rows: [] });
    groups.at(-1).rows.push(row);
  }
  const monotonicChase = groups.every(group =>
    group.rows.every((row, index) => index === 0
      || row.target_error.reduce((sum, value) => sum + Math.abs(value), 0)
        <= group.rows[index - 1].target_error.reduce((sum, value) => sum + Math.abs(value), 0)));

  await page.reload({ waitUntil: "networkidle" });
  await page.waitForFunction(() => window.__compReq599Ready === true);
  await page.evaluate(() => {
    window.__compReq761ResetRuntime("warm", true);
    window.__compReq714ClearTrace();
  });
  const shortStart = point(0.5, 0.5);
  const shortEnd = point(0.65, 0.5);
  await page.mouse.move(shortStart.x, shortStart.y);
  await page.mouse.down();
  await page.mouse.move(shortEnd.x, shortEnd.y, { steps: 8 });
  await page.waitForTimeout(1100);
  await page.mouse.up();
  await page.waitForTimeout(1100);
  const returnTrace = await page.evaluate(() => window.__compReq599Snapshot().trace);
  const returnRows = returnTrace.filter(row => row.type === "pointer_follow_return_commit");

  const contracts = await page.evaluate(() => ({
    blinkVisibility: window.__compReq762Contract(),
    blinkIndependence: window.__compReq763Contract(),
    pointer: window.__compReq764Contract()
  }));

  const cards = [rightFrame, leftFrame, diagonalFrame, pointerBlinkFrame];
  await page.evaluate(cards => {
    document.body.innerHTML = "<main><h1>COMP-REQ-762/763/764 独立眨眼与注视跟随</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0", background: "#202426", color: "#fff", fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid", gridTemplateColumns: "repeat(4, 260px)", gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = card.data_url;
      image.width = 260;
      image.height = 260;
      image.style.imageRendering = "pixelated";
      caption.textContent = card.label;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, cards);
  await page.screenshot({
    path: path.join(screenshotRoot, "blink-independent-pointer-follow.png"),
    fullPage: true
  });

  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    emotion_switch_does_not_reset_blink_deadline:
      Math.abs(blinkAfterCurious.next_due_at - blinkStart.next_due_at) < 1
      && Math.abs(blinkAfterWarm.next_due_at - blinkStart.next_due_at) < 1
      && blinkAfterCurious.epoch === blinkStart.epoch
      && blinkAfterWarm.epoch === blinkStart.epoch,
    blink_occurs_on_current_family_after_switch:
      switchClosed?.family === "warm" && switchClosed?.blink === true,
    blink_opens_on_next_physical_commit:
      switchOpen?.blink === false
      && switchOpen.at - switchClosed.at >= 440
      && switchOpen.at - switchClosed.at <= 540,
    pointer_uses_multiple_monotonic_bounded_steps:
      followRows.length >= 8 && boundedSteps && noOvershoot && monotonicChase,
    pointer_reaches_latest_right_left_diagonal_targets:
      groups.some(group => group.key === "4:0" && group.rows.at(-1).target_error.every(value => value === 0))
      && groups.some(group => group.key === "-4:0" && group.rows.at(-1).target_error.every(value => value === 0))
      && groups.some(group => group.key === "4:4" && group.rows.at(-1).target_error.every(value => value === 0)),
    pointer_keeps_family_and_mouth_stable:
      followCommits.length >= 4
      && new Set(followCommits.map(row => row.family)).size === 1
      && followCommits.every(row => row.family === "warm")
      && new Set(followCommits.map(row => row.mouth_pose)).size === 1,
    pointer_brow_lags_and_stays_small:
      followRows.every(row => row.brow_gravity.every(value => Math.abs(value) <= 4))
      && followRows.some(row =>
        row.brow_gravity.some((value, axis) => value !== row.gravity[axis])),
    blink_composes_while_pointer_is_stationary:
      followCommits.some(row => row.blink === true)
      && followCommits.some((row, index) =>
        row.blink === true && followCommits[index + 1]?.blink === false),
    short_drag_returns_half_then_neutral_in_two_commits:
      returnRows.length === 2
      && JSON.stringify(returnRows.map(row => row.gravity)) === JSON.stringify([[1, 0], [0, 0]]),
    contracts_match:
      contracts.blinkVisibility.first_visible_blink_ms ===
        authoredBlink.first_visible_blink_ms
      && JSON.stringify(contracts.blinkVisibility.steady_interval_ms) ===
        JSON.stringify(authoredBlink.steady_interval_ms)
      && contracts.blinkIndependence.emotion_family_independent
      && !contracts.blinkIndependence.emotion_switch_resets_clock
      && contracts.pointer.gaze_max_step_px_per_axis === 2
      && contracts.pointer.release_without_transition.return_commits === 2
      && contracts.pointer.mouth_during_follow === "stable_current_emotion_mouth",
    hardware_contact_zero:
      Object.values(contracts).every(contract => contract.hardware_contact === 0)
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    checks,
    evidence: {
      blink_deadlines: {
        start: blinkStart.next_due_at,
        curious: blinkAfterCurious.next_due_at,
        warm: blinkAfterWarm.next_due_at
      },
      switched_blink_closed: switchClosed,
      switched_blink_open: switchOpen,
      switched_blink_family: switchClosed?.family ?? null,
      follow_rows: followRows,
      follow_mouths: [...new Set(followCommits.map(row => row.mouth_pose))],
      return_rows: returnRows,
      browser_errors: browserErrors
    },
    screenshot:
      ".cache/validation/comp-req-762-764-blink-pointer-follow/screenshots/blink-independent-pointer-follow.png"
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
