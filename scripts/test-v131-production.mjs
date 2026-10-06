// This gate tests the installed production path, never an experimental peer selected by env.
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..');
const selection=JSON.parse(await readFile(root+'/PRODUCTION-CODEC.json','utf8'));
assert(['protobuf','msgpack'].includes(selection.codec));assert.equal(selection.json_application_fallback,false);
process.env.V13_CANDIDATE_ROOT=root;process.env.V13_CODEC=selection.codec;
const {setup}=await import('./v131-browser-support.mjs');const {encode,decode}=await import('../experiments/v131/js/'+selection.codec+'.mjs');
const worker=await readFile(root+'/browser/src/product.remote.worker.ts','utf8');
assert(worker.includes('/js/'+selection.codec+'.mjs'));assert(!worker.includes('/js/codec.mjs'));assert(!worker.includes('JSON.parse(e.data)'));assert(worker.includes("socket.binaryType='arraybuffer'"));
const server=await readFile(root+'/ingestion/src/bin/view_server.rs','utf8');assert(server.includes('Ok(Message::Binary(text))'));assert(!server.includes('Ok(Message::Text(text))'));
const cargo=await readFile(root+'/ingestion/Cargo.toml','utf8');assert(cargo.includes('default-features = false, features = ["'+selection.codec+'"]'));
const h=await setup('wire');
try{
 await h.server();await h.connect('provider');const snapshot=await h.page.evaluate(()=>window.v12.snapshot('provider','s',{where_expr:{op:'true'},direction:'ascending',offset:0,limit:4}));assert.deepEqual(snapshot.rows,[]);
 const hello=encode({v:14,type:'hello',token:h.token,nonce:'a'.repeat(32)});
 const observed=await h.page.evaluate(({url,protocol,hello})=>new Promise((resolve,reject)=>{
  const socket=new WebSocket(url,protocol);socket.binaryType='arraybuffer';let received;
  const timer=setTimeout(()=>{socket.close();reject(Error('text frame was not rejected'));},5000);
  socket.onopen=()=>socket.send(Uint8Array.from(hello));
  socket.onmessage=event=>{if(!(event.data instanceof ArrayBuffer)){reject(Error('non-binary application result'));return;}received=Array.from(new Uint8Array(event.data));socket.send('{"type":"ping","v":13}');};
  socket.onclose=()=>{clearTimeout(timer);resolve({received,textClosed:true});};socket.onerror=()=>{};
 }),{url:h.url,protocol:selection.subprotocol,hello:[...hello]});
 assert.equal(decode(Uint8Array.from(observed.received)).type,'ready');assert(observed.textClosed);
 const oldEndpoint=await h.page.evaluate(({url,protocol})=>new Promise(resolve=>{const socket=new WebSocket(url.replace('/v14','/v13'),protocol);socket.onopen=()=>{socket.close();resolve(false);};socket.onerror=()=>resolve(true);}),{url:h.url,protocol:selection.subprotocol});assert(oldEndpoint);
 // The healthy production provider is still usable after terminal peer rejection.
 await h.page.evaluate(()=>window.v12.apply('provider',{command:'change_window',subscription:'s',offset:0,limit:4}));await h.page.evaluate(()=>window.v12.close('provider'));await h.shutdown();
 assert(h.parsed().some(x=>x.state==='stopped'&&x.subscriptions===0&&x.shapes===0));
 await h.evidence({status:'passed',codec:selection.codec,productionRoot:root,applicationFramesBinary:true,textApplicationFrameRejected:true,oldEndpointRejected:true,healthyPeerSurvives:true,finalZeroSubscriptions:true});
}finally{await h.cleanup();}
