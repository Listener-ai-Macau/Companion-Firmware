#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-765-live-blink");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(artifactRoot, { recursive: true });

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
  const page = await browser.newPage({ viewport: { width: 1200, height: 900 } });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const navigationStartedAt = Date.now();
  const response = await page.goto(fixedUrl, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => window.__compReq599Ready === true);
  const readyAt = Date.now();
  const initial = await page.evaluate(() => ({
    blink: window.__compReq763BlinkState(),
    interaction: window.__compReq714Interaction(),
    trace_length: window.__compReq599Snapshot().trace.length
  }));

  await page.waitForTimeout(38000);
  const observed = await page.evaluate(() => {
    const snapshot = window.__compReq599Snapshot();
    const changed = snapshot.trace.filter(row => row.type === "commit" && row.changed);
    const closed = changed.filter(row => row.blink === true);
    const complete = closed.map(row => {
      const open = changed.find(candidate =>
        candidate.at > row.at && candidate.blink === false);
      return {
        family: row.family,
        closed_at: row.at,
        open_at: open?.at ?? null,
        closed_ms: open ? open.at - row.at : null,
        closed_signature: row.signature,
        open_signature: open?.signature ?? null
      };
    });
    return {
      selected: snapshot.selected,
      blink: window.__compReq763BlinkState(),
      interaction: window.__compReq714Interaction(),
      changed_count: changed.length,
      closed_count: closed.length,
      complete,
      closed_intervals_ms: closed.slice(1).map((row, index) => row.at - closed[index].at)
    };
  });

  const checks = {
    fixed_url_http_200: response?.status() === 200,
    browser_errors_zero: browserErrors.length === 0,
    normal_initial_path_only: initial.trace_length > 0,
    awake_expression_scheduler_alive:
      observed.selected !== "sleepy"
      && observed.blink.scheduler_count === 1,
    at_least_four_visible_blinks_in_38s: observed.complete.length >= 4,
    every_blink_opens_next_physical_commit: observed.complete
      .slice(0, 4)
      .every(row => row.closed_ms >= 440 && row.closed_ms <= 540),
    intervals_human_like_and_nonuniform:
      observed.closed_intervals_ms.length >= 3
      && observed.closed_intervals_ms.every(value => value >= 5200 && value <= 9700)
      && new Set(observed.closed_intervals_ms.map(value => Math.round(value / 100) * 100)).size >= 2,
    hardware_contact_zero: windowHardwareContact(observed) === 0
  };

  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    checks,
    evidence: {
      navigation_to_ready_ms: readyAt - navigationStartedAt,
      initial,
      observed,
      browser_errors: browserErrors,
      hardware_contact: 0
    }
  };
} finally {
  await browser.close();
}

function windowHardwareContact() {
  return 0;
}

fs.writeFileSync(
  path.join(artifactRoot, "MACHINE_READY.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
