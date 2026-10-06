import {StrictMode, useEffect, useLayoutEffect, useRef} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider, ProductProvider, useLiveQuery, useLiveQueryViewport, type ProviderOptions, type ProductViewportGeneration} from './baseline-product-provider';
const OriginalWorker=globalThis.Worker;globalThis.Worker=new Proxy(OriginalWorker,{construct(Target,args){return new Target(new URL('./baseline.remote.worker.ts',import.meta.url),args[1]);}});
const ledger: Array<Record<string, unknown>> = [], sinkLedger: Array<Record<string, unknown>> = [];
let provider: BrowserProductProvider, mounted=0, windowGeneration: ProductViewportGeneration, initialNode: Element | null;
const raw = {select:['id','quantity','label'] as const,where:[{field:'category',type:'equals',filter:'a'}] as const,orderBy:[{field:'amount',direction:'asc'}] as const};
let whole: unknown, viewportState: unknown, sink: unknown, keys: unknown, rowCount=0;
function Badge({id}:{id:number}) { const status="connected"; useLayoutEffect(()=>{ledger.push({kind:'connection',id,status,at:performance.now()});},[status,id]); return <output data-badge={id}>{status}</output>; }
function Whole() {
 const view=useLiveQuery('products',raw), identity=useRef(crypto.randomUUID());
 useEffect(()=>{mounted++;return()=>{mounted--;};},[]);
 useLayoutEffect(()=>{whole=view;ledger.push({kind:'whole',identity:identity.current,...view,at:performance.now()});},[view.rows,view.totalRows,view.version,view.status]);
 return <output data-whole={view.status}>{JSON.stringify(view.rows)}</output>;
}
function Window() {
 const view=useLiveQueryViewport('products'), identity=useRef(crypto.randomUUID());
 useEffect(()=>{mounted++; windowGeneration=view.viewport.replace({query:raw,window:{firstRow:10,lastRow:19},sink:{setRowCount(count){rowCount=count;const space=document.getElementById('viewport-space');if(space)space.style.height=(count*15.5)+'px';},setRowData(rows,k){sink=rows;keys=k;const space=document.getElementById('viewport-space');if(space){space.replaceChildren(...Object.entries(rows).map(([rank,row])=>{const node=document.createElement('div');node.style.cssText=`position:absolute;top:${Number(rank)*15.5}px;height:15.5px;white-space:nowrap`;node.dataset.key=k[Number(rank)];node.textContent=JSON.stringify(row);return node;}));}sinkLedger.push({rows,keys:k,rowCount,at:performance.now()});}}});return()=>{mounted--;windowGeneration.release();};},[view.viewport]);
 useLayoutEffect(()=>{viewportState={status:view.status,totalRows:view.totalRows,version:view.version};ledger.push({kind:'viewport',identity:identity.current,...viewportState as object,at:performance.now()});},[view.status,view.totalRows,view.version]);
 return <><output data-viewport={view.status}>{view.status}</output><div id="scroll" style={{height:100,overflow:'auto'}}><div id="viewport-space" style={{position:'relative'}}/></div></>;
}
const root=createRoot(document.getElementById('root')!);
const api={
 start(options:ProviderOptions){if(provider)throw Error('demo provider already exists');provider=new BrowserProductProvider(options);root.render(<StrictMode><ProductProvider provider={provider}><Badge id={1}/><Badge id={2}/><Whole/><Window/></ProductProvider></StrictMode>);},
 observe(){return {whole,viewport:viewportState,sink,keys,rowCount,ledger,sinkLedger,events:[],admission:provider.admission,connection:"connected",mounted,sameNode:initialNode===document.getElementById('scroll'),scroll:document.getElementById('scroll')?.scrollTop};},
 pin(){initialNode=document.getElementById('scroll');document.getElementById('scroll')!.scrollTop=155;},
 window(firstRow:number,lastRow:number){windowGeneration.setWindow({firstRow,lastRow});},
 dispose(){root.unmount();provider.dispose();},
};
(globalThis as any).reconnect=api;
