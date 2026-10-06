// Real release service -> socket -> actual Worker/provider -> mounted React.
import assert from 'node:assert/strict';
import {appendFile} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {setup,wait,root,projectRoot,hash} from './v131-browser-support.mjs';
import {check,verifyLedger,verifyVersions} from './v131-oracle.mjs';
const archive=projectRoot+'/rust-differential-product-20260929-review-checkpoint-v12.2.zip';
assert.equal(await hash(archive),'182e24d5911222f943c930059dc9317d44324d0a96c665ee14259fdd57062a09');
const old=await import('data:text/javascript;base64,'+execFileSync('python3',['-c','import sys,zipfile;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("scripts/v122-oracle.mjs"))',archive]).toString('base64'));
const h=await setup('integer-browser'),{page}=h;
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:2};
let offset=0;const cuts={'0':[]};
const row={id:'exact',category:'a',quantity:'9_007_199_254_740_993',amount:{coefficient:'-1__1_',scale:0},label:{state:'value',value:''}};
const expected={...row,quantity:'9007199254740993',amount:{coefficient:'-11',scale:0}};
async function put(r){const o=offset++;cuts[String(offset)]=[structuredClone(r)];await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');await wait(()=>h.parsed().some(e=>e.state==='source_committed'&&e.offset===o),'commit '+o);}
try{
 await h.server();await put(row);await h.connect('integer');
 await page.evaluate(q=>{window.v12.watch('integer','q',q);window.v12.mount('integer');},q);
 await page.waitForFunction(()=>document.querySelector('output')?.textContent==='1|exact'&&window.v12.results['integer:q']?.length===1);
 const first=await page.evaluate(()=>window.v12.results['integer:q'][0]);assert.deepEqual(first.rows,[expected]);assert.throws(()=>old.check(first,[row],q));check(first,[row],q);
 await page.waitForFunction(()=>window.v12.admission('integer').outstanding===0);
 const snapshot=()=>page.evaluate(async()=>(await window.v12.apply('integer',{command:'change_window',subscription:'q',offset:0,limit:2})).q);
 const before=await snapshot(),count=await page.evaluate(()=>window.v13ledger.filter(e=>e.type==='receive'&&e.message.type==='live').length);
 await put({...row,quantity:'+09007199254740993_',amount:{coefficient:'-0_110_',scale:1}});
 const after=await snapshot();assert.equal(after.version,before.version);assert.deepEqual(after.rows,[expected]);
 // No unsolicited publication is permitted for a canonical no-op source cut.
 assert.equal(await page.evaluate(()=>window.v13ledger.filter(e=>e.type==='receive'&&e.message.type==='live').length),count);
 await put({...row,label:{state:'value',value:'changed'}});
 await page.waitForFunction(()=>window.v12.results['integer:q'].at(-1).remote.sourceSequence==='3');
 await page.evaluate(()=>window.v12.unmount());await page.waitForFunction(()=>window.v12.admission('integer').outstanding===0);
 const ledger=await page.evaluate(()=>window.v13ledger),events=h.parsed();
 const oracle=verifyLedger(ledger,cuts),versions=verifyVersions(ledger,events,cuts);assert(oracle.live>=1);assert.throws(()=>old.verifyLedger(ledger,cuts));
 const bad=structuredClone(ledger),live=bad.find(e=>e.type==='receive'&&e.message.type==='live'&&e.message.results.q);assert(live);live.message.results.q.rows[0].quantity='9007199254740992';assert.throws(()=>verifyLedger(bad,cuts));
 const badVersion=structuredClone(ledger),last=badVersion.find(e=>e.type==='receive'&&e.message.type==='live'&&e.message.results.q);last.message.results.q.version++;assert.throws(()=>verifyVersions(badVersion,events,cuts));
 await page.evaluate(()=>window.v12.close('integer'));await h.shutdown();assert(h.parsed().some(e=>e.state==='stopped'&&e.subscriptions===0&&e.shapes===0));
 const paths=['scripts/v131-oracle.mjs','scripts/test-v131-integer-browser.mjs','browser/src/product.remote.worker.ts'];
 await h.evidence({status:'passed',scope:'native socket, actual Worker/provider, mounted React',historical_archive_sha256:await hash(archive),historicalRejectsCorrect:true,poisonedValueRejected:true,poisonedVersionRejected:true,equivalentSourceNoop:true,finalZeroSubscriptions:true,oracle,versions,ledger,cuts,server_events:events,source_hashes:Object.fromEntries(await Promise.all(paths.map(async p=>[p,await hash((p.startsWith('scripts/')?projectRoot:root)+'/'+p)])))});
 console.log(JSON.stringify({status:'passed',oracle,versions}));
}finally{await h.cleanup();}
