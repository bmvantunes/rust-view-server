// Test/demo harness: native results only; no source mutation API in this page.
import {createElement, StrictMode, useEffect} from 'react';
import {createRoot, type Root} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,useProductLiveQuery,useLiveQuery,useLiveQueryViewport,type ProductQuery,type ProductResult} from './product-provider';
const query:ProductQuery={where_expr:{op:'true'},direction:'ascending',offset:0,limit:16};
const providers=new Map<string,BrowserProductProvider>();
const results:Record<string,ProductResult[]>={};
const errors:Record<string,string[]>={};
let root:Root|undefined;
const hookSamples:unknown[]=[];
const mounted:Record<string,{status:string;data?:ProductResult;error?:string}>={};
function Narrow({id,distinct}:{id:number;distinct:boolean}){
 const q:ProductQuery={where_expr:distinct?{op:'condition',args:{field:'category_equals',condition:['a','b','c'][id%3]}}:{op:'true'},direction:'ascending',offset:id%3,limit:Number((globalThis as any).v13Window??2)};
 const view=useProductLiveQuery('burst:'+id,q);
 useEffect(()=>{if(view.data)hookSamples.push({id,ns:Math.round(performance.now()*1e6),timeOrigin:performance.timeOrigin,result:view.data});mounted[String(id)]={status:view.error?'error':view.data?'ready':'loading',data:view.data,error:view.error?.message};if(view.data){(results['burst:'+id]??=[]).push(view.data);}},[view.data,view.error]);
 return createElement('output',{'data-burst':id},view.error?'ERROR:'+view.error.message:view.data?'ready':'loading');
}
function Burst({count,distinct}:{count:number;distinct:boolean}){return Array.from({length:count},(_,id)=>createElement(Narrow,{key:id,id,distinct}));}
function View({name}:{name:string}){const view=useLiveQuery('products',{select:['id','amount','quantity'] as const,where:[],orderBy:[{field:'amount',direction:'asc'}]});return createElement('output',{'data-testid':name},view.status==='error'?`ERROR:${view.message}`:view.status==='ready'?`${view.totalRows}|${view.rows.map(r=>r.id).join(',')}`:'loading');}
function ViewportView(){
 const {viewport,status,message}=useLiveQueryViewport('products');
 useEffect(()=>{const acquisition=viewport.replace({window:{firstRow:1,lastRow:1},query:{select:['id','quantity'] as const,where:[],orderBy:[{field:'amount',direction:'asc'}]},sink:{setRowCount(count){document.getElementById('root')!.dataset.total=String(count);},setRowData(rows){document.getElementById('root')!.dataset.window=JSON.stringify(rows);}}});return()=>acquisition.release();},[viewport]);
 return createElement('output',{'data-testid':'viewport'},status==='error'?`ERROR:${message}`:status);
}
function DeltaWhole(){
 const view=useLiveQuery('products',{select:['label','quantity'] as const,where:[],orderBy:[{field:'amount',direction:'asc'}]});
 return createElement('output',{'data-delta-whole':true},view.status==='ready'?JSON.stringify(view.rows):view.status==='error'?'ERROR:'+view.message:'loading');
}
function DeltaViewport(){
 const {viewport,status,message}=useLiveQueryViewport('products');
 useEffect(()=>{const acquired=viewport.replace({window:{firstRow:0,lastRow:99},query:{select:['label'] as const,where:[],orderBy:[{field:'amount',direction:'asc'}]},sink:{setRowCount(count){document.getElementById('root')!.dataset.deltaTotal=String(count);},setRowData(rows,keys){document.getElementById('root')!.dataset.deltaRows=JSON.stringify(rows);document.getElementById('root')!.dataset.deltaKeys=JSON.stringify(keys);}}});return()=>acquired.release();},[viewport]);
 return createElement('output',{'data-delta-viewport':true},status==='error'?'ERROR:'+message:status);
}
const callbackLog:string[]=[];
function CallbackView({name,action}:{name:string;action:string}){
 const {viewport,status,message}=useLiveQueryViewport('products');
 useEffect(()=>{
  let generation:ReturnType<typeof viewport.replace>;let fired=false;
  const input={window:{firstRow:0,lastRow:1},query:{select:['id','quantity','amount'] as const,where:[] as const,orderBy:[{field:'amount',direction:'asc'}] as const}};
  generation=viewport.replace({...input,sink:{setRowCount(){
   callbackLog.push('old-count');if(fired)return;fired=true;
   if(action==='replace')generation=viewport.replace({...input,window:{firstRow:1,lastRow:1},sink:{setRowCount(){callbackLog.push('new-count');},setRowData(){callbackLog.push('new-data');}}});
   else if(action==='dispose')providers.get(name)!.dispose();
   else generation.release();
   if(action==='invalidate-throw')throw Error('invalidated callback');
  },setRowData(){callbackLog.push('old-data');}}});
  return()=>generation.release();
 },[viewport,name,action]);
 return createElement('output',{'data-callback':action},status==='error'?'ERROR:'+message:status);
}
const api={
 results,errors,mounted,callbackLog,hookSamples,
 recovery(name:string){const p=providers.get(name)!;return {events:p.recoveryEvents,connection:p.connectionStatus,diagnostics:p.connectionDiagnostics};},
 mountDelta(name:string){root?.unmount();root=createRoot(document.getElementById('root')!);root.render(createElement(StrictMode,null,createElement(ProductProvider,{provider:providers.get(name)!,children:[createElement(DeltaWhole,{key:'whole'}),createElement(DeltaViewport,{key:'viewport'})]})));},
 mountCallback(name:string,action:string){root?.unmount();root=createRoot(document.getElementById('root')!);callbackLog.length=0;root.render(createElement(StrictMode,null,createElement(ProductProvider,{provider:providers.get(name)!,children:createElement(CallbackView,{name,action})})));},
 admission(name:string){return providers.get(name)!.admission;},
 async connect(name:string,url:string,token:string,subscriptions=16){const p=new BrowserProductProvider({mode:'remote',url,token,subscriptions});providers.set(name,p);await p.ready;},
 begin(name:string,url:string,token:string,subscriptions=70){providers.set(name,new BrowserProductProvider({mode:'remote',url,token,subscriptions}));},
 mountBurst(name:string,count:number,distinct=false){if(!root)root=createRoot(document.getElementById('root')!);root.render(createElement(StrictMode,null,createElement(ProductProvider,{provider:providers.get(name)!,children:createElement(Burst,{count,distinct})})));},
 watch(name:string,local:string,q:ProductQuery=query){const key=name+':'+local;results[key]=[];errors[key]=[];const listener=Object.assign((r:ProductResult)=>results[key].push(r),{onError:(e:Error)=>errors[key].push(e.message)});return providers.get(name)!.watch(local,q,listener);},
 async apply(name:string,command:unknown){return providers.get(name)!.apply(command);},
 async snapshot(name:string,local:string,q:ProductQuery=query){return providers.get(name)!.open(local,q);},
 mount(name:string){root?.unmount();root=createRoot(document.getElementById('root')!);root.render(createElement(StrictMode,null,createElement(ProductProvider,{provider:providers.get(name)!,children:createElement(View,{name})})));},
 mountViewport(name:string){root?.unmount();root=createRoot(document.getElementById('root')!);root.render(createElement(StrictMode,null,createElement(ProductProvider,{provider:providers.get(name)!,children:createElement(ViewportView)})));},
 unmount(){root?.unmount();root=undefined;},
 close(name:string){providers.get(name)?.dispose();providers.delete(name);},
};
declare global{interface Window{v12:typeof api}}
window.v12=api;
