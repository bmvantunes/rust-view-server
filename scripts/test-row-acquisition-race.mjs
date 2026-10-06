import {setup,wait} from './v131-browser-support.mjs';import {appendFile} from 'node:fs/promises';import assert from 'node:assert/strict';
const h=await setup('acquisition-race'),q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2,projection:['quantity','label']};const cuts={'0':[]};let checked=0;
try{await h.server();await h.connect('race',70);
 for(let i=0;i<20;i++){
  const sub='s'+i,label='acquisition-'+i,row={id:'🦀',category:'a',quantity:'18446744073709551617',amount:{coefficient:'-123000000000000000009',scale:18},label:{state:'value',value:label}};cuts[String(i+1)]=[row];
  await h.page.evaluate(({q,sub})=>{window.raceRelease=window.v12.watch('race',sub,q);},{q,sub});
  // Arrival races registration/first extraction; do not await initial delivery.
  await appendFile(h.feed,JSON.stringify({partition:0,offset:i,mutation:{kind:'upsert',row}})+'\n');
  await h.page.waitForFunction(({sub,label})=>window.v12.results['race:'+sub]?.at(-1)?.rows[0]?.label.value===label,{sub,label});
  const results=await h.page.evaluate(sub=>window.v12.results['race:'+sub],sub);
  for(const result of results){const expected=cuts[result.remote.sourceSequence];assert(expected);assert.deepEqual(result.keys,expected.map(r=>r.id));assert.deepEqual(result.rows,expected.map(r=>({quantity:r.quantity,label:r.label})));assert.equal(result.total_rows,expected.length);assert.equal(result.start_rank,0);assert.equal(result.effectiveEnd,expected.length);checked++;}
  await h.page.evaluate(()=>window.raceRelease());await h.page.waitForFunction(()=>window.v12.admission('race').outstanding===0);
 }
 await h.page.evaluate(()=>window.v12.close('race'));await h.shutdown();assert(h.parsed().some(v=>v.state==='stopped'&&v.subscriptions===0&&v.shapes===0));await h.evidence({passed:true,races:20,checked,query:q,scope:'actual native fixture socket/Worker acquisition arrival race; not real Kafka'});console.log(JSON.stringify({passed:true,races:20,checked}));
}finally{await h.cleanup();}
