// Qualification regression: execute native WASM against fixed typed-row literals.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {root,hash} from './v124-browser-support.mjs';
import {check,normalized,verifyVersions} from './v124-oracle.mjs';
const archive=root+'/rust-differential-product-20260929-review-checkpoint-v12.3.zip';
assert.equal(await hash(archive),'b35504ee3d90c576db1ee62a5a608f56702426918ac28c7bce6374c87be720a8');
const old=await import('data:text/javascript;base64,'+execFileSync('python3',['-c','import sys,zipfile;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("scripts/v123-oracle.mjs"))',archive]).toString('base64'));
const {instance}=await WebAssembly.instantiate(fs.readFileSync(root+'/browser/public/product_core.wasm'),{}),e=instance.exports;
const read=(p,l)=>new TextDecoder().decode(new Uint8Array(e.memory.buffer,p,l));
function call(h,fn,s){const b=new TextEncoder().encode(s),p=e.product_core_alloc(b.length);assert(p);new Uint8Array(e.memory.buffer,p,b.length).set(b);try{const code=e[fn](h,p,b.length);assert.equal(code,0,read(e.product_core_error_ptr(h),e.product_core_error_len(h)));}finally{e.product_core_dealloc(p,b.length);}}
const base={id:'x',category:'a',quantity:'11',amount:{coefficient:'11',scale:0}};
const missing={...base,label:{state:'missing'}};
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:1};
const inputs=[
 ['omitted-label',base,missing],
 ['explicit-missing',missing,missing],
 ['null',{...base,label:{state:'null'}},{...base,label:{state:'null'}}],
 ['empty-string',{...base,label:{state:'value',value:''}},{...base,label:{state:'value',value:''}}],
 ['value',{...base,label:{state:'value',value:'hello'}},{...base,label:{state:'value',value:'hello'}}],
 ['ignored-row-field',{...missing,extra:'ignored'},missing],
 ['ignored-amount-field',{...missing,amount:{...base.amount,extra:'ignored'}},missing],
 ['ignored-value-label-field',{...base,label:{state:'value',value:'hello',extra:'ignored'}},{...base,label:{state:'value',value:'hello'}}],
];
const cases=[];
for(const [name,input,expected] of inputs){
 const h=e.product_core_new();
 try{
  call(h,'product_core_apply',JSON.stringify({command:'upsert',row:input}));
  call(h,'product_core_apply',JSON.stringify({command:'open',subscription:'q',query:q}));
  call(h,'product_core_result','q');const result=JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h)));
  assert.deepEqual(result.rows,[expected]);assert.deepEqual(normalized(input),expected);check(result,[input],q);
  const red=['omitted-label','ignored-row-field','ignored-value-label-field'].includes(name);
  if(red){assert.throws(()=>old.check(result,[input],q));const poison=structuredClone(result);poison.rows=[structuredClone(input)];old.check(poison,[input],q);assert.throws(()=>check(poison,[input],q));}
  for(const label of [{state:'missing'},{state:'null'},{state:'value',value:''}])if(JSON.stringify(label)!==JSON.stringify(expected.label)){
   const poison=structuredClone(result);poison.rows[0].label=label;assert.throws(()=>check(poison,[input],q));
  }
  call(h,'product_core_apply',JSON.stringify({command:'upsert',row:expected}));call(h,'product_core_result','q');
  const after=JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h)));assert.equal(after.version,result.version);
  cases.push({name,wasmMatchesFixedExpected:true,repairedAccepts:true,labelDistinctionsPreserved:true,nativeEquivalentNoop:true,historicalRejectsCorrect:red,historicalAcceptsPoison:red,repairedRejectsPoison:red});
 }finally{e.product_core_free(h);}
}
const ops=[{state:'ready',incarnation:'test',source_sequence:'0'},{state:'source_committed',offset:0},{state:'profile_command',connection:1,id:1,acquisition:1,command:{command:'open',subscription:'q',query:q}},{state:'source_committed',offset:1},{state:'profile_command',connection:1,id:2,acquisition:1,command:{command:'change_window',subscription:'q',offset:0,limit:1}}];
const event={type:'receive',message:{type:'ack',results:{q:{subscription:'q',rows:[missing],total_rows:1,start_rank:0,version:2,sequence:0,query_generation:2,remote:{incarnation:'test',connection:'1',sourceSequence:'2',requestId:2,acquisition:1}}}}};
const cuts={'0':[],'1':[base],'2':[missing]};
assert.throws(()=>old.verifyVersions([event],ops,cuts));verifyVersions([event],ops,cuts);
const poison=structuredClone(event);poison.message.results.q.version++;old.verifyVersions([poison],ops,cuts);assert.throws(()=>verifyVersions([poison],ops,cuts));
const paths=['scripts/v124-oracle.mjs','scripts/test-v124-row-canonical.mjs','native/src/product.rs'];
const report={status:'passed',run_id:process.env.ACCEPTANCE_RUN_ID??null,wasm_sha256:await hash(root+'/browser/public/product_core.wasm'),historical_archive_sha256:await hash(archive),source_hashes:Object.fromEntries(await Promise.all(paths.map(async p=>[p,await hash(root+'/'+p)]))),cases,equivalentVersionChecked:true,historicalAcceptsPoisonedVersion:true,repairedRejectsPoisonedVersion:true};
fs.mkdirSync(root+'/evidence/v12.4',{recursive:true});fs.writeFileSync(root+'/evidence/v12.4/row-canonical.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
