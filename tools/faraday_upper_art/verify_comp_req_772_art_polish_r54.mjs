#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-772-art-polish-r54");
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

function hashBits(bits) {
  return crypto.createHash("sha256").update(Buffer.from(bits)).digest("hex");
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({ viewport: { width: 1540, height: 1280 } });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq714FreezeLifeAction === "function"
    && typeof window.__compReq625FreezeMode === "function"
    && typeof window.__compReq628FreezeUpgrade === "function"
    && typeof window.__compReq752EnterSleep === "function"
  );
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  const capture = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const image = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200);
    const bits = [];
    const palette = new Set();
    for (let offset = 0; offset < image.data.length; offset += 4) {
      bits.push(image.data[offset] < 128 ? 1 : 0);
      palette.add([
        image.data[offset],
        image.data[offset + 1],
        image.data[offset + 2],
        image.data[offset + 3]
      ].join(","));
    }
    return {
      label,
      bits,
      palette: [...palette].sort(),
      data_url: canvas.toDataURL("image/png")
    };
  }, label);

  const regionInk = (frame, left, top, width, height) => {
    let ink = 0;
    for (let y = top; y < top + height; y += 1) {
      for (let x = left; x < left + width; x += 1) {
        ink += frame.bits[y * 200 + x];
      }
    }
    return ink;
  };
  const outsideHash = (frame, regions) => {
    const bits = [];
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const ignored = regions.some(([left, top, width, height]) =>
          x >= left && x < left + width && y >= top && y < top + height);
        if (!ignored) bits.push(frame.bits[y * 200 + x]);
      }
    }
    return hashBits(bits);
  };

  const families = [
    "calm", "curious", "delighted", "warm", "playful",
    "sleepy", "bashful", "thoughtful", "focused", "alert"
  ];
  const familyFrames = [];
  for (const family of families) {
    const pose = await page.evaluate(family =>
      window.__compReq714FreezeLifeAction(
        family, "notice_left", "hold", 0, 0, true
      ), family);
    familyFrames.push({ family, pose, ...(await capture(family)) });
  }

  await page.evaluate(() =>
    window.__compReq714FreezeLifeAction("calm", "notice_left", "hold", 0, 0, false));
  const chargingFrames = [];
  for (const frameIndex of [0, 1, 2]) {
    await page.evaluate(frameIndex =>
      window.__compReq625FreezeMode("charging", frameIndex), frameIndex);
    chargingFrames.push({
      frame_index: frameIndex,
      ...(await capture(`charging_${frameIndex}`))
    });
  }

  await page.evaluate(() =>
    window.__compReq714FreezeLifeAction("calm", "notice_left", "hold", 0, 0, false));
  const otaFrames = [];
  for (const progress of [0, 0.5, 1]) {
    const state = await page.evaluate(progress =>
      window.__compReq628FreezeUpgrade(progress), progress);
    otaFrames.push({
      progress,
      state,
      ...(await capture(`ota_${Math.round(progress * 100)}`))
    });
  }

  const sleepState = await page.evaluate(() =>
    window.__compReq752EnterSleep("machine_r54_static_check"));
  const sleepA = await capture("low_power_sleep_a");
  await page.waitForTimeout(1200);
  const sleepB = await capture("low_power_sleep_b");

  const statusGeometry = await page.evaluate(() =>
    window.__compReq772FreezeBattery(0.75));
  const statusFrame = await capture("status_optical_balance");
  const bluetoothWhiteInk =
    (7 * 14) - regionInk(statusFrame, 154, 0, 7, 14);
  const oldBluetoothSlotWhiteInk =
    (7 * 14) - regionInk(statusFrame, 145, 0, 7, 14);
  const timingContract = await page.evaluate(() => ({
    special: window.__compReq625Contract().special_modes,
    cadence_ms: window.__compReq757Contract().cadence_ms
  }));

  const chargingBaseInk = chargingFrames.map(frame =>
    regionInk(frame, 84, 185, 32, 11));
  const chargingEnergyInk = chargingFrames.map(frame =>
    regionInk(frame, 92, 168, 17, 16));
  const otaInk = otaFrames.map(frame =>
    regionInk(frame, 103, 0, 40, 14));
  const otaProgressWhite = otaFrames.map(frame =>
    12 - regionInk(frame, 118, 10, 12, 1));
  const otaOutsideHashes = otaFrames.map(frame =>
    outsideHash(frame, [[103, 0, 40, 14]]));
  const familyHashes = familyFrames.map(frame => hashBits(frame.bits));
  const closeFamilyHashes = ["calm", "warm", "bashful"].map(family =>
    hashBits(familyFrames.find(frame => frame.family === family).bits));

  const allFrames = [
    ...familyFrames,
    ...chargingFrames,
    ...otaFrames,
    sleepA,
    sleepB,
    statusFrame
  ];
  const strictPalette = ["0,0,0,255", "255,255,255,255"];

  const cards = [
    ...familyFrames.map(frame => ({
      section: "十表情原生对照",
      title: frame.family,
      data_url: frame.data_url
    })),
    ...chargingFrames.map(frame => ({
      section: "充电三阶段",
      title: `charging ${frame.frame_index + 1}/3`,
      data_url: frame.data_url
    })),
    ...otaFrames.map(frame => ({
      section: "OTA 顶部状态栏附件槽",
      title: `OTA ${Math.round(frame.progress * 100)}%`,
      data_url: frame.data_url
    })),
    {
      section: "低功耗锁定",
      title: "deep sleep stable",
      data_url: sleepA.data_url
    },
    {
      section: "状态栏光学校正",
      title: "time / Bluetooth / battery",
      data_url: statusFrame.data_url
    }
  ];

  await page.evaluate(cards => {
    document.body.innerHTML = "<main><h1>Companion r54 状态栏间距校正对照</h1></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    for (const sectionName of [...new Set(cards.map(card => card.section))]) {
      const heading = document.createElement("h2");
      heading.textContent = sectionName;
      const section = document.createElement("section");
      Object.assign(section.style, {
        display: "grid",
        gridTemplateColumns: "repeat(5, 240px)",
        gap: "14px",
        marginBottom: "28px"
      });
      for (const card of cards.filter(item => item.section === sectionName)) {
        const figure = document.createElement("figure");
        const image = document.createElement("img");
        const caption = document.createElement("figcaption");
        image.src = card.data_url;
        image.width = 240;
        image.height = 240;
        image.style.imageRendering = "pixelated";
        caption.textContent = card.title;
        figure.append(image, caption);
        section.append(figure);
      }
      document.querySelector("main").append(heading, section);
    }
  }, cards);

  const screenshotPath = path.join(
    screenshotRoot, "ten-expression-functional-status-contact-sheet.png"
  );
  await page.screenshot({ path: screenshotPath, fullPage: true });

  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    strict_1bpp_all_samples: allFrames.every(frame =>
      JSON.stringify(frame.palette) === JSON.stringify(strictPalette)),
    ten_expression_native_frames_present:
      familyFrames.length === 10 && new Set(familyHashes).size === 10,
    calm_warm_bashful_visually_distinct:
      new Set(closeFamilyHashes).size === 3,
    charging_base_static:
      new Set(chargingBaseInk).size === 1 && chargingBaseInk[0] > 0,
    charging_energy_progresses:
      chargingEnergyInk[0] > 0
      && chargingEnergyInk[1] > chargingEnergyInk[0]
      && chargingEnergyInk[2] > chargingEnergyInk[1],
    charging_and_ota_visible_stage_dwell_at_most_two_seconds:
      timingContract.cadence_ms === 480
      && Math.max(...timingContract.special.charging.dwell)
        * timingContract.cadence_ms <= 2000
      && Math.max(...timingContract.special.upgrading.dwell)
        * timingContract.cadence_ms <= 2000
      && new Set(timingContract.special.charging.dwell).size > 1
      && new Set(timingContract.special.upgrading.dwell).size > 1,
    ota_progress_visible_and_monotonic:
      otaInk.every(value => value > 0)
      && otaProgressWhite[0] === 0
      && otaProgressWhite[1] > otaProgressWhite[0]
      && otaProgressWhite[2] > otaProgressWhite[1],
    ota_progress_confined_to_safe_slot:
      new Set(otaOutsideHashes).size === 1,
    low_power_frame_is_static:
      sleepState.locked
      && !sleepState.scheduler_active
      && hashBits(sleepA.bits) === hashBits(sleepB.bits),
    status_phone_battery_body_preserved:
      JSON.stringify(statusGeometry.body_bounds) === "[168,3,16,8]"
      && JSON.stringify(statusGeometry.terminal_bounds) === "[184,5,2,4]",
    status_bluetooth_shifted_right_without_old_slot_residue:
      bluetoothWhiteInk > 0 && oldBluetoothSlotWhiteInk === 0,
    status_content_not_clipped:
      regionInk(statusFrame, 0, 0, 200, 14) > 0
      && regionInk(statusFrame, 0, 14, 200, 6) === 0,
    hardware_contact_zero:
      (await page.evaluate(() => window.__compReq772Contract().hardware_contact)) === 0
  };

  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    revision: "r54",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    evidence: {
      charging_base_ink: chargingBaseInk,
      charging_energy_ink: chargingEnergyInk,
      ota_ink: otaInk,
      ota_progress_white: otaProgressWhite,
      ota_outside_hashes: otaOutsideHashes,
      close_family_hashes: closeFamilyHashes,
      sleep_signature: hashBits(sleepA.bits),
      status_geometry: statusGeometry,
      bluetooth_white_ink: bluetoothWhiteInk,
      old_bluetooth_slot_white_ink: oldBluetoothSlotWhiteInk,
      timing: {
        cadence_ms: timingContract.cadence_ms,
        charging_dwell: timingContract.special.charging.dwell,
        ota_dwell: timingContract.special.upgrading.dwell
      }
    },
    browser_errors: browserErrors,
    screenshot:
      ".cache/validation/comp-req-772-art-polish-r54/screenshots/"
      + "ten-expression-functional-status-contact-sheet.png"
  };
} catch (error) {
  result = {
    status: "NO_GO",
    requirement: "COMP-REQ-772",
    revision: "r54",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    error: error.stack || String(error),
    browser_errors: browserErrors
  };
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(artifactRoot, result.status === "MACHINE_READY"
    ? "MACHINE_READY.json"
    : "NO_GO.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
process.exit(result.status === "MACHINE_READY" ? 0 : 1);
