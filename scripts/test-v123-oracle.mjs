// Fresh WASM + fixed expected rows + sealed historical oracle red/green proof.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
import {root,hash} from './v123-browser-support.mjs';
import {check,verifyLedger,verifyVersions,normalized} from './v123-oracle.mjs';
const zip=root+'/rust-differential-product-20260929-review-checkpoint-v12.1.zip';
const historical=execFileSync('python3',['-c','import sys,zipfile;sys.stdout.buffer.write(zipfile.ZipFile(sys.argv[1]).read("scripts/v121-oracle.mjs"))',zip]);
const old=await import('data:text/javascript;base64,'+historical.toString('base64'));
const wasm=fs.readFileSync(root+'/browser/public/product_core.wasm');
const {instance}=await WebAssembly.instantiate(wasm,{}),e=instance.exports;
const read=(p,l)=>new TextDecoder().decode(new Uint8Array(e.memory.buffer,p,l));
function call(h,fn,s){const b=new TextEncoder().encode(s),p=e.product_core_alloc(b.length);assert(p);new Uint8Array(e.memory.buffer,p,b.length).set(b);try{if(e[fn](h,p,b.length))throw Error(read(e.product_core_error_ptr(h),e.product_core_error_len(h)));}finally{e.product_core_dealloc(p,b.length);}}
const row=(id,coefficient='1',scale=0)=>({id,category:'a',quantity:'9007199254740993',amount:{coefficient,scale},label:{state:'missing'}});
const cases=[];
for(const [name,rows,direction] of [
 ['descending-ties',[row('a'),row('b')],'descending'],
 ['scale-floor',[row('a','10',-10000)],'ascending'],
 ['unicode-id-ties',[row('\ue000'),row('\u{10000}')],'ascending'],
]){
 const h=e.product_core_new(),q={where_expr:{op:'true'},direction,offset:0,limit:10};let r;
 try{for(const row of rows)call(h,'product_core_apply',JSON.stringify({command:'upsert',row}));call(h,'product_core_apply',JSON.stringify({command:'open',subscription:'q',query:q}));call(h,'product_core_result','q');r=JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h)));}finally{e.product_core_free(h);}
 // Fixed expected rows are independent of both old/new oracle sort/normalization.
 assert.deepEqual(r.rows,rows);assert.throws(()=>old.check(r,rows,q));check(r,rows,q);
 const bad=structuredClone(r);if(name==='scale-floor')bad.rows[0].amount={coefficient:'1',scale:-10001};else bad.rows.reverse();
 old.check(bad,rows,q);assert.throws(()=>check(bad,rows,q));
 // Exercise the exact unsolicited-publication verifier, not only its comparator.
 const events=[{worker:1,type:'send',message:{id:1,acquisition:1,command:{command:'open',subscription:'q',query:q}}},{worker:1,type:'receive',message:{type:'live',results:{q:{...r,remote:{incarnation:'a',connection:'1',sourceSequence:'1',acquisition:1}}},acquisitions:{q:1}}}];
 assert.equal(verifyLedger(events,{'1':rows}).live,1);
 const poisoned=structuredClone(events);poisoned[1].message.results.q.rows=bad.rows;
 assert.throws(()=>verifyLedger(poisoned,{'1':rows}));
 cases.push({name,fresh_wasm_matches_fixed_expected:true,historical_rejects_correct:true,historical_accepts_poison:true,repaired_accepts_correct:true,repaired_rejects_poison:true,live_ledger_rejects_poison:true});
}
// Equivalent and negative-prefix values, zero, exact scale endpoints, and ties in
// both directions; manually ordered expected IDs and canonical forms.
const rows=[row('neg-prefix','-1001',3),row('neg-one','-10',1),row('zero','-0000',10000),row('positive','00100',2),row('floor','100',-9999),row('tiny','1',10000),row('tie-a','2'),row('tie-b','20',1)];
const expected={ascending:['neg-prefix','neg-one','zero','tiny','positive','tie-a','tie-b','floor'],descending:['floor','tie-a','tie-b','positive','tiny','zero','neg-one','neg-prefix']};
const canonical=rows.map(r=>({...r,amount:r.id==='zero'?{coefficient:'0',scale:0}:r.id==='positive'?{coefficient:'1',scale:0}:r.id==='neg-one'?{coefficient:'-1',scale:0}:r.id==='floor'?{coefficient:'10',scale:-10000}:r.id==='tie-b'?{coefficient:'2',scale:0}:r.amount}));
for(const direction of ['ascending','descending'])for(const [offset,limit] of [[0,8],[1,3],[8,2],[100000,2],[0,0]]){
 const q={where_expr:{op:'true'},direction,offset,limit};const ordered=expected[direction].map(id=>canonical.find(r=>r.id===id));
 check({rows:ordered.slice(offset,offset+limit),total_rows:8,start_rank:offset},rows,q);
}
assert.deepEqual(normalized(row('negative-floor','-100',-9999)).amount,{coefficient:'-10',scale:-10000});
assert.throws(()=>normalized(row('invalid','1',-10001)));
// Independent source-version model regression: representational changes alone
// do not advance completed content version. Obtain the version from fresh WASM.
const q={where_expr:{op:'true'},direction:'ascending',offset:0,limit:10};
const before=row('same','10',1),equivalent=row('same','100',2);
const h=e.product_core_new();let unchanged;
try{
 call(h,'product_core_apply',JSON.stringify({command:'upsert',row:before}));
 call(h,'product_core_apply',JSON.stringify({command:'open',subscription:'q',query:q}));
 call(h,'product_core_apply',JSON.stringify({command:'upsert',row:equivalent}));
 call(h,'product_core_result','q');unchanged=JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h)));
}finally{e.product_core_free(h);}
assert.equal(unchanged.version,2);assert.deepEqual(unchanged.rows,[row('same')]);
const operations=[{state:'ready',incarnation:'test',source_sequence:'0'},
 {state:'source_committed',offset:0},
 {state:'profile_command',connection:1,id:1,acquisition:1,command:{command:'open',subscription:'q',query:q}},
 {state:'source_committed',offset:1},
 {state:'profile_command',connection:1,id:2,acquisition:1,command:{command:'change_window',subscription:'q',offset:0,limit:10}}];
const events=[{type:'receive',message:{type:'ack',results:{q:{...unchanged,query_generation:2,remote:{incarnation:'test',connection:'1',sourceSequence:'2',requestId:2,acquisition:1}}}}}];
const cuts={'0':[],'1':[before],'2':[equivalent]};
assert.throws(()=>old.verifyVersions(events,operations,cuts));verifyVersions(events,operations,cuts);
const poisoned=structuredClone(events);poisoned[0].message.results.q.version++;
old.verifyVersions(poisoned,operations,cuts);assert.throws(()=>verifyVersions(poisoned,operations,cuts));
const equivalent_source_noop={fresh_wasm_version:unchanged.version,historical_rejects_correct:true,historical_accepts_poison:true,repaired_accepts_correct:true,repaired_rejects_poison:true};
const report={status:'passed',run_id:process.env.ACCEPTANCE_RUN_ID??null,wasm_sha256:createHash('sha256').update(wasm).digest('hex'),historical_archive_sha256:await hash(zip),historical_oracle_sha256:createHash('sha256').update(historical).digest('hex'),source_hashes:Object.fromEntries(await Promise.all(['scripts/v123-oracle.mjs','scripts/test-v123-oracle.mjs'].map(async p=>[p,await hash(root+'/'+p)]))),cases,equivalent_source_noop,additional_fixed_cases:10};
fs.mkdirSync(root+'/evidence/v12.3',{recursive:true});fs.writeFileSync(root+'/evidence/v12.3/oracle-regressions.json',JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
