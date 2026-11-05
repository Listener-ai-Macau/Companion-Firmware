#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
const artifactRoot = path.join(root, ".cache/validation/comp-req-727-generated-emotion-rig");
const manifest = JSON.parse(fs.readFileSync(path.join(artifactRoot, "manifest.json"), "utf8"));
fs.mkdirSync(path.join(artifactRoot, "screenshots"), { recursive: true });

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
    const type = target.endsWith(".html") ? "text/html; charset=utf-8"
      : target.endsWith(".png") ? "image/png"
        : target.endsWith(".json") ? "application/json"
          : "application/octet-stream";
    response.writeHead(200, { "content-type": type, "cache-control": "no-store" });
    response.end(data);
  });
});

const subset = (left, right) => {
  const rightSet = new Set(right);
  return left.every(value => rightSet.has(value));
};

const hasExactPeriod = (values, maxPeriod) => {
  for (let period = 1; period <= maxPeriod; period += 1) {
    if (values.every((value, index) => index < period || value === values[index - period])) {
      return true;
    }
  }
  return false;
};

const boundsFromIndices = indices => {
  if (!indices.length) return null;
  const xs = indices.map(value => value % 200);
  const ys = indices.map(value => Math.floor(value / 200));
  return {
    left: Math.min(...xs),
    top: Math.min(...ys),
    right: Math.max(...xs) + 1,
    bottom: Math.max(...ys) + 1
  };
};

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 720, height: 760 }, deviceScaleFactor: 1 });
  const browserErrors = [];
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  const url = `http://127.0.0.1:${server.address().port}/${pageRel}?comp_req_728=${Date.now()}`;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    window.__compReq599Ready === true
    && typeof window.__compReq728FreezeOrnament === "function"
  );
  await page.evaluate(() => window.__compReq714SetScheduler(false));
  const contract = await page.evaluate(() => window.__compReq728Contract());
  const ornamentSequences = await page.evaluate(families =>
    Object.fromEntries(families.map(family => [
      family,
      window.__compReq731OrnamentSequence(family, 74)
    ])), contract.families);
  const ornamentMotionSequences = await page.evaluate(families =>
    Object.fromEntries(families.map(family => [
      family,
      window.__compReq732OrnamentSequence(family, 512)
    ])), contract.families);
  const familyRows = [];
  const faceCards = [];
  const stageCards = [];

  for (const family of contract.families) {
    const stages = [];
    for (let stage = 0; stage <= 3; stage += 1) {
      const sample = await page.evaluate(async ({ family, stage }) => {
        const result = window.__compReq728FreezeOrnament(family, stage);
        const canvas = document.querySelector("#face");
        const pixels = canvas.getContext("2d", { willReadFrequently: true })
          .getImageData(0, 0, 200, 200).data;
        const bits = [];
        const values = new Set();
        for (let y = 0; y < 200; y += 1) {
          for (let x = 0; x < 200; x += 1) {
            const offset = (y * 200 + x) * 4;
            values.add(pixels[offset]);
            bits.push(pixels[offset] < 128 ? "1" : "0");
          }
        }
        const source = new Image();
        source.src = `/.cache/validation/comp-req-727-generated-emotion-rig/${result.source}`;
        await source.decode();
        const scratch = document.createElement("canvas");
        scratch.width = scratch.height = 200;
        const scratchContext = scratch.getContext("2d", { willReadFrequently: true });
        scratchContext.drawImage(source, 0, 0);
        const sourcePixels = scratchContext.getImageData(0, 0, 200, 200).data;
        const sourceInk = [];
        for (let y = 14; y < 200; y += 1) {
          for (let x = 0; x < 200; x += 1) {
            if (sourcePixels[(y * 200 + x) * 4 + 3] > 0) sourceInk.push(y * 200 + x);
          }
        }
        return {
          result,
          bits: bits.join(""),
          sourceInk,
          palette: [...values].sort((a, b) => a - b),
          dataUrl: canvas.toDataURL("image/png")
        };
      }, { family, stage });
      stages.push(sample);
      stageCards.push({ family, stage, dataUrl: sample.dataUrl });
    }

    const exactFace = await page.evaluate(async family => {
      window.__compReq728FreezeOrnament(family, 0);
      const actual = document.querySelector("#face").getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      const source = new Image();
      source.src = `/.cache/validation/comp-req-727-generated-emotion-rig/faces/${family}.png`;
      await source.decode();
      const scratch = document.createElement("canvas");
      scratch.width = scratch.height = 200;
      const scratchContext = scratch.getContext("2d", { willReadFrequently: true });
      scratchContext.drawImage(source, 0, 0);
      const expected = scratchContext.getImageData(0, 0, 200, 200).data;
      let mismatch = 0;
      for (let y = 14; y < 200; y += 1) {
        for (let x = 0; x < 200; x += 1) {
          const at = (y * 200 + x) * 4;
          if ((actual[at] < 128) !== (expected[at] < 128)) mismatch += 1;
        }
      }
      return mismatch;
    }, family);

    const added = stages.map((stage, index) => {
      if (index === 0) return [];
      const result = [];
      for (let at = 14 * 200; at < 200 * 200; at += 1) {
        if (stages[0].bits[at] === "0" && stage.bits[at] === "1") result.push(at);
      }
      return result;
    });
    const stageInks = manifest.ornaments[family].stages.map(stage => stage.ink);
    const stageBounds = stages.map(stage => boundsFromIndices(stage.sourceInk));
    familyRows.push({
      family,
      exact_face_mismatch_px: exactFace,
      stage_ink: stageInks,
      added_ink: added.map(value => value.length),
      coherent_pivot_scale_entry: [1, 2].every(index =>
        stageBounds[index]
        && stageBounds[index + 1]
        && stageBounds[index].right - stageBounds[index].left
          <= stageBounds[index + 1].right - stageBounds[index + 1].left
        && stageBounds[index].bottom - stageBounds[index].top
          <= stageBounds[index + 1].bottom - stageBounds[index + 1].top
        && Math.abs(
          (stageBounds[index].left + stageBounds[index].right) / 2
          - (stageBounds[3].left + stageBounds[3].right) / 2
        ) <= 1.5
        && Math.abs(stageBounds[index].bottom - stageBounds[3].bottom) <= 2),
      exact_overlay_pixels: [1, 2, 3].every(stage =>
        added[stage].length === stages[stage].sourceInk.length
        && subset(added[stage], stages[stage].sourceInk)
        && subset(stages[stage].sourceInk, added[stage])
      ),
      binary: stages.every(stage => stage.palette.every(value => value === 0 || value === 255)),
      anchor: manifest.ornaments[family].anchor,
      bounds: manifest.ornaments[family].bounds,
      stage_bounds: stageBounds
    });
    faceCards.push({ family, dataUrl: stages[3].dataUrl });
  }

  await page.evaluate(() => {
    window.__compReq714ClearTrace();
    window.__compReq599Freeze("calm", 0, "hold");
    window.__compReq625Touch(0.86, 0.16);
  });
  const transitionCards = [];
  const transitionPhasesSeen = new Set();
  for (let index = 0; index < 40; index += 1) {
    const card = await page.evaluate(() => {
      const result = window.__compReq728StepTransition();
      const canvas = document.querySelector("#face");
      const commits = result.trace.filter(item => item.type === "commit" && item.transition_target);
      return {
        phase: commits.at(-1)?.phase || "unknown",
        dataUrl: canvas.toDataURL("image/png"),
        active: result.active
      };
    });
    if (!transitionPhasesSeen.has(card.phase)) {
      transitionPhasesSeen.add(card.phase);
      transitionCards.push(card);
    }
    if (!card.active) break;
  }
  const transitionTrace = await page.evaluate(() => window.__compReq599Snapshot().trace);
  const transitionCommits = transitionTrace
    .filter(item => item.type === "commit" && item.transition_target);

  const functionalOverlayPriority = await page.evaluate(async () => {
    const rows = {};
    for (const mode of ["charging", "upgrading", "menu", "recording", "speaker"]) {
      document.querySelector('[data-family="focused"]').click();
      window.__compReq714FreezeLifeAction("focused", "soften", "follow", 0, 0, true);
      document.querySelector(`[data-mode="${mode}"]`).click();
      await new Promise(resolve => setTimeout(resolve, 40));
      rows[mode] = window.__compReq733FunctionalOverlayAudit(mode);
    }
    return rows;
  });
  const faceMotionAudit = await page.evaluate(() => {
    const choreography = window.__compReq728Contract().generated_component_bounds.warm;
    const actions = ["notice_left", "notice_right", "small_breath", "listen_up", "soften"];
    const hashBoxes = (data, boxes) => {
      let hash = 2166136261;
      boxes.forEach(([x, y, width, height]) => {
        for (let row = y; row < y + height; row += 1) {
          for (let column = x; column < x + width; column += 1) {
            hash ^= data[(row * 200 + column) * 4] < 128 ? 1 : 0;
            hash = Math.imul(hash, 16777619);
          }
        }
      });
      return (hash >>> 0).toString(16).padStart(8, "0");
    };
    return actions.map((action, index) => {
      const pose = window.__compReq714FreezeLifeAction(
        "warm",
        action,
        "follow",
        0,
        action === "notice_left" ? -1 : action === "notice_right" ? 1 : 0,
        true
      );
      const data = document.querySelector("#face").getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      return {
        action,
        mouth: hashBoxes(data, choreography.mouth),
        mouth_pose: pose.mouth_pose,
        brows: hashBoxes(data, choreography.brows),
        eyes: hashBoxes(data, choreography.eyes),
        motion: pose.face_motion,
        index
      };
    });
  });
  const emotionSystemAudit = await page.evaluate(() => {
    window.__compReq599Restore();
    window.__compReq714ResetInteraction();
    const run = (event, x, y, meta = {}) =>
      window.__compReq739EmotionEvent(event, x, y, meta);
    const decisions = [];
    for (let index = 0; index < 8; index += 1) {
      decisions.push(run("single_tap", 0.5, 0.5));
    }
    for (let index = 0; index < 5; index += 1) {
      decisions.push(run("single_tap", 0.5, 0.18));
    }
    [[0.15, 0.18], [0.85, 0.18], [0.15, 0.8], [0.85, 0.8]]
      .forEach(([x, y]) => decisions.push(run("single_tap", x, y)));
    decisions.push(run("slow_stroke", 0.55, 0.55));
    decisions.push(run("quick_sweep", 0.8, 0.5));
    decisions.push(run("repeated_tease", 0.5, 0.5));
    window.__compReq599Restore();
    window.__compReq714ResetInteraction();
    const idle = run("idle", 0.5, 0.5, { idleSeconds: 60 });
    return {
      targets: decisions.map(item => item.target),
      unique_targets: [...new Set(decisions.map(item => item.target))],
      gestures: decisions.slice(-3).map(item => item.target),
      idle_target: idle.target,
      traceable: decisions.every(item =>
        item.decision?.variables
        && Object.keys(item.decision?.scores || {}).length === 10),
      contract: window.__compReq739EmotionContract()
    };
  });
  const calmMouthGuard = await page.evaluate(() => {
    const rest = window.__compReq643FreezeLife("calm", 0, 0);
    const actions = ["notice_left", "notice_right", "small_breath", "listen_up", "soften"]
      .map(action => window.__compReq714FreezeLifeAction(
        "calm",
        action,
        "follow",
        0,
        action === "notice_left" ? -1 : action === "notice_right" ? 1 : 0,
        true
      ));
    return [rest, ...actions].map(item => item.face_motion?.mouth || null);
  });
  const protectedFaceActions = [];
  for (const family of ["calm", "alert"]) {
    for (const action of ["rest", "notice_left", "notice_right", "small_breath", "listen_up", "soften"]) {
      protectedFaceActions.push(await page.evaluate(({ family, action }) => {
        if (action === "rest") {
          window.__compReq643FreezeLife(family, 0, 0);
        } else {
          window.__compReq714FreezeLifeAction(
            family,
            action,
            "follow",
            0,
            action === "notice_left" ? -1 : action === "notice_right" ? 1 : 0,
            true
          );
        }
        return {
          family,
          action,
          eye_audit: window.__compReq740EyeHighlightAudit(),
          dataUrl: document.querySelector("#face").toDataURL("image/png")
        };
      }, { family, action }));
    }
  }

  const review = await browser.newPage({ viewport: { width: 1050, height: 760 }, deviceScaleFactor: 1 });
  const cardHtml = faceCards.map(card =>
    `<figure><img src="${card.dataUrl}"><figcaption>${card.family}</figcaption></figure>`
  ).join("");
  await review.setContent(`<style>
    body{margin:20px;background:#202426;color:#fff;font:16px sans-serif}
    h1{font-size:20px;margin:0 0 14px}.grid{display:grid;grid-template-columns:repeat(5,200px);gap:10px}
    figure{margin:0}img{display:block;width:200px;height:200px;image-rendering:pixelated;background:#fff}
    figcaption{text-align:center;padding:5px 0 8px}
  </style><h1>COMP-REQ-727/728 生成表情与动态饰件总览</h1><div class="grid">${cardHtml}</div>`);
  await review.screenshot({
    path: path.join(artifactRoot, "screenshots", "ten-emotions-with-ornaments.png"),
    fullPage: true
  });

  const stageReview = await browser.newPage({ viewport: { width: 860, height: 1120 }, deviceScaleFactor: 1 });
  const stageHtml = stageCards.map(card =>
    `<figure><img src="${card.dataUrl}"><figcaption>${card.family} · ${card.stage}</figcaption></figure>`
  ).join("");
  await stageReview.setContent(`<style>
    body{margin:16px;background:#202426;color:#fff;font:12px sans-serif}
    h1{font-size:18px;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(4,200px);gap:8px}
    figure{margin:0}img{display:block;width:200px;height:200px;image-rendering:pixelated;background:#fff}
    figcaption{text-align:center;padding:3px 0}
  </style><h1>饰件固定锚点：0 → 1 → 2 → 3</h1><div class="grid">${stageHtml}</div>`);
  await stageReview.screenshot({
    path: path.join(artifactRoot, "screenshots", "ornament-four-stage-atlas.png"),
    fullPage: true
  });

  const transitionReview = await browser.newPage({ viewport: { width: 1050, height: 280 }, deviceScaleFactor: 1 });
  const transitionHtml = transitionCards.map(card =>
    `<figure><img src="${card.dataUrl}"><figcaption>${card.phase}</figcaption></figure>`
  ).join("");
  await transitionReview.setContent(`<style>
    body{margin:16px;background:#202426;color:#fff;font:13px sans-serif}
    h1{font-size:18px;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(5,200px);gap:8px}
    figure{margin:0}img{display:block;width:200px;height:200px;image-rendering:pixelated;background:#fff}
    figcaption{text-align:center;padding:4px 0}
  </style><h1>触摸因果过渡：注视 → 预备 → 强调 → 跟随 → 稳定</h1><div class="grid">${transitionHtml}</div>`);
  await transitionReview.screenshot({
    path: path.join(artifactRoot, "screenshots", "touch-transition-five-phase.png"),
    fullPage: true
  });

  const protectedReview = await browser.newPage({ viewport: { width: 1270, height: 480 }, deviceScaleFactor: 1 });
  const protectedHtml = protectedFaceActions.map(card =>
    `<figure><img src="${card.dataUrl}"><figcaption>${card.family} · ${card.action}</figcaption></figure>`
  ).join("");
  await protectedReview.setContent(`<style>
    body{margin:16px;background:#202426;color:#fff;font:12px sans-serif}
    h1{font-size:18px;margin:0 0 12px}.grid{display:grid;grid-template-columns:repeat(6,200px);gap:8px}
    figure{margin:0}img{display:block;width:200px;height:200px;image-rendering:pixelated;background:#fff}
    figcaption{text-align:center;padding:3px 0}
  </style><h1>COMP-REQ-740 平静嘴型与警觉眼体保护</h1><div class="grid">${protectedHtml}</div>`);
  await protectedReview.screenshot({
    path: path.join(artifactRoot, "screenshots", "protected-calm-alert-actions.png"),
    fullPage: true
  });

  const expectedPhases = ["orient", "anticipate", "accent", "follow", "settle"];
  const transitionPhaseOrder = transitionCommits
    .map(item => item.phase)
    .filter((phase, index, all) => index === 0 || phase !== all[index - 1]);
  const transitionCommitFor = phase =>
    transitionCommits.find(item => item.phase === phase);
  const faceBounds = Object.values(manifest.faces).map(face => face.bounds);
  const checks = {
    browser_errors_zero: browserErrors.length === 0,
    generated_sources_complete: contract.families.length === 10
      && Object.values(contract.ornament_sources).every(frames => frames.length === 4),
    exact_generated_faces: familyRows.every(row => row.exact_face_mismatch_px === 0),
    strict_1bit_canvas: familyRows.every(row => row.binary),
    ornament_ink_strictly_progressive: familyRows.every(row =>
      row.stage_ink.every((value, index, values) => index === 0 || value > values[index - 1])
    ),
    ornament_coherent_pivot_scale_entry:
      familyRows.every(row => row.coherent_pivot_scale_entry),
    ornament_overlay_exact: familyRows.every(row => row.exact_overlay_pixels),
    ornament_fixed_anchor: contract.fixed_anchor === true
      && contract.body_motion === "seeded_pivot_micro_choreography"
      && contract.max_pivot_angle_deg === 2.2,
    ornament_does_not_replace_face: contract.replaces_face === false,
    in_context_face_composition:
      manifest.composition.method === "same-cell split plus centred whole-composition scale; no legacy-face scaling"
      && manifest.composition.scale === 1.18
      && manifest.composition.threshold === 96
      && faceBounds.every(([left, top, right, bottom]) =>
        right - left <= 128 && bottom - top <= 86),
    canonical_faces_trace_to_matching_5x2_cells:
      manifest.checks.canonical_faces_from_5x2_cells === true
      && Object.entries(manifest.faces).slice(0, 10)
        .every(([family, face], index) =>
          face.source_cell === index && face.source_family === family),
    same_cell_reconstruction_exact:
      manifest.checks.same_cell_reconstruction_exact === true
      && Object.values(manifest.same_cell_reconstruction_differences)
        .every(value => value === 0),
    face_center_locked: faceBounds.every(([left, top, right, bottom]) =>
      Math.abs((left + right) / 2 - 100) <= 2
      && Math.abs((top + bottom) / 2 - 119) <= 2),
    face_ornament_intersections_zero:
      Object.values(manifest.face_ornament_intersections).every(value => value === 0),
    ornament_persists_without_timed_reentry:
      contract.persistent_until_family_or_special_state_changes === true
      && contract.timed_withdrawal === false
      && Object.values(ornamentSequences).every(sequence =>
        sequence.length === 74 && sequence.every(stage => stage === 3)),
    ornament_seeded_nonperiodic_micro_choreography:
      Object.values(ornamentMotionSequences).every(sequence => {
        const poses = sequence.map(item => item.motion.pose);
        const durations = sequence.map(item => item.motion.duration);
        return sequence.every(item =>
          item.stage === 3
          && item.motion.fixed_pivot === true
          && Math.abs(item.motion.angle_deg) <= 2.2)
          && new Set(poses).size >= 4
          && new Set(durations).size >= 5
          && !hasExactPeriod(poses, 32);
      }),
    functional_and_emotion_ornaments_coexist:
      Object.values(functionalOverlayPriority).every(row =>
        row.emotion_base_ink > 0
        && row.emotion_difference_outside_overlap === 0
        && row.functional_ink > 0),
    mouth_brows_and_eyes_have_living_choreography:
      new Set(faceMotionAudit.map(row => row.mouth)).size === 2
      && faceMotionAudit.find(row => row.action === "soften")?.mouth_pose
        === "recovered_wide_smile"
      && faceMotionAudit
        .filter(row => row.action !== "soften")
        .every(row => row.mouth_pose === "recovered_gentle_smile")
      && new Set(faceMotionAudit.map(row => row.brows)).size >= 3
      && new Set(faceMotionAudit.map(row => row.eyes)).size >= 3
      && faceMotionAudit.every(row =>
        row.motion?.mouth && row.motion?.brows && row.motion?.eyes),
    pointer_follow_and_emotion_rules_are_explicit:
      contract.face_choreography?.mouth === "emotion_family_plus_semantic_intent_only"
      && contract.functional_and_emotion_ornaments_coexist === true,
    event_driven_emotion_system_reaches_diverse_families:
      emotionSystemAudit.unique_targets.length >= 8
      && emotionSystemAudit.gestures.join(",") === "warm,playful,delighted"
      && emotionSystemAudit.idle_target === "sleepy"
      && emotionSystemAudit.traceable === true
      && emotionSystemAudit.contract?.architecture
        === "event_updates_affect_vector_then_scored_hysteretic_family_selection",
    calm_mouth_guard_removes_three_peak_grimace:
      calmMouthGuard[0] === "guarded_calm_closed_smile"
      && calmMouthGuard.slice(1, 3).every(value => value === "guarded_calm_closed_smile")
      && calmMouthGuard.slice(3, 5).every(value => value === "guarded_listening_o")
      && calmMouthGuard[5] === "guarded_warm_smile",
    eye_highlight_components_move_whole_inside_safe_border:
      protectedFaceActions.every(row =>
        row.eye_audit.length >= 2
        && row.eye_audit.every(component =>
          component.complete === true
          && component.pixels > 0
          && Array.isArray(component.applied))),
    transition_phase_order:
      transitionPhaseOrder.join(",") === expectedPhases.join(","),
    transition_component_order:
      transitionCommitFor("orient")?.component_order?.[0] === "gaze"
      && transitionCommitFor("anticipate")?.component_order?.[0] === "brows"
      && transitionCommitFor("accent")?.component_order?.includes("mouth")
      && transitionCommitFor("follow")?.component_order?.[0] === "full_face",
    seeded_not_fixed_playlist: contract.scheduler === "semantic_sparse_life_v3"
      && contract.fixed_playlist === false,
    hardware_contact_zero: contract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  const result = {
    schema: "companion.comp_req_727_728.generated_emotion_ornament_rig.verification.v1",
    status,
    checks,
    family_rows: familyRows,
    transition: transitionCommits.map(item => ({
      phase: item.phase,
      source: item.transition_source,
      target: item.transition_target,
      component_order: item.component_order,
      ornament_stage: item.ornament?.stage ?? 0
    })),
    ornament_sequences: ornamentSequences,
    ornament_motion_sequences: ornamentMotionSequences,
    functional_overlay_priority: functionalOverlayPriority,
    face_motion_audit: faceMotionAudit,
    emotion_system_audit: emotionSystemAudit,
    calm_mouth_guard: calmMouthGuard,
    protected_face_actions: protectedFaceActions.map(({ family, action, eye_audit }) => ({
      family,
      action,
      eye_audit
    })),
    screenshots: [
      ".cache/validation/comp-req-727-generated-emotion-rig/screenshots/ten-emotions-with-ornaments.png",
      ".cache/validation/comp-req-727-generated-emotion-rig/screenshots/ornament-four-stage-atlas.png",
      ".cache/validation/comp-req-727-generated-emotion-rig/screenshots/touch-transition-five-phase.png",
      ".cache/validation/comp-req-727-generated-emotion-rig/screenshots/protected-calm-alert-actions.png"
    ],
    browser_errors: browserErrors
  };
  fs.writeFileSync(
    path.join(artifactRoot, "MACHINE_READY.json"),
    `${JSON.stringify(result, null, 2)}\n`
  );
  console.log(JSON.stringify(result, null, 2));
  if (status !== "MACHINE_READY") process.exitCode = 1;
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
}
