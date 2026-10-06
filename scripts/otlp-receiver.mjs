// Bounded local qualification sink, not shipped as a production Collector.
import http from 'node:http';
import {createRequire} from 'node:module';
import {resolve,join} from 'node:path';
import {mkdir,writeFile} from 'node:fs/promises';
const require=createRequire(resolve(import.meta.dirname,'../experiments/v131/package.json'));
const protobuf=require('protobufjs');
export async function receiver(directory){
 const base=resolve(import.meta.dirname,'../fixtures/otel-proto'),root=new protobuf.Root();root.resolvePath=(_,target)=>join(base,target);
 await root.load(['opentelemetry/proto/collector/trace/v1/trace_service.proto','opentelemetry/proto/collector/metrics/v1/metrics_service.proto']);
 const types={traces:root.lookupType('opentelemetry.proto.collector.trace.v1.ExportTraceServiceRequest'),metrics:root.lookupType('opentelemetry.proto.collector.metrics.v1.ExportMetricsServiceRequest')};
 await mkdir(directory,{recursive:true});const captures=[];let active=0,peak=0,bytes=0,mode='normal';
 const server=http.createServer({maxHeaderSize:8192,requestTimeout:3000},async(req,res)=>{
  const origin=req.headers.origin;if(origin?.startsWith('http://127.0.0.1:'))res.setHeader('access-control-allow-origin',origin);
  res.setHeader('access-control-allow-headers','content-type');res.setHeader('access-control-allow-methods','POST, OPTIONS');
  if(req.method==='OPTIONS'){res.writeHead(204).end();return;}
  const type=req.url==='/v1/traces'?'traces':req.url==='/v1/metrics'?'metrics':undefined;
  if(!type||req.method!=='POST'||active>=8||captures.length>=2048){res.writeHead(503).end();return;}
  active++;peak=Math.max(peak,active);let chunks=[],size=0;
  try{for await(const c of req){size+=c.length;if(size>1048576)throw Error('body bound');chunks.push(c);}const body=Buffer.concat(chunks);bytes+=body.length;const decoded=types[type].toObject(types[type].decode(body),{longs:String,bytes:String,enums:String});const n=captures.length;captures.push({type,bytes:body.length,received:Date.now(),decoded});await writeFile(join(directory,`${n}-${type}.pb`),body);if(mode==='slow')await new Promise(r=>setTimeout(r,2500));res.writeHead(mode==='unavailable'?503:200,{'content-type':'application/x-protobuf'}).end();}catch{res.writeHead(400).end();}finally{active--;}
 });await new Promise(r=>server.listen(0,'127.0.0.1',r));
 return {url:`http://127.0.0.1:${server.address().port}`,captures,get peak(){return peak;},get bytes(){return bytes;},set mode(v){mode=v;},async close(){await writeFile(join(directory,'decoded.json'),JSON.stringify(captures,null,2));await new Promise(r=>server.close(r));server.closeAllConnections();}};
}
export function spans(captures){return captures.filter(c=>c.type==='traces').flatMap(c=>(c.decoded.resourceSpans??[]).flatMap(r=>(r.scopeSpans??[]).flatMap(s=>(s.spans??[]).map(span=>({...span,resource:Object.fromEntries((r.resource.attributes??[]).map(a=>[a.key,a.value.stringValue]))})))));}
