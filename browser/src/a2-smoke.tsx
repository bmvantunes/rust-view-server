import React,{useEffect,useLayoutEffect,useMemo,useState} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,createTopicHooks} from './product-provider';
import {catalog} from './generated/topics';
const hooks=createTopicHooks(catalog);
const latest:Record<string,unknown>={},windows:Record<string,unknown>={},counts:Record<string,number>={},mounts:Record<string,number>={};
let root:ReturnType<typeof createRoot>,provider:BrowserProductProvider;
let switchChoices:(groupChoice:boolean,selectChoice:boolean)=>void;
function Dataset_grouped({groupChoice,selectChoice}:{groupChoice:boolean;selectChoice:boolean}){
 const query=useMemo(()=>{const group=groupChoice?'symbol':'hedged';return {groupBy:[group],aggregates:{total:{aggFunc:'sum',field:'risk'},mean:{aggFunc:'avg',field:'risk'}},orderBy:[]} as const;},[groupChoice]);
 const whole=hooks.useLiveQuery('positions',query),view=hooks.useLiveQueryViewport('positions');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['grouped']=(mounts['grouped']??0)+1;},[]);
 useLayoutEffect(()=>{latest['grouped']={whole,helper,groupChoice,selectChoice};},[whole,helper,groupChoice,selectChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){counts['grouped']=count;},setRowData(rows){windows['grouped']={rows,choice:groupChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="grouped">{whole.rows.map(row=><output key={row.rowId}>{(typeof row.symbol==='string'?row.symbol.toUpperCase():row.hedged===undefined?'absent':String(row.hedged))+':'+row.total.toFixed(2)+':'+row.mean.toFixed(2)}</output>)}</section>;
}
function Dataset_selected({groupChoice,selectChoice}:{groupChoice:boolean;selectChoice:boolean}){
 const query=useMemo(()=>{const select=selectChoice?['symbol'] as const:['quantity'] as const;return {select,orderBy:[{field:'positionId',direction:'asc'}]} as const;},[selectChoice]);
 const whole=hooks.useLiveQuery('positions',query),view=hooks.useLiveQueryViewport('positions');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['selected']=(mounts['selected']??0)+1;},[]);
 useLayoutEffect(()=>{latest['selected']={whole,helper,groupChoice,selectChoice};},[whole,helper,groupChoice,selectChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){counts['selected']=count;},setRowData(rows){windows['selected']={rows,choice:selectChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="selected">{whole.rows.map(row=><output key={row.rowId}>{typeof row.symbol==='string'?row.symbol.toUpperCase():typeof row.quantity==='string'?row.quantity.toUpperCase():'absent'}</output>)}</section>;
}
function Dataset_presence({groupChoice,selectChoice}:{groupChoice:boolean;selectChoice:boolean}){
 const query=useMemo(()=>{const field=groupChoice?'note':'customer';return {groupBy:['open',field],aggregates:{count:{aggFunc:'count'}},orderBy:[]} as const;},[groupChoice]);
 const whole=hooks.useLiveQuery('orders',query),view=hooks.useLiveQueryViewport('orders');
 const helper=view.useWholeResult(query);
 useEffect(()=>{mounts['presence']=(mounts['presence']??0)+1;},[]);
 useLayoutEffect(()=>{latest['presence']={whole,helper,groupChoice,selectChoice};},[whole,helper,groupChoice,selectChoice]);
 useEffect(()=>{const generation=view.viewport.replace({query,window:{firstRow:0,lastRow:9},sink:{setRowCount(count){counts['presence']=count;},setRowData(rows){windows['presence']={rows,choice:groupChoice};}}});return()=>generation.release();},[query,view.viewport]);
 return <section data-name="presence">{whole.rows.map(row=><output key={row.rowId}>{(typeof row.customer==='string'?row.customer.toUpperCase():row.note===null?'null':row.note===undefined?'missing':row.note.toUpperCase())+':'+row.count.toUpperCase()}</output>)}</section>;
}
function start(url:string,token:string){
 provider=new BrowserProductProvider({mode:'remote',url,token,catalog:{orders:catalog.orders,positions:catalog.positions},subscriptions:32});
 function App(){const[choices,setChoices]=useState({groupChoice:false,selectChoice:false});switchChoices=(groupChoice,selectChoice)=>setChoices({groupChoice,selectChoice});return <><Dataset_grouped {...choices}/><Dataset_selected {...choices}/><Dataset_presence {...choices}/></>;}
 root=createRoot(document.getElementById('root')!);root.render(<ProductProvider provider={provider}><App/></ProductProvider>);
}
Object.assign(window,{a2Smoke:{start,choose:(group:boolean,select:boolean)=>switchChoices(group,select),observe:()=>({latest,windows,counts,mounts,diagnostics:provider.connectionDiagnostics}),dispose:()=>{root.unmount();provider.dispose();}}});
