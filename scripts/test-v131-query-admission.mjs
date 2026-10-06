// Independent query-admission expectations; deliberately outside the narrow publication oracle.
import {setup,wait,codec} from './v131-browser-support.mjs';
import {appendFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const h=await setup('query-admission-'+codec),cases=[];
const base={where_expr:{op:'true'},direction:'ascending',offset:0,limit:4};
let deep={op:'true'};for(let i=0;i<40;i++)deep={op:'not',args:deep};
let boundary={op:'true'};for(let i=0;i<122;i++)boundary={op:'not',args:boundary};
const predicates=[
 ['admitted-depth-122',boundary,true],
 ['quantity-source-spelling',{op:'condition',args:{field:'quantity',condition:{op:'equal',value:'1__1_'}}},true],
 ['decimal-constructor-normalization',{op:'condition',args:{field:'amount',condition:{op:'equal',value:{coefficient:'110',scale:0}}}},true],
 ['admitted-depth-40',deep,true],
 ['invalid-decimal-keeps-previous-acquisition',{op:'condition',args:{field:'amount',condition:{op:'equal',value:{coefficient:'1',scale:10001}}}},false],
];
const watchdog=setTimeout(async()=>{console.error('watchdog',JSON.stringify(h.parsed()).slice(-6000));try{console.error('ledger',JSON.stringify(await h.page.evaluate(()=>window.v13ledger)).slice(-6000));}finally{await h.cleanup();process.exit(2);}},45000);
try{
 await h.server();await appendFile(h.feed,JSON.stringify({partition:0,offset:0,mutation:{kind:'upsert',row:{id:'a',category:'a',quantity:'11',amount:{coefficient:'110',scale:0},label:{state:'missing'}}}})+'\n');
 await wait(()=>h.parsed().some(e=>e.state==='source_committed'),'source seed');
 for(const [name,where_expr,valid]of predicates){
  console.log('case',name);await h.connect(name);console.log('connected',name);await h.page.evaluate(async({name,base})=>{await window.v12.snapshot(name,'s',base);window.v12.mount(name);},{name,base});
  await h.page.waitForFunction(()=>document.querySelector('output')?.textContent==='1|a');
  console.log('mounted',name);
  const result=await h.page.evaluate(async({name,queryText})=>{const query=JSON.parse(queryText);let changed,error,after,afterError;
   try{changed=(await window.v12.apply(name,{command:'change_query',subscription:'s',query})).s;}catch(e){error=String(e);}
   try{after=(await window.v12.apply(name,{command:'change_window',subscription:'s',offset:0,limit:4})).s;}catch(e){afterError=String(e);}
   return{changed,error,after,afterError,admission:window.v12.admission(name)};
  },{name,queryText:JSON.stringify({...base,where_expr,limit:name==='admitted-depth-122'?1000000000000000100:base.limit})});
  console.log('result',name,result.error,result.afterError);
  const correct=(valid?result.changed?.rows?.map(r=>r.id).join(',')==='a':!!result.error)&&!result.afterError&&result.after?.rows?.map(r=>r.id).join(',')==='a';
  cases.push({name,valid,expected:'valid predicate returns a; invalid predicate rejects only the command; previous acquisition remains navigable',correct,...result});
  await h.page.evaluate(name=>{window.v12.unmount();window.v12.close(name);},name);
 }
 const terminal=[];
 for(const bound of ['source-depth-123','source-bytes-over-65536']){
  await h.connect(bound);await h.page.evaluate(async({name,base})=>window.v12.snapshot(name,'s',base),{name:bound,base});
  const r=await h.page.evaluate(async({name,base})=>{
   let where_expr={op:'true'};if(name==='source-depth-123')for(let i=0;i<123;i++)where_expr={op:'not',args:where_expr};
   const command={command:'change_query',subscription:'s',query:{...base,where_expr},...(name==='source-bytes-over-65536'?{ignored:'x'.repeat(65536)}:{})};
   let error,afterError;try{await window.v12.apply(name,command);}catch(e){error=String(e);}try{await window.v12.apply(name,{command:'change_window',subscription:'s',offset:0,limit:4});}catch(e){afterError=String(e);}
   return{error,afterError,fatal:window.v13ledger.filter(x=>x.type==='receive'&&x.message.type==='fatal').at(-1)?.message};
  },{name:bound,base});assert(r.error&&r.afterError&&r.fatal);terminal.push({name:bound,...r});await h.page.evaluate(name=>window.v12.close(name),bound);
 }
 await h.shutdown();assert(h.parsed().some(e=>e.state==='stopped'&&e.subscriptions===0&&e.shapes===0));
 const passed=cases.every(c=>c.correct);await h.evidence({status:passed?'passed':'failed',codec,scope:'real native service, WebSocket, actual Worker/provider and mounted hook; fixed expectations, not the limited publication oracle',cases,terminal,server_events:h.parsed(),finalZeroSubscriptions:true});
 console.log(JSON.stringify({codec,passed,cases:cases.map(({name,correct,error,afterError})=>({name,correct,error,afterError}))}));
 if(!passed)process.exitCode=1;
}finally{clearTimeout(watchdog);await h.cleanup();}
