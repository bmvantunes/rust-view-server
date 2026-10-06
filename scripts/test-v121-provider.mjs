// Actual provider in a controlled Worker environment: FIFO bounds and ownership.
import {readFile,writeFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import {webcrypto} from 'node:crypto';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {root,hash} from './v121-browser-support.mjs';
import {join} from 'node:path';
const {transformWithOxc}=await import(createRequire(join(root,'browser/package.json')).resolve('vite'));
let {code}=await transformWithOxc(await readFile(join(root,'browser/src/product-provider.tsx'),'utf8'),'provider.tsx',{jsx:{runtime:'classic'}});
code=code.replace(/import[\s\S]*?from "react";/,'const createContext=()=>({});').replaceAll('import.meta.url','"file:///provider.js"').replace(/export /g,'')+'\nglobalThis.Provider=BrowserProductProvider;';
let worker;class Worker{sent=[];constructor(){worker=this;}postMessage(m){this.sent.push(m);}terminate(){}}
const context=vm.createContext({Worker,URL,structuredClone,crypto:webcrypto,Uint8Array});vm.runInContext(code,context);
const p=new context.Provider({mode:'remote',url:'ws://127.0.0.1:8080/v12',token:'x'.repeat(32),subscriptions:70});
const tick=()=>new Promise(r=>setImmediate(r));const frame=m=>worker.onmessage({data:m});frame({type:'ready'});
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2},seen=[],errors=[];
function ack(request,version=1,sequence=0){const sub=request.command.subscription;const result={subscription:sub,query_generation:request.acquisition,sequence,start_rank:request.command.offset??0,version,total_rows:0,rows:[]};frame({type:'ack',id:request.id,traceparent:request.traceparent,results:request.command.command==='close'?{}:{[sub]:result},acquisitions:{[sub]:request.acquisition}});return result;}
const release=p.watch('s',q,Object.assign(r=>seen.push(r),{onError:e=>errors.push(e.message)}));await tick();let old=worker.sent.find(m=>m.type==='apply');ack(old);await tick();
// Old replacement error arrives after a successfully acknowledged successor.
const a=p.apply({command:'change_query',subscription:'s',query:{...q,direction:'descending'}}).catch(e=>e.message);
const b=p.apply({command:'change_query',subscription:'s',query:q});await tick();const requests=worker.sent.filter(m=>m.type==='apply').slice(-2);ack(requests[1],3);await b;
frame({type:'request_error',id:requests[0].id,traceparent:requests[0].traceparent,error:'old error',currentAcquisition:old.acquisition});await a;assert.equal(seen.at(-1).query_generation,requests[1].acquisition);assert.equal(errors.length,0);
// Equal data version with later navigation sequence is deliverable; older error cannot poison it.
const nav=p.apply({command:'change_window',subscription:'s',offset:1,limit:2});await tick();ack(worker.sent.at(-1),3,1);await nav;assert.equal(seen.at(-1).sequence,1);assert.equal(seen.at(-1).start_rank,1);
release();await tick();ack(worker.sent.at(-1));await tick();assert.equal(p.admission.subscriptions,0);
const spare=p.watch('spare',q,()=>{});await tick();ack(worker.sent.at(-1));await tick();
// Exactly the finite request capacity, then explicit rejection; bounded FIFO drains fully.
const accepted=Array.from({length:242},(_,i)=>p.apply({command:'open',subscription:'q'+i,query:q}));await tick();assert.equal(p.admission.inFlight,4);assert.equal(p.admission.queued,238);
await assert.rejects(p.apply({command:'open',subscription:'overflow',query:q}),/budget/);
spare();await tick();assert.equal(p.admission.outstanding,243);assert.equal(p.admission.subscriptions,0);
let cursor=worker.sent.length-4;
while(p.admission.outstanding){while(cursor<worker.sent.length){const r=worker.sent[cursor++];if(r.type==='apply')ack(r);}await tick();}
await Promise.all(accepted);assert.equal(p.admission.queued,0);assert.equal(p.admission.inFlight,0);
const recovery=p.apply({command:'open',subscription:'recovered',query:q});await tick();ack(worker.sent.at(-1));await recovery;
const pending=Array.from({length:8},(_,i)=>p.apply({command:'open',subscription:'dispose'+i,query:q}).then(()=>{throw Error('unexpected success');},e=>e.message));await tick();p.dispose();for(const error of await Promise.all(pending))assert.match(error,/uncertain/);await tick();assert.equal(p.admission.outstanding,0);assert.equal(p.admission.queued,0);
const value={status:'passed',scope:'actual provider code, controlled Worker messages; mounted actual remote hooks are a separate gate',source_sha256:await hash(join(root,'browser/src/product-provider.tsx')),cases:['stale error after valid successor','equal-version later navigation sequence','242 ordinary accepted / 243rd rejected / reserved release admitted / bounded drain / successful reacquisition','disposal rejects four in-flight and four queued requests once'],limits:{capacity:312,ordinary:242,cleanupReserve:70,window:4}};
await writeFile(join(root,'evidence/v12.1/provider.json'),JSON.stringify(value,null,2)+'\n');console.log(JSON.stringify(value));
