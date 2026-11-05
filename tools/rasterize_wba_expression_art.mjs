// Compile editable SVG art at the panel's native resolution. No screenshot resizing.
import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
let pw;
for(const source of [process.env.COMPANION_PLAYWRIGHT_MODULE,'playwright',
  'C:/Users/Billy/AppData/Local/npm-cache/_npx/420ff84f11983ee5/node_modules/playwright']) {
  if(!source)continue;
  try {pw=require(source);break;} catch {}
}
if(!pw)throw Error('Playwright unavailable');
const directory=path.resolve(process.argv[2]);
const browser=await pw.chromium.launch({headless:true});
try {
  const page=await browser.newPage({viewport:{width:200,height:200},deviceScaleFactor:1});
  for(const name of fs.readdirSync(path.join(directory,'svg')).filter(n=>n.endsWith('.svg')).sort()) {
    const svg=fs.readFileSync(path.join(directory,'svg',name),'utf8');
    await page.setContent('<style>html,body{margin:0;width:200px;height:200px;overflow:hidden}svg{display:block}</style>'+svg);
    await page.screenshot({path:path.join(directory,'raster',name.replace('.svg','.png')),animations:'disabled'});
  }
} finally {await browser.close();}
