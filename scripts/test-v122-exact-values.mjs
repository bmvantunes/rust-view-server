// Actual ordinary release -> socket -> Worker -> provider -> mounted React.
import {setup,wait,root,hash} from './v122-browser-support.mjs';
import {check,verifyLedger,verifyVersions} from './v122-oracle.mjs';
import {appendFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const h=await setup('exact-values'),{page}=h;
const rows=new Map(),cuts={'0':[]};let offset=0;
const row=(id,coefficient,scale=0)=>({id,category:'a',quantity:'9007199254740993',amount:{coefficient,scale},label:{state:'value',value:id}});
const initial=[row('a','1'),row('b','10',1),row('\ue000','1'),row('\u{10000}','1'),row('floor','10',-10000),row('negative-floor','-10',-10000),row('negative-prefix','-1001',3),row('zero','-000',10000),row('tiny','1',10000)];
const asc=['negative-floor','negative-prefix','zero','tiny','a','b','\ue000','\u{10000}','floor'];
const desc=['floor','a','b','\ue000','\u{10000}','tiny','zero','negative-prefix','negative-floor'];
async function put(r){rows.set(r.id,r);cuts[String(offset+1)]=[...rows.values()].map(r=>structuredClone(r));const o=offset++;await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');await wait(()=>h.parsed().some(v=>v.state==='source_committed'&&v.offset===o),'source '+o);}
try{
 await h.server();for(const r of initial)await put(r);await h.connect('exact');
 const queries=['ascending','descending'].map(direction=>({where_expr:{op:'true'},direction,offset:0,limit:20}));
 await page.evaluate(queries=>{queries.forEach((q,i)=>window.v12.watch('exact','q'+i,q));window.v12.mount('exact');},queries);
 await page.waitForFunction(()=>window.v12.results['exact:q0']?.length===1&&window.v12.results['exact:q1']?.length===1);
 await page.waitForFunction(expected=>document.querySelector('output')?.textContent===expected,'9|'+asc.join(','));
 for(let i=0;i<2;i++){const result=await page.evaluate(i=>window.v12.results['exact:q'+i].at(-1),i);assert.deepEqual(result.rows.map(r=>r.id),i===0?asc:desc);check(result,[...rows.values()],queries[i]);}
 // Equivalent coefficient/scale and quantity spelling is a committed source cut
 // with no result-version change or unsolicited content publication.
 await page.waitForFunction(()=>window.v12.admission('exact').outstanding===0);
 const beforeNoop=await page.evaluate(async()=>{const current=(await window.v12.apply('exact',{command:'change_window',subscription:'q1',offset:0,limit:20})).q1;return {version:current.version,count:window.v12.results['exact:q0'].length};});
 await put({...initial[1],quantity:'+09007199254740993',amount:{coefficient:'100',scale:2}});
 const noop=await page.evaluate(async()=>(await window.v12.apply('exact',{command:'change_window',subscription:'q1',offset:0,limit:20})).q1);
 assert.equal(noop.version,beforeNoop.version);assert.equal(noop.remote.sourceSequence,String(offset));
 assert.equal(await page.evaluate(()=>window.v12.results['exact:q0'].length),beforeNoop.count);
 const changed={...initial[1],label:{state:'value',value:'payload only'}};await put(changed);
 await page.waitForFunction(cut=>['q0','q1'].every(s=>window.v12.results['exact:'+s].at(-1).remote.sourceSequence===cut),String(offset));
 for(const [start,limit] of [[1,4],[100000,2],[0,0],[0,20]]){
  const result=await page.evaluate(async({start,limit})=>(await window.v12.apply('exact',{command:'change_window',subscription:'q1',offset:start,limit})).q1,{start,limit});
  assert.deepEqual(result.rows.map(r=>r.id),desc.slice(start,start+limit));assert.equal(result.total_rows,9);assert.equal(result.start_rank,start);
 }
 // New payload publication after navigation must retain its acquisition/window.
 await put({...initial[0],label:{state:'value',value:''}});
 await page.waitForFunction(cut=>['q0','q1'].every(s=>window.v12.results['exact:'+s].at(-1).remote.sourceSequence===cut),String(offset));
 await page.evaluate(()=>window.v12.unmount());
 await page.waitForFunction(()=>window.v12.admission('exact').outstanding===0);
 const ledger=await page.evaluate(()=>window.v122ledger);const events=h.parsed();
 const oracle=verifyLedger(ledger,cuts),versions=verifyVersions(ledger,events,cuts);assert(oracle.live>=4);
 const negatives=[];
 for(const kind of ['descending-ties','unicode-id-ties','scale-floor']){
  const bad=structuredClone(ledger);const message=bad.find(e=>e.type==='receive'&&e.message.type==='live'&&e.message.results?.q1)?.message;assert(message);
  const rows=message.results.q1.rows;
  if(kind==='scale-floor')rows.find(r=>r.id==='floor').amount={coefficient:'1',scale:-10001};
  else {const ids=kind==='descending-ties'?['a','b']:['\ue000','\u{10000}'];const a=rows.findIndex(r=>r.id===ids[0]),b=rows.findIndex(r=>r.id===ids[1]);[rows[a],rows[b]]=[rows[b],rows[a]];}
  assert.throws(()=>verifyLedger(bad,cuts));negatives.push(kind);
 }
 await page.evaluate(()=>window.v12.close('exact'));await h.shutdown();
 assert(h.parsed().some(v=>v.state==='stopped'&&v.subscriptions===0&&v.shapes===0));
 await h.evidence({status:'passed',scope:'ordinary release, native socket, actual Worker/provider, mounted React; all received results checked',oracle,versions,ledger,cuts,server_events:events,poisoning_rejected:negatives,equivalent_source_noop:{version:noop.version,sourceSequence:noop.remote.sourceSequence,no_live_publication:true},source_hashes:Object.fromEntries(await Promise.all(['scripts/v122-oracle.mjs','scripts/test-v122-exact-values.mjs','browser/src/product.remote.worker.ts'].map(async p=>[p,await hash(root+'/'+p)])))});
 console.log(JSON.stringify({status:'passed',oracle,versions,poisoning_rejected:negatives}));
}catch(e){console.error(h.logs.join('').slice(-5000));throw e;}finally{await h.cleanup();}
