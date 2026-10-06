import {setup,wait,root,hash} from './v131-browser-support.mjs';
import {appendFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const h=await setup('r1-native-browser'),{page}=h;const source=[];let offset=0;
async function put(row){source.push(row);const o=offset++;await appendFile(h.feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row}})+'\n');await wait(()=>h.parsed().some(x=>x.state==='source_committed'&&x.offset===o),'commit');}
try{
 await h.server();for(const category of ['a','b','c'])for(let i=0;i<12;i++)await put({id:category+i,category,label:{state:'missing'},quantity:String(i+1),amount:{coefficient:String(100+source.length),scale:0}});
 await page.goto(new URL('/r1-demo.html',page.url()).href);await page.waitForFunction(()=>!!window.r1);await page.evaluate(({url,token})=>window.r1.start(url,token),{url:h.url,token:h.token});await page.waitForFunction(()=>document.querySelector('output')?.textContent==='ready:ready');
 const results=await page.evaluate(async()=>{
  const p=window.r1.provider(),observations=[],statuses=[],errors=[];
  const q=category=>({where_expr:{op:'condition',args:{field:'category_equals',condition:category}},direction:'ascending',offset:0,limit:2,projection:['id']});
  let armed=false,nested;const waitFor=async f=>{const end=performance.now()+10000;while(!f()){if(performance.now()>end)throw Error('page timeout');await new Promise(r=>setTimeout(r,5));}};
  const listener=Object.assign(r=>observations.push(r),{onStatus:s=>{statuses.push(s);if(armed&&s==='loading'){armed=false;nested=p.apply({command:'change_query',subscription:'r1-query',query:q('c')});}}});
  const release=p.watch('r1-query',q('a'),listener);await waitFor(()=>observations.length===1);armed=true;
  const outer=p.apply({command:'change_query',subscription:'r1-query',query:q('b')}).then(()=> 'admitted',e=>e.code);
  const outcomes=[await outer,await nested.then(()=> 'admitted',e=>e.code)];await waitFor(()=>observations.at(-1)?.rows[0]?.id==='c0');release();
  const windows=[];let nav=false,next;const stop=p.watch('r1-window',{...q('a'),where_expr:{op:'true'}},Object.assign(r=>windows.push(r),{onStatus:s=>{if(nav&&s==='loading'){nav=false;next=p.apply({command:'change_window',subscription:'r1-window',offset:8,limit:2});}}}));await waitFor(()=>windows.length===1);nav=true;
  const old=p.apply({command:'change_window',subscription:'r1-window',offset:4,limit:2}).then(()=> 'admitted',e=>e.code);const windowOutcomes=[await old,await next.then(()=> 'admitted',e=>e.code)];await waitFor(()=>windows.at(-1)?.start_rank===8);
  window.r1WindowResults=windows;window.r1WindowRelease=stop;return {observations,statuses,outcomes,windowOutcomes,windows,mounted:window.r1.observe(),consumerErrors:p.consumerErrors.map(x=>x.error.message)};
 });
 assert.deepEqual(results.outcomes,['read_superseded','admitted']);assert.deepEqual(results.windowOutcomes,['read_superseded','admitted']);assert.deepEqual(results.observations.map(r=>r.rows.map(x=>x.id)),[['a0','a1'],['c0','c1']]);assert.deepEqual(results.windows.map(x=>x.start_rank),[0,8]);assert.equal(results.consumerErrors.length,0);assert.deepEqual(results.statuses,['ready','loading','ready','closed']);
 await put({...source[8],quantity:'999'});await page.waitForFunction(()=>window.r1WindowResults.at(-1)?.remote.sourceSequence==='37');const live=await page.evaluate(()=>({windows:window.r1WindowResults,mounted:window.r1.observe(),ledger:window.v13ledger}));assert.equal(live.windows.at(-1).start_rank,8);assert.deepEqual(live.windows.at(-1).rows.map(x=>x.id),['a8','a9']);
 const canonical=[...new Map(source.map(r=>[r.id,r])).values()].sort((a,b)=>Number(a.amount.coefficient)-Number(b.amount.coefficient));const full=canonical.map(({id,quantity})=>({id,quantity}));const initial=source.slice(0,36).map(({id,quantity})=>({id,quantity}));for(const event of live.mounted.mounted){if(event.whole.status==='ready'){assert.equal(event.whole.totalRows,36);assert([initial,full].some(rows=>JSON.stringify(rows)===JSON.stringify(event.whole.rows)));}}
 const commands=live.ledger.filter(x=>x.type==='send'&&x.message.command.subscription?.startsWith('r1-')).map(x=>x.message.command);assert(!commands.some(x=>x.command==='change_query'&&x.query.where_expr.args.condition==='b'));assert(!commands.some(x=>x.command==='change_window'&&x.offset===4));
 await page.evaluate(()=>{window.r1WindowRelease();window.r1.dispose();});await h.shutdown();assert(h.parsed().some(x=>x.state==='stopped'&&x.subscriptions===0));
 await h.evidence({passed:true,scope:'real ordinary fixture v14 socket, actual Worker/provider, same-provider external watch status reentrancy; separately mounted StrictMode whole and viewport hooks',results,live,commands,sourceMutations:source,provider:await hash(root+'/browser/src/product-provider.tsx'),worker:await hash(root+'/browser/src/product.remote.worker.ts')});console.log('PASS R1 actual native/browser query and window, live and mounted hooks');
}finally{await h.cleanup();}
