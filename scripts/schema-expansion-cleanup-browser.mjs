import {chromium} from '../browser/node_modules/playwright/index.mjs';
import fs from 'node:fs';
const [url,out,mode='red']=process.argv.slice(2);
const browser=await chromium.launch({headless:true});const page=await browser.newPage();
const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.addInitScript(()=>{window.workerTraffic=[];const Native=window.Worker;window.Worker=class extends Native{constructor(...args){super(...args);this.addEventListener('message',e=>window.workerTraffic.push({direction:'in',at:Date.now(),message:structuredClone(e.data)}));}postMessage(m,...args){window.workerTraffic.push({direction:'out',at:Date.now(),message:structuredClone(m)});return super.postMessage(m,...args);}};});
const save=async()=>{const result=await page.evaluate(()=>({observations:window.groupedDemo?.observe(),traffic:window.workerTraffic,probe:window.cleanupProbe}));fs.writeFileSync(out,JSON.stringify({mode,errors,...result},null,2));return result;};
try{
 await page.addInitScript(mode=>window.repairMode=mode,mode);await page.goto(url);await page.waitForFunction(()=>window.groupedDemo?.start);
 await page.evaluate(async()=>{const c=await(await fetch('/retention-case.json')).json();window.cleanupCase=c;window.groupedDemo.start(c.wsUrl,c.token,c.catalog,c.definitions,undefined,window.repairMode==='green');});
 await page.waitForFunction(()=>{const x=window.groupedDemo.observe().latest;return ['ordersRaw','ordersGroup','positionsRaw','positionsGroup'].every(n=>x[n]?.status==='ready');},{},{timeout:30000});
 await page.evaluate(async()=>{
  const p=window.groupedDemo.provider(),c=window.cleanupCase;const q={topic:'orders',schema:c.catalog.orders.fingerprint,select:['oo.name'],order_by:[],offset:0,limit:2};
  window.cleanupProbe={statuses:{control:[],a:[],b:[],...(window.repairMode==='green'?{health:[]}: {})},errors:[],results:{},controlBefore:structuredClone(window.groupedDemo.observe())};
  const listener=n=>Object.assign(r=>window.cleanupProbe.results[n]=r,{onStatus:s=>window.cleanupProbe.statuses[n].push(s),onError:e=>window.cleanupProbe.errors.push({name:n,error:e.message})});
  window.releaseControl=p.watch('cleanup-control',q,listener('control'));window.releaseA=p.watch('cleanup-a',q,listener('a'));window.releaseB=p.watch('cleanup-b',{...q,topic:'positions',schema:c.catalog.positions.fingerprint,select:['details.name']},listener('b'));if(window.repairMode==='green'){window.releaseHealth=p.watch('cleanup-health',q,listener('health'));window.unsubHealth=p.subscribeHealth(()=>{if(window.cleanupProbe.releaseOnHealth){window.cleanupProbe.releaseOnHealth=false;window.cleanupProbe.healthReentrant=true;window.releaseHealth();}});await p.apply({command:'open',subscription:'cleanup-direct',query:q});}
 });
 await page.waitForFunction(()=>Object.values(window.cleanupProbe.statuses).every(v=>v.at(-1)==='ready'));
 await page.evaluate(()=>window.releaseControl());
 await page.waitForFunction(()=>window.workerTraffic.some(x=>x.direction==='in'&&x.message.type==='ack'&&window.workerTraffic.some(y=>y.direction==='out'&&y.message.id===x.message.id&&y.message.command?.subscription==='cleanup-control'&&y.message.command?.command==='close')));
 await page.evaluate(async()=>{window.cleanupProbe.controlAfter={diagnostics:window.groupedDemo.observe().diagnostics,admission:window.groupedDemo.observe().admission};await fetch('/result',{method:'POST',body:JSON.stringify({stage:'cleanup_ready',status:'PASS'})});});
 {const deadline=Date.now()+50000;for(;;){const response=await page.request.get(new URL('/phase.json',url).href);if(response.ok()&&(await response.json()).phase==='release')break;if(Date.now()>deadline)throw Error('pending-phase deadline');await page.waitForTimeout(50);}}
 await page.evaluate(async()=>{window.cleanupProbe.beforeRelease={health:await(await fetch('/health')).json(),observations:structuredClone(window.groupedDemo.observe())};if(!window.cleanupProbe.beforeRelease.health.sources.find(s=>s.topic==='orders').retention.pending_due)throw Error('release did not observe pending retention');window.releaseA();if(window.repairMode==='green'){window.groupedDemo.unmount('ordersRaw');window.cleanupProbe.releaseOnHealth=true;window.directClose=window.groupedDemo.provider().apply({command:'close',subscription:'cleanup-direct'}).then(()=>window.cleanupProbe.directClose='ack',e=>window.cleanupProbe.directClose=String(e));}await fetch('/result',{method:'POST',body:JSON.stringify({stage:'release_queued',status:'PASS'})});});
 if(mode==='red')await page.waitForFunction(()=>window.groupedDemo.observe().diagnostics.phase==='failed',{},{timeout:15000});
 else await page.waitForFunction(()=>window.workerTraffic.some(x=>x.direction==='in'&&x.message.type==='ack'&&window.workerTraffic.some(y=>y.direction==='out'&&y.message.id===x.message.id&&y.message.command?.subscription==='cleanup-a'&&y.message.command?.command==='close')),{},{timeout:15000});
 if(mode==='green')await page.waitForFunction(()=>window.cleanupProbe.healthReentrant&&window.cleanupProbe.directClose==='ack');
 await page.evaluate(()=>{window.cleanupProbe.afterRelease=structuredClone(window.groupedDemo.observe());});
 const result=await save();
 const control=result.probe.controlBefore.latest;
 if(control.ordersRaw.rows.length!==520||control.ordersGroup.rows[0].count!=='520'||control.ordersGroup.rows[0].sum!=='520'||control.positionsRaw.rows.length!==1)throw Error('nested initial oracle');
 await page.waitForFunction(()=>window.groupedDemo.observe().latest.ordersGroup.rows.length===0);
 if(mode==='red'&&!result.traffic.some(x=>x.message.type==='request_error'&&x.message.error==='retention maintenance pending'))throw Error('missing actual native rejection');
 if(mode!=='red'&&result.probe.afterRelease.diagnostics.phase==='failed')throw Error('provider failed');
 if(mode==='green'){await page.evaluate(async()=>{window.cleanupProbe.peerNavigation=await window.groupedDemo.provider().apply({command:'change_window',subscription:'cleanup-b',offset:0,limit:1});});await page.waitForTimeout(1200);await page.evaluate(async()=>{window.cleanupProbe.afterHealth=await(await fetch('/health')).json();if(window.cleanupProbe.afterHealth.subscriptions!==10)throw Error('native resource count after cleanup '+window.cleanupProbe.afterHealth.subscriptions);window.unsubHealth();await window.groupedDemo.dispose();});}
 await page.evaluate(async mode=>{await fetch('/result',{method:'POST',body:JSON.stringify({stage:'cleanup_complete',status:'PASS',mode})});},mode);
 await page.waitForTimeout(1500);await save();
 console.log(JSON.stringify({mode,status:mode==='red'?'REPRODUCED':'PASS',out}));
}catch(e){await save();throw e;}finally{await browser.close();}
