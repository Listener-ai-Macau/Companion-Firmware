#!/usr/bin/env node
/* Isolated COMP-REQ-596 whole-face choreography proof. */
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-596-whole-face-choreography/index.html";
const outRel = ".cache/validation/comp-req-596-whole-face-choreography";
const outDir = path.join(root, ...outRel.split("/"));
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const sourceHashes = {
  calm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-04-calm_blink_settle.png", "CACD27828EE8197B46C5B34BFD04F271501698B2F171D37115E88E5590A7AB47"],
  curious: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-02-question_mouth_arrive.png", "F2627FA8EE0BF467DBA59551CCE55B737D42F68A21B5C3D2637B72D152CC4003"],
  delighted: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-02-delighted_mouth_arrive.png", "47BEA68C763CAFA0EDD2287443330625CBF355622F581384C7FA166DB807013E"],
  gazeCenter: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/touch-gaze-overlay-149.png", "ADFB327C69DA45A3BCD5B6B24E8757D5BE27FCCB590B687DEB8E77E0EF4ADD6A"],
  gazeCalm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/touch-gaze-overlay-147.png", "F5265695DF89355A25EFB054922B124946831D82232A8AB625C8019392297619"],
  gazeCurious: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/touch-gaze-overlay-126.png", "AAB6651CE881A75AF5EBDAC5B2A853DC2641570D926EB65392FDDB336B3B652A"],
  gazeDelighted: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/touch-gaze-overlay-186.png", "22329B042CBCB2608B34FE135EF65AC8AD8E187004ADE539B162472313256BE4"]
};
const livePage = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const livePageExpected = "0272365C090662F888ED664EA13A57BD164C87863D944439BF0EBD1BB47EF4D4";

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
  const page = await browser.newPage({ viewport: { width: 800, height: 390 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  const response = await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => window.__compReq596Ready === true, null, { timeout: 15000 });

  const browserAudit = await page.evaluate(() => {
    const names = ["calm", "curious", "delighted"];
    const regions = {
      calm: {
        eyes: [[40, 82, 122, 50]],
        brow: [[42, 54, 33, 19], [124, 54, 34, 19]],
        cheek: [[29, 127, 23, 18], [148, 126, 24, 18]],
        nose: [[90, 117, 20, 14]],
        mouth: [[82, 128, 36, 18]]
      },
      curious: {
        eyes: [[41, 106, 121, 50]],
        brow: [[53, 63, 38, 24], [121, 82, 32, 18]],
        cheek: [[28, 150, 25, 18], [149, 147, 25, 18]],
        nose: [[90, 141, 20, 15]],
        mouth: [[89, 153, 25, 21]]
      },
      delighted: {
        eyes: [[41, 86, 121, 50]],
        brow: [[41, 51, 37, 22], [123, 50, 35, 22]],
        cheek: [[29, 129, 25, 19], [148, 129, 25, 19]],
        nose: [[90, 121, 20, 15]],
        mouth: [[83, 130, 35, 21]]
      }
    };
    const inside = (x, y, boxes) => boxes.some(([bx, by, width, height]) => x >= bx && x < bx + width && y >= by && y < by + height);
    const capture = step => {
      const state = window.__compReq596FreezeStep(step);
      const frames = {};
      for (const name of names) {
        const canvas = document.querySelector(`#${name}`);
        const data = new Uint8Array(canvas.getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data);
        let nonBinary = 0;
        for (let index = 0; index < data.length; index += 4) {
          if (![0, 255].includes(data[index]) || data[index] !== data[index + 1] || data[index] !== data[index + 2] || data[index + 3] !== 255) nonBinary++;
        }
        frames[name] = { data, signature: canvas.toDataURL(), nonBinary };
      }
      return { state, frames };
    };
    const diff = (a, b) => {
      const points = [];
      for (let pixel = 0; pixel < 40000; pixel++) {
        const at = pixel * 4;
        if (a[at] !== b[at] || a[at + 1] !== b[at + 1] || a[at + 2] !== b[at + 2] || a[at + 3] !== b[at + 3]) {
          points.push([pixel % 200, Math.floor(pixel / 200)]);
        }
      }
      return points;
    };
    const first = Object.fromEntries([0, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(value => [value, capture(value)]));
    const second = Object.fromEntries([0, 3, 4, 5, 6, 7, 8, 9, 10, 11].map(value => [value, capture(value)]));
    const motifs = {};
    for (const name of names) {
      const hold = first[0].frames[name];
      const anticipate = first[3].frames[name];
      const accent = first[4].frames[name];
      const accentHold = first[5].frames[name];
      const settle = first[6].frames[name];
      const gazeDiff = diff(hold.data, anticipate.data);
      const faceDiff = diff(anticipate.data, accent.data);
      const allRegions = Object.values(regions[name]).flat();
      motifs[name] = {
        signatures: Object.fromEntries(Object.entries(first).map(([key, value]) => [key, value.frames[name].signature])),
        non_binary_pixels: Object.values(first).reduce((sum, value) => sum + value.frames[name].nonBinary, 0),
        gaze_diff_pixels: gazeDiff.length,
        gaze_diff_outside_eyes: gazeDiff.filter(([x, y]) => !inside(x, y, regions[name].eyes)).length,
        accent_diff_pixels: faceDiff.length,
        accent_lane_hits: Object.fromEntries(["brow", "cheek", "nose", "mouth"].map(lane => [
          lane,
          faceDiff.filter(([x, y]) => inside(x, y, regions[name][lane])).length
        ])),
        accent_diff_outside_registered_union: faceDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
        accent_hold_exact: accent.signature === accentHold.signature,
        settle_exact: hold.signature === settle.signature,
        quiet_exact: [7, 8, 9, 10, 11].every(value => first[value].frames[name].signature === hold.signature),
        deterministic_replay: Object.keys(first).every(value => first[value].frames[name].signature === second[value].frames[name].signature)
      };
    }
    const holdSignatures = Object.fromEntries(names.map(name => [name, first[0].frames[name].signature]));
    capture(4);
    window.__compReq596Interrupt("machine_probe");
    const interrupted = Object.fromEntries(names.map(name => [name, document.querySelector(`#${name}`).toDataURL()]));
    window.__compReq596Restore();
    const restored = Object.fromEntries(names.map(name => [name, document.querySelector(`#${name}`).toDataURL()]));
    for (let index = 0; index < 60; index++) capture(index % 12);
    const snapshot = window.__compReq596Snapshot();
    const contract = window.__compReq596Contract();
    return {
      contract,
      motifs,
      phase_sequence: [first[0].state.phase, first[3].state.phase, first[4].state.phase, first[6].state.phase],
      interruption_to_hold: names.every(name => interrupted[name] === holdSignatures[name]),
      restore_to_hold: names.every(name => restored[name] === holdSignatures[name]),
      stale_replay: snapshot.trace.some(item => item.stale_replay === true),
      trace_length: snapshot.trace.length,
      canvas_count: document.querySelectorAll("canvas[width='200'][height='200']").length,
      css_animated_nodes: [...document.querySelectorAll("*")].filter(node => {
        const style = getComputedStyle(node);
        return style.animationName !== "none" || style.transitionDuration.split(",").some(value => parseFloat(value) > 0);
      }).length
    };
  });

  await page.evaluate(() => window.__compReq596FreezeStep(4));
  await page.screenshot({ path: path.join(outDir, "whole-face-choreography.png"), fullPage: true });

  const pageSource = fs.readFileSync(path.join(root, ...pageRel.split("/")), "utf8");
  const sources = Object.fromEntries(Object.entries(sourceHashes).map(([name, [rel, expected]]) => {
    const actual = sha(fs.readFileSync(path.join(root, ...rel.split("/"))));
    return [name, { path: rel, expected_sha256: expected, actual_sha256: actual, match: actual === expected }];
  }));
  const livePageActual = sha(fs.readFileSync(path.join(root, ...livePage.split("/"))));
  const motifChecks = Object.values(browserAudit.motifs);
  const checks = {
    page_http_200: response?.status() === 200,
    source_hashes_match: Object.values(sources).every(item => item.match),
    strict_1bpp: motifChecks.every(item => item.non_binary_pixels === 0),
    phase_order_exact: JSON.stringify(browserAudit.phase_sequence) === JSON.stringify(["hold", "anticipate", "accent", "settle"]),
    three_changed_frames: browserAudit.contract.changed_frames_per_phrase === 3,
    gaze_leads_inside_eyes_only: motifChecks.every(item => item.gaze_diff_pixels > 0 && item.gaze_diff_outside_eyes === 0),
    whole_face_lanes_participate: motifChecks.every(item => Object.values(item.accent_lane_hits).every(count => count > 0)),
    changed_pixels_inside_registered_union: motifChecks.every(item => item.accent_diff_outside_registered_union === 0),
    accent_hold_no_refresh: motifChecks.every(item => item.accent_hold_exact),
    exact_settle_return: motifChecks.every(item => item.settle_exact),
    five_quiet_slots_after_settle: browserAudit.contract.quiet_steps_after_settle === 5 && motifChecks.every(item => item.quiet_exact),
    deterministic_two_run_replay: motifChecks.every(item => item.deterministic_replay),
    component_step_at_most_2px: Object.values(browserAudit.contract.motifs).every(item => item.max_component_step_px <= 2),
    nose_has_no_independent_timer: Object.values(browserAudit.contract.motifs).every(item => item.nose_timer === false),
    sole_scheduler_writer: browserAudit.contract.scheduler_count === 1 && browserAudit.contract.writer_count === 1,
    fixed_trace_capacity: browserAudit.contract.trace_capacity === 48 && browserAudit.trace_length <= 48,
    interrupt_restore_exact: browserAudit.interruption_to_hold && browserAudit.restore_to_hold && !browserAudit.stale_replay,
    no_css_animation: browserAudit.css_animated_nodes === 0 && !pageSource.includes("Math.random"),
    three_isolated_200x200_previews: browserAudit.canvas_count === 3,
    browser_errors_zero: errors.length === 0,
    live_page_unchanged: livePageActual === livePageExpected
  };
  const result = {
    schema: "companion.comp_req_596.whole_face_choreography.verification.v1",
    status: Object.values(checks).every(Boolean) ? "PASS_OWNER_REVIEW_READY" : "NO_GO",
    page: { path: pageRel, sha256: sha(fs.readFileSync(path.join(root, ...pageRel.split("/")))) },
    research: {
      path: "docs/validation/companion-whole-face-choreography-research-20260725.md",
      sha256: sha(fs.readFileSync(path.join(root, "docs/validation/companion-whole-face-choreography-research-20260725.md")))
    },
    sources,
    live_page: { path: livePage, expected_sha256: livePageExpected, actual_sha256: livePageActual },
    browser_audit: browserAudit,
    checks,
    errors,
    screenshot: `${outRel}/whole-face-choreography.png`
  };
  const resultPath = path.join(outDir, "verification.json");
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({
    status: result.status,
    evidence_sha256: sha(fs.readFileSync(resultPath)),
    page_sha256: result.page.sha256,
    checks
  }, null, 2));
  if (result.status !== "PASS_OWNER_REVIEW_READY") process.exitCode = 2;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
