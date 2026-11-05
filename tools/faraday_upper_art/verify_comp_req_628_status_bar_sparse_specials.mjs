#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
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
    const lifeSequence = window.__compReq625Sequence('calm', 128);
    const audioEnvelopes = Object.fromEntries(['recording', 'speaker'].map(mode => [mode, {
      first: window.__compReq643AudioEnvelope(mode, 128, 0),
      replay: window.__compReq643AudioEnvelope(mode, 128, 0),
      next_entry: window.__compReq643AudioEnvelope(mode, 128, 1)
    }]));
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
    const binaryFrame = () => {
      const pixels = ctx.getImageData(0, 0, 200, 200).data;
      for (let index = 0; index < pixels.length; index += 4) {
        if (![0, 255].includes(pixels[index]) || pixels[index + 1] !== pixels[index]
            || pixels[index + 2] !== pixels[index] || pixels[index + 3] !== 255) return false;
      }
      return true;
    };
    const binarySamples = [];
    const modeSignatures = {};
    for (const mode of Object.keys(contract.special_modes)) {
      modeSignatures[mode] = [];
      for (let frame = 0; frame < contract.special_modes[mode].frames.length; frame += 1) {
        window.__compReq625FreezeMode(mode, frame);
        modeSignatures[mode].push(signature());
        binarySamples.push(binaryFrame());
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
        const root = ornament.asset_root
          || '/docs/art/iterations/companion-pet-expression-v9-function-state-decoration-rig-v1/candidate/wb55-browser-parity-attempt-01/';
        sourceUrls.push(`${root}${source}`);
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
    const audioDirectionSignatures = Object.fromEntries(['recording', 'speaker'].map(mode => [
      mode,
      [0, 1, 2, 3].map((level, index) => {
        window.__compReq643FreezeAudio(mode, level, index - 1, 24);
        return signature();
      })
    ]));
    const regionBits = (left, top, width, height) => {
      const pixels = ctx.getImageData(left, top, width, height).data;
      const bits = [];
      for (let index = 0; index < pixels.length; index += 4) bits.push(pixels[index] < 128 ? 1 : 0);
      return bits;
    };
    const countBlack = (left, top, width, height) => {
      const pixels = ctx.getImageData(left, top, width, height).data;
      let total = 0;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] < 128) total += 1;
      }
      return total;
    };
    const audioMotion = Object.fromEntries(['recording', 'speaker'].map(mode => {
      const bounds = contract.special_modes[mode].safe_bounds;
      return [mode, Array.from({ length: 48 }, (_, audioTick) => {
        const result = window.__compReq649FreezeAudioMotion(mode, audioTick, 24, 0);
        return {
          signature: signature(),
          ink: countBlack(bounds.x, bounds.y, bounds.width, bounds.height),
          level: result.envelope.level,
          phase: result.envelope.wave_phase,
          step: result.envelope.wave_step,
          dwell: result.envelope.wave_dwell,
          cycle: result.envelope.wave_cycle,
          drift: result.envelope.wave_drift
        };
      })];
    }));
    const bitDiff = (left, right) => left.reduce((total, bit, index) => total + (bit === right[index] ? 0 : 1), 0);
    const bitsSignature = bits => {
      let hash = 2166136261;
      for (const bit of bits) {
        hash ^= bit;
        hash = Math.imul(hash, 16777619);
      }
      return (hash >>> 0).toString(16).padStart(8, '0');
    };
    window.__compReq625SetMode('expression');
    document.querySelector('[data-family="calm"]').click();
    window.__compReq599Restore();
    const baseFaceCore = regionBits(45, 85, 110, 51);
    const baseStatusBar = regionBits(0, 0, 200, 14);
    const safeZoneBaseInk = Object.fromEntries(
      Object.entries(contract.special_modes).map(([mode, definition]) => {
        const { x, y, width, height } = definition.safe_bounds;
        return [mode, countBlack(x, y, width, height)];
      })
    );
    const overlayIntegrity = {};
    for (const mode of ['charging', 'upgrading', 'menu', 'recording', 'speaker']) {
      const lastFrame = contract.special_modes[mode].frames.length - 1;
      window.__compReq625FreezeMode(mode, lastFrame);
      overlayIntegrity[mode] = {
        face_core_diff: bitDiff(baseFaceCore, regionBits(45, 85, 110, 51)),
        status_bar_diff: bitDiff(baseStatusBar, regionBits(0, 0, 200, 14))
      };
    }
    const audioOverlayDynamics = {};
    for (const mode of ['recording', 'speaker']) {
      const bounds = contract.special_modes[mode].safe_bounds;
      const rows = [0, 4, 8, 12].map(lifeTick => {
        window.__compReq649FreezeAudioMotion(mode, 0, lifeTick, 0);
        return {
          life_tick: lifeTick,
          accessory: regionBits(bounds.x, bounds.y, bounds.width, bounds.height).join(''),
          face: regionBits(45, 85, 110, 51).join('')
        };
      });
      audioOverlayDynamics[mode] = {
        accessory_stable: new Set(rows.map(row => row.accessory)).size === 1,
        face_variants: new Set(rows.map(row => row.face)).size,
        rows
      };
    }
    const terminalHold = {};
    for (const mode of ['charging', 'upgrading', 'menu']) {
      const startAt = performance.now();
      window.__compReq625SetMode(mode);
      await new Promise(resolve => setTimeout(resolve, 3200));
      const bounds = contract.special_modes[mode].safe_bounds;
      const samples = [];
      for (let sample = 0; sample < 4; sample += 1) {
        samples.push({
          accessory: regionBits(bounds.x, bounds.y, bounds.width, bounds.height).join(''),
          face: regionBits(45, 85, 110, 51).join('')
        });
        if (sample < 3) await new Promise(resolve => setTimeout(resolve, 520));
      }
      const commits = window.__compReq599Snapshot().trace
        .filter(event => event.at >= startAt && event.type === 'commit' && event.mode === mode);
      terminalHold[mode] = {
        accessory_stable: new Set(samples.map(sample => sample.accessory)).size === 1,
        face_variants: new Set(samples.map(sample => sample.face)).size,
        commit_frames: commits.map(event => event.phrase),
        terminal_frame: commits.at(-1)?.phrase ?? null,
        last_frame: contract.special_modes[mode].frames.length - 1
      };
    }
    window.__compReq625SetMode('expression');
    document.querySelector('[data-family="calm"]').click();
    window.__compReq599Restore();
    const touch = window.__compReq625Touch(0.92, 0.16);
    await new Promise(resolve => setTimeout(resolve, 3000));
    const trace = window.__compReq599Snapshot().trace.slice(-16);
    const touchEvents = trace.filter(event => event.type === 'touch_transition_phase');
    const touchPhases = touchEvents.map(event => event.phase).slice(0, 5);
    const menuProgress = [];
    const longPressSnapshot = await window.__compReq625LongPress(contract.menu_hold.threshold_ms + 300);
    const longRestoreAt = [...longPressSnapshot.trace].reverse().find(event => event.type === 'restore')?.at || 0;
    menuProgress.push(...longPressSnapshot.trace.filter(event => event.at >= longRestoreAt && event.type === 'commit' && event.phase === 'menu_progress').map(event => event.progress));
    const menuEntered = longPressSnapshot.trace.some(event => event.at >= longRestoreAt && event.type === 'menu_enter' && event.source === 'long_press');
    const menuUiState = window.__compReq657MenuState();
    const menuUiSignature = signature();
    const menuUiTopBlack = ctx.getImageData(0, 0, 1, 1).data[0] < 128;
    const menuTerminalCells = [[86, 26], [102, 26], [86, 42], [102, 42]]
      .map(([x, y]) => ctx.getImageData(x + 3, y + 3, 1, 1).data[0] < 128);
    const shortHoldSnapshot = await window.__compReq625ShortHold(1600);
    const shortRestoreAt = [...shortHoldSnapshot.trace].reverse().find(event => event.type === 'restore')?.at || 0;
    const shortHoldProgress = shortHoldSnapshot.trace.filter(event => event.at >= shortRestoreAt && event.type === 'commit' && event.phase === 'menu_progress').map(event => event.progress);
    const shortHoldEntered = shortHoldSnapshot.trace.some(event => event.at >= shortRestoreAt && event.type === 'menu_enter' && event.source === 'long_press');
    const menuCells = [0.4, 0.51, 0.68, 0.84, 1].map(progress => window.__compReq625FreezeMenuProgress(progress).filled_cells);
    const menuDiscreteStages = [0.4, 0.51, 0.68, 0.84, 1].map(progress => {
      window.__compReq625FreezeMenuProgress(progress);
      return {
        progress,
        interior_black: [[88, 28], [104, 28], [88, 44], [104, 44]]
          .map(([x, y]) => countBlack(x, y, 8, 8))
      };
    });
    const upgradeRaw = [0, 0.25, 0.5, 0.75, 1].map(progress => {
      const result = window.__compReq628FreezeUpgrade(progress);
      binarySamples.push(binaryFrame());
      return { ...result, icon_black: countBlack(84, 18, 32, 36), bits: regionBits(84, 18, 32, 36) };
    });
    const upgradeOutline = upgradeRaw[0].bits;
    const upgradeProgress = upgradeRaw.map(({ bits, ...row }) => ({
      ...row,
      signature: bitsSignature(bits),
      outline_missing: upgradeOutline.reduce((total, bit, index) =>
        total + (bit === 1 && bits[index] !== 1 ? 1 : 0), 0)
    }));
    [0, 0.25, 0.5, 0.75, 1].forEach(progress => {
      window.__compReq625FreezeMenuProgress(progress);
      binarySamples.push(binaryFrame());
    });
    const chargingLayers = [0, 1, 2].map(frame => {
      window.__compReq625FreezeMode('charging', frame);
      const base = regionBits(72, 183, 56, 17);
      const energy = regionBits(72, 168, 56, 15);
      return {
        frame,
        base_signature: bitsSignature(base),
        base_ink: base.reduce((sum, bit) => sum + bit, 0),
        energy_signature: bitsSignature(energy),
        energy_ink: energy.reduce((sum, bit) => sum + bit, 0)
      };
    });
    const chargingFrame = window.__compReq625FreezeMode('charging', 2);
    const chargingPixels = ctx.getImageData(0, 0, 200, 200).data;
    let chargingMinY = 200;
    let chargingMaxY = -1;
    for (let y = 0; y < 200; y += 1) for (let x = 0; x < 200; x += 1) {
      if (chargingPixels[(y * 200 + x) * 4] < 128) { chargingMinY = Math.min(chargingMinY, y); chargingMaxY = Math.max(chargingMaxY, y); }
    }
    const expressionButtons = [...document.querySelectorAll('[data-family]')].map(button => ({ family: button.dataset.family, variant: Number(button.dataset.variant || 0), label: button.textContent.trim() }));
    document.querySelector('[data-family="calm"]').click();
    window.__compReq599Restore();
    await new Promise(resolve => setTimeout(resolve, 6500));
    const livingHoldSignatures = window.__compReq599Snapshot().trace
      .filter(event => event.type === 'commit' && event.family === 'calm' && event.phase === 'hold')
      .map(event => event.signature);
    const statusPixels = ctx.getImageData(0, 0, 200, 14).data;
    const regionHasWhite = (left, top, right, bottom) => {
      for (let y = top; y < bottom; y += 1) for (let x = left; x < right; x += 1) {
        if (statusPixels[(y * 200 + x) * 4] > 127) return true;
      }
      return false;
    };
    const statusBarPalette = {
      top_black: statusPixels[0] < 128,
      time_white: regionHasWhite(0, 1, 28, 11),
      bluetooth_white: regionHasWhite(142, 1, 154, 13),
      battery_white: regionHasWhite(166, 1, 190, 13)
    };
    return {
      contract,
      lifeSequence,
      audioEnvelopes,
      variantRows,
      modeSignatures,
      audioSignatures,
      audioDirectionSignatures,
      audioMotion,
      audioOverlayDynamics,
      overlayIntegrity,
      safeZoneBaseInk,
      terminalHold,
      sourceStatus,
      canvasCount: document.querySelectorAll('canvas').length,
      canvasSize: [canvas.width, canvas.height],
      touch,
      traceAdded: touchEvents.length,
      touchPhases,
      touchEvents,
      menuProgress,
      menuEntered,
      menuUiState,
      menuUiSignature,
      menuUiTopBlack,
      menuTerminalCells,
      shortHoldProgress,
      shortHoldEntered,
      menuCells,
      menuDiscreteStages,
      upgradeProgress,
      chargingLayers,
      chargingBounds: { minY: chargingMinY, maxY: chargingMaxY },
      expressionButtons,
      livingHoldSignatures,
      statusBarPalette,
      binarySamples,
      errors: []
    };
  });

  const allVariantsDeterministic = Object.values(audit.variantRows).every(row => row.deterministic);
  const allFamiliesVary = Object.values(audit.variantRows).every(row => row.unique.length >= 2);
  const allRuntimeSequencesVary = Object.values(audit.variantRows).every(row => row.sequencePhrases.length >= 2);
  const centersBounded = Object.values(audit.variantRows).every(row => row.center.every(value => Number.isInteger(value) && value >= -4 && value <= 4));
  const accessoryAssetsReachable = audit.sourceStatus.length > 0 && audit.sourceStatus.every(item => item.status === 200);
  const authoredMotion = ['charging', 'upgrading', 'menu'].every(mode => new Set(audit.modeSignatures[mode]).size >= 2);
  const chargingSemantics = audit.contract.special_modes.charging.asset_root === 'art' && audit.contract.special_modes.charging.direction === 'energy_inbound' && audit.contract.special_modes.charging.icon === 'bottom_connector';
  const audioSemantics = audit.contract.special_modes.recording.direction === 'inbound'
    && audit.contract.special_modes.recording.icon === 'chibi_microphone'
    && audit.contract.special_modes.speaker.direction === 'outbound'
    && audit.contract.special_modes.speaker.icon === 'chibi_speaker'
    && audit.audioSignatures.recording !== audit.audioSignatures.speaker;
  const overlaysPreserveFaceAndStatus = Object.values(audit.overlayIntegrity).every(item =>
    item.face_core_diff === 0 && item.status_bar_diff === 0);
  const safeBoundsValid = Object.values(audit.contract.special_modes).every(mode => {
    const bounds = mode.safe_bounds;
    return Number.isInteger(bounds?.x) && Number.isInteger(bounds?.y)
      && Number.isInteger(bounds?.width) && Number.isInteger(bounds?.height)
      && bounds.x >= 0 && bounds.y >= 14 && bounds.width > 0 && bounds.height > 0
      && bounds.x + bounds.width <= 200 && bounds.y + bounds.height <= 200;
  });
  const compositedOverlayModes = new Set(['charging', 'recording', 'speaker']);
  const ornamentSafeZonesClear = safeBoundsValid
    && Object.entries(audit.safeZoneBaseInk).every(([mode, blackPixels]) =>
      blackPixels === 0 || compositedOverlayModes.has(mode));
  const specialTerminalHold = Object.keys(audit.terminalHold).length === 3
    && Object.entries(audit.terminalHold).every(([mode, item]) =>
    item.accessory_stable === true
      && item.face_variants >= (mode === 'upgrading' ? 1 : 2)
    && item.terminal_frame === item.last_frame
    && item.commit_frames.length >= 3
    && item.commit_frames.every((frame, index, frames) => index === 0 || frame >= frames[index - 1]));
  const allStateOverlaysLive = Object.values(audit.audioOverlayDynamics).every(item =>
    item.accessory_stable === true && item.face_variants >= 2)
    && Object.entries(audit.terminalHold).every(([mode, item]) =>
      item.accessory_stable === true && item.face_variants >= (mode === 'upgrading' ? 1 : 2));
  const lifeActionEpisodes = [...new Map(
    audit.lifeSequence
      .filter(state => state.life_action !== 'rest')
      .map(state => [state.action_episode, state])
  ).values()];
  const quietRuns = [];
  let quietLength = 0;
  for (const state of audit.lifeSequence) {
    if (state.life_action === 'rest') quietLength += 1;
    else if (quietLength > 0) { quietRuns.push(quietLength); quietLength = 0; }
  }
  if (quietLength > 0) quietRuns.push(quietLength);
  const lifeSchedulerHasMemory = lifeActionEpisodes.length >= 8
    && new Set(lifeActionEpisodes.map(state => state.life_action)).size >= 4
    && lifeActionEpisodes.every((state, index, rows) =>
      index === 0 || state.life_action !== rows[index - 1].life_action)
    && lifeActionEpisodes.every(state => !state.recent_actions.slice(-2).includes(state.life_action));
  const completeQuietRuns = quietRuns.filter(length => length >= 3);
  const lifeQuietDwellVaries = completeQuietRuns.length >= 8
    && new Set(completeQuietRuns).size >= 3
    && completeQuietRuns.every(length => length <= 9);
  const audioEnvelopeProcedural = Object.values(audit.audioEnvelopes).every(group => {
    const episodes = group.first.filter((row, index, rows) =>
      index === 0 || row.envelope_episode !== rows[index - 1].envelope_episode);
    return JSON.stringify(group.first) === JSON.stringify(group.replay)
      && JSON.stringify(group.first) !== JSON.stringify(group.next_entry)
      && new Set(group.first.map(row => row.level)).size === 4
      && episodes.length >= 12
      && episodes.every((row, index, rows) =>
        index === 0 || (row.level !== rows[index - 1].level
          && (index < 2 || row.level !== rows[index - 2].level)))
      && episodes.every(row => row.dwell >= 2 && row.dwell <= 6);
  });
  const audioDirectionLevelInvariant = Object.values(audit.audioDirectionSignatures).every(signatures =>
    signatures.length === 4 && new Set(signatures).size === 1)
    && audit.contract.audio_envelope?.ornament_visual_mapping === 'direction_only_seeded_motion'
    && audit.contract.audio_envelope?.visible_intensity === false
    && audit.contract.audio_envelope?.wave_layer_count === 'continuous_packet'
    && audit.contract.audio_envelope?.wave_packet_lobes === 4
    && audit.contract.audio_envelope?.wave_geometry === 'shared_20px_two_cycle_triangle'
    && audit.contract.audio_envelope?.wave_energy_profile === 'fast_temporal_attack_stable_ink'
    && audit.contract.audio_envelope?.wave_motion_level_coupled === false
    && audit.contract.audio_envelope?.ornament_body_motion === false
    && audit.contract.audio_envelope?.speaker_body_style === 'imagegen_rounded_rear_short_throat_shallow_cone_1bit'
    && audit.contract.audio_envelope?.speaker_source === '.cache/validation/comp-req-628-status-bar/comp-req-689-generated-speaker-reference.png'
    && audit.contract.audio_envelope?.speaker_source_author === 'OpenAI image generation guided by Companion microphone reference'
    && audit.contract.audio_envelope?.speaker_source_license === 'project_generated'
    && audit.contract.audio_envelope?.speaker_source_sha256 === '6B6FE29C22B47635862CFF7A68C37E738B68ECC6807FAB1A68F07E08586E238A'
    && audit.contract.audio_envelope?.mirrored_audio_layout === 'wave20_gap2_body16/body16_gap2_wave20'
    && audit.contract.audio_envelope?.shared_audio_centerline_y === 168
    && audit.contract.audio_envelope?.speaker_semantic_reference === 'rounded_rear_short_throat_shallow_cone_plus_outward_wave';
  const audioWaveProceduralMotion = Object.values(audit.audioMotion).every(frames => {
    const phaseRuns = [];
    let runPhase = frames[0]?.phase;
    let runLength = 0;
    for (const frame of frames) {
      if (frame.phase !== runPhase) {
        phaseRuns.push({ phase: runPhase, length: runLength });
        runPhase = frame.phase;
        runLength = 0;
      }
      runLength += 1;
    }
    phaseRuns.push({ phase: runPhase, length: runLength });
    const completeRuns = phaseRuns.slice(1, -1);
    const inkValues = frames.map(frame => frame.ink);
    return new Set(frames.map(frame => frame.signature)).size >= 6
      && new Set(frames.map(frame => frame.phase)).size === 6
      && Math.max(...inkValues) - Math.min(...inkValues) <= 4
      && frames.every(frame => frame.phase >= 0 && frame.phase <= 5
        && frame.dwell === 1
        && frame.drift >= -1 && frame.drift <= 1)
      && frames.every((frame, index, all) => index === 0 || frame.phase === all[index - 1].phase
        || frame.phase === (all[index - 1].phase + 1) % 6)
      && completeRuns.length >= 6
      && completeRuns.every(run => run.length === 1);
  }) && audit.contract.audio_envelope?.wave_motion_seeded === true
    && audit.contract.audio_envelope?.audio_cadence_ms === 500
    && audit.contract.audio_envelope?.physical_driver_path === 'companion_epaper_panel_stm32wb_ssd1681_cached_mode2_diff/ssd1681_native_cached_mode2_movement_activation'
    && audit.contract.audio_envelope?.physical_update_control === '0xCF'
    && audit.contract.audio_envelope?.physical_measured_frame_count === 182
    && audit.contract.audio_envelope?.physical_measured_transaction_max_ms === 475
    && audit.contract.audio_envelope?.physical_measured_busy_max_ms === 447
    && audit.contract.audio_envelope?.physical_reference_expression_hold_ms === 750
    && audit.contract.audio_envelope?.physical_cadence_margin_ms === 25
    && audit.contract.audio_envelope?.visible_frame_coalescing === false
    && audit.contract.audio_envelope?.wave_motion_phase_count === 6
    && audit.contract.audio_envelope?.wave_spatial_speed_multiplier === 2
    && audit.contract.audio_envelope?.wave_cycle_duration_ms === 3000
    && audit.contract.audio_envelope?.wave_flow_cue === 'rightward_asymmetric_triangle_constant_energy'
    && audit.contract.audio_envelope?.wave_asymmetric_peak_cycle === 0.46
    && audit.contract.audio_envelope?.wave_motion_path === 'shared_rightward_triangle_packet_body_relative_flow'
    && audit.contract.audio_envelope?.wave_cycle_shape_variation === 'seeded_peak_spacing_micro_warp'
    && audit.contract.audio_envelope?.wave_raster_ink_tolerance_px === 4
    && audit.contract.audio_envelope?.recording_direction === 'inbound'
    && audit.contract.audio_envelope?.speaker_direction === 'outbound'
    && audit.contract.audio_envelope?.recording_screen_motion === 'right_toward_body'
    && audit.contract.audio_envelope?.speaker_screen_motion === 'right_away_from_body'
    && JSON.stringify(audit.contract.audio_envelope?.wave_motion_drift_px) === JSON.stringify([0, 0])
    && JSON.stringify(audit.contract.audio_envelope?.wave_motion_dwell_commits) === JSON.stringify([1, 1]);
  const menuProgresses = audit.menuProgress;
  const menuProgressMonotonic = menuProgresses.length >= 3 && menuProgresses.every((value, index) => index === 0 || value >= menuProgresses[index - 1]) && menuProgresses.at(-1) >= 0.9 && audit.menuEntered;
  const menuFillDeliberate = audit.contract.menu_hold?.threshold_ms === 3000
    && audit.contract.menu_hold?.recognition_lead_ms === 1000
    && audit.contract.menu_hold?.cell_step_ms === 500
    && audit.contract.menu_hold?.cell_fill === 'whole_cell'
    && menuProgresses.length >= 30;
  const earlyReleaseCancels = audit.shortHoldEntered === false && audit.shortHoldProgress.length > 0 && audit.shortHoldProgress.at(-1) < 1;
  const menuCellsMonotonic = JSON.stringify(audit.menuCells) === JSON.stringify([0, 1, 2, 3, 4]);
  const menuCellsFillIndependently = JSON.stringify(
    audit.menuDiscreteStages.map(stage => stage.interior_black)
  ) === JSON.stringify([
    [0, 0, 0, 0],
    [64, 0, 0, 0],
    [64, 64, 0, 0],
    [64, 64, 0, 64],
    [64, 64, 64, 64]
  ]);
  const gestureContract =
    audit.contract.gestures?.single_tap === 'immediate_emotion_touch'
    && audit.contract.gestures?.repeated_taps === 'all_commit_to_emotion_without_recording'
    && audit.contract.gestures?.double_tap === 'no_special_action'
    && audit.contract.gestures?.recording === 'drag_visible_microphone_horizontally_from_lower_left_then_release_to_exit'
    && audit.contract.gestures?.recording_gesture_default === 'edge_pull'
    && audit.contract.gestures?.recording_gesture_current === 'edge_pull'
    && JSON.stringify(audit.contract.gestures?.recording_gesture_options)
      === JSON.stringify(['edge_pull', 'double_tap'])
    && audit.contract.gestures?.recording_start_max_x === 0.24
    && audit.contract.gestures?.recording_start_min_y === 0.68
    && audit.contract.gestures?.recording_trigger_dx === 0.18
    && audit.contract.gestures?.recording_max_dy === 0.12
    && audit.contract.gestures?.recording_min_hold_ms === 120
    && audit.contract.gestures?.recording_preview === 'quantized_horizontal_same_microphone_geometry'
    && audit.contract.gestures?.recording_visible_stages === 4
    && audit.contract.gestures?.recording_visible_cadence_ms === 500
    && audit.contract.gestures?.long_press === 'menu'
    && audit.contract.gestures?.long_press_ms === 3000
    && audit.contract.gestures?.mutually_exclusive === true;
  const menuVisualArbitrationContract =
    audit.contract.menu_hold?.preview_delay_ms === 1000
    && JSON.stringify(audit.contract.menu_hold?.fill_order)
      === JSON.stringify(['upper_left', 'upper_right', 'lower_right', 'lower_left']);
  const menuTerminalSurfaceEntered =
    audit.contract.menu_hold?.terminal_surface === 'extensible_vertical_root_menu_ui'
    && audit.contract.menu_hold?.entry_ack_ms === 180
    && audit.menuUiState?.active === true
    && audit.menuUiState?.screen === 'home'
    && audit.menuUiTopBlack === true;
  const menuVerticalRootExtensible =
    audit.contract.menu_hold?.root_list?.layout === 'extensible_vertical_list'
    && audit.contract.menu_hold?.root_list?.partial_next_row === true
    && audit.contract.menu_hold?.root_list?.pointer_vertical_drag === 'bounded_scroll_without_activation'
    && Array.isArray(audit.contract.menu_hold?.root_list?.item_model)
    && audit.contract.menu_hold.root_list.item_model.length === 4;
  const upgradeMonotonic = audit.upgradeProgress.every((item, index, all) => index === 0 || item.progress >= all[index - 1].progress) && audit.upgradeProgress.at(-1)?.complete === true;
  const upgradePixelsIncrease = audit.upgradeProgress.every((item, index, all) =>
    index === 0 || item.icon_black > all[index - 1].icon_black);
  const upgradeGeneratedBodyFixed = audit.upgradeProgress.every(item => item.outline_missing === 0)
    && audit.contract.upgrade_art?.style === 'standard_pixel_download'
    && audit.contract.upgrade_art?.fixed_outer_body === true
    && audit.contract.upgrade_art?.fill_direction === 'top_to_bottom_inside_arrow'
    && JSON.stringify(audit.contract.upgrade_art?.progress_samples) === JSON.stringify([0, 0.25, 0.5, 0.75, 1])
    && JSON.stringify(audit.contract.upgrade_art?.native_bounds) === JSON.stringify([88, 21, 24, 30])
    && audit.contract.upgrade_art?.optical_stroke_px === 2
    && audit.contract.upgrade_art?.silhouette === 'down_arrow_to_short_receiver'
    && audit.contract.upgrade_art?.progress_treatment === 'monotonic_arrow_black_fill'
    && audit.contract.upgrade_art?.circular_refresh === false;
  const chargingBaseFixedEnergyMoves = new Set(audit.chargingLayers.map(row => row.base_signature)).size === 1
    && new Set(audit.chargingLayers.map(row => row.energy_signature)).size >= 2
    && audit.contract.charging_layers?.base_source_frame === 0
    && audit.contract.charging_layers?.base_motion === false
    && audit.contract.charging_layers?.energy_motion === true
    && JSON.stringify(audit.contract.charging_layers?.base_destination) === JSON.stringify([72, 183])
    && JSON.stringify(audit.contract.charging_layers?.energy_destination) === JSON.stringify([72, 168]);
  const chargingBottomAttached = audit.chargingBounds.maxY >= 190;
  const statusBarBounded = audit.contract.status_bar.x >= 0 && audit.contract.status_bar.y >= 0 && audit.contract.status_bar.width > 0 && audit.contract.status_bar.height > 0 && audit.contract.status_bar.x + audit.contract.status_bar.width <= 200 && audit.contract.status_bar.y + audit.contract.status_bar.height <= 200;
  const statusBarPhonePalette = audit.statusBarPalette.top_black && audit.statusBarPalette.time_white && audit.statusBarPalette.bluetooth_white && audit.statusBarPalette.battery_white;
  const oneBitOutput = audit.binarySamples.length >= 15 && audit.binarySamples.every(Boolean);
  const sparseBlink = audit.contract.blink_interval_ms.every(value => value >= 8000);
  const finiteSpecialSequence = audit.contract.special_sequence_policy === 'event_progress_or_procedural_sparse_envelope';
  const extraExpressions = audit.expressionButtons.filter(item => item.variant > 0).length >= 3;
  const livingHoldVaries = new Set(audit.livingHoldSignatures).size >= 3;
  const livingMotionAnchor = audit.contract.living_motion?.anchor === 'authored_face_fixed'
    && audit.contract.living_motion?.max_local_offset_px <= 2
    && audit.contract.living_motion?.outer_eye_motion === false;
  const sourceLeadTransition = audit.touchEvents.some(event => event.phase === 'orient' && event.source_lead === true);
  const touchOrder = JSON.stringify(audit.touchPhases.slice(0, 5)) === JSON.stringify(['orient', 'anticipate', 'accent', 'follow', 'settle']);
  const checks = {
    page_http_200: response?.status() === 200,
    browser_errors_zero: errors.length === 0,
    one_composed_200x200_face: audit.canvasCount === 1 && JSON.stringify(audit.canvasSize) === JSON.stringify([200, 200]),
    deterministic_seed_replay: allVariantsDeterministic,
    every_family_has_logical_variation: allFamiliesVary,
    runtime_sequence_uses_variations: allRuntimeSequencesVary,
    affect_centers_bounded: centersBounded,
    touch_targets_centered_transition: audit.touch.target === 'curious' && touchOrder && audit.touchEvents.length >= 5,
    transition_has_source_lead: sourceLeadTransition,
    special_modes_registered: Object.keys(audit.contract.special_modes).length === 5,
    emotion_ornaments_registered: Object.keys(audit.contract.emotion_ornaments).length >= 3,
    accessory_assets_http_200: accessoryAssetsReachable,
    special_mode_authored_motion: authoredMotion,
    charging_semantics: chargingSemantics,
    audio_direction_and_icon_semantics: audioSemantics,
    special_overlays_preserve_face_and_status: overlaysPreserveFaceAndStatus,
    ornament_safe_zones_clear: ornamentSafeZonesClear,
    special_sequences_hold_terminal_without_loop: specialTerminalHold,
    all_special_states_overlay_evolving_face: allStateOverlaysLive,
    procedural_life_action_memory_and_cooldown: lifeSchedulerHasMemory,
    procedural_life_variable_quiet_dwell: lifeQuietDwellVaries,
    procedural_audio_envelope_no_short_loop: audioEnvelopeProcedural,
    audio_direction_marker_invariant_across_activity: audioDirectionLevelInvariant,
    audio_direction_wave_procedural_motion: audioWaveProceduralMotion,
    menu_long_press_progress: menuProgressMonotonic && menuCellsMonotonic && menuFillDeliberate,
    menu_cells_fill_independently: menuCellsFillIndependently,
    gesture_contract_single_double_long_press: gestureContract,
    menu_preview_waits_for_gesture_arbitration: menuVisualArbitrationContract,
    menu_terminal_surface_entered: menuTerminalSurfaceEntered,
    menu_vertical_root_is_extensible: menuVerticalRootExtensible,
    upgrade_progress_monotonic_and_complete: upgradeMonotonic && upgradePixelsIncrease,
    upgrade_generated_outer_body_fixed: upgradeGeneratedBodyFixed,
    charging_base_station_fixed_energy_only_moves: chargingBaseFixedEnergyMoves,
    charging_bottom_attached: chargingBottomAttached,
    status_bar_bounded: statusBarBounded,
    status_bar_phone_palette: statusBarPhonePalette,
    one_bit_output: oneBitOutput,
    native_200x200_shared_framebuffer: audit.contract.framebuffer?.width === 200
      && audit.contract.framebuffer?.height === 200
      && audit.contract.framebuffer?.bits_per_pixel === 1
      && audit.contract.framebuffer?.source === 'canvas_image_data'
      && audit.contract.framebuffer?.device_sink === 'same_packed_pixels',
    sparse_blink_interval: sparseBlink,
    finite_special_sequence: finiteSpecialSequence,
    extra_expression_variants: extraExpressions,
    seeded_living_hold_variation: livingHoldVaries && audit.contract.living_motion?.seeded === true,
    living_motion_anchor_stable: livingMotionAnchor,
    menu_early_release_stays_out: earlyReleaseCancels,
    no_unbounded_randomness: !pageSource.includes('Math.random') && !pageSource.includes('requestAnimationFrame'),
    no_css_animation: !pageSource.includes('@keyframes') && !pageSource.includes('animation:'),
    one_source_canvas_contract: pageSource.includes('context.putImageData') && pageSource.includes('one_canvas: true')
  };
  const result = {
    schema: 'companion.comp_req_629.expression_expansion_status_bar.verification.v1',
    status: Object.values(checks).every(Boolean) ? 'PASS_OWNER_REVIEW_READY' : 'NO_GO',
    page_sha256: sha(pageSource),
    checks,
    evidence: {
      variant_rows: audit.variantRows,
      mode_signatures: audit.modeSignatures,
      audio_signatures: audit.audioSignatures,
      audio_direction_signatures: audit.audioDirectionSignatures,
      audio_motion: audit.audioMotion,
      audio_overlay_dynamics: audit.audioOverlayDynamics,
      overlay_integrity: audit.overlayIntegrity,
      safe_zone_base_ink: audit.safeZoneBaseInk,
      terminal_hold: audit.terminalHold,
      life_sequence: audit.lifeSequence,
      audio_envelopes: audit.audioEnvelopes,
      touch: { target: audit.touch.target, gravity: audit.touch.gravity, phases: audit.touchPhases },
      touch_events: audit.touchEvents,
      menu_progress: audit.menuProgress,
      menu_entered: audit.menuEntered,
      menu_terminal_cells: audit.menuTerminalCells,
      short_hold_progress: audit.shortHoldProgress,
      short_hold_entered: audit.shortHoldEntered,
      menu_cells: audit.menuCells,
      menu_partial_fill: audit.menuPartialFill,
      upgrade_progress: audit.upgradeProgress,
      charging_layers: audit.chargingLayers,
      charging_bounds: audit.chargingBounds,
      status_bar_palette: audit.statusBarPalette,
      expression_buttons: audit.expressionButtons,
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
