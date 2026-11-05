#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(
  root,
  ".cache/validation/comp-req-751-semantic-pet-rhythm"
);
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
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

function asSet(value) {
  return new Set(Array.isArray(value) ? value : [value]);
}

const { chromium } = playwright();
const browser = await chromium.launch({ headless: true });
const browserErrors = [];
let result;

try {
  const page = await browser.newPage({
    viewport: { width: 1180, height: 900 },
    deviceScaleFactor: 1
  });
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(`console:${message.text()}`);
  });
  page.on("pageerror", error => browserErrors.push(`page:${error.message}`));
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq751Contract === "function"
    && typeof window.__compReq751LifeSequence === "function");
  await page.evaluate(() => window.__compReq714SetScheduler(false));

  const contract = await page.evaluate(() => window.__compReq751Contract());
  const semanticRows = await page.evaluate(familyNames => {
    const allActions = [
      "notice_left",
      "notice_right",
      "soften",
      "small_breath",
      "listen_up",
      "question",
      "beam",
      "tease_grin",
      "yawn",
      "shy_smile",
      "ponder",
      "refocus",
      "startle"
    ];
    return familyNames.map(family => ({
      family,
      rest: window.__compReq751MouthPose(family, "rest", "hold", 0),
      rest_accent: window.__compReq751MouthPose(family, "rest", "accent", 1),
      actions: allActions.map(action => ({
        hold: window.__compReq751MouthPose(family, action, "hold", 0),
        accent: window.__compReq751MouthPose(family, action, "accent", 1)
      }))
    }));
  }, families);

  const lifeRows = {};
  const deterministicRows = {};
  for (const family of families) {
    lifeRows[family] = await page.evaluate(
      familyName => window.__compReq751LifeSequence(familyName, 640),
      family
    );
    deterministicRows[family] = await page.evaluate(familyName => ({
      first: window.__compReq751LifeSequence(familyName, 256),
      second: window.__compReq751LifeSequence(familyName, 256)
    }), family);
  }

  const transitionPairs = [
    ["calm", "curious"],
    ["warm", "playful"],
    ["thoughtful", "alert"]
  ];
  const transitions = [];
  for (const [source, target] of transitionPairs) {
    const start = await page.evaluate(
      ({ source, target }) =>
        window.__compReq751StartTransition(source, target, "semantic_pointer_reaction"),
      { source, target }
    );
    const commits = [];
    for (let step = 0; step < 80; step += 1) {
      const row = await page.evaluate(() => {
        const stepped = window.__compReq728StepTransition();
        const commit = stepped.trace
          .filter(item => item.type === "commit" && item.transition_target)
          .at(-1);
        const canvas = document.querySelector("#face");
        const data = canvas.getContext("2d", { willReadFrequently: true })
          .getImageData(0, 0, 200, 200).data;
        let nonBinaryPixels = 0;
        for (let index = 0; index < data.length; index += 4) {
          const value = data[index];
          if ((value !== 0 && value !== 255)
              || data[index + 1] !== value
              || data[index + 2] !== value
              || data[index + 3] !== 255) {
            nonBinaryPixels += 1;
          }
        }
        return {
          active: stepped.active,
          commit,
          non_binary_pixels: nonBinaryPixels,
          data_url: canvas.toDataURL("image/png")
        };
      });
      if (row.commit) commits.push(row);
      if (!row.active) break;
    }
    transitions.push({ source, target, start, commits });
  }

  const transitionCards = transitions.flatMap(transition => {
    const firstByPhase = new Map();
    transition.commits.forEach(row => {
      if (!firstByPhase.has(row.commit.phase)) {
        firstByPhase.set(row.commit.phase, {
          source: transition.source,
          target: transition.target,
          ...row
        });
      }
    });
    return [...firstByPhase.values()];
  });
  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-751 semantic transition audit</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#202426",
      color: "#fff",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "18px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gridTemplateColumns: "repeat(5, 200px)",
      gap: "14px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      figure.style.margin = "0";
      image.src = card.data_url;
      image.width = 200;
      image.height = 200;
      image.style.display = "block";
      image.style.imageRendering = "pixelated";
      caption.textContent =
        `${card.source} > ${card.target} / ${card.commit.phase} / ${card.commit.mouth_pose}`;
      Object.assign(caption.style, {
        minHeight: "42px",
        padding: "5px",
        boxSizing: "border-box",
        background: "#303638",
        fontSize: "11px"
      });
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, transitionCards);
  await page.screenshot({
    path: path.join(screenshotRoot, "semantic-transition-phases.png"),
    fullPage: true
  });

  const rhythmRows = Object.fromEntries(families.map(family => {
    const sequence = lifeRows[family];
    const episodes = [];
    for (const state of sequence) {
      let episode = episodes.at(-1);
      if (!episode || episode.id !== state.action_episode) {
        episode = {
          id: state.action_episode,
          quiet: [],
          actions: [],
          quiet_dwell: state.quiet_dwell_commits
        };
        episodes.push(episode);
      }
      if (state.life_action === "rest") episode.quiet.push(state);
      else episode.actions.push(state);
    }
    return [family, episodes.slice(0, -1).map(episode => ({
      id: episode.id,
      quiet_commits: episode.quiet.length,
      quiet_dwell: episode.quiet_dwell,
      action: episode.actions[0]?.life_action || null,
      phases: episode.actions.map(state => state.phase),
      phase_dwells: episode.actions.map(state => state.dwell_commits)
    }))];
  }));

  await page.evaluate(rows => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-751 sparse nonperiodic pet rhythm</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0",
      background: "#f4f4f1",
      color: "#111",
      fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid",
      gap: "12px"
    });
    for (const [family, episodes] of Object.entries(rows)) {
      const row = document.createElement("div");
      const label = document.createElement("strong");
      const timeline = document.createElement("div");
      label.textContent = family;
      Object.assign(row.style, {
        display: "grid",
        gridTemplateColumns: "100px 1fr",
        alignItems: "center",
        gap: "10px"
      });
      Object.assign(timeline.style, {
        display: "flex",
        alignItems: "stretch",
        height: "34px",
        overflow: "hidden",
        border: "1px solid #777"
      });
      episodes.slice(0, 9).forEach(episode => {
        const quiet = document.createElement("span");
        quiet.title = `quiet ${episode.quiet_commits}`;
        Object.assign(quiet.style, {
          flex: `${episode.quiet_commits} 0 0`,
          minWidth: "8px",
          background: "#fff"
        });
        const action = document.createElement("span");
        action.title = `${episode.action} ${episode.phase_dwells.join("/")}`;
        Object.assign(action.style, {
          flex: `${Math.max(2, episode.phase_dwells.reduce((a, b) => a + b, 0))} 0 0`,
          minWidth: "8px",
          background: "#222"
        });
        timeline.append(quiet, action);
      });
      row.append(label, timeline);
      document.querySelector("section").append(row);
    }
  }, rhythmRows);
  await page.screenshot({
    path: path.join(screenshotRoot, "nonperiodic-rhythm-map.png"),
    fullPage: true
  });

  const semanticChecks = semanticRows.slice(1).every(row => {
    const semantics = contract.mouth_semantics[row.family];
    const stable = asSet(semantics.stable);
    const accent = asSet(semantics.accent);
    if (!stable.has(row.rest.mouth_pose) || !accent.has(row.rest_accent.mouth_pose)) {
      return false;
    }
    return row.actions.every(({ hold, accent: actionAccent }) => {
      if (!hold.allowed_for_family) {
        return stable.has(hold.mouth_pose) && stable.has(actionAccent.mouth_pose);
      }
      if (semantics.accent_actions.includes(hold.action)) {
        return stable.has(hold.mouth_pose) && accent.has(actionAccent.mouth_pose);
      }
      return stable.has(hold.mouth_pose) && stable.has(actionAccent.mouth_pose);
    });
  });

  const lifeSemanticChecks = families.every(family => {
    const allowed = new Set(contract.family_actions[family]);
    const semantics = contract.mouth_semantics[family];
    const stable = asSet(semantics.stable);
    const accent = asSet(semantics.accent);
    return lifeRows[family].every(state => {
      if (state.life_action === "rest") return stable.has(state.mouth_pose);
      if (!allowed.has(state.life_action)) return false;
      if (family === "calm") {
        if (["small_breath", "listen_up"].includes(state.life_action)) {
          return state.mouth_pose === "listening_o";
        }
        if (state.life_action === "soften") return state.mouth_pose === "warm_smile";
        return state.mouth_pose === "calm_closed_smile";
      }
      const shouldAccent = semantics.accent_actions.includes(state.life_action)
        && ["accent", "follow"].includes(state.phase);
      return (shouldAccent ? accent : stable).has(state.mouth_pose);
    });
  });

  const quietEpisodesValid = families.every(family => {
    const episodes = rhythmRows[family];
    return episodes.length >= 8
      && episodes.every(episode =>
        episode.quiet_commits === episode.quiet_dwell
        && episode.quiet_commits >= 2
        && episode.quiet_commits <= 4)
      && episodes.every((episode, index) =>
        index === 0 || episode.quiet_commits !== episodes[index - 1].quiet_commits)
      && new Set(episodes.slice(0, 10).map(row => row.quiet_commits)).size === 3;
  });

  const actionDwellsValid = families.every(family =>
    lifeRows[family].every(state => {
      if (state.life_action === "rest") return state.dwell_commits === 1;
      const [minimum, maximum] = contract.action_phase_dwell_ranges[state.phase];
      return state.dwell_commits >= minimum && state.dwell_commits <= maximum;
    }));

  const stableRestEpisodes = families.every(family => {
    const byEpisode = new Map();
    lifeRows[family].filter(state => state.life_action === "rest").forEach(state => {
      if (!byEpisode.has(state.action_episode)) byEpisode.set(state.action_episode, []);
      byEpisode.get(state.action_episode).push(state);
    });
    return [...byEpisode.values()].every(states =>
      new Set(states.map(state => state.variation)).size === 1
      && new Set(states.map(state => state.mouth_pose)).size === 1);
  });

  const transitionSemanticsValid = transitions.every(transition => {
    const sourceStable = asSet(contract.mouth_semantics[transition.source].stable);
    const targetStable = asSet(contract.mouth_semantics[transition.target].stable);
    const targetAccent = asSet(contract.mouth_semantics[transition.target].accent);
    return transition.commits.every(row => {
      const expected = ["orient", "anticipate"].includes(row.commit.phase)
        ? sourceStable
        : ["accent", "follow"].includes(row.commit.phase)
          ? targetAccent
          : targetStable;
      return expected.has(row.commit.mouth_pose) && row.commit.interaction_intent;
    });
  });

  const transitionDwellsValid = transitions.every(transition => {
    const counts = Object.fromEntries(
      ["orient", "anticipate", "accent", "follow", "settle"].map(phase => [
        phase,
        transition.commits.filter(row => row.commit.phase === phase).length
      ])
    );
    return ["orient", "anticipate", "accent", "follow", "settle"]
      .every((phase, index) => counts[phase] === transition.start.phase_dwells[index]);
  });

  const checks = {
    fixed_url_http_200:
      response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    semantic_architecture_declared:
      contract.architecture
        === "emotion_family_plus_semantic_intent_with_sparse_seeded_dwell"
      && contract.unrelated_action_policy === "keep_family_stable_mouth",
    ten_family_semantics_complete:
      families.every(family =>
        contract.mouth_semantics[family]
        && contract.family_actions[family]?.length >= 2),
    unrelated_actions_keep_family_mouth: semanticChecks,
    life_actions_restricted_to_family: lifeSemanticChecks,
    quiet_dwell_nonperiodic_and_sparse: quietEpisodesValid,
    action_phase_dwell_nonperiodic_and_bounded: actionDwellsValid,
    rest_frames_keep_one_variant_and_mouth: stableRestEpisodes,
    deterministic_replay:
      families.every(family =>
        JSON.stringify(deterministicRows[family].first)
          === JSON.stringify(deterministicRows[family].second)),
    long_timeline_not_short_loop:
      contract.timeline_commits >= 2048
      && families.every(family =>
        JSON.stringify(lifeRows[family].slice(0, 160))
          !== JSON.stringify(lifeRows[family].slice(160, 320))),
    transition_never_leaks_unmapped_source_mouth: transitionSemanticsValid,
    transition_phase_dwells_match_seeded_plan: transitionDwellsValid,
    transition_rhythm_vectors_vary:
      new Set(transitions.map(row => JSON.stringify(row.start.phase_dwells))).size >= 2,
    transition_canvas_strict_1bpp:
      transitions.every(transition =>
        transition.commits.every(row => row.non_binary_pixels === 0)),
    calm_mouth_contract_protected:
      contract.calm_guard.hold === "calm_closed_smile"
      && contract.calm_guard.breathing_and_listening === "listening_o"
      && contract.calm_guard.soften === "warm_smile",
    fixed_review_url_unchanged: contract.fixed_review_url === fixedUrl,
    hardware_contact_zero: contract.hardware_contact === 0
  };
  const status = Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO";
  result = {
    schema: "companion.comp_req_751.semantic_pet_rhythm.v1",
    status,
    fixed_url: fixedUrl,
    checks,
    browser_errors: browserErrors,
    rhythm: rhythmRows,
    transitions: transitions.map(transition => ({
      source: transition.source,
      target: transition.target,
      phase_dwells: transition.start.phase_dwells,
      commits: transition.commits.map(row => ({
        phase: row.commit.phase,
        mouth_pose: row.commit.mouth_pose,
        interaction_intent: row.commit.interaction_intent,
        non_binary_pixels: row.non_binary_pixels
      }))
    })),
    screenshots: [
      ".cache/validation/comp-req-751-semantic-pet-rhythm/screenshots/semantic-transition-phases.png",
      ".cache/validation/comp-req-751-semantic-pet-rhythm/screenshots/nonperiodic-rhythm-map.png"
    ],
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
  screenshots: result.screenshots
}, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
