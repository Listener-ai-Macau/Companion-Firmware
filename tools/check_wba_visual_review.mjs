#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'.cache/wba-visual-review');
const require=createRequire(import.meta.url);
let playwright;
for(const source of [process.env.COMPANION_PLAYWRIGHT_MODULE,'playwright',
  'C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright']){
  if(!source)continue;
  try{playwright=require(source);break;}catch{}
}
if(!playwright)throw new Error('Playwright unavailable');
const browser=await playwright.chromium.launch({headless:true});
const errors=[];
try{
  const page=await browser.newPage({viewport:{width:1280,height:1000}});
  page.on('pageerror',e=>errors.push(e.message));
  page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.goto(pathToFileURL(path.join(out,'index.html')).href);
  const images=await page.locator('img').evaluateAll(items=>items.every(i=>i.complete&&i.naturalWidth===200&&i.naturalHeight===200));
  if(!images)throw new Error('An actual native frame failed to load');
  const nativeCopy=await page.locator('body').textContent();
  if(!nativeCopy.includes('原生 200×200 黑白像素帧')||!nativeCopy.includes('不代表屏幕物理尺寸'))throw new Error('native pixel/physical-size disclosure missing');
  if(await page.locator('.art-link').getAttribute('href')!=='./art/index.html')throw new Error('art comparison link missing');
  const desktopGeometry=await page.evaluate(()=>{
    const screen=document.querySelector('#screen').getBoundingClientRect();
    const frame=getComputedStyle(document.querySelector('.screen-frame'));
    const thumbs=[...document.querySelectorAll('.family-choice img')].map(img=>{
      const r=img.getBoundingClientRect();return [r.width,r.height,getComputedStyle(img).borderRadius];
    });
    return {screen:[screen.width,screen.height],frameRadius:frame.borderRadius,
      rendering:getComputedStyle(document.querySelector('#screen')).imageRendering,thumbs};
  });
  if(desktopGeometry.screen[0]!==400||desktopGeometry.screen[1]!==400)throw new Error(`desktop default is not exact 2x: ${desktopGeometry.screen}`);
  if(desktopGeometry.frameRadius!=='0px'||desktopGeometry.thumbs.some(([w,h,r])=>w!==200||h!==200||r!=='0px'))throw new Error('screen or native thumbnails are rounded/non-native size');
  if(desktopGeometry.rendering!=='pixelated')throw new Error(`integer pixel rendering disabled: ${desktopGeometry.rendering}`);
  await page.locator('[data-scale="1"]').click();
  if((await page.locator('#screen').boundingBox()).width!==200)throw new Error('desktop 1x toggle is not 200px');
  await page.locator('[data-scale="2"]').click();
  if((await page.locator('#screen').boundingBox()).width!==400)throw new Error('desktop 2x toggle is not 400px');
  await page.locator('[data-frame="cue-recording"]').click();
  if(await page.locator('#label').textContent()!=='正在录音')throw new Error('recording control failed');
  await page.locator('[data-family="warm"]').click();
  if(!(await page.locator('#screen').getAttribute('src')).endsWith('family-warm.png'))throw new Error('family thumbnail did not select the main preview');
  await page.locator('#blink').click();
  await page.waitForFunction(()=>document.querySelector('#screen').getAttribute('src')==='images/family-warm-blink.png');
  if((await page.locator('#label').textContent()).startsWith('好奇'))throw new Error('selected-family blink fell back to curious');
  await page.waitForFunction(()=>document.querySelector('#screen').getAttribute('src')==='images/family-warm.png'&&document.querySelector('#label').textContent.includes('恢复'));
  await page.locator('#hold').click();
  await page.waitForFunction(()=>document.querySelector('#screen').getAttribute('src')==='images/hold-3.png');
  await page.locator('[data-frame="cue-idle"]').click();
  await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.reload();
  if((await page.locator('#screen').boundingBox()).width!==200)throw new Error('narrow default is not exact 1x');
  if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('mobile overflow');
  await page.locator('[data-scale="2"]').click();
  const mobileZoom=await page.evaluate(()=>{
    const viewport=document.querySelector('#screenViewport');
    const screen=document.querySelector('#screen').getBoundingClientRect();
    return {screen:[screen.width,screen.height],localScroll:viewport.scrollWidth>viewport.clientWidth,
      documentOverflow:document.documentElement.scrollWidth>innerWidth};
  });
  if(mobileZoom.screen[0]!==400||mobileZoom.screen[1]!==400||!mobileZoom.localScroll||mobileZoom.documentOverflow)throw new Error(`narrow 2x must scroll locally: ${JSON.stringify(mobileZoom)}`);
  await page.locator('[data-scale="1"]').click();
  await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
  if(errors.length)throw new Error(errors.join('\n'));
  const digest=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
  fs.writeFileSync(path.join(out,'browser-result.json'),JSON.stringify({result:'PASS_PREVIEW_UI_ONLY',
    nativeImages:11,nativeFrame:[200,200],desktopDefaultScale:2,narrowDefaultScale:1,
    controls:['recording','hold-four-milestones','selected-family-blink','idle','scale-1x-2x'],
    squarePixels:true,thumbnailNativePixels:true,narrowTwoXLocalScroll:true,mobileHorizontalOverflow:false,
    screenshots:['desktop.png','mobile.png'],sourceSha256:{
      'tools/render_wba_visual_review.py':digest(path.join(root,'tools/render_wba_visual_review.py')),
      'tools/check_wba_visual_review.mjs':digest(fileURLToPath(import.meta.url))},errors},null,2)+'\n');
  console.log('PASS_PREVIEW_UI_ONLY: square native pixels, integer 1x/2x, selected-family blink, desktop/mobile layout');
}finally{await browser.close();}
