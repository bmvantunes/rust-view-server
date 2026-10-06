import {setup,wait,root,hash} from './v131-browser-support.mjs';
import {appendFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const h=await setup('stage0-mixed-native-browser'),source=[];
try {
 await h.server();
 for(const category of ['a','b'])for(let i=0;i<12;i++){
  const row={id:category+i,category,label:{state:'missing'},quantity:String(i+1),amount:{coefficient:String(100+source.length),scale:0}};
  const offset=source.length;source.push(row);
  await appendFile(h.feed,JSON.stringify({partition:0,offset,mutation:{kind:'upsert',row}})+'\n');
  await wait(()=>h.parsed().some(x=>x.state==='source_committed'&&x.offset===offset),'commit');
 }
 await h.page.goto(new URL('/r1-demo.html',h.page.url()).href);
 await h.page.waitForFunction(()=>!!window.r1);
 await h.page.evaluate(({url,token})=>window.r1.start(url,token),{url:h.url,token:h.token});
 await h.page.waitForFunction(()=>document.querySelector('output')?.textContent==='ready:ready');
 const result=await h.page.evaluate(async()=>{
  const p=window.r1.provider(),observed=[],statuses=[];
  const query=category=>({where_expr:{op:'condition',args:{field:'category_equals',condition:category}},direction:'ascending',offset:0,limit:2,projection:['id']});
  const until=async f=>{const end=performance.now()+10000;while(!f()){if(performance.now()>end)throw Error('page timeout');await new Promise(r=>setTimeout(r,5));}};
  const settle=p=>p.then(()=> 'admitted',e=>e.code??e.message);let armed=false,nested;
  const release=p.watch('stage0-mixed',query('a'),Object.assign(r=>observed.push({rows:r.rows,remote:r.remote,rank:r.start_rank,desired:structuredClone(p.listeners.get('stage0-mixed').desired)}),{onStatus:s=>{
   statuses.push(s);if(armed&&s==='loading'){armed=false;nested=settle(p.apply({command:'change_window',subscription:'stage0-mixed',offset:8,limit:2}));}
  }}));
  await until(()=>observed.length===1);armed=true;
  const outer=settle(p.apply({command:'change_query',subscription:'stage0-mixed',query:query('b')}));
  const outcomes=[await outer,await nested];await until(()=>observed.length===2);
  const entry=p.listeners.get('stage0-mixed');
  const evidence={outcomes,observed,statuses,desired:structuredClone(entry.desired),confirmed:structuredClone(entry.confirmedDesired),status:entry.status,consumerErrors:p.consumerErrors.map(e=>e.error.message),outstanding:p.admission.outstanding,wire:window.v13ledger.filter(x=>x.message.command?.subscription==='stage0-mixed'||x.message.results?.['stage0-mixed'])};
  release();return evidence;
 });
 await h.page.evaluate(()=>window.r1.dispose());await h.shutdown();
 const actual=result.observed.at(-1).rows.map(r=>r.id),expected=source.filter(r=>r.category==='b').slice(8,10).map(r=>r.id);
 await h.evidence({passed:JSON.stringify(actual)===JSON.stringify(expected),scope:'real private-loopback ordinary fixture service, production v14 MessagePack Worker, unchanged provider, same provider mounts both StrictMode query hooks; direct watch callback triggers mixed replacement',result,actual,expected,provider:await hash(root+'/browser/src/product-provider.tsx'),worker:await hash(root+'/browser/src/product.remote.worker.ts'),source,stopped:h.parsed().find(x=>x.state==='stopped')});
 console.log(JSON.stringify({outcomes:result.outcomes,status:result.status,actual,expected,desired:result.desired,confirmed:result.confirmed},null,2));
 assert.deepEqual(actual,expected,'READY rows must match latest composed query/window intent');
} finally {await h.cleanup();}
