import {reconstruct} from './row-delta.mjs';
import {encode,decodeNative,adapt} from '../../experiments/v131/js/msgpack.mjs';
import {initializeAdmission,admitEnvelope} from './request-admission';
const codec='msgpack';
import type { ProductResult } from './product-provider';
type Apply = { type:'apply';id:number;command:{command:string;subscription?:string};acquisition?:number;previousAcquisition?:number;traceparent:string };
type Options={url:string;token:string;subscriptions?:number};
type Pending={request:Apply;result?:ProductResult;timer:ReturnType<typeof setTimeout>};
const scope=self as unknown as {onmessage:((e:MessageEvent<Apply|{type:'configure';options:Options}|{type:'dispose'}>)=>void)|null;postMessage(v:unknown):void};
let socket:WebSocket|undefined, incarnation='',connection='',nonce='',done=false,configured=false;
let heartbeat:ReturnType<typeof setInterval>|undefined;
let last=performance.now();
const pending=new Map<number,Pending>();const acquisitions=new Map<string,number>();const bases=new Map<string,{acquisition:number;result:ProductResult}>();
const post=(v:unknown)=>{const t=performance.now();scope.postMessage(v);const ns=Math.round((performance.now()-t)*1e6);scope.postMessage({type:'v13_metrics',postCallNs:ns,workerTimeOrigin:performance.timeOrigin,workerEndNs:Math.round(performance.now()*1e6)});};
function fatal(message:string):void{if(done)return;done=true;for(const p of pending.values())clearTimeout(p.timer);pending.clear();acquisitions.clear();bases.clear();clearInterval(heartbeat);socket?.close();post({type:'fatal',error:message+'; pending completion uncertain'});}
const integer=(v:unknown):v is number=>typeof v==='number'&&Number.isSafeInteger(v)&&v>=0;
function record(v:unknown):v is Record<string,unknown>{return typeof v==='object'&&v!==null&&!Array.isArray(v);}
function send(v:unknown):void{if(!socket||socket.readyState!==WebSocket.OPEN)throw Error('remote socket unavailable');const text=encode(v,codec);const bytes=text.byteLength;if(bytes>4194304||socket.bufferedAmount+bytes>8388608)throw Error('remote send budget exceeded');socket.send(text);}
function envelope(v:Record<string,unknown>):Record<string,unknown>{return {...v,v:14,incarnation,connection,nonce};}
scope.onmessage=async e=>{
 const m=e.data;if(done)return;if(m.type==='dispose'){fatal('provider disposed');return;}
 if(m.type==='configure'){
  if(configured){fatal('duplicate configuration');return;}configured=true;
  const url=new URL(m.options.url);if(url.protocol!=='ws:'||url.hostname!=='127.0.0.1'||url.pathname!=='/v14'||url.search||url.username||url.password){fatal('remote mode requires an explicit loopback /v14 URL');return;}
  nonce=Array.from(crypto.getRandomValues(new Uint8Array(16)),b=>b.toString(16).padStart(2,'0')).join('');
  try{await initializeAdmission();}catch(e){fatal(String(e));return;}if(done)return;
  socket=new WebSocket(url,'view-server.v14.msgpack');socket.binaryType='arraybuffer';socket.onopen=()=>{try{send({type:'hello',v:14,token:m.options.token,nonce});}catch(e){fatal(String(e));}};
  socket.onerror=()=>fatal('remote connection error');socket.onclose=e=>fatal('remote connection closed: '+e.reason+'; pending completion uncertain; create a new provider for a fresh lifetime');
  heartbeat=setInterval(()=>{if(performance.now()-last>10000){fatal('remote heartbeat/readiness timeout');return;}if(incarnation)try{send(envelope({type:'ping'}));}catch(e){fatal(String(e));}},2000);
  socket.onmessage=e=>{
   if(done)return;if(!(e.data instanceof ArrayBuffer)){fatal('binary frame required');return;}
   if(e.data.byteLength>4*1024*1024){fatal('remote frame budget');return;}
   let v:unknown;let decodeNs=0,adaptNs=0;try{const t=performance.now();const native=decodeNative(new Uint8Array(e.data),codec);decodeNs=Math.round((performance.now()-t)*1e6);const a=performance.now();v=adapt(native,codec);adaptNs=Math.round((performance.now()-a)*1e6);}catch{fatal('malformed binary frame');return;}
   if(!record(v)||v.v!==14){fatal('incompatible binary envelope version');return;}
   if(!record(v)||v.v!==14||v.nonce!==nonce||typeof v.incarnation!=='string'||typeof v.connection!=='string'||!/^[0-9a-f]{32}$/.test(v.incarnation)||!/^\d{1,20}$/.test(v.connection))return;
   if(v.type==='ready'){
    if(incarnation||!Array.isArray(v.coverage)||v.coverage.length===0||!v.coverage.every(integer))return;
    if(!record(v.limits)||!integer(v.limits.per_client)||!integer(v.limits.total)||(m.options.subscriptions??16)>v.limits.per_client){fatal('remote subscription capability unavailable');return;}
    incarnation=v.incarnation;connection=v.connection;last=performance.now();post({type:'ready',serverIncarnation:incarnation});return;
   }
   if(v.incarnation!==incarnation||v.connection!==connection||!incarnation)return;
   if(v.type==='pong'){last=performance.now();return;}
   if(v.type==='result'){
    if(typeof v.subscription!=='string'||!integer(v.acquisition)||!record(v.result)||v.result.subscription!==v.subscription){fatal('malformed result identity');return;}
    if(v.id!==undefined){if(!integer(v.id)){fatal('invalid result request');return;}const p=pending.get(v.id);if(!p||p.result||v.traceparent!==p.request.traceparent||v.subscription!==p.request.command.subscription||v.acquisition!==p.request.acquisition){fatal('unexpected command result');return;}}
    else if(acquisitions.get(v.subscription)!==v.acquisition)return;
    const prior=bases.get(v.subscription);
    const applyStarted=performance.now();const batch=v.result;let reconstructed:ProductResult;try{reconstructed=reconstruct(prior?.acquisition===v.acquisition?prior.result:undefined,v.result);}catch(e){fatal(String(e)+'; acquire a new provider snapshot');return;}
    bases.set(v.subscription,{acquisition:v.acquisition,result:reconstructed});v.result=reconstructed;
    if(typeof v.source_sequence!=='string'||!/^\d{1,20}$/.test(v.source_sequence)){fatal('invalid source cut');return;}
    reconstructed.remote={sourceSequence:v.source_sequence,incarnation,connection,acquisition:v.acquisition,requestId:integer(v.id)?v.id:undefined,batchKind:batch.kind,operationCount:Array.isArray(batch.operations)?batch.operations.length:0,payloadRows:batch.kind==='snapshot'?reconstructed.rows.length:Array.isArray(batch.operations)?batch.operations.filter((o:unknown)=>record(o)&&o.row!==undefined).length:0,applyNs:Math.round((performance.now()-applyStarted)*1e6),receivedNs:Math.round(performance.now()*1e6),encodedBytes:e.data.byteLength,decodeNs,adaptNs,workerTimeOrigin:performance.timeOrigin,workerPostNs:Math.round(performance.now()*1e6)} as ProductResult['remote'];
    if(v.id!==undefined){
     if(!integer(v.id))return;const p=pending.get(v.id);if(!p||p.result||v.traceparent!==p.request.traceparent||v.subscription!==p.request.command.subscription||v.acquisition!==p.request.acquisition)return;
     p.result=reconstructed;
    }else if(acquisitions.get(v.subscription)===v.acquisition){post({type:'live',results:{[v.subscription]:reconstructed},acquisitions:{[v.subscription]:v.acquisition}});}
    return;
   }
   if(!integer(v.id))return;const p=pending.get(v.id);if(!p||v.traceparent!==p.request.traceparent)return;
   const sub=p.request.command.subscription;
   if(v.type==='request_error'){
    if(typeof v.error!=='string'||(v.currentAcquisition!==null&&v.currentAcquisition!==undefined&&!integer(v.currentAcquisition)))return;
    pending.delete(v.id);clearTimeout(p.timer);post({type:'request_error',id:v.id,error:v.error,currentAcquisition:v.currentAcquisition??undefined,traceparent:v.traceparent});return;
   }
   if(v.type!=='ack'||v.result_count!==(p.request.command.command==='close'?0:1)||((v.result_count===1)!==!!p.result))return;
   pending.delete(v.id);clearTimeout(p.timer);
   if(sub){if(p.request.command.command==='close'){if(acquisitions.get(sub)===p.request.acquisition){acquisitions.delete(sub);bases.delete(sub);}}else if(p.request.acquisition!==undefined&&p.request.acquisition>=(acquisitions.get(sub)??0))acquisitions.set(sub,p.request.acquisition);}
   post({type:'ack',id:v.id,traceparent:v.traceparent,results:p.result&&sub?{[sub]:p.result}:{},acquisitions:sub?{[sub]:p.request.acquisition}:{}});
  };return;
 }
 if(pending.size>=64){fatal('remote commands in flight exceeded');return;}
 if(!incarnation){fatal('remote command before readiness');return;}
 const timer=setTimeout(()=>fatal('remote request timeout; completion uncertain'),10000);pending.set(m.id,{request:m,timer});
 try{const command=structuredClone(m.command) as Apply['command'] & {query?:{projection?:string[]}};const projection=command.query?.projection;if(command.query)delete command.query.projection;send(admitEnvelope(envelope({type:'command',request:{projection,id:m.id,acquisition:m.acquisition??0,previous_acquisition:m.previousAcquisition??null,traceparent:m.traceparent,command}})));}catch(e){fatal(`remote send failed; completion uncertain: ${String(e)}`);}
};
