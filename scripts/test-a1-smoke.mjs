// Focused actual production Worker, mounted typed hooks, unchanged native service.
import fs from 'node:fs/promises';import path from 'node:path';import http from 'node:http';
import {spawn} from 'node:child_process';import {createRequire} from 'node:module';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {decodeGeneric} from '../experiments/v131/js/msgpack.mjs';
const W=path.resolve(import.meta.dirname,'..'),[configPath,out,rt]=process.argv.slice(2),require=createRequire(W+'/browser/package.json'),{chromium}=require('playwright');
const cfg=JSON.parse(await fs.readFile(configPath,'utf8')),token=process.env.V12_SESSION_TOKEN;
const children=[],logs=[],acks=[],wire=[],observations=[];let producer,server,web,browser,page,ack=0,phase='initial',webPort;
const pause=ms=>new Promise(r=>setTimeout(r,ms)),alive=p=>p&&p.exitCode===null&&p.signalCode===null;
async function wait(fn,label){const end=Date.now()+30000;while(Date.now()<end){if(await fn())return;await pause(25);}throw Error('timeout '+label+' '+JSON.stringify(logs.slice(-8)));}
function launch(binary,args,label){const p=spawn(binary,args,{env:process.env,cwd:rt});children.push(p);let pending='';p.on('error',e=>logs.push({label,text:String(e)}));for(const stream of [p.stdout,p.stderr])stream.on('data',b=>{logs.push({label,text:String(b)});if(label==='producer'&&stream===p.stdout){pending+=b;while(pending.includes('\n')){const at=pending.indexOf('\n'),line=pending.slice(0,at);pending=pending.slice(at+1);try{acks.push(JSON.parse(line));}catch{}}}});return p;}
async function put(topic,i,row){const id=++ack,key=topic==='grouped_fixture'?{key:String(i)}:{tenant:'local',desk:'desk',account:String(i),partitionKey:String(i%2)};producer.stdin.write(JSON.stringify({topic,partition:i%2,ack:id,key,row})+'\n');await wait(()=>acks.some(v=>v.ack===id),'produce '+topic);assert(!acks.find(v=>v.ack===id).error);}
const strip=rows=>rows.map(({rowId,...r})=>r);
function expected(field,operation){return{
 positions:[{hedged:true,total:field?4:'7',mean:field?2:'3.5'}],
 orders:[{open:true,value:operation?'3.5':'7',lowest:field?null:'A'}],
 grouped_fixture:['missing','null'].map(group=>({group,total:field?'0':0,mean:null,lowest:null,highest:null}))
};}
async function check(field,operation){const want=expected(field,operation);await wait(async()=>{
 const observed=await page.evaluate(()=>window.a1Smoke.observe());
 try{for(const [name,rows]of Object.entries(want)){
  const d=observed.latest[name],sink=observed.windows[name];assert(d&&sink);assert.equal(d.fieldChoice,field);assert.equal(d.operationChoice,operation);
  assert.equal(d.whole.status,'ready');assert.equal(d.helper.status,'ready');
  assert.deepEqual(strip(d.whole.rows),rows);assert.deepEqual(d.helper.rows,d.whole.rows);
  assert.equal(sink.fieldChoice,field);assert.equal(sink.operationChoice,operation);assert.deepEqual(Object.values(sink.rows),d.whole.rows);
  for(const r of d.whole.rows)assert(r.rowId.startsWith('gid1:'));
 }return true;}catch{return false;}
 },'all three result paths '+phase);
 const value=await page.evaluate(()=>window.a1Smoke.observe());assert.deepEqual(value.mounts,{positions:1,orders:1,grouped_fixture:1});
 observations.push({phase,field,operation,expected:want,observed:value,rendered:await page.locator('section').allTextContents()});
}
try{
 const build=W+'/build/a1';web=http.createServer(async(req,res)=>{try{const f=path.resolve(build,'.'+new URL(req.url,'http://local').pathname);if(!f.startsWith(build+'/'))throw Error('path');res.setHeader('Content-Type',f.endsWith('.js')?'text/javascript':'text/html');res.end(await fs.readFile(f));}catch{res.writeHead(404).end();}});
 await new Promise(r=>web.listen(0,'127.0.0.1',r));webPort=web.address().port;cfg.origin='http://127.0.0.1:'+webPort;await fs.writeFile(configPath,JSON.stringify(cfg));await fs.writeFile(out+'/configuration.json',JSON.stringify(cfg,null,2));
 producer=launch(W+'/bin/generic_kafka_producer_grouped',[configPath],'producer');await wait(()=>acks.some(a=>a.producer_ready),'producer');
 for(let i=0;i<2;i++){
  await put('positions',i,{positionId:'p'+i,symbol:'S',quantity:String(i+3),risk:i+1.5,hedged:true});
  await put('orders',i,{orderId:'o'+i,customer:i?'B':'A',units:String(i+3),price:'1',open:true,...(i?{note:null}:{})});
  await put('grouped_fixture',i,{group:'missing'});
  await put('grouped_fixture',i+2,{group:'null',number:null,signed:null,unsigned:null,decimal:null,boolean:null});
 }
 server=launch(W+'/bin/view_server_grouped',[configPath],'service');await wait(()=>logs.some(l=>l.label==='service'&&l.text.includes('"state":"ready"')),'service');
 browser=await chromium.launch({headless:true});page=await browser.newPage();page.on('pageerror',e=>logs.push({label:'browser-error',text:String(e)}));
 page.on('websocket',ws=>ws.on('framereceived',e=>{try{wire.push({phase,value:decodeGeneric(new Uint8Array(e.payload))});}catch{}}));
 await page.goto(cfg.origin+'/a1-smoke.html');await page.evaluate(({url,token})=>window.a1Smoke.start(url,token),{url:'ws://'+cfg.bind+'/v15',token});
 await check(false,false);
 for(const [field,operation]of [[true,false],[true,true],[false,true],[false,false]]){phase='field-'+field+'-avg-'+operation;await page.evaluate(([f,o])=>window.a1Smoke.choose(f,o),[field,operation]);await check(field,operation);}
 assert(!logs.some(l=>l.label==='browser-error'));assert.equal(wire.filter(f=>f.value.type==='ready').length,1);
 const health=await(await fetch('http://'+cfg.health.bind+'/health',{headers:{Authorization:'Bearer '+token}})).json();assert.equal(health.connections,1);await fs.writeFile(out+'/health.json',JSON.stringify(health,null,2));
 const bins={};for(const n of ['view_server_grouped','view_server_grouped_faults','generic_kafka_producer_grouped'])bins[n]=createHash('sha256').update(await fs.readFile(W+'/bin/'+n)).digest('hex');
 await fs.writeFile(out+'/result.json',JSON.stringify({status:'PASS',scope:'A1 focused smoke, production Worker, real Kafka, mounted useLiveQuery + viewport whole helper + sink; hard-coded independent expected values',phases:observations.length,providerConnections:1,mounts:observations.at(-1).observed.mounts,unchangedBinaries:bins},null,2));
 console.log('PASS '+out);
}finally{
 if(page)try{await fs.writeFile(out+'/last-browser.json',JSON.stringify(await page.evaluate(()=>window.a1Smoke.observe()),null,2));await page.evaluate(()=>window.a1Smoke.dispose());}catch{}
 await browser?.close();for(const c of children)if(alive(c))c.kill('SIGTERM');await pause(500);for(const c of children)if(alive(c))c.kill('SIGKILL');
 if(web)await new Promise(r=>web.close(r));
 for(const[name,data]of Object.entries({logs,acks,wire,observations}))await fs.writeFile(out+'/'+name+'.json',JSON.stringify(data,null,2));
 await fs.writeFile(out+'/child-cleanup.json',JSON.stringify({webPort,children:children.map(c=>({pid:c.pid,exit:c.exitCode,signal:c.signalCode}))},null,2));
}
