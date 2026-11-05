#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-627-special-state-refinement/index.html";
const pagePath = path.join(root, ...pageRel.split("/"));
const pageSource = fs.readFileSync(pagePath, "utf8");
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();

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

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) return response.writeHead(403).end();
  fs.readFile(target, (error, data) => {
    if (error) return response.writeHead(404).end();
    const type = target.endsWith(".html") ? "text/html; charset=utf-8" : "image/png";
    response.writeHead(200, { "content-type": type });
    response.end(data);
  });
});

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 680, height: 630 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const response = await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => window.__compReq599Ready === true && typeof window.__compReq625Contract === 'function', null, { timeout: 15000 });

  const audit = await page.evaluate(async () => {
    const contract = window.__compReq625Contract();
    const families = Object.keys(contract.affect_centers);
    const variantRows = Object.fromEntries(families.map(family => {
      const first = window.__compReq625Variant(family, 12, 7);
      const second = window.__compReq625Variant(family, 12, 7);
      const values = Array.from({ length: 64 }, (_, tick) => window.__compReq625Variant(family, tick, 0).variant);
      const sequence = window.__compReq625Sequence(family, 64);
      return [family, {
        deterministic: JSON.stringify(first) === JSON.stringify(second),
        unique: [...new Set(values)].sort((a, b) => a - b),
        sequencePhrases: [...new Set(sequence.filter(item => item.phase !== 'hold').map(item => item.phrase))].sort((a, b) => a - b),
        center: first.affect_center,
        ornament: first.ornament
      }];
    }));
    const canvas = document.querySelector('#face');
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const signature = () => {
      const pixels = ctx.getImageData(0, 0, 200, 200).data;
      let value = 2166136261;
      for (let index = 0; index < pixels.length; index += 4) {
        value ^= pixels[index] < 128 ? 1 : 0;
        value = Math.imul(value, 16777619);
      }
      return (value >>> 0).toString(16).padStart(8, '0');
    };
    const modeSignatures = {};
    for (const mode of Object.keys(contract.special_modes)) {
      modeSignatures[mode] = [];
      for (let frame = 0; frame < contract.special_modes[mode].frames.length; frame += 1) {
        window.__compReq625FreezeMode(mode, frame);
        modeSignatures[mode].push(signature());
      }
    }
    const sourceUrls = [];
    for (const [modeName, mode] of Object.entries(contract.special_modes)) {
      for (const source of mode.frames) {
        const root = mode.asset_root === 'system'
          ? '/docs/art/iterations/companion-pet-special-states-v1/review-pages/special-system-v1/'
          : mode.asset_root === 'speaker'
            ? '/docs/art/iterations/companion-pet-expression-v9-function-state-speaker-output-v1/candidate/wb55-browser-parity-attempt-01/'
            : mode.asset_root === 'special'
              ? '/docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/wb55-browser-parity-attempt-01/'
            : '/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/';
        sourceUrls.push(`${root}${source}`);
      }
    }
    for (const ornament of Object.values(contract.emotion_ornaments)) {
      for (const source of ornament.frames) {
        sourceUrls.push(`/docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/wb55-browser-parity-attempt-01/${source}`);
      }
    }
    sourceUrls.push('/docs/art/iterations/companion-pet-special-states-v1/review-pages/special-system-v1/01-voice-speaking.png');
    const sourceStatus = await Promise.all(sourceUrls.map(async url => {
      const result = await fetch(url);
      return { url, status: result.status };
    }));
    const audioSignatures = {};
    for (const mode of ['recording', 'speaker']) {
      window.__compReq625FreezeMode(mode, 1);
      audioSignatures[mode] = signature();
    }
    window.__compReq625SetMode('expression');
    window.__compReq599Restore();
    const before = window.__compReq599Snapshot().trace.length;
    const touch = window.__compReq625Touch(0.92, 0.16);
    await new Promise(resolve => setTimeout(resolve, 3000));
    const trace = window.__compReq599Snapshot().trace.slice(-16);
    const touchEvents = trace.filter(event => event.type === 'touch_transition_phase');
    const touchPhases = touchEvents.map(event => event.phase).slice(0, 5);
    const menuProgress = [];
    const longPressSnapshot = await window.__compReq625LongPress(1800);
    const longRestoreAt = [...longPressSnapshot.trace].reverse().find(event => event.type === 'restore')?.at || 0;
    menuProgress.push(...longPressSnapshot.trace.filter(event => event.at >= longRestoreAt && event.type === 'commit' && event.phase === 'menu_progress').map(event => event.progress));
    const menuEntered = longPressSnapshot.trace.some(event => event.at >= longRestoreAt && event.type === 'menu_enter' && event.source === 'long_press');
    const shortHoldSnapshot = await window.__compReq625ShortHold(700);
    const shortRestoreAt = [...shortHoldSnapshot.trace].reverse().find(event => event.type === 'restore')?.at || 0;
    const shortHoldProgress = shortHoldSnapshot.trace.filter(event => event.at >= shortRestoreAt && event.type === 'commit' && event.phase === 'menu_progress').map(event => event.progress);
    const shortHoldEntered = shortHoldSnapshot.trace.some(event => event.at >= shortRestoreAt && event.type === 'menu_enter' && event.source === 'long_press');
    return {
      contract,
      variantRows,
      modeSignatures,
      audioSignatures,
      sourceStatus,
      canvasCount: document.querySelectorAll('canvas').length,
      canvasSize: [canvas.width, canvas.height],
      touch,
      traceAdded: window.__compReq599Snapshot().trace.length - before,
      touchPhases,
      touchEvents,
      menuProgress,
      menuEntered,
      shortHoldProgress,
      shortHoldEntered,
      errors: []
    };
  });

  const allVariantsDeterministic = Object.values(audit.variantRows).every(row => row.deterministic);
  const allFamiliesVary = Object.values(audit.variantRows).every(row => row.unique.length >= 2);
  const allRuntimeSequencesVary = Object.values(audit.variantRows).every(row => row.sequencePhrases.length >= 2);
  const centersBounded = Object.values(audit.variantRows).every(row => row.center.every(value => Number.isInteger(value) && value >= -4 && value <= 4));
  const accessoryAssetsReachable = audit.sourceStatus.length > 0 && audit.sourceStatus.every(item => item.status === 200);
  const authoredMotion = ['charging', 'upgrading', 'menu', 'recording'].every(mode => new Set(audit.modeSignatures[mode]).size >= 2);
  const chargingSemantics = audit.contract.special_modes.charging.asset_root === 'art' && audit.contract.special_modes.charging.direction === 'energy_inbound' && audit.contract.special_modes.charging.icon === 'bottom_connector';
  const audioSemantics = audit.contract.special_modes.recording.direction === 'inbound' && audit.contract.special_modes.recording.icon === 'microphone' && audit.contract.special_modes.speaker.direction === 'outbound' && audit.contract.special_modes.speaker.icon === 'speaker_cone' && audit.audioSignatures.recording !== audit.audioSignatures.speaker;
  const menuProgresses = audit.menuProgress;
  const menuProgressMonotonic = menuProgresses.length >= 3 && menuProgresses.every((value, index) => index === 0 || value >= menuProgresses[index - 1]) && menuProgresses.at(-1) >= 0.9 && audit.menuEntered;
  const earlyReleaseCancels = audit.shortHoldEntered === false && audit.shortHoldProgress.length > 0 && audit.shortHoldProgress.at(-1) < 1;
  const sourceLeadTransition = audit.touchEvents.some(event => event.phase === 'orient' && event.source_lead === true);
  const touchOrder = JSON.stringify(audit.touchPhases.slice(0, 5)) === JSON.stringify(['orient', 'anticipate', 'accent', 'hold', 'settle']);
  const checks = {
    page_http_200: response?.status() === 200,
    browser_errors_zero: errors.length === 0,
    one_composed_200x200_face: audit.canvasCount === 1 && JSON.stringify(audit.canvasSize) === JSON.stringify([200, 200]),
    deterministic_seed_replay: allVariantsDeterministic,
    every_family_has_logical_variation: allFamiliesVary,
    runtime_sequence_uses_variations: allRuntimeSequencesVary,
    affect_centers_bounded: centersBounded,
    touch_targets_centered_transition: audit.touch.target === 'alert' && touchOrder && audit.traceAdded >= 5,
    transition_has_source_lead: sourceLeadTransition,
    special_modes_registered: Object.keys(audit.contract.special_modes).length === 5,
    emotion_ornaments_registered: Object.keys(audit.contract.emotion_ornaments).length >= 3,
    accessory_assets_http_200: accessoryAssetsReachable,
    special_mode_authored_motion: authoredMotion,
    charging_semantics: chargingSemantics,
    audio_direction_and_icon_semantics: audioSemantics,
    menu_long_press_progress: menuProgressMonotonic,
    menu_early_release_stays_out: earlyReleaseCancels,
    no_unbounded_randomness: !pageSource.includes('Math.random') && !pageSource.includes('requestAnimationFrame'),
    no_css_animation: !pageSource.includes('@keyframes') && !pageSource.includes('animation:'),
    one_source_canvas_contract: pageSource.includes('context.putImageData') && pageSource.includes('one_canvas: true')
  };
  const result = {
    schema: 'companion.comp_req_627.special_state_refinement.verification.v1',
    status: Object.values(checks).every(Boolean) ? 'PASS_OWNER_REVIEW_READY' : 'NO_GO',
    page_sha256: sha(pageSource),
    checks,
    evidence: {
      variant_rows: audit.variantRows,
      mode_signatures: audit.modeSignatures,
      audio_signatures: audit.audioSignatures,
      touch: { target: audit.touch.target, gravity: audit.touch.gravity, phases: audit.touchPhases },
      touch_events: audit.touchEvents,
      menu_progress: audit.menuProgress,
      menu_entered: audit.menuEntered,
      short_hold_progress: audit.shortHoldProgress,
      short_hold_entered: audit.shortHoldEntered,
      source_count: audit.sourceStatus.length,
      non_200_sources: audit.sourceStatus.filter(item => item.status !== 200)
    },
    browser_errors: errors
  };
  const outDir = path.dirname(pagePath);
  fs.writeFileSync(path.join(outDir, 'verification.json'), `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result, null, 2));
  if (result.status !== 'PASS_OWNER_REVIEW_READY') process.exitCode = 1;
} finally {
  await browser?.close();
  server.close();
}
