import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
const { chromium } = createRequire(import.meta.url)('C:/Users/Billy/Desktop/Denzic/Companion/Companion-Type/node_modules/playwright');
const url='http://127.0.0.1:4173/docs/validation/companion-menu-luna-r2-machine-ready/index.html';
const out='C:/Users/Billy/Desktop/Denzic/Companion/Companion-Firmware/docs/validation/companion-menu-luna-r2-machine-ready';
const cases=[['desktop',1000,760],['mobile',390,844]];
const b=await chromium.launch({headless:true});const evidence=[];
for(const [name,w,h] of cases){
  const p=await b.newPage({viewport:{width:w,height:h}});await p.goto(url);await p.evaluate(()=>window.menuReady);await p.waitForFunction(()=>window.menuState.ready);
  const screen=p.locator('#screen');const box=await screen.boundingBox();if(!box||box.width!==200||box.height!==200)throw new Error(`${name}: target screen not 200x200`);
  await p.screenshot({path:`${out}/${name}-menu.png`});
  await screen.locator('[data-testid="root-row"]').nth(1).click();await screen.locator('[data-testid="detail-row"]').nth(3).click();
  await p.waitForFunction(()=>window.menuState.view==='expression'&&document.querySelector('#screen').dataset.expression===undefined&&document.querySelector('#art').naturalWidth===200);
  if(await p.locator('[data-testid="expression-calm"]').count()!==1)throw new Error(`${name}: expression choices missing`);
  await p.locator('[data-testid="expression-warm"]').click();await p.waitForFunction(()=>window.menuState.expression==='warm');
  const screenState=await p.locator('#screen').getAttribute('data-screen');if(screenState!=='expression')throw new Error(`${name}: expression screen missing`);
  await p.screenshot({path:`${out}/${name}-expression-warm.png`});
  await p.locator('[data-testid="back-to-menu"]').click();await p.waitForFunction(()=>window.menuState.view==='roots');
  if(!(await p.locator('#art').getAttribute('data-asset')).endsWith('/en/01-home.png'))throw new Error(`${name}: menu did not restore`);
  await p.screenshot({path:`${out}/${name}-back.png`});
  await p.locator('[data-testid="root-row"]').nth(3).click();const detail=p.locator('#screen');const dbox=await detail.boundingBox();await p.mouse.move(dbox.x+80,dbox.y+130);await p.mouse.down();await p.mouse.move(dbox.x+80,dbox.y+70,{steps:4});await p.mouse.up();
  evidence.push({viewport:name,screen:[box.width,box.height],menu:'passed',expression:'warm',back:'passed',pointer_drag:'passed'});await p.close();
}
await b.close();console.log(JSON.stringify({status:'PASS',evidence,screenshots:fs.readdirSync(out).filter(x=>x.endsWith('.png')).sort()},null,2));
