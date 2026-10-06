// Qualification only: actual WASM admission versus independent fixed literals.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {root,hash} from './v123-browser-support.mjs';
import {exactInteger,check,normalized,verifyVersions} from './v123-oracle.mjs';
const archive=root+'/rust-differential-product-20260929-review-checkpoint-v12.2.zip';
assert.equal(await hash(archive),'182e24d5911222f943c930059dc9317d44324d0a96c665ee14259fdd57062a09');
const source=execFileSync('python3',['-c','import sys,zipfile;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("scripts/v122-oracle.mjs"))',archive]);
const old=await import('data:text/javascript;base64,'+source.toString('base64'));
const {instance}=await WebAssembly.instantiate(fs.readFileSync(root+'/browser/public/product_core.wasm'),{}),e=instance.exports;
const read=(p,l)=>new TextDecoder().decode(new Uint8Array(e.memory.buffer,p,l));
function call(h,fn,s){const b=new TextEncoder().encode(s),p=e.product_core_alloc(b.length);assert(p);new Uint8Array(e.memory.buffer,p,b.length).set(b);try{const code=e[fn](h,p,b.length);return code?read(e.product_core_error_ptr(h),e.product_core_error_len(h)):null;}finally{e.product_core_dealloc(p,b.length);}}
const row=(quantity,coefficient='1')=>({id:'x',category:'a',quantity,amount:{coefficient,scale:0},label:{state:'missing'}});
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:1};
const cases=[['1_1','11'],['1__1_','11'],['+0_01_1','11'],['-1__1_','-11'],['-0_','0'],['+0','0'],['00011','11'],['9007199254740993','9007199254740993'],['-9223372036854775808','-9223372036854775808'],['18446744073709551615','18446744073709551615'],['18446744073709551616','18446744073709551616'],['1'.repeat(10001),'1'.repeat(10001)],['-'+'1'.repeat(10000),'-'+'1'.repeat(10000)]];
const invalid=['','_1','+_1','-_1','--1','++1','-+1','+-1',' 1','1 ','\t1','1\n','0x11','0b11','1.0','1e2','NaN','Infinity','١','１','1'.repeat(10002),'-'+'1'.repeat(10001)];
const records=[];
for(const [input,expected] of cases){
 assert.equal(exactInteger(input),expected);
 for(const field of ['quantity','coefficient']){
  const r=field==='quantity'?row(input):row('11',input),want=field==='quantity'?row(expected):row('11',expected);
  const h=e.product_core_new();let result;
  try{assert.equal(call(h,'product_core_apply',JSON.stringify({command:'upsert',row:r})),null);assert.equal(call(h,'product_core_apply',JSON.stringify({command:'open',subscription:'q',query:q})),null);assert.equal(call(h,'product_core_result','q'),null);result=JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h)));}finally{e.product_core_free(h);}
  assert.deepEqual(result.rows,[want]);check(result,[r],q);
  if(input.includes('_'))assert.throws(()=>old.check(result,[r],q));
  const poison=structuredClone(result);poison.rows[0].quantity='12';assert.throws(()=>check(poison,[r],q));
  records.push({inputLength:input.length,input:input.length<80?input:'bounded-long-integer',field,wasmMatchesFixedExpected:true,historicalRejectsAdmitted:input.includes('_'),repairedAccepts:true,poisonRejected:true});
 }
}
for(const input of invalid){
 assert.throws(()=>exactInteger(input));
 for(const field of ['quantity','coefficient']){
  const h=e.product_core_new();try{assert.match(call(h,'product_core_apply',JSON.stringify({command:'upsert',row:field==='quantity'?row(input):row('11',input)})),/invalid typed command/);}finally{e.product_core_free(h);}
 }
}
// Canonical equivalent commits must not invent a result-version increment.
const before=row('11','11'),after=row('+0_11','1__1_');
const ops=[{state:'ready',incarnation:'test',source_sequence:'0'},{state:'source_committed',offset:0},{state:'profile_command',connection:1,id:1,acquisition:1,command:{command:'open',subscription:'q',query:q}},{state:'source_committed',offset:1},{state:'profile_command',connection:1,id:2,acquisition:1,command:{command:'change_window',subscription:'q',offset:0,limit:1}}];
const event={type:'receive',message:{type:'ack',results:{q:{subscription:'q',rows:[before],total_rows:1,start_rank:0,version:2,sequence:0,query_generation:2,remote:{incarnation:'test',connection:'1',sourceSequence:'2',requestId:2,acquisition:1}}}}};
const cuts={'0':[],'1':[before],'2':[after]};
assert.deepEqual(normalized(after),before);assert.throws(()=>old.verifyVersions([event],ops,cuts));verifyVersions([event],ops,cuts);
const poisoned=structuredClone(event);poisoned.message.results.q.version++;assert.throws(()=>verifyVersions([poisoned],ops,cuts));
const paths=['scripts/v123-oracle.mjs','scripts/test-v123-integer-admission.mjs','native/src/product.rs'];
const report={status:'passed',run_id:process.env.ACCEPTANCE_RUN_ID??null,wasm_sha256:await hash(root+'/browser/public/product_core.wasm'),historical_archive_sha256:await hash(archive),source_hashes:Object.fromEntries(await Promise.all(paths.map(async p=>[p,await hash(root+'/'+p)]))),cases:records,invalidCases:invalid.length*2,equivalentVersionChecked:true};
fs.mkdirSync(root+'/evidence/v12.3',{recursive:true});fs.writeFileSync(root+'/evidence/v12.3/integer-admission.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
