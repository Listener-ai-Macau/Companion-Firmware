import { createRequire } from 'node:module';
const { chromium } = createRequire(import.meta.url)('C:/Users/Billy/Desktop/Denzic/Companion/Companion-Type/node_modules/playwright');
import fs from 'node:fs';
import path from 'node:path';

const root = 'http://127.0.0.1:4173';
const overall = `${root}/docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html`;
const menu = `${root}/docs/validation/companion-menu-luna-r2-machine-ready/index.html`;
const evidence = path.resolve('docs/validation/companion-menu-luna-r2-machine-ready');
fs.mkdirSync(evidence, { recursive: true });

const browser = await chromium.launch({ headless: true });
const result = { status: 'PASS', overall, menu, screenshots: [], checks: {} };
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const failures = [];
page.on('response', response => { if (response.status() >= 400) failures.push(`${response.status()} ${response.url()}`); });
page.on('requestfailed', request => failures.push(`requestfailed ${request.url()}`));

await page.goto(overall, { waitUntil: 'networkidle' });
await page.screenshot({ path: path.join(evidence, 'total-home-desktop.png'), fullPage: true });
result.screenshots.push('total-home-desktop.png');
result.checks.home = await page.locator('text=Companion 总体验收').isVisible();
result.checks.home_entries = await page.locator('#enter-expression').isVisible() && await page.locator('#enter-menu').isVisible();
result.checks.home_hides_expression = await page.locator('main').evaluate(node => getComputedStyle(node).display === 'none');

await page.click('#enter-expression');
await page.locator('#overall-viewport').waitFor({ state: 'visible' });
await page.screenshot({ path: path.join(evidence, 'total-expression-desktop.png'), fullPage: true });
result.screenshots.push('total-expression-desktop.png');
result.checks.expression_entry = await page.locator('#overall-viewport').isVisible();
await page.click('#return-home');
result.checks.expression_return = await page.locator('#enter-menu').isVisible() && await page.locator('main').evaluate(node => getComputedStyle(node).display === 'none');

await page.click('#enter-menu');
await page.waitForLoadState('networkidle');
result.checks.menu_entry = page.url().endsWith('/companion-menu-luna-r2-machine-ready/index.html');
result.checks.four_roots = await page.locator('.root-hit').count() === 4;
for (const label of ['Voice', 'Connection', 'Preferences']) {
  await page.getByRole('button', { name: label, exact: true }).click();
  result.checks[`root_${label.toLowerCase()}`] = await page.locator('.screen[data-screen="details"]').isVisible();
  await page.locator('[data-testid="detail-header"]').click();
}
await page.getByRole('button', { name: 'Device', exact: true }).click();
await page.getByRole('button', { name: 'UI assets', exact: true }).click();
result.checks.device_ui_assets = await page.locator('.screen[data-screen="expression"]').isVisible();
for (const label of ['Calm', 'Curious', 'Warm']) {
  await page.getByRole('button', { name: label, exact: true }).click();
  result.checks[`expression_${label.toLowerCase()}`] = await page.locator('.screen img').count() === 1;
}
await page.screenshot({ path: path.join(evidence, 'total-menu-expression-desktop.png'), fullPage: true });
result.screenshots.push('total-menu-expression-desktop.png');
await page.getByRole('button', { name: 'Back to menu', exact: true }).click();
result.checks.menu_back = await page.locator('.screen[data-screen="roots"]').isVisible();
await page.locator('.overall-link').click();
await page.waitForLoadState('networkidle');
result.checks.menu_return_home = page.url().includes('/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01/index.html#home');

await page.setViewportSize({ width: 390, height: 844 });
await page.goto(overall, { waitUntil: 'networkidle' });
await page.screenshot({ path: path.join(evidence, 'total-home-mobile.png'), fullPage: true });
result.screenshots.push('total-home-mobile.png');
await page.click('#enter-menu');
await page.waitForLoadState('networkidle');
await page.screenshot({ path: path.join(evidence, 'total-menu-mobile.png'), fullPage: true });
result.screenshots.push('total-menu-mobile.png');
result.checks.mobile_menu_visible = await page.locator('.screen').isVisible();
result.checks.no_404 = failures.length === 0;
result.failures = failures;
result.status = Object.values(result.checks).every(Boolean) ? 'PASS' : 'FAIL';
await browser.close();
console.log(JSON.stringify(result, null, 2));
if (result.status !== 'PASS') process.exit(1);
