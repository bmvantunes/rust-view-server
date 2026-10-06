import {reconstruct} from '../browser/src/row-delta.mjs';
// Actual remote Worker, deterministic fake socket and manual time. No native/browser claim.
import {readFile,writeFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {encode,decode,decodeNative,adapt,prepare,encodePrepared} from '../experiments/v131/js/codec.mjs';
import assert from 'node:assert/strict';
import {hostile} from './v131-hostile-vectors.mjs';
const root=process.env.V13_CANDIDATE_ROOT;assert(root);const codec=process.env.V13_CODEC;const source=await readFile(root+'/browser/src/product.remote.worker.ts','utf8');
const code=stripTypeScriptTypes(source.replace(/^import \{[^\n]+\}[^\n]+\n/gm, '')).replace(/export \{\};?/g,'');
const results=[];
const admissionSource=await readFile(new URL('../browser/src/request-admission.ts',import.meta.url),'utf8');
const wasm=await readFile(new URL('../browser/public/request_admission.wasm',import.meta.url));
const admissionContext=vm.createContext({WebAssembly,TextEncoder,TextDecoder,fetch:async()=>({ok:true,arrayBuffer:async()=>wasm})});
vm.runInContext(stripTypeScriptTypes(admissionSource.replaceAll('export ','')),admissionContext);await admissionContext.initializeAdmission();
async function setup(){
 let now=0,next=0,socket;const timers=new Map(),posts=[];
 const scope={postMessage:m=>{if(m.type!=='v13_metrics')posts.push(structuredClone(m));}};
 class Socket{static OPEN=1;readyState=1;bufferedAmount=0;sent=[];fail=false;constructor(){socket=this;}send(v){if(this.fail)throw Error('injected send failure');this.sent.push(codec==='json'?JSON.parse(v):decode(v,codec));}close(){this.closed=true;}}
 const context=vm.createContext({structuredClone,reconstruct,initializeAdmission:async()=>{},admitEnvelope:admissionContext.admitEnvelope,self:scope,WebSocket:Socket,URL,TextEncoder,ArrayBuffer,encode,decodeNative,adapt,crypto:webcrypto,Uint8Array,performance:{now:()=>now},setTimeout:(fn,ms)=>{timers.set(++next,{fn,at:now+ms});return next;},clearTimeout:id=>timers.delete(id),setInterval:(fn,ms)=>{timers.set(++next,{fn,at:now+ms,ms});return next;},clearInterval:id=>timers.delete(id)});vm.runInContext(code,context);
 const input=m=>scope.onmessage({data:m});await input({type:'configure',options:{url:'ws://127.0.0.1:8080/'+(codec==='json'?'v12':'v14'),token:'x'.repeat(32)}});socket.onopen();
 const nonce=socket.sent[0].nonce,envelope={v:codec==='json'?1:14,nonce,incarnation:'a'.repeat(32),connection:'1'};
 const frame=m=>{const value={...envelope,...m};if(value.id===undefined)delete value.id;const b=codec==='json'?JSON.stringify(value):encode(JSON.parse(JSON.stringify(value)),codec);socket.onmessage({data:typeof b==='string'?b:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});};frame({type:'ready',coverage:[0],limits:{per_client:70,total:80}});
 const request={type:'apply',id:1,acquisition:1,traceparent:'00-'+ 'a'.repeat(32)+'-'+ 'b'.repeat(16)+'-01',command:{command:'open',subscription:'s',query:{where_expr:{op:'true'},direction:'ascending',offset:0,limit:4}}};
 const result={type:'result',id:1,acquisition:1,traceparent:request.traceparent,subscription:'s',source_sequence:'1',result:{kind:'snapshot',projection:['id','category','quantity','amount','label'],keys:['x'],revision:1,contentVersion:1,windowId:1,effectiveEnd:1,subscription:'s',query_generation:1,sequence:1,start_rank:0,version:1,total_rows:1,rows:[{id:'x',category:'a',quantity:'9223372036854775807',amount:{coefficient:'-1001',scale:2},label:{state:'missing'}}]}};
 const ack={type:'ack',id:1,traceparent:request.traceparent,result_count:1};
 const tick=ms=>{const end=now+ms;for(;;){let chosen;for(const [id,t] of timers)if(t.at<=end&&(!chosen||t.at<chosen[1].at))chosen=[id,t];if(!chosen)break;const[id,t]=chosen;now=t.at;timers.delete(id);if(t.ms)timers.set(id,{...t,at:now+t.ms});t.fn();}now=end;};
 return {socket,posts,input,frame,request,result,ack,tick};
}
for(const [name,modify] of Object.entries({wrong_incarnation:r=>({...r,incarnation:'b'.repeat(32)}),wrong_connection:r=>({...r,connection:'2'}),wrong_nonce:r=>({...r,nonce:'b'.repeat(32)}),wrong_acquisition:r=>({...r,acquisition:2}),wrong_subscription:r=>({...r,subscription:'x'}),wrong_trace:r=>({...r,traceparent:'bad'}),unsafe_integer:r=>({...r,result:{...r.result,total_rows:2**53}}),inexact_quantity:r=>({...r,result:{...r.result,rows:[{...r.result.rows[0],quantity:42}]}}),invalid_cut:r=>({...r,source_sequence:1})})){
 if(codec!=='json'&&['unsafe_integer','inexact_quantity','invalid_cut'].includes(name)){const s=await setup();s.input(s.request);const bad=prepare({...s.result,v:14,nonce:s.socket.sent[0].nonce,incarnation:'a'.repeat(32),connection:'1'});if(name==='unsafe_integer')bad.result.total_rows=2**53;else if(name==='inexact_quantity')bad.result.rows[0].quantity=42;else bad.source_sequence=1;const b=encodePrepared(bad,codec);s.socket.onmessage({data:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);s.tick(10000);assert.equal(s.posts.filter(x=>x.type==='ack').length,0);results.push({name,status:'terminal malformed binary rejected'});continue;}
 if(['wrong_acquisition','wrong_subscription','wrong_trace','invalid_cut'].includes(name)){const s=await setup();s.input(s.request);s.frame(modify(s.result));s.frame(s.ack);s.tick(20000);assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.equal(s.posts.filter(x=>x.type==='ack').length,0);results.push({name,status:'explicit terminal invalid frame, exactly once'});continue;}
 const s=await setup();s.input(s.request);s.frame(modify(s.result));s.frame(s.ack);assert.equal(s.posts.length,1,name);s.frame(s.result);s.frame(s.ack);assert.equal(s.posts.filter(x=>x.type==='ack').length,1);s.frame(s.ack);s.tick(9999);assert.equal(s.posts.filter(x=>x.type==='fatal').length,0);results.push({name,status:'passed'});
 const t=await setup();t.input(t.request);t.frame(modify(t.result));t.frame(t.ack);t.tick(10000);assert.equal(t.posts.filter(x=>x.type==='fatal').length,1);assert.match(t.posts.at(-1).error,/uncertain/);t.frame(t.result);t.frame(t.ack);assert.equal(t.posts.filter(x=>x.type==='ack').length,0);results.push({name:name+'_timeout',status:'passed'});
}
for(const phase of ['before_result','between_result_ack','after_ack','close','dispose']){
 const s=await setup();s.input(s.request);if(phase!=='before_result')s.frame(s.result);if(['after_ack','close','dispose'].includes(phase))s.frame(s.ack);
 if(phase==='close')s.input({...s.request,id:2,command:{command:'close',subscription:'s'}});
 if(phase==='dispose')s.input({type:'dispose'});else s.socket.onclose({reason:'test'});
 s.tick(20000);assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.equal(s.posts.filter(x=>x.type==='ack').length,['after_ack','close','dispose'].includes(phase)?1:0);results.push({name:'loss_'+phase,status:'passed'});
}
for(const mode of ['throw','buffer']){const s=await setup();if(mode==='throw')s.socket.fail=true;else s.socket.bufferedAmount=codec==='json'?131072:8388608;s.input(s.request);s.tick(20000);assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.match(s.posts.at(-1).error,/uncertain/);results.push({name:'send_'+mode,status:'passed'});}
for(const phase of ['normal','disconnect_before_error','disconnect_after_error','dispose','close']){
 const s=await setup();s.input(s.request);s.frame(s.result);s.frame(s.ack);
 const invalid={...s.request,id:2,acquisition:2,command:{command:'change_query',subscription:'s',query:{where_expr:{op:'condition',args:{field:'amount',condition:{op:'equal',value:{coefficient:'1',scale:10001}}}},direction:'ascending',offset:0,limit:4}}};
 s.input(invalid);assert.equal(s.posts.filter(x=>x.type==='request_error').length,0);
 assert.equal(s.socket.sent.at(-1).type,codec==='json'?'command':'command_rejected');
 const error={type:'request_error',id:2,traceparent:s.request.traceparent,error:'invalid typed query command',currentAcquisition:1};
 if(phase==='disconnect_before_error')s.socket.onclose({reason:'before rejection'});
 if(phase==='dispose')s.input({type:'dispose'});
 s.frame(error);
 if(phase==='disconnect_after_error')s.socket.onclose({reason:'after rejection'});
 if(['normal','close'].includes(phase)){
  const successor={...s.request,id:3,acquisition:3};s.input(successor);s.frame({...s.result,id:3,acquisition:3});s.frame({...s.ack,id:3});
  const length=s.posts.length;s.frame(error);assert.equal(s.posts.length,length,'stale rejection settled twice');
  s.frame({...s.result,id:undefined,acquisition:3,result:{...s.result.result,revision:2}});assert.equal(s.posts.at(-1).type,'live');
  if(phase==='close'){s.input({...successor,id:4,command:{command:'close',subscription:'s'}});s.frame({...s.ack,id:4,result_count:0});const count=s.posts.length;s.frame(error);s.frame({...s.result,id:undefined,acquisition:3});assert.equal(s.posts.length,count);}
 }
 assert.equal(s.posts.filter(x=>x.type==='request_error').length,['disconnect_before_error','dispose'].includes(phase)?0:1);
 assert.equal(s.posts.filter(x=>x.type==='fatal').length,['disconnect_before_error','disconnect_after_error','dispose'].includes(phase)?1:0);
 results.push({name:'ordered_admission_'+phase,status:'passed'});
}
if(codec!=='json')for(const [name,bytes] of Object.entries(hostile[codec])){
 const s=await setup();s.input(s.request);s.frame(s.result);s.frame(s.ack);
 s.socket.onmessage({data:Uint8Array.from(bytes).buffer});assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.equal(s.socket.closed,true);
 s.frame({...s.result,id:undefined});assert.equal(s.posts.filter(x=>x.type==='live').length,0);
 results.push({name:'terminal_'+name,status:'passed'});
}
if(codec!=='json'){
 const s=await setup();s.frame({type:'pong',v:999});assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.equal(s.socket.closed,true);results.push({name:'terminal_incompatible_version',status:'passed'});
}
for(const mode of ['missing_base','wrong_revision','wrong_window','duplicate_delivery','partial_invalid_batch']){
 const s=await setup();s.input(s.request);
 const delta={...s.result,id:undefined,result:{...s.result.result,kind:'delta',rows:undefined,keys:undefined,revision:2,fromRevision:1,fromVersion:1,toVersion:2,contentVersion:2,operations:[{type:'update',key:'x',index:0,row:{...s.result.result.rows[0],label:{state:'value',value:'changed'}}}]}};
 if(mode==='missing_base'){s.frame({...delta,id:1});}
 else{s.frame(s.result);s.frame(s.ack);if(mode==='wrong_revision')delta.result.fromRevision=0;if(mode==='wrong_window')delta.result.windowId=9;if(mode==='partial_invalid_batch')delta.result.operations.push({type:'remove',key:'not-present'});if(mode==='duplicate_delivery'){s.frame(delta);s.frame(delta);}else s.frame(delta);}
 assert.equal(s.posts.filter(p=>p.type==='fatal').length,1);assert.equal(s.posts.filter(p=>p.type==='live').length,mode==='duplicate_delivery'?1:0);s.tick(20000);assert.equal(s.posts.filter(p=>p.type==='fatal').length,1);results.push({name:'delta_'+mode,status:'terminal exactly once, no partial publication'});
}
{
 const s=await setup();s.input(s.request);s.frame(s.result);s.frame(s.ack);s.frame({...s.result,id:undefined,result:{...s.result.result,kind:'delta',rows:undefined,keys:undefined,revision:2,fromRevision:1,fromVersion:1,toVersion:1,contentVersion:1,operations:[],total_rows:2}});assert.equal(s.posts.at(-1).type,'live');assert.equal(s.posts.at(-1).results.s.total_rows,2);assert.deepEqual(s.posts.at(-1).results.s.rows,s.result.result.rows);results.push({name:'delta_total_only',status:'passed'});
}
for(const closeCode of [1002,1007,1008,1009]){const s=await setup();s.socket.onclose({code:closeCode,reason:'structured policy'});assert.equal(s.posts.at(-1).recoverable,false);results.push({name:'terminal_close_'+closeCode,status:'passed'});}
{
 const s=await setup();s.input(s.request);s.frame(s.result);
 s.frame({...s.result,id:undefined,result:{...s.result.result,kind:'delta',rows:undefined,keys:undefined,revision:2,fromRevision:1,fromVersion:1,toVersion:2,contentVersion:2,operations:[{type:'update',key:'x',index:0,row:{...s.result.result.rows[0],label:{state:'value',value:'before-ACK'}}}]}});
 assert.equal(s.posts.filter(p=>p.type==='live').length,0);s.frame(s.ack);assert.equal(s.posts.at(-1).type,'ack');assert.equal(s.posts.at(-1).results.s.rows[0].label.value,'before-ACK');results.push({name:'dependent_delta_before_admission_ACK',status:'staged atomically, admitted once'});
}
{
 const s=await setup();s.tick(12000);assert.equal(s.posts.at(-1).recoverable,true);assert.equal(s.posts.at(-1).code,'heartbeat-timeout');results.push({name:'quiet_blackhole_classification',status:'passed'});
}
const evidence={status:'passed',scope:'actual Worker code in VM, scripted socket, manual clock',source_sha256:createHash('sha256').update(source).digest('hex'),cases:results};await writeFile(new URL('../evidence/v13.1/row-delta-protocol-'+codec+'.json',import.meta.url),JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
