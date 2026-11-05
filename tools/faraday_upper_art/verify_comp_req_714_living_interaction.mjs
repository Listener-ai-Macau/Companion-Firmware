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
const artifactRoot = path.join(root, ".cache/validation/comp-req-714-living-interaction");
fs.mkdirSync(artifactRoot, { recursive: true });

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

const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const server = http.createServer((request, response) => {
  const target = path.resolve(root, `.${decodeURIComponent(request.url.split("?")[0])}`);
  if (!target.startsWith(`${root}${path.sep}`)) return response.writeHead(403).end();
  fs.readFile(target, (error, data) => {
    if (error) return response.writeHead(404).end();
    response.writeHead(200, { "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "image/png" });
    response.end(data);
  });
});

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 680, height: 720 }, deviceScaleFactor: 1 });
  const errors = [];
  page.on("pageerror", error => errors.push(`page:${error.message}`));
  page.on("console", message => { if (message.type() === "error") errors.push(`console:${message.text()}`); });
  await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load", timeout: 15000 });
  await page.waitForFunction(() => window.__compReq599Ready === true && typeof window.__compReq714FreezeLifeAction === "function");

  const contract = await page.evaluate(() => window.__compReq625Contract());
  await page.evaluate(() => window.__compReq714SetScheduler(false));
  const families = Object.keys(contract.family_choreography);
  const actions = ["notice_left", "notice_right", "soften", "small_breath", "listen_up"];
  const regionBits = async bounds => page.evaluate(bounds => {
    const data = document.querySelector("#face").getContext("2d").getImageData(...bounds).data;
    const bits = [];
    for (let offset = 0; offset < data.length; offset += 4) bits.push(data[offset] < 128 ? 1 : 0);
    return bits;
  }, bounds);
  const browBits = async boxes => {
    const groups = [];
    for (const bounds of boxes) groups.push(...await regionBits(bounds));
    return groups;
  };
  const saveCanvas = async name => {
    const url = await page.evaluate(() => document.querySelector("#face").toDataURL("image/png"));
    fs.writeFileSync(path.join(artifactRoot, name), Buffer.from(url.split(",")[1], "base64"));
  };

  const mouthSignatures = {};
  const browResidual = {};
  for (const family of families) {
    const art = contract.family_choreography[family];
    const signatures = [];
    for (const action of actions) {
      await page.evaluate(({ family, action }) =>
        window.__compReq714FreezeLifeAction(family, action, "hold", 0, 0, false), { family, action });
      signatures.push({ action, signature: sha(Buffer.from(await regionBits(art.mouth_bounds))) });
    }
    mouthSignatures[family] = signatures;

    await page.evaluate(family => window.__compReq599Freeze(family, 0, "accent"), family);
    const baseline = sha(Buffer.from(await browBits(art.brow_bounds)));
    const shifted = {};
    for (const action of ["notice_left", "notice_right", "listen_up"]) {
      await page.evaluate(({ family, action }) =>
        window.__compReq714FreezeLifeAction(family, action, "accent", 0, 0, false), { family, action });
      shifted[action] = sha(Buffer.from(await browBits(art.brow_bounds)));
    }
    browResidual[family] = {
      baseline,
      shifted,
      residue_free: Object.values(shifted).every(signature => signature === baseline)
    };
  }

  const proceduralFamilies = Object.entries(contract.emotion_ornaments)
    .filter(([, ornament]) => ornament.kind === "procedural")
    .map(([family]) => family);
  const ornamentAudit = {};
  for (const family of proceduralFamilies) {
    await page.evaluate(family =>
      window.__compReq714FreezeLifeAction(family, "soften", "accent", 0, 0, false), family);
    const without = await page.evaluate(() =>
      Array.from(document.querySelector("#face").getContext("2d").getImageData(0, 0, 200, 200).data));
    await page.evaluate(family =>
      window.__compReq714FreezeLifeAction(family, "soften", "accent", 0, 0, true), family);
    const withOrnament = await page.evaluate(() =>
      Array.from(document.querySelector("#face").getContext("2d").getImageData(0, 0, 200, 200).data));
    const bounds = contract.emotion_ornaments[family].safe_bounds;
    let insideDiff = 0;
    let outsideDiff = 0;
    for (let y = 0; y < 200; y += 1) {
      for (let x = 0; x < 200; x += 1) {
        const offset = (y * 200 + x) * 4;
        if (without[offset] === withOrnament[offset]) continue;
        const inside = x >= bounds.x && x < bounds.x + bounds.width
          && y >= bounds.y && y < bounds.y + bounds.height;
        if (inside) insideDiff += 1;
        else outsideDiff += 1;
      }
    }
    ornamentAudit[family] = { inside_diff: insideDiff, outside_diff: outsideDiff };
    await saveCanvas(`comp-req-714-${family}-ornament.png`);
  }

  const canvas = page.locator("#face");
  const box = await canvas.boundingBox();
  const point = (x, y) => ({ x: box.x + box.width * x, y: box.y + box.height * y });
  const drag = async points => {
    await page.mouse.move(...Object.values(point(...points[0])));
    await page.mouse.down();
    for (const [x, y] of points.slice(1)) {
      const target = point(x, y);
      await page.mouse.move(target.x, target.y, { steps: 4 });
      await page.waitForTimeout(520);
    }
    await page.mouse.up();
    await page.waitForTimeout(80);
    return page.evaluate(() => window.__compReq599Snapshot().trace);
  };

  await page.evaluate(() => window.__compReq714SetScheduler(true));
  await page.evaluate(() => { window.__compReq599Restore(); window.__compReq714ResetInteraction(); window.__compReq714ClearTrace(); });
  const shortTrace = await drag([[0.45, 0.55], [0.5, 0.55]]);
  const shortRelease = shortTrace.find(event => event.type === "tease_release");

  await page.evaluate(() => { window.__compReq599Restore(); window.__compReq714ResetInteraction(); window.__compReq714ClearTrace(); });
  const teaseTrace = await drag([[0.18, 0.5], [0.5, 0.3], [0.82, 0.5], [0.42, 0.72], [0.78, 0.38]]);
  const teaseRelease = teaseTrace.find(event => event.type === "tease_release");
  const teaseStart = teaseTrace.find(event => event.type === "touch_transition_start");
  const followCommits = teaseTrace.filter(event => event.type === "tease_follow_commit");
  await saveCanvas("comp-req-714-tease-release.png");

  const routeChecks = [];
  for (const source of families) {
    for (const target of families) {
      const route = await page.evaluate(({ source, target }) => window.__compReq714Route(source, target), { source, target });
      const legal = route.every((name, index) => index === 0
        || contract.living_motion.affect_graph[route[index - 1]].includes(name));
      routeChecks.push({ source, target, route, legal });
    }
  }

  const checks = {
    browser_errors_zero: errors.length === 0,
    brow_residue_zero: Object.values(browResidual).every(row => row.residue_free),
    mouth_presence_rich: Object.values(mouthSignatures).every(rows =>
      new Set(rows.map(row => row.signature)).size >= 4),
    later_families_have_profiles: ["warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"]
      .every(family => contract.family_choreography[family].local_mouth_profile !== "accepted_authored"),
    mood_ornaments_are_overlays: proceduralFamilies.length >= 3
      && Object.values(ornamentAudit).every(row => row.inside_diff > 0 && row.outside_diff === 0),
    affect_routes_legal: routeChecks.every(row => row.legal),
    short_drag_does_not_tease: shortRelease?.qualifies === false,
    qualifying_drag_enters_playful: teaseRelease?.qualifies === true
      && teaseStart?.target === "playful"
      && teaseStart?.intent === "tease_release",
    drag_tracks_latest_quantized_target: followCommits.length >= 3
      && followCommits.every((row, index, rows) => Array.isArray(row.zone)
        && row.cadence_ms === contract.gestures.pointer_follow_cadence_ms
        && (index === 0 || row.at - rows[index - 1].at >= contract.gestures.pointer_follow_cadence_ms - 40)),
    physical_visible_cadence_only: contract.gestures.pointer_follow_cadence_ms >= 480
  };
  const report = {
    schema: "companion.comp_req_714.living_interaction.verification.v1",
    status: Object.values(checks).every(Boolean) ? "GO" : "NO_GO",
    checks,
    evidence: {
      mature_product_model: "attention_reflex_then_local_reaction_then_bounded_relationship_update",
      mouth_signatures: mouthSignatures,
      brow_residual: browResidual,
      ornaments: ornamentAudit,
      short_drag: shortRelease,
      tease_drag: { release: teaseRelease, transition: teaseStart, follow_commits: followCommits },
      legal_route_count: routeChecks.filter(row => row.legal).length,
      route_count: routeChecks.length,
      hardware_contact: 0
    },
    browser_errors: errors
  };
  fs.writeFileSync(path.join(artifactRoot, "verification.json"), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report, null, 2));
  process.exitCode = report.status === "GO" ? 0 : 1;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
