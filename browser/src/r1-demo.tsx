import {StrictMode,useEffect,useLayoutEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,useConnectionStatus,useLiveQuery,useLiveQueryViewport} from './product-provider';
const mounted:Array<unknown>=[],sink:Array<unknown>=[];
let provider:BrowserProductProvider;
const query={select:['id','quantity'] as const,where:[] as const,orderBy:[{field:'amount',direction:'asc'}] as const};
function App(){const connection=useConnectionStatus(),whole=useLiveQuery('products',query),viewport=useLiveQueryViewport('products');
 useEffect(()=>{const generation=viewport.viewport.replace({query,window:{firstRow:0,lastRow:1},sink:{setRowCount(count){sink.push({count});},setRowData(rows){sink.push({rows});}}});return()=>generation.release();},[viewport.viewport]);
 useLayoutEffect(()=>{mounted.push({connection,whole,viewport:{status:viewport.status,totalRows:viewport.totalRows,version:viewport.version}});},[connection,whole,viewport.status,viewport.totalRows,viewport.version]);return <output>{whole.status}:{viewport.status}</output>;}
const root=createRoot(document.getElementById('root')!);
(globalThis as any).r1={start(url:string,token:string){provider=new BrowserProductProvider({mode:'remote',url,token});root.render(<StrictMode><ProductProvider provider={provider}><App/></ProductProvider></StrictMode>);},provider:()=>provider,observe:()=>({mounted,sink}),dispose(){root.unmount();provider.dispose();}};
