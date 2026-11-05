#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-603-premium-face-blink/index.html";
const outRel = ".cache/validation/comp-req-603-premium-face-blink";
const outDir = path.join(root, ...outRel.split("/"));
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const packFrame = signature => {
  const packed = Buffer.alloc(5000);
  for (let index = 0; index < 40000; index += 1) {
    if (signature[index] === "1") packed[index >> 3] |= 0x80 >> (index & 7);
  }
  return packed;
};
const sourceHashes = {
  calm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-04-calm_blink_settle.png", "CACD27828EE8197B46C5B34BFD04F271501698B2F171D37115E88E5590A7AB47"],
  curious: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-02-question_mouth_arrive.png", "F2627FA8EE0BF467DBA59551CCE55B737D42F68A21B5C3D2637B72D152CC4003"],
  delighted: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-02-delighted_mouth_arrive.png", "47BEA68C763CAFA0EDD2287443330625CBF355622F581384C7FA166DB807013E"],
  blink_closed: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-02-calm_blink_closed.png", "69B342A719613F7B406C45DF7375C4FC680B59FEE63FB449F1CF0C6AFADEDBFA"]
};
const livePage = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const livePageExpected = "0272365C090662F888ED664EA13A57BD164C87863D944439BF0EBD1BB47EF4D4";
const protectedFiles = {
  driver: ["app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c", "F52A7E853BFE2E66680F08420941265CFF163FB579B2D3870128FC72C79E035F"],
  frame_header: ["app/companion_pendant/epaper/companion_r7_locked_v9_frames.h", "9571CF9F896B6C14451BAA7348CB717643B4963AE834B0A554E0C2ED2C7E8D35"],
  owner_acceptance: ["docs/validation/companion-pet-special-system-owner-acceptance-20260717.json", "8A3BDF4BD1254B0D0F4DE13A7F293C3D74587C800339ABD4C61FEB0B7737E227"]
};

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
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 15000 });

  const audit = await page.evaluate(() => {
    const families = ["calm", "curious", "delighted"];
    const phases = ["hold", "orient", "anticipate", "accent", "follow", "settle"];
    const boxes = {
      calm: {
        eyes: [[40, 82, 38, 51], [123, 82, 39, 51]],
        brow: [[42, 56, 32, 17], [124, 56, 33, 17]],
        cheek: [[30, 127, 24, 19], [148, 126, 25, 19]],
        nose: [[90, 116, 20, 17]],
        mouth: [[82, 129, 36, 19]]
      },
      curious: {
        eyes: [[41, 106, 38, 51], [124, 106, 39, 51]],
        brow: [[53, 64, 39, 23], [121, 83, 34, 17]],
        cheek: [[29, 150, 25, 19], [149, 147, 25, 19]],
        nose: [[90, 140, 20, 17]],
        mouth: [[89, 153, 26, 22]]
      },
      delighted: {
        eyes: [[41, 86, 38, 51], [124, 86, 39, 51]],
        brow: [[41, 50, 39, 23], [123, 49, 38, 23]],
        cheek: [[29, 128, 25, 21], [148, 128, 25, 21]],
        nose: [[90, 120, 20, 17]],
        mouth: [[83, 130, 36, 21]]
      }
    };
    const inside = (x, y, regions) => regions.some(([bx, by, width, height]) =>
      x >= bx && x < bx + width && y >= by && y < by + height
    );
    const pixels = () => new Uint8Array(
      document.querySelector("#face").getContext("2d", { willReadFrequently: true }).getImageData(0, 0, 200, 200).data
    );
    const signature = data => {
      let value = "";
      for (let index = 0; index < data.length; index += 4) value += data[index] < 128 ? "1" : "0";
      return value;
    };
    const blackComponentCount = (data, ignoredBoxes) => {
      const seen = new Set();
      let count = 0;
      for (let y = 0; y < 200; y += 1) {
        for (let x = 0; x < 200; x += 1) {
          const key = y * 200 + x;
          if (seen.has(key) || inside(x, y, ignoredBoxes) || data[key * 4] >= 128) continue;
          count += 1;
          const queue = [[x, y]];
          seen.add(key);
          while (queue.length) {
            const [cx, cy] = queue.shift();
            for (const [nx, ny] of [[cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1]]) {
              if (nx < 0 || nx >= 200 || ny < 0 || ny >= 200) continue;
              const next = ny * 200 + nx;
              if (!seen.has(next) && !inside(nx, ny, ignoredBoxes) && data[next * 4] < 128) {
                seen.add(next);
                queue.push([nx, ny]);
              }
            }
          }
        }
      }
      return count;
    };
    const components = (data, box) => {
      const [bx, by, width, height] = box;
      const white = (x, y) => data[(y * 200 + x) * 4] > 127;
      const seen = new Set();
      const enclosed = [];
      for (let y = by; y < by + height; y += 1) {
        for (let x = bx; x < bx + width; x += 1) {
          const key = y * 200 + x;
          if (seen.has(key) || !white(x, y)) continue;
          const queue = [[x, y]];
          const points = [];
          let border = false;
          seen.add(key);
          while (queue.length) {
            const [cx, cy] = queue.shift();
            points.push([cx, cy]);
            if (cx === bx || cy === by || cx === bx + width - 1 || cy === by + height - 1) border = true;
            for (const [nx, ny] of [[cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1]]) {
              if (nx < bx || nx >= bx + width || ny < by || ny >= by + height) continue;
              const next = ny * 200 + nx;
              if (!seen.has(next) && white(nx, ny)) {
                seen.add(next);
                queue.push([nx, ny]);
              }
            }
          }
          if (!border) enclosed.push(points);
        }
      }
      return enclosed.sort((a, b) => b.length - a.length);
    };
    const blackComponentsInBox = (data, box) => {
      const [bx, by, width, height] = box;
      const seen = new Set();
      const found = [];
      for (let y = by; y < by + height; y += 1) {
        for (let x = bx; x < bx + width; x += 1) {
          const key = y * 200 + x;
          if (seen.has(key) || data[key * 4] >= 128) continue;
          const queue = [[x, y]];
          const points = [];
          seen.add(key);
          while (queue.length) {
            const [cx, cy] = queue.shift();
            points.push([cx, cy]);
            for (const [nx, ny] of [[cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1]]) {
              if (nx < bx || nx >= bx + width || ny < by || ny >= by + height) continue;
              const next = ny * 200 + nx;
              if (!seen.has(next) && data[next * 4] < 128) {
                seen.add(next);
                queue.push([nx, ny]);
              }
            }
          }
          found.push(points);
        }
      }
      return found.sort((a, b) => b.length - a.length);
    };
    const filledEyeSignature = (data, box) => {
      const copy = new Uint8Array(data);
      components(data, box).flat().forEach(([x, y]) => {
        const at = (y * 200 + x) * 4;
        copy[at] = copy[at + 1] = copy[at + 2] = 0;
      });
      const [bx, by, width, height] = box;
      const seen = new Set();
      const blackComponents = [];
      for (let y = by; y < by + height; y += 1) {
        for (let x = bx; x < bx + width; x += 1) {
          const key = y * 200 + x;
          if (seen.has(key) || copy[key * 4] >= 128) continue;
          const queue = [[x, y]];
          const points = [];
          seen.add(key);
          while (queue.length) {
            const [cx, cy] = queue.shift();
            points.push(cy * 200 + cx);
            for (const [nx, ny] of [[cx - 1, cy], [cx + 1, cy], [cx, cy - 1], [cx, cy + 1]]) {
              if (nx < bx || nx >= bx + width || ny < by || ny >= by + height) continue;
              const next = ny * 200 + nx;
              if (!seen.has(next) && copy[next * 4] < 128) {
                seen.add(next);
                queue.push([nx, ny]);
              }
            }
          }
          blackComponents.push(points.sort((a, b) => a - b));
        }
      }
      blackComponents.sort((a, b) => b.length - a.length);
      return blackComponents[0]?.join(",") || "";
    };
    const diff = (a, b) => {
      const points = [];
      for (let pixel = 0; pixel < 40000; pixel += 1) {
        const at = pixel * 4;
        if (a[at] !== b[at]) points.push([pixel % 200, Math.floor(pixel / 200)]);
      }
      return points;
    };
    const capture = (family, phrase, phase) => {
      window.__compReq599Freeze(family, phrase, phase);
      const data = pixels();
      let nonBinary = 0;
      for (let at = 0; at < data.length; at += 4) {
        if (![0, 255].includes(data[at]) || data[at] !== data[at + 1] || data[at] !== data[at + 2] || data[at + 3] !== 255) nonBinary += 1;
      }
      return {
        data,
        signature: signature(data),
        nonBinary,
        blackComponents: blackComponentCount(data, boxes[family].eyes),
        mouthComponents: blackComponentsInBox(data, boxes[family].mouth[0]).filter(component => component.length > 60)
      };
    };
    const result = {};
    for (const family of families) {
      const phraseResults = [];
      const hold = capture(family, 0, "hold");
      const holdEyeBodies = boxes[family].eyes.map(box => filledEyeSignature(hold.data, box));
      const holdHoleAreas = boxes[family].eyes.map(box => components(hold.data, box).map(item => item.length));
      for (let phrase = 0; phrase < 3; phrase += 1) {
        const frames = Object.fromEntries(phases.map(phase => [phase, capture(family, phrase, phase)]));
        const eyeAudit = {};
        for (const phase of phases) {
          eyeAudit[phase] = boxes[family].eyes.map((box, eye) => {
            const holes = components(frames[phase].data, box);
            return {
              count: holes.length,
              areas: holes.map(item => item.length),
              no_fragment: holes.every(item => item.length > 8),
              body_exact: filledEyeSignature(frames[phase].data, box) === holdEyeBodies[eye],
              areas_exact: JSON.stringify(holes.map(item => item.length)) === JSON.stringify(holdHoleAreas[eye])
            };
          });
        }
        const gazeDiff = diff(frames.hold.data, frames.orient.data);
        const browDiff = diff(frames.orient.data, frames.anticipate.data);
        const lowerDiff = diff(frames.anticipate.data, frames.accent.data);
        const followDiff = diff(frames.accent.data, frames.follow.data);
        const allRegions = Object.values(boxes[family]).flat();
        phraseResults.push({
          signatures: Object.fromEntries(phases.map(phase => [phase, frames[phase].signature])),
          non_binary: Object.values(frames).reduce((sum, frame) => sum + frame.nonBinary, 0),
          eye_audit: eyeAudit,
          gaze_pixels: gazeDiff.length,
          gaze_outside_eyes: gazeDiff.filter(([x, y]) => !inside(x, y, boxes[family].eyes)).length,
          brow_pixels: browDiff.filter(([x, y]) => inside(x, y, boxes[family].brow)).length,
          brow_outside_registered_union: browDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
          lower_lane_hits: Object.fromEntries(["cheek", "nose", "mouth"].map(lane => [
            lane,
            lowerDiff.filter(([x, y]) => inside(x, y, boxes[family][lane])).length
          ])),
          lower_outside_registered_union: lowerDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
          follow_pixels: followDiff.length,
          follow_outside_registered_union: followDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
          settle_exact: frames.settle.signature === frames.hold.signature,
          mouth_connected: phases.every(phase => frames[phase].mouthComponents.length === 1),
          mouth_pixel_count_exact: phases.every(phase =>
            frames[phase].mouthComponents[0]?.length === frames.hold.mouthComponents[0]?.length
          ),
          component_topology_exact: phases.every(phase => frames[phase].blackComponents === frames.hold.blackComponents),
          black_component_counts: Object.fromEntries(phases.map(phase => [phase, frames[phase].blackComponents]))
        });
      }
      const replayA = phraseResults.map(item => ({ ...item.signatures }));
      const replayB = [0, 1, 2].map(phrase => Object.fromEntries(phases.map(phase => [
        phase,
        capture(family, phrase, phase).signature
      ])));
      result[family] = {
        hold_hole_areas: holdHoleAreas,
        phrases: phraseResults,
        deterministic_replay: JSON.stringify(replayA) === JSON.stringify(replayB),
        distinct_orients: new Set(phraseResults.map(item => item.signatures.orient)).size,
        distinct_accents: new Set(phraseResults.map(item => item.signatures.accent)).size,
        distinct_follows: new Set(phraseResults.map(item => item.signatures.follow)).size
      };
    }
    window.__compReq599Freeze("calm", 1, "accent");
    window.__compReq599Interrupt("machine_probe");
    const interrupted = signature(pixels());
    const calmHold = capture("calm", 0, "hold").signature;
    window.__compReq599Restore();
    const restored = signature(pixels());
    const blinkClosed = (() => {
      window.__compReq603FreezeBlink("closed");
      return signature(pixels());
    })();
    const blinkOpen = (() => {
      window.__compReq603FreezeBlink("open");
      return signature(pixels());
    })();
    for (let index = 0; index < 80; index += 1) capture("calm", index % 3, phases[index % phases.length]);
    const snapshot = window.__compReq599Snapshot();
    return {
      contract: window.__compReq599Contract(),
      families: result,
      interruption_to_hold: interrupted === calmHold,
      restore_to_hold: restored === calmHold,
      blink: {
        closed_signature: blinkClosed,
        open_signature: blinkOpen,
        closed_differs_from_open: blinkClosed !== blinkOpen,
        exact_open_return: blinkOpen === calmHold
      },
      stale_replay: snapshot.trace.some(item => item.stale_replay === true),
      trace_length: snapshot.trace.length,
      canvas_count: document.querySelectorAll("canvas[width='200'][height='200']").length,
      css_animated_nodes: [...document.querySelectorAll("*")].filter(node => {
        const style = getComputedStyle(node);
        return style.animationName !== "none" || style.transitionDuration.split(",").some(value => parseFloat(value) > 0);
      }).length
    };
  });

  await page.reload({ waitUntil: "load" });
  await page.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 15000 });
  const runtimeAudit = await page.evaluate(async () => {
    const canvas = document.querySelector("#face");
    const changes = [];
    const startedAt = performance.now();
    let previous = "";
    await new Promise(resolve => {
      const timer = setInterval(() => {
        const signature = canvas.toDataURL();
        if (signature !== previous) {
          const snapshot = window.__compReq599Snapshot();
          changes.push({
            elapsed_ms: performance.now() - startedAt,
            signature,
            tick: snapshot.tick,
            beat: document.querySelector("#beatLabel").textContent
          });
          previous = signature;
        }
        if (performance.now() - startedAt >= 30000) {
          clearInterval(timer);
          resolve();
        }
      }, 60);
    });
    return { duration_ms: performance.now() - startedAt, changes, trace: window.__compReq599Snapshot().trace };
  });

  for (const family of ["calm", "curious", "delighted"]) {
    await page.evaluate(name => window.__compReq599Freeze(name, 1, "accent"), family);
    await page.screenshot({ path: path.join(outDir, `${family}-accent.png`), fullPage: true });
  }
  await page.evaluate(() => window.__compReq599Freeze("calm", 0, "hold"));
  await page.screenshot({ path: path.join(outDir, "calm-hold.png"), fullPage: true });
  await page.evaluate(() => {
    const atlas = document.createElement("canvas");
    atlas.id = "clipAtlas";
    atlas.width = 600;
    atlas.height = 600;
    atlas.style.width = "600px";
    atlas.style.height = "600px";
    atlas.style.imageRendering = "pixelated";
    const atlasContext = atlas.getContext("2d");
    ["calm", "curious", "delighted"].forEach((family, row) => {
      [0, 1, 2].forEach(phrase => {
        window.__compReq599Freeze(family, phrase, "accent");
        atlasContext.drawImage(document.querySelector("#face"), phrase * 200, row * 200);
      });
    });
    const strip = document.createElement("canvas");
    strip.id = "poseStrip";
    strip.width = 1200;
    strip.height = 600;
    strip.style.width = "1200px";
    strip.style.height = "600px";
    strip.style.imageRendering = "pixelated";
    const stripContext = strip.getContext("2d");
    ["calm", "curious", "delighted"].forEach((family, row) => {
      ["hold", "orient", "anticipate", "accent", "follow", "settle"].forEach((phase, column) => {
        window.__compReq599Freeze(family, 1, phase);
        stripContext.drawImage(document.querySelector("#face"), column * 200, row * 200);
      });
    });
    const blinkStrip = document.createElement("canvas");
    blinkStrip.id = "blinkStrip";
    blinkStrip.width = 600;
    blinkStrip.height = 200;
    blinkStrip.style.width = "600px";
    blinkStrip.style.height = "200px";
    blinkStrip.style.imageRendering = "pixelated";
    const blinkContext = blinkStrip.getContext("2d");
    window.__compReq599Freeze("calm", 0, "hold");
    blinkContext.drawImage(document.querySelector("#face"), 0, 0);
    window.__compReq603FreezeBlink("closed");
    blinkContext.drawImage(document.querySelector("#face"), 200, 0);
    window.__compReq603FreezeBlink("open");
    blinkContext.drawImage(document.querySelector("#face"), 400, 0);
    document.body.replaceChildren(strip, atlas, blinkStrip);
  });
  await page.locator("#poseStrip").screenshot({ path: path.join(outDir, "six-pose-motion-atlas.png") });
  await page.locator("#clipAtlas").screenshot({ path: path.join(outDir, "nine-clip-accent-atlas.png") });
  await page.locator("#blinkStrip").screenshot({ path: path.join(outDir, "blink-strip.png") });

  const pagePath = path.join(root, ...pageRel.split("/"));
  const pageSource = fs.readFileSync(pagePath, "utf8");
  const sources = Object.fromEntries(Object.entries(sourceHashes).map(([name, [rel, expected]]) => {
    const actual = sha(fs.readFileSync(path.join(root, ...rel.split("/"))));
    return [name, { path: rel, expected_sha256: expected, actual_sha256: actual, match: actual === expected }];
  }));
  const protectedAudit = Object.fromEntries(Object.entries(protectedFiles).map(([name, [rel, expected]]) => {
    const actual = sha(fs.readFileSync(path.join(root, ...rel.split("/"))));
    return [name, { path: rel, expected_sha256: expected, actual_sha256: actual, match: actual === expected }];
  }));
  const framePlanEntries = [];
  for (const [family, familyAudit] of Object.entries(audit.families)) {
    familyAudit.phrases.forEach((phrase, phraseIndex) => {
      for (const [phase, signature] of Object.entries(phrase.signatures)) {
        const payload = packFrame(signature);
        framePlanEntries.push({
          id: `${family}.${phraseIndex}.${phase}`,
          family,
          phrase: phraseIndex,
          phase,
          dwell_commits: 1,
          cadence_ms: 480,
          payload_bytes: payload.length,
          framebuffer_sha256: sha(payload),
          payload
        });
      }
    });
  }
  for (const phase of ["closed", "open"]) {
    const payload = packFrame(audit.blink[`${phase}_signature`]);
    framePlanEntries.push({
      id: `calm.blink.${phase}`,
      family: "calm",
      phrase: null,
      phase: `blink_${phase}`,
      dwell_commits: 1,
      cadence_ms: 480,
      payload_bytes: payload.length,
      framebuffer_sha256: sha(payload),
      payload
    });
  }
  let payloadOffset = 0;
  const wb55Payload = Buffer.concat(framePlanEntries.map(entry => entry.payload));
  const framePlan = {
    schema: "companion.canonical_1bit_frame_plan.comp_req_603_604_605.v1",
    pixel_format: "row_major_msb_first_1_is_black",
    width: 200,
    height: 200,
    bytes_per_frame: 5000,
    cadence_ms: 480,
    entries: framePlanEntries.map(({ payload, ...entry }) => {
      const result = { ...entry, payload_offset: payloadOffset };
      payloadOffset += payload.length;
      return result;
    }),
    wb55_payload_sha256: sha(wb55Payload)
  };
  const framePlanPath = path.join(outDir, "canonical-frame-plan.json");
  const wb55PayloadPath = path.join(outDir, "wb55-frame-plan.bin");
  fs.writeFileSync(framePlanPath, `${JSON.stringify(framePlan, null, 2)}\n`);
  fs.writeFileSync(wb55PayloadPath, wb55Payload);
  const framePlanParity = framePlan.entries.every(entry => {
    const payload = wb55Payload.subarray(entry.payload_offset, entry.payload_offset + entry.payload_bytes);
    return payload.length === 5000 && sha(payload) === entry.framebuffer_sha256;
  });
  const families = Object.values(audit.families);
  const phrases = families.flatMap(family => family.phrases);
  const eyeFrames = phrases.flatMap(phrase => Object.values(phrase.eye_audit).flat());
  const contractFamilies = Object.values(audit.contract.families);
  const runtimeChanges = runtimeAudit.changes;
  const runtimeGaps = runtimeChanges.slice(1).map((item, index) => ({
    elapsed_ms: item.elapsed_ms - runtimeChanges[index].elapsed_ms,
    tick_gap: item.tick - runtimeChanges[index].tick
  }));
  const runtimePhaseOrder = runtimeChanges.slice(0, 6).map(item => item.beat.split(" · ").at(-1));
  const runtimeBlinkIndex = runtimeChanges.findIndex(item => item.beat === "自然眨眼");
  const runtimeCommits = runtimeAudit.trace.filter(item => item.type === "commit");
  const checks = {
    page_http_200: response?.status() === 200,
    source_hashes_match: Object.values(sources).every(item => item.match),
    strict_1bpp: phrases.every(item => item.non_binary === 0),
    exactly_two_clean_highlights_per_eye: eyeFrames.every(item =>
      item.count === 2 && item.no_fragment && item.body_exact && item.areas_exact
    ),
    outer_eye_shell_invariant: eyeFrames.every(item => item.body_exact),
    gaze_leads_inside_eyes_only: phrases.every(item => item.gaze_pixels > 0 && item.gaze_outside_eyes === 0),
    brow_answers_after_gaze: phrases.every(item => item.brow_pixels > 0 && item.brow_outside_registered_union === 0),
    lower_face_completes_accent: phrases.every(item => Object.values(item.lower_lane_hits).every(count => count > 0)),
    follow_through_is_distinct: phrases.every(item => item.follow_pixels > 0),
    every_mouth_pose_connected: phrases.every(item => item.mouth_connected),
    mouth_source_pixel_mass_preserved: phrases.every(item => item.mouth_pixel_count_exact),
    feature_components_never_merge_or_split: phrases.every(item => item.component_topology_exact),
    registered_union_only: phrases.every(item =>
      item.lower_outside_registered_union === 0 && item.follow_outside_registered_union === 0
    ),
    exact_settle_return: phrases.every(item => item.settle_exact),
    three_distinct_clips_per_family: families.every(item =>
      item.distinct_orients === 3 && item.distinct_accents === 3 && item.distinct_follows === 3
    ),
    deterministic_pixel_replay: families.every(item => item.deterministic_replay),
    non_repeating_selector: contractFamilies.every(item =>
      item.phrase_count >= 3 && item.phrase_order.every((value, index, order) => index === 0 || value !== order[index - 1])
    ),
    authored_quiet_range: contractFamilies.every(item =>
      new Set(item.quiet_slots).size >= 4 && item.quiet_slots.every(value => value >= 4 && value <= 7)
    ),
    oled_like_authored_amplitude: contractFamilies.every(item =>
      item.displacement_profiles.every(profile =>
        Math.max(...profile.gaze.map(Math.abs)) >= 2 &&
        Math.max(...profile.gaze.map(Math.abs)) <= 4 &&
        profile.brow.every(value => Math.abs(value) <= 2) &&
        profile.cheek.every(value => Math.abs(value) <= 2) &&
        Math.max(...profile.mouth.map(Math.abs)) >= 1 &&
        Math.max(...profile.mouth.map(Math.abs)) <= 2 &&
        Math.abs(profile.nose) <= 2
      ) &&
      Math.max(...item.displacement_profiles.flatMap(profile => profile.gaze.map(value => Math.abs(value)))) >= 3 &&
      item.displacement_profiles.some(profile => profile.brow.some(value => Math.abs(value) === 2)) &&
      item.displacement_profiles.some(profile => profile.mouth.some(value => Math.abs(value) >= 1))
    ) && contractFamilies.some(item =>
      item.displacement_profiles.some(profile => profile.mouth.some(value => Math.abs(value) === 2))
    ),
    physical_cadence_and_five_changes: audit.contract.cadence_ms === 480 &&
      audit.contract.changed_commits_per_phrase === 5 &&
      audit.contract.first_orient_slots === 1,
    actual_first_change_within_960ms: runtimeChanges.length > 1 &&
      runtimeChanges[1].elapsed_ms >= 400 && runtimeChanges[1].elapsed_ms <= 960,
    actual_runtime_phase_order: JSON.stringify(runtimePhaseOrder) ===
      JSON.stringify(["安静陪伴", "目光发现", "情绪预备", "整脸回应", "自然回弹", "自然落稳"]),
    actual_runtime_two_complete_clips: runtimeChanges.filter(item => item.beat.endsWith("自然落稳")).length >= 2,
    actual_runtime_ge_30_seconds: runtimeAudit.duration_ms >= 30000,
    actual_runtime_contains_natural_blink: runtimeBlinkIndex >= 0 &&
      runtimeChanges[runtimeBlinkIndex + 1]?.beat === "安静陪伴",
    blink_source_backed_and_exact_open: audit.blink.closed_differs_from_open && audit.blink.exact_open_return,
    blink_interval_matches_lower_cadence: audit.contract.blink.interval_ms.every(value =>
      value >= 8000 && value <= 20000 && value % audit.contract.cadence_ms === 0
    ) && audit.contract.blink.closed_commits === 1 && audit.contract.blink.exact_open_next_commit,
    actual_runtime_max_dwell: runtimeGaps.length > 0 &&
      Math.max(...runtimeGaps.map(item => item.tick_gap)) <= 7 &&
      Math.max(...runtimeGaps.map(item => item.elapsed_ms)) <= 3500,
    sole_scheduler_writer: audit.contract.scheduler_count === 1 && audit.contract.writer_count === 1,
    unchanged_frame_never_requests_lower_refresh: runtimeCommits.length > 0 &&
      runtimeCommits.every(item => item.lower_refresh_requested === item.changed),
    bounded_trace: audit.contract.trace_capacity === 64 && audit.trace_length <= 64,
    interruption_restore_exact: audit.interruption_to_hold && audit.restore_to_hold && !audit.stale_replay,
    no_pixel_noise_or_block_translation: !pageSource.includes("Math.random") &&
      !pageSource.includes("shiftRegion") &&
      !/drawImage\\s*\\([^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^)]+\\)/.test(pageSource),
    no_css_animation: audit.css_animated_nodes === 0,
    one_composed_200x200_face: audit.canvas_count === 1,
    canonical_browser_wb55_payload_parity: framePlanParity &&
      framePlan.entries.every(entry => entry.payload_bytes === 5000 && entry.cadence_ms === 480),
    protected_files_unchanged: Object.values(protectedAudit).every(item => item.match),
    browser_errors_zero: errors.length === 0,
    live_page_unchanged: sha(fs.readFileSync(path.join(root, ...livePage.split("/")))) === livePageExpected
  };
  const result = {
    schema: "companion.comp_req_603_604_605.premium_face_blink.verification.v1",
    status: Object.values(checks).every(Boolean) ? "PASS_OWNER_REVIEW_READY" : "NO_GO",
    page: { path: pageRel, sha256: sha(fs.readFileSync(pagePath)) },
    research: {
      path: "docs/validation/companion-whole-face-choreography-research-20260725.md",
      sha256: sha(fs.readFileSync(path.join(root, "docs/validation/companion-whole-face-choreography-research-20260725.md")))
    },
    sources,
    protected: protectedAudit,
    canonical_frame_plan: {
      path: `${outRel}/canonical-frame-plan.json`,
      sha256: sha(fs.readFileSync(framePlanPath)),
      entries: framePlan.entries.length,
      bytes_per_frame: framePlan.bytes_per_frame,
      wb55_payload_path: `${outRel}/wb55-frame-plan.bin`,
      wb55_payload_bytes: wb55Payload.length,
      wb55_payload_sha256: sha(wb55Payload)
    },
    live_page: { path: livePage, expected_sha256: livePageExpected },
    audit,
    runtime_audit: {
      duration_ms: runtimeAudit.duration_ms,
      changes: runtimeChanges.map(({ signature, ...item }) => item),
      first_change_latency_ms: runtimeChanges[1]?.elapsed_ms,
      max_elapsed_gap_ms: runtimeGaps.length ? Math.max(...runtimeGaps.map(item => item.elapsed_ms)) : null,
      max_tick_gap: runtimeGaps.length ? Math.max(...runtimeGaps.map(item => item.tick_gap)) : null,
      complete_clips: runtimeChanges.filter(item => item.beat.endsWith("自然落稳")).length,
      complete_blinks: runtimeChanges.filter(item => item.beat === "自然眨眼").length
    },
    checks,
    errors,
    screenshots: ["calm-hold.png", "calm-accent.png", "curious-accent.png", "delighted-accent.png", "six-pose-motion-atlas.png", "nine-clip-accent-atlas.png", "blink-strip.png"]
      .map(name => `${outRel}/${name}`)
  };
  const resultPath = path.join(outDir, "verification.json");
  fs.writeFileSync(resultPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify({
    status: result.status,
    page_sha256: result.page.sha256,
    evidence_sha256: sha(fs.readFileSync(resultPath)),
    checks
  }, null, 2));
  if (result.status !== "PASS_OWNER_REVIEW_READY") process.exitCode = 2;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
