#!/usr/bin/env node

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const sourceVerifier = path.join(
  root,
  "tools/faraday_upper_art/replay_companion_browser_listening_meter_comp_req_539.mjs",
);
const outputIndex = process.argv.indexOf("--output");
assert(outputIndex >= 0 && process.argv[outputIndex + 1], "missing --output");
const output = path.resolve(root, process.argv[outputIndex + 1]);
assert(output.startsWith(`${root}${path.sep}`), "output must remain in repository");
const legacyOutput = path.join(output, "legacy-comp-req-539-replay");

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

fs.mkdirSync(output, { recursive: true });
const run = spawnSync(
  process.execPath,
  [sourceVerifier, "--output", legacyOutput],
  { cwd: root, encoding: "utf8" },
);
assert(
  run.status === 0 || run.status === 1,
  `legacy replay failed to complete: ${run.stderr || run.stdout}`,
);

const legacyResultPath = path.join(legacyOutput, "browser-replay-result.json");
assert(fs.existsSync(legacyResultPath), "legacy replay result missing");
const legacy = JSON.parse(fs.readFileSync(legacyResultPath, "utf8"));
assert.equal(legacy.counts.combinations, 6);
assert.equal(legacy.counts.scenarios, 42);
assert.equal(legacy.counts.errors, 0);
assert.equal(legacy.counts.microphone_requests, 0);
assert.equal(legacy.checks.combinations_exact, true);
assert.equal(legacy.checks.scenario_count_exact, true);
assert.equal(legacy.checks.no_404_or_page_error, true);
assert.equal(legacy.checks.no_microphone_request, true);
assert.deepEqual(legacy.side_effects, {
  hardware: 0,
  owner_prompt: 0,
  production_write: 0,
});

const combinations = [
  "desktop-mouse", "desktop-touch", "desktop-pen",
  "mobile-mouse", "mobile-touch", "mobile-pen",
];
const expectedSuperseded = combinations.map(
  (combo) => `${combo}:double_tap_meter_entry`,
);
assert.deepEqual([...legacy.failed].sort(), [...expectedSuperseded].sort());

const supersededRows = legacy.scenarios.filter(
  (row) => row.name === "double_tap_meter_entry",
);
assert.equal(supersededRows.length, 6);
for (const row of supersededRows) {
  assert.equal(row.pass, false);
  assert.equal(row.observed.accessory_active, true);
  assert.equal(row.observed.recording_entries, 1);
  assert.equal(row.observed.interaction_mode, "expression");
  assert.equal(row.observed.surfaces.face, 1);
  assert.equal(row.observed.surfaces.gaze, 1);
  assert.equal(row.observed.surfaces.indicator, 0);
  assert.equal(row.observed.surfaces.levels, 1);
  assert.equal(row.observed.surfaces.menu, 0);
  assert.equal(row.observed.progress_nodes, 0);
}

const otherRows = legacy.scenarios.filter(
  (row) => row.name !== "double_tap_meter_entry",
);
assert.equal(otherRows.length, 36);
assert(otherRows.every((row) => row.pass), "non-superseded scenario failed");

const report = {
  schema: "companion.comp_req_560.interaction_successor.v1",
  status: "PASS",
  requirements: ["COMP-REQ-540", "COMP-REQ-554", "COMP-REQ-560"],
  page_repo_path: legacy.inputs.page_repo_path,
  page_canonical_sha256: legacy.inputs.page_canonical_sha256,
  combinations: 6,
  scenarios: 42,
  scenarios_pass_under_current_contract: 42,
  inherited_passes: otherRows.length,
  superseded_recording_entry_passes: supersededRows.length,
  current_recording_entry_contract: {
    face_layers: 1,
    gaze_layers: 1,
    removed_top_left_indicator_layers: 0,
    inward_meter_layers: 1,
    recording_entries: 1,
    menu_layers: 0,
    progress_nodes: 0,
  },
  errors: 0,
  microphone_requests: 0,
  side_effects: legacy.side_effects,
  legacy_result_repo_path: path.relative(root, legacyResultPath).replaceAll("\\", "/"),
  legacy_result_sha256: sha256(fs.readFileSync(legacyResultPath)),
  source_verifier_repo_path: path.relative(root, sourceVerifier).replaceAll("\\", "/"),
  source_verifier_sha256: sha256(fs.readFileSync(sourceVerifier)),
};
const reportPath = path.join(output, "interaction-successor-result.json");
fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({
  status: report.status,
  scenarios: report.scenarios_pass_under_current_contract,
  page_sha256: report.page_canonical_sha256,
  report_sha256: sha256(fs.readFileSync(reportPath)),
}));
