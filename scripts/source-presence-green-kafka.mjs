// Real broker/native qualification. This is a wire peer, not a browser-provider gate.
import fs from 'node:fs/promises';import path from 'node:path';import {spawn,execFile} from 'node:child_process';import {promisify} from 'node:util';import {createRequire} from 'node:module';import assert from 'node:assert/strict';import net from 'node:net';import {createHash} from 'node:crypto';
import http from 'node:http';
import {encodeGeneric,decodeGeneric} from '../experiments/v131/js/msgpack.mjs';
const W=path.resolve(import.meta.dirname,'..'),[configPath,out,rt]=process.argv.slice(2),req=createRequire(W+'/browser/package.json');const {ws:WebSocket}=req(path.join(path.dirname(req.resolve('playwright')),'../playwright-core/lib/utilsBundle.js'));
const binary=process.env.TOPICS_BINARY??W+'/bin/view_server_kafka_topics',producerBinary=W+'/ingestion/target/debug/examples/generic_kafka_producer',exec=promisify(execFile);
const original=JSON.parse(await fs.readFile(configPath,'utf8')),cfg={...original,catalog:{...original.catalog,topics:original.catalog.topics.filter(t=>t.topic!=='wide')},sources:original.sources.filter(s=>s.topic!=='wide')},faultDir=rt+'/faults',children=[],logs=[],frames=[],acks=[],evidence={fairness:[],readiness:[],faults:[],admission:[]};let service,producer,client,ackId=0,sink;const exporterFailures=[];
const pause=ms=>new Promise(r=>setTimeout(r,ms));const alive=p=>p.exitCode===null&&p.signalCode===null;
async function wait(f,label,ms=45000){const end=performance.now()+ms;while(performance.now()<end){if(await f())return;await pause(20);}throw Error('timeout '+label+' '+logs.slice(-4).map(v=>v.text).join(''));}
function launch(bin,args,label,env={}){const p=spawn(bin,args,{cwd:rt,env:{...process.env,...env}});children.push(p);let buffer='';for(const s of [p.stdout,p.stderr])s.on('data',b=>{logs.push({label,at:Date.now(),text:b.toString()});if(label==='producer'&&s===p.stdout){buffer+=b;while(buffer.includes('\n')){const n=buffer.indexOf('\n'),line=buffer.slice(0,n);buffer=buffer.slice(n+1);try{acks.push(JSON.parse(line));}catch{}}}});return p;}
async function produce(topic,partition,row){const ack=++ackId;producer.stdin.write(JSON.stringify({topic,partition,row,ack})+'\n');await wait(()=>acks.some(v=>v.ack===ack),'producer ack');return acks.find(v=>v.ack===ack);}
const order=(id,price)=>({orderId:id,customer:'customer-'+id,open:true,units:'18446744073709551615',price:String(price)}),position=(id,risk)=>({positionId:id,symbol:'symbol-'+id,quantity:'-9223372036854775808',risk,hedged:false});
async function get(route){const r=await fetch('http://'+cfg.health.bind+route,{headers:{Authorization:'Bearer '+process.env.V12_SESSION_TOKEN}});return {status:r.status,body:await r.text()};}
async function health(){return JSON.parse((await get('/health')).body);}
async function arm(point,action='hold'){for(const ext of ['reached','release','arm'])await fs.rm(faultDir+'/'+point+'.'+ext,{force:true});await fs.writeFile(faultDir+'/'+point+'.arm',action);}
async function reached(point){await wait(()=>fs.access(faultDir+'/'+point+'.reached').then(()=>true,()=>false),point+' reached',12000);}
async function release(point){await fs.writeFile(faultDir+'/'+point+'.release','release');}
async function start(label,config=cfg){await fs.writeFile(configPath,JSON.stringify(config));service=launch(binary,[configPath],label,{V121_FAULT_DIR:faultDir});await wait(()=>logs.some(v=>v.label===label&&v.text.includes('"state":"ready"'))||!alive(service),label+' startup');assert(alive(service),logs.filter(v=>v.label===label).map(v=>v.text).join(''));await wait(async()=>{try{return(await get('/readyz')).status===200;}catch{return false;}},label+' ready');}
async function kill(){client?.socket.terminate();if(service&&alive(service)){service.kill('SIGKILL');await wait(()=>!alive(service),'native killed');}}
function reduce(prior,b){if(b.kind==='snapshot')return {...b,keys:b.keys.slice(),rows:structuredClone(b.rows)};assert(prior);assert.equal(b.fromRevision,prior.revision);const keys=prior.keys.slice(),rows=structuredClone(prior.rows);for(const op of b.operations){const i=keys.indexOf(op.key);if(op.type==='remove'){assert(i>=0);keys.splice(i,1);rows.splice(i,1);}else if(op.type==='insert'){assert.equal(i,-1);keys.splice(op.index,0,op.key);rows.splice(op.index,0,op.row);}else if(op.type==='update'){assert.equal(i,op.index);rows[i]=op.row;}else if(op.type==='move'){assert.equal(i,op.fromIndex);keys.splice(i,1);const row=rows.splice(i,1)[0];keys.splice(op.toIndex,0,op.key);rows.splice(op.toIndex,0,row);}else assert.fail('unknown delta');}return {...b,keys,rows};}
async function connect(config=cfg){
 const socket=new WebSocket('ws://'+config.bind+'/v15','view-server.v15.msgpack',{origin:config.origin}),c={socket,received:[],latest:{},ready:null,id:0};socket.on('error',e=>logs.push({label:'peer-error',text:e.message}));socket.on('message',b=>{const v=decodeGeneric(new Uint8Array(b));c.received.push(v);frames.push({at:Date.now(),value:v});if(v.type==='ready')c.ready=v;if(v.type==='result')c.latest[v.subscription]=reduce(c.latest[v.subscription],v.result);});await wait(()=>socket.readyState===WebSocket.OPEN,'wire socket');const catalog=Object.fromEntries(config.catalog.topics.map(t=>[t.topic,t.schema]));socket.send(encodeGeneric({v:15,type:'hello',token:process.env.V12_SESSION_TOKEN,nonce:'01234567890123456789012345678901',catalog,capabilities:['generic_schemas_v1','health_v1']}));await wait(()=>c.ready,'wire hello');c.send=v=>socket.send(encodeGeneric({v:15,incarnation:c.ready.incarnation,connection:c.ready.connection,nonce:c.ready.nonce,...v}));c.command=async(command,acquisition=1)=>{const id=++c.id;c.send({type:'command',request:{id,acquisition,previous_acquisition:null,traceparent:'00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01',command}});await wait(()=>c.received.some(v=>v.id===id&&(v.type==='ack'||v.type==='request_error')),'command '+id,10000);return c.received.find(v=>v.id===id&&(v.type==='ack'||v.type==='request_error'));};
 for(const topic of ['orders','positions']){const schema=catalog[topic],select=topic==='orders'?['orderId','price','customer']:['positionId','risk','symbol'],field=topic==='orders'?'orderId':'positionId';assert.equal((await c.command({command:'open',subscription:topic,query:{topic,schema,select,order_by:[{field,direction:'asc'}],offset:0,limit:32}})).type,'ack');}return c;
}
async function price(expected){await wait(()=>client.latest.orders?.rows.find(r=>r.orderId==='p1')?.price===String(expected),'orders price '+expected);}
async function stateEnds(source){const script='/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime/kafka_2.13-4.1.0/bin/kafka-get-offsets.sh';return (await exec(script,['--bootstrap-server',source.brokers,'--topic',source.state_topic,'--time','-1'],{env:process.env,timeout:30000})).stdout.trim();}
async function port(){const s=net.createServer();await new Promise(r=>s.listen(0,'127.0.0.1',r));const p=s.address().port;await new Promise(r=>s.close(r));return p;}
// SOURCE-PRESENCE green checks use exact raw bytes and read-only canonical/group cuts.
async function capture(label){
 const p=rt+'/probe-config.json';await fs.writeFile(p,JSON.stringify(cfg));
 const result=JSON.parse((await exec(W+'/ingestion/target/debug/examples/source_presence_probe',[p],{timeout:90000,env:process.env,maxBuffer:16*1024*1024})).stdout);
 await fs.writeFile(out+'/'+label+'.json',JSON.stringify(result,null,2));return result;
}
function canonicalProgress(c){return Object.fromEntries(Object.entries(c).map(([topic,v])=>{
 const state={next:{},manifest:null,rows:{},sourceGroup:v.source_group_committed};
 for(const r of v.records){const x=r.envelope.value;if(x.kind==='next')state.next[r.partition]=x.next;if(x.kind==='manifest')state.manifest=x;if(x.kind==='row')state.rows[x.key]=x;}
 return [topic,state];
}));}
function vi(n){n=BigInt(n);const b=[];while(n>127n){b.push(Number(n&127n)|128);n>>=7n;}b.push(Number(n));return Buffer.from(b)}
function str(tag,value){const b=Buffer.isBuffer(value)?value:Buffer.from(value);return Buffer.concat([vi(tag*8+2),vi(b.length),b])}
function num(tag,value){return Buffer.concat([vi(tag*8),vi(value)])}
function implicitRiskDescriptor(src,schema){
 const kinds={string:9,number:1,boolean:8,int64:3,uint64:4,decimal:9};let msg=str(1,'Positions'),oneofs=[];
 for(const m of src.mapping){const f=schema.fields.find(f=>f.name===m.field);let field=Buffer.concat([str(1,m.field),num(3,m.tag),num(4,1),num(5,kinds[f.kind])]);
  if(m.field!=='risk'){field=Buffer.concat([field,num(9,oneofs.length),num(17,1)]);oneofs.push(str(8,str(1,'_'+m.field)));}msg=Buffer.concat([msg,str(2,field)]);
 }msg=Buffer.concat([msg,...oneofs]);return str(1,Buffer.concat([str(4,msg),str(12,'proto3')])).toString('hex');
}
try{
 await fs.mkdir(faultDir,{recursive:true});await fs.writeFile(configPath,JSON.stringify(cfg));producer=launch(producerBinary,[configPath],'producer');await wait(()=>acks.some(v=>v.producer_ready),'producer ready');
 // Valid explicit defaults, including boolean false, empty non-key strings, numeric/exact zero.
 for(let p=0;p<2;p++){
  await produce('orders',p,{orderId:'p'+p,customer:'',open:false,units:'0',price:'0',...(p===0?{note:null}:{})});
  await produce('positions',p,{positionId:'p'+p,symbol:'',quantity:'0',risk:0,hedged:false});
 }
 const beforeStartup=await capture('A-before-startup');const bad=structuredClone(cfg),src=bad.sources.find(s=>s.topic==='positions'),schema=bad.catalog.schemas.find(s=>s.key==='positionId');src.value_descriptor.descriptor_hex=implicitRiskDescriptor(src,schema);
 await fs.writeFile(configPath,JSON.stringify(bad));service=launch(binary,[configPath],'A-implicit-rejection');await wait(()=>!alive(service),'implicit binding rejects',15000);assert.notEqual(service.exitCode,0);
 const diagnostic=logs.filter(x=>x.label==='A-implicit-rejection').map(x=>x.text).join('');assert(diagnostic.includes("source topic 'positions'")&&diagnostic.includes('SOURCE-PRESENCE')&&diagnostic.includes("field 'risk'")&&diagnostic.includes('tag 4')&&diagnostic.includes('proto3 optional'),diagnostic);
 assert(!diagnostic.includes('REQUIRED_FIELD_OMITTED'));const afterStartup=await capture('A-after-startup');assert.deepEqual(afterStartup,beforeStartup);assert(Object.values(afterStartup).every(x=>x.records.length===0));
 evidence.startup={passed:true,diagnostic,before:canonicalProgress(beforeStartup),after:canonicalProgress(afterStartup)};
 await start('C-explicit-defaults');client=await connect();
 for(const r of client.latest.positions.rows)assert.deepEqual(r,{positionId:r.positionId,risk:0,symbol:''});
 for(const r of client.latest.orders.rows)assert.deepEqual(r,{orderId:r.orderId,price:'0',customer:''});
 assert.equal(client.latest.positions.total_rows,2);assert.equal(client.latest.orders.total_rows,2);
 // Full projections independently verify explicit false and exact zero too.
 for(const topic of ['orders','positions']){const s=cfg.catalog.topics.find(t=>t.topic===topic),def=cfg.catalog.schemas.find(d=>d.key===(topic==='orders'?'orderId':'positionId'));assert.equal((await client.command({command:'open',subscription:'full-'+topic,query:{topic,schema:s.schema,select:def.fields.map(f=>f.name),order_by:[],offset:0,limit:10}})).type,'ack');}
 assert.deepEqual(client.latest['full-positions'].rows,[{positionId:'p0',symbol:'',quantity:'0',risk:0,hedged:false},{positionId:'p1',symbol:'',quantity:'0',risk:0,hedged:false}]);
 assert.deepEqual(client.latest['full-orders'].rows,[{orderId:'p0',customer:'',open:false,units:'0',price:'0',note:null},{orderId:'p1',customer:'',open:false,units:'0',price:'0'}]);
 await wait(async()=>{const h=await health();return h.sources.every(s=>s.partitions.every(p=>p.durable_next===p.derived_next));},'valid default cuts complete');
 const beforeInvalid=await capture('B-before-invalid');evidence.defaults={passed:true,wholeRows:client.latest,progress:canonicalProgress(beforeInvalid)};
 const originalSource=cfg.sources.find(s=>s.topic==='positions');const row={positionId:'omitted-risk',symbol:'REQUIRED_FIELD_OMITTED',quantity:'0',risk:777,hedged:false};let payload=Buffer.alloc(0);
 for(const m of originalSource.mapping){if(m.field==='risk')continue;const f=schema.fields.find(f=>f.name===m.field),v=row[m.field];payload=Buffer.concat([payload,f.kind==='string'?str(m.tag,v):num(m.tag,f.kind==='boolean'?Number(v):BigInt.asUintN(64,BigInt(v)))]);}
 const header=Buffer.alloc(6);header.writeUInt32BE(originalSource.value_descriptor.schema_id,1);const raw=Buffer.concat([header,payload]).toString('hex'),ack=++ackId;producer.stdin.write(JSON.stringify({topic:'positions',partition:0,row,raw_value_hex:raw,ack})+'\n');await wait(()=>acks.some(v=>v.ack===ack),'raw omitted record reaches source');const sourceAck=acks.find(v=>v.ack===ack);
 await wait(()=>!alive(service),'explicit omission fails service');assert.notEqual(service.exitCode,0);const omittedDiagnostic=logs.filter(x=>x.label==='C-explicit-defaults').map(x=>x.text).join('');assert(omittedDiagnostic.includes('missing required field: risk'));assert(!frames.some(f=>f.value.type==='result'&&JSON.stringify(f.value.result).includes('omitted-risk')));
 const afterInvalid=await capture('B-after-invalid');assert.deepEqual(canonicalProgress(afterInvalid),canonicalProgress(beforeInvalid));assert.equal(afterInvalid.positions.source_group_committed['0'],'Offset('+sourceAck.offset+')');
 client.socket.terminate();service=launch(binary,[configPath],'B-successor-same-invalid');await wait(()=>!alive(service),'successor must retry/reject same invalid record');assert.notEqual(service.exitCode,0);assert(logs.filter(x=>x.label==='B-successor-same-invalid').some(x=>x.text.includes('missing required field: risk')));
 const afterRetry=await capture('B-after-successor-retry');assert.deepEqual(canonicalProgress(afterRetry),canonicalProgress(beforeInvalid));
 evidence.omission={passed:true,raw_value_hex:raw,sourceAck,before:canonicalProgress(beforeInvalid),after:canonicalProgress(afterInvalid),afterSuccessor:canonicalProgress(afterRetry),publishedInvalidRow:false,normalBarriersExcludedFromUserProgress:true};
 evidence.passed=true;evidence.issue='SOURCE-PRESENCE';evidence.binary=binary;evidence.sha256=createHash('sha256').update(await fs.readFile(binary)).digest('hex');evidence.scope='ordinary binary, real private Kafka, two topics/two partitions, native wire peer; not browser-hook evidence';await fs.writeFile(out+'/SOURCE-PRESENCE-green.json',JSON.stringify(evidence,null,2));console.log(JSON.stringify({passed:true,issue:evidence.issue,out,sha256:evidence.sha256}));
}finally{sink?.close();await fs.writeFile(out+'/raw-logs.json',JSON.stringify(logs,null,2));await fs.writeFile(out+'/fault-partial.json',JSON.stringify(evidence,null,2));await fs.writeFile(out+'/wire-frames.json',JSON.stringify(frames,null,2));await fs.writeFile(out+'/producer-acks.json',JSON.stringify(acks,null,2));client?.socket.terminate();for(const p of children)if(alive(p))p.kill('SIGTERM');await pause(500);for(const p of children)if(alive(p))p.kill('SIGKILL');}
