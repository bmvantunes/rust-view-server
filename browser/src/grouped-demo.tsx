import React,{useEffect,useLayoutEffect,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,createTopicHooks,useViewServerHealthSummary} from './product-provider';
import {createBrowserTelemetry} from './browser-telemetry';
import type {BrowserCatalog,TopicQuery,Schema} from './topic-schema';
const helpers:Record<string,unknown>={},helperObservations:unknown[]=[];
const latest:Record<string,unknown>={},windows:Record<string,unknown>={},observations:unknown[]=[];
let root:ReturnType<typeof createRoot>|undefined,provider:BrowserProductProvider|undefined,telemetry:ReturnType<typeof createBrowserTelemetry>|undefined;
let setMounted:((names:string[])=>void)|undefined;
let mountedNames:string[]=[];
const controls:Record<string,{window:(offset:number,limit:number)=>void;query:(q:TopicQuery<Schema>)=>void}>={};
function start(url:string,token:string,catalog:BrowserCatalog,definitions:Record<string,{topic:string;query:TopicQuery<Schema>}>,endpoint?:string,strict=false,fieldPatches=false,schemaEvolution=false){
 const hooks=createTopicHooks(catalog);telemetry=endpoint?createBrowserTelemetry({endpoint:endpoint+'/v1/traces',sampleRatio:1,deployment:'grouped-qualification'}):undefined;
 provider=new BrowserProductProvider({mode:'remote',url,token,catalog,subscriptions:32,fieldPatches,schemaEvolution},telemetry);
 function Dataset({name}:{name:string}){const d=definitions[name];const[q,setQuery]=useState(d.query);const whole=hooks.useLiveQuery(d.topic,q),view=hooks.useLiveQueryViewport(d.topic);const helper=view.useWholeResult(q);
 useLayoutEffect(()=>{helpers[name]=helper;helperObservations.push({name,at:performance.now(),helper});},[helper.rows,helper.status,helper.version]);
 useLayoutEffect(()=>{const span=whole.observationTraceContext?telemetry?.start('dom_observation',whole.observationTraceContext):undefined;latest[name]=whole;observations.push({name,at:performance.now(),timeOrigin:performance.timeOrigin,whole});span?.end();},[whole.rows,whole.status,whole.version]);
 useEffect(()=>{const gen=view.viewport.replace({query:q,window:{firstRow:0,lastRow:1},sink:{setRowCount(count){windows[name]={...(windows[name] as object??{}),count};},setRowData(rows,keys){windows[name]={...(windows[name] as object??{}),rows,keys};}}});controls[name]={query:setQuery,window:(offset,limit)=>gen.setWindow({firstRow:offset,lastRow:offset+limit-1})};return()=>gen.release();},[q,view.viewport]);
 return <section data-name={name}><output>{whole.status}:{view.status}</output><pre>{JSON.stringify(whole.rows)}</pre></section>;}
 function App(){const[names,setNames]=useState(Object.keys(definitions));setMounted=setNames;mountedNames=names;const health=useViewServerHealthSummary();useLayoutEffect(()=>{latest.health=health;},[health]);return <>{names.map(name=><Dataset key={name} name={name}/>)}</>}
 root=createRoot(document.getElementById('root')!);const content=<ProductProvider provider={provider}><App/></ProductProvider>;root.render(strict?<React.StrictMode>{content}</React.StrictMode>:content);
}
Object.assign(window,{groupedDemo:{start,unmount:(name:string)=>setMounted?.(mountedNames.filter(n=>n!==name)),observe:()=>({latest,helpers,helperObservations,windows,observations,diagnostics:provider?.connectionDiagnostics,admission:provider?.admission}),query:(name:string,q:TopicQuery<Schema>)=>controls[name]?.query(q),window:(name:string,offset:number,limit:number)=>controls[name]?.window(offset,limit),provider:()=>provider,dispose:async()=>{root?.unmount();provider?.dispose();await telemetry?.shutdown();}}});
// Qualification-only peer proving negotiation against the same live service.
import {encodeGeneric,decodeGeneric} from '../../experiments/v131/js/msgpack.mjs';
function probeRecord(v:unknown):v is Record<string,unknown>{return typeof v==='object'&&v!==null&&!Array.isArray(v);}
Object.assign(window,{groupedCapabilityProbe:(url:string,token:string,catalog:BrowserCatalog)=>new Promise<unknown[]>((resolve,reject)=>{
 const ws=new WebSocket(url,'view-server.v15.msgpack');ws.binaryType='arraybuffer';const received:unknown[]=[];const nonce='0123456789abcdef0123456789abcdef',traceparent='00-11111111111111111111111111111111-1111111111111111-01';let ready:Record<string,unknown>;const timer=setTimeout(()=>{ws.close();reject(Error('capability probe timeout'));},10000);
 const send=(v:unknown)=>ws.send(encodeGeneric(v));ws.onopen=()=>send({type:'hello',v:15,token,nonce,catalog:Object.fromEntries(Object.entries(catalog).map(([t,s])=>[t,s.fingerprint])),capabilities:['generic_schemas_v1']});ws.onerror=()=>{clearTimeout(timer);reject(Error('capability socket'));};
 ws.onmessage=e=>{const v=decodeGeneric(new Uint8Array(e.data));if(!probeRecord(v)){clearTimeout(timer);ws.close();reject(Error('capability frame'));return;}received.push(v);const query={topic:'orders',schema:catalog.orders.fingerprint,offset:0,limit:2};const command=(id:number,query:unknown)=>send({type:'command',v:15,nonce,incarnation:ready.incarnation,connection:ready.connection,request:{id,acquisition:id,previous_acquisition:id===1?null:1,traceparent,command:{command:id===1?'open':'change_query',subscription:'probe',query}}});
 if(v.type==='ready'){ready=v;command(1,{...query,select:['customer'],order_by:[]});}
 if(v.type==='ack'&&v.id===1)command(2,{...query,group_by:['customer'],aggregates:{n:{aggFunc:'count'}},order_by:[]});
 if(v.type==='request_error'&&v.id===2){clearTimeout(timer);ws.close();resolve(received);}
 };
})});
