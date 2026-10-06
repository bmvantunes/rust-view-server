import {StrictMode,useEffect,useLayoutEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,useConnectionStatus,useLiveQuery,useLiveQueryViewport,useViewServerHealthSummary,useSourceHealth} from './product-provider';
import {createBrowserTelemetry} from './browser-telemetry';
let provider:BrowserProductProvider,telemetry:ReturnType<typeof createBrowserTelemetry>|undefined;
const samples:unknown[]=[],deliveries:unknown[]=[],rows:unknown[]=[],query={select:['id','quantity'] as const,where:[] as const,orderBy:[{field:'amount',direction:'asc'}] as const};
function Badge(){const h=useViewServerHealthSummary(),source=useSourceHealth({topic:'products'});useEffect(()=>{samples.push({h,source});if(samples.length>1000)samples.shift();},[h,source]);return <pre className="health">{JSON.stringify({summary:h,source},null,2)}</pre>;}
function App(){const connection=useConnectionStatus(),whole=useLiveQuery('products',query),viewport=useLiveQueryViewport('products');
 useEffect(()=>{const handle=viewport.viewport.replace({query,window:{firstRow:0,lastRow:1},sink:{setRowCount(){},setRowData(value){rows.push(value);}}});return()=>handle.release();},[viewport.viewport]);
 useLayoutEffect(()=>{const span=whole.observationTraceContext?telemetry?.start('dom_observation',whole.observationTraceContext):undefined;deliveries.push({status:whole.status,viewport:viewport.status,whole,dom:document.querySelector('output')?.textContent});span?.end();},[whole,viewport.status]);
 return <main><h1>Runtime health</h1><p>Transport: {connection}</p><output>{whole.status}:{viewport.status}</output><Badge/><Badge/><Badge/></main>;}
const root=createRoot(document.getElementById('root')!);
(globalThis as any).healthDemo={start(url:string,token:string,endpoint?:string){telemetry=endpoint?createBrowserTelemetry({endpoint:endpoint+'/v1/traces',sampleRatio:1,deployment:'local-qualification'}):undefined;provider=new BrowserProductProvider({mode:'remote',url,token},telemetry);root.render(<StrictMode><ProductProvider provider={provider}><App/></ProductProvider></StrictMode>);},provider:()=>provider,observe:()=>({samples,deliveries,rows}),async dispose(){root.unmount();provider.dispose();await telemetry?.shutdown();}};

document.querySelector<HTMLFormElement>('#connect')?.addEventListener('submit',event=>{event.preventDefault();const form=event.currentTarget as HTMLFormElement,data=new FormData(form);(globalThis as any).healthDemo.start(String(data.get('url')),String(data.get('token')),String(data.get('endpoint')||'')||undefined);form.remove();});
