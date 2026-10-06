import React,{useEffect,useLayoutEffect,useMemo,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,createTopicHooks} from './product-provider';
import {catalog} from './generated/topics';
import {catalog as optionalCatalog} from '../../examples/grouped/browser/src/generated/topics';
const hooks=createTopicHooks(catalog),optionalHooks=createTopicHooks(optionalCatalog);
const latest:Record<string,unknown>={},windows:Record<string,unknown>={},mounts:Record<string,number>={};
let root:ReturnType<typeof createRoot>,provider:BrowserProductProvider;
let switchChoices:(field:boolean,operation:boolean)=>void;
function show(value:number|string|null){return value===null?'null':typeof value==='number'?value.toFixed(2):value.toUpperCase();}
function Dataset_positions({fieldChoice,operationChoice}:{fieldChoice:boolean;operationChoice:boolean}){
 const query=useMemo(()=>{const field=fieldChoice?'risk':'quantity';return {groupBy:['hedged'],aggregates:{total:{aggFunc:'sum',field},mean:{aggFunc:'avg',field}},orderBy:[]} as const;},[fieldChoice,operationChoice]);
 const whole=hooks.useLiveQuery('positions',query),view=hooks.useLiveQueryViewport('positions');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['positions']=(mounts['positions']??0)+1;},[]);
 useLayoutEffect(()=>{latest['positions']={whole,helper,fieldChoice,operationChoice};},[whole,helper,fieldChoice,operationChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){windows['positions']={count,rows:{}};},setRowData(rows){windows['positions']={rows,fieldChoice,operationChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="positions">{whole.rows.map(row=><output key={row.rowId}>{show(row.total)+':'+show(row.mean)}</output>)}</section>;
}
function Dataset_orders({fieldChoice,operationChoice}:{fieldChoice:boolean;operationChoice:boolean}){
 const query=useMemo(()=>{const field=fieldChoice?'note':'customer',aggFunc=operationChoice?'avg':'sum';return {groupBy:['open'],aggregates:{value:{aggFunc,field:'units'},lowest:{aggFunc:'min',field}},orderBy:[]} as const;},[fieldChoice,operationChoice]);
 const whole=hooks.useLiveQuery('orders',query),view=hooks.useLiveQueryViewport('orders');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['orders']=(mounts['orders']??0)+1;},[]);
 useLayoutEffect(()=>{latest['orders']={whole,helper,fieldChoice,operationChoice};},[whole,helper,fieldChoice,operationChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){windows['orders']={count,rows:{}};},setRowData(rows){windows['orders']={rows,fieldChoice,operationChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="orders">{whole.rows.map(row=><output key={row.rowId}>{show(row.value)+':'+show(row.lowest)}</output>)}</section>;
}
function Dataset_grouped_fixture({fieldChoice,operationChoice}:{fieldChoice:boolean;operationChoice:boolean}){
 const query=useMemo(()=>{const field=fieldChoice?'decimal':'number';return {groupBy:['group'],aggregates:{total:{aggFunc:'sum',field},mean:{aggFunc:'avg',field},lowest:{aggFunc:'min',field},highest:{aggFunc:'max',field}},orderBy:[{field:'group',direction:'asc'}]} as const;},[fieldChoice,operationChoice]);
 const whole=optionalHooks.useLiveQuery('grouped_fixture',query),view=optionalHooks.useLiveQueryViewport('grouped_fixture');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['grouped_fixture']=(mounts['grouped_fixture']??0)+1;},[]);
 useLayoutEffect(()=>{latest['grouped_fixture']={whole,helper,fieldChoice,operationChoice};},[whole,helper,fieldChoice,operationChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){windows['grouped_fixture']={count,rows:{}};},setRowData(rows){windows['grouped_fixture']={rows,fieldChoice,operationChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="grouped_fixture">{whole.rows.map(row=><output key={row.rowId}>{show(row.total)+':'+show(row.mean)+':'+show(row.lowest)+':'+show(row.highest)}</output>)}</section>;
}
function start(url:string,token:string){
 provider=new BrowserProductProvider({mode:'remote',url,token,catalog:{orders:catalog.orders,positions:catalog.positions,...optionalCatalog},subscriptions:32});
 function App(){const[choices,setChoices]=useState({fieldChoice:false,operationChoice:false});switchChoices=(fieldChoice,operationChoice)=>setChoices({fieldChoice,operationChoice});return <><Dataset_positions {...choices}/><Dataset_orders {...choices}/><Dataset_grouped_fixture {...choices}/></>;}
 root=createRoot(document.getElementById('root')!);root.render(<ProductProvider provider={provider}><App/></ProductProvider>);
}
Object.assign(window,{a1Smoke:{start,choose:(field:boolean,operation:boolean)=>switchChoices(field,operation),observe:()=>({latest,windows,mounts,diagnostics:provider.connectionDiagnostics}),dispose:()=>{root.unmount();provider.dispose();}}});
