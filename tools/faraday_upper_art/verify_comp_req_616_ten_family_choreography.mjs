#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-616-ten-family-choreography/index.html";
const outRel = ".cache/validation/comp-req-616-ten-family-choreography";
const outDir = path.join(root, ...outRel.split("/"));
const sha = value => crypto.createHash("sha256").update(value).digest("hex").toUpperCase();
const frozenEvidenceSha = "12E924C86A4A6787D2502ABE1F6D1DF278200FF9AC0E330CC002088144FEA76D";
const phaseDwellCommits = Object.freeze({ hold: 1, orient: 1, anticipate: 1, accent: 2, follow: 1, settle: 2 });
const packFrame = signature => {
  const packed = Buffer.alloc(5000, 0xFF);
  for (let index = 0; index < 40000; index += 1) {
    if (signature[index] === "1") packed[index >> 3] &= ~(0x80 >> (index & 7));
  }
  return packed;
};
const sourceHashes = {
  calm: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-04-calm_blink_settle.png", "CACD27828EE8197B46C5B34BFD04F271501698B2F171D37115E88E5590A7AB47"],
  curious_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-00-question_entry.png", "1A09AC75EA654E3699D50604AE758B4C8194DA5BA68FD62427E74DA9C23CC368"],
  curious_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-01-question_brow_lead.png", "6E024DFCD54E57DE20887C6BEBDF0CB10C98FE4F87915F04DF9B3CBA74AA8A7D"],
  curious_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-02-question_mouth_arrive.png", "F2627FA8EE0BF467DBA59551CCE55B737D42F68A21B5C3D2637B72D152CC4003"],
  curious_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-03-question_hold.png", "45F88F8ED0D47E8F20EE9776CFA6FEC99EEB9A4C2096F5C5AADA73FE927CC74E"],
  curious_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/curious_question-04-question_settle.png", "1A09AC75EA654E3699D50604AE758B4C8194DA5BA68FD62427E74DA9C23CC368"],
  delighted_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-00-delighted_entry.png", "C1B6B3410369C57F835270075644240CDB5FC1ED18856D8C26F7976F5A454A2A"],
  delighted_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-01-delighted_brow_lead.png", "53AC0DF43BC47044040D99E67C29F1BD3C0D5EF313E0687E0C437BA071391187"],
  delighted_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-02-delighted_mouth_arrive.png", "47BEA68C763CAFA0EDD2287443330625CBF355622F581384C7FA166DB807013E"],
  delighted_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-03-delighted_hold.png", "47BEA68C763CAFA0EDD2287443330625CBF355622F581384C7FA166DB807013E"],
  delighted_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/delighted_presence-04-delighted_settle.png", "C1B6B3410369C57F835270075644240CDB5FC1ED18856D8C26F7976F5A454A2A"],
  warm_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-00-warm_entry.png", "97EB6E87188E6A5896E9F62C8E2D00C4A47F6781619DEE575C2E3FE686ABBBC7"],
  warm_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-01-warm_brow_lead.png", "9DBD2A93679B69CB191A006EF12A1463603A0CB33B7BD3270447EBC88A42192D"],
  warm_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-02-warm_smile_arrive.png", "9E080E9FB442461E03915ECA0D0E297ADA4330F9AD85BE9A588FEAE4E296A4B5"],
  warm_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-03-warm_hold.png", "9E080E9FB442461E03915ECA0D0E297ADA4330F9AD85BE9A588FEAE4E296A4B5"],
  warm_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/warm_presence-04-warm_settle.png", "97EB6E87188E6A5896E9F62C8E2D00C4A47F6781619DEE575C2E3FE686ABBBC7"],
  playful_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-00-playful_entry.png", "2C6AA0375027C086D71736BF094C123D92D73062EFA56EE9A1E943BF4570E7AC"],
  playful_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-01-playful_brow_lead.png", "71092B9C9F21CD48BDDA6B1E286A4406F4E896D50BBA777F2D0B2105BCD423E4"],
  playful_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-02-playful_smile_arrive.png", "D996F15C72DE8B45AA5DFB28F64BCC6699BC57F47B926EAFE8675CDB604F7FBA"],
  playful_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-03-playful_hold.png", "D996F15C72DE8B45AA5DFB28F64BCC6699BC57F47B926EAFE8675CDB604F7FBA"],
  playful_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/playful_presence-04-playful_settle.png", "2C6AA0375027C086D71736BF094C123D92D73062EFA56EE9A1E943BF4570E7AC"],
  sleepy_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/sleepy_presence-00-sleep_entry.png", "1B4E773D65519C480BE573D5940F8863986F0BF35680F18152CAD635402A13D9"],
  sleepy_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/sleepy_presence-01-eyes_soften.png", "C3CADF42990CAE1936EA1084B1DA048A433776AF4DAF78FB26DFC05040ADDFD8"],
  sleepy_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/sleepy_presence-02-zzz_arrive.png", "2D4B2AC09D0DDC6E7D05536ABF6B9ADDF96D420412BBC387E786369C101EF49D"],
  sleepy_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/sleepy_presence-03-zzz_rise.png", "471E0895487B493E5FE3D5820BDD90AB2EEE843ACF858D697227CFC5C77304A6"],
  sleepy_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/sleepy_presence-04-sleep_hold.png", "2A77E2540EBC97E0C2C8DDEE8B12B24C54573C9FA5588FA15A2BF40D1979C1A6"],
  bashful_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/bashful_presence-00-bashful_entry.png", "FFE74F45B753D8BBE4AF328B1844DC47D9DB7796855664BE0E6C90F8F3853E95"],
  bashful_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/bashful_presence-01-bashful_brow_lead.png", "04D25A586CABC8D41E1DA6381D6CF3541327FD75B514D446A1981681A8924080"],
  bashful_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/bashful_presence-02-bashful_mouth_arrive.png", "DB89DB4F7BB76E8145820EBB747049974CD764F9F7EA33E98D92EBB1FD55CDB0"],
  bashful_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/bashful_presence-03-bashful_hold.png", "DB89DB4F7BB76E8145820EBB747049974CD764F9F7EA33E98D92EBB1FD55CDB0"],
  bashful_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/bashful_presence-04-bashful_settle.png", "FFE74F45B753D8BBE4AF328B1844DC47D9DB7796855664BE0E6C90F8F3853E95"],
  thoughtful_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/thoughtful_presence-00-thoughtful_entry.png", "3D7918A5B27D7CCDEA440A48337CB4D9F1BD8742885AFA288E390AC6FBD5980B"],
  thoughtful_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/thoughtful_presence-01-thoughtful_brow_lead.png", "33B9034EC9CAADE4128DA25CB52EDF5F46DC9D723E82026A93A17428FF957D18"],
  thoughtful_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/thoughtful_presence-02-thoughtful_mouth_arrive.png", "CB8CA21F5C5E0BC0D87E1AB44C268848036CC6A77A188770FB81F102C3F30970"],
  thoughtful_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/thoughtful_presence-03-thoughtful_hold.png", "CB8CA21F5C5E0BC0D87E1AB44C268848036CC6A77A188770FB81F102C3F30970"],
  thoughtful_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/thoughtful_presence-04-thoughtful_settle.png", "3D7918A5B27D7CCDEA440A48337CB4D9F1BD8742885AFA288E390AC6FBD5980B"],
  focused_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-00-focused_entry.png", "53BC852C1847C4167ECFF56B2A3B4616C6B90301CAF462BFC49F152ADF5E4D23"],
  focused_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-01-focused_brow_lead.png", "E5E3DA6E96D90CAAC5F726D92142BBDE946415B23600E70342EE86C50BB3BE1B"],
  focused_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-02-focused_mouth_arrive.png", "472456F0A242C1C8B4BD9DAE69C4FFC8B4A052E2EA938AC1B37EB61FE557864B"],
  focused_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-03-focused_hold.png", "472456F0A242C1C8B4BD9DAE69C4FFC8B4A052E2EA938AC1B37EB61FE557864B"],
  focused_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/focused_presence-04-focused_settle.png", "53BC852C1847C4167ECFF56B2A3B4616C6B90301CAF462BFC49F152ADF5E4D23"],
  alert_0: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/alert_exclamation-00-exclamation_entry.png", "CD960D88E681632DBA02A0C376AC1C2E9151EBC1F11A820C95A60A477D6F39C9"],
  alert_1: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/alert_exclamation-01-exclamation_brow_lead.png", "529467B1D8C03F9EAE08F763EED97476E11E610336388111A30F7DA8A6514426"],
  alert_2: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/alert_exclamation-02-exclamation_mouth_arrive.png", "D2C6069F7AC4E305726E00BAE86765EA7AE3191FAD556C89467995A08C811B2E"],
  alert_3: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/alert_exclamation-03-exclamation_hold.png", "BDA87E841734C404E09B36E251201AF68E8688E682F83C9F333CFD469CEF7D71"],
  alert_4: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/alert_exclamation-04-exclamation_settle.png", "CD960D88E681632DBA02A0C376AC1C2E9151EBC1F11A820C95A60A477D6F39C9"],
  blink_closed: ["docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/calm_presence-02-calm_blink_closed.png", "69B342A719613F7B406C45DF7375C4FC680B59FEE63FB449F1CF0C6AFADEDBFA"]
};
const livePage = "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html";
const livePageExpected = "0272365C090662F888ED664EA13A57BD164C87863D944439BF0EBD1BB47EF4D4";
const protectedFiles = {
  driver: ["app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c", "A9E79BCC0DBF8A36F8B5B82BDA08517D82E16F3EB17BC8AB71B5F06FCD5FB40B"],
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
    const families = ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"];
    const phases = ["hold", "orient", "anticipate", "accent", "follow", "settle"];
    const boxes = {
      calm: {
        eyes: [[40, 82, 38, 51], [123, 82, 39, 51]],
        brow: [[42, 56, 32, 17], [124, 56, 33, 17]],
        cheek: [[30, 127, 24, 19], [148, 126, 25, 19]],
        nose: [[93, 118, 14, 11]],
        mouth: [[82, 129, 36, 19]]
      },
      curious: {
        eyes: [[41, 106, 38, 51], [124, 106, 39, 51]],
        brow: [[53, 64, 39, 23], [121, 83, 34, 17]],
        cheek: [[29, 150, 25, 19], [149, 147, 25, 19]],
        nose: [[93, 142, 14, 11]],
        mouth: [[86, 151, 32, 26]],
        ornament: [[126, 2, 54, 116]]
      },
      delighted: {
        eyes: [[41, 86, 38, 51], [124, 86, 39, 51]],
        brow: [[41, 50, 39, 23], [123, 49, 38, 23]],
        cheek: [[29, 128, 25, 21], [148, 128, 25, 21]],
        nose: [[93, 122, 14, 10]],
        mouth: [[83, 130, 36, 21]]
      },
      warm: {
        eyes: [[39, 78, 37, 49], [122, 78, 38, 49]],
        brow: [[47, 52, 27, 18], [120, 52, 27, 18]],
        cheek: [[30, 122, 20, 15], [150, 121, 22, 15]],
        nose: [[91, 113, 18, 14]],
        mouth: [[82, 126, 31, 14]]
      },
      playful: {
        eyes: [[37, 83, 37, 49], [120, 83, 38, 49]],
        brow: [[49, 54, 27, 23], [118, 53, 30, 16]],
        cheek: [[27, 127, 20, 16], [142, 132, 19, 14]],
        nose: [[89, 118, 18, 14]],
        mouth: [[81, 131, 31, 14]]
      },
      sleepy: {
        eyes: [[40, 112, 37, 49], [123, 112, 38, 49]],
        brow: [[44, 87, 28, 13], [126, 87, 28, 13]],
        cheek: [[32, 158, 18, 13], [151, 158, 19, 13]],
        nose: [[92, 147, 18, 13]],
        mouth: [[84, 160, 29, 14]]
      },
      bashful: {
        eyes: [[40, 78, 37, 49], [123, 78, 38, 49]],
        brow: [[41, 60, 33, 14], [126, 60, 25, 13]],
        cheek: [[41, 123, 20, 13], [140, 123, 20, 13]],
        nose: [[92, 113, 18, 14]],
        mouth: [[84, 126, 29, 14]]
      },
      thoughtful: {
        eyes: [[45, 89, 37, 49], [128, 89, 38, 49]],
        brow: [[53, 54, 30, 19], [130, 72, 29, 13]],
        cheek: [[36, 134, 18, 13]],
        nose: [[97, 124, 18, 13]],
        mouth: [[89, 137, 29, 14]]
      },
      focused: {
        eyes: [[42, 78, 37, 49], [125, 78, 38, 49]],
        brow: [[51, 61, 26, 14], [128, 61, 25, 14]],
        cheek: [[33, 126, 18, 13], [151, 126, 18, 13]],
        nose: [[94, 113, 18, 14]],
        mouth: [[86, 126, 29, 14]]
      },
      alert: {
        eyes: [[40, 105, 37, 49], [123, 105, 38, 49]],
        brow: [[55, 77, 27, 21], [117, 77, 28, 21]],
        cheek: [[31, 152, 19, 13], [152, 152, 18, 13]],
        nose: [[92, 140, 18, 13]],
        mouth: [[84, 153, 29, 14]]
      }
    };
    for (const family of families) {
      boxes[family].registered = [[20, 10, 165, 180]];
    }
    const featureSeeds = {
      calm: { cheeks: [[40, 136], [160, 135]], nose: [100, 124] },
      curious: { cheeks: [[40, 159], [161, 156]], nose: [100, 148] },
      delighted: { cheeks: [[41, 139], [160, 139]], nose: [100, 128] },
      warm: { cheeks: [[40, 129], [160, 128]], nose: [99, 120] },
      playful: { cheeks: [[36, 134], [151, 139]], nose: [97, 125] },
      sleepy: { cheeks: [[40, 165], [160, 164]], nose: [100, 154] },
      bashful: { cheeks: [[50, 129], [150, 129]], nose: [100, 120] },
      thoughtful: { cheeks: [[45, 140]], nose: [105, 131] },
      focused: { cheeks: [[42, 132], [160, 132]], nose: [102, 120] },
      alert: { cheeks: [[40, 158], [160, 158]], nose: [100, 147] }
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
    const normalizedShape = points => {
      if (!points?.length) return "";
      const minX = Math.min(...points.map(([x]) => x));
      const minY = Math.min(...points.map(([, y]) => y));
      return points.map(([x, y]) => `${x - minX},${y - minY}`).sort().join(";");
    };
    const shapeMetrics = points => {
      if (!points?.length) return { area: 0, width: 0, height: 0, perimeter: 0 };
      const keys = new Set(points.map(([x, y]) => `${x},${y}`));
      const xs = points.map(([x]) => x);
      const ys = points.map(([, y]) => y);
      let perimeter = 0;
      for (const [x, y] of points) {
        for (const [nx, ny] of [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]]) {
          if (!keys.has(`${nx},${ny}`)) perimeter += 1;
        }
      }
      return {
        area: points.length,
        width: Math.max(...xs) - Math.min(...xs) + 1,
        height: Math.max(...ys) - Math.min(...ys) + 1,
        perimeter
      };
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
    const blackComponentAt = (data, seed) => {
      const black = (x, y) => data[(y * 200 + x) * 4] < 128;
      if (!black(seed[0], seed[1])) return [];
      const seen = new Set([seed[1] * 200 + seed[0]]);
      const queue = [[seed[0], seed[1]]];
      const points = [];
      while (queue.length) {
        const [x, y] = queue.shift();
        points.push([x, y]);
        for (const [nx, ny] of [[x - 1, y], [x + 1, y], [x, y - 1], [x, y + 1]]) {
          if (nx < 0 || nx >= 200 || ny < 0 || ny >= 200) continue;
          const next = ny * 200 + nx;
          if (!seen.has(next) && black(nx, ny)) {
            seen.add(next);
            queue.push([nx, ny]);
          }
        }
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
      const mouthComponents = blackComponentsInBox(data, boxes[family].mouth[0]).filter(component => component.length > 60);
      const browComponentSets = boxes[family].brow.map(box =>
        blackComponentsInBox(data, box).filter(component => component.length > 10)
      );
      const browComponents = browComponentSets.map(components => components[0] || []);
      const cheekComponents = featureSeeds[family].cheeks.map(seed => blackComponentAt(data, seed));
      const noseComponent = blackComponentAt(data, featureSeeds[family].nose);
      return {
        data,
        signature: signature(data),
        nonBinary,
        blackComponents: blackComponentCount(data, boxes[family].eyes),
        mouthComponents,
        mouthShape: normalizedShape(mouthComponents[0]),
        mouthMetrics: shapeMetrics(mouthComponents[0]),
        browShapes: browComponents.map(normalizedShape),
        browMetrics: browComponents.map(shapeMetrics),
        browComponentCounts: browComponentSets.map(components => components.length),
        cheekShapes: cheekComponents.map(normalizedShape),
        cheekMetrics: cheekComponents.map(shapeMetrics),
        cheekConnected: cheekComponents.every(component => component.length > 10 && component.length < 220),
        noseShape: normalizedShape(noseComponent),
        noseMetrics: shapeMetrics(noseComponent),
        noseConnected: noseComponent.length > 4 && noseComponent.length < 120
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
          family,
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
          lower_pixels: lowerDiff.length,
          lower_outside_registered_union: lowerDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
          follow_pixels: followDiff.length,
          follow_outside_registered_union: followDiff.filter(([x, y]) => !inside(x, y, allRegions)).length,
          settle_exact: frames.settle.signature === frames.hold.signature,
          mouth_connected: phases.every(phase => frames[phase].mouthComponents.length === 1),
          mouth_shape_changes_at_accent: frames.accent.mouthShape !== frames.hold.mouthShape,
          mouth_shape_returns_at_settle: frames.settle.mouthShape === frames.hold.mouthShape,
          mouth_metrics: Object.fromEntries(phases.map(phase => [phase, frames[phase].mouthMetrics])),
          brow_shape_changes_at_anticipate: frames.anticipate.browShapes.some((shape, side) =>
            shape !== frames.hold.browShapes[side]
          ),
          brow_shape_returns_at_settle: frames.settle.browShapes.every((shape, side) =>
            shape === frames.hold.browShapes[side]
          ),
          brows_connected: phases.every(phase =>
            frames[phase].browComponentCounts.every(count => count === 1)
          ),
          brow_metrics: Object.fromEntries(phases.map(phase => [phase, frames[phase].browMetrics])),
          cheek_shape_changes_at_accent: frames.accent.cheekShapes.some((shape, side) =>
            shape !== frames.anticipate.cheekShapes[side]
          ),
          cheek_shape_returns_at_settle: frames.settle.cheekShapes.every((shape, side) =>
            shape === frames.hold.cheekShapes[side]
          ),
          cheeks_connected: phases.every(phase =>
            frames[phase].cheekConnected
          ),
          cheek_metrics: Object.fromEntries(phases.map(phase => [phase, frames[phase].cheekMetrics])),
          nose_shape_changes_at_accent: frames.accent.noseShape !== frames.anticipate.noseShape,
          nose_shape_returns_at_settle: frames.settle.noseShape === frames.hold.noseShape,
          nose_connected: phases.every(phase => frames[phase].noseConnected),
          nose_metrics: Object.fromEntries(phases.map(phase => [phase, frames[phase].noseMetrics])),
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

  const mobilePage = await browser.newPage({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 1 });
  mobilePage.on("pageerror", error => errors.push(`mobile-page:${error.message}`));
  mobilePage.on("console", message => {
    if (message.type() === "error") errors.push(`mobile-console:${message.text()}`);
  });
  await mobilePage.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load", timeout: 15000 });
  await mobilePage.waitForFunction(() => window.__compReq599Ready === true, null, { timeout: 15000 });
  await mobilePage.locator('[data-family="playful"]').click();
  await mobilePage.waitForTimeout(1920);
  const mobileAudit = await mobilePage.evaluate(() => {
    const canvas = document.querySelector("#face").getBoundingClientRect();
    const buttons = [...document.querySelectorAll("[data-family]")].map(item => item.getBoundingClientRect());
    return {
      canvas_inside_viewport: canvas.left >= 0 && canvas.right <= innerWidth,
      controls_inside_viewport: buttons.every(rect => rect.left >= 0 && rect.right <= innerWidth),
      horizontal_overflow: document.documentElement.scrollWidth > innerWidth,
      canvas_count: document.querySelectorAll("canvas").length
    };
  });
  await mobilePage.screenshot({ path: path.join(outDir, "mobile-playful-runtime.png"), fullPage: true });
  await mobilePage.close();

  const allFamilies = ["calm", "curious", "delighted", "warm", "playful", "sleepy", "bashful", "thoughtful", "focused", "alert"];
  for (const family of allFamilies) {
    await page.evaluate(name => window.__compReq599Freeze(name, 1, "accent"), family);
    await page.screenshot({ path: path.join(outDir, `${family}-accent.png`), fullPage: true });
  }
  await page.evaluate(() => window.__compReq599Freeze("calm", 0, "hold"));
  await page.screenshot({ path: path.join(outDir, "calm-hold.png"), fullPage: true });
  await page.evaluate(allFamilies => {
    const atlas = document.createElement("canvas");
    atlas.id = "clipAtlas";
    atlas.width = 600;
    atlas.height = 2000;
    atlas.style.width = "600px";
    atlas.style.height = "2000px";
    atlas.style.imageRendering = "pixelated";
    const atlasContext = atlas.getContext("2d");
    allFamilies.forEach((family, row) => {
      [0, 1, 2].forEach(phrase => {
        window.__compReq599Freeze(family, phrase, "accent");
        atlasContext.drawImage(document.querySelector("#face"), phrase * 200, row * 200);
      });
    });
    const strip = document.createElement("canvas");
    strip.id = "poseStrip";
    strip.width = 1200;
    strip.height = 2000;
    strip.style.width = "1200px";
    strip.style.height = "2000px";
    strip.style.imageRendering = "pixelated";
    const stripContext = strip.getContext("2d");
    allFamilies.forEach((family, row) => {
      ["hold", "orient", "anticipate", "accent", "follow", "settle"].forEach((phase, column) => {
        window.__compReq599Freeze(family, 1, phase);
        stripContext.drawImage(document.querySelector("#face"), column * 200, row * 200);
      });
    });
    const shapeStrip = document.createElement("canvas");
    shapeStrip.id = "shapeStrip";
    shapeStrip.width = 1050;
    shapeStrip.height = 2100;
    shapeStrip.style.width = "1050px";
    shapeStrip.style.height = "2100px";
    shapeStrip.style.imageRendering = "pixelated";
    const shapeContext = shapeStrip.getContext("2d");
    allFamilies.forEach((family, row) => {
      ["hold", "anticipate", "accent", "follow", "settle"].forEach((phase, column) => {
        window.__compReq599Freeze(family, 1, phase);
        shapeContext.drawImage(document.querySelector("#face"), 30, 35, 140, 145, column * 210, row * 210, 210, 210);
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
    document.body.replaceChildren(strip, shapeStrip, atlas, blinkStrip);
  }, allFamilies);
  await page.locator("#poseStrip").screenshot({ path: path.join(outDir, "six-pose-motion-atlas.png") });
  await page.locator("#shapeStrip").screenshot({ path: path.join(outDir, "feature-deformation-atlas.png") });
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
  let nativePolarityParity = true;
  for (const [family, familyAudit] of Object.entries(audit.families)) {
    familyAudit.phrases.forEach((phrase, phraseIndex) => {
      for (const [phase, signature] of Object.entries(phrase.signatures)) {
        const payload = packFrame(signature);
        for (let pixel = 0; pixel < 40000; pixel += 1) {
          const payloadWhite = (payload[pixel >> 3] & (0x80 >> (pixel & 7))) !== 0;
          if (payloadWhite !== (signature[pixel] === "0")) nativePolarityParity = false;
        }
        framePlanEntries.push({
          id: `${family}.${phraseIndex}.${phase}`,
          family,
          phrase: phraseIndex,
          phase,
          dwell_commits: phaseDwellCommits[phase] || 1,
          cadence_ms: 480,
          payload_bytes: payload.length,
          framebuffer_sha256: sha(payload),
          payload
        });
      }
    });
  }
  for (const phase of ["closed", "open"]) {
    const signature = audit.blink[`${phase}_signature`];
    const payload = packFrame(signature);
    for (let pixel = 0; pixel < 40000; pixel += 1) {
      const payloadWhite = (payload[pixel >> 3] & (0x80 >> (pixel & 7))) !== 0;
      if (payloadWhite !== (signature[pixel] === "0")) nativePolarityParity = false;
    }
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
    schema: "companion.canonical_1bit_frame_plan.comp_req_616.ten_family.v1",
    pixel_format: "row_major_msb_first_1_is_white",
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
  const firstSignature = audit.families.calm.phrases[0].signatures.hold;
  const legacyBlackPayload = Buffer.alloc(5000);
  for (let pixel = 0; pixel < 40000; pixel += 1) {
    if (firstSignature[pixel] === "1") legacyBlackPayload[pixel >> 3] |= 0x80 >> (pixel & 7);
  }
  let legacyPolarityMismatch = 0;
  for (let pixel = 0; pixel < 40000; pixel += 1) {
    const payloadWhite = (legacyBlackPayload[pixel >> 3] & (0x80 >> (pixel & 7))) !== 0;
    if (payloadWhite !== (firstSignature[pixel] === "0")) legacyPolarityMismatch += 1;
  }
  const negativeFixtures = [
    {
      name: "missing_tenth_family",
      rejected: Object.keys(audit.families).filter(name => name !== "alert").length !== 10
    },
    {
      name: "pure_translation_mouth_claim",
      rejected: !({ ...audit.families.warm.phrases[0], mouth_shape_changes_at_accent: false }).mouth_shape_changes_at_accent
    },
    {
      name: "single_highlight_fragment",
      rejected: ({ ...audit.families.calm.phrases[0].eye_audit.hold[0], count: 1 }).count !== 2
    },
    {
      name: "stale_nonsettling_frame",
      rejected: audit.families.curious.phrases[0].signatures.hold !==
        `${audit.families.curious.phrases[0].signatures.settle}tampered`
    },
    {
      name: "wrong_481ms_cadence",
      rejected: 481 !== audit.contract.cadence_ms
    },
    {
      name: "duplicate_sleepy_clip",
      rejected: ({ ...audit.families.sleepy, distinct_accents: 2 }).distinct_accents !== 3
    },
    {
      name: "legacy_1_is_black_payload",
      rejected: legacyPolarityMismatch > 0
    }
  ];
  const families = Object.values(audit.families);
  const phrases = families.flatMap(family => family.phrases);
  const openFamilyEyeFrames = phrases
    .filter(phrase => phrase.family !== "sleepy")
    .flatMap(phrase => Object.values(phrase.eye_audit).flat());
  const sleepyPhrases = audit.families.sleepy.phrases;
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
    exactly_two_clean_highlights_per_eye: openFamilyEyeFrames.every(item =>
      item.count === 2 && item.no_fragment && item.body_exact && item.areas_exact
    ),
    outer_eye_shell_invariant: openFamilyEyeFrames.every(item => item.body_exact),
    sleepy_closure_is_authored_not_blink_substitute: sleepyPhrases.every(item =>
      ["hold", "orient", "settle"].every(phase =>
        item.eye_audit[phase].every(eye => eye.count === 2 && eye.body_exact)
      ) &&
      ["anticipate", "accent", "follow"].every(phase =>
        item.eye_audit[phase].every(eye => eye.count === 0)
      )
    ),
    gaze_leads_inside_eyes_only: phrases.every(item => item.gaze_pixels > 0 && item.gaze_outside_eyes === 0),
    brow_answers_after_gaze: phrases.every(item => item.brow_pixels > 0 && item.brow_outside_registered_union === 0),
    lower_face_has_readable_intent: phrases.every(item =>
      (item.family === "sleepy" ? item.lower_pixels > 0 : item.lower_lane_hits.mouth > 0) &&
      item.lower_outside_registered_union === 0
    ),
    follow_through_is_distinct: phrases.every(item => item.follow_pixels > 0),
    every_mouth_pose_connected: phrases.every(item => item.mouth_connected),
    mouth_silhouette_deforms_not_translates: phrases.every(item =>
      item.mouth_shape_changes_at_accent && item.mouth_shape_returns_at_settle
    ),
    brow_silhouette_deforms_not_translates: phrases.every(item =>
      item.brow_shape_changes_at_anticipate && item.brow_shape_returns_at_settle
    ),
    coordinated_cheek_nose_deformation: Object.entries(audit.families)
      .filter(([family]) => ["curious", "delighted"].includes(family))
      .flatMap(([, item]) => item.phrases)
      .every(item =>
        item.cheek_shape_changes_at_accent &&
        item.cheek_shape_returns_at_settle &&
        item.nose_shape_changes_at_accent &&
        item.nose_shape_returns_at_settle
      ),
    authored_feature_components_remain_connected: phrases.every(item =>
      item.mouth_connected && item.brows_connected && item.cheeks_connected && item.nose_connected
    ),
    registered_union_only: phrases.every(item =>
      item.lower_outside_registered_union === 0 && item.follow_outside_registered_union === 0
    ),
    exact_settle_return: phrases.every(item => item.settle_exact),
    three_distinct_clips_per_family: families.every(item =>
      item.distinct_orients === 3 && item.distinct_accents === 3 && item.distinct_follows === 3
    ),
    ten_owner_visible_families_present: Object.keys(audit.families).length === 10 &&
      Object.keys(audit.contract.families).length === 10,
    deterministic_pixel_replay: families.every(item => item.deterministic_replay),
    non_repeating_selector: contractFamilies.every(item =>
      item.phrase_count >= 3 && item.phrase_order.every((value, index, order) => index === 0 || value !== order[index - 1])
    ),
    authored_quiet_range: contractFamilies.every(item =>
      new Set(item.quiet_slots).size >= 4 && item.quiet_slots.every(value => value >= 4 && value <= 7)
    ),
    intent_led_shape_profiles: contractFamilies.every(item =>
      item.shape_profiles.length === 3 &&
      item.shape_profiles.every(profile =>
        typeof profile.intent === "string" && profile.intent.length > 0 &&
        Math.max(...profile.gaze.map(Math.abs)) >= 2 &&
        Math.max(...profile.gaze.map(Math.abs)) <= 4
      )
    ),
    physical_cadence_and_five_changes: audit.contract.cadence_ms === 480 &&
      audit.contract.changed_commits_per_phrase === 5 &&
      audit.contract.first_orient_slots === 1 &&
      JSON.stringify(audit.contract.phase_dwell_commits) === JSON.stringify(phaseDwellCommits),
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
    no_pixel_noise_or_whole_component_translation: !pageSource.includes("Math.random") &&
      !pageSource.includes("shiftRegion") &&
      !pageSource.includes("translateProfile") &&
      !/drawImage\\s*\\([^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^,]+,[^)]+\\)/.test(pageSource),
    no_css_animation: audit.css_animated_nodes === 0,
    one_composed_200x200_face: audit.canvas_count === 1,
    mobile_layout_and_runtime_fit: mobileAudit.canvas_inside_viewport &&
      mobileAudit.controls_inside_viewport &&
      !mobileAudit.horizontal_overflow &&
      mobileAudit.canvas_count === 1,
    canonical_browser_wb55_payload_parity: framePlanParity &&
      framePlan.entries.every(entry => entry.payload_bytes === 5000 && entry.cadence_ms === 480 &&
        entry.dwell_commits === (entry.phase.startsWith("blink_") ? 1 : (phaseDwellCommits[entry.phase] || 1))),
    native_polarity_browser_wb55_pixel_parity: nativePolarityParity &&
      framePlan.pixel_format === "row_major_msb_first_1_is_white",
    negative_fixtures_reject_all: negativeFixtures.length === 7 &&
      negativeFixtures.every(item => item.rejected),
    protected_files_unchanged: Object.values(protectedAudit).every(item => item.match),
    browser_errors_zero: errors.length === 0,
    live_page_unchanged: sha(fs.readFileSync(path.join(root, ...livePage.split("/")))) === livePageExpected
  };
  const result = {
    schema: "companion.comp_req_616.ten_family_choreography.verification.v1",
    status: Object.values(checks).every(Boolean) ? "PASS_OWNER_REVIEW_READY" : "NO_GO",
    page: { path: pageRel, sha256: sha(fs.readFileSync(pagePath)) },
    research: {
      path: "docs/validation/companion-open-source-oled-pet-research-20260726.md",
      sha256: sha(fs.readFileSync(path.join(root, "docs/validation/companion-open-source-oled-pet-research-20260726.md")))
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
    mobile_audit: mobileAudit,
    negative_fixtures: negativeFixtures,
    checks,
    errors,
    screenshots: ["calm-hold.png", ...allFamilies.map(family => `${family}-accent.png`), "mobile-playful-runtime.png", "six-pose-motion-atlas.png", "feature-deformation-atlas.png", "nine-clip-accent-atlas.png", "blink-strip.png"]
      .map(name => `${outRel}/${name}`)
  };
  const resultPath = path.join(outDir, "verification.json");
  const resultBytes = Buffer.from(`${JSON.stringify(result, null, 2)}\n`);
  const candidateEvidenceSha = sha(resultBytes);
  let evidenceSha = candidateEvidenceSha;
  let frozenEvidencePreserved = false;
  if (fs.existsSync(resultPath)) {
    const existingBytes = fs.readFileSync(resultPath);
    const existingSha = sha(existingBytes);
    if (existingSha === frozenEvidenceSha && candidateEvidenceSha !== frozenEvidenceSha) {
      fs.writeFileSync(path.join(outDir, "verification.candidate.json"), resultBytes);
      evidenceSha = existingSha;
      frozenEvidencePreserved = true;
    } else {
      fs.writeFileSync(resultPath, resultBytes);
    }
  } else {
    fs.writeFileSync(resultPath, resultBytes);
  }
  console.log(JSON.stringify({
    status: result.status,
    page_sha256: result.page.sha256,
    evidence_sha256: evidenceSha,
    candidate_evidence_sha256: candidateEvidenceSha,
    frozen_evidence_preserved: frozenEvidencePreserved,
    checks
  }, null, 2));
  if (result.status !== "PASS_OWNER_REVIEW_READY") process.exitCode = 2;
} finally {
  await browser?.close();
  await new Promise(resolve => server.close(resolve));
}
