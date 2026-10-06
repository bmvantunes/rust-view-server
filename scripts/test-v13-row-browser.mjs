// Ordinary Rust -> real socket -> actual Worker/provider -> mounted hook.
import assert from 'node:assert/strict';
import {appendFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {setup,wait,root,projectRoot,hash} from './v13-browser-support.mjs';
import {check,verifyLedger,verifyVersions} from './v13-oracle.mjs';
const archive=projectRoot+'/rust-differential-product-20260929-review-checkpoint-v12.3.zip';
assert.equal(await hash(archive),'b35504ee3d90c576db1ee62a5a608f56702426918ac28c7bce6374c87be720a8');
const old=await import('data:text/javascript;base64,'+execFileSync('python3',['-c','import sys,zipfile;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("scripts/v123-oracle.mjs"))',archive]).toString('base64'));
const h=await setup('row-browser'),{page}=h;
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2};
let offset=0;const cuts={'0':[]};
const row={id:'exact',category:'a',quantity:'9_007_199_254_740_993',amount:{coefficient:'-1__1_',scale:0}};
const expected={...row,quantity:'9007199254740993',amount:{coefficient:'-11',scale:0},label:{state:'missing'}};
async function put(r){const o=offset++;cuts[String(offset)]=[structuredClone(r)];await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');await wait(()=>h.parsed().some(e=>e.state==='source_committed'&&e.offset===o),'commit '+o);}
const snapshot=()=>page.evaluate(async()=>(await window.v12.apply('row',{command:'change_window',subscription:'q',offset:0,limit:2})).q);
const hookRows=[];
try{
 await h.server();await put(row);await h.connect('row');
 await page.evaluate(q=>{window.v12.watch('row','q',q);window.v12.mountBurst('row',1);},q);
 await page.waitForFunction(()=>window.v12.mounted['0']?.status==='ready'&&window.v12.results['row:q']?.length===1);
 const first=await page.evaluate(()=>window.v12.results['row:q'][0]);assert.deepEqual(first.rows,[expected]);
 const hook=await page.evaluate(()=>window.v12.mounted['0'].data);assert.deepEqual(hook.rows,[expected]);hookRows.push(hook);
 assert.throws(()=>old.check(first,[row],q));check(first,[row],q);
 const poisoned=structuredClone(first);delete poisoned.rows[0].label;old.check(poisoned,[row],q);assert.throws(()=>check(poisoned,[row],q));
 await page.waitForFunction(()=>window.v12.admission('row').outstanding===0);
 const before=await snapshot(),count=await page.evaluate(()=>window.v13ledger.filter(e=>e.type==='receive'&&e.message.type==='live').length);
 await put({...row,label:{state:'missing'}});const explicit=await snapshot();
 await put({...row,label:{state:'missing'},ignored:'source spelling only'});const extra=await snapshot();
 for(const r of [explicit,extra]){assert.equal(r.version,before.version);assert.deepEqual(r.rows,[expected]);}
 assert.equal(await page.evaluate(()=>window.v13ledger.filter(e=>e.type==='receive'&&e.message.type==='live').length),count);
 let version=extra.version;
 for(const label of [{state:'null'},{state:'value',value:''},{state:'missing'},{state:'value',value:'changed'}]){
  await put({...row,label});
  await page.waitForFunction(cut=>window.v12.results['row:q'].at(-1)?.remote.sourceSequence===cut&&window.v12.mounted['0']?.data?.remote?.sourceSequence===cut,String(offset));
  const result=await page.evaluate(()=>window.v12.results['row:q'].at(-1));
  const mounted=await page.evaluate(()=>window.v12.mounted['0'].data);assert.deepEqual(result.rows,[{...expected,label}]);assert.deepEqual(mounted.rows,result.rows);assert.equal(result.version,version+1);version=result.version;hookRows.push(mounted);
 }
 await page.evaluate(()=>window.v12.unmount());await page.waitForFunction(()=>window.v12.admission('row').outstanding===0);
 const ledger=await page.evaluate(()=>window.v13ledger),events=h.parsed();
 const oracle=verifyLedger(ledger,cuts),versions=verifyVersions(ledger,events,cuts);assert(oracle.live>=4);assert.throws(()=>old.verifyLedger(ledger,cuts));assert.throws(()=>old.verifyVersions(ledger,events,cuts));
 const bad=structuredClone(ledger),live=bad.find(e=>e.type==='receive'&&e.message.type==='live'&&e.message.results.q);assert(live);live.message.results.q.rows[0].label={state:'missing'};assert.throws(()=>verifyLedger(bad,cuts));
 const badVersion=structuredClone(ledger),last=badVersion.find(e=>e.type==='receive'&&e.message.type==='live'&&e.message.results.q);last.message.results.q.version++;assert.throws(()=>verifyVersions(badVersion,events,cuts));
 await page.evaluate(()=>window.v12.close('row'));await h.shutdown();assert(h.parsed().some(e=>e.state==='stopped'&&e.subscriptions===0&&e.shapes===0));
 const paths=['scripts/v13-oracle.mjs','scripts/test-v13-row-browser.mjs','browser/src/product.remote.worker.ts','browser/src/v12-harness.tsx'];
 await h.evidence({status:'passed',scope:'native socket, actual Worker/provider, mounted React hook rows',historical_archive_sha256:await hash(archive),historicalRejectsCorrect:true,historicalAcceptsPoison:true,poisonedLabelRejected:true,poisonedVersionRejected:true,equivalentSourceNoop:true,labelDistinctionsPreserved:true,finalZeroSubscriptions:true,hookRows,oracle,versions,ledger,cuts,server_events:h.parsed(),source_hashes:Object.fromEntries(await Promise.all(paths.map(async p=>[p,await hash((p.startsWith('scripts/')?projectRoot:root)+'/'+p)])))});
 console.log(JSON.stringify({status:'passed',oracle,versions}));
}finally{await h.cleanup();}
