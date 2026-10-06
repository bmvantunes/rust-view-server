// Focused actual native -> production Worker -> typed mounted consumers.
import fs from 'node:fs/promises';import path from 'node:path';import http from 'node:http';
import {spawn} from 'node:child_process';import {createRequire} from 'node:module';import assert from 'node:assert/strict';import {createHash} from 'node:crypto';
import {decodeGeneric} from '../experiments/v131/js/msgpack.mjs';
const W=path.resolve(import.meta.dirname,'..'),[configPath,out,rt]=process.argv.slice(2),require=createRequire(W+'/browser/package.json'),{chromium}=require('playwright');
const cfg=JSON.parse(await fs.readFile(configPath,'utf8')),token=process.env.V12_SESSION_TOKEN,catalog=JSON.parse(await fs.readFile(W+'/fixtures/proto-topics/browser-catalog.json','utf8'));
const children=[],logs=[],acks=[],wire=[],observations=[];let producer,server,web,browser,page,ack=0,phase='initial',webPort;
const pause=ms=>new Promise(r=>setTimeout(r,ms)),alive=p=>p&&p.exitCode===null&&p.signalCode===null;
async function wait(fn,label){const end=Date.now()+30000;while(Date.now()<end){if(await fn())return;await pause(25);}throw Error('timeout '+label+' '+JSON.stringify(logs.slice(-8)));}
function launch(binary,args,label){const p=spawn(binary,args,{env:process.env,cwd:rt});children.push(p);let pending='';p.on('error',e=>logs.push({label,text:String(e)}));for(const stream of [p.stdout,p.stderr])stream.on('data',b=>{logs.push({label,text:String(b)});if(label==='producer'&&stream===p.stdout){pending+=b;while(pending.includes('\n')){const at=pending.indexOf('\n'),line=pending.slice(0,at);pending=pending.slice(at+1);try{acks.push(JSON.parse(line));}catch{}}}});return p;}
async function put(topic,i,row){const id=++ack,key={tenant:'local',desk:'desk',account:String(i),partitionKey:String(i%2)};producer.stdin.write(JSON.stringify({topic,partition:i%2,ack:id,key,row})+'\n');await wait(()=>acks.some(v=>v.ack===id),'produce '+topic);assert(!acks.find(v=>v.ack===id).error);}
// Independent encodings for these fixed fixtures: no production groupId helper.
function gid(topic,fields,row){const parts=fields.map(name=>{const f=catalog[topic].schema.fields.find(f=>f.name===name);const state=Object.hasOwn(row,name)?row[name]===null?1:2:0;return[name,f.kind,state,state===2?row[name]:null];});return 'gid1:'+Buffer.from(JSON.stringify([1,topic,catalog[topic].fingerprint,parts])).toString('hex');}
function sourceId(i){const parts=[Buffer.from([1,4])];for(const [tag,value]of [[1,'local'],[1,'desk'],[5,i],[4,i%2]]){let bytes;if(tag===1)bytes=Buffer.from(value);else{bytes=Buffer.alloc(8);if(tag===5)bytes.writeBigUInt64BE(BigInt(value));else bytes.writeBigInt64BE(BigInt(value));}const header=Buffer.alloc(5);header[0]=tag;header.writeUInt32BE(bytes.length,1);parts.push(header,bytes);}return 'rid2:'+Buffer.concat(parts).toString('hex');}
const ranked=rows=>rows.sort((a,b)=>a.rowId<b.rowId?-1:a.rowId>b.rowId?1:0);
function expected(group,select){
 const grouped=group?[{symbol:'S0',total:1.5,mean:1.5},{symbol:'S1',total:2.5,mean:2.5}]:[{hedged:true,total:4,mean:2}];
 const presence=group?[{open:true,count:'1'},{open:true,note:null,count:'1'}]:[{open:true,customer:'A',count:'1'},{open:true,customer:'B',count:'1'}];
 return {
  grouped:ranked(grouped.map(r=>({...r,rowId:gid('positions',[group?'symbol':'hedged'],r)}))),
  selected:[0,1].map(i=>({...select?{symbol:'S'+i}:{quantity:String(i+3)},rowId:sourceId(i)})),
  presence:ranked(presence.map(r=>({...r,rowId:gid('orders',['open',group?'note':'customer'],r)})))
 };
}
async function check(group,select){const want=expected(group,select);await wait(async()=>{
 const observed=await page.evaluate(()=>window.a2Smoke.observe());
 try{for(const[name,rows]of Object.entries(want)){
  const d=observed.latest[name],sink=observed.windows[name];assert(d&&sink);assert.equal(d.groupChoice,group);assert.equal(d.selectChoice,select);
  assert.equal(d.whole.status,'ready');assert.equal(d.helper.status,'ready');
  assert.deepEqual(d.whole.rows,rows);assert.deepEqual(d.helper.rows,rows);assert.deepEqual(Object.values(sink.rows),rows);
  assert.equal(sink.choice,name==='selected'?select:group);assert.equal(d.whole.totalRows,rows.length);assert.equal(d.helper.totalRows,rows.length);assert.equal(observed.counts[name],rows.length);
  for(let i=0;i<rows.length;i++)assert.deepEqual(Object.keys(d.whole.rows[i]).sort(),Object.keys(rows[i]).sort());
 }return true;}catch{return false;}
 },'exact rows/keys/IDs on all three result paths '+phase);
 const value=await page.evaluate(()=>window.a2Smoke.observe());assert.deepEqual(value.mounts,{grouped:1,selected:1,presence:1});
 observations.push({phase,group,select,expected:want,observed:value,rendered:await page.locator('section').allTextContents()});
}
try{
 const build=W+'/build/a2';web=http.createServer(async(req,res)=>{try{const f=path.resolve(build,'.'+new URL(req.url,'http://local').pathname);if(!f.startsWith(build+'/'))throw Error('path');res.setHeader('Content-Type',f.endsWith('.js')?'text/javascript':'text/html');res.end(await fs.readFile(f));}catch{res.writeHead(404).end();}});
 await new Promise(r=>web.listen(0,'127.0.0.1',r));webPort=web.address().port;cfg.origin='http://127.0.0.1:'+webPort;await fs.writeFile(configPath,JSON.stringify(cfg));await fs.writeFile(out+'/configuration.json',JSON.stringify(cfg,null,2));
 producer=launch(W+'/bin/generic_kafka_producer_grouped',[configPath],'producer');await wait(()=>acks.some(a=>a.producer_ready),'producer');
 for(let i=0;i<2;i++){
  await put('positions',i,{positionId:'p'+i,symbol:'S'+i,quantity:String(i+3),risk:i+1.5,hedged:true});
  await put('orders',i,{orderId:'o'+i,customer:i?'B':'A',units:String(i+3),price:'1',open:true,...(i?{note:null}:{})});
 }
 server=launch(W+'/bin/view_server_grouped',[configPath],'service');await wait(()=>logs.some(l=>l.label==='service'&&l.text.includes('"state":"ready"')),'service');
 browser=await chromium.launch({headless:true});page=await browser.newPage();page.on('pageerror',e=>logs.push({label:'browser-error',text:String(e)}));
 page.on('websocket',ws=>ws.on('framereceived',e=>{try{wire.push({phase,value:decodeGeneric(new Uint8Array(e.payload))});}catch{}}));
 await page.goto(cfg.origin+'/a2-smoke.html');await page.evaluate(({url,token})=>window.a2Smoke.start(url,token),{url:'ws://'+cfg.bind+'/v15',token});
 await check(false,false);
 for(const[group,select]of [[true,false],[true,true],[false,true],[false,false]]){phase='group-symbol-'+group+'-select-symbol-'+select;await page.evaluate(([g,s])=>window.a2Smoke.choose(g,s),[group,select]);await check(group,select);}
 assert(!logs.some(l=>l.label==='browser-error'));assert.equal(wire.filter(f=>f.value.type==='ready').length,1);
 const ids=(v,n)=>v.observed.latest[n].whole.rows.map(r=>r.rowId);
 for(const v of observations)assert.deepEqual(ids(v,'selected'),ids(observations[0],'selected'));
 assert(!ids(observations[1],'grouped').some(id=>ids(observations[0],'grouped').includes(id)));
 assert.deepEqual(ids(observations.at(-1),'grouped'),ids(observations[0],'grouped'));
 assert.deepEqual(ids(observations.at(-1),'presence'),ids(observations[0],'presence'));
 const health=await(await fetch('http://'+cfg.health.bind+'/health',{headers:{Authorization:'Bearer '+token}})).json();assert.equal(health.connections,1);await fs.writeFile(out+'/health.json',JSON.stringify(health,null,2));
 const bins={};for(const n of ['view_server_grouped','view_server_grouped_faults','generic_kafka_producer_grouped'])bins[n]=createHash('sha256').update(await fs.readFile(W+'/bin/'+n)).digest('hex');
 await fs.writeFile(out+'/result.json',JSON.stringify({status:'PASS',scope:'A2 focused actual native/production Worker/mounted useLiveQuery + viewport whole helper + sink; independent concrete rows/keys/identities',phases:observations.length,providerConnections:1,mounts:observations.at(-1).observed.mounts,groupIdentityChangesWithGrouping:true,groupIdentityReproducesOnReturn:true,rawIdentityStableAcrossProjection:true,unchangedBinaries:bins},null,2));console.log('PASS '+out);
}finally{
 if(page)try{await fs.writeFile(out+'/last-browser.json',JSON.stringify(await page.evaluate(()=>window.a2Smoke.observe()),null,2));await page.evaluate(()=>window.a2Smoke.dispose());}catch{}
 await browser?.close();for(const c of children)if(alive(c))c.kill('SIGTERM');await pause(500);for(const c of children)if(alive(c))c.kill('SIGKILL');
 if(web)await new Promise(r=>web.close(r));
 for(const[name,data]of Object.entries({logs,acks,wire,observations}))await fs.writeFile(out+'/'+name+'.json',JSON.stringify(data,null,2));
 await fs.writeFile(out+'/child-cleanup.json',JSON.stringify({webPort,children:children.map(c=>({pid:c.pid,exit:c.exitCode,signal:c.signalCode}))},null,2));
}
