import {setup,root,hash,wait} from './v131-browser-support.mjs';
import {appendFile,writeFile} from 'node:fs/promises';
import {createServer} from 'node:net';
import assert from 'node:assert/strict';
const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const port=s.address().port;await new Promise(r=>s.close(r));
const kind=process.env.HEALTH_STATIC_BUILD==='1'?'built':'source';
const h=await setup('h1-'+kind,{health:{bind:`127.0.0.1:${port}`,readiness:{enter_offset_distance:2,exit_offset_distance:5,max_sample_age_ms:1500,enter_hold_ms:200,exit_hold_ms:300},sample_ms:500}});
try{
 await h.page.addInitScript(()=>{
  const workers=[];window.h1Workers=workers;const Original=window.Worker;window.Worker=new Proxy(Original,{construct(Target,args){const w=new Target(...args),entry={dead:false};workers.push(entry);const terminate=w.terminate.bind(w);w.terminate=()=>{entry.dead=true;terminate();};return w;}});
  const timers=new Set();window.h1Timers=timers;const set=window.setTimeout.bind(window),clear=window.clearTimeout.bind(window);window.setTimeout=(fn,ms,...args)=>{let id=set(()=>{timers.delete(id);fn(...args);},ms);timers.add(id);return id;};window.clearTimeout=id=>{timers.delete(id);clear(id);};
 });
 await h.page.goto(new URL('/health-demo.html',h.page.url()).href);await h.page.waitForFunction(()=>!!window.healthDemo);
 await h.server();await appendFile(h.feed,JSON.stringify({partition:0,offset:0,mutation:{kind:'upsert',row:{id:'h1',category:'a',label:{state:'missing'},quantity:'1',amount:{coefficient:'1',scale:0}}}})+'\n');
 await h.page.evaluate(({url,token})=>window.healthDemo.start(url,token),{url:h.url,token:h.token});
 await h.page.waitForFunction(()=>document.querySelector('output')?.textContent==='ready:ready'&&window.healthDemo.provider().getHealthSnapshot().status==='ready');
 const before=await h.page.evaluate(()=>{window.h1Provider=window.healthDemo.provider();return {snapshot:window.h1Provider.getHealthSnapshot(),observation:window.healthDemo.observe()};});
 // Healthy disconnect/reacquisition on this very same provider, before arming disposal.
 await h.shutdown();await h.page.waitForFunction(()=>window.healthDemo.provider().getHealthSnapshot().status==='stale');await h.server();
 await h.page.waitForFunction(old=>window.healthDemo.provider().getHealthSnapshot().status==='ready'&&window.healthDemo.provider().getHealthSnapshot().snapshot.instance!==old&&document.querySelector('output')?.textContent==='ready:ready',before.snapshot.snapshot.instance);
 await appendFile(h.feed,JSON.stringify({partition:0,offset:1,mutation:{kind:'upsert',row:{id:'h1',category:'a',label:{state:'missing'},quantity:'2',amount:{coefficient:'1',scale:0}}}})+'\n');
 await h.page.waitForFunction(()=>window.healthDemo.observe().deliveries.some(v=>v.whole.rows?.[0]?.quantity==='2'));
 const control=await h.page.evaluate(()=>{const p=window.healthDemo.provider(),o=window.healthDemo.observe();return {sameProvider:p===window.h1Provider,connection:p.connectionStatus,health:p.getHealthSnapshot(),whole:o.deliveries.filter(x=>x.whole.status==='ready').at(-1).whole.rows,viewport:o.rows.at(-1),workers:window.h1Workers.length};});assert(control.sameProvider);assert.equal(control.connection,'connected');assert.deepEqual(control.whole,[{id:'h1',quantity:'2'}]);assert.deepEqual(control.viewport,{'0':{id:'h1',quantity:'2'}});
 await h.page.evaluate(()=>{const p=window.healthDemo.provider();window.h1Ready=p.ready;window.h1Events=[];window.h1Off=p.subscribeHealth(()=>{window.h1Events.push(p.getHealthSnapshot().status);if(p.getHealthSnapshot().status==='stale'){p.dispose();window.h1Inside={connection:p.connectionStatus,health:p.getHealthSnapshot().status};}});});
 await h.shutdown();await h.page.waitForFunction(()=>window.h1Inside&&document.querySelector('output')?.textContent==='closed:closed');
 const inspect=()=>h.page.evaluate(async()=>{const p=window.healthDemo.provider();let settled=false;p.ready.then(()=>settled=true,()=>settled=true);await Promise.resolve();return {connection:p.connectionStatus,phase:p.connectionDiagnostics.phase,terminalCode:p.connectionDiagnostics.terminalCode,health:p.getHealthSnapshot().status,readyIdentity:p.ready===window.h1Ready,settled,admission:p.admission,workers:window.h1Workers.length,liveWorkers:window.h1Workers.filter(x=>!x.dead).length,providerTimers:['retryTimer','budgetTimer','connectTimer','healthyTimer','healthTimer'].filter(k=>window.h1Timers.has(p[k])),healthListeners:p.healthListeners.size,connectionListeners:p.connectionListeners.size,dom:document.querySelector('output')?.textContent,events:window.h1Events,inside:window.h1Inside};});
 const immediate=await inspect();await h.page.waitForTimeout(31000);const afterBudget=await inspect();
 for(const state of [immediate,afterBudget]){assert.equal(state.connection,'disconnected');assert.equal(state.phase,'disposed');assert.equal(state.terminalCode,'disposed');assert.equal(state.health,'closed');assert(state.readyIdentity&&state.settled);assert.equal(state.liveWorkers,0);assert.deepEqual(state.providerTimers,[]);assert.equal(state.admission.outstanding,0);assert.equal(state.admission.inFlight,0);assert.equal(state.admission.queued,0);assert.equal(state.admission.subscriptions,0);assert.equal(state.healthListeners,0);assert.equal(state.connectionListeners,0);assert.equal(state.dom,'closed:closed');}assert.equal(afterBudget.workers,immediate.workers);
 await h.page.evaluate(async()=>{window.h1Off();await window.healthDemo.dispose();});assert.equal(await h.page.evaluate(()=>window.healthDemo.provider().getHealthSnapshot().status),'closed');
 const result={passed:true,kind,scope:'actual ordinary fixture / production Worker / mounted both hooks and three badges; direct public observer disposal, plus healthy recovery on same provider',control,immediate,afterBudget,provider:await hash(root+'/browser/src/product-provider.tsx'),worker:await hash(root+'/browser/src/product.remote.worker.ts'),backend:await hash(root+'/bin/view_server')};
 await h.evidence(result);await writeFile(root+'/../h1-evidence/browser-'+kind+'.json',JSON.stringify(result,null,2));console.log(JSON.stringify({passed:true,kind,workers:immediate.workers,waitBeyondBudgetMs:31000}));
}finally{await h.cleanup();}
