const fs = require('fs');
const path = require('path');
const mainDir = path.dirname(require.main.filename);
const playwrightTestPath = [
  path.join(mainDir, 'test.js'),
  path.resolve(mainDir, '..', '..', 'test.js'),
  path.resolve(mainDir, '..', '..', '..', 'test.js'),
].find((candidate) => fs.existsSync(candidate));
if (!playwrightTestPath) throw new Error('Playwright test API was not found beside the active CLI/worker');
const playwrightTest = require(playwrightTestPath);
const { test, expect } = playwrightTest;

const REVISION = 'v45-touch-failsafe-r7-20260721';
const SINGLE = 'file:///C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html';
const EXPANDED = 'file:///C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/expanded-review-wall-01/index.html';
const BLINK_CUES = new Set(['calm_blink_closing', 'calm_blink_closed', 'calm_blink_opening']);

async function waitForCalmEntry(page, screen) {
  await expect(screen).toHaveAttribute('data-review-revision', 'v45-touch-failsafe-r7');
  await expect(screen).toHaveAttribute('data-cache-review', REVISION);
  await expect.poll(async () => screen.getAttribute('data-active-frame-cue'), { timeout: 5000 }).toBe('calm_entry');
  await expect.poll(
    async () => page.evaluate(() => typeof window.__v45TouchState === 'function' && window.__v45TouchState().gaze_hidden === false),
    { timeout: 5000 },
  ).toBe(true);
}

async function state(page) {
  return page.evaluate(() => {
    const screen = document.querySelector('#epaper-screen') || document.querySelector('.story .epaper-screen');
    const frame = screen.querySelector('.frame, #epaper-frame');
    const gaze = screen.querySelector('.gaze, #epaper-gaze');
    return {
    state: { ...window.__v45TouchState(), primary_src: frame.currentSrc, primary_hidden: frame.hidden, gaze_src: gaze.currentSrc, gaze_hidden_dom: gaze.hidden },
    trace: window.__v45TouchTrace.slice(),
    };
  });
}

function assertFrozenInteraction(before, during, releaseWindow) {
  expect(during.state.story_index).toBe(before.state.story_index);
  expect(during.state.active_frame_index).toBe(before.state.active_frame_index);
  expect(during.state.active_frame_cue).toBe(before.state.active_frame_cue);
  expect(BLINK_CUES.has(during.state.active_frame_cue)).toBe(false);
  expect(releaseWindow.state.story_index).toBe(before.state.story_index);
  expect(releaseWindow.state.active_frame_index).toBe(before.state.active_frame_index);
  expect(releaseWindow.state.active_frame_cue).toBe(before.state.active_frame_cue);
  expect(BLINK_CUES.has(releaseWindow.state.active_frame_cue)).toBe(false);
  const release = releaseWindow.trace.filter((item) => item.kind === 'touch_release').at(-1);
  expect(release).toBeTruthy();
  expect(release.frame_cue).toBe(before.state.active_frame_cue);
  expect(release.story_index).toBe(before.state.story_index);
  expect(release.resume_delay_ms).toBeGreaterThanOrEqual(180);
}

test.use({
  launchOptions: { executablePath: 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' },
  headless: true,
});

test('real mouse press, drag and release never hide the primary expression frame', async ({ page }) => {
  await page.goto(`${SINGLE}?review=${REVISION}`);
  const screen = page.locator('#epaper-screen');
  await expect(screen).toBeVisible();
  const box = await screen.boundingBox();
  if (!box) throw new Error('200x200 viewport has no bounding box');
  await waitForCalmEntry(page, screen);
  const before = await state(page);
  await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.48);
  await page.mouse.down();
  await page.waitForTimeout(80);
  const duringPress = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-real-browser-touch-press-20260721.png' });
  await page.mouse.move(box.x + box.width * 0.68, box.y + box.height * 0.52);
  await page.waitForTimeout(80);
  const duringDrag = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-real-browser-touch-drag-20260721.png' });
  await page.mouse.up();
  await page.waitForTimeout(120);
  const releaseWindow = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-real-browser-touch-release-20260721.png' });
  assertFrozenInteraction(before, duringPress, releaseWindow);
  expect(duringDrag.state.story_index).toBe(before.state.story_index);
  expect(duringDrag.state.active_frame_index).toBe(before.state.active_frame_index);
  expect(duringDrag.state.active_frame_cue).toBe(before.state.active_frame_cue);
  expect(BLINK_CUES.has(duringDrag.state.active_frame_cue)).toBe(false);
  console.log(JSON.stringify({ revision: REVISION, viewport: 'single', before, press: duringPress, drag: duringDrag, release: releaseWindow }));
});

test('expanded wall mouse input keeps the story viewport visible', async ({ page }) => {
  await page.goto(`${EXPANDED}?review=${REVISION}`);
  const screen = page.locator('.story').first().locator('.epaper-screen');
  await expect(screen).toBeVisible();
  const box = await screen.boundingBox();
  if (!box) throw new Error('expanded 200x200 viewport has no bounding box');
  const frame = screen.locator('.frame');
  const gaze = screen.locator('.gaze');
  await waitForCalmEntry(page, screen);
  const before = await state(page);
  await page.mouse.move(box.x + box.width * 0.72, box.y + box.height * 0.48);
  await page.mouse.down();
  await page.waitForTimeout(120);
  const duringPress = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-expanded-real-browser-touch-press-20260721.png' });
  await page.mouse.move(box.x + box.width * 0.68, box.y + box.height * 0.52);
  await page.waitForTimeout(120);
  const duringDrag = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-expanded-real-browser-touch-drag-20260721.png' });
  await page.mouse.up();
  await page.waitForTimeout(120);
  const releaseWindow = await state(page);
  await screen.screenshot({ path: 'docs/validation/companion-v45-expanded-real-browser-touch-release-20260721.png' });
  assertFrozenInteraction(before, duringPress, releaseWindow);
  expect(duringDrag.state.story_index).toBe(before.state.story_index);
  expect(duringDrag.state.active_frame_index).toBe(before.state.active_frame_index);
  expect(duringDrag.state.active_frame_cue).toBe(before.state.active_frame_cue);
  expect(BLINK_CUES.has(duringDrag.state.active_frame_cue)).toBe(false);
  console.log(JSON.stringify({ revision: REVISION, viewport: 'expanded-first-story', before, press: duringPress, drag: duringDrag, release: releaseWindow }));
});
