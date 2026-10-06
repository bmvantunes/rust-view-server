import React,{useEffect,useLayoutEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,createTopicHooks} from './product-provider';
import {catalog} from '../../examples/symbol-collisions/browser/src/generated/topics';
const hooks=createTopicHooks(catalog);
type Topic=keyof typeof catalog;
const query={select:['quantity'],where:{op:'ge',field:'risk',value:0},orderBy:[{field:'risk',direction:'desc'}]} as const;
const latest:Partial<Record<Topic,unknown>>={},windows:Partial<Record<Topic,{rows?:unknown;keys?:unknown;count?:number}>>={};
let provider:BrowserProductProvider|undefined,root:ReturnType<typeof createRoot>|undefined;
function Dataset({topic}:{topic:Topic}){
 const whole=hooks.useLiveQuery(topic,query),view=hooks.useLiveQueryViewport(topic);
 useLayoutEffect(()=>{latest[topic]=whole;},[whole,topic]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:1},sink:{setRowCount(count){windows[topic]={...windows[topic],count};},setRowData(rows,keys){windows[topic]={...windows[topic],rows,keys};}}});return()=>generation.release();},[topic,view.viewport]);
 return <section data-topic={topic}><output>{whole.status}:{view.status}</output><pre>{JSON.stringify(whole.rows)}</pre></section>;
}
Object.assign(window,{symbolSmoke:{start(url:string,token:string){provider=new BrowserProductProvider({mode:'remote',url,token,catalog,subscriptions:32});root=createRoot(document.getElementById('root')!);root.render(<ProductProvider provider={provider}>{(Object.keys(catalog) as Topic[]).map(topic=><Dataset key={topic} topic={topic}/>)}</ProductProvider>);},observe:()=>({latest,windows}),dispose(){root?.unmount();provider?.dispose();}}});
