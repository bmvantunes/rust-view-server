// Actual remote Worker, deterministic fake socket and manual time. No native/browser claim.
import {readFile,writeFile} from 'node:fs/promises';
import {stripTypeScriptTypes} from 'node:module';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {encode,decode,decodeNative,adapt,prepare,encodePrepared} from '../experiments/v13/js/codec.mjs';
import assert from 'node:assert/strict';
const root=process.env.V13_CANDIDATE_ROOT;assert(root);const codec=process.env.V13_CODEC;const source=await readFile(root+'/browser/src/product.remote.worker.ts','utf8');
const code=stripTypeScriptTypes(source.replace(/^import \{encode,decodeNative,adapt\}[^\n]+\n/, '')).replace(/export \{\};?/g,'');
const results=[];
function setup(){
 let now=0,next=0,socket;const timers=new Map(),posts=[];
 const scope={postMessage:m=>{if(m.type!=='v13_metrics')posts.push(structuredClone(m));}};
 class Socket{static OPEN=1;readyState=1;bufferedAmount=0;sent=[];fail=false;constructor(){socket=this;}send(v){if(this.fail)throw Error('injected send failure');this.sent.push(codec==='json'?JSON.parse(v):decode(v,codec));}close(){this.closed=true;}}
 const context=vm.createContext({self:scope,WebSocket:Socket,URL,TextEncoder,ArrayBuffer,encode,decodeNative,adapt,crypto:webcrypto,Uint8Array,performance:{now:()=>now},setTimeout:(fn,ms)=>{timers.set(++next,{fn,at:now+ms});return next;},clearTimeout:id=>timers.delete(id),setInterval:(fn,ms)=>{timers.set(++next,{fn,at:now+ms,ms});return next;},clearInterval:id=>timers.delete(id)});vm.runInContext(code,context);
 const input=m=>scope.onmessage({data:m});input({type:'configure',options:{url:'ws://127.0.0.1:8080/'+(codec==='json'?'v12':'v13'),token:'x'.repeat(32)}});socket.onopen();
 const nonce=socket.sent[0].nonce,envelope={v:codec==='json'?1:13,nonce,incarnation:'a'.repeat(32),connection:'1'};
 const frame=m=>{const value={...envelope,...m};const b=codec==='json'?JSON.stringify(value):encode(value,codec);socket.onmessage({data:typeof b==='string'?b:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});};frame({type:'ready',coverage:[0],limits:{per_client:70,total:80}});
 const request={type:'apply',id:1,acquisition:1,traceparent:'00-'+ 'a'.repeat(32)+'-'+ 'b'.repeat(16)+'-01',command:{command:'open',subscription:'s'}};
 const result={type:'result',id:1,acquisition:1,traceparent:request.traceparent,subscription:'s',source_sequence:'1',result:{subscription:'s',query_generation:1,sequence:1,start_rank:0,version:1,total_rows:1,rows:[{id:'x',category:'a',quantity:'9223372036854775807',amount:{coefficient:'-1001',scale:2},label:{state:'missing'}}]}};
 const ack={type:'ack',id:1,traceparent:request.traceparent,result_count:1};
 const tick=ms=>{const end=now+ms;for(;;){let chosen;for(const [id,t] of timers)if(t.at<=end&&(!chosen||t.at<chosen[1].at))chosen=[id,t];if(!chosen)break;const[id,t]=chosen;now=t.at;timers.delete(id);if(t.ms)timers.set(id,{...t,at:now+t.ms});t.fn();}now=end;};
 return {socket,posts,input,frame,request,result,ack,tick};
}
for(const [name,modify] of Object.entries({wrong_incarnation:r=>({...r,incarnation:'b'.repeat(32)}),wrong_connection:r=>({...r,connection:'2'}),wrong_nonce:r=>({...r,nonce:'b'.repeat(32)}),wrong_acquisition:r=>({...r,acquisition:2}),wrong_subscription:r=>({...r,subscription:'x'}),wrong_trace:r=>({...r,traceparent:'bad'}),unsafe_integer:r=>({...r,result:{...r.result,total_rows:2**53}}),inexact_quantity:r=>({...r,result:{...r.result,rows:[{...r.result.rows[0],quantity:42}]}}),invalid_cut:r=>({...r,source_sequence:1})})){
 if(codec!=='json'&&['unsafe_integer','inexact_quantity','invalid_cut'].includes(name)){const s=setup();s.input(s.request);const bad=prepare({...s.result,v:13,nonce:s.socket.sent[0].nonce,incarnation:'a'.repeat(32),connection:'1'});if(name==='unsafe_integer')bad.result.total_rows=2**53;else if(name==='inexact_quantity')bad.result.rows[0].quantity=42;else bad.source_sequence=1;const b=encodePrepared(bad,codec);s.socket.onmessage({data:b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength)});assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);s.tick(10000);assert.equal(s.posts.filter(x=>x.type==='ack').length,0);results.push({name,status:'terminal malformed binary rejected'});continue;}
 const s=setup();s.input(s.request);s.frame(modify(s.result));s.frame(s.ack);assert.equal(s.posts.length,1,name);s.frame(s.result);s.frame(s.ack);assert.equal(s.posts.filter(x=>x.type==='ack').length,1);s.frame(s.ack);s.tick(9999);assert.equal(s.posts.filter(x=>x.type==='fatal').length,0);results.push({name,status:'passed'});
 const t=setup();t.input(t.request);t.frame(modify(t.result));t.frame(t.ack);t.tick(10000);assert.equal(t.posts.filter(x=>x.type==='fatal').length,1);assert.match(t.posts.at(-1).error,/uncertain/);t.frame(t.result);t.frame(t.ack);assert.equal(t.posts.filter(x=>x.type==='ack').length,0);results.push({name:name+'_timeout',status:'passed'});
}
for(const phase of ['before_result','between_result_ack','after_ack','close','dispose']){
 const s=setup();s.input(s.request);if(phase!=='before_result')s.frame(s.result);if(['after_ack','close','dispose'].includes(phase))s.frame(s.ack);
 if(phase==='close')s.input({...s.request,id:2,command:{command:'close',subscription:'s'}});
 if(phase==='dispose')s.input({type:'dispose'});else s.socket.onclose({reason:'test'});
 s.tick(20000);assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.equal(s.posts.filter(x=>x.type==='ack').length,['after_ack','close','dispose'].includes(phase)?1:0);results.push({name:'loss_'+phase,status:'passed'});
}
for(const mode of ['throw','buffer']){const s=setup();if(mode==='throw')s.socket.fail=true;else s.socket.bufferedAmount=131072;s.input(s.request);s.tick(20000);assert.equal(s.posts.filter(x=>x.type==='fatal').length,1);assert.match(s.posts.at(-1).error,/uncertain/);results.push({name:'send_'+mode,status:'passed'});}
const evidence={status:'passed',scope:'actual Worker code in VM, scripted socket, manual clock',source_sha256:createHash('sha256').update(source).digest('hex'),cases:results};await writeFile(new URL('../evidence/v13/protocol-'+codec+'.json',import.meta.url),JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
