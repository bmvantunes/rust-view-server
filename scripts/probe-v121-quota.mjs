// Exported provider cold admission probe; deliberately no mounted/native claim.
import {readFile,writeFile} from 'node:fs/promises';
import {createHash,webcrypto} from 'node:crypto';
import vm from 'node:vm';
import {execFileSync} from 'node:child_process';
import {createRequire} from 'node:module';
import {resolve} from 'node:path';
const root=resolve(import.meta.dirname,'..');
const {transformWithOxc}=await import(createRequire(resolve(root,'browser/package.json')).resolve('vite'));
const version=process.argv.find(x=>x.startsWith('--baseline='))?.split('=')[1];
const source=version?execFileSync('unzip',['-p',resolve(root,`rust-differential-product-20260929-review-checkpoint-${version}.zip`),'browser/src/product-provider.tsx'],{encoding:'utf8'}):await readFile(resolve(root,'browser/src/product-provider.tsx'),'utf8');
let {code}=await transformWithOxc(source,'product-provider.tsx',{jsx:{runtime:'classic'}});
code=code.replace(/import[\s\S]*?from "react";/,'const createContext=()=>({});').replaceAll('import.meta.url','"file:///provider.js"').replace(/export /g,'');
code+='\nglobalThis.Provider=BrowserProductProvider;';
const outcomes=[];
for(const mode of (version==='v11'?['local']:['local','remote'])){
 const context=vm.createContext({URL,Map,Promise,Error,Object,Array,JSON,Number,Uint8Array,structuredClone,crypto:webcrypto,Worker:class{postMessage(){}terminate(){}}});vm.runInContext(code,context);
 const provider=new context.Provider({mode,url:'ws://127.0.0.1:9999/v12',token:'x'.repeat(32)});let admitted=0,error=null;
 for(let i=0;i<20;i++){try{provider.watch(`s${i}`,{where_expr:{op:'true'},direction:'ascending',offset:0,limit:1},()=>{});admitted++;}catch(e){error=e.message;break;}}
 provider.dispose();outcomes.push({mode,admitted,error});
}
const evidence={version:version??'v12.1',source_sha256:createHash('sha256').update(source).digest('hex'),scope:'20 unique exported watch IDs, identical query, before Worker ready; fake Worker; not mounted/native',outcomes};
if(process.argv[2])await writeFile(process.argv[2],JSON.stringify(evidence,null,2)+'\n');console.log(JSON.stringify(evidence));
if(process.argv.includes('--green')&&!(outcomes[0].admitted===20&&outcomes[1].admitted===16))process.exitCode=1;
