import {chromium} from '../browser/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const[url,out]=process.argv.slice(2);const browser=await chromium.launch({headless:true});const page=await browser.newPage();const errors=[];
page.on('pageerror',e=>errors.push(String(e)));
await page.addInitScript(()=>{window.workerTraffic=[];const Native=window.Worker;window.Worker=class extends Native{constructor(...a){super(...a);this.addEventListener('message',e=>window.workerTraffic.push({direction:'in',at:Date.now(),message:structuredClone(e.data)}));}postMessage(m,...a){window.workerTraffic.push({direction:'out',at:Date.now(),message:structuredClone(m)});return super.postMessage(m,...a);}};});
try{await page.goto(url);await page.waitForFunction(()=>window.retentionFinished||document.getElementById('retention-status')?.textContent.startsWith('FAIL:'),{},{timeout:300000});const status=await page.locator('#retention-status').textContent();if(status.startsWith('FAIL:'))throw Error(status);console.log('PRODUCTION_BROWSER_PASS');}
finally{fs.writeFileSync(out,JSON.stringify({errors,...await page.evaluate(()=>({traffic:window.workerTraffic,observed:window.groupedDemo?.observe(),result:document.getElementById('retention-result')?.textContent}))},null,2));await browser.close();}
