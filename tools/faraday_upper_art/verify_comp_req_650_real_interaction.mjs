#!/usr/bin/env node
import fs from "node:fs";
import http from "node:http";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const pageRel = ".cache/validation/comp-req-628-status-bar/index.html";
const outPath = path.join(root, ".cache/validation/comp-req-628-status-bar/comp-req-660-real-interaction.json");
const artifactRoot = path.dirname(outPath);

function playwright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
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
    response.writeHead(200, {
      "content-type": target.endsWith(".html") ? "text/html; charset=utf-8" : "image/png"
    });
    response.end(data);
  });
});

let browser;
try {
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  browser = await playwright().chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 680, height: 790 } });
  const errors = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto(`http://127.0.0.1:${server.address().port}/${pageRel}`, { waitUntil: "load" });
  await page.waitForFunction(() => window.__compReq599Ready === true);

  const audio = {};
  const definitions = {
    recording: {
      wave: [1, 159, 20, 19], centerRow: 9,
      gap: [21, 156, 2, 24], body: [23, 156, 18, 28]
    },
    speaker: {
      wave: [179, 158, 20, 20], centerRow: 10,
      gap: [177, 156, 2, 28], body: [159, 156, 18, 28]
    }
  };
  for (const [mode, definition] of Object.entries(definitions)) {
    const traceStart = await page.evaluate(() => window.__compReq599Snapshot().trace.length);
    await page.click(`[data-mode="${mode}"]`);
    const rows = [];
    for (let sample = 0; sample < 24; sample += 1) {
      rows.push(await page.evaluate(({ wave, gap, body, centerRow, mode }) => {
        const context = document.querySelector("#face").getContext("2d");
        const measure = rectangle => {
          const pixels = context.getImageData(...rectangle).data;
          let signature = 2166136261;
          let ink = 0;
          let minX = rectangle[2];
          let maxX = -1;
          const mask = new Uint8Array(rectangle[2] * rectangle[3]);
          for (let index = 0; index < pixels.length; index += 4) {
            const bit = pixels[index] < 128 ? 1 : 0;
            signature = Math.imul(signature ^ bit, 16777619);
            ink += bit;
            if (bit) {
              const pixelIndex = index / 4;
              const x = pixelIndex % rectangle[2];
              mask[pixelIndex] = 1;
              minX = Math.min(minX, x);
              maxX = Math.max(maxX, x);
            }
          }
          let components = 0;
          for (let seed = 0; seed < mask.length; seed += 1) {
            if (!mask[seed]) continue;
            components += 1;
            const queue = [seed];
            mask[seed] = 0;
            while (queue.length) {
              const current = queue.pop();
              const x = current % rectangle[2];
              const y = Math.floor(current / rectangle[2]);
              for (let dy = -1; dy <= 1; dy += 1) {
                for (let dx = -1; dx <= 1; dx += 1) {
                  if (dx === 0 && dy === 0) continue;
                  const nextX = x + dx;
                  const nextY = y + dy;
                  if (nextX < 0 || nextX >= rectangle[2] || nextY < 0 || nextY >= rectangle[3]) continue;
                  const next = nextY * rectangle[2] + nextX;
                  if (!mask[next]) continue;
                  mask[next] = 0;
                  queue.push(next);
                }
              }
            }
          }
          return {
            signature: (signature >>> 0).toString(16),
            ink,
            min_x: minX,
            max_x: maxX,
            components
          };
        };
        const endpointRows = x => {
          const pixels = context.getImageData(x, wave[1], 1, wave[3]).data;
          const rows = [];
          for (let index = 0; index < pixels.length; index += 4) {
            if (pixels[index] < 128) rows.push(index / 4);
          }
          return rows;
        };
        const latestCommit = [...window.__compReq599Snapshot().trace].reverse()
          .find(event => event.type === "commit" && event.mode === mode);
        return {
          wave: measure(wave),
          gap: measure(gap),
          body: measure(body),
          entry_wave_progress: latestCommit?.envelope?.entry_wave_progress ?? 1,
          endpoints: {
            expected_row: centerRow,
            outer_rows: endpointRows(wave[0]),
            inner_rows: endpointRows(wave[0] + wave[2] - 1)
          }
        };
      }, { ...definition, mode }));
      await page.waitForTimeout(240);
    }
    const firstChange = rows.findIndex((row, index) =>
      index > 0 && row.wave.signature !== rows[0].wave.signature);
    const commitTimes = await page.evaluate(({ mode, traceStart }) =>
      window.__compReq599Snapshot().trace.slice(traceStart)
        .filter(event => event.type === "commit" && event.mode === mode && event.changed)
        .map(event => event.at), { mode, traceStart });
    const commitIntervals = commitTimes.slice(1).map((value, index) =>
      Math.round((value - commitTimes[index]) * 10) / 10);
    const steadyRows = rows.filter(row => row.entry_wave_progress >= 1);
    audio[mode] = {
      first_change_ms: firstChange * 240,
      commit_interval_ms: commitIntervals,
      minimum_commit_interval_ms: Math.min(...commitIntervals),
      unique_frames: new Set(rows.map(row => row.wave.signature)).size,
      unique_body_frames: new Set(rows.map(row => row.body.signature)).size,
      entry_wave_progress_values: [...new Set(rows.map(row => row.entry_wave_progress))],
      steady_sample_count: steadyRows.length,
      ink_values: [...new Set(steadyRows.map(row => row.wave.ink))],
      component_values: [...new Set(steadyRows.map(row => row.wave.components))],
      body_gap_ink_values: [...new Set(rows.map(row => row.gap.ink))],
      body_clearance_ok: rows.every(row => row.gap.ink === 0),
      centerline_locked: steadyRows.every(row =>
        JSON.stringify(row.endpoints.outer_rows) === JSON.stringify([row.endpoints.expected_row])
        && JSON.stringify(row.endpoints.inner_rows) === JSON.stringify([row.endpoints.expected_row]))
    };
  }

  await page.click('[data-mode="menu"]');
  const readMenuCells = () => page.evaluate(() => {
    const context = document.querySelector("#face").getContext("2d");
    const count = (x, y) => {
      const pixels = context.getImageData(x, y, 8, 8).data;
      let ink = 0;
      for (let index = 0; index < pixels.length; index += 4) {
        if (pixels[index] < 128) ink += 1;
      }
      return ink;
    };
    return [count(88, 28), count(104, 28), count(88, 44), count(104, 44)];
  });
  const idleMenuRows = [];
  for (let sample = 0; sample < 20; sample += 1) {
    idleMenuRows.push(await readMenuCells());
    await page.waitForTimeout(80);
  }

  const canvas = await page.locator("#face").boundingBox();
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(1600);
  const earlyReleasePartial = await readMenuCells();
  await page.mouse.up();
  const earlyReleaseRows = [await readMenuCells()];
  await page.waitForTimeout(560);
  earlyReleaseRows.push(await readMenuCells());

  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  await page.waitForTimeout(480);
  await page.mouse.move(canvas.x + canvas.width * 0.65, canvas.y + canvas.height / 2);
  const dragCancelRows = [await readMenuCells()];
  await page.waitForTimeout(560);
  dragCancelRows.push(await readMenuCells());
  await page.mouse.up();

  await page.click('[data-mode="expression"]');
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  const menuRows = [];
  const menuStartedAt = Date.now();
  for (let sample = 0; sample < 42; sample += 1) {
    menuRows.push({
      elapsed_ms: Date.now() - menuStartedAt,
      cells: await page.evaluate(() => {
      const context = document.querySelector("#face").getContext("2d");
      const count = (x, y) => {
        const pixels = context.getImageData(x, y, 8, 8).data;
        let ink = 0;
        for (let index = 0; index < pixels.length; index += 4) {
          if (pixels[index] < 128) ink += 1;
        }
        return ink;
      };
      return [count(88, 28), count(104, 28), count(88, 44), count(104, 44)];
      })
    });
    await page.waitForTimeout(80);
  }
  await page.waitForTimeout(300);
  const menuStateAfterHandoff = await page.evaluate(() => window.__compReq657MenuState());
  await page.mouse.up();

  const menuNavigationStart = await page.evaluate(() => performance.now());
  await page.mouse.click(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.42);
  await page.waitForTimeout(120);
  const menuDetailState = await page.evaluate(() => window.__compReq657MenuState());
  await page.mouse.click(canvas.x + canvas.width * 0.12, canvas.y + canvas.height * 0.12);
  await page.waitForTimeout(120);
  const menuBackState = await page.evaluate(() => window.__compReq657MenuState());
  await page.mouse.move(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.82);
  await page.mouse.down();
  await page.mouse.move(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.45, { steps: 6 });
  await page.mouse.up();
  await page.waitForTimeout(120);
  const menuScrolledState = await page.evaluate(() => window.__compReq657MenuState());
  await page.mouse.click(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.85);
  await page.waitForTimeout(120);
  const menuScrolledTapState = await page.evaluate(() => window.__compReq657MenuState());
  await page.mouse.click(canvas.x + canvas.width * 0.12, canvas.y + canvas.height * 0.12);
  await page.waitForTimeout(120);
  await page.mouse.move(canvas.x + canvas.width * 0.25, canvas.y + canvas.height * 0.55);
  await page.mouse.down();
  await page.mouse.move(canvas.x + canvas.width * 0.68, canvas.y + canvas.height * 0.55, { steps: 5 });
  await page.mouse.up();
  await page.waitForTimeout(180);
  const menuExitState = await page.evaluate(() => window.__compReq657MenuState());
  const menuNavigationTrace = await page.evaluate(start =>
    window.__compReq599Snapshot().trace.filter(event => event.at >= start), menuNavigationStart);

  const menuStageScreenshots = [];
  await page.click('[data-mode="expression"]');
  const captureCanvas = async stage => {
    const target = path.join(
      root,
      `.cache/validation/comp-req-628-status-bar/comp-req-660-menu-stage-${stage}.png`
    );
    await page.locator("#face").screenshot({ path: target });
    menuStageScreenshots.push(path.relative(root, target).replaceAll("\\", "/"));
  };
  await captureCanvas(0);
  await page.mouse.move(canvas.x + canvas.width / 2, canvas.y + canvas.height / 2);
  await page.mouse.down();
  let previousMilestone = 0;
  for (const [stage, milestone] of [[1, 1550], [2, 2050], [3, 2550], [4, 3050]]) {
    await page.waitForTimeout(milestone - previousMilestone);
    await captureCanvas(stage);
    previousMilestone = milestone;
  }
  await page.mouse.up();

  const rawFullAt = menuRows.findIndex(row => row.cells.every(value => value === 64));
  const handoffAt = rawFullAt < 0 ? -1 : menuRows.findIndex((row, index) =>
    index > rawFullAt && !row.cells.every(value => value === 64));
  const menuProgressRows = handoffAt > 0 ? menuRows.slice(0, handoffAt) : menuRows;
  const fullCounts = menuProgressRows.map(row => row.cells.filter(value => value === 64).length);
  const wholeCellOnly = menuProgressRows.every(row => row.cells.every(value => value === 0 || value === 64));
  const quadrantOrder = [0, 1, 3, 2];
  const quadrantPrefixOnly = menuProgressRows.every(row => {
    const ordered = quadrantOrder.map(index => row.cells[index]);
    return ordered.every((value, index) => index === 0 || value === 0 || ordered[index - 1] === 64);
  });
  const monotonicSingleSteps = fullCounts.every((value, index) =>
    index === 0 || (value >= fullCounts[index - 1] && value - fullCounts[index - 1] <= 1));
  const countSequence = [...new Set(fullCounts)];
  const fillMilestones = [1, 2, 3, 4].map(count =>
    menuProgressRows.find(row => row.cells.filter(value => value === 64).length >= count)?.elapsed_ms ?? null);
  const expectedMilestones = [1500, 2000, 2500, 3000];
  const milestonesNearExpected = fillMilestones.every((value, index) =>
    value !== null && Math.abs(value - expectedMilestones[index]) <= 260);
  const fullAt = menuProgressRows.findIndex(row => row.cells.every(value => value === 64));
  const terminalRows = fullAt >= 0 ? menuProgressRows.slice(fullAt) : [];

  const traceSince = startAt => page.evaluate(start =>
    window.__compReq599Snapshot().trace.filter(event => event.at >= start), startAt);
  const enterExpression = async () => {
    await page.click('[data-mode="expression"]');
    await page.waitForTimeout(60);
  };
  const center = { x: canvas.x + canvas.width / 2, y: canvas.y + canvas.height / 2 };
  const readMenuOrnamentInk = () => page.evaluate(() => {
    const pixels = document.querySelector("#face").getContext("2d").getImageData(84, 24, 32, 32).data;
    let ink = 0;
    for (let index = 0; index < pixels.length; index += 4) {
      if (pixels[index] < 128) ink += 1;
    }
    return ink;
  });

  await enterExpression();
  const singleStart = await page.evaluate(() => performance.now());
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  await page.waitForTimeout(180);
  const singleDuringArbitrationInk = await readMenuOrnamentInk();
  await page.mouse.up();
  await page.waitForTimeout(80);
  const singleImmediateTrace = await traceSince(singleStart);

  await enterExpression();
  const repeatedTapStart = await page.evaluate(() => performance.now());
  for (let index = 0; index < 5; index += 1) {
    await page.mouse.click(center.x, center.y);
    await page.waitForTimeout(80);
  }
  const repeatedTapTrace = await traceSince(repeatedTapStart);
  const expressionPressedAfterRepeatedTaps = await page.getAttribute('[data-mode="expression"]', 'aria-pressed');

  const recordingStart = {
    x: canvas.x + canvas.width * 0.08,
    y: canvas.y + canvas.height * 0.82
  };
  const recordingMid = {
    x: canvas.x + canvas.width * 0.17,
    y: canvas.y + canvas.height * 0.82
  };
  const recordingEnd = {
    x: canvas.x + canvas.width * 0.30,
    y: canvas.y + canvas.height * 0.82
  };
  await page.evaluate(() => window.__compReq743SetRecordingGesture('edge_pull'));
  const recordingSwipeStart = await page.evaluate(() => performance.now());
  await page.mouse.move(recordingStart.x, recordingStart.y);
  await page.mouse.down();
  await page.waitForTimeout(150);
  await page.mouse.move(recordingMid.x, recordingMid.y);
  await page.waitForTimeout(430);
  await page.locator("#face").screenshot({
    path: path.join(artifactRoot, "recording-mic-pull-mid.png")
  });
  await page.mouse.move(recordingEnd.x, recordingEnd.y);
  await page.waitForTimeout(120);
  await page.locator("#face").screenshot({
    path: path.join(artifactRoot, "recording-mic-pull-locked.png")
  });
  const recordingPressedWhileHeld = await page.getAttribute('[data-mode="recording"]', 'aria-pressed');
  const recordingHeldTrace = await traceSince(recordingSwipeStart);
  await page.mouse.up();
  await page.waitForTimeout(160);
  const recordingPressedAfterRecordingRelease = await page.getAttribute('[data-mode="recording"]', 'aria-pressed');
  const silenceExit = await page.evaluate(() =>
    window.__compReq753InjectVoiceControl('silence_stop'));
  await page.waitForFunction(() =>
    document.querySelector('[data-mode="expression"]')?.getAttribute('aria-pressed') === 'true',
    null,
    { timeout: 3500 });
  const recordingSwipeTrace = await traceSince(recordingSwipeStart);
  const expressionPressedAfterRecordingRelease = await page.getAttribute('[data-mode="expression"]', 'aria-pressed');

  await enterExpression();
  const invalidSwipeStart = await page.evaluate(() => performance.now());
  await page.mouse.move(center.x, canvas.y + canvas.height * 0.88);
  await page.mouse.down();
  await page.waitForTimeout(220);
  await page.mouse.move(center.x + canvas.width * 0.2, canvas.y + canvas.height * 0.58);
  await page.waitForTimeout(120);
  await page.mouse.up();
  await page.waitForTimeout(120);
  const invalidSwipeTrace = await traceSince(invalidSwipeStart);

  await page.evaluate(() => window.__compReq657RenderMenuScreen(4));
  await page.mouse.click(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.49);
  await page.waitForTimeout(100);
  const interactionMenuOpened = await page.evaluate(() => window.__compReq657MenuState());
  const defaultRecordingMenu = await page.evaluate(() =>
    window.__compReq743FreezeRecordingGestureMenu('corner_double_tap'));
  await page.locator("#face").screenshot({
    path: path.join(artifactRoot, "recording-gesture-menu-default.png")
  });
  await page.mouse.click(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.62);
  await page.waitForTimeout(100);
  const doubleRecordingMenu = await page.evaluate(() => ({
    menu: window.__compReq657MenuState(),
    contract: window.__compReq625Contract().gestures
  }));
  await page.locator("#face").screenshot({
    path: path.join(artifactRoot, "recording-gesture-menu-double.png")
  });

  await page.evaluate(() => window.__compReq743SetRecordingGesture('corner_double_tap'));
  await enterExpression();
  const doubleEnterStart = await page.evaluate(() => performance.now());
  await page.mouse.click(recordingStart.x, recordingStart.y);
  await page.waitForTimeout(100);
  await page.mouse.click(recordingStart.x, recordingStart.y);
  await page.waitForTimeout(120);
  const doubleEnterTrace = await traceSince(doubleEnterStart);
  const recordingPressedAfterDouble = await page.getAttribute('[data-mode="recording"]', 'aria-pressed');
  const doubleExitStart = await page.evaluate(() => performance.now());
  await page.mouse.click(center.x, center.y);
  await page.waitForTimeout(100);
  await page.mouse.click(center.x, center.y);
  await page.waitForFunction(() =>
    document.querySelector('[data-mode="expression"]')?.getAttribute('aria-pressed') === 'true',
    null,
    { timeout: 3500 });
  const doubleExitTrace = await traceSince(doubleExitStart);
  const expressionPressedAfterDoubleExit = await page.getAttribute('[data-mode="expression"]', 'aria-pressed');

  await page.evaluate(() => window.__compReq743FreezeRecordingGestureMenu('corner_double_tap'));
  await page.mouse.click(canvas.x + canvas.width * 0.5, canvas.y + canvas.height * 0.38);
  await page.waitForTimeout(100);
  const restoredDefaultGesture = await page.evaluate(() =>
    window.__compReq625Contract().gestures);
  await enterExpression();

  await enterExpression();
  const longPressStart = await page.evaluate(() => performance.now());
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  await page.waitForTimeout(3200);
  await page.mouse.up();
  await page.waitForTimeout(440);
  const longPressTrace = await traceSince(longPressStart);

  await enterExpression();
  const dragStart = await page.evaluate(() => performance.now());
  await page.mouse.move(center.x, center.y);
  await page.mouse.down();
  await page.waitForTimeout(180);
  await page.mouse.move(center.x + canvas.width * 0.18, center.y);
  await page.waitForTimeout(440);
  await page.mouse.up();
  await page.waitForTimeout(440);
  const dragTrace = await traceSince(dragStart);

  const singleTapCommitsImmediate = singleImmediateTrace.filter(event =>
    event.type === 'single_tap_commit').length;
  const repeatedTapCommits = repeatedTapTrace.filter(event =>
    event.type === 'single_tap_commit').length;
  const recordingEnterEvents = recordingSwipeTrace.filter(event => event.type === 'recording_enter');
  const recordingExitEvents = recordingSwipeTrace.filter(event => event.type === 'recording_exit');
  const recordingPreviewEvents = recordingSwipeTrace.filter(event =>
    event.type === 'recording_mic_pull_preview');
  const recordingPreviewIntervals = recordingPreviewEvents.slice(1).map((event, index) =>
    event.at - recordingPreviewEvents[index].at);
  const doubleEnterEvents = doubleEnterTrace.filter(event => event.type === 'recording_enter');
  const doubleExitEvents = doubleExitTrace.filter(event => event.type === 'recording_exit');
  const longMenuEvents = longPressTrace.filter(event => event.type === 'menu_enter');
  const result = {
    schema: "companion.comp_req_660.real_interaction.v1",
    status: "PASS_REAL_INTERACTION",
    checks: {
      browser_errors_zero: errors.length === 0,
      audio_first_motion_matches_500ms_visible_hold: Object.values(audio).every(row =>
        row.first_change_ms >= 480 && row.first_change_ms <= 720),
      audio_visible_commit_interval_exceeds_475ms_measured_transaction:
        Object.values(audio).every(row => row.minimum_commit_interval_ms >= 490),
      audio_body_remains_stable: Object.values(audio).every(row => row.unique_body_frames === 1),
      audio_motion_not_intensity: Object.values(audio).every(row =>
        Math.max(...row.ink_values) - Math.min(...row.ink_values) <= 4),
      audio_motion_has_extended_visual_vocabulary:
        Object.values(audio).every(row => row.unique_frames >= 5),
      audio_wave_packet_is_one_connected_polyline:
        Object.values(audio).every(row =>
          row.component_values.length === 1 && row.component_values[0] === 1),
      audio_wave_packet_never_touches_ornament_body:
        Object.values(audio).every(row => row.body_clearance_ok),
      audio_wave_packet_vertical_center_is_locked:
        Object.values(audio).every(row => row.centerline_locked),
      menu_idle_click_never_fills: idleMenuRows.every(row => row.every(value => value === 0)),
      menu_early_release_stops_and_clears:
        JSON.stringify(earlyReleasePartial) === JSON.stringify([64, 0, 0, 0])
        && earlyReleaseRows.every(row => row.every(value => value === 0)),
      menu_drag_cancel_stops_and_clears:
        dragCancelRows.every(row => row.every(value => value === 0)),
      menu_cells_are_discrete_whole_clockwise_steps: wholeCellOnly && quadrantPrefixOnly,
      menu_full_count_sequence_is_0_1_2_3_4:
        JSON.stringify(countSequence) === JSON.stringify([0, 1, 2, 3, 4])
        && monotonicSingleSteps,
      menu_milestones_after_1s_lead_at_500ms_steps: milestonesNearExpected,
      menu_enters_within_3300ms: fillMilestones[3] >= 2850 && fillMilestones[3] <= 3300,
      menu_acknowledgement_reaches_full_before_handoff: terminalRows.length >= 1
        && terminalRows.every(row => row.cells.every(value => value === 64)),
      menu_handoff_opens_existing_home_ui:
        menuStateAfterHandoff.active === true
        && menuStateAfterHandoff.screen === 'home',
      menu_root_detail_and_back_are_pointer_operable:
        menuDetailState.active === true
        && menuDetailState.screen === 'device'
        && menuBackState.active === true
        && menuBackState.screen === 'home',
      menu_vertical_scroll_is_bounded_and_nonactivating:
        menuScrolledState.active === true
        && menuScrolledState.screen === 'home'
        && menuScrolledState.scroll_offset > 0
        && menuScrolledState.scroll_offset <= menuScrolledState.scroll_max
        && menuNavigationTrace.filter(event => event.type === 'menu_scroll_end'
          && event.activated === false).length === 1,
      menu_post_scroll_tap_opens_correct_item:
        menuScrolledTapState.active === true
        && menuScrolledTapState.screen === 'preferences',
      menu_right_swipe_exits_without_row_activation:
        menuExitState.active === false
        && menuNavigationTrace.filter(event => event.type === 'menu_swipe_right').length === 1
        && menuNavigationTrace.filter(event => event.type === 'menu_exit').length === 1
        && menuNavigationTrace.filter(event => event.type === 'menu_row_open').length === 2,
      single_tap_commits_immediately_once:
        singleTapCommitsImmediate === 1
        && singleImmediateTrace.some(event =>
          event.type === 'single_tap_commit' && event.immediate === true)
        && singleImmediateTrace.every(event => event.type !== 'recording_enter'),
      short_tap_never_draws_menu_ornament: singleDuringArbitrationInk === 0,
      five_repeated_taps_all_reach_emotion_and_never_record:
        repeatedTapCommits === 5
        && expressionPressedAfterRepeatedTaps === 'true'
        && repeatedTapTrace.every(event => event.type !== 'recording_enter'),
      lower_left_microphone_visibly_tracks_pull:
        recordingPreviewEvents.length >= 2
        && recordingPreviewEvents.some(event => event.progress > 0 && event.progress < 1)
        && new Set(recordingPreviewEvents.map(event => event.origin.join(','))).size >= 2
        && recordingPreviewEvents.every(event =>
          event.axis === 'horizontal' && event.origin_y_fixed === 156)
        && recordingPreviewIntervals.every(interval => interval >= 490),
      lower_left_microphone_pull_enters_recording_while_held:
        recordingEnterEvents.length === 1
        && recordingEnterEvents[0].source === 'lower_left_horizontal_mic_pull'
        && recordingPressedWhileHeld === 'true'
        && recordingHeldTrace.some(event => event.type === 'recording_mic_pull_locked')
        && recordingSwipeTrace.every(event => event.type !== 'single_tap_commit'),
      releasing_recording_microphone_holds_until_silence_reverse_exit:
        recordingPressedAfterRecordingRelease === 'true'
        && silenceExit.accepted === true
        && recordingExitEvents.length === 1
        && recordingExitEvents[0].source === 'voice_activation.auto_stop_silence'
        && recordingSwipeTrace.filter(event =>
          event.type === 'recording_mic_retract_frame').length === 0
        && recordingSwipeTrace.filter(event =>
          event.type === 'commit' && event.phase === 'recording_exit_restore').length === 1
        && expressionPressedAfterRecordingRelease === 'true',
      non_left_corner_upward_drag_never_records:
        invalidSwipeTrace.every(event => event.type !== 'recording_enter')
        && invalidSwipeTrace.some(event => event.type === 'tease_release'),
      recording_gesture_menu_defaults_to_corner_double_and_switches:
        interactionMenuOpened.screen === 'recording_gesture'
        && defaultRecordingMenu.mode === 'corner_double_tap'
        && defaultRecordingMenu.default === true
        && doubleRecordingMenu.contract.recording_gesture_current === 'edge_pull'
        && doubleRecordingMenu.menu.screen === 'recording_gesture',
      corner_double_tap_enters_and_anywhere_double_exits_recording:
        doubleEnterEvents.length === 1
        && doubleEnterEvents[0].source === 'lower_left_double_tap'
        && recordingPressedAfterDouble === 'true'
        && doubleExitEvents.length === 1
        && doubleExitEvents[0].source === 'anywhere_double_tap'
        && expressionPressedAfterDoubleExit === 'true',
      menu_can_restore_default_corner_double_tap:
        restoredDefaultGesture.recording_gesture_current === 'corner_double_tap'
        && restoredDefaultGesture.double_tap === 'lower_left_start_and_anywhere_exit',
      long_press_only_enters_menu:
        longMenuEvents.length === 1
        && longPressTrace.every(event =>
          event.type !== 'recording_enter' && event.type !== 'single_tap_commit'),
      drag_cancels_all_gestures:
        dragTrace.some(event => event.type === 'menu_hold_cancel')
        && dragTrace.every(event =>
          event.type !== 'menu_enter'
          && event.type !== 'recording_enter'
          && event.type !== 'single_tap_commit')
    },
    evidence: {
      audio,
      menu: {
        idle_after_menu_click: idleMenuRows,
        early_release_partial: earlyReleasePartial,
        after_early_release: earlyReleaseRows,
        after_drag_cancel: dragCancelRows,
        whole_cell_only: wholeCellOnly,
        quadrant_order: ["upper_left", "upper_right", "lower_right", "lower_left"],
        quadrant_prefix_only: quadrantPrefixOnly,
        full_counts: fullCounts,
        count_sequence: countSequence,
        monotonic_single_steps: monotonicSingleSteps,
        fill_milestones_ms: fillMilestones,
        state_after_handoff: menuStateAfterHandoff,
        detail_state: menuDetailState,
        back_state: menuBackState,
        scrolled_state: menuScrolledState,
        scrolled_tap_state: menuScrolledTapState,
        exit_state: menuExitState,
        navigation_trace: menuNavigationTrace,
        full_at_sample: fullAt,
        handoff_at_sample: handoffAt,
        timeline: menuRows,
        stage_screenshots: menuStageScreenshots
      },
      gestures: {
        single_tap_menu_ornament_ink_during_arbitration: singleDuringArbitrationInk,
        single_immediate: singleImmediateTrace,
        repeated_taps: repeatedTapTrace,
        recording_held: recordingHeldTrace,
        recording_swipe: recordingSwipeTrace,
        invalid_non_bottom_swipe: invalidSwipeTrace,
        recording_menu_default: defaultRecordingMenu,
        recording_menu_double: doubleRecordingMenu,
        double_tap_enter: doubleEnterTrace,
        double_tap_exit: doubleExitTrace,
        restored_default_gesture: restoredDefaultGesture,
        long_press: longPressTrace,
        drag_cancel: dragTrace
      }
    },
    browser_errors: errors,
    hardware_contact: 0
  };
  if (!Object.values(result.checks).every(Boolean)) result.status = "NO_GO";
  fs.writeFileSync(outPath, `${JSON.stringify(result, null, 2)}\n`);
  console.log(JSON.stringify(result, null, 2));
  if (result.status !== "PASS_REAL_INTERACTION") process.exitCode = 1;
} finally {
  await browser?.close();
  server.close();
}
