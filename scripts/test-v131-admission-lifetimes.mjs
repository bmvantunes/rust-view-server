// Real native service / socket / Worker / provider. Fixed literal outcomes, no restricted oracle.
import {setup,wait,codec} from './v131-browser-support.mjs';
import {appendFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const h=await setup('admission-lifetimes-'+codec),cases=[];
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:4};
const invalids=[
 {where_expr:{op:'condition',args:{field:'amount',condition:{op:'equal',value:{coefficient:'1',scale:10001}}}}},
 {where_expr:{op:'condition',args:{field:'quantity',condition:{op:'equal',value:'bad'}}}},
 {where_expr:{op:'unsupported'}}, {offset:-1},{offset:Number.MAX_SAFE_INTEGER+1},
];
let offset=0;
const put=async label=>{await appendFile(h.feed,JSON.stringify({partition:0,offset:offset++,mutation:{kind:'upsert',row:{id:'a',category:'a',quantity:'11',amount:{coefficient:'110',scale:0},label:{state:'value',value:label}}}})+'\n');};
try{
 await h.server();await put('seed');await wait(()=>h.parsed().some(x=>x.state==='source_committed'),'seed');
 for(let i=0;i<invalids.length;i++){
  const name='recovery-'+i;await h.connect(name);
  await h.page.evaluate(({name,q})=>{window.v12.watch(name,'s',q);window.v12.mount(name);},{name,q});
  await h.page.waitForFunction(name=>window.v12.results[name+':s']?.length>0,name);
  await h.page.waitForFunction(()=>document.querySelector('output')?.textContent==='1|a');
  const before=await h.page.evaluate(async name=>(await window.v12.apply(name,{command:'change_window',subscription:'s',offset:0,limit:4})).s,name);
  const reject=await h.page.evaluate(async({name,q})=>{try{await window.v12.apply(name,{command:'change_query',subscription:'s',query:q});return false;}catch(e){return String(e);}},{name,q:{...q,...invalids[i]}});assert(reject);
  const nav=await h.page.evaluate(name=>window.v12.apply(name,{command:'change_window',subscription:'s',offset:0,limit:4}),name);
  assert.equal(nav.s.version,before.version);assert.equal(nav.s.query_generation,before.query_generation);assert.deepEqual(nav.s.rows.map(x=>x.id),['a']);
  const label='after-reject-'+i;await put(label);
  await h.page.waitForFunction(({name,label})=>window.v12.results[name+':s'].at(-1)?.rows[0]?.label.value===label,{name,label});
  const c=await h.page.evaluate(async({name,q})=>(await window.v12.apply(name,{command:'change_query',subscription:'s',query:q})).s,{name,q:{...q,direction:'descending'}});assert.deepEqual(c.rows.map(x=>x.id),['a']);
  const live=await h.page.evaluate(name=>window.v12.results[name+':s'].at(-1),name);assert.equal(live.remote.acquisition,c.remote.acquisition);
  cases.push({name,status:'passed',reject,before,navigation:nav.s,successor:c,live});
  await h.page.evaluate(name=>{window.v12.unmount();window.v12.close(name);},name);
 }
 for(const mode of ['replacement','navigation','close']){
  const name='concurrent-'+mode;await h.connect(name);
  const result=await h.page.evaluate(async({name,q,bad,mode})=>{
   const start=window.v13ledger.length;
   const submit=command=>window.v12.apply(name,command).then(value=>({ok:true,value}),e=>({ok:false,error:String(e)}));
   // Four commands submitted before awaiting any response, matching the provider window.
   const pending=[submit({command:'open',subscription:'s',query:q}),submit({command:'change_query',subscription:'s',query:bad}),submit(mode==='replacement'?{command:'change_query',subscription:'s',query:{...q,direction:'descending'}}:mode==='navigation'?{command:'change_window',subscription:'s',offset:0,limit:4}:{command:'close',subscription:'s'}),submit({command:'open',subscription:'other',query:q})];
   const settled=await Promise.all(pending);const ledger=window.v13ledger.slice(start);
   const after=await submit({command:'change_window',subscription:'s',offset:0,limit:4});
   return{settled,ledger,after};
  },{name,q,bad:{...q,...invalids[0]},mode});
  assert.deepEqual(result.settled.map(x=>x.ok),[true,false,mode==='replacement',true]);
  assert(result.after.ok);assert.deepEqual(result.after.value.s.rows.map(x=>x.id),['a']);
  const sends=result.ledger.filter(x=>x.type==='send');const receives=result.ledger.filter(x=>x.type==='receive');
  assert.equal(sends.length,4);assert.equal(receives.length,4);assert.deepEqual(receives.map(x=>x.message.id),sends.map(x=>x.message.id));
  assert.equal(receives[1].message.currentAcquisition,sends[0].message.acquisition);
  assert.equal(result.after.value.s.remote.acquisition,sends[mode==='replacement'?2:0].message.acquisition);
  // Navigation/close submitted before rejection captures the rejected acquisition and
  // is itself rejected, exactly as JSON. A subsequent command uses the restored owner.
  cases.push({name,status:'passed',...result});await h.page.evaluate(name=>window.v12.close(name),name);
 }
 await h.connect('dispose');const disposal=await h.page.evaluate(async({q,bad})=>{await window.v12.snapshot('dispose','s',q);let settlements=0;const p=window.v12.apply('dispose',{command:'change_query',subscription:'s',query:bad}).then(()=>({ok:true}),e=>({error:String(e)})).finally(()=>settlements++);window.v12.close('dispose');return{result:await p,settlements};},{q,bad:{...q,...invalids[0]}});assert.equal(disposal.settlements,1);assert(disposal.result.error);cases.push({name:'dispose-during-rejection',...disposal});
 await h.shutdown();assert(h.parsed().some(e=>e.state==='stopped'&&e.subscriptions===0&&e.shapes===0));
 await h.evidence({status:'passed',codec,cases,finalZeroSubscriptions:true,scope:'real native socket/Worker/provider and mounted hook, source mutation after recoverable error; four concurrently submitted commands; same-version navigation'});console.log(codec,'admission lifetimes passed');
}finally{await h.cleanup();}
