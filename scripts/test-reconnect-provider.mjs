import {readFile,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {webcrypto} from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const root=new URL('../',import.meta.url).pathname;
const {transformWithOxc}=await import(createRequire(root+'browser/package.json').resolve('vite'));
let {code}=await transformWithOxc(await readFile(root+'browser/src/product-provider.tsx','utf8'),'provider.tsx',{jsx:{runtime:'classic'}});
code=code.replace(/import[\s\S]*?from "react";/,'const createContext=()=>({});').replaceAll('import.meta.url','"file:///provider.js"').replace(/export /g,'')+'\nglobalThis.Provider=BrowserProductProvider;';
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2,projection:['id']};
const tick=async()=>{for(let i=0;i<8;i++)await Promise.resolve();};
function setup(policy={}) {
 let now=0,id=0;const timers=new Map(),workers=[];
 class Worker{sent=[];dead=false;constructor(){workers.push(this);}postMessage(m){this.sent.push(m);}terminate(){this.dead=true;}}
 const context=vm.createContext({Worker,URL,structuredClone,crypto:webcrypto,Uint8Array,performance:{now:()=>now},Math:Object.assign(Object.create(Math),{random:()=>0}),setTimeout:(fn,ms)=>{timers.set(++id,{fn,at:now+ms});return id;},clearTimeout:id=>timers.delete(id)});vm.runInContext(code,context);
 const p=new context.Provider({mode:'remote',url:'ws://127.0.0.1:8080/v14',token:'test-token',subscriptions:70,recovery:{initialDelayMs:100,maxDelayMs:800,budgetMs:5000,maxAttempts:5,healthyMs:2000,...policy}});
 const frame=(w,m)=>w.onmessage({data:m});
 const advance=async ms=>{const end=now+ms;for(;;){const t=[...timers].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at)[0];if(!t)break;now=t[1].at;timers.delete(t[0]);t[1].fn();await tick();}now=end;await tick();};
 const ready=async()=>{frame(workers.at(-1),{type:'ready'});await tick();};
 const ack=async(request,w=workers.at(-1),version=1)=>{assert(request);const sub=request.command.subscription;frame(w,{type:'ack',id:request.id,traceparent:request.traceparent,results:request.command.command==='close'?{}:{[sub]:{subscription:sub,query_generation:request.acquisition,sequence:1,start_rank:request.command.query?.offset??request.command.offset??0,version,total_rows:0,rows:[]}},acquisitions:{[sub]:request.acquisition}});await tick();};
 const lost=()=>frame(workers.at(-1),{type:'fatal',error:'lost; pending completion uncertain',recoverable:true,code:'network'});
 return {p,workers,timers,frame,advance,ready,ack,lost};
}
const cases=[];
{
 const h=setup(),states=[],seen=[],status=[];const removers=Array.from({length:12},()=>h.p.subscribeConnectionStatus(()=>states.push(h.p.connectionStatus)));
 const stop=h.p.watch('s',q,Object.assign(r=>seen.push(r),{onStatus:s=>status.push(s)}));assert.equal(h.workers.length,1);await h.ready();await h.ack(h.workers[0].sent.at(-1));assert.equal(status.at(-1),'ready');assert.equal(seen[0].rows.length,0);
 const prior=seen[0],old=h.workers[0],oldCallback=old.onmessage;h.lost();assert.equal(h.p.connectionStatus,'connecting');assert.equal(status.at(-1),'stale');assert.equal(seen.length,1);await h.advance(50);assert.equal(h.workers.length,2);assert(old.dead);await h.ready();assert.equal(status.at(-1),'stale');assert.equal(h.p.connectionStatus,'connected');
 oldCallback({data:{type:'fatal',recoverable:false,error:'obsolete'}});oldCallback({data:{type:'ready'}});assert.equal(h.p.connectionStatus,'connected');await h.ack(h.workers[1].sent.at(-1),h.workers[1],0);assert.equal(status.at(-1),'ready');assert.equal(seen.length,2);assert.equal(prior.version,1);assert.equal(seen[1].version,0,'fresh incarnation may have lower native version');
 stop();await tick();await h.ack(h.workers[1].sent.at(-1));assert.equal(status.at(-1),'closed');for(const remove of removers)remove();h.p.dispose();assert.equal(h.timers.size,0);assert.equal(h.p.admission.subscriptions,0);cases.push('shared status, valid empty ready, stale preserved, fresh lower-version snapshot, old callback fenced, release cleanup');
}
{
 const h=setup(),errors=[],status=[];h.p.watch('s',q,Object.assign(()=>{},{onStatus:s=>status.push(s),onError:e=>errors.push(e.message)}));await h.ready();await h.ack(h.workers[0].sent.at(-1));
 const interrupted=h.p.apply({command:'change_window',subscription:'s',offset:4,limit:2}).catch(e=>e.code);await tick();h.lost();assert.equal(await interrupted,'transport_uncertain');
 await assert.rejects(h.p.apply({command:'upsert',row:{}}),/not replayed/);
 for(const offset of [6,8,10])await assert.rejects(h.p.apply({command:'change_window',subscription:'s',offset,limit:2}),/retained/);
 await h.advance(50);await h.ready();assert.equal(h.workers[1].sent.filter(m=>m.type==='apply').length,1);assert.equal(h.workers[1].sent.at(-1).command.query.offset,10);await h.ack(h.workers[1].sent.at(-1));assert.equal(errors.length,0);h.p.dispose();cases.push('original promise settled once, no writes replayed, latest offline window only');
}
{
 const h=setup(),statusA=[],statusB=[],errors=[];h.p.watch('a',q,Object.assign(()=>{},{onStatus:s=>statusA.push(s)}));h.p.watch('b',q,Object.assign(()=>{},{onStatus:s=>statusB.push(s),onError:e=>errors.push(e.message)}));await h.ready();const req=h.workers[0].sent.filter(m=>m.type==='apply');await h.ack(req[0]);h.frame(h.workers[0],{type:'request_error',id:req[1].id,traceparent:req[1].traceparent,error:'quota',currentAcquisition:undefined});await tick();assert.equal(statusA.at(-1),'ready');assert.equal(statusB.at(-1),'error');assert.equal(h.p.connectionStatus,'connected');assert.equal(errors.length,1);h.p.dispose();cases.push('per-query readiness/rejection leaves transport healthy');
}
{
 const h=setup({maxAttempts:3}),errors=[],status=[];h.p.watch('s',q,Object.assign(()=>{},{onStatus:s=>status.push(s),onError:e=>errors.push(e.message)}));h.lost();await h.advance(50);h.lost();await h.advance(100);h.lost();await tick();assert.equal(h.workers.length,3);assert.equal(h.p.connectionStatus,'disconnected');assert.equal(status.at(-1),'error');assert.equal(errors.length,1);assert.equal(h.timers.size,0);h.p.dispose();cases.push('deterministic jitter, exponential delay, finite exhaustion exactly once');
}
{
 const h=setup();h.p.watch('s',q,()=>{});h.lost();h.p.dispose();await h.advance(5000);assert.equal(h.workers.length,1);assert.equal(h.p.connectionStatus,'disconnected');assert.equal(h.timers.size,0);cases.push('dispose cancels retry, deadline and observers');
}
{
 const h=setup();const stop=h.p.subscribeConnectionStatus(()=>{h.p.dispose();throw Error('status consumer');});await h.ready();assert.equal(h.p.connectionStatus,'disconnected');assert.equal(h.workers[0].dead,true);assert.equal(h.timers.size,0);stop();cases.push('reentrant status disposal followed by exception');
}
{
 const h=setup();for(let i=0;i<70;i++)h.p.watch('s'+i,q,()=>{});assert.throws(()=>h.p.watch('overflow',q,()=>{}),/budget/);await h.ready();assert.equal(h.p.admission.inFlight,4);assert.equal(h.p.admission.queued,66);let cursor=1;while(h.p.admission.outstanding){const w=h.workers[0];while(cursor<w.sent.length){const r=w.sent[cursor++];if(r.type==='apply')await h.ack(r);}await tick();}h.lost();await h.advance(50);await h.ready();assert.equal(h.p.admission.inFlight,4);assert.equal(h.p.admission.queued,66);cursor=1;while(h.p.admission.outstanding){const w=h.workers[1];while(cursor<w.sent.length){const r=w.sent[cursor++];if(r.type==='apply')await h.ack(r);}await tick();}h.p.dispose();assert.equal(h.timers.size,0);cases.push('70+1 quota and restoration: four in flight, bounded queue, one Worker');
}
{
 const h=setup(),seen=[];let changed=false;
 h.p.watch('s',q,Object.assign(r=>seen.push(r),{onStatus:status=>{if(status==='ready'&&!changed){changed=true;void h.p.apply({command:'change_window',subscription:'s',offset:5,limit:2});}}}));await h.ready();await h.ack(h.workers[0].sent.at(-1));assert.equal(seen.length,0,'status reentrancy invalidates the old result before data callback');await h.ack(h.workers[0].sent.at(-1),h.workers[0],2);assert.equal(seen.at(-1).start_rank,5);h.p.dispose();cases.push('reentrant status navigation fences old-window publication');
}
{
 const h=setup();h.p.watch('s',q,()=>{});await assert.rejects(h.p.apply({command:'change_window',subscription:'s',offset:7,limit:2}),/retained/);await h.ready();assert.equal(h.workers[0].sent.at(-1).command.query.offset,7);await h.ack(h.workers[0].sent.at(-1));h.p.dispose();cases.push('intent change during initial handshake dispatches latest window');
}
{
 const h=setup();const seen=[];h.p.watch('s',q,r=>seen.push(r));await h.ready();await h.ack(h.workers[0].sent.at(-1));const operation=h.p.apply({command:'change_query',subscription:'s',query:{...q,where_expr:{op:'invalid'}}}).catch(e=>e);await tick();const request=h.workers[0].sent.at(-1);h.frame(h.workers[0],{type:'request_error',id:request.id,traceparent:request.traceparent,error:'invalid query',currentAcquisition:seen[0].query_generation});await operation;h.lost();await h.advance(50);await h.ready();assert.deepEqual(h.workers[1].sent.at(-1).command.query.where_expr,q.where_expr);h.p.dispose();cases.push('A -> rejected B -> surviving valid A reacquired');
}
{
 const h=setup(),states=[];h.p.watch('s',q,Object.assign(()=>{},{onStatus:s=>states.push(s)}));await h.ready();await h.ack(h.workers[0].sent.at(-1));h.lost();assert.equal(states.at(-1),'stale');await assert.rejects(h.p.apply({command:'change_window',subscription:'s',offset:0,limit:2}),/retained/);assert.equal(states.at(-1),'stale','equivalent offline read must retain coherent display');h.p.dispose();cases.push('equivalent offline read coalesces without relabelling retained data');
}
await writeFile(root+'../fresh-evidence/provider-state-machine.json',JSON.stringify({passed:true,scope:'actual provider; controlled Workers and deterministic clocks, independent assertions',cases},null,2));console.log(JSON.stringify({passed:true,cases}));
