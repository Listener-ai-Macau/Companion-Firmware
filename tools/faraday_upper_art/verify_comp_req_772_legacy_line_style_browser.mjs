#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root,
  ".cache/validation/comp-req-772-legacy-line-style-browser"
);
const screenshotRoot = path.join(artifactRoot, "screenshots");
const manifestPath = path.join(artifactRoot, "legacy-face-manifest.json");
const fixedPage = path.join(
  root,
  ".cache/validation/comp-req-628-status-bar/index.html"
);
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
const legacyPageUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-616-ten-family-choreography/index.html";
const expectedPayload =
  "087654306CFC0ECA07BEE9F270DAF72C0DB269E3CF39C6D4D6098BB96EA137DC";
const families = [
  "calm",
  "curious",
  "delighted",
  "warm",
  "playful",
  "sleepy",
  "bashful",
  "thoughtful",
  "focused",
  "alert"
];
const expectedMouthPairs = {
  calm: { hold: "calm_closed_smile", accent: "calm_closed_smile" },
  curious: { hold: "owner_curious_round", accent: "owner_curious_round_open" },
  delighted: { hold: "owner_delighted_open", accent: "owner_delighted_open_wide" },
  warm: { hold: "recovered_gentle_smile", accent: "recovered_wide_smile" },
  playful: { hold: "recovered_side_smile_left", accent: "recovered_side_open_right" },
  sleepy: { hold: "owner_sleepy_rest_arc", accent: "recovered_large_open" },
  bashful: { hold: "owner_bashful_wave", accent: "owner_bashful_wave_deep" },
  thoughtful: { hold: "recovered_thoughtful_left", accent: "owner_thoughtful_deep" },
  focused: { hold: "recovered_pressed_short", accent: "recovered_pressed_long" },
  alert: { hold: "owner_alert_o", accent: "owner_alert_o_tall" }
};

fs.mkdirSync(screenshotRoot, { recursive: true });
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));

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

function sha256(filePath) {
  return crypto.createHash("sha256").update(fs.readFileSync(filePath))
    .digest("hex").toUpperCase();
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function sheet(cards, title, paired = false) {
  const body = cards.map(card => `
    <figure>
      <figcaption>${escapeHtml(card.label)}</figcaption>
      <div class="${paired ? "pair" : "single"}">
        ${card.images.map(image => `
          <div><img src="${image.dataUrl}"><span>${escapeHtml(image.label)}</span></div>
        `).join("")}
      </div>
    </figure>`).join("");
  return `<!doctype html><meta charset="utf-8"><style>
    *{box-sizing:border-box}body{margin:0;background:#202426;color:#fff;
    font-family:Segoe UI,Arial,sans-serif;padding:28px}h1{font-size:26px;margin:0 0 24px}
    main{display:grid;grid-template-columns:repeat(5,max-content);gap:18px}
    figure{margin:0;background:#2c3235;padding:10px;border-radius:4px}
    figcaption{font-weight:700;margin:0 0 8px}.pair{display:flex;gap:8px}
    .single{display:block}.pair div,.single div{display:grid;gap:4px}
    img{width:200px;height:200px;image-rendering:pixelated;background:#fff}
    span{font-size:12px;color:#d8dddf}
  </style><h1>${escapeHtml(title)}</h1><main>${body}</main>`;
}

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 2260, height: 1120 },
    deviceScaleFactor: 1
  });
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
    && typeof window.__compReq772Contract === "function"
    && typeof window.__compReq749FreezeFamilyMouth === "function"
    && typeof window.__compReq714FreezeLifeAction === "function"
    && typeof window.__compReq772FreezeOrnamentMotion === "function"
  );
  await page.evaluate(() => window.__compReq714SetScheduler(false));
  const contract = await page.evaluate(() => window.__compReq772Contract());
  const mouthContract = await page.evaluate(() => window.__compReq750Contract());
  const generatedBounds = await page.evaluate(
    () => window.__compReq728Contract().generated_component_bounds
  );
  const legacyLink = await page.locator(".legacy-page-link").getAttribute("href");
  const familyActions = await page.evaluate(
    () => window.__compReq751Contract().family_actions
  );
  const rows = [];

  for (const family of families) {
    rows.push(await page.evaluate(async ({ family, action }) => {
      const canvas = document.querySelector("#face");
      const context = canvas.getContext("2d", { willReadFrequently: true });
      const bits = data => {
        let value = "";
        const palette = new Set();
        for (let index = 0; index < data.length; index += 4) {
          palette.add(data[index]);
          value += data[index] < 128 ? "1" : "0";
        }
        return { value, palette: [...palette].sort((a, b) => a - b) };
      };
      const load = source => new Promise((resolve, reject) => {
        const image = new Image();
        image.onload = () => {
          const scratch = document.createElement("canvas");
          scratch.width = scratch.height = 200;
          const scratchContext = scratch.getContext("2d", { willReadFrequently: true });
          scratchContext.drawImage(image, 0, 0);
          const frame = scratchContext.getImageData(0, 0, 200, 200);
          resolve({ bits: bits(frame.data), dataUrl: scratch.toDataURL("image/png") });
        };
        image.onerror = reject;
        image.src = source;
      });
      const inspectMouth = (pose, frame) => {
        const bounds = pose.mouth_placement.rasterBounds;
        const isInk = (x, y) =>
          frame.data[(y * 200 + x) * 4] < 128;
        const ink = [];
        for (let y = bounds.top; y <= bounds.bottom; y += 1) {
          for (let x = bounds.left; x <= bounds.right; x += 1) {
            if (isInk(x, y)) ink.push([x, y]);
          }
        }
        const keys = new Set(ink.map(([x, y]) => `${x}:${y}`));
        const orthogonallySupported = ink.filter(([x, y]) =>
          keys.has(`${x - 1}:${y}`)
          || keys.has(`${x + 1}:${y}`)
          || keys.has(`${x}:${y - 1}`)
          || keys.has(`${x}:${y + 1}`)
        ).length;
        return {
          pose: pose.mouth_pose,
          bounds,
          clearBounds: pose.mouth_placement.clearBounds,
          inkPixels: ink.length,
          orthogonallySupported,
          allPixelsHaveStrokeNeighbor:
            ink.length > 0 && orthogonallySupported === ink.length
        };
      };

      if (family !== "sleepy") {
        window.__compReq761FreezeBlink(family, false);
      }
      const pose = window.__compReq749FreezeFamilyMouth(
        family, "hold", 0, "rest"
      );
      const candidateFrame = context.getImageData(0, 0, 200, 200);
      const holdMouth = inspectMouth(pose, candidateFrame);
      const candidate = {
        bits: bits(candidateFrame.data),
        dataUrl: canvas.toDataURL("image/png")
      };
      const accentPose = window.__compReq749FreezeFamilyMouth(
        family, "accent", 1, "rest"
      );
      const accentFrame = context.getImageData(0, 0, 200, 200);
      const accentMouth = inspectMouth(accentPose, accentFrame);
      const accent = {
        bits: bits(accentFrame.data),
        dataUrl: canvas.toDataURL("image/png")
      };
      let blinkDataUrl = candidate.dataUrl;
      if (family !== "sleepy") {
        window.__compReq761FreezeBlink(family, true);
        blinkDataUrl = canvas.toDataURL("image/png");
      }
      const fusedSource = `finished-balanced-${family}.png`;
      const styled = await load(
        `/.cache/validation/comp-req-772-legacy-line-style-browser/${fusedSource}`
      );
      const previous = await load(
        `/.cache/validation/comp-req-727-generated-emotion-rig/faces/${family}.png`
      );
      const legacy = await load(
        `/.cache/validation/comp-req-772-legacy-line-style-browser/legacy-${family}-hold.png`
      );
      const clear = pose.mouth_placement.clearBounds;
      const componentBounds =
        window.__compReq728Contract().generated_component_bounds[family];
      const eyeBoxes = componentBounds.eyes;
      const browBoxes = componentBounds.brows;
      const cheekBoxes = componentBounds.cheeks;
      let mismatchOutsideMouth = 0;
      let mismatchOutsideEyesAndMouth = 0;
      let candidateStatus = "";
      for (let y = 0; y < 200; y += 1) {
        for (let x = 0; x < 200; x += 1) {
          const at = y * 200 + x;
          if (y < 14) candidateStatus += candidate.bits.value[at];
          const inMouth = x >= clear.left && x <= clear.right
            && y >= clear.top && y <= clear.bottom;
          const inEyes = eyeBoxes.some(([left, top, width, height]) =>
            x >= left - 2 && x < left + width + 2
            && y >= top - 2 && y < top + height + 2
          );
          const inBrows = browBoxes.some(([left, top, width, height]) =>
            x >= left - 2 && x < left + width + 2
            && y >= top - 2 && y < top + height + 2
          );
          const inCheeks = cheekBoxes.some(([left, top, width, height]) =>
            x >= left - 3 && x < left + width + 3
            && y >= top - 3 && y < top + height + 3
          );
          if (y >= 14 && !inMouth
              && candidate.bits.value[at] !== styled.bits.value[at]) {
            mismatchOutsideMouth += 1;
            if (!inEyes && !inBrows && !inCheeks) mismatchOutsideEyesAndMouth += 1;
          }
        }
      }

      window.__compReq714FreezeLifeAction(
        family, action, "accent", 0, 0, true
      );
      const richFrame = context.getImageData(0, 0, 200, 200);
      const rich = {
        bits: bits(richFrame.data),
        dataUrl: canvas.toDataURL("image/png")
      };
      let richDifference = 0;
      let richStatus = "";
      for (let at = 0; at < 40000; at += 1) {
        if (rich.bits.value[at] !== candidate.bits.value[at]) richDifference += 1;
        if (at < 14 * 200) richStatus += rich.bits.value[at];
      }
      return {
        family,
        action,
        mouthPose: pose.mouth_pose,
        mismatchOutsideMouth,
        mismatchOutsideEyesAndMouth,
        candidatePalette: candidate.bits.palette,
        richPalette: rich.bits.palette,
        statusStable: candidateStatus === richStatus,
        richDifference,
        mouthStates: [holdMouth, accentMouth],
        previousDataUrl: previous.dataUrl,
        legacyDataUrl: legacy.dataUrl,
        candidateDataUrl: candidate.dataUrl,
        accentDataUrl: accent.dataUrl,
        blinkDataUrl,
        richDataUrl: rich.dataUrl
      };
    }, { family, action: familyActions[family][0] }));
  }

  const ornamentRows = [];
  for (const family of families) {
    ornamentRows.push(await page.evaluate(family => {
      if (family !== "sleepy") {
        window.__compReq761FreezeBlink(family, false);
      }
      const samples = Array.from(
        { length: 64 },
        (_, value) => window.__compReq772FreezeOrnamentMotion(family, value)
      );
      const positionKey = sample =>
        `${sample.placement_offset[0]}:${sample.placement_offset[1]}`;
      const positions = [...new Set(samples.map(positionKey))];
      const reviewSamples = family === "calm"
        ? [samples[0], samples.find(sample =>
            JSON.stringify(sample.motion.local_dot_levels) === "[2,1,0]"
          ) || samples[1]]
        : ["curious", "alert"].includes(family)
          ? [
              [...samples].sort((left, right) =>
                left.motion.angle_deg - right.motion.angle_deg
              )[0],
              [...samples].sort((left, right) =>
                right.motion.angle_deg - left.motion.angle_deg
              )[0]
            ]
          : [
              samples.find(sample => sample.motion.local_stage === 2)
                || samples[0],
              samples.find(sample => sample.motion.local_stage === 3)
                || samples[1]
            ];
      const reviewDataUrls = reviewSamples.map(sample => {
        window.__compReq772FreezeOrnamentMotion(family, sample.value);
        return document.querySelector("#face").toDataURL("image/png");
      });
      return {
        family,
        positions,
        samples,
        reviewPositions: reviewSamples.map(positionKey),
        reviewDataUrls
      };
    }, family));
  }

  const comparisonModeLoads = [];
  for (const style of ["fused", "rich", "legacy616"]) {
    const modePage = await browser.newPage();
    const modeErrors = [];
    modePage.on("console", message => {
      if (message.type() === "error") modeErrors.push(`console:${message.text()}`);
    });
    modePage.on("pageerror", error => modeErrors.push(`page:${error.message}`));
    await modePage.addInitScript(value => {
      sessionStorage.setItem("companion.comp_req_772.line_style.r15", value);
    }, style);
    const modeResponse = await modePage.goto(fixedUrl, { waitUntil: "networkidle" });
    await modePage.waitForFunction(() =>
      window.__compReq599Ready === true
      && typeof window.__compReq772Contract === "function"
    );
    const modeContract = await modePage.evaluate(() => window.__compReq772Contract());
    comparisonModeLoads.push({
      requested: style,
      active: modeContract.active_line_style,
      status: modeResponse?.status() ?? 0,
      url: modePage.url(),
      browser_errors: modeErrors
    });
    await modePage.close();
  }

  const canvas = page.locator("#face");
  await canvas.screenshot({
    path: path.join(screenshotRoot, "fixed-url-live-canvas.png")
  });

  const comparisonCards = rows.map(row => ({
    label: row.family,
    images: [
      { label: "此前丰富版线条", dataUrl: row.previousDataUrl },
      { label: "最满意 616 线条参考", dataUrl: row.legacyDataUrl },
      { label: "当前角色化融合候选", dataUrl: row.candidateDataUrl }
    ]
  }));
  await page.setContent(sheet(
    comparisonCards,
    "同一构图三方对照：当前丰富版、最满意 616 参考、角色化融合候选",
    true
  ));
  await page.screenshot({
    path: path.join(screenshotRoot, "previous-vs-legacy-line-style.png"),
    fullPage: true
  });

  const mouthCards = rows.map(row => ({
    label: row.family,
    images: [
      {
        label: `静态 · ${row.mouthStates[0].pose}`,
        dataUrl: row.candidateDataUrl
      },
      {
        label: `强调 · ${row.mouthStates[1].pose}`,
        dataUrl: row.accentDataUrl
      }
    ]
  }));
  await page.setContent(sheet(
    mouthCards,
    "十类表情全嘴型检查：静态与强调共二十个状态",
    true
  ));
  await page.screenshot({
    path: path.join(screenshotRoot, "all-family-hold-accent-mouths.png"),
    fullPage: true
  });

  const blinkCards = rows.map(row => ({
    label: row.family,
    images: row.family === "sleepy"
      ? [{ label: "低功耗困倦闭眼", dataUrl: row.blinkDataUrl }]
      : [
          { label: "开放眼身份骨架", dataUrl: row.candidateDataUrl },
          { label: "独立自然眨眼", dataUrl: row.blinkDataUrl }
        ]
  }));
  await page.setContent(sheet(
    blinkCards,
    "十类整脸身份检查：清醒睁眼与独立自然眨眼、困倦低功耗闭眼",
    true
  ));
  await page.screenshot({
    path: path.join(screenshotRoot, "all-family-open-blink-balance.png"),
    fullPage: true
  });

  const ornamentCards = ornamentRows.map(row => ({
    label: row.family,
    images: [
      {
        label: `活动位置 A · ${row.reviewPositions[0]}`,
        dataUrl: row.reviewDataUrls[0]
      },
      {
        label: `活动位置 B · ${row.reviewPositions[1]}`,
        dataUrl: row.reviewDataUrls[1]
      }
    ]
  }));
  await page.setContent(sheet(
    ornamentCards,
    "十类饰件原地编舞与遮挡检查：统一脸外锚位的非周期局部强调",
    true
  ));
  await page.screenshot({
    path: path.join(screenshotRoot, "all-family-fixed-anchor-ornaments.png"),
    fullPage: true
  });

  const richCards = rows.map(row => ({
    label: `${row.family} · ${row.action}`,
    images: [{ label: "当前嘴型 + 情绪饰件 + 角色化融合线条", dataUrl: row.richDataUrl }]
  }));
  await page.setContent(sheet(
    richCards,
    "十情绪丰富度保留：语义嘴型、情绪饰件与角色化融合线条",
    false
  ));
  await page.screenshot({
    path: path.join(screenshotRoot, "rich-ten-family-candidate.png"),
    fullPage: true
  });

  const manifestRows = Object.fromEntries(
    manifest.families.map(row => [row.family, row])
  );
  const proportionMetrics = families.map(family => {
    const bounds = generatedBounds[family];
    const [leftEye, rightEye] = bounds.eyes;
    const [mouth] = bounds.mouth;
    const eyeMidpoint = (
      leftEye[0] + leftEye[2] / 2
      + rightEye[0] + rightEye[2] / 2
    ) / 2;
    const mouthMidpoint = mouth[0] + mouth[2] / 2;
    const browGaps = bounds.brows.map((brow, index) =>
      bounds.eyes[index][1] - (brow[1] + brow[3])
    );
    const faceBoxes = [
      ...bounds.eyes,
      ...bounds.brows,
      ...bounds.nose,
      ...bounds.mouth,
      ...bounds.cheeks
    ];
    const faceLeft = Math.min(...faceBoxes.map(box => box[0]));
    const faceTop = Math.min(...faceBoxes.map(box => box[1]));
    const faceRight = Math.max(...faceBoxes.map(box => box[0] + box[2] - 1));
    const faceBottom = Math.max(...faceBoxes.map(box => box[1] + box[3] - 1));
    return {
      family,
      eye_origins: [
        [leftEye[0], leftEye[1]],
        [rightEye[0], rightEye[1]]
      ],
      eye_widths: [leftEye[2], rightEye[2]],
      eye_heights: [leftEye[3], rightEye[3]],
      eye_top_delta: Math.abs(leftEye[1] - rightEye[1]),
      eye_origin_spacing: rightEye[0] - leftEye[0],
      mouth_size: [mouth[2], mouth[3]],
      mouth_origin: [mouth[0], mouth[1]],
      nose_origin: [bounds.nose[0][0], bounds.nose[0][1]],
      face_bounds: [
        faceLeft,
        faceTop,
        faceRight - faceLeft + 1,
        faceBottom - faceTop + 1
      ],
      face_center: [
        (faceLeft + faceRight) / 2,
        (faceTop + faceBottom) / 2
      ],
      mouth_center_offset: mouthMidpoint - eyeMidpoint,
      mouth_eye_gap:
        mouth[1] - Math.max(
          leftEye[1] + leftEye[3],
          rightEye[1] + rightEye[3]
        ),
      brow_eye_gaps: browGaps
    };
  });
  const awakeProportions = proportionMetrics.filter(
    row => row.family !== "sleepy"
  );
  const sleepyProportions = proportionMetrics.find(
    row => row.family === "sleepy"
  );
  const runtimeMouthMetrics = rows.map(row => {
    const bounds = generatedBounds[row.family];
    const [leftEye, rightEye] = bounds.eyes;
    const eyeMidpoint = (
      leftEye[0] + leftEye[2] / 2
      + rightEye[0] + rightEye[2] / 2
    ) / 2;
    return {
      family: row.family,
      center_offsets: row.mouthStates.map(mouth =>
        (mouth.bounds.left + mouth.bounds.right) / 2 - eyeMidpoint
      )
    };
  });
  const legacyResponse = await page.request.get(legacyPageUrl);
  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    accepted_616_payload_exact:
      manifest.source_sha256 === expectedPayload
      && contract.accepted_style_reference.payload_sha256 === expectedPayload,
    accepted_616_awake_geometry_is_source:
      contract.geometry_source
        === "crafted_616_awake_shells_plus_current_family_highlights_and_sleepy_closed",
    ten_family_sources_exact:
      JSON.stringify(Object.keys(contract.face_sources)) === JSON.stringify(families)
      && Object.entries(contract.face_sources).every(
        ([family, source]) => source === `finished-balanced-${family}.png`
      ),
    fused_default_and_three_in_page_modes:
      contract.active_line_style === "fused"
      && JSON.stringify(contract.comparison_modes)
        === JSON.stringify(["fused", "rich", "legacy616"]),
    all_comparison_modes_load_at_fixed_url:
      comparisonModeLoads.every(row =>
        row.requested === row.active
        && row.status === 200
        && row.url === fixedUrl
        && row.browser_errors.length === 0
      ),
    awake_sources_keep_616_shells_and_current_two_highlights:
      families.filter(family => family !== "sleepy").every(family =>
        contract.face_sources[family] === `finished-balanced-${family}.png`
        && manifestRows[family].crafted_eye_metrics.length === 2
        && manifestRows[family].crafted_eye_metrics.every(eye =>
          eye.highlight_components === 2
          && eye.one_pixel_black_safe_border === true
          && eye.crafted_eye_components === 1
          && eye.ink_ratio >= 0.93
          && eye.ink_ratio <= 1.02
          && eye.crafted_terminal_row_widths[0]
            < eye.crafted_terminal_row_widths[1]
          && eye.crafted_terminal_row_widths[3]
            < eye.crafted_terminal_row_widths[2]
          && eye.crafted_terminal_column_heights[0]
            < eye.crafted_terminal_column_heights[1]
          && eye.crafted_terminal_column_heights[3]
            < eye.crafted_terminal_column_heights[2]
          && Math.max(
            eye.crafted_terminal_row_widths[0],
            eye.crafted_terminal_row_widths[3]
          ) <= 5
          && Math.max(
            eye.crafted_terminal_row_widths[1],
            eye.crafted_terminal_row_widths[2]
          ) <= 10
          && Math.max(
            eye.crafted_terminal_column_heights[0],
            eye.crafted_terminal_column_heights[3]
          ) <= 5
          && Math.max(
            eye.crafted_terminal_column_heights[1],
            eye.crafted_terminal_column_heights[2]
          ) <= 13
        )
      ),
    sleepy_closed_eye_identity_preserved:
      manifestRows.sleepy.styled_metrics.styled_ink_pixels
        < manifestRows.sleepy.kept_face_ink_pixels * 0.55,
    frozen_legacy_page_available_from_fixed_page:
      legacyLink
        === "/.cache/validation/comp-req-616-ten-family-choreography/index.html"
      && legacyResponse.status() === 200,
    original_ornaments_restored_for_all_families:
      contract.ornament_root
        === "/.cache/validation/comp-req-727-generated-emotion-rig/",
    all_semantic_mouths_use_weighted_stroke:
      contract.mouth_line_weight
        === "direction_aware_two_pixel_stroke_for_all_semantic_mouths",
    all_runtime_mouths_centered_on_eye_midline:
      JSON.stringify(contract.mouth_center_correction_x)
        === JSON.stringify({ awake: 2, sleepy: 1 })
      && runtimeMouthMetrics.every(row =>
        row.center_offsets.every(offset => Math.abs(offset) <= 0.75)
      ),
    all_twenty_mouth_states_have_supported_two_pixel_strokes:
      rows.every(row => row.mouthStates.every(mouth =>
        mouth.inkPixels > 0
        && mouth.allPixelsHaveStrokeNeighbor
        && mouth.clearBounds.left >= 0
        && mouth.clearBounds.top >= 14
        && mouth.clearBounds.right < 200
        && mouth.clearBounds.bottom < 200
      )),
    calm_dots_have_wider_even_spacing:
      JSON.stringify(contract.calm_dot_spread_x) === "[-2,1,4]",
    calm_dots_are_outside_face:
      JSON.stringify(contract.calm_dot_offset) === "[3,-28]"
      && ornamentRows.find(row => row.family === "calm").samples.every(
        sample => sample.ornament_bounds.bottom < 54
      ),
    all_ornaments_choreograph_at_fixed_anchor_without_overlap:
      contract.ornament_motion.fixed_anchor === true
      && contract.ornament_motion.bounded_anchor_region === true
      && contract.ornament_motion.kind
        === "fixed_anchor_punctuation_tilt"
      && JSON.stringify(contract.ornament_motion.anchor) === "[8,28]"
      && JSON.stringify(contract.ornament_motion.placement_translation_px)
        === "[0,0]"
      && JSON.stringify(contract.ornament_motion.punctuation_families)
        === '["curious","alert"]'
      && JSON.stringify(contract.ornament_motion.punctuation_tilt_degrees)
        === "[-8,8]"
      && contract.ornament_motion.returns_to_anchor === true
      && JSON.stringify(contract.ornament_motion.calm_profile_duration_commits)
        === "[1,3]"
      && JSON.stringify(contract.ornament_motion.local_hold_commits) === "[2,4]"
      && JSON.stringify(contract.ornament_motion.local_emphasis_commits) === "[2,4]"
      && ornamentRows.every(row =>
        row.samples.every(sample =>
          sample.face_overlap_pixels === 0
          && sample.ornament_ink_pixels > 0
          && sample.ornament_bounds.left >= 0
          && sample.ornament_bounds.top >= 14
          && sample.ornament_bounds.right < 200
          && sample.ornament_bounds.bottom < 200
        )
        && new Set(row.samples.map(sample =>
          sample.ornament_components
        )).size === 1
        && (row.family === "calm" || (
          row.positions.length === 1
          && new Set(row.samples.map(sample =>
            sample.placement_offset[1]
          )).size === 1
          && row.samples.every(sample =>
            sample.motion.motion_kind === "fixed_anchor_punctuation_tilt"
            && sample.motion.fixed_pivot === true
          )
          && (["curious", "alert"].includes(row.family)
            ? Math.min(...row.samples.map(sample =>
                sample.motion.angle_deg
              )) < 0
              && Math.max(...row.samples.map(sample =>
                sample.motion.angle_deg
              )) > 0
              && Math.max(...row.samples.map(sample =>
                Math.abs(sample.motion.angle_deg)
              )) <= 8
            : new Set(row.samples.map(sample =>
                sample.motion.local_stage
              )).size >= 2
              && row.samples.every(sample => sample.motion.angle_deg === 0))
        ))
      ),
    ten_family_overall_proportions_coordinated:
      awakeProportions.every(row =>
        JSON.stringify(row.eye_origins) === "[[42,93],[125,93]]"
        && JSON.stringify(row.eye_widths) === "[33,34]"
        && JSON.stringify(row.eye_heights) === "[45,45]"
        && row.eye_top_delta === 0
        && row.eye_origin_spacing === 83
        && JSON.stringify(row.mouth_size) === "[23,8]"
        && JSON.stringify(row.nose_origin) === "[94,129]"
        && JSON.stringify(row.mouth_origin) === "[87,142]"
        && Math.abs(row.mouth_center_offset + 1.75) < 0.001
        && row.mouth_eye_gap >= 4
        && row.mouth_eye_gap <= 5
        && row.brow_eye_gaps.every(gap => gap >= 7 && gap <= 25)
      )
      && sleepyProportions.eye_widths.every(width =>
        width >= 31 && width <= 32
      )
      && JSON.stringify(sleepyProportions.eye_origins) === "[[47,110],[122,110]]"
      && JSON.stringify(sleepyProportions.eye_heights) === "[11,11]"
      && sleepyProportions.eye_top_delta === 0
      && JSON.stringify(sleepyProportions.mouth_size) === "[15,14]"
      && JSON.stringify(sleepyProportions.nose_origin) === "[94,122]"
      && JSON.stringify(sleepyProportions.mouth_origin) === "[92,135]"
      && Math.abs(sleepyProportions.mouth_center_offset + 0.75) < 0.001
      && sleepyProportions.mouth_eye_gap === 14,
    rigid_identity_balance_declared_and_asset_backed:
      contract.identity_balance.method === "rigid_whole_face_translation_only"
      && JSON.stringify(contract.identity_balance.awake_anchor)
        === JSON.stringify({
          left_eye: [42, 93],
          right_eye: [125, 93],
          nose: [94, 129],
          mouth: [87, 142]
        })
      && families.every(family =>
        JSON.stringify(contract.identity_balance.offsets[family])
          === JSON.stringify(manifestRows[family].balance_offset)
        && manifestRows[family].finished_balanced_png.endsWith(
          `finished-balanced-${family}.png`
        )
      ),
    styled_face_matches_runtime_outside_allowed_eye_cheek_mouth:
      rows.every(row =>
        row.mismatchOutsideEyesAndMouth === 0
        && row.mismatchOutsideMouth
          <= (["warm", "bashful"].includes(row.family) ? 800 : 160)
      ),
    strict_1bpp_all_candidates:
      rows.every(row =>
        JSON.stringify(row.candidatePalette) === "[0,255]"
        && JSON.stringify(row.richPalette) === "[0,255]"
      ),
    current_mouth_semantics_protected:
      JSON.stringify(mouthContract.family_pairs) === JSON.stringify(expectedMouthPairs),
    current_richness_contract_protected:
      contract.preserved_richness.emotion_ornaments === true
      && contract.preserved_richness.functional_ornaments === true
      && contract.preserved_richness.natural_blink === true
      && contract.preserved_richness.pointer_follow === true
      && contract.preserved_richness.seeded_non_periodic_life === true,
    rich_family_frames_remain_distinct:
      rows.every(row => row.richDifference > 0),
    status_bar_constant_across_base_and_rich_frames:
      rows.every(row => row.statusStable),
    fixed_review_url_unchanged: contract.fixed_review_url === fixedUrl,
    hardware_contact_zero: contract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean)
    ? "MACHINE_READY"
    : "NO_GO";
  result = {
    schema: "companion.comp_req_772.legacy_line_style_browser.v2",
    requirement: "COMP-REQ-772",
    status,
    hardware_contact: 0,
    fixed_url: fixedUrl,
    fixed_url_http_status: response?.status() ?? 0,
    fixed_page_sha256: sha256(fixedPage),
    accepted_616_payload_sha256: manifest.source_sha256,
    comparison_mode_loads: comparisonModeLoads,
    proportion_metrics: proportionMetrics,
    runtime_mouth_metrics: runtimeMouthMetrics,
    ornament_motion: ornamentRows.map(row => ({
      family: row.family,
      positions: row.positions,
      samples: row.samples
    })),
    checks,
    browser_errors: browserErrors,
    families: rows.map(row => ({
      family: row.family,
      action: row.action,
      mouth_pose: row.mouthPose,
      mouth_states: row.mouthStates,
      mismatch_outside_mouth_px: row.mismatchOutsideMouth,
      mismatch_outside_eyes_and_mouth_px: row.mismatchOutsideEyesAndMouth,
      rich_difference_px: row.richDifference,
      status_stable: row.statusStable,
      current_ink_pixels:
        manifestRows[row.family].styled_metrics.source_ink_pixels,
      styled_ink_pixels:
        manifestRows[row.family].styled_metrics.styled_ink_pixels,
      legacy_616_ink_pixels:
        manifestRows[row.family].kept_face_ink_pixels
    })),
    screenshots: [
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/fixed-url-live-canvas.png",
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/previous-vs-legacy-line-style.png",
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/all-family-hold-accent-mouths.png",
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/all-family-open-blink-balance.png",
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/all-family-fixed-anchor-ornaments.png",
      ".cache/validation/comp-req-772-legacy-line-style-browser/screenshots/rich-ten-family-candidate.png"
    ]
  };
  fs.writeFileSync(
    path.join(artifactRoot, "MACHINE_READY.json"),
    `${JSON.stringify(result, null, 2)}\n`
  );
  console.log(JSON.stringify({
    status,
    checks,
    screenshots: result.screenshots
  }, null, 2));
  if (status !== "MACHINE_READY") process.exitCode = 1;
} finally {
  await browser.close();
}
