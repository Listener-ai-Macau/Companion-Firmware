#!/usr/bin/env node
/* Derive the COMP-REQ-540 replay from the protected 539 gesture matrix. */

import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const inputPath = path.join(
  repoRoot,
  "tools/faraday_upper_art/replay_companion_browser_listening_meter_comp_req_539.mjs",
);
const outputPath = path.join(
  repoRoot,
  "tools/faraday_upper_art/replay_companion_family_micro_choreography_comp_req_540.mjs",
);
const expectedInputSha256 =
  "FAE04F583870933146E657466A771258B11215852BD60AFED2861F4A7676F948";

function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
}

function replaceExact(source, before, after, label) {
  const index = source.indexOf(before);
  if (index < 0 || source.indexOf(before, index + before.length) >= 0) {
    throw new Error(`expected exactly one ${label}`);
  }
  return source.slice(0, index) + after + source.slice(index + before.length);
}

let source = fs.readFileSync(inputPath, "utf8").replaceAll("\r\n", "\n");
if (sha256(source) !== expectedInputSha256) {
  throw new Error("protected COMP-REQ-539 replay source drifted");
}
source = replaceExact(
  source,
  "/* Six viewport/pointer combinations and 42 scenarios for COMP-REQ-539. */",
  "/* Six viewport/pointer combinations and 42 scenarios for COMP-REQ-540. */",
  "header",
);
source = replaceExact(
  source,
  "entered.surfaces.indicator === 1",
  "entered.surfaces.indicator === 0",
  "meter-only recording entry",
);
source = source.replaceAll(
  "companion.comp-req-539-",
  "companion.comp-req-540-",
);
source = replaceExact(
  source,
  'requirements: ["COMP-REQ-539"],',
  'requirements: ["COMP-REQ-539", "COMP-REQ-540", "COMP-REQ-541"],',
  "requirements",
);
source = replaceExact(
  source,
  "recording_is_orthogonal: scenarios",
  "recording_indicator_zero: scenarios\n"
    + '      .filter((row) => row.name === "double_tap_meter_entry")\n'
    + "      .every((row) => row.pass),\n"
    + "    recording_is_orthogonal: scenarios",
  "recording indicator invariant",
);
if (source.includes("indicator === 1")) {
  throw new Error("legacy recording dot expectation survived");
}
fs.writeFileSync(outputPath, source, "utf8");
console.log(JSON.stringify({
  status: "PASS",
  input_sha256: expectedInputSha256,
  output: path.relative(repoRoot, outputPath).replaceAll("\\", "/"),
  output_sha256: sha256(source),
}, null, 2));
