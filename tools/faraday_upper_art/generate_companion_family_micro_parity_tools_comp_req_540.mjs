#!/usr/bin/env node
/* Derive the 540 PBM/C parity tools from the protected 539 pack tools. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const generatorInput = path.join(
  root,
  "tools/faraday_upper_art/generate_companion_browser_listening_meter_parity_comp_req_539.mjs",
);
const verifierInput = path.join(
  root,
  "tools/faraday_upper_art/verify_companion_browser_listening_meter_parity_comp_req_539.py",
);
const generatorOutput = path.join(
  root,
  "tools/faraday_upper_art/generate_companion_family_micro_parity_comp_req_540.mjs",
);
const verifierOutput = path.join(
  root,
  "tools/faraday_upper_art/verify_companion_family_micro_parity_comp_req_540.py",
);
const expected = {
  generator: "C92FAD86F9038BECB35C56DC008C345A17124506FE36797B6F05D5E31B5F9F28",
  verifier: "0A53FB0BBB52AD4D1EE2689A8B9A7DF7A9BF1019A76E26786EA3502E24F8122D",
};

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function readCanonical(file) {
  return fs.readFileSync(file, "utf8").replaceAll("\r\n", "\n");
}

function replaceExact(source, before, after, label) {
  const index = source.indexOf(before);
  if (index < 0 || source.indexOf(before, index + before.length) >= 0) {
    throw new Error(`expected exactly one ${label}`);
  }
  return source.slice(0, index) + after + source.slice(index + before.length);
}

let generator = readCanonical(generatorInput);
let verifier = readCanonical(verifierInput);
if (sha256(generator) !== expected.generator) {
  throw new Error("protected 539 parity generator drifted");
}
if (sha256(verifier) !== expected.verifier) {
  throw new Error("protected 539 parity verifier drifted");
}

generator = generator
  .replaceAll("COMP-REQ-539", "COMP-REQ-540")
  .replaceAll("comp-req-539", "comp-req-540")
  .replaceAll("LISTENING_METER", "FAMILY_MICRO")
  .replaceAll("listening_meter", "family_micro");
generator = replaceExact(
  generator,
  `  for (const [index, key] of manifest.idle_glint.ordered_keys.entries()) {
    specs.push({
      frame_index: 4,
      gaze_key: key,
      id: \`idle_glint_\${index}\`,
      kind: "expression",
      story: "calm_presence",
    });
  }`,
  `  for (const plan of manifest.family_micro_choreography.plans) {
    for (const step of [0, 2, 3, 4]) {
      specs.push({
        family: plan.state,
        id: \`family_micro_\${plan.state}_step_\${step}\`,
        kind: "micro",
        micro_step: step,
      });
    }
  }`,
  "family micro specs",
);
generator = replaceExact(
  generator,
  `      frame_index: emotion.hold,
      gaze_key: manifest.idle_glint.baseline_key,
      id: \`recording_\${emotion.state}_hold_meter_0\`,
      kind: "expression",
      meter_step: 0,
      story: emotion.story,`,
  `      family: emotion.state,
      id: \`recording_\${emotion.state}_hold_meter_0\`,
      kind: "micro",
      meter_step: 0,
      micro_step: 0,`,
  "recording family specs",
);
generator = replaceExact(
  generator,
  `      accessory: true,
      frame_index: 4,
      gaze_key: manifest.idle_glint.baseline_key,
      id: \`recording_calm_hold_meter_\${meterStep}\`,
      kind: "expression",
      meter_step: meterStep,
      story: "calm_presence",`,
  `      accessory: true,
      family: "calm",
      id: \`recording_calm_hold_meter_\${meterStep}\`,
      kind: "micro",
      meter_step: meterStep,
      micro_step: 0,`,
  "recording meter specs",
);
generator = replaceExact(
  generator,
  `      } else {
        const story = stories.find((value) => value.name === item.story);`,
  `      } else if (item.kind === "micro") {
        await window.__setFamilyMicroChoreographyFamily(item.family);
        await window.__epaperFreezeIdleGlintStep(item.micro_step);
        const stage = document.querySelector("#overall-viewport");
        const frameNode = stage.querySelector(".viewport-frame");
        const gazeNode = stage.querySelector(".viewport-gaze");
        const frameImage = await load(frameNode.src);
        const gazeImage = await load(gazeNode.src);
        const transform = getComputedStyle(gazeNode).transform;
        const matrix = !transform || transform === "none"
          ? { e: 0, f: 0 }
          : new DOMMatrixReadOnly(transform);
        context.drawImage(frameImage, 0, 0);
        context.drawImage(gazeImage, Math.round(matrix.e), Math.round(matrix.f));
        if (item.accessory) {
          meter = window.__recordingFreezeMeterStep(item.meter_step);
          context.drawImage(recordingLevels, 0, 0);
        }
      } else {
        const story = stories.find((value) => value.name === item.story);`,
  "micro renderer",
);
generator = replaceExact(
  generator,
  "          context.drawImage(recordingIndicator, 12, 12);\n",
  "",
  "recording dot draw",
);

verifier = verifier
  .replaceAll("COMP-REQ-539", "COMP-REQ-540")
  .replaceAll("comp-req-539", "comp-req-540")
  .replaceAll("LISTENING_METER", "FAMILY_MICRO")
  .replaceAll("listening_meter", "family_micro");
verifier = replaceExact(
  verifier,
  "len(states) == 82\n"
    + '            and manifest["invariants"]["state_count"] == 82\n'
    + '            and len({state["id"] for state in states}) == 82',
  "len(states) == 111\n"
    + '            and manifest["invariants"]["state_count"] == 111\n'
    + '            and len({state["id"] for state in states}) == 111',
  "state count",
);
verifier = replaceExact(
  verifier,
  '            and manifest["invariants"]["emotion_count"] == 10',
  '            and manifest["invariants"]["emotion_count"] == 10\n'
    + '            and sum(\n'
    + '                state["id"].startswith("family_micro_")\n'
    + "                for state in states\n"
    + "            ) == 40",
  "family micro state count",
);

fs.writeFileSync(generatorOutput, generator, "utf8");
fs.writeFileSync(verifierOutput, verifier, "utf8");
console.log(JSON.stringify({
  status: "PASS",
  outputs: {
    generator: {
      path: path.relative(root, generatorOutput).replaceAll("\\", "/"),
      sha256: sha256(generator),
    },
    verifier: {
      path: path.relative(root, verifierOutput).replaceAll("\\", "/"),
      sha256: sha256(verifier),
    },
  },
}, null, 2));
