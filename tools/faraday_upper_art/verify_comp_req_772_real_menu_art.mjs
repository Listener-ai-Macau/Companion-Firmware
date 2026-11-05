#!/usr/bin/env node
import crypto from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const artifactRoot = path.join(root, ".cache/validation/comp-req-772-real-menu-art");
const screenshotRoot = path.join(artifactRoot, "screenshots");
const fixedUrl =
  "http://127.0.0.1:4185/.cache/validation/comp-req-628-status-bar/index.html";
fs.mkdirSync(screenshotRoot, { recursive: true });

function loadPlaywright() {
  for (const name of [
    process.env.COMPANION_PLAYWRIGHT_MODULE,
    "playwright",
    "C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright"
  ].filter(Boolean)) {
    try { return require(name); } catch {}
  }
  throw new Error("Playwright unavailable");
}

function hash(values) {
  return crypto.createHash("sha256").update(Uint8Array.from(values)).digest("hex");
}

function crop(bits, left, top, right, bottom) {
  const result = [];
  for (let y = top; y < bottom; y += 1) {
    for (let x = left; x < right; x += 1) result.push(bits[y * 200 + x]);
  }
  return result;
}

function ink(bits, left, top, right, bottom) {
  return crop(bits, left, top, right, bottom).filter(Boolean).length;
}

const { chromium } = loadPlaywright();
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
const browserErrors = [];
page.on("pageerror", error => browserErrors.push(String(error)));
page.on("console", message => {
  if (message.type() === "error") browserErrors.push(message.text());
});

let result;
try {
  const response = await page.goto(fixedUrl, { waitUntil: "networkidle" });
  await page.waitForFunction(() =>
    typeof window.__compReq657RenderMenuScreen === "function"
    && typeof window.__compReq657MenuState === "function"
    && typeof window.__compReq772SetMenuLocale === "function"
    && typeof window.__compReq599Restore === "function");

  const sampleCanvas = async label => {
    const sample = await page.evaluate(name => {
      const canvas = document.querySelector("#face");
      const data = canvas.getContext("2d", { willReadFrequently: true })
        .getImageData(0, 0, 200, 200).data;
      const bits = [];
      const rgba = new Set();
      for (let offset = 0; offset < data.length; offset += 4) {
        bits.push(data[offset] < 128 ? 1 : 0);
        rgba.add(`${data[offset]},${data[offset + 1]},${data[offset + 2]},${data[offset + 3]}`);
      }
      return {
        label: name,
        bits,
        rgba: [...rgba].sort(),
        data_url: canvas.toDataURL("image/png")
      };
    }, label);
    sample.sha256 = hash(sample.bits);
    sample.status_sha256 = hash(crop(sample.bits, 0, 0, 200, 20));
    return sample;
  };

  const definitions = [
    ["root-top", 0, 0],
    ["root-bottom", 0, 7],
    ["voice-top", 1, 0],
    ["voice-bottom", 1, 6],
    ["display", 2, 0],
    ["connection-top", 3, 0],
    ["connection-bottom", 3, 6],
    ["preferences", 4, 0],
    ["recording-gesture", 5, 0],
    ["language", 6, 0],
    ["about-top", 7, 0],
    ["about-bottom", 7, 4],
    ["interaction-top", 8, 0],
    ["interaction-bottom", 8, 5],
    ["storage-top", 9, 0],
    ["storage-bottom", 9, 6],
    ["power-top", 10, 0],
    ["power-bottom", 10, 4],
    ["clear-recordings", 11, 0],
    ["restore-defaults", 12, 0]
  ];

  const renderLocale = async locale => {
    await page.evaluate(value => window.__compReq772SetMenuLocale(value), locale);
    const samples = [];
    for (const [name, index, item] of definitions) {
      await page.evaluate(([screen, selected]) =>
        window.__compReq657RenderMenuScreen(screen, selected), [index, item]);
      const sample = await sampleCanvas(`${locale}-${name}`);
      sample.state = await page.evaluate(() => window.__compReq657MenuState());
      samples.push(sample);
      await page.locator("#face").screenshot({
        path: path.join(
          screenshotRoot,
          `${String(samples.length).padStart(2, "0")}-${locale}-${name}.png`
        )
      });
    }
    return samples;
  };

  const zhScreens = await renderLocale("zh_cn");
  const enScreens = await renderLocale("en");
  await page.evaluate(() => window.__compReq772SetMenuLocale("zh_cn"));
  const screens = [...zhScreens, ...enScreens];

  const canvasBox = await page.locator("#face").boundingBox();
  if (!canvasBox) throw new Error("face canvas has no bounding box");
  const point = (x, y) => ({
    x: canvasBox.x + canvasBox.width * x / 200,
    y: canvasBox.y + canvasBox.height * y / 200
  });
  const tap = async (x, y, waitMs = 620) => {
    const target = point(x, y);
    await page.mouse.click(target.x, target.y);
    await page.waitForTimeout(waitMs);
  };
  const navigateTap = async (x, y, expectedScreen) => {
    const target = point(x, y);
    const startedAt = await page.evaluate(() => performance.now());
    await page.mouse.click(target.x, target.y);
    await page.waitForTimeout(90);
    const ack = await page.evaluate(() => window.__compReq657MenuState());
    const ackCanvas = await sampleCanvas(`navigation-ack-${expectedScreen}`);
    await page.waitForFunction(
      screen => {
        const state = window.__compReq657MenuState();
        return state.screen === screen && state.tap_ack === null;
      },
      expectedScreen,
      { timeout: 1400 }
    );
    const endedAt = await page.evaluate(() => performance.now());
    const after = await page.evaluate(() => window.__compReq657MenuState());
    return { ack, ackCanvas, after, elapsed_ms: Math.round(endedAt - startedAt) };
  };
  const settingTap = async (x, y, expectedItem) => {
    const target = point(x, y);
    const before = await page.evaluate(() => window.__compReq657MenuState());
    const startedAt = await page.evaluate(() => performance.now());
    await page.mouse.click(target.x, target.y);
    await page.waitForTimeout(90);
    const ack = await page.evaluate(() => window.__compReq657MenuState());
    const ackCanvas = await sampleCanvas(`setting-ack-${expectedItem}`);
    await page.waitForFunction(
      item => {
        const state = window.__compReq657MenuState();
        return state.tap_ack === null
          && state.layout_audit.some(row => row.id === item);
      },
      expectedItem,
      { timeout: 1400 }
    );
    const endedAt = await page.evaluate(() => performance.now());
    const after = await page.evaluate(() => window.__compReq657MenuState());
    return { before, ack, ackCanvas, after, elapsed_ms: Math.round(endedAt - startedAt) };
  };
  const actionTap = async (x, y, expectedItem, timeout = 1800) => {
    const target = point(x, y);
    const before = await page.evaluate(() => window.__compReq657MenuState());
    const startedAt = await page.evaluate(() => performance.now());
    await page.mouse.click(target.x, target.y);
    await page.waitForTimeout(90);
    const processing = await page.evaluate(() => window.__compReq657MenuState());
    const processingCanvas = await sampleCanvas(`action-processing-${expectedItem}`);
    await page.waitForFunction(
      item => {
        const state = window.__compReq657MenuState();
        return state.action_state?.item === item
          && state.action_state?.phase === "result";
      },
      expectedItem,
      { timeout }
    );
    const endedAt = await page.evaluate(() => performance.now());
    const resultState = await page.evaluate(() => window.__compReq657MenuState());
    return {
      before,
      processing,
      processingCanvas,
      result: resultState,
      elapsed_ms: Math.round(endedAt - startedAt)
    };
  };
  const rowCenter = async expectedItem => {
    const state = await page.evaluate(() => window.__compReq657MenuState());
    const row = state.layout_audit.find(candidate => candidate.id === expectedItem);
    if (!row) throw new Error(`row ${expectedItem} is not visible`);
    return row.centerY;
  };
  const swipe = async (fromX, fromY, toX, toY, inspectDuringMove = false) => {
    const start = point(fromX, fromY);
    const end = point(toX, toY);
    await page.mouse.move(start.x, start.y);
    await page.mouse.down();
    await page.mouse.move(end.x, end.y, { steps: 8 });
    const during = inspectDuringMove
      ? await page.evaluate(() => window.__compReq657MenuState())
      : null;
    await page.mouse.up();
    await page.waitForTimeout(100);
    const after = await page.evaluate(() => window.__compReq657MenuState());
    return { during, after };
  };
  const slowShortScroll = async label => {
    const start = point(100, 170);
    const end = point(100, 140);
    const before = await page.evaluate(() => window.__compReq657MenuState());
    await page.mouse.move(start.x, start.y);
    await page.mouse.down();
    await page.mouse.move(end.x, end.y, { steps: 4 });
    await page.waitForTimeout(80);
    const during = await page.evaluate(() => window.__compReq657MenuState());
    const duringCanvas = await sampleCanvas(`${label}-scroll-follow`);
    await page.mouse.up();
    await page.waitForTimeout(100);
    const after = await page.evaluate(() => window.__compReq657MenuState());
    const afterCanvas = await sampleCanvas(`${label}-scroll-settle`);
    return { before, during, duringCanvas, after, afterCanvas };
  };

  await page.evaluate(() => {
    window.__compReq772ResetPracticalMenuState();
    window.__compReq599Restore();
  });
  const hold = point(100, 100);
  await page.mouse.move(hold.x, hold.y);
  await page.mouse.down();
  await page.waitForTimeout(3260);
  await page.mouse.up();
  await page.waitForTimeout(300);
  const entered = await page.evaluate(() => window.__compReq657MenuState());

  const idleBefore = await page.evaluate(() => window.__compReq657MenuState());
  await page.waitForTimeout(1200);
  const idleAfter = await page.evaluate(() => window.__compReq657MenuState());

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 0));
  const rootOpenBefore = await page.evaluate(() => window.__compReq657MenuState());
  const voiceNavigation = await navigateTap(100, 60, "voice");
  const voiceOpened = voiceNavigation.after;
  const rootAckScreen = voiceNavigation.ackCanvas;
  fs.writeFileSync(
    path.join(screenshotRoot, "10-root-navigation-ack.png"),
    Buffer.from(rootAckScreen.data_url.split(",")[1], "base64")
  );
  const statusBefore = voiceOpened;
  await tap(100, 60);
  const statusAfter = await page.evaluate(() => window.__compReq657MenuState());
  const headerBackBefore = statusAfter;
  await tap(20, 10);
  const headerBackAfter = await page.evaluate(() => window.__compReq657MenuState());

  const rootRoutes = [];
  for (const [item, screen, index] of [
    ["voice", "voice", 0],
    ["display", "display", 1],
    ["interaction", "interaction", 2],
    ["connection", "connection", 3],
    ["storage_root", "storage", 4],
    ["power", "power", 5],
    ["preferences", "preferences", 6],
    ["about", "about", 7]
  ]) {
    await page.evaluate(selected => window.__compReq657RenderMenuScreen(0, selected), index);
    const before = await page.evaluate(() => window.__compReq657MenuState());
    const visibleRow = before.layout_audit.find(row => row.absoluteIndex === index);
    const navigation = await navigateTap(100, visibleRow.centerY, screen);
    rootRoutes.push({ item, screen, before, ...navigation });
  }

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 0));
  const rootScrollFollow = await slowShortScroll("root");
  const rootScrollToBottom = await swipe(100, 180, 100, 20, true);
  await page.locator("#face").screenshot({
    path: path.join(screenshotRoot, "10-root-scroll-bottom.png")
  });
  const rootScrollBackToTop = await swipe(100, 20, 100, 180, true);

  await page.evaluate(() => window.__compReq657RenderMenuScreen(1, 0));
  const scrollFollow = await slowShortScroll("voice");
  await page.locator("#face").screenshot({
    path: path.join(screenshotRoot, "10-voice-scroll-settle.png")
  });
  const scrollToBottom = await swipe(100, 170, 100, 70, true);
  const bottomStatusBefore = scrollToBottom.after;
  await tap(100, 174);
  const bottomStatusAfter = await page.evaluate(() => window.__compReq657MenuState());
  const scrollBackToTop = await swipe(100, 60, 100, 190, true);

  await page.evaluate(() => window.__compReq657RenderMenuScreen(1, 4));
  const autoStopSetting = await settingTap(100, await rowCenter("auto_stop"), "auto_stop");
  fs.writeFileSync(
    path.join(screenshotRoot, "10-setting-toggle-ack.png"),
    Buffer.from(autoStopSetting.ackCanvas.data_url.split(",")[1], "base64")
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(10, 2));
  const autoSleepSetting = await settingTap(100, await rowCenter("auto_sleep"), "auto_sleep");

  await page.evaluate(() => window.__compReq657RenderMenuScreen(3, 3));
  const autoReconnectSetting = await settingTap(
    100,
    await rowCenter("auto_reconnect"),
    "auto_reconnect"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(1, 2));
  const recorderProfileSetting = await settingTap(
    100,
    await rowCenter("recorder_profile"),
    "recorder_profile"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(8, 3));
  const gazeFollowSetting = await settingTap(
    100,
    await rowCenter("gaze_follow"),
    "gaze_follow"
  );
  const gazeDisabledContract = await page.evaluate(() =>
    window.__compReq625Contract().gestures.pointer_follow_enabled);
  const gazeFollowRestored = await settingTap(
    100,
    await rowCenter("gaze_follow"),
    "gaze_follow"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(8, 4));
  const naturalBlinkSetting = await settingTap(
    100,
    await rowCenter("natural_blink"),
    "natural_blink"
  );
  const naturalBlinkRestored = await settingTap(
    100,
    await rowCenter("natural_blink"),
    "natural_blink"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 7));
  const rootBottomBeforeAbout = await page.evaluate(() => window.__compReq657MenuState());
  const aboutNavigation = await navigateTap(100, 174, "about");
  const aboutOpened = aboutNavigation.after;
  const aboutBack = await swipe(50, 110, 155, 110);
  const rootRestored = aboutBack.after;

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 0));
  await tap(100, 60);
  const voiceMethodNavigation = await navigateTap(100, 100, "recording_gesture");
  const voiceMethodOpened = voiceMethodNavigation.after;
  const voiceMethodBack = await swipe(50, 110, 155, 110);
  const voiceRestored = voiceMethodBack.after;

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 2));
  await navigateTap(100, await rowCenter("interaction"), "interaction");
  await navigateTap(100, await rowCenter("recording_gesture"), "recording_gesture");
  const gestureOpened = await page.evaluate(() => window.__compReq657MenuState());
  const gestureBefore = await page.evaluate(() =>
    window.__compReq625Contract().gestures.recording_gesture_current);
  await tap(100, 100);
  const gestureOptionalState = await page.evaluate(() => window.__compReq657MenuState());
  const gestureOptional = await page.evaluate(() =>
    window.__compReq625Contract().gestures.recording_gesture_current);
  await tap(100, 60);
  const gestureRestoredState = await page.evaluate(() => window.__compReq657MenuState());
  const gestureRestored = await page.evaluate(() =>
    window.__compReq625Contract().gestures.recording_gesture_current);

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 6));
  await navigateTap(100, 174, "preferences");
  await navigateTap(100, await rowCenter("language"), "language");
  const languageBefore = await page.evaluate(() => window.__compReq657MenuState());
  await tap(100, 100);
  const languageEnglish = await page.evaluate(() => window.__compReq657MenuState());
  await tap(100, 60);
  const languageRestored = await page.evaluate(() => window.__compReq657MenuState());

  await page.evaluate(() => window.__compReq657RenderMenuScreen(5, 0));
  const singlePageDragBefore = await page.evaluate(() => window.__compReq657MenuState());
  const singlePageDrag = await swipe(100, 170, 100, 70, true);
  const emptyBefore = singlePageDrag.after;
  await tap(100, 174);
  const emptyAfter = await page.evaluate(() => window.__compReq657MenuState());

  await page.evaluate(() => window.__compReq657RenderMenuScreen(2, 0));
  const menuDoubleTapBefore = await page.evaluate(() => window.__compReq657MenuState());
  await tap(20, 180, 60);
  await tap(20, 180, 120);
  const menuDoubleTapAfter = await page.evaluate(() => window.__compReq657MenuState());

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 0));
  await tap(100, 180);
  const actionBefore = await page.evaluate(() => window.__compReq657MenuState());
  await tap(100, 100, 80);
  const actionProcessing = await page.evaluate(() => window.__compReq657MenuState());
  const processingScreen = await sampleCanvas("connection-processing");
  await page.locator("#face").screenshot({
    path: path.join(screenshotRoot, "10-connection-processing.png")
  });
  await page.waitForTimeout(760);
  const actionResult = await page.evaluate(() => window.__compReq657MenuState());

  await page.evaluate(() => window.__compReq657RenderMenuScreen(3, 2));
  const disconnectAction = await actionTap(
    100,
    await rowCenter("connection_toggle"),
    "connection_toggle"
  );
  const reconnectAction = await actionTap(
    100,
    await rowCenter("connection_toggle"),
    "connection_toggle"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(9, 2));
  const clearNavigation = await navigateTap(
    100,
    await rowCenter("clear_recordings"),
    "clear_recordings"
  );
  const clearAction = await actionTap(
    100,
    await rowCenter("confirm_clear"),
    "confirm_clear"
  );

  await page.evaluate(() => {
    window.__compReq772ResetPracticalMenuState();
    window.__compReq657RenderMenuScreen(4, 1);
  });
  const timeZoneSetting = await settingTap(
    100,
    await rowCenter("time_zone"),
    "time_zone"
  );
  await page.evaluate(() => window.__compReq657RenderMenuScreen(4, 3));
  const restoreNavigation = await navigateTap(
    100,
    await rowCenter("restore_defaults"),
    "restore_defaults"
  );
  const restoreAction = await actionTap(
    100,
    await rowCenter("confirm_restore"),
    "confirm_restore"
  );

  await page.evaluate(() => window.__compReq657RenderMenuScreen(0, 0));
  await tap(100, 60);
  const childBeforeSwipeBack = await page.evaluate(() => window.__compReq657MenuState());
  const childBack = await swipe(50, 110, 155, 110);
  const rootBeforeExit = childBack.after;
  const rootExit = await swipe(50, 110, 155, 110);
  const exited = rootExit.after;

  await page.evaluate(() => window.__compReq657RenderMenuScreen(10, 3));
  const sleepTarget = point(100, await rowCenter("sleep_now"));
  await page.mouse.click(sleepTarget.x, sleepTarget.y);
  const sleepProcessing = await page.evaluate(() => window.__compReq657MenuState());
  await page.waitForFunction(
    () => window.__compReq752Snapshot().locked === true,
    { timeout: 9000 }
  );
  const sleepLocked = await page.evaluate(() => window.__compReq752Snapshot());
  await page.evaluate(() => window.__compReq599Restore());

  const menuContract = await page.evaluate(() => {
    const menu = window.__compReq625Contract().menu_hold;
    return {
      terminal_surface: menu.terminal_surface,
      root_list: menu.root_list,
      child_menu: menu.child_menu,
      practical_information_architecture: menu.practical_information_architecture
    };
  });

  const overflowScreens = screens.filter(screen => screen.state.scroll_max > 0);
  const shortScreens = screens.filter(screen => screen.state.scroll_max === 0);
  const strictSamples = [
    ...screens,
    processingScreen,
    rootAckScreen,
    rootScrollFollow.duringCanvas,
    rootScrollFollow.afterCanvas,
    scrollFollow.duringCanvas,
    scrollFollow.afterCanvas,
    autoStopSetting.ackCanvas,
    autoSleepSetting.ackCanvas,
    autoReconnectSetting.ackCanvas,
    recorderProfileSetting.ackCanvas,
    gazeFollowSetting.ackCanvas,
    gazeFollowRestored.ackCanvas,
    naturalBlinkSetting.ackCanvas,
    naturalBlinkRestored.ackCanvas,
    disconnectAction.processingCanvas,
    reconnectAction.processingCanvas,
    clearAction.processingCanvas,
    restoreAction.processingCanvas
  ];
  const checks = {
    fixed_url_http_200: response?.status() === 200 && response.url() === fixedUrl,
    browser_errors_zero: browserErrors.length === 0,
    twenty_scroll_states_rendered_in_both_locales:
      zhScreens.length === 20 && enScreens.length === 20,
    strict_1bpp_all_pages_and_interactions: strictSamples.every(screen =>
      screen.rgba.every(value =>
        ["0,0,0,255", "255,255,255,255"].includes(value))),
    pages_visually_distinct_within_each_locale:
      new Set(zhScreens.map(screen => screen.sha256)).size === zhScreens.length
      && new Set(enScreens.map(screen => screen.sha256)).size === enScreens.length,
    status_bar_constant_across_menu_family:
      new Set(screens.map(screen => screen.status_sha256)).size === 1,
    four_row_viewport_is_stable:
      overflowScreens.every(screen =>
        screen.state.layout_audit.length === 4
        && screen.state.layout_audit.every(row =>
          row.top >= 34 && row.top <= 154 && row.fits)),
    overflow_lists_have_moving_scroll_indicator:
      overflowScreens.every(screen => ink(screen.bits, 196, 34, 200, 194) >= 20)
      && hash(crop(zhScreens[0].bits, 196, 34, 200, 194))
        !== hash(crop(zhScreens[1].bits, 196, 34, 200, 194)),
    short_lists_hide_scroll_indicator:
      shortScreens.every(screen => ink(screen.bits, 196, 34, 200, 194) === 0),
    child_pages_have_back_cue:
      [...zhScreens.filter(screen => screen.state.screen_index !== 0),
        ...enScreens.filter(screen => screen.state.screen_index !== 0)]
        .every(screen => ink(screen.bits, 7, 21, 21, 40) >= 12),
    bilingual_layout_tracks_do_not_overlap:
      screens.every(screen =>
        screen.state.layout_audit.every(row =>
          row.fits && (row.gap_px === null || row.gap_px >= 6))),
    eight_root_entries_and_real_child_counts:
      zhScreens[0].state.item_count === 8
      && [8, 7, 4, 7, 4, 2, 2, 5, 6, 7, 5, 3, 3].every((count, index) =>
        zhScreens.find(screen => screen.state.screen_index === index)?.state.item_count === count),
    no_idle_fixed_cadence_rerender:
      idleAfter.visible_commit_count === idleBefore.visible_commit_count
      && idleAfter.revision === idleBefore.revision,
    long_press_enters_root:
      entered.active && entered.screen === "home" && entered.stack_depth === 0,
    root_navigation_has_one_500ms_ack_then_destination:
      voiceOpened.screen === "voice"
      && voiceNavigation.ack.screen === "home"
      && voiceNavigation.ack.tap_ack?.item === "voice"
      && voiceNavigation.ack.visible_commit_count === rootOpenBefore.visible_commit_count + 1
      && voiceOpened.visible_commit_count === rootOpenBefore.visible_commit_count + 2
      && voiceNavigation.elapsed_ms >= 450
      && voiceNavigation.elapsed_ms <= 800,
    navigation_ack_band_is_full_row_and_stronger:
      ink(rootAckScreen.bits, 5, 44, 195, 76)
        > ink(zhScreens[0].bits, 5, 44, 195, 76) + 3000,
    all_eight_root_rows_ack_then_open_in_two_commits:
      rootRoutes.every(route =>
        route.after.active
        && route.after.screen === route.screen
        && route.after.stack_depth === 1
        && route.ack.screen === "home"
        && route.ack.tap_ack?.item === route.item
        && route.ack.visible_commit_count === route.before.visible_commit_count + 1
        && route.after.visible_commit_count === route.before.visible_commit_count + 2
        && route.elapsed_ms >= 450
        && route.elapsed_ms <= 800),
    root_scroll_follows_snaps_reaches_both_ends_without_activation:
      rootScrollFollow.before.scroll_offset === 0
      && rootScrollFollow.during.scroll_offset > 0
      && rootScrollFollow.during.scroll_offset < 40
      && rootScrollFollow.after.scroll_offset === 40
      && rootScrollFollow.after.scroll_offset % 40 === 0
      && rootScrollToBottom.after.scroll_offset === 160
      && rootScrollToBottom.after.scroll_max === 160
      && rootScrollBackToTop.after.scroll_offset === 0
      && rootScrollFollow.after.screen === "home"
      && rootScrollFollow.after.tap_ack === null
      && rootScrollToBottom.after.screen === "home"
      && rootScrollToBottom.after.stack_depth === 0,
    status_row_is_zero_revision_zero_refresh:
      statusAfter.revision === statusBefore.revision
      && statusAfter.visible_commit_count === statusBefore.visible_commit_count
      && statusAfter.selected_index === statusBefore.selected_index,
    bottom_status_row_is_zero_revision_zero_refresh:
      bottomStatusAfter.revision === bottomStatusBefore.revision
      && bottomStatusAfter.visible_commit_count === bottomStatusBefore.visible_commit_count,
    scroll_follows_direction_then_snaps_to_row:
      scrollFollow.before.scroll_offset === 0
      && scrollFollow.during.scroll_offset > 0
      && scrollFollow.during.scroll_offset < 40
      && scrollFollow.during.visible_commit_count
        === scrollFollow.before.visible_commit_count + 1
      && scrollFollow.after.scroll_offset === 40
      && scrollFollow.after.scroll_offset % 40 === 0
      && scrollFollow.after.visible_commit_count
        === scrollFollow.before.visible_commit_count + 2,
    scroll_reaches_bottom_and_returns_to_top:
      scrollToBottom.after.scroll_offset === 120
      && scrollToBottom.after.scroll_max === 120
      && scrollBackToTop.after.scroll_offset === 0,
    scroll_drag_never_activates_a_row:
      scrollFollow.after.screen === "voice"
      && scrollFollow.after.tap_ack === null
      && scrollFollow.after.action_state === null
      && scrollToBottom.after.screen === "voice"
      && scrollToBottom.after.stack_depth === 0,
    scroll_commits_are_bounded_not_pointermove_rate:
      scrollFollow.during.visible_commit_count - scrollFollow.before.visible_commit_count === 1
      && scrollFollow.after.visible_commit_count - scrollFollow.before.visible_commit_count === 2
      && rootScrollFollow.during.visible_commit_count
        - rootScrollFollow.before.visible_commit_count === 1
      && rootScrollFollow.after.visible_commit_count
        - rootScrollFollow.before.visible_commit_count === 2
      && menuContract.child_menu.pointer_drag_cadence_ms === 500
      && menuContract.root_list.continuous_drag_redraw === false,
    full_40x40_back_target_works:
      headerBackAfter.screen === "home"
      && headerBackAfter.visible_commit_count === headerBackBefore.visible_commit_count + 1,
    toggle_setting_has_ack_then_real_result:
      autoStopSetting.ack.tap_ack?.item === "auto_stop"
      && autoStopSetting.after.layout_audit.find(row => row.id === "auto_stop")?.checked === false
      && autoStopSetting.after.visible_commit_count
        === autoStopSetting.before.visible_commit_count + 2
      && autoStopSetting.elapsed_ms >= 450
      && autoStopSetting.elapsed_ms <= 800,
    cycle_setting_has_ack_then_real_result:
      autoSleepSetting.ack.tap_ack?.item === "auto_sleep"
      && autoSleepSetting.before.layout_audit.find(row => row.id === "auto_sleep")?.value === "3分钟"
      && autoSleepSetting.after.layout_audit.find(row => row.id === "auto_sleep")?.value === "5分钟"
      && autoSleepSetting.after.visible_commit_count
        === autoSleepSetting.before.visible_commit_count + 2,
    bottom_toggle_is_reachable_and_changes:
      autoReconnectSetting.before.scroll_offset === 0
      && autoReconnectSetting.ack.tap_ack?.item === "auto_reconnect"
      && autoReconnectSetting.after.layout_audit
        .find(row => row.id === "auto_reconnect")?.checked === false
      && autoReconnectSetting.after.visible_commit_count
        === autoReconnectSetting.before.visible_commit_count + 2,
    recorder_profile_setting_changes_real_state:
      recorderProfileSetting.before.practical_state.recorder_profile === "voice"
      && recorderProfileSetting.after.practical_state.recorder_profile === "meeting"
      && recorderProfileSetting.ack.tap_ack?.item === "recorder_profile"
      && recorderProfileSetting.after.visible_commit_count
        === recorderProfileSetting.before.visible_commit_count + 2,
    gaze_follow_toggle_changes_pointer_contract_and_restores:
      gazeFollowSetting.before.practical_state.gaze_follow === true
      && gazeFollowSetting.after.practical_state.gaze_follow === false
      && gazeDisabledContract === false
      && gazeFollowRestored.after.practical_state.gaze_follow === true,
    natural_blink_toggle_changes_scheduler_setting_and_restores:
      naturalBlinkSetting.before.practical_state.natural_blink === true
      && naturalBlinkSetting.after.practical_state.natural_blink === false
      && naturalBlinkRestored.after.practical_state.natural_blink === true,
    hierarchical_right_swipe_restores_root_scroll:
      rootBottomBeforeAbout.scroll_offset === 160
      && aboutOpened.screen === "about"
      && aboutOpened.stack_depth === 1
      && rootRestored.screen === "home"
      && rootRestored.scroll_offset === 160
      && rootRestored.stack_depth === 0
      && rootRestored.selected_index === 7,
    voice_start_method_opens_real_gesture_setting:
      voiceMethodOpened.screen === "recording_gesture"
      && voiceMethodOpened.stack_depth === 2
      && voiceMethodNavigation.ack.tap_ack?.item === "recording_start"
      && voiceRestored.screen === "voice"
      && voiceRestored.stack_depth === 1,
    recording_gesture_page_and_options_work:
      gestureOpened.screen === "recording_gesture"
      && gestureBefore === "corner_double_tap"
      && gestureOptional === "edge_pull"
      && gestureRestored === "corner_double_tap"
      && gestureOptionalState.visible_commit_count === gestureOpened.visible_commit_count + 1
      && gestureRestoredState.visible_commit_count
        === gestureOptionalState.visible_commit_count + 1,
    language_page_switches_once_and_restores_once:
      languageBefore.locale === "zh_cn"
      && languageEnglish.locale === "en"
      && languageEnglish.visible_commit_count === languageBefore.visible_commit_count + 1
      && languageRestored.locale === "zh_cn"
      && languageRestored.visible_commit_count === languageEnglish.visible_commit_count + 1,
    short_list_drag_and_empty_row_are_zero_refresh:
      singlePageDrag.during.visible_commit_count === singlePageDragBefore.visible_commit_count
      && singlePageDrag.after.visible_commit_count === singlePageDragBefore.visible_commit_count
      && emptyAfter.visible_commit_count === emptyBefore.visible_commit_count
      && emptyAfter.revision === emptyBefore.revision,
    menu_consumes_double_tap_without_recording_leak:
      menuDoubleTapAfter.active
      && menuDoubleTapAfter.screen === "display"
      && menuDoubleTapAfter.revision === menuDoubleTapBefore.revision,
    action_has_one_processing_and_one_result_commit:
      actionProcessing.action_state?.phase === "processing"
      && actionProcessing.visible_commit_count === actionBefore.visible_commit_count + 1
      && actionResult.action_state?.phase === "result"
      && actionResult.visible_commit_count === actionBefore.visible_commit_count + 2,
    connection_control_changes_state_and_can_reconnect:
      disconnectAction.before.practical_state.link_status === "connected"
      && disconnectAction.processing.action_state?.phase === "processing"
      && disconnectAction.result.practical_state.link_status === "disconnected"
      && reconnectAction.result.practical_state.link_status === "connected",
    destructive_recording_clear_requires_confirmation_and_changes_counts:
      clearNavigation.after.screen === "clear_recordings"
      && clearNavigation.after.stack_depth === 1
      && clearAction.processing.action_state?.phase === "processing"
      && clearAction.result.practical_state.recording_count === 0
      && clearAction.result.practical_state.recording_storage_kb === 0,
    restore_defaults_requires_confirmation_and_restores_user_settings:
      timeZoneSetting.after.practical_state.time_zone_offset_minutes === 0
      && restoreNavigation.after.screen === "restore_defaults"
      && restoreAction.processing.action_state?.phase === "processing"
      && restoreAction.result.practical_state.time_zone_offset_minutes === 480
      && restoreAction.result.practical_state.recorder_profile === "voice"
      && restoreAction.result.practical_state.gaze_follow === true,
    sleep_now_runs_drowsy_sequence_then_locks_low_power:
      sleepProcessing.action_state?.item === "sleep_now"
      && sleepProcessing.action_state?.phase === "processing"
      && sleepLocked.selected === "sleepy"
      && sleepLocked.locked === true
      && sleepLocked.scheduler_active === false,
    processing_band_is_local_and_stronger:
      ink(processingScreen.bits, 5, 84, 195, 106)
        > ink(zhScreens[5].bits, 5, 84, 195, 106) + 1600,
    child_right_swipe_returns_one_level:
      childBeforeSwipeBack.screen === "voice"
      && rootBeforeExit.active
      && rootBeforeExit.screen === "home"
      && rootBeforeExit.stack_depth === 0,
    root_right_swipe_exits_to_source:
      exited.active === false,
    contract_matches_scrollable_practical_semantics:
      menuContract.terminal_surface === "companion_native_full_width_four_row_menu_family"
      && menuContract.root_list.layout ===
        "four-row_viewport_over_scrollable_40px_root_list"
      && menuContract.root_list.item_model.length === 8
      && menuContract.root_list.reading_order.join(",") ===
        "voice,display,interaction,connection,storage_root,power,preferences,about"
      && menuContract.root_list.scroll_commit_cadence_ms === 500
      && menuContract.child_menu.layout ===
        "four-row_viewport_over_scrollable_40px_touch_list"
      && menuContract.child_menu.pointer_drag ===
        "directional_quantized_follow_at_epaper_cadence_then_row_snap"
      && menuContract.child_menu.scrollbar ===
        "content_proportional_right_edge_thumb_only_when_overflowing"
      && menuContract.child_menu.navigation_ack_ms === 500
      && menuContract.child_menu.visible_commits_per_navigation === 2
      && menuContract.practical_information_architecture.root.length === 8
      && menuContract.practical_information_architecture.voice.length === 7
      && menuContract.practical_information_architecture.display.length === 4
      && menuContract.practical_information_architecture.interaction.length === 6
      && menuContract.practical_information_architecture.connection.length === 7
      && menuContract.practical_information_architecture.storage.length === 7
      && menuContract.practical_information_architecture.power.length === 5
      && menuContract.practical_information_architecture.preferences.length === 4
      && menuContract.practical_information_architecture.about.length === 5
      && menuContract.practical_information_architecture.clear_recordings.length === 3
      && menuContract.practical_information_architecture.restore_defaults.length === 3
      && menuContract.child_menu.destructive_confirmation ===
        "dedicated_child_screen_with_cancel_and_explicit_confirm"
      && menuContract.practical_information_architecture
        .actionable_rows_have_observable_result === true
      && menuContract.practical_information_architecture.menu_recording_shortcut === false,
    hardware_contact_zero: true
  };

  await page.evaluate(cards => {
    document.body.innerHTML =
      "<main><h1>COMP-REQ-772 可滚动实用菜单总体验收</h1><section></section></main>";
    Object.assign(document.body.style, {
      margin: "0", background: "#202426", color: "#fff", fontFamily: "sans-serif"
    });
    Object.assign(document.querySelector("main").style, { padding: "20px" });
    Object.assign(document.querySelector("section").style, {
      display: "grid", gridTemplateColumns: "repeat(3, 400px)", gap: "20px"
    });
    for (const card of cards) {
      const figure = document.createElement("figure");
      const image = document.createElement("img");
      const caption = document.createElement("figcaption");
      Object.assign(figure.style, { margin: "0" });
      Object.assign(image.style, {
        width: "400px", height: "400px", imageRendering: "pixelated"
      });
      image.src = card.data_url;
      caption.textContent = card.label;
      figure.append(image, caption);
      document.querySelector("section").append(figure);
    }
  }, [
    ...screens,
    rootAckScreen,
    rootScrollFollow.duringCanvas,
    rootScrollFollow.afterCanvas,
    scrollFollow.duringCanvas,
    scrollFollow.afterCanvas,
    autoStopSetting.ackCanvas,
    recorderProfileSetting.ackCanvas,
    clearAction.processingCanvas,
    restoreAction.processingCanvas,
    processingScreen
  ].map(({ label, data_url }) => ({ label, data_url })));
  const contactSheet = path.join(screenshotRoot, "real-menu-bilingual-contact-sheet.png");
  await page.screenshot({ path: contactSheet, fullPage: true });

  result = {
    status: Object.values(checks).every(Boolean) ? "MACHINE_READY" : "NO_GO",
    requirement: "COMP-REQ-772",
    fixed_url: fixedUrl,
    hardware_contact: 0,
    checks,
    screens: strictSamples.map(screen => ({
      name: screen.label,
      sha256: screen.sha256,
      status_sha256: screen.status_sha256
    })),
    interaction: {
      entered,
      idle_before: idleBefore,
      idle_after: idleAfter,
      voice_navigation: {
        ack: voiceNavigation.ack,
        after: voiceNavigation.after,
        elapsed_ms: voiceNavigation.elapsed_ms,
        ack_canvas_sha256: voiceNavigation.ackCanvas.sha256
      },
      root_routes: rootRoutes.map(({ ackCanvas, ...route }) => ({
        ...route,
        ack_canvas_sha256: ackCanvas.sha256
      })),
      root_scroll_follow: {
        before: rootScrollFollow.before,
        during: rootScrollFollow.during,
        after: rootScrollFollow.after,
        during_canvas_sha256: rootScrollFollow.duringCanvas.sha256,
        after_canvas_sha256: rootScrollFollow.afterCanvas.sha256
      },
      root_scroll_to_bottom: rootScrollToBottom,
      root_scroll_back_to_top: rootScrollBackToTop,
      scroll_follow: {
        before: scrollFollow.before,
        during: scrollFollow.during,
        after: scrollFollow.after,
        during_canvas_sha256: scrollFollow.duringCanvas.sha256,
        after_canvas_sha256: scrollFollow.afterCanvas.sha256
      },
      scroll_to_bottom: scrollToBottom,
      scroll_back_to_top: scrollBackToTop,
      auto_stop_setting: {
        ...autoStopSetting,
        ackCanvas: undefined,
        ack_canvas_sha256: autoStopSetting.ackCanvas.sha256
      },
      auto_sleep_setting: {
        ...autoSleepSetting,
        ackCanvas: undefined,
        ack_canvas_sha256: autoSleepSetting.ackCanvas.sha256
      },
      auto_reconnect_setting: {
        ...autoReconnectSetting,
        ackCanvas: undefined,
        ack_canvas_sha256: autoReconnectSetting.ackCanvas.sha256
      },
      recorder_profile_setting: {
        ...recorderProfileSetting,
        ackCanvas: undefined,
        ack_canvas_sha256: recorderProfileSetting.ackCanvas.sha256
      },
      gaze_follow_setting: {
        disabled: gazeFollowSetting.after,
        restored: gazeFollowRestored.after,
        contract_while_disabled: gazeDisabledContract
      },
      natural_blink_setting: {
        disabled: naturalBlinkSetting.after,
        restored: naturalBlinkRestored.after
      },
      about_opened: aboutOpened,
      root_restored: rootRestored,
      gesture_opened: gestureOpened,
      gesture_optional: gestureOptional,
      gesture_restored: gestureRestored,
      language_before: languageBefore,
      language_english: languageEnglish,
      language_restored: languageRestored,
      action_before: actionBefore,
      action_processing: actionProcessing,
      action_result: actionResult,
      disconnect_action: {
        before: disconnectAction.before,
        processing: disconnectAction.processing,
        result: disconnectAction.result
      },
      reconnect_action: {
        before: reconnectAction.before,
        processing: reconnectAction.processing,
        result: reconnectAction.result
      },
      clear_navigation: clearNavigation.after,
      clear_action: {
        before: clearAction.before,
        processing: clearAction.processing,
        result: clearAction.result
      },
      time_zone_setting: timeZoneSetting.after,
      restore_navigation: restoreNavigation.after,
      restore_action: {
        before: restoreAction.before,
        processing: restoreAction.processing,
        result: restoreAction.result
      },
      sleep_processing: sleepProcessing,
      sleep_locked: sleepLocked,
      menu_double_tap_before: menuDoubleTapBefore,
      menu_double_tap_after: menuDoubleTapAfter,
      exited
    },
    menu_contract: menuContract,
    browser_errors: browserErrors,
    screenshot:
      ".cache/validation/comp-req-772-real-menu-art/screenshots/real-menu-bilingual-contact-sheet.png"
  };
} finally {
  await browser.close();
}

fs.writeFileSync(
  path.join(artifactRoot, "MACHINE_READY.json"),
  `${JSON.stringify(result, null, 2)}\n`
);
console.log(JSON.stringify(result, null, 2));
if (result.status !== "MACHINE_READY") process.exitCode = 1;
