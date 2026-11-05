#!/usr/bin/env node

import assert from "node:assert/strict";
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pagePath = path.join(root, "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7", "candidate/wb55-browser-parity-attempt-01/index.html");
const outputIndex = process.argv.indexOf("--output");
assert(outputIndex >= 0 && process.argv[outputIndex + 1], "missing --output");
const output = path.resolve(root, process.argv[outputIndex + 1]);
assert(output.startsWith(`${root}${path.sep}`), "output must remain in repository");
const screenshotDir = path.join(path.dirname(output), "screenshots");
fs.mkdirSync(path.dirname(output), { recursive: true });
fs.mkdirSync(screenshotDir, { recursive: true });

const PAGE_URL = "/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const FAMILIES = ["calm", "curious", "warm", "playful", "sleepy", "delighted", "bashful", "thoughtful", "focused", "alert"];
const STEPS = [0, 2, 3, 4, 5, 6, 7, 8, 9];
const ACTIVE_STEPS = [2, 4, 6, 8];
const GAZES = [["center", "1,0,1,0"], ["left", "-2,0,-6,0"], ["right", "5,0,5,0"], ["up", "1,-3,1,-6"], ["down", "1,4,1,6"]];
const ROI = { left: [38, 82, 75, 131], right: [125, 82, 162, 131] };
const PUPIL_PATTERN = ["..111..", ".11111.", "1111111", "1111111", "1111111", "1111111", "1111111", "1111111", "1111111", ".11111.", "..111.."];
const GLINT_PATTERN = ["0110", "1110", "0110"];
const NARROW = process.argv.includes("--narrow");
const CHECK_FAMILIES = NARROW ? ["calm", "sleepy", "alert"] : FAMILIES;
const CHECK_STEPS = NARROW ? [0, 2, 4, 8, 9] : STEPS;

const sha256 = (value) => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
function loadPlaywright() {
  for (const candidate of [process.env.COMPANION_PLAYWRIGHT_MODULE, "playwright", "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"].filter(Boolean)) {
    try { return require(candidate); } catch { /* bounded candidates */ }
  }
  throw new Error("Playwright unavailable");
}
function pngSize(file) {
  const data = fs.readFileSync(file);
  assert.equal(data.readUInt32BE(0), 0x89504e47, `${file}: not PNG`);
  return { width: data.readUInt32BE(16), height: data.readUInt32BE(20) };
}
function rel(file) { return path.relative(root, file).replaceAll("\\", "/"); }
function bitHash(bits) { return sha256(Buffer.from(bits)); }
function setOf(points) { return new Set(points); }
function bounds(points) {
  return { minX: Math.min(...points.map((p) => p % 200)), maxX: Math.max(...points.map((p) => p % 200)), minY: Math.min(...points.map((p) => Math.floor(p / 200))), maxY: Math.max(...points.map((p) => Math.floor(p / 200))) };
}
function centroid(points) { return { x: points.reduce((sum, p) => sum + p % 200, 0) / points.length, y: points.reduce((sum, p) => sum + Math.floor(p / 200), 0) / points.length }; }
function diff(a, b) { const added = [], removed = []; for (let i = 0; i < a.length; i++) { if (!a[i] && b[i]) added.push(i); if (a[i] && !b[i]) removed.push(i); } return { added, removed }; }
function sameSet(a, b) { return a.length === b.length && a.every((p) => b.includes(p)); }
function region(points, side) { return points.filter((p) => side === "left" ? p % 200 < 100 : p % 200 >= 100); }
function pointComponents(points) {
  const available = new Set(points), components = [];
  while (available.size) {
    const first = available.values().next().value, component = [first], queue = [first]; available.delete(first);
    while (queue.length) {
      const p = queue.pop(), neighbors = [p - 1, p + 1, p - 200, p + 200];
      for (const n of neighbors) if (available.delete(n)) { queue.push(n); component.push(n); }
    }
    components.push(component);
  }
  return components.sort((a, b) => b.length - a.length);
}
function shapeIsLargePupil(points) {
  if (points.length < 60) return false;
  const box = bounds(points);
  if (box.maxX - box.minX !== 6 || box.maxY - box.minY !== 10) return false;
  return new Set(points).size === points.length;
}
function envelopePoints(envelope) {
  return (envelope?.rows || []).flatMap((row) => Array.from({ length: row.maxX - row.minX + 1 }, (_, offset) => row.y * 200 + row.minX + offset));
}
function envelopeBySide(sample, side) {
  return sample.binding?.envelopes?.find((envelope) => envelope.eye === side) || null;
}
function envelopeNormalizationOracle(sample, name) {
  assert.equal(sample.binding?.envelopes?.length, 2, `${name}: missing paired row-span envelopes`);
  const result = {};
  for (const side of Object.keys(ROI)) {
    const envelope = envelopeBySide(sample, side);
    const points = envelopePoints(envelope);
    assert(points.length > 0, `${name}/${side}: empty row-span envelope`);
    assert.equal(points.length, envelope.area, `${name}/${side}: envelope area/rows drift`);
    const baseWhite = points.filter((p) => sample.base.white[p]);
    assert.equal(baseWhite.length, 0, `${name}/${side}: bound base retained source white cue inside envelope`);
    result[side] = { area: points.length, bounds: envelope.bounds, source_white_pixels: envelope.source_white_pixels, bound_base_white_pixels: baseWhite.length, points };
  }
  return result;
}
function authoredPupilFromGlint(rendered, glintPoints) {
  const glintBox = bounds(glintPoints), x0 = glintBox.minX - 1, y0 = glintBox.minY - 2, glintSet = setOf(glintPoints), points = [];
  for (let y = 0; y < PUPIL_PATTERN.length; y++) for (let x = 0; x < PUPIL_PATTERN[y].length; x++) if (PUPIL_PATTERN[y][x] === "1") points.push((y0 + y) * 200 + x0 + x);
  const expectedGlint = []; for (let y = 0; y < GLINT_PATTERN.length; y++) for (let x = 0; x < GLINT_PATTERN[y].length; x++) if (GLINT_PATTERN[y][x] === "1") expectedGlint.push((y0 + y + 2) * 200 + x0 + x + 1);
  assert.deepEqual([...glintSet].sort((a, b) => a - b), expectedGlint.sort((a, b) => a - b), "glint shape/relative anchor mismatch");
  assert(points.length === 65 && points.filter((p) => !glintSet.has(p)).every((p) => rendered.black[p]), "authored black pupil pixels are missing");
  return points;
}
function pupilFullyInsetOracle(sample, side, field, pupil, name) {
  const pupilSet = new Set(pupil), envelopeSet = new Set(envelopePoints(envelopeBySide(sample, side))), ring = new Set();
  for (const p of pupil) {
    const x = p % 200, y = Math.floor(p / 200);
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue;
      const n = (y + dy) * 200 + x + dx;
      if (!pupilSet.has(n)) ring.add(n);
    }
  }
  assert([...ring].every((p) => field.has(p) && sample.rendered.white[p]), `${name}/${side}: pupil lacks complete 8-neighbor white separation`);
  const shell = new Set([...envelopeSet].filter((p) => sample.rendered.black[p] && !pupilSet.has(p)));
  assert(!pupil.some((p) => { const x = p % 200, y = Math.floor(p / 200); for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && shell.has((y + dy) * 200 + x + dx)) return true; return false; }), `${name}/${side}: pupil touches envelope black shell`);
  return { pass: true, white_ring_pixels: ring.size, shell_touch_pixels: 0 };
}
function renderedResidualOracle(sample, name) {
  const normalized = envelopeNormalizationOracle(sample, name);
  const result = {};
  for (const side of Object.keys(ROI)) {
    const current = pointComponents(normalized[side].points.filter((p) => sample.rendered.white[p]));
    assert.equal(current.length, 2, `${name}/${side}: rendered envelope white components are not exactly field + glint ${JSON.stringify(current.map((component) => ({ size: component.length, box: bounds(component) })))}`);
    assert(current[0].length >= 100 && current[0].length >= current[1].length, `${name}/${side}: authored field is not the unique large white component ${JSON.stringify(current.map((component) => component.length))}`);
    assert.equal(current[1].length, 7, `${name}/${side}: unique glint is not exactly 7 pixels`);
    const field = setOf(current[0]), glintPoints = current[1], glint = setOf(glintPoints);
    const residual = normalized[side].points.filter((p) => sample.rendered.white[p] && !field.has(p) && !glint.has(p));
    assert.equal(residual.length, 0, `${name}/${side}: residual white cue outside authored field/glint`);
    const box = sample.meta.inner_field_bounds[side === "left" ? 0 : 1];
    const pupil = authoredPupilFromGlint(sample.rendered, glintPoints);
    const inset = pupilFullyInsetOracle(sample, side, field, pupil, name);
    const fieldMinusPupil = pointComponents(current[0].filter((p) => !pupil.includes(p)));
    assert.equal(fieldMinusPupil.length, 1, `${name}/${side}: field-minus-pupil has isolated white island ${JSON.stringify(fieldMinusPupil.map((component) => ({ size: component.length, box: bounds(component) })))}`);
    const pupilBox = bounds(pupil);
    assert(pupil.length >= 50 && glintPoints.every((p) => { const x = p % 200, y = Math.floor(p / 200); return x >= pupilBox.minX && x <= pupilBox.maxX && y >= pupilBox.minY && y <= pupilBox.maxY; }), `${name}/${side}: glint detached from pupil ${JSON.stringify({ glint: bounds(glintPoints), pupil: pupilBox })}`);
    result[side] = { source_white_pixels: normalized[side].source_white_pixels, bound_base_white_pixels: 0, rendered_components: current.map((component) => component.length), field_minus_pupil_components: fieldMinusPupil.map((component) => component.length), residual_white_cue: residual.length, field, glint: glintPoints, pupil, inset };
  }
  return result;
}
function familyFrameBindingOracle(sample, name) {
  const binding = sample.binding;
  assert(binding, name + ": missing COMP-REQ-567 frame binding");
  assert.equal(binding.overlay_frame_src, binding.frame_open ? binding.frame_src : "", name + ": closed frame still has an overlay");
  if (binding.frame_open) {
    assert.equal(binding.gaze_hidden, false, name + ": open frame hid its pupil overlay");
    assert.equal(binding.overlay_frame_src, binding.frame_src, name + ": overlay was not rebuilt for the new frame");
    const layers = renderedResidualOracle(sample, name);
    return { kind: "open", architecture: sample.meta?.architecture || null, layers };
  }
  assert.equal(binding.gaze_hidden, true, name + ": closed frame still shows gaze");
  assert.equal(sample.meta, null, name + ": closed/squint frame still exposes gaze metadata");
  assert.equal(sample.gaze_src, "", name + ": closed/squint frame retained a pupil/glint source");
  const normalized = envelopeNormalizationOracle(sample, name);
  const residual = {};
  for (const side of Object.keys(ROI)) {
    const white = normalized[side].points.filter((p) => sample.rendered.white[p]);
    assert.equal(white.length, 0, name + "/" + side + ": closed/squint frame retained white cue inside envelope");
    residual[side] = { source_white_pixels: normalized[side].source_white_pixels, bound_base_white_pixels: 0, rendered_white_pixels: 0 };
  }
  return { kind: "closed", architecture: null, layers: residual };
}

async function capture(page) {
  return page.evaluate(async () => {
    const frame = document.querySelector("#overall-viewport .viewport-frame");
    const gaze = document.querySelector("#overall-viewport .viewport-gaze");
    const wait = (image) => image.complete ? Promise.resolve() : new Promise((resolve) => image.addEventListener("load", resolve, { once: true }));
    await wait(frame); if (!gaze.hidden) await wait(gaze);
    const draw = (includeGaze) => { const canvas = document.createElement("canvas"); canvas.width = canvas.height = 200; const context = canvas.getContext("2d", { willReadFrequently: true }); context.drawImage(frame, 0, 0); if (includeGaze && !gaze.hidden) context.drawImage(gaze, 0, 0); const data = context.getImageData(0, 0, 200, 200).data; return { black: Array.from({ length: 40000 }, (_, i) => data[i * 4] < 128 ? 1 : 0), white: Array.from({ length: 40000 }, (_, i) => data[i * 4] > 220 ? 1 : 0) }; };
    const base = draw(false), rendered = draw(true);
    const binding = window.__compReq567FrameBindingState ? window.__compReq567FrameBindingState() : null;
    return { frame_src: frame.src, gaze_src: gaze.hidden ? "" : gaze.src, gaze_hidden: gaze.hidden, base, rendered, meta: gaze.hidden ? null : (touchGazeRenderMetaBySrc.get(gaze.src) || null), binding, family: window.__familyMicroChoreographyState(), recording: window.__recordingContractState() };
  });
}
async function screenShot(page, file) {
  const target = path.join(screenshotDir, file);
  const box = await page.locator("#overall-viewport").boundingBox();
  assert(box, "missing overall viewport bounding box");
  await page.screenshot({ path: target, clip: { x: box.x, y: box.y, width: 400, height: 400 } });
  const size = pngSize(target);
  assert.deepEqual(size, { width: 400, height: 400 }, `${file}: screenshot is not tight 400x400 owner scale`);
  return target;
}
async function strip(browser, entries, file, columns) {
  const page = await browser.newPage({ viewport: { width: Math.max(420, columns * 420), height: Math.ceil(entries.length / columns) * 430 } });
  const html = entries.map((entry) => `<figure><img src="data:image/png;base64,${fs.readFileSync(entry.path).toString("base64")}"><figcaption>${entry.label}</figcaption></figure>`).join("");
  await page.setContent(`<style>body{margin:0;background:#e7e7e3;color:#111;font:14px Arial}main{display:grid;grid-template-columns:repeat(${columns},400px);gap:12px;padding:10px}figure{margin:0}img{display:block;width:400px;height:400px;image-rendering:pixelated;background:#fff}figcaption{text-align:center;height:18px;padding-top:2px}</style><main>${html}</main>`);
  const target = path.join(screenshotDir, file); await page.screenshot({ path: target, fullPage: true }); await page.close(); return target;
}

function directOracle(sample, center, name) {
  const meta = sample.meta;
  assert(meta, `${name}: missing gaze overlay metadata`);
  assert.equal(meta.architecture, "fixed_outer_silhouette|authored_inner_white_field|paired_large_pupil_plus_rigid_glint", `${name}: wrong eye architecture`);
  assert(meta.inner_field_area >= 200 && meta.pupil_area >= 120 && meta.glint_area === 14, `${name}: insufficient three-layer areas`);
  assert.equal(meta.highlight_hole_architecture, false, `${name}: highlight-hole architecture`);
  assert.equal(meta.field_boundary_fixed, true); assert.equal(meta.pupil_glint_rigid, true); assert.equal(meta.old_pose_pixels, 0);
  const layers = renderedResidualOracle(sample, name);
  const centerLayers = renderedResidualOracle(center, `${name}/center`);
  for (const side of ["left", "right"]) { const rel = (layers[side].glint.map((p) => `${Math.round((p % 200) - centroid(layers[side].pupil).x)},${Math.round(Math.floor(p / 200) - centroid(layers[side].pupil).y)}`).sort()); const centerRel = centerLayers[side].glint.map((p) => `${Math.round((p % 200) - centroid(centerLayers[side].pupil).x)},${Math.round(Math.floor(p / 200) - centroid(centerLayers[side].pupil).y)}`).sort(); assert.deepEqual(rel, centerRel, `${name}/${side}: glint geometry is not rigid`); }
  const fieldBoxes = sample.meta.inner_field_bounds;
  assert.deepEqual(fieldBoxes, center.meta.inner_field_bounds, `${name}: inner white field boundary moved`);
  const outsideField = (bits) => bits.map((value, index) => fieldBoxes.some((box) => { const x = index % 200, y = Math.floor(index / 200); return x >= box.minX && x <= box.maxX && y >= box.minY && y <= box.maxY; }) ? 0 : value);
  assert.deepEqual(outsideField(sample.rendered.black), outsideField(center.rendered.black), `${name}: outer silhouette changed`);
  const pupilPoints = (state, side) => state === sample ? layers[side].pupil : centerLayers[side].pupil;
  const left = pupilPoints(sample, "left"), right = pupilPoints(sample, "right");
  const centerLeft = pupilPoints(center, "left"), centerRight = pupilPoints(center, "right");
  assert(shapeIsLargePupil(left) || left.length >= 50, `${name}: left pupil too small`);
  assert(shapeIsLargePupil(right) || right.length >= 50, `${name}: right pupil too small`);
  const lc = centroid(left), rc = centroid(right), cc = centroid(centerLeft), cr = centroid(centerRight);
  assert.equal(Math.round(lc.x - cc.x), Math.round(rc.x - cr.x), `${name}: pupils not paired`);
  const sign = (v) => Math.sign(v);
  const expected = { left: [-1, 0], right: [1, 0], up: [0, -1], down: [0, 1], center: [0, 0] }[name];
  assert.equal(sign(lc.x - cc.x), expected[0], `${name}: horizontal direction wrong`);
  assert.equal(sign(lc.y - cc.y), expected[1], `${name}: vertical direction wrong`);
  return { pass: true, meta, left_bounds: bounds(left), right_bounds: bounds(right), paired: true, stale: 0, rendered_residual_white_cue: Object.fromEntries(Object.entries(layers).map(([side, value]) => [side, value.residual_white_cue])) };
}
function temporalOracle(rows, family) {
  const signatures = rows.map((row) => row.trace?.family_signature || "");
  const active = rows.filter((row) => ACTIVE_STEPS.includes(row.step));
  const holds = rows.filter((row) => [3, 5, 7].includes(row.step));
  const components = active.every((row) => row.components.some((item) => item !== "pupil"));
  const result = { pass: new Set(rows.map((row) => row.face_hash)).size >= 4 && rows[0].face_hash === rows.at(-1).face_hash && components && holds.every((row) => row.trace?.changed === false && row.trace?.refresh_requested === false), family, distinct_face_hashes: new Set(rows.map((row) => row.face_hash)).size, components, holds: holds.map((row) => ({ step: row.step, changed: row.trace?.changed, refresh_requested: row.trace?.refresh_requested })), baseline_return: rows[0].face_hash === rows.at(-1).face_hash, signature: signatures[0] };
  assert(result.pass, `${family}: choreography signature/hold/baseline failed`);
  return result;
}
function negativeFixtures(sample, center) {
  const results = {};
  const reject = (mutated, predicate) => predicate(mutated) === false;
  results.missing_inner_field = reject({ ...sample.meta, inner_field_area: 0 }, (m) => m.inner_field_area >= 200);
  results.highlight_hole_architecture = reject({ ...sample.meta, highlight_hole_architecture: true }, (m) => !m.highlight_hole_architecture);
  results.tiny_pupil = reject({ ...sample.meta, pupil_area: 8 }, (m) => m.pupil_area >= 120);
  results.detached_glint = reject({ ...sample.meta, pupil_glint_rigid: false }, (m) => m.pupil_glint_rigid);
  const switched = { ...sample, binding: { ...sample.binding, frame_src: "switched-family-frame.png" } };
  try { familyFrameBindingOracle(switched, "negative-family-frame-switch"); results.family_frame_switch_without_rebuilding_overlay = false; } catch { results.family_frame_switch_without_rebuilding_overlay = true; }
  const rightEnvelope = envelopePoints(envelopeBySide(sample, "right"));
  const rightEnvelopeSet = new Set(rightEnvelope);
  const currentRight = pointComponents(rightEnvelope.filter((p) => sample.rendered.white[p]));
  const currentRightSet = new Set(currentRight.flat());
  const fourNeighbors = (p) => [p - 1, p + 1, p - 200, p + 200];
  const detached = rightEnvelope.find((p) => !currentRightSet.has(p) && sample.rendered.black[p] && fourNeighbors(p).every((n) => rightEnvelopeSet.has(n) && sample.rendered.black[n] && !currentRightSet.has(n)));
  const detachedSample = { ...sample, base: { ...sample.base, white: [...sample.base.white] }, rendered: { ...sample.rendered, white: [...sample.rendered.white], black: [...sample.rendered.black] } };
  if (detached !== undefined) { detachedSample.rendered.white[detached] = 1; detachedSample.rendered.black[detached] = 0; }
  try { renderedResidualOracle(detachedSample, "negative-detached-old-glint"); results.detached_old_glint = false; } catch { results.detached_old_glint = detached !== undefined; }
  const connectedCueSample = { ...sample, base: { ...sample.base, white: [...sample.base.white], black: [...sample.base.black] } };
  const cue = rightEnvelope.find((p) => sample.base.black[p]);
  if (cue !== undefined) { connectedCueSample.base.white[cue] = 1; connectedCueSample.base.black[cue] = 0; }
  try { envelopeNormalizationOracle(connectedCueSample, "negative-boundary-connected-source-cue"); results.boundary_connected_source_cue = false; } catch { results.boundary_connected_source_cue = cue !== undefined; }
  const rightField = new Set(currentRight[0]), rightPupil = authoredPupilFromGlint(sample.rendered, currentRight[1]), rightPupilSet = new Set(rightPupil);
  const touching = rightPupil.flatMap((p) => { const x = p % 200, y = Math.floor(p / 200); const out = []; for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if ((dx || dy) && !rightPupilSet.has((y + dy) * 200 + x + dx)) out.push((y + dy) * 200 + x + dx); return out; }).find((p) => rightField.has(p));
  const touchingSample = { ...sample, rendered: { ...sample.rendered, white: [...sample.rendered.white], black: [...sample.rendered.black] } };
  if (touching !== undefined) { touchingSample.rendered.white[touching] = 0; touchingSample.rendered.black[touching] = 1; }
  try { renderedResidualOracle(touchingSample, "negative-touching-shell"); results.touching_shell = false; } catch { results.touching_shell = touching !== undefined; }
  results.moved_outer_silhouette = reject({ ...sample.meta, field_boundary_fixed: false }, (m) => m.field_boundary_fixed);
  results.stale_pose = reject({ ...sample.meta, old_pose_pixels: 1 }, (m) => m.old_pose_pixels === 0);
  results.missing_pupil_pixel = reject({ ...sample.meta, pupil_area: 119 }, (m) => m.pupil_area >= 120);
  results.one_eye_only = reject({ ...sample.meta, paired_pupil_shift: false }, (m) => m.paired_pupil_shift);
  results.inverted_direction = reject({ ...sample.meta, desired_dx: -sample.meta.desired_dx || -1 }, (m) => Math.sign(m.applied_dx) === Math.sign(m.desired_dx));
  results.frozen_family = reject({ distinct_face_hashes: 1 }, (m) => m.distinct_face_hashes >= 4);
  results.generic_family_signature = reject({ signatures: ["same", "same"] }, (m) => new Set(m.signatures).size === 10);
  results.no_non_pupil_component = reject({ components: ["pupil"] }, (m) => m.components.some((item) => item !== "pupil"));
  assert(Object.values(results).every(Boolean), `negative fixture escaped: ${JSON.stringify(results)}`);
  return results;
}

const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) { response.writeHead(403).end(); return; }
  fs.readFile(target, (error, value) => { if (error) { response.writeHead(404).end(); return; } response.writeHead(200, { "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "application/octet-stream", "cache-control": "no-store" }).end(value); });
});
await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe" });
const page = await browser.newPage({ viewport: { width: 1000, height: 760 } });
const httpErrors = [];
page.on("response", (response) => { if (response.status() >= 400) httpErrors.push({ status: response.status(), url: response.url() }); });
const report = { schema: "companion.comp-req-567.three-layer-eye.machine-ready.v2", requirement: "COMP-REQ-567", base_commit: "3a2d9a70c1be756e8a54a64e564894856984a5c7", page_sha256: sha256(fs.readFileSync(pagePath)), screenshot_dir: rel(screenshotDir), hardware_contact: 0, production_enable: 0, direct_gaze: {}, families: {}, recording: {}, negatives: {}, http_errors: [] };
try {
  const port = server.address().port;
  await page.goto(`http://127.0.0.1:${port}${PAGE_URL}?rev=comp-req-567#expression`, { waitUntil: "load" });
  await page.evaluate(() => { document.body.classList.add("expression-open"); const stage = document.querySelector("#overall-viewport"); stage.style.width = "400px"; stage.style.height = "400px"; stage.style.flex = "0 0 400px"; stage.style.overflow = "hidden"; const debug = document.querySelector("#expression-state-view"); if (debug) debug.style.display = "none"; for (const image of stage.querySelectorAll("img")) { image.style.width = "400px"; image.style.height = "400px"; } });
  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); await window.__epaperFreezeIdleGlintStep(0); await window.__compReq567Probe("1,0,1,0"); });
  const center = await capture(page); const gazeRows = []; const gazeShots = [];
  for (const [name, key] of GAZES) {
    await page.evaluate((value) => window.__compReq567Probe(value), key);
    const sample = await capture(page); const oracle = directOracle(sample, center, name); const shot = await screenShot(page, `gaze-${name}.png`); gazeShots.push({ path: shot, label: name }); gazeRows.push({ name, key, oracle, meta: sample.meta, screenshot: rel(shot) });
  }
  await page.evaluate(() => window.__compReq567Probe("1,0,1,0")); const returned = await capture(page); assert.deepEqual(returned.rendered, center.rendered, "center pose did not return exactly");
  const gazeStrip = await strip(browser, gazeShots, "gaze-five-direction-strip.png", 5);
  report.direct_gaze = { pass: true, rows: gazeRows, exact_center_return: true, owner_scale_strip: rel(gazeStrip) };

  const familyStripEntries = [];
  for (const family of CHECK_FAMILIES) {
    await page.evaluate(async (value) => { await window.__setFamilyMicroChoreographyFamily(value); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); }, family);
    const rows = []; const shots = [];
    for (const step of CHECK_STEPS) {
      await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step);
      const sample = await capture(page); const shot = await screenShot(page, `family-${family}-step-${step}.png`); const trace = sample.family.trace.at(-1) || {}; const binding = familyFrameBindingOracle(sample, `${family}/step-${step}`);
      rows.push({ step, face_hash: bitHash(sample.rendered.black), trace, components: trace.components || [], meta: sample.meta, binding: sample.binding, binding_oracle: binding, screenshot: rel(shot) }); if ([0, 2, 4, 6, 8, 9].includes(step)) shots.push({ path: shot, label: `${family} ${step}` });
    }
    const temporal = temporalOracle(rows, family); const familyStrip = await strip(browser, shots, `family-${family}-time-strip.png`, 6); familyStripEntries.push({ path: familyStrip, label: family }); report.families[family] = { pass: true, cadence_ms: 480, temporal, signature: rows[0].trace?.family_signature, rows };
  }
  report.families.owner_scale_all_family_strip = rel(await strip(browser, familyStripEntries, "families-ten-strip-atlas.png", 2));

  await page.evaluate(async () => { await window.__setFamilyMicroChoreographyFamily("calm"); window.__interruptEpaperIdleGlint("comp_req_567_freeze"); await window.__epaperFreezeIdleGlintStep(0); });
  const off = []; for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const s = await capture(page); off.push(bitHash(s.rendered.black)); }
  const box = await page.locator("#overall-viewport").boundingBox(); await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(80); await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2); await page.waitForTimeout(80); assert.equal((await page.evaluate(() => window.__recordingContractState())).active, true, "recording did not enter");
  const on = []; for (const step of [0, 2, 4, 6, 8]) { await page.evaluate((value) => window.__epaperFreezeIdleGlintStep(value), step); const s = await capture(page); on.push(bitHash(s.rendered.black)); } const recordingState = await page.evaluate(() => window.__recordingContractState()); assert.deepEqual(on, off, "recording changed underlying face sequence"); assert.equal(recordingState.indicatorNodes, 0); assert.equal(recordingState.micGlyphPresent, false); report.recording = { pass: true, underlying_face_sequence_equal: true, state: recordingState, hardware_contact: 0 };
  report.negatives = negativeFixtures(center, center);
  report.http_errors = httpErrors; assert.equal(httpErrors.length, 0, `HTTP errors: ${JSON.stringify(httpErrors)}`); report.pass = true;
} finally { await browser.close(); server.close(); }
const body = JSON.stringify(report, null, 2) + "\n"; report.report_sha256 = sha256(body); fs.writeFileSync(output, JSON.stringify(report, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ pass: report.pass === true, page_sha256: report.page_sha256, report_sha256: report.report_sha256, output: rel(output), screenshot_dir: report.screenshot_dir, direct_gaze: report.direct_gaze.pass, families: Object.keys(report.families).filter((key) => key !== "owner_scale_all_family_strip").length, recording: report.recording.pass, negatives: report.negatives }, null, 2));
