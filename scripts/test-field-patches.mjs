import assert from 'node:assert/strict';
import fs from 'node:fs';
import {reconstruct} from '../browser/src/row-delta.mjs';
import {encodeGeneric,decodeGeneric} from '../experiments/v131/js/msgpack.mjs';
const plain=v=>JSON.parse(JSON.stringify(v));
const round=v=>decodeGeneric(encodeGeneric(v));
const contract={fieldPatches:true,topic:'nested',schema:'fingerprint',fields:['details.note','details.extra','wide'],key:'unused',validate(row){assert.equal(typeof row.wide,'string');assert(Object.keys(row).every(k=>['details','wide'].includes(k)));if(Object.hasOwn(row,'details')){assert(row.details&&typeof row.details==='object'&&!Array.isArray(row.details));assert(Object.keys(row.details).every(k=>['note','extra'].includes(k)));}}};
let snapshot={subscription:'p',topic:'nested',schema:'fingerprint',query_generation:1,sequence:1,start_rank:0,version:1,total_rows:1,revision:1,contentVersion:1,windowId:1,effectiveEnd:1,projection:contract.fields,kind:'snapshot',keys:['key'],rows:[{details:{note:'before'},wide:'x'.repeat(2048)}]};
const base=reconstruct(undefined,round(snapshot),contract),old=JSON.stringify(base),row=base.rows[0];
function delta(changes){const {keys,rows,...metadata}=snapshot;return {...metadata,kind:'delta',revision:2,contentVersion:2,fromRevision:1,fromVersion:1,toVersion:2,operations:[{type:'patch',key:'key',index:0,changes}]};}
const apply=changes=>reconstruct(base,round(delta(changes)),contract);
for(const value of [null,0,false,'', 'é', {domain:'example.Status',code:-2147483648}])assert.deepEqual(JSON.parse(JSON.stringify(apply([{type:'set',path:'details.note',value}]).rows[0].details.note)),value);
assert.deepEqual(plain(apply([{type:'remove',path:'details.note'}]).rows[0].details),{});
assert(!Object.hasOwn(apply([{type:'remove',path:'details'}]).rows[0],'details'));
const absent=reconstruct(undefined,round({...snapshot,rows:[{wide:'x'}]}),contract);
const present=reconstruct(absent,round(delta([{type:'object',path:'details'}])),contract);assert.deepEqual(plain(present.rows[0].details),{});
const nested=reconstruct(absent,round(delta([{type:'object',path:'details'},{type:'set',path:'details.extra',value:false}])),contract);assert.deepEqual(plain(nested.rows[0].details),{extra:false});
for(const bad of [
 [{type:'set',path:'secret',value:1}], [{type:'set',path:'details.hidden',value:1}], [{type:'set',path:'rowId',value:'new'}], [{type:'set',path:'__proto__.polluted',value:true}],
 [{type:'object',path:'details'}],[{type:'remove',path:'details.extra'}], [{type:'set',path:'details.note',value:'valid'},{type:'remove',path:'details'},{type:'set',path:'details.note',value:'invalid'}],
 [{type:'set',path:'details.note',value:1},{type:'set',path:'details.note',value:2}], [{type:'remove',path:'details',value:null}], [{type:'set',path:'details.note'}],
])assert.throws(()=>apply(bad));
const batch=delta([{type:'set',path:'details.note',value:'first'}]);batch.operations.push({type:'patch',key:'key',index:0,changes:[{type:'set',path:'secret',value:1}]});assert.throws(()=>reconstruct(base,round(batch),contract));assert.equal(JSON.stringify(base),old);assert.equal(base.rows[0],row);
assert.throws(()=>reconstruct(base,round(delta([{type:'set',path:'details.note',value:1}])),{...contract,fieldPatches:false}));
for(const changes of [{fromRevision:99},{windowId:2},{schema:'other'},{result_shape:'other'},{query_generation:2}])assert.throws(()=>reconstruct(base,round({...delta([{type:'set',path:'details.note',value:1}]),...changes}),contract));
const sparse=apply([{type:'set',path:'wide',value:'new'}]);assert.equal(sparse.rows[0].details,base.rows[0].details,'unmodified subtree reused');
if(process.argv[2]){const text=fs.readFileSync(process.argv[2],'utf8'),vectors=text.split('\n').filter(l=>l.startsWith('VECTOR:')).map(l=>JSON.parse(l.slice(7)));assert(vectors.length);for(const v of vectors){const b=reconstruct(undefined,round(v.snapshot),contract);const actual=reconstruct(b,round(v.delta),contract);const expected=reconstruct(b,round(v.full),contract);assert.deepEqual(actual.rows,expected.rows);assert(encodeGeneric(v.delta).byteLength<encodeGeneric(v.full).byteLength/2);}console.log('native MessagePack parity',vectors.length);}
console.log(JSON.stringify({status:'PASS',atomicInvalidFinal:true,presence:true,unselectedRejected:true,negotiation:true,structuralSharing:true}));
