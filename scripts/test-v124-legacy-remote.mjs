// Real native binary + loopback WebSocket + Chromium Worker + mounted React.
import {spawn} from 'node:child_process';
import {mkdtemp,writeFile,appendFile,readFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
import {createServer} from 'node:net';
import {get as httpGet} from 'node:http';
const httpReady=url=>new Promise(resolve=>{const req=httpGet(url,response=>{response.resume();resolve(response.statusCode===200);});req.on('error',()=>resolve(false));req.setTimeout(2000,()=>req.destroy());});
import {createHash,randomBytes} from 'node:crypto';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const root=resolve(import.meta.dirname,'..');const require=createRequire(join(root,'browser/package.json'));const {chromium}=require('playwright');
const temporary=await mkdtemp(join(tmpdir(),'v12-remote-'));const token=randomBytes(24).toString('hex');
const children=[];const logs=[];const samples=[];let browser;
async function port(){const s=createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
const http=await port();let ws=await port();
function launch(command,args,options={}){const p=spawn(command,args,{cwd:root,detached:true,env:{...process.env,V12_SESSION_TOKEN:token},...options});children.push(p);p.on('error',e=>logs.push(String(e)));p.stdout?.on('data',b=>logs.push(b.toString()));p.stderr?.on('data',b=>logs.push(b.toString()));return p;}
async function wait(test,label){const end=Date.now()+15000;while(Date.now()<end){if(await test())return;await new Promise(r=>setTimeout(r,10));}throw Error('timeout '+label+'\n'+logs.join('').slice(-4000));}
const feed=join(temporary,'fixture.jsonl'),db=join(temporary,'canonical.db'),stop=join(temporary,'stop');await writeFile(feed,'');
const binary=process.env.V12_SERVICE_BINARY||join(root,'ingestion/target/debug/view_server');
async function server(){const config={bind:`127.0.0.1:${ws}`,origin:`http://127.0.0.1:${http}`,database:db,source:{incarnation:'v12-browser-fixture',topic:'products',schema:'product-v1'},expected_partitions:[0],mode:{kind:'fixture',path:feed},run_ms:180000,stop_file:stop};const cp=join(temporary,'config.json');await writeFile(cp,JSON.stringify(config));const start=logs.length;const p=launch(binary,[cp]);await wait(()=>logs.slice(start).join('').includes('"state":"ready"'),'native ready');return p;}
let offset=0;
const canonical=new Map();
function row(id,amount,label=id){return {id,category:'a',label:{state:'value',value:label},quantity:'9223372036854775807',amount:{coefficient:String(amount),scale:2}};}
async function put(r){canonical.set(r.id,r);const o=offset++;await appendFile(feed,JSON.stringify({partition:0,offset:o,mutation:{kind:'upsert',row:r}})+'\n');await wait(()=>logs.join('').includes(`"offset":${o},`),'durable source '+o);}
try{
 const vite=launch(join(root,'browser/node_modules/.bin/vp'),['dev','--host','127.0.0.1','--port',String(http),'--strictPort'],{cwd:join(root,'browser')});await wait(async()=>{return await httpReady(`http://127.0.0.1:${http}/remote-demo.html`);},'Vite');
 let native=await server();
 await put(row('b',-201));await put(row('a',-1001));await put(row('c',-201));
 browser=await chromium.launch({headless:true});const page=await browser.newPage();await page.goto(`http://127.0.0.1:${http}/remote-demo.html`);await page.waitForFunction(()=>!!window.v12);
 const url=()=>`ws://127.0.0.1:${ws}/v13`;
 await page.evaluate(async({url,token})=>{await window.v12.connect('one',url,token);await window.v12.connect('two',url,token);window.v12.watch('one','same');window.v12.watch('two','same',{where_expr:{op:'true'},direction:'ascending',offset:1,limit:1});window.v12.mount('one');},{url:url(),token});
 await page.waitForFunction(()=>window.v12.results['one:same']?.length===1&&window.v12.results['two:same']?.length===1);
 let values=await page.evaluate(()=>[window.v12.results['one:same'].at(-1),window.v12.results['two:same'].at(-1)]);assert.deepEqual(values[0].rows.map(r=>r.id),['a','b','c']);assert.deepEqual(values[1].rows.map(r=>r.id),['b']);assert.equal(values[0].rows[0].quantity,'9223372036854775807');
 await page.waitForFunction(()=>document.querySelector('output')?.textContent==='3|a,b,c');
 await put(row('a',-1001,'payload-only'));await page.waitForFunction(()=>window.v12.results['one:same'].at(-1)?.rows[0].label.value==='payload-only');
 await put(row('z',99999));await page.waitForFunction(()=>window.v12.results['two:same'].at(-1)?.total_rows===4);
 const before=await page.evaluate(()=>window.v12.results['one:same'].length);await put(row('z',99999));
 // A command on the same owner supplies a completion barrier after the no-op.
 await page.evaluate(()=>window.v12.snapshot('two','barrier'));assert.equal(await page.evaluate(()=>window.v12.results['one:same'].length),before);
 const rejected=await page.evaluate(async()=>{try{await window.v12.apply('one',{command:'change_query',subscription:'same',query:{where_expr:{op:'unknown'},direction:'ascending',offset:0,limit:10}});return false;}catch{return true;}});assert(rejected);
 await put(row('a',-1001,'after-rejection'));await page.waitForFunction(()=>window.v12.results['one:same'].at(-1)?.rows[0].label.value==='after-rejection');
 for(const start of [100000,4,0]){const r=await page.evaluate(async start=>(await window.v12.apply('two',{command:'change_window',subscription:'same',offset:start,limit:start===0?0:2})).same,start);assert.equal(r.start_rank,start);assert.equal(r.rows.length,0);assert.equal(r.total_rows,4);}
 await page.evaluate(()=>window.v12.close('two'));await wait(()=>logs.join('').includes('"state":"client_closed"'),'staggered cleanup');
 // Fixed seed bounded lifecycle; independent exact integer amount ordering outside timing.
 let seed=90210;const oracle=[];
 for(let i=0;i<80;i++){
  seed=(Math.imul(seed,1664525)+1013904223)>>>0;const id='r'+(seed%20).toString().padStart(2,'0');await put(row(id,-(seed%997+1),`iteration-${i}`));
  const start=seed%24,limit=seed%7;const t=process.hrtime.bigint();const r=await page.evaluate(async({start,limit,i})=>(await window.v12.apply('one',{command:i===0?'open':'change_query',subscription:'random',query:{where_expr:{op:'true'},direction:'ascending',offset:start,limit}})).random,{start,limit,i});const ns=Number(process.hrtime.bigint()-t);
  const sorted=[...canonical.values()].sort((a,b)=>Number(BigInt(a.amount.coefficient)-BigInt(b.amount.coefficient))||a.id.localeCompare(b.id));
  assert.equal(r.total_rows,sorted.length);assert.deepEqual(r.rows.map(x=>x.id),sorted.slice(start,start+limit).map(x=>x.id));oracle.push({iteration:i,start,limit,ids:r.rows.map(x=>x.id),total:r.total_rows});samples.push({iteration:i,round_trip_ns:ns,rows:r.rows.length});
 }
 // Captured live publication structure check; exact per-cut oracle coverage is separate.
 values=await page.evaluate(()=>window.v12.results['one:same']);for(const v of values){assert(v.rows.every(r=>typeof r.quantity==='string'&&typeof r.amount.coefficient==='string'));assert(v.total_rows>=v.rows.length);}
 await page.evaluate(()=>window.v12.mountViewport('one'));await page.waitForFunction(()=>document.querySelector('output')?.textContent==='ready');
 const viewport=await page.evaluate(()=>({total:document.getElementById('root').dataset.total,window:JSON.parse(document.getElementById('root').dataset.window)}));assert.equal(Number(viewport.total),canonical.size);assert.deepEqual(Object.keys(viewport.window),['1']);
 native.kill('SIGKILL');await new Promise(r=>native.once('exit',r));
 await page.waitForFunction(()=>window.v12.errors['one:same'].length>0);await page.waitForFunction(()=>document.querySelector('output')?.textContent?.startsWith('ERROR:'));await page.evaluate(()=>window.v12.unmount());
 const incarnation=JSON.parse(logs.join('').split('\n').find(l=>l.includes('"state":"ready"'))).incarnation;
 const start=logs.length;native=await server();const second=JSON.parse(logs.slice(start).join('').split('\n').find(l=>l.includes('"state":"ready"'))).incarnation;assert.notEqual(incarnation,second);
 const recovered=await page.evaluate(async({url,token})=>{await window.v12.connect('fresh',url,token);return window.v12.snapshot('fresh','same',{where_expr:{op:'true'},direction:'ascending',offset:0,limit:100});},{url:url(),token});assert.equal(recovered.total_rows,canonical.size);assert.equal(recovered.rows.find(r=>r.id==='a').label.value,'after-rejection');
 // Ordinary query socket cannot directly mutate canonical state.
 assert(await page.evaluate(async()=>{try{await window.v12.apply('fresh',{command:'delete',id:'a'});return false;}catch{return true;}}));
 await page.evaluate(()=>{window.v12.close('fresh');window.v12.close('one');});
 await writeFile(stop,'stop');await new Promise(r=>native.once('exit',r));assert(logs.join('').includes('"shapes":0,"state":"stopped","subscriptions":0'));
 const evidence={status:'passed',binary_sha256:createHash('sha256').update(await readFile(binary)).digest('hex'),browser:await browser.version(),node:process.version,react:require('react/package.json').version,transport:'real loopback WebSocket',worker:'product.remote.worker.ts; no WASM',seed:90210,lifecycle_iterations:80,live_publications_structure_checked:values.length,oracle,samples,clock:'Node hrtime request through browser evaluation and native response; no cross-process subtraction; not paint'};
 await writeFile(join(root,'evidence/v124-remote.json'),JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify({...evidence,oracle:undefined,samples:undefined}));
}catch(e){console.error(logs.join('').slice(-6000));throw e;}finally{await browser?.close();for(const p of children){try{process.kill(-p.pid,'SIGTERM');}catch{}}await writeFile(join(root,'evidence/v124-remote.log'),logs.join(''));await rm(temporary,{recursive:true,force:true});}
