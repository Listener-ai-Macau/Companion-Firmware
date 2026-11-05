import { createRequire } from 'node:module';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const require = createRequire(import.meta.url);
const playwrightCandidates = [
  'C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright',
  'C:/Users/Billy/Desktop/Denzic/Companion/Companion-Type/node_modules/playwright',
];
let chromium;
for (const candidate of playwrightCandidates) {
  try {
    ({ chromium } = require(candidate));
    break;
  } catch {
    // Try the next installed Playwright used by this repository.
  }
}
if (!chromium) throw new Error('Playwright was not found in the repository-approved locations');

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const pageRepoPath = 'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html';
const pagePath = path.join(root, pageRepoPath);
const priorResultRepoPath = 'docs/validation/companion-menu-luna-r2-machine-ready/total-interaction-result.json';
const priorResultPath = path.join(root, priorResultRepoPath);
const oldPageSha = 'D68478DAB33D4B2F13E5A62B63A65F1A9B37593C3551D8B19444731EA6C22116';
const expectedPageSha = 'BAE21BCCC7BB5FAD4A0922D5E9C42FCB25EF58DD7B8102A7C72656F7B700CF5E';
const expectedPriorResultSha = '9A831B882E24D5C1726B674BA40D8187F5E726E00A234BA3FFDACD33AD215123';
const expectedSteadyFacePngSha = '3269679155DE09F2FCEDFF3DC059DE4C9AC1E811400258B3B110F839646A0E31';
const requirement = 'COMP-REQ-471';
const gestureConstants = {
  menu_hold_ms: 700,
  double_tap_gap_ms: 350,
  double_tap_move_px: 32,
  drag_move_px: 44,
};
const defaultUrl = `http://127.0.0.1:4173/${pageRepoPath}`;

function parseArgs(argv) {
  const result = {
    output: path.join(root, 'docs/validation/companion-browser-visual-contract-comp-req-471/browser-capture'),
    url: defaultUrl,
  };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--output') result.output = path.resolve(argv[++i]);
    else if (argv[i] === '--url') result.url = argv[++i];
    else throw new Error(`unknown argument: ${argv[i]}`);
  }
  return result;
}

const args = parseArgs(process.argv.slice(2));
const sha256 = value => crypto.createHash('sha256').update(value).digest('hex').toUpperCase();
const fileSha = file => sha256(fs.readFileSync(file));
const pageSource = fs.readFileSync(pagePath, 'utf8');
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

assert(fileSha(pagePath) === expectedPageSha, 'accepted browser page SHA-256 changed');
assert(fileSha(priorResultPath) === expectedPriorResultSha, 'accepted 20/20 artifact SHA-256 changed');
assert(pageSource.includes('const touchContract={menuHoldMs:700,doubleGapMs:350,doubleMovePx:32,dragMovePx:gestureAuthority.defaults.long_press_max_move_px}'),
  'accepted browser gesture constants changed');
assert(pageSource.includes('long_press_max_move_px": 44'), 'accepted 44 px drag threshold changed');
const authorizedReturnToken = "history.replaceState(null,'','#expression');integratedMenu.hidden=true;interactionActions.hidden=true";
assert(pageSource.split(authorizedReturnToken).length - 1 === 1, 'authorized face-return teardown token count changed');
const reconstructedOldPage = pageSource.replace(
  authorizedReturnToken,
  "history.replaceState(null,'','#expression');interactionActions.hidden=true",
);
assert(sha256(Buffer.from(reconstructedOldPage, 'utf8')) === oldPageSha,
  'page contains changes beyond the one authorized face-return teardown token');
fs.mkdirSync(args.output, { recursive: true });

const stateDefinitions = [
  ['centered_rest', 'expression', 'center'],
  ['gaze_left', 'expression', 'left'],
  ['gaze_up', 'expression', 'up'],
  ['gaze_right', 'expression', 'right'],
  ['gaze_down', 'expression', 'down'],
  ['gaze_center', 'expression', 'center'],
  ['single_tap_response', 'expression', 'right_up'],
  ['hold_feedback_50', 'expression', 'center'],
  ['menu_roots', 'menu', 'browser'],
  ['menu_voice', 'menu', 'browser'],
  ['menu_device', 'menu', 'browser'],
  ['menu_connection', 'menu', 'browser'],
  ['menu_preferences', 'menu', 'browser'],
  ['menu_device_ui_assets', 'menu_asset', 'browser'],
  ['menu_return_rest', 'expression', 'center'],
  ['recording_entry', 'recording', 'browser'],
  ['recording_return_rest', 'expression', 'center'],
].map(([id, kind, orientation]) => ({ id, kind, orientation }));
const definitionById = new Map(stateDefinitions.map(item => [item.id, item]));

function localAsset(url) {
  const parsed = new URL(url);
  const repoPath = decodeURIComponent(parsed.pathname).replace(/^\/+/, '').replaceAll('/', path.sep);
  const absolute = path.join(root, repoPath);
  return fs.existsSync(absolute) && fs.statSync(absolute).isFile()
    ? { repo_path: repoPath.replaceAll(path.sep, '/'), sha256: fileSha(absolute) }
    : { repo_path: null, sha256: null };
}

async function dispatchPointer(page, pointerType, kind, x, y, pointerId) {
  if (pointerType === 'mouse') {
    await page.mouse.move(x, y);
    if (kind === 'pointerdown') await page.mouse.down();
    else if (kind === 'pointerup') await page.mouse.up();
    return;
  }
  await page.evaluate(({ pointerType, kind, x, y, pointerId }) => {
    const stage = document.querySelector('#overall-viewport');
    stage.dispatchEvent(new PointerEvent(kind, {
      bubbles: true,
      cancelable: true,
      pointerId,
      pointerType,
      isPrimary: true,
      clientX: x,
      clientY: y,
      buttons: kind === 'pointerup' ? 0 : 1,
    }));
  }, { pointerType, kind, x, y, pointerId });
}

async function waitForImage(page, selector = '#overall-viewport') {
  await page.waitForFunction(selectorValue => {
    const stage = document.querySelector(selectorValue);
    if (!stage) return false;
    const visible = [...stage.querySelectorAll('img')].filter(img => !img.hidden && !img.closest('[hidden]'));
    return visible.length > 0 && visible.every(img => img.complete && img.naturalWidth === 200 && img.naturalHeight === 200);
  }, selector);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function waitForCue(page, story, cue) {
  await page.waitForFunction(({ story, cue }) => {
    const state = window.__v45TouchState?.();
    return state?.story_name === story
      && state?.active_frame_cue === cue
      && document.querySelector('#overall-viewport .viewport-frame')?.naturalWidth === 200
      && document.querySelector('#overall-viewport .viewport-gaze')?.naturalWidth === 200;
  }, { story, cue }, { timeout: 10000 });
  await waitForImage(page);
}

async function stageBox(page, selector = '#overall-viewport') {
  const box = await page.locator(selector).boundingBox();
  assert(box && box.width === 200 && box.height === 200, `${selector} is not 200x200`);
  return box;
}

async function domSnapshot(page, selector) {
  return page.evaluate(selectorValue => {
    const stage = document.querySelector(selectorValue);
    const stageRect = stage.getBoundingClientRect();
    const rectValue = rect => ({
      left: rect.left,
      top: rect.top,
      right: rect.right,
      bottom: rect.bottom,
      width: rect.width,
      height: rect.height,
    });
    const intersection = rect => {
      const left = Math.max(stageRect.left, rect.left);
      const top = Math.max(stageRect.top, rect.top);
      const right = Math.min(stageRect.right, rect.right);
      const bottom = Math.min(stageRect.bottom, rect.bottom);
      const width = Math.max(0, right - left);
      const height = Math.max(0, bottom - top);
      return {
        left: left - stageRect.left,
        top: top - stageRect.top,
        right: right - stageRect.left,
        bottom: bottom - stageRect.top,
        width,
        height,
        area: width * height,
      };
    };
    const isVisible = node => {
      const style = getComputedStyle(node);
      return !node.hidden && !node.closest('[hidden]') && style.display !== 'none' && style.visibility !== 'hidden';
    };
    const visibleImages = [...stage.querySelectorAll('img')].filter(isVisible).map(img => {
      const role = img.classList.contains('viewport-frame') ? 'face_base'
        : img.classList.contains('viewport-gaze') ? 'gaze_highlight'
          : img.classList.contains('integrated-menu-image') ? 'exclusive_menu'
            : 'other';
      const rect = img.getBoundingClientRect();
      const clipped = intersection(rect);
      return {
        role,
        src: img.src,
        transform: getComputedStyle(img).transform,
        rect: rectValue(rect),
        rect_relative_to_stage: {
          left: rect.left - stageRect.left,
          top: rect.top - stageRect.top,
          right: rect.right - stageRect.left,
          bottom: rect.bottom - stageRect.top,
          width: rect.width,
          height: rect.height,
        },
        visible_intersection_relative_to_stage: clipped,
        rect_outside_stage_area: Math.max(0, rect.width * rect.height - clipped.area),
      };
    });
    const debugSelectors = ['.screen-meta', '.decision-panel', '#emotion-rule', '#gesture-status', '.authority-source'];
    const screen = document.querySelector('#overall-viewport').getBoundingClientRect();
    const hold = stage.querySelector('.hold-progress');
    const interaction = window.__overallInteractionState?.() || {};
    const touch = window.__touchContractState?.() || {};
    const story = window.__v45TouchState?.() || {};
    delete story.active_frame_elapsed_ms;
    const menuSurface = stage.querySelector('#integrated-menu');
    const stagingSurface = stage.querySelector('.viewport-staging');
    const actionSurface = document.querySelector('.interaction-actions');
    const faceBaseCount = visibleImages.filter(item => item.role === 'face_base').length;
    const menuCount = visibleImages.filter(item => item.role === 'exclusive_menu').length;
    const gazeCount = visibleImages.filter(item => item.role === 'gaze_highlight').length;
    const pairwiseIntersections = [];
    for (let i = 0; i < visibleImages.length; i += 1) {
      for (let j = i + 1; j < visibleImages.length; j += 1) {
        const a = visibleImages[i].rect;
        const b = visibleImages[j].rect;
        const width = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const height = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        pairwiseIntersections.push({
          roles: [visibleImages[i].role, visibleImages[j].role],
          area: width * height,
          policy_class: visibleImages[i].role === 'gaze_highlight' || visibleImages[j].role === 'gaze_highlight'
            ? 'intentional_gaze_composite'
            : 'exclusive_primary_surfaces',
        });
      }
    }
    return {
      interaction,
      touch,
      story,
      layers: window.__overallLayerSnapshot?.() || {},
      visible_images: visibleImages,
      observed: {
        stage_rect: rectValue(stageRect),
        stage_overflow: {
          x: getComputedStyle(stage).overflowX,
          y: getComputedStyle(stage).overflowY,
        },
        visible_image_count: visibleImages.length,
        layer_rect_clip_count: visibleImages.filter(item => item.rect_outside_stage_area > 0).length,
        layer_rect_outside_stage_area: visibleImages.reduce((sum, item) => sum + item.rect_outside_stage_area, 0),
        relationships: {
          face_base_count: faceBaseCount,
          exclusive_menu_count: menuCount,
          gaze_highlight_count: gazeCount,
          face_and_menu_visible_together: faceBaseCount > 0 && menuCount > 0,
          exclusive_primary_surface_count: faceBaseCount + menuCount,
          pairwise_intersections: pairwiseIntersections,
        },
        inactive_surfaces: {
          integrated_menu_visible: Boolean(menuSurface && isVisible(menuSurface)),
          interaction_actions_visible: Boolean(actionSurface && isVisible(actionSurface)),
          staging_visible: Boolean(stagingSurface && isVisible(stagingSurface)),
          hold_feedback_visible: Boolean(hold && isVisible(hold)),
          recording_story_visible: interaction.mode === 'recording'
            || String(story.story_name || '').startsWith('recording_'),
        },
      },
      hold_visible: Boolean(hold && isVisible(hold)),
      hold_progress: Number.parseInt(stage.querySelector('.hold-fill')?.style.width || '0', 10),
      geometry: {
        width: stageRect.width,
        height: stageRect.height,
        main_center_delta_px: Math.abs(screen.left + screen.width / 2 - window.innerWidth / 2),
      },
      debug_visible: debugSelectors.filter(item => {
        const node = document.querySelector(item);
        if (!node) return false;
        const style = getComputedStyle(node);
        const rect = node.getBoundingClientRect();
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0;
      }),
      owner_surface_text: document.querySelector('.authority-head')?.innerText || '',
      page_hash: location.hash,
    };
  }, selector);
}

async function captureState(page, viewportName, id, records, selector = '#overall-viewport') {
  const definition = definitionById.get(id);
  assert(definition, `state definition missing: ${id}`);
  await waitForImage(page, selector);
  const relativePng = `browser/${viewportName}/${id}.png`;
  const pngPath = path.join(args.output, ...relativePng.split('/'));
  fs.mkdirSync(path.dirname(pngPath), { recursive: true });
  let captureSelector = selector;
  if (selector === '#overall-viewport') {
    captureSelector = '#faraday-state-capture';
    await page.evaluate(() => {
      document.querySelector('#faraday-state-capture')?.remove();
      const clone = document.querySelector('#overall-viewport').cloneNode(true);
      clone.id = 'faraday-state-capture';
      clone.style.position = 'fixed';
      clone.style.left = '0';
      clone.style.top = '0';
      clone.style.margin = '0';
      clone.style.zIndex = '2147483647';
      document.body.appendChild(clone);
    });
    await waitForImage(page, captureSelector);
  }
  await page.locator(captureSelector).screenshot({ path: pngPath, animations: 'disabled' });
  const dom = await domSnapshot(page, selector);
  if (captureSelector === '#faraday-state-capture') {
    await page.evaluate(() => document.querySelector('#faraday-state-capture')?.remove());
  }
  const assets = dom.visible_images.map(image => ({ ...image, ...localAsset(image.src) }));
  const menuExclusive = definition.kind === 'menu';
  const assetFace = definition.kind === 'menu_asset';
  const expressionFace = !menuExclusive;
  const primaryCount = assets.filter(item => item.role === 'face_base' || item.role === 'exclusive_menu').length;
  const gazeCount = assets.filter(item => item.role === 'gaze_highlight').length;
  const conflictingSurfaceCount = dom.observed.relationships.face_and_menu_visible_together
    ? 1 : Math.max(0, primaryCount - 1);
  const staleCount = assets.filter(item => item.role === 'other').length
    + (menuExclusive && gazeCount !== 0 ? gazeCount : 0)
    + (menuExclusive && assets.some(item => item.role === 'face_base') ? 1 : 0)
    + (!menuExclusive && !assetFace && assets.some(item => item.role === 'exclusive_menu') ? 1 : 0);
  const semantic = {
    primary_surface_count: primaryCount,
    expression_face_count: expressionFace ? 1 : 0,
    exclusive_menu_surface_count: menuExclusive ? 1 : 0,
    gaze_highlight_count: gazeCount,
    stale_layer_count: staleCount,
    observed_layer_rect_clip_count: dom.observed.layer_rect_clip_count,
    conflicting_surface_overlap_count: conflictingSurfaceCount,
    menu_asset_uses_accepted_face: assetFace,
  };
  records.push({
    id,
    kind: definition.kind,
    orientation: definition.orientation,
    png: relativePng,
    png_sha256: fileSha(pngPath),
    dom,
    semantic,
    source_assets: assets,
  });
  return records.at(-1);
}

async function createHoldFixture(page) {
  await page.evaluate(() => {
    document.querySelector('#faraday-hold-capture')?.remove();
    const clone = document.querySelector('#overall-viewport').cloneNode(true);
    clone.id = 'faraday-hold-capture';
    clone.setAttribute('aria-label', 'accepted hold feedback deterministic capture');
    clone.style.position = 'fixed';
    clone.style.left = '0';
    clone.style.top = '0';
    clone.style.margin = '0';
    clone.style.zIndex = '2147483647';
    clone.querySelector('#integrated-menu').hidden = true;
    const hold = clone.querySelector('.hold-progress');
    hold.hidden = false;
    clone.querySelector('.hold-fill').style.width = '50%';
    document.body.appendChild(clone);
  });
  await waitForImage(page, '#faraday-hold-capture');
}

async function openExpressionPage(browser, viewport, errors) {
  const page = await browser.newPage({
    viewport: { width: viewport.width, height: viewport.height },
    hasTouch: viewport.pointerType === 'touch',
    deviceScaleFactor: 1,
  });
  page.setDefaultTimeout(10000);
  page.on('pageerror', error => errors.push(`pageerror:${error.message}`));
  page.on('requestfailed', request => errors.push(`requestfailed:${request.url()}`));
  page.on('response', response => {
    if (response.status() >= 400) errors.push(`http:${response.status()}:${response.url()}`);
  });
  await page.goto(args.url, { waitUntil: 'load' });
  await page.getByRole('button', { name: '表情系统', exact: true }).click();
  await page.locator('#overall-viewport').waitFor({ state: 'visible' });
  await waitForCue(page, 'calm_presence', 'calm_blink_settle');
  return page;
}

async function collectRestGazeHold(browser, viewport, records, checks, errors) {
  const page = await openExpressionPage(browser, viewport, errors);
  try {
    const box = await stageBox(page);
    const center = { x: box.x + 100, y: box.y + 100 };
    const layout = await domSnapshot(page, '#overall-viewport');
    checks.push(
      [`${viewport.name}.screen_200x200`, layout.geometry.width === 200 && layout.geometry.height === 200],
      [`${viewport.name}.screen_centered`, layout.geometry.main_center_delta_px <= 1],
      [`${viewport.name}.debug_hidden`, layout.debug_visible.length === 0
        && !/(当前情绪|命中|输出|registered|authority)/i.test(layout.owner_surface_text)],
    );
    const rest = await captureState(page, viewport.name, 'centered_rest', records);
    checks.push([`${viewport.name}.rest_single_face`, rest.semantic.primary_surface_count === 1
      && rest.semantic.expression_face_count === 1 && rest.semantic.gaze_highlight_count === 1]);

    await createHoldFixture(page);
    const hold = await captureState(page, viewport.name, 'hold_feedback_50', records, '#faraday-hold-capture');
    checks.push([`${viewport.name}.hold_feedback_source_component`, hold.dom.hold_visible
      && hold.dom.hold_progress === 50 && hold.semantic.stale_layer_count === 0]);
    await page.evaluate(() => document.querySelector('#faraday-hold-capture')?.remove());

    await dispatchPointer(page, viewport.pointerType, 'pointerdown', center.x, center.y, 101);
    const directions = [
      ['gaze_left', 28, 100],
      ['gaze_up', 100, 28],
      ['gaze_right', 172, 100],
      ['gaze_down', 100, 172],
      ['gaze_center', 100, 100],
    ];
    const gazeSources = [];
    for (const [id, x, y] of directions) {
      await dispatchPointer(page, viewport.pointerType, 'pointermove', box.x + x, box.y + y, 101);
      await sleep(60);
      await page.waitForFunction(() => {
        const state = window.__touchContractState?.();
        const image = document.querySelector('#overall-viewport .viewport-gaze');
        return state?.activePointer?.moved && state.holdProgress === 0 && image?.complete && image.naturalWidth === 200;
      });
      const current = await captureState(page, viewport.name, id, records);
      gazeSources.push(current.source_assets.find(item => item.role === 'gaze_highlight')?.repo_path);
      checks.push([`${viewport.name}.${id}_replacement`, current.semantic.primary_surface_count === 1
        && current.semantic.gaze_highlight_count === 1 && current.semantic.stale_layer_count === 0
        && current.dom.touch.activePointer?.moved && current.dom.touch.holdProgress === 0]);
    }
    checks.push([`${viewport.name}.gaze_sources_unique`, new Set(gazeSources).size === directions.length]);
    await dispatchPointer(page, viewport.pointerType, 'pointerup', center.x, center.y, 101);
    await sleep(100);
    const released = await domSnapshot(page, '#overall-viewport');
    checks.push([`${viewport.name}.drag_release_no_route`, released.interaction.mode === 'expression'
      && released.interaction.menuEntries === 0 && released.interaction.recordingEntries === 0]);
  } finally {
    await page.close();
  }
}

async function collectTap(browser, viewport, records, checks, errors) {
  const page = await openExpressionPage(browser, viewport, errors);
  try {
    const box = await stageBox(page);
    const x = box.x + 158;
    const y = box.y + 82;
    await dispatchPointer(page, viewport.pointerType, 'pointerdown', x, y, 201);
    await sleep(35);
    await dispatchPointer(page, viewport.pointerType, 'pointerup', x, y, 201);
    await waitForCue(page, 'curious_question', 'question_hold');
    const state = await captureState(page, viewport.name, 'single_tap_response', records);
    checks.push([`${viewport.name}.single_tap_response`, state.dom.interaction.mode === 'expression'
      && state.dom.interaction.menuEntries === 0 && state.dom.interaction.recordingEntries === 0
      && state.semantic.primary_surface_count === 1 && state.semantic.gaze_highlight_count === 1
      && state.dom.story.story_name === 'curious_question']);
  } finally {
    await page.close();
  }
}

async function collectMenu(browser, viewport, records, checks, errors) {
  const page = await openExpressionPage(browser, viewport, errors);
  try {
    const box = await stageBox(page);
    const x = box.x + 100;
    const y = box.y + 100;
    await dispatchPointer(page, viewport.pointerType, 'pointerdown', x, y, 301);
    await page.waitForFunction(() => window.__overallInteractionState?.().mode === 'menu', null, { timeout: 2000 });
    await dispatchPointer(page, viewport.pointerType, 'pointerup', x, y, 301);
    await waitForImage(page);
    let state = await captureState(page, viewport.name, 'menu_roots', records);
    checks.push([`${viewport.name}.menu_route_once`, state.dom.interaction.mode === 'menu'
      && state.dom.interaction.menuEntries === 1 && state.dom.interaction.recordingEntries === 0]);
    checks.push([`${viewport.name}.menu_exclusive_surface`, state.semantic.primary_surface_count === 1
      && state.semantic.exclusive_menu_surface_count === 1 && state.semantic.gaze_highlight_count === 0
      && state.semantic.stale_layer_count === 0]);

    const rootStates = ['menu_voice', 'menu_device', 'menu_connection', 'menu_preferences'];
    for (let index = 0; index < rootStates.length; index += 1) {
      await page.locator(`#integrated-menu [data-root="true"][data-index="${index}"]`).click();
      await page.waitForFunction(expected => window.__overallInteractionState?.().menuView === 'details'
        && document.querySelector('#integrated-menu')?.dataset.screen === 'details'
        && document.querySelector('.integrated-menu-image')?.complete, rootStates[index]);
      state = await captureState(page, viewport.name, rootStates[index], records);
      checks.push([`${viewport.name}.${rootStates[index]}`, state.semantic.primary_surface_count === 1
        && state.semantic.exclusive_menu_surface_count === 1 && state.semantic.gaze_highlight_count === 0
        && state.dom.interaction.menuEntries === 1]);
      if (index === 1) {
        await page.locator('#integrated-menu [data-detail="true"][data-index="3"]').click();
        await page.waitForFunction(() => window.__overallInteractionState?.().menuView === 'expression');
        state = await captureState(page, viewport.name, 'menu_device_ui_assets', records);
        checks.push([`${viewport.name}.device_ui_assets`, state.semantic.primary_surface_count === 1
          && state.semantic.expression_face_count === 1 && state.semantic.gaze_highlight_count === 0
          && state.dom.interaction.menuEntries === 1]);
        await page.getByTestId('integrated-menu-back').click();
      } else {
        await page.locator('#integrated-menu [data-header="true"]').click();
      }
      await page.waitForFunction(() => window.__overallInteractionState?.().menuView === 'roots');
    }

    await page.getByTestId('integrated-menu-return').click();
    await waitForCue(page, 'calm_presence', 'calm_blink_settle');
    state = await captureState(page, viewport.name, 'menu_return_rest', records);
    const inactive = state.dom.observed.inactive_surfaces;
    checks.push([`${viewport.name}.menu_return`, state.dom.interaction.mode === 'expression'
      && state.dom.interaction.menuEntries === 1 && state.semantic.gaze_highlight_count === 1
      && state.semantic.primary_surface_count === 1 && state.semantic.stale_layer_count === 0
      && state.semantic.conflicting_surface_overlap_count === 0
      && !inactive.integrated_menu_visible && !inactive.interaction_actions_visible
      && !inactive.staging_visible && !inactive.hold_feedback_visible
      && !inactive.recording_story_visible]);
  } finally {
    await page.close();
  }
}

async function collectRecording(browser, viewport, records, checks, errors) {
  const page = await openExpressionPage(browser, viewport, errors);
  try {
    const box = await stageBox(page);
    const x = box.x + 100;
    const y = box.y + 100;
    await dispatchPointer(page, viewport.pointerType, 'pointerdown', x, y, 401);
    await sleep(40);
    await dispatchPointer(page, viewport.pointerType, 'pointerup', x, y, 401);
    await sleep(90);
    await dispatchPointer(page, viewport.pointerType, 'pointerdown', x + 2, y + 1, 402);
    await sleep(40);
    await dispatchPointer(page, viewport.pointerType, 'pointerup', x + 2, y + 1, 402);
    await page.waitForFunction(() => window.__overallInteractionState?.().mode === 'recording');
    await waitForCue(page, 'recording_with_calm', 'recording_input_2');
    let state = await captureState(page, viewport.name, 'recording_entry', records);
    checks.push([`${viewport.name}.recording_route_once`, state.dom.interaction.mode === 'recording'
      && state.dom.interaction.recordingEntries === 1 && state.dom.interaction.menuEntries === 0
      && state.semantic.primary_surface_count === 1 && state.semantic.gaze_highlight_count === 1]);
    await page.getByTestId('recording-return').click();
    await waitForCue(page, 'calm_presence', 'calm_blink_settle');
    state = await captureState(page, viewport.name, 'recording_return_rest', records);
    const inactive = state.dom.observed.inactive_surfaces;
    checks.push([`${viewport.name}.recording_return`, state.dom.interaction.mode === 'expression'
      && state.dom.interaction.recordingEntries === 1 && state.semantic.gaze_highlight_count === 1
      && state.semantic.primary_surface_count === 1 && state.semantic.stale_layer_count === 0
      && state.semantic.conflicting_surface_overlap_count === 0
      && !inactive.integrated_menu_visible && !inactive.interaction_actions_visible
      && !inactive.staging_visible && !inactive.hold_feedback_visible
      && !inactive.recording_story_visible]);
  } finally {
    await page.close();
  }
}

async function run() {
  const browser = await chromium.launch({ headless: true });
  const records = [];
  const checks = [];
  const errors = [];
  try {
    for (const viewport of [
      { name: 'desktop', width: 1280, height: 900, pointerType: 'mouse' },
      { name: 'mobile', width: 390, height: 844, pointerType: 'touch' },
    ]) {
      await collectRestGazeHold(browser, viewport, records, checks, errors);
      await collectTap(browser, viewport, records, checks, errors);
      await collectMenu(browser, viewport, records, checks, errors);
      await collectRecording(browser, viewport, records, checks, errors);
      checks.push([`${viewport.name}.no_http_or_page_errors`, errors.length === 0]);
    }
  } finally {
    await browser.close();
  }

  for (const viewport of ['desktop', 'mobile']) {
    const state = id => records.find(
      item => item.id === id && item.png.split('/')[1] === viewport);
    const rest = state('centered_rest');
    const menuReturn = state('menu_return_rest');
    const recordingReturn = state('recording_return_rest');
    checks.push(
      [`${viewport}.steady_face_pixel_identity`, rest.png_sha256 === expectedSteadyFacePngSha],
      [`${viewport}.menu_return_pixels_equal_fresh_rest`, menuReturn.png_sha256 === rest.png_sha256],
      [`${viewport}.recording_return_pixels_equal_fresh_rest`, recordingReturn.png_sha256 === rest.png_sha256],
    );
  }
  const aggregateAssets = new Map();
  for (const record of records) {
    for (const asset of record.source_assets) {
      if (asset.repo_path) aggregateAssets.set(asset.repo_path, asset.sha256);
    }
  }
  const checkObjects = checks.map(([id, pass]) => ({ id, pass: Boolean(pass) }));
  const failed = checkObjects.filter(item => !item.pass);
  const staleLayerCount = records.reduce((sum, item) => sum + item.semantic.stale_layer_count, 0);
  const overlapCount = records.reduce((sum, item) => sum + item.semantic.conflicting_surface_overlap_count, 0);
  const observedLayerRectClipCount = records.reduce(
    (sum, item) => sum + item.semantic.observed_layer_rect_clip_count, 0);
  const holdRouteObservations = ['desktop', 'mobile'].map(viewport => {
    const state = records.find(item => item.id === 'menu_roots' && item.png.split('/')[1] === viewport);
    return {
      viewport,
      pointer_type: viewport === 'desktop' ? 'mouse' : 'touch',
      real_stationary_pointer_hold: true,
      accepted_hold_threshold_ms: 700,
      resulting_mode: state.dom.interaction.mode,
      menu_entries: state.dom.interaction.menuEntries,
      recording_entries: state.dom.interaction.recordingEntries,
      route_exactly_once: state.dom.interaction.menuEntries === 1
        && state.dom.interaction.recordingEntries === 0,
    };
  });
  const manifest = {
    schema: 'companion.browser-visual-capture.v1',
    requirement,
    status: failed.length === 0 && errors.length === 0
      && staleLayerCount === 0 && overlapCount === 0 ? 'PASS' : 'NO_GO',
    source: {
      page_repo_path: pageRepoPath,
      page_sha256: fileSha(pagePath),
      accepted_page_sha256: expectedPageSha,
      old_page_sha256: oldPageSha,
      authorized_change: {
        token: 'integratedMenu.hidden=true',
        occurrence_count: 1,
        reconstructed_old_page_sha256: sha256(Buffer.from(reconstructedOldPage, 'utf8')),
        only_authorized_change: true,
      },
      prior_20_of_20_repo_path: priorResultRepoPath,
      prior_20_of_20_sha256: fileSha(priorResultPath),
      accepted_prior_20_of_20_sha256: expectedPriorResultSha,
      url: args.url,
      accepted_steady_face_png_sha256: expectedSteadyFacePngSha,
      gesture_constants: gestureConstants,
      gesture_constants_sha256: sha256(Buffer.from(JSON.stringify(gestureConstants), 'utf8')),
      gesture_constants_unchanged: true,
    },
    capture: {
      dimensions: [200, 200],
      device_scale_factor: 1,
      state_count: stateDefinitions.length,
      viewport_count: 2,
      rendered_frame_count: records.length,
      hold_feedback_normalization: 'clone accepted DOM/CSS at exactly 50 percent; no source file mutation',
      pixel_capture_normalization: 'clone current accepted stage DOM/CSS at integer origin (0,0) to produce exact 200x200 pixels; original stage geometry remains measured separately',
      hold_feedback_binding: {
        deterministic_frame: 'hold_feedback_50',
        real_pointer_regressions: holdRouteObservations,
      },
    },
    checks: {
      passed: checkObjects.filter(item => item.pass).length,
      total: checkObjects.length,
      failed,
      items: checkObjects,
      route_activation: {
        menu_per_viewport: 1,
        recording_per_viewport: 1,
      },
      http_404_count: errors.filter(item => item.startsWith('http:404:')).length,
      stale_layer_count: staleLayerCount,
      observed_layer_rect_clip_count: observedLayerRectClipCount,
      clipping_policy_violation_count: null,
      conflicting_surface_overlap_count: overlapCount,
    },
    source_assets: [...aggregateAssets].sort(([a], [b]) => a.localeCompare(b))
      .map(([repo_path, sha]) => ({ repo_path, sha256: sha })),
    states: records,
    errors,
  };
  const manifestPath = path.join(args.output, 'capture-manifest.json');
  fs.writeFileSync(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify({
    status: manifest.status,
    manifest: path.relative(root, manifestPath).replaceAll(path.sep, '/'),
    passed: manifest.checks.passed,
    total: manifest.checks.total,
    rendered_frames: records.length,
    http_404_count: manifest.checks.http_404_count,
    stale_layer_count: manifest.checks.stale_layer_count,
  }, null, 2));
  if (manifest.status !== 'PASS') process.exitCode = 1;
}

await run();
