import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {generate} from './generate-proto-topics.mjs';
const W=path.resolve(import.meta.dirname,'..'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'codegen-symbols-'));
const input=W+'/examples/symbol-collisions/proto/topics.proto';
const a=await generate({input,out:tmp+'/a'}),b=await generate({input,out:tmp+'/b'});
for(const file of [...Object.keys(a.outputs),'fixtures/proto-topics/GENERATION.json'])assert.deepEqual(fs.readFileSync(tmp+'/a/'+file),fs.readFileSync(tmp+'/b/'+file));
await generate({input,out:W+'/examples/symbol-collisions',check:true});
const proto=fs.readFileSync(input,'utf8'),start=proto.indexOf('message '),messages=proto.slice(start).match(/message [\s\S]*?\}/g);
fs.writeFileSync(tmp+'/topics.proto',proto.slice(0,start)+'message Unrelated { option (view.schema_id)="unrelated"; optional bool flag=1; }\n'+messages.reverse().join('\n'));
fs.copyFileSync(W+'/proto/view-options.proto',tmp+'/view-options.proto');
await generate({input:tmp+'/topics.proto',out:tmp+'/reordered'});
async function load(dir){fs.writeFileSync(dir+'/browser/src/topic-schema.ts',`export * from ${JSON.stringify(pathToFileURL(W+'/browser/src/topic-schema.ts').href)};\n`);return import(pathToFileURL(dir+'/browser/src/generated/topics.ts'));}
const original=await load(tmp+'/a'),reordered=await load(tmp+'/reordered');
assert.deepEqual(Object.keys(original).sort(),['catalog','keyFields','schemas']);
for(const name of Object.keys(original.schemas)){
 assert.equal(original.schemas[name].id,name+'_v2');
 assert.deepEqual(reordered.schemas[name],original.schemas[name]);
 assert.deepEqual(reordered.catalog[name],original.catalog[name]);
}
assert.deepEqual(reordered.keyFields,original.keyFields);
assert.deepEqual(original.keyFields.BalanceKey.map(f=>f.name),['tenant','account']);
assert.deepEqual(original.keyFields.balanceKey.map(f=>f.name),['different']);
assert.notEqual(original.schemas.comparison_products.id,original.schemas.comparisonProducts.id);
console.log(JSON.stringify({passed:true,cleanGenerations:2,exactTopics:Object.keys(original.catalog),reorderedAndExtendedPublicReferencesStable:true,descriptorOrder:'not compared; existing descriptor numeric IDs remain definition-order dependent'}));
