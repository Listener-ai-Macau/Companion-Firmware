#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");

function parseArgs(argv) {
  const result = {};
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith("--") || value === undefined) {
      throw new Error(`invalid argument near ${key || "<end>"}`);
    }
    result[key.slice(2)] = value;
  }
  return result;
}

const args = parseArgs(process.argv.slice(2));
const artifactRoot = args.output
  ? path.resolve(root, args.output)
  : path.join(
      root,
      ".cache/validation/comp-req-775-incremental-sync",
      "hardware-external-loader-acceptance",
      "touch-irq-stop-fix",
      "browser-pointer-contract"
    );
if (!artifactRoot.startsWith(`${root}${path.sep}`)) {
  throw new Error("output must remain inside repository");
}
let fixedUrl = args.url || null;
const currentContractPath = path.join(
  root,
  "cubeide/Companion_Nucleo_WB55RG_Bringup/build_freertos/generated/companion_browser_interaction_contract.json"
);
const currentContractBytes = fs.readFileSync(currentContractPath);
const currentContract = JSON.parse(currentContractBytes.toString("utf8"));
const expectedPageSha256 = currentContract.page_sha256;
const resultPath = path.join(artifactRoot, "MACHINE_READY.json");
fs.mkdirSync(artifactRoot, { recursive: true });

function loadPlaywright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
  ].filter(Boolean)) {
    try {
      return require(name);
    } catch {}
  }
  throw new Error("Playwright unavailable");
}

function sha256(bytes) {
  return crypto.createHash("sha256").update(bytes).digest("hex").toUpperCase();
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

let staticServer = null;
if (!fixedUrl) {
  const mime = {
    ".html": "text/html; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".pbm": "image/x-portable-bitmap",
    ".js": "text/javascript; charset=utf-8"
  };
  staticServer = http.createServer((request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, "http://127.0.0.1").pathname);
      const target = path.resolve(root, pathname.replace(/^\/+/, ""));
      if (target !== root && !target.startsWith(`${root}${path.sep}`)) {
        response.writeHead(403).end("forbidden");
        return;
      }
      const body = fs.readFileSync(target);
      response.writeHead(200, {
        "Content-Type": mime[path.extname(target).toLowerCase()] || "application/octet-stream",
        "Content-Length": body.length,
        "Cache-Control": "no-store"
      });
      response.end(body);
    } catch {
      response.writeHead(404).end("not found");
    }
  });
  await new Promise((resolve, reject) => {
    staticServer.once("error", reject);
    staticServer.listen(0, "127.0.0.1", resolve);
  });
  const address = staticServer.address();
  if (!address || typeof address === "string") throw new Error("temporary static server failed");
  fixedUrl = `http://127.0.0.1:${address.port}/.cache/validation/comp-req-628-status-bar/index.html`;
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const browserErrors = [];
const pageLoads = [];
page.on("pageerror", error => browserErrors.push(`pageerror: ${String(error)}`));
page.on("console", message => {
  if (message.type() === "error") browserErrors.push(`console: ${message.text()}`);
});

async function loadFresh(label) {
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  assert(response, `${label}: navigation did not return a response`);
  const body = await response.body();
  const identity = {
    label,
    requested_url: fixedUrl,
    final_url: page.url(),
    http_status: response.status(),
    body_bytes: body.length,
    body_sha256: sha256(body)
  };
  pageLoads.push(identity);
  assert(identity.http_status === 200, `${label}: HTTP ${identity.http_status}`);
  assert(identity.final_url === fixedUrl, `${label}: fixed URL redirected`);
  assert(identity.body_sha256 === expectedPageSha256, `${label}: page SHA-256 changed`);
  await page.waitForFunction(() => window.__compReq599Ready === true, null, {
    timeout: 15000
  });
  await page.evaluate(() => {
    window.__compReq599Restore();
    window.__compReq714SetScheduler(false);
    window.__compReq714ResetInteraction();
    window.__compReq743SetRecordingGesture("corner_double_tap");
    window.__compReq714ClearTrace();
  });
}

async function point(x, y) {
  const box = await page.locator("#face").boundingBox();
  assert(box, "face canvas has no bounding box");
  return {
    x: box.x + (x / 200) * box.width,
    y: box.y + (y / 200) * box.height
  };
}

async function click(x, y) {
  const target = await point(x, y);
  await page.mouse.click(target.x, target.y);
}

async function interactionState() {
  return page.evaluate(() => window.__compReq758InteractionState());
}

async function sampleMenuCells(label) {
  const sample = await page.evaluate(() => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const cells = [[153, 31], [162, 31], [162, 40], [153, 40]];
    const packed = new Uint8Array(5000);
    let blackPixels = 0;
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const black = data[(y * 200 + x) * 4] < 128;
        if (black) {
          blackPixels += 1;
        } else {
          packed[y * 25 + (x >> 3)] |= 0x80 >> (x & 7);
        }
      }
    }
    const ink = (left, top, width, height) => {
      let count = 0;
      for (let y = top; y < top + height; y += 1) {
        for (let x = left; x < left + width; x += 1) {
          if (data[(y * 200 + x) * 4] < 128) count += 1;
        }
      }
      return count;
    };
    return {
      cell_ink: cells.map(([left, top]) => ink(left, top, 6, 6)),
      ornament_ink: ink(149, 27, 22, 22),
      black_pixels: blackPixels,
      frame_base64: btoa(String.fromCharCode(...packed))
    };
  });
  sample.frame_sha256 = sha256(Buffer.from(sample.frame_base64, "base64"));
  delete sample.frame_base64;
  const screenshot = path.join(artifactRoot, `${label}.png`);
  await page.locator("#face").screenshot({ path: screenshot });
  return { ...sample, screenshot: path.relative(root, screenshot).replaceAll("\\", "/") };
}

async function waitForFilledMenuCells(count) {
  await page.waitForFunction(expected => {
    const canvas = document.querySelector("#face");
    const data = canvas.getContext("2d", { willReadFrequently: true })
      .getImageData(0, 0, 200, 200).data;
    const cells = [[153, 31], [162, 31], [162, 40], [153, 40]];
    const cellInk = cells.map(([left, top]) => {
      let ink = 0;
      for (let y = top; y < top + 6; y += 1) {
        for (let x = left; x < left + 6; x += 1) {
          if (data[(y * 200 + x) * 4] < 128) ink += 1;
        }
      }
      return ink;
    });
    return cellInk.filter(value => value === 32).length === expected;
  }, count, { timeout: 4000 });
}

let result;
try {
  await loadFresh("ordinary_single_tap");
  await click(100, 100);
  await page.waitForTimeout(60);
  const ordinarySingle = await interactionState();
  const ordinarySingleCommits = ordinarySingle.trace.filter(
    item => item.type === "single_tap_commit"
  );
  assert(ordinarySingleCommits.length === 1, "ordinary tap did not commit exactly once");
  assert(ordinarySingleCommits[0].immediate === true, "ordinary tap was not immediate");
  assert(
    ordinarySingle.trace.every(item => item.type !== "recording_enter"),
    "ordinary tap entered recording"
  );

  await loadFresh("ordinary_double_tap");
  await click(100, 100);
  await page.waitForTimeout(100);
  await click(100, 100);
  await page.waitForTimeout(60);
  const ordinaryDouble = await interactionState();
  const ordinaryDoubleCommits = ordinaryDouble.trace.filter(
    item => item.type === "single_tap_commit"
  );
  assert(ordinaryDoubleCommits.length === 2, "ordinary double tap lost a tap semantic");
  assert(
    ordinaryDoubleCommits.every(item => item.immediate === true),
    "ordinary double tap contained a delayed commit"
  );
  assert(
    ordinaryDouble.trace.every(item => item.type !== "recording_enter"),
    "ordinary double tap entered recording"
  );

  await loadFresh("lower_left_double_tap");
  const recordingReturnBefore = await sampleMenuCells("recording-return-before");
  await click(24, 170);
  await page.waitForTimeout(100);
  await click(24, 170);
  await page.waitForTimeout(80);
  const cornerDouble = await interactionState();
  const cornerRecording = cornerDouble.trace.filter(item => item.type === "recording_enter");
  assert(cornerRecording.length === 1, "lower-left double tap did not enter recording once");
  assert(
    cornerRecording[0].source === "lower_left_double_tap",
    "lower-left double tap used the wrong recording source"
  );
  assert(
    cornerDouble.trace.every(item => item.type !== "single_tap_commit"),
    "lower-left double tap leaked an ordinary tap commit"
  );
  await click(100, 100);
  await page.waitForTimeout(100);
  const recordingExitStartedAt = Date.now();
  await click(100, 100);
  const recordingExitDispatchMs = Date.now() - recordingExitStartedAt;
  await page.waitForTimeout(80);
  const recordingStopped = await interactionState();
  const recordingReturnAfter = await sampleMenuCells("recording-return-after");
  const recordingExit = recordingStopped.trace.filter(
    item => item.type === "recording_exit"
  );
  assert(recordingExit.length === 1, "second double tap did not exit recording once");
  assert(
    recordingReturnAfter.frame_sha256 === recordingReturnBefore.frame_sha256,
    "recording exit did not restore the exact pre-recording frame"
  );

  await loadFresh("long_press_menu_drag_and_exit");
  const hold = await point(100, 100);
  await page.mouse.move(hold.x, hold.y);
  await page.mouse.down();
  await waitForFilledMenuCells(1);
  const progress1 = await sampleMenuCells("hold-progress-1");
  await waitForFilledMenuCells(2);
  const progress2 = await sampleMenuCells("hold-progress-2");
  await waitForFilledMenuCells(3);
  const progress3 = await sampleMenuCells("hold-progress-3");
  await waitForFilledMenuCells(4);
  const progress4 = await sampleMenuCells("hold-progress-4");
  await page.mouse.up();
  await page.waitForFunction(() => window.__compReq657MenuState().active === true, null, {
    timeout: 1500
  });
  const enteredMenu = await page.evaluate(() => ({
    menu: window.__compReq657MenuState(),
    interaction: window.__compReq758InteractionState(),
    contract: window.__compReq625Contract()
  }));

  const expectedCellInk = [
    [32, 16, 16, 16],
    [32, 32, 16, 16],
    [32, 32, 32, 16],
    [32, 32, 32, 32]
  ];
  const progressSamples = [progress1, progress2, progress3, progress4];
  assert(
    progressSamples.every((sample, index) =>
      sample.cell_ink.every((value, cell) => value === expectedCellInk[index][cell])),
    `long-press four-cell ornament did not fill in browser order: ${
      JSON.stringify(progressSamples.map(sample => sample.cell_ink))
    }`
  );
  assert(
    progressSamples.every(sample => sample.ornament_ink > 0),
    "long-press ornament body was not visible"
  );
  assert(enteredMenu.menu.active, "long press did not enter the menu");
  assert(
    enteredMenu.contract.menu_hold.progress_cells === 4
      && enteredMenu.contract.menu_hold.threshold_ms === 3000,
    "browser long-press contract changed"
  );
  assert(
    enteredMenu.interaction.trace.filter(item => item.type === "menu_enter").length === 1,
    "long press did not produce exactly one menu_enter"
  );

  const dragStart = await point(100, 180);
  const dragMid = await point(100, 125);
  const dragEnd = await point(100, 55);
  await page.mouse.move(dragStart.x, dragStart.y);
  await page.mouse.down();
  await page.mouse.move(dragMid.x, dragMid.y, { steps: 5 });
  await page.waitForTimeout(520);
  await page.mouse.move(dragEnd.x, dragEnd.y, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(80);
  const afterDrag = await page.evaluate(() => ({
    menu: window.__compReq657MenuState(),
    interaction: window.__compReq758InteractionState()
  }));
  await page.locator("#face").screenshot({
    path: path.join(artifactRoot, "menu-after-vertical-drag.png")
  });
  const visibleDragCommits = afterDrag.interaction.trace.filter(
    item => item.type === "menu_scroll_drag_preview" && item.visible_commit === true
  );
  assert(afterDrag.menu.scroll_offset > 0, "menu vertical drag did not change scroll offset");
  assert(visibleDragCommits.length >= 2, "menu drag did not honor bounded visible cadence");
  assert(
    visibleDragCommits.every(item => item.cadence_ms === 500),
    "menu drag cadence changed from 500 ms"
  );
  assert(
    afterDrag.interaction.trace.some(item => item.type === "menu_scroll_end"),
    "menu vertical drag did not terminate as a scroll"
  );

  const swipeStart = await point(30, 100);
  const swipeEnd = await point(170, 100);
  await page.mouse.move(swipeStart.x, swipeStart.y);
  await page.mouse.down();
  await page.mouse.move(swipeEnd.x, swipeEnd.y, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(80);
  const afterExit = await page.evaluate(() => ({
    menu: window.__compReq657MenuState(),
    interaction: window.__compReq758InteractionState()
  }));
  assert(afterExit.menu.active === false, "right swipe did not exit the root menu");
  assert(
    afterExit.interaction.trace.filter(item => item.type === "menu_swipe_right").length === 1,
    "root menu right swipe was not classified exactly once"
  );
  assert(
    afterExit.interaction.trace.filter(
      item => item.type === "menu_exit" && item.source === "swipe_right"
    ).length === 1,
    "root menu right swipe did not produce exactly one menu_exit"
  );
  assert(browserErrors.length === 0, `browser errors: ${browserErrors.join(" | ")}`);

  result = {
    verdict: "MACHINE_READY",
    requirement: "COMP-REQ-775",
    generated_at: new Date().toISOString(),
    fixed_url: fixedUrl,
    expected_page_sha256: expectedPageSha256,
    resource_page_sha256: currentContract.resource_page_sha256,
    product_resource_id: currentContract.product_resource_id,
    interaction_contract_sha256: currentContract.contract_sha256,
    interaction_contract_file_sha256: sha256(currentContractBytes),
    page_loads: pageLoads,
    pointer_contract: {
      ordinary_single_tap: {
        single_tap_commits: ordinarySingleCommits,
        trace: ordinarySingle.trace
      },
      ordinary_double_tap: {
        single_tap_commits: ordinaryDoubleCommits,
        recording_enter_count: 0,
        trace: ordinaryDouble.trace
      },
      lower_left_double_tap: {
        recording_enter: cornerRecording,
        recording_exit: recordingExit,
        second_pointer_cycle_to_synchronous_restore_ms: recordingExitDispatchMs,
        return_frame_before: recordingReturnBefore,
        return_frame_after: recordingReturnAfter,
        exact_return_frame: recordingReturnAfter.frame_sha256 === recordingReturnBefore.frame_sha256,
        trace: recordingStopped.trace
      },
      long_press: {
        progress_samples: progressSamples,
        expected_cell_ink: expectedCellInk,
        menu_state: enteredMenu.menu,
        trace: enteredMenu.interaction.trace
      },
      menu_vertical_drag: {
        state: afterDrag.menu,
        visible_commit_count: visibleDragCommits.length,
        trace: afterDrag.interaction.trace
      },
      menu_right_swipe_exit: {
        state: afterExit.menu,
        trace: afterExit.interaction.trace
      }
    },
    browser_errors: browserErrors
  };
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  process.stdout.write(`MACHINE_READY ${resultPath}\n`);
} catch (error) {
  result = {
    verdict: "NO_GO",
    requirement: "COMP-REQ-775",
    generated_at: new Date().toISOString(),
    fixed_url: fixedUrl,
    expected_page_sha256: expectedPageSha256,
    page_loads: pageLoads,
    error: String(error?.stack || error),
    browser_errors: browserErrors
  };
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  process.stderr.write(`${result.error}\n`);
  process.exitCode = 1;
} finally {
  await browser.close();
  if (staticServer) await new Promise(resolve => staticServer.close(resolve));
}
