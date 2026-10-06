// Diagnostic harness only: ordinary Worker/provider; observation is React commit, not paint.
import {createElement,useLayoutEffect} from 'react';
import {createRoot} from 'react-dom/client';
import {BrowserProductProvider,ProductProvider,useProductLiveQuery} from './src/product-provider';
let provider:BrowserProductProvider;let root:ReturnType<typeof createRoot>;
const samples:any[]=[];const query={where_expr:{op:'true'},direction:'ascending',offset:0,limit:1} as const;
function View(){const view=useProductLiveQuery('latency',query);const value=view.data?.rows[0]?.label;
 useLayoutEffect(()=>{if(view.data)samples.push({label:view.data.rows[0]?.label,at:performance.now(),result:view.data,dom:document.getElementById('latency-value')?.textContent});},[view.data]);
 return createElement('output',{id:'latency-value'},value?.state==='value'?value.value:view.error?'ERROR:'+view.error.message:'loading');}
export async function mount(url:string,token:string){provider=new BrowserProductProvider({mode:'remote',url,token,subscriptions:4});await provider.ready;const div=document.createElement('div');document.body.appendChild(div);root=createRoot(div);root.render(createElement(ProductProvider,{provider,children:createElement(View)}));(window as any).f1={samples,admission:()=>provider.admission,close:()=>{root.unmount();provider.dispose();}};}
