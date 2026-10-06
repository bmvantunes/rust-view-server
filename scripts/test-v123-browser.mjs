import {setup,wait,root,hash} from './v123-browser-support.mjs';
import {verifyLedger,verifyVersions,check} from './v123-oracle.mjs';
import {appendFile,readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
import {join} from 'node:path';
const h=await setup('browser-profile');const {page}=h;
const canonical=new Map(),cuts={'0':[]},samples=[],cases=[];let offset=0;
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2};
function row(i,n=0){return{id:'r'+String(i).padStart(3,'0'),category:['a','b','c'][i%3],label:{state:'value',value:'label '+n+' 日本語'},quantity:'9223372036854775807',amount:{coefficient:String(-10001+i*13+n*7),scale:2}};}
async function put(r,waiting=true){canonical.set(r.id,r);const o=offset++;cuts[String(offset)]=[...canonical.values()].map(r=>structuredClone(r));await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');if(waiting)await wait(()=>h.parsed().some(v=>v.state==='source_committed'&&v.offset===o),'source '+o);return o;}
async function settled(name){await page.waitForFunction(name=>window.v12.admission(name).outstanding===0,name);}
try{
 await h.server();h.profile();for(let i=0;i<96;i++)await put(row(i));
 await h.connect('one');await page.evaluate(q=>window.v12.watch('one','same',q),q);await page.waitForFunction(()=>window.v12.results['one:same']?.length===1);
 // Dense arrivals: 12 records available together, fixture still processes one per turn.
 const begin=process.hrtime.bigint();for(let i=0;i<12;i++)await put(row(i,1),false);await wait(()=>h.parsed().some(v=>v.state==='source_committed'&&v.offset===offset-1),'dense completion');
 await page.waitForFunction(cut=>window.v12.results['one:same'].at(-1)?.remote.sourceSequence===cut,String(offset));samples.push({phase:'one_client_dense_12',node_boundary_ns:Number(process.hrtime.bigint()-begin)});
 await h.connect('peer');await page.evaluate(q=>window.v12.watch('peer','same',q),q);await page.waitForFunction(()=>window.v12.results['peer:same']?.length===1);
 for(let i=0;i<6;i++){const start=process.hrtime.bigint();await put(row(0,10+i));await page.waitForFunction(cut=>window.v12.results['peer:same'].at(-1)?.remote.sourceSequence===cut,String(offset));samples.push({phase:'two_client_sparse',node_boundary_ns:Number(process.hrtime.bigint()-start)});}
 // A -> B -> A and queued same-version windows, including invalid predecessor rollback.
 await page.evaluate(async q=>{const p=window.v12;await Promise.all([p.apply('one',{command:'change_query',subscription:'same',query:{...q,direction:'descending'}}),p.apply('one',{command:'change_query',subscription:'same',query:q})]);await Promise.all([p.apply('one',{command:'change_window',subscription:'same',offset:1,limit:2}),p.apply('one',{command:'change_window',subscription:'same',offset:0,limit:2})]);try{await p.apply('one',{command:'change_query',subscription:'same',query:{...q,where_expr:{op:'invalid'}}});}catch{}},q);
 const unchanged=await page.evaluate(async()=>{const command={command:'change_window',subscription:'same',offset:0,limit:2};const a=(await window.v12.apply('one',command)).same;const b=(await window.v12.apply('one',command)).same;return[a,b];});assert.equal(unchanged[0].version,unchanged[1].version);assert.equal(unchanged[0].sequence,unchanged[1].sequence);
 await put(row(0,20));await page.waitForFunction(cut=>window.v12.results['one:same'].at(-1)?.remote.sourceSequence===cut,String(offset));cases.push('rapid A-B-A, same-version FIFO navigation, invalid replacement then live predecessor');
 // Cold: instantiate and mount within the same browser turn before readiness.
 await page.evaluate(({url,token})=>{window.v12.close('one');window.v12.begin('burst',url,token,70);window.v12.mountBurst('burst',71);},{url:h.url,token:h.token});
 await page.waitForFunction(()=>document.querySelectorAll('[data-burst]').length===71&&[...document.querySelectorAll('[data-burst]')].filter(x=>x.textContent==='ready').length===70&&document.querySelector('[data-burst="70"]')?.textContent==='ERROR:subscription budget exceeded');await settled('burst');
 assert.equal((await page.evaluate(()=>window.v12.admission('burst'))).subscriptions,70);cases.push('mounted cold 70+1 shared hooks, StrictMode, coherent quota error, healthy peer');
 await page.evaluate(()=>window.v12.mountBurst('burst',35));await settled('burst');await wait(()=>h.parsed().some(v=>v.state==='profile_command'&&v.subscriptions===36),'35+peer server cleanup');
 await page.evaluate(()=>window.v12.mountBurst('burst',70));await page.waitForFunction(()=>[...document.querySelectorAll('[data-burst]')].filter(x=>x.textContent==='ready').length===70);await settled('burst');
 for(let i=0;i<3;i++){const start=process.hrtime.bigint();await put(row(0,30+i));await page.waitForFunction(cut=>Array.from({length:70},(_,i)=>window.v12.mounted[String(i)]?.data?.remote.sourceSequence===cut).every(Boolean),String(offset));samples.push({phase:'70_shared_plus_peer_sparse',node_boundary_ns:Number(process.hrtime.bigint()-start)});}
 await page.evaluate(()=>window.v12.mountBurst('burst',70,true));await page.waitForFunction(()=>Array.from({length:70},(_,i)=>window.v12.mounted[String(i)]?.data?.total_rows===32).every(Boolean));await settled('burst');
 assert(h.parsed().some(v=>v.state==='profile_command'&&v.subscriptions===71&&v.shapes===4));
 for(let i=0;i<3;i++){await put(row(i,40));await page.waitForFunction(({cut,category})=>Array.from({length:70},(_,i)=>i%3!==category||window.v12.mounted[String(i)]?.data?.remote.sourceSequence===cut).every(Boolean),{cut:String(offset),category:i});}
 const dims=await page.evaluate(()=>window.v12.admission('burst'));assert.equal(dims.commandWindow,4);assert.equal(dims.commandLimit,312);assert.equal(dims.queued,0);assert.equal(dims.inFlight,0);
 await page.evaluate(()=>window.v12.mountBurst('burst',35,true));await settled('burst');await page.evaluate(()=>window.v12.unmount());await settled('burst');assert.equal((await page.evaluate(()=>window.v12.admission('burst'))).subscriptions,0);
 assert(h.parsed().some(v=>v.state==='profile_command'&&v.subscriptions===1&&v.shapes===1));
 await put(row(0,50));await page.waitForFunction(cut=>window.v12.results['peer:same'].at(-1)?.remote.sourceSequence===cut,String(offset));cases.push('70 distinct shapes across 3 predicates, staggered unmount, final peer live');
 // Real remote hooks: callbacks invalidate ownership before later sink/status effects.
 for(const action of ['release','replace','dispose','invalidate-throw']){
  await h.connect('callback');await page.evaluate(action=>window.v12.mountCallback('callback',action),action);
  await page.waitForFunction(()=>window.v12.callbackLog.includes('old-count'));
  if(action==='replace')await page.waitForFunction(()=>window.v12.callbackLog.includes('new-data'));
  else if(action==='dispose')await page.waitForFunction(()=>document.querySelector('[data-callback]')?.textContent?.startsWith('ERROR:'));
  else await settled('callback');
  const state=await page.evaluate(()=>({log:window.v12.callbackLog,status:document.querySelector('[data-callback]')?.textContent}));
  assert(!state.log.includes('old-data'));if(['release','invalidate-throw'].includes(action))assert.equal(state.status,'loading');
  await put(row(0,60+['release','replace','dispose','invalidate-throw'].indexOf(action)));await page.waitForFunction(cut=>window.v12.results['peer:same'].at(-1)?.remote.sourceSequence===cut,String(offset));
  await page.evaluate(()=>{window.v12.unmount();window.v12.close('callback');});cases.push('actual remote viewport callback '+action);
 }
 const ledger=await page.evaluate(()=>window.v123ledger);const oracle=verifyLedger(ledger,cuts);const versions=verifyVersions(ledger,h.parsed(),cuts);assert(oracle.live>=200);assert(oracle.connections>=3);
 await page.evaluate(()=>{window.v12.close('burst');window.v12.close('peer');});await h.shutdown();assert(h.parsed().some(v=>v.state==='stopped'&&v.subscriptions===0&&v.shapes===0));
 const profile=h.parsed().filter(v=>v.state.startsWith('profile_'));assert(profile.some(v=>v.state==='profile_peer'&&v.encoded_bytes>0));assert(h.resources.some(v=>v.rssKiB>0));
 await h.evidence({status:'passed',cases,oracle,versions,dimensions:{dataset:96,clients_max:2,subscriptions:70,peer_subscriptions:1,viewport_rows:2,distinct_predicates:3,command_window:4,command_capacity:312,server_client_limit:70,server_total_limit:80,output_frames:86,output_bytes:8388608},ledger,cuts,samples,profile,server_events:h.parsed(),source_hashes:Object.fromEntries(await Promise.all(['browser/src/product-provider.tsx','browser/src/product.remote.worker.ts','ingestion/src/bin/view_server.rs','scripts/v123-oracle.mjs'].map(async p=>[p,await hash(join(root,p))]))),boundaries:'Node hrtime includes automation, append and waiting. Worker receipt ns uses Worker performance clock only. Server integer durations use Instant. No cross-clock subtraction; not React commit/paint; ps CPU/RSS samples, not allocator or physical IO. SQLite FULL; fixture one-record-per-turn; dense arrival is not Kafka batching.'});console.log(JSON.stringify({status:'passed',oracle,dimensions:dims,cases}));
}catch(e){console.error(h.logs.join('').slice(-5000));throw e;}finally{await h.cleanup();}
