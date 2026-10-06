// Same complete parent-chain oracle as v1, additionally bound to received frame context.
import assert from 'node:assert/strict';import {spans} from './otlp-receiver.mjs';
const hex=x=>Buffer.from(x??'','base64').toString('hex');
const attrs=s=>Object.fromEntries((s.attributes??[]).map(a=>[a.key,Object.values(a.value)[0]]));
export function completeChains(captures,wire,phase,topic,kind){
 const ss=spans(captures),byId=new Map(ss.map(s=>[hex(s.spanId),s]));const result=[];
 for(const dom of ss){if(dom.name!=='dom_observation')continue;const chain=[dom],seen=new Set();
  while(chain.at(-1).parentSpanId&&byId.has(hex(chain.at(-1).parentSpanId))){const id=hex(chain.at(-1).parentSpanId);assert(!seen.has(id));seen.add(id);chain.push(byId.get(id));}
  const names=kind==='live'?['dom_observation','hook_delivery','worker_reconstruct','live_publish','source_apply']:['dom_observation','hook_delivery','worker_reconstruct','query_handle','worker_command','query_acquisition'];
  if(JSON.stringify(chain.map(s=>s.name))!==JSON.stringify(names))continue;
  assert.equal(new Set(chain.map(s=>s.traceId)).size,1);
  const native=chain[3];if(attrs(native).topic!==topic)continue;
  const frame=wire.find(f=>f.phase===phase&&f.value.result?.topic===topic&&f.value.trace_context===`00-${hex(native.traceId)}-${hex(native.spanId)}-01`);if(!frame)continue;
  assert.equal(native.resource['service.name'],'view-server');assert.equal(chain[2].resource['service.name'],'view-server-worker');assert.equal(dom.resource['service.name'],'view-server-browser');
  assert(chain.every(s=>(s.attributes??[]).length<=8&&(s.links??[]).length<=4));
  assert(!chain.at(-1).parentSpanId||/^0+$/.test(hex(chain.at(-1).parentSpanId)));
  result.push({phase,topic,kind,frameContext:frame.value.trace_context,frameReceivedAt:frame.at,instance:native.resource['service.instance.id'],chain:chain.map(s=>({name:s.name,traceId:hex(s.traceId),spanId:hex(s.spanId),parentSpanId:hex(s.parentSpanId),service:s.resource['service.name']}))});
 }
 return result;
}
