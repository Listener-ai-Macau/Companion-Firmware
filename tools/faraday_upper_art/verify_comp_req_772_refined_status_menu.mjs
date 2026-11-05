#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root, ".cache/validation/comp-req-772-refined-status-menu"
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
  const page = await browser.newPage({ viewport: { width: 1500, height: 1200 } });
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
    && typeof window.__compReq772FreezeBattery === "function"
    && typeof window.__compReq625FreezeMenuProgress === "function"
  );

  const inspect = label => page.evaluate(label => {
    const canvas = document.querySelector("#face");
    const context = canvas.getContext("2d", { willReadFrequently: true });
    const image = context.getImageData(0, 0, 200, 200);
    const value = (x, y) => image.data[(y * 200 + x) * 4];
    const bits = (left, top, width, height, black) => {
      const output = [];
      for (let y = top; y < top + height; y += 1) {
        for (let x = left; x < left + width; x += 1) {
          if ((value(x, y) < 128) === black) output.push([x, y]);
        }
      }
      return output;
    };
    const crop = document.createElement("canvas");
    crop.width = 24;
    crop.height = 14;
    crop.getContext("2d").putImageData(context.getImageData(166, 0, 24, 14), 0, 0);
    const cells = [[153, 31], [162, 31], [162, 40], [153, 40]];
    return {
      label,
      data_url: canvas.toDataURL("image/png"),
      battery_crop_url: crop.toDataURL("image/png"),
      palette: [...new Set(
        Array.from({ length: 200 * 200 }, (_, index) => image.data[index * 4])
      )].sort((a, b) => a - b),
      battery_white: bits(166, 0, 24, 14, false),
      menu_cell_ink: cells.map(([left, top]) =>
        bits(left, top, 6, 6, true).length
      )
    };
  }, label);

  const batteryFrames = [];
  for (const level of [0, 0.25, 0.5, 0.75, 1]) {
    const geometry = await page.evaluate(level =>
      window.__compReq772FreezeBattery(level), level);
    batteryFrames.push({
      level,
      geometry,
      ...(await inspect(`battery_${level}`))
    });
  }
  const emptyBattery = new Set(
    batteryFrames[0].battery_white.map(([x, y]) => `${x}:${y}`)
  );
  const batteryDiffInsideInterior = batteryFrames.every(frame =>
    frame.battery_white
      .filter(([x, y]) => !emptyBattery.has(`${x}:${y}`))
      .every(([x, y]) => x >= 174 && x <= 185 && y >= 5 && y <= 8)
  );
  const batteryStaticOutline = [...emptyBattery].every(key =>
    batteryFrames.every(frame =>
      frame.battery_white.some(([x, y]) => `${x}:${y}` === key)
    )
  );

  const menuSamples = [
    ["seed", 0],
    ["one", 0.5],
    ["two", 0.667],
    ["three", 0.834],
    ["four", 1]
  ];
  const menuFrames = [];
  for (const [label, progress] of menuSamples) {
    const state = await page.evaluate(progress =>
      window.__compReq625FreezeMenuProgress(progress), progress);
    menuFrames.push({
      progress,
      state,
      ...(await inspect(`menu_${label}`))
    });
  }

  const contract = await page.evaluate(() => window.__compReq625Contract());
  const batteryFillWidths = batteryFrames.map(frame => frame.geometry.fill_width);
  const batteryWhiteCounts = batteryFrames.map(frame => frame.battery_white.length);
  const menuInkRows = menuFrames.map(frame => frame.menu_cell_ink);
  const expectedMenuInk = [
    [16, 16, 16, 16],
    [32, 16, 16, 16],
    [32, 32, 16, 16],
    [32, 32, 32, 16],
    [32, 32, 32, 32]
  ];

  await page.evaluate(({ batteryFrames, menuFrames }) => {
    document.body.innerHTML = `
      <main>
        <h1>COMP-REQ-772 手机式电池与精修菜单徽章</h1>
        <h2>电池 0 / 25 / 50 / 75 / 100%</h2>
        <section id="battery"></section>
        <h2>圆角菜单徽章按左上 → 右上 → 右下 → 左下填实</h2>
        <section id="menu"></section>
      </main>`;
    Object.assign(document.body.style, {
      margin: "0", background: "#202426", color: "#fff", fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    for (const id of ["battery", "menu"]) {
      Object.assign(document.querySelector(`#${id}`).style, {
        display: "flex", gap: "12px", flexWrap: "wrap", marginBottom: "24px"
      });
    }
    const add = (parent, source, label, width, height) => {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      image.src = source;
      image.width = width;
      image.height = height;
      image.style.imageRendering = "pixelated";
      caption.textContent = label;
      figure.append(image, caption);
      parent.append(figure);
    };
    for (const frame of batteryFrames) {
      add(
        document.querySelector("#battery"),
        frame.battery_crop_url,
        `${Math.round(frame.level * 100)}%`,
        240,
        140
      );
    }
    for (const frame of menuFrames) {
      add(
        document.querySelector("#menu"),
        frame.data_url,
        `${Math.round(frame.progress * 100)}%`,
        240,
        240
      );
    }
  }, { batteryFrames, menuFrames });
  await page.screenshot({
    path: path.join(screenshotRoot, "phone-battery-and-menu-badge.png"),
    fullPage: true
  });

  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    strict_1bpp_all_samples:
      [...batteryFrames, ...menuFrames].every(
        frame => JSON.stringify(frame.palette) === "[0,255]"
      ),
    battery_single_body_and_terminal_fixed:
      batteryStaticOutline
      && batteryFrames.every(frame =>
        JSON.stringify(frame.geometry.body_bounds) === "[172,3,16,8]"
        && JSON.stringify(frame.geometry.terminal_bounds) === "[188,5,2,4]"
      ),
    battery_fill_is_continuous_monotonic_and_interior_only:
      JSON.stringify(batteryFillWidths) === "[0,3,6,9,12]"
      && batteryWhiteCounts.every((count, index) =>
        index === 0 || count > batteryWhiteCounts[index - 1])
      && batteryDiffInsideInterior,
    menu_badge_cell_ink_exact:
      JSON.stringify(menuInkRows) === JSON.stringify(expectedMenuInk),
    menu_fill_order_and_timing_protected:
      menuFrames.map(frame => frame.state.filled_cells).join(",") === "0,1,2,3,4"
      && JSON.stringify(contract.menu_hold.fill_order)
        === JSON.stringify(["upper_left", "upper_right", "lower_right", "lower_left"])
      && contract.menu_hold.threshold_ms === 3000
      && contract.menu_hold.cell_step_ms === 500,
    visual_language_contract_updated:
      contract.menu_hold.cell_fill === "rounded_menu_badge_2x2_outline_to_solid_cells"
      && JSON.stringify(contract.menu_hold.ornament_anchor_center) === "[160,38]"
      && JSON.stringify(contract.menu_hold.ornament_bounds) === "[149,27,22,22]",
    hardware_contact_zero:
      (await page.evaluate(() => window.__compReq772Contract().hardware_contact)) === 0
  };
  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    battery: {
      fill_widths: batteryFillWidths,
      white_counts: batteryWhiteCounts
    },
    menu: {
      ink_rows: menuInkRows,
      filled_cells: menuFrames.map(frame => frame.state.filled_cells)
    },
    browser_errors: browserErrors,
    screenshot:
      ".cache/validation/comp-req-772-refined-status-menu/screenshots/phone-battery-and-menu-badge.png"
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
