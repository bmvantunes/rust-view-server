import {setup,wait,root,hash} from './v121-browser-support.mjs';
import {writeFile,appendFile,rm,access} from 'node:fs/promises';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {check,verifyLedger,verifyVersions} from './v121-oracle.mjs';
const h=await setup('barriers'),{page}=h;const cases=[];let offset=0;const rows=new Map(),cuts={'0':[]};
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2};
async function exists(p){try{await access(p);return true;}catch{return false;}}
async function arm(name,action='pause'){for(const suffix of ['release','reached','arm'])await rm(join(h.dir,name+'.'+suffix),{force:true});await writeFile(join(h.dir,name+'.arm'),action);}
async function reached(name){await wait(()=>exists(join(h.dir,name+'.reached')),name);}
async function release(name){await writeFile(join(h.dir,name+'.release'),'go');}
async function put(label,waiting=true){const r={id:'a',category:'a',label:{state:'value',value:label},quantity:'9223372036854775807',amount:{coefficient:'-1001',scale:2}};rows.set(r.id,r);const o=offset++;cuts[String(offset)]=[...rows.values()].map(r=>structuredClone(r));await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');if(waiting)await wait(()=>h.parsed().some(v=>v.state==='source_committed'&&v.offset===o),'committed '+o);return o;}
async function startRequest(name,command){await page.evaluate(({name,command})=>{window.v121settlement={count:0};window.v12.apply(name,command).then(result=>{window.v121settlement={count:window.v121settlement.count+1,result};},error=>{window.v121settlement={count:window.v121settlement.count+1,error:error.message};});},{name,command});}
try{
 let native=await h.server(true);await put('before');await h.connect('old');await page.evaluate(q=>window.v12.watch('old','same',q),q);await page.waitForFunction(()=>window.v12.results['old:same']?.length===1);
 const oldInc=h.parsed().find(v=>v.state==='ready').incarnation;
 await arm('committed_before_publication','crash');const o=await put('durable-unpublished',false);await reached('committed_before_publication');await wait(()=>native.exitCode!==null,'crash exit');assert.equal(native.exitCode,86);
 await page.waitForFunction(()=>window.v12.errors['old:same'].length===1);assert.equal(await page.evaluate(()=>window.v12.results['old:same'].length),1);assert(!h.parsed().some(v=>v.state==='source_committed'&&v.offset===o));
 native=await h.server(true);const newInc=h.parsed().filter(v=>v.state==='ready').at(-1).incarnation;assert.notEqual(oldInc,newInc);await h.connect('fresh');
 const recovered=await page.evaluate(q=>window.v12.snapshot('fresh','same',q),q);check(recovered,[...rows.values()],q);assert.equal(recovered.remote.incarnation,newInc);assert(h.parsed().some(v=>v.state==='profile_command'&&v.subscriptions===1));cases.push('durable commit before publication crash; exact reconstructed prefix under new incarnation; no old subscription continuation');
 // Source changes while the initial acquisition is held before queueing.
 await arm('acquisition_before_output');await page.evaluate(()=>window.v12.mountBurst('fresh',1));await reached('acquisition_before_output');await put('during-initial',false);await release('acquisition_before_output');await page.waitForFunction(()=>window.v12.mounted['0']?.status==='ready');await wait(()=>h.parsed().some(v=>v.state==='source_committed'&&v.offset===offset-1),'initial source processed');await page.waitForFunction(cut=>window.v12.mounted['0']?.data?.remote.sourceSequence===cut,String(offset));await page.evaluate(()=>window.v12.unmount());cases.push('source change during mounted StrictMode initial acquisition held before output');
 await page.evaluate(q=>window.v12.watch('fresh','rollback',q),q);await page.waitForFunction(()=>window.v12.results['fresh:rollback']?.length===1);
 await arm('committed_before_publication');await put('committed-predecessor',false);await reached('committed_before_publication');
 await startRequest('fresh',{command:'change_query',subscription:'rollback',query:{...q,where_expr:{op:'invalid'}}});await release('committed_before_publication');await page.waitForFunction(()=>window.v121settlement.count===1&&!!window.v121settlement.error);await page.waitForFunction(()=>window.v12.results['fresh:rollback'].at(-1)?.rows[0].label.value==='committed-predecessor');cases.push('pending invalid replacement restores already committed predecessor publication');
 await arm('output_pending');await startRequest('fresh',{command:'change_window',subscription:'rollback',offset:0,limit:1});await reached('output_pending');
 await page.evaluate(q=>{window.v12.apply('fresh',{command:'change_query',subscription:'rollback',query:{...q,direction:'descending'}}).catch(()=>{});window.v12.apply('fresh',{command:'change_query',subscription:'rollback',query:q}).catch(()=>{});},q);await release('output_pending');await page.waitForFunction(()=>window.v12.admission('fresh').outstanding===0);cases.push('delayed FIFO predecessor frames with rapid successor changes');
 await page.evaluate(()=>{window.v12.close('old');window.v12.close('fresh');});await h.shutdown();
 // Each shutdown point is independently deterministic and preserves exact settlement.
 for(const point of ['source_admitted','acquisition_before_output','result_before_ack','output_pending']){
  await rm(join(h.dir,'shutdown'),{force:true});native=await h.server(true);await h.connect('shutdown');
  await page.evaluate(q=>window.v12.watch('shutdown','same',q),q);await page.waitForFunction(()=>window.v12.results['shutdown:same'].length===1);await arm(point);
  if(point==='source_admitted')await put('shutdown-source',false);
  else await startRequest('shutdown',point==='output_pending'?{command:'close',subscription:'same'}:point==='acquisition_before_output'?{command:'open',subscription:'pending',query:q}:{command:'change_window',subscription:'same',offset:0,limit:1});
  await reached(point);
  // Source, an acquisition, ACK and output can all be pending at this stop.
  if(point==='source_admitted')await startRequest('shutdown',{command:'open',subscription:'pending',query:q});
  await writeFile(join(h.dir,'shutdown'),'stop at barrier');await writeFile(h.stop,'stop');await wait(()=>native.exitCode!==null,'bounded shutdown');assert.equal(native.exitCode,0);
  await page.waitForFunction(()=>window.v121settlement.count===1&&!!window.v121settlement.error);const settlement=await page.evaluate(()=>window.v121settlement);assert.match(settlement.error,/uncertain/);
  const stopped=h.parsed().filter(v=>v.state==='stopped').at(-1);assert.equal(stopped.subscriptions,0);assert.equal(stopped.shapes,0);cases.push('shutdown '+point+'; exactly one explicit uncertain rejection; zero subscriptions/shapes');await page.evaluate(()=>window.v12.close('shutdown'));
 }
 // Simultaneous pending states: queued result+ACK from a prior command,
 // a locally admitted source record, and a second accepted acquisition request.
 await rm(join(h.dir,'shutdown'),{force:true});native=await h.server(true);await h.connect('combined');
 await page.evaluate(q=>window.v12.watch('combined','same',q),q);await page.waitForFunction(()=>window.v12.results['combined:same'].length===1);
 await arm('result_before_ack');await arm('source_admitted');
 await page.evaluate(()=>{window.v121group=[];const settle=(i,command)=>{window.v121group[i]={count:0};window.v12.apply('combined',command).then(()=>window.v121group[i]={count:window.v121group[i].count+1,ok:true},e=>window.v121group[i]={count:window.v121group[i].count+1,error:e.message});};window.v121start=settle;settle(0,{command:'change_window',subscription:'same',offset:0,limit:1});});
 await reached('result_before_ack');await put('combined-pending-source',false);
 await page.evaluate(q=>window.v121start(1,{command:'open',subscription:'pending',query:q}),q);
 await release('result_before_ack');await reached('source_admitted');
 await writeFile(join(h.dir,'shutdown'),'stop');await writeFile(h.stop,'stop');await wait(()=>native.exitCode!==null,'combined shutdown');assert.equal(native.exitCode,0);
 await page.waitForFunction(()=>window.v121group.every(x=>x.count===1&&x.error?.includes('uncertain')));assert.equal(await page.evaluate(()=>window.v121group.length),2);
 assert(h.parsed().filter(v=>v.state==='stopped').at(-1).subscriptions===0);await page.evaluate(()=>window.v12.close('combined'));
 cases.push('simultaneous source record, acquisition request, queued result and ACK at shutdown; two exactly-once uncertain rejections');
 const ledger=await page.evaluate(()=>window.v121ledger);const oracle=verifyLedger(ledger,cuts);const versions=verifyVersions(ledger,h.parsed(),cuts);
 await h.evidence({status:'passed',fault_binary_sha256:await hash(join(root,'bin/view_server_faults')),scope:'actual separate fault-feature service + real loopback + Worker; deterministic file barriers outside SQLite; release binary separately tested',cases,ledger,cuts,server_events:h.parsed(),oracle,versions});console.log(JSON.stringify({status:'passed',cases,oracle}));
}catch(e){console.error(h.logs.join('').slice(-7000));throw e;}finally{await h.cleanup();}
