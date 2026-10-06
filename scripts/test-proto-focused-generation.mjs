import assert from 'node:assert/strict';import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import {generate} from './generate-proto-topics.mjs';
const W=path.resolve(import.meta.dirname,'..'),R=path.dirname(W),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'proto-focused-'));const results=[];
for(const fixture of ['appended-v2-no-legacy','standalone-catalog']){
 const result=await generate({input:R+'/supplementary-review/generator-fixtures/'+fixture+'/topics.proto',out:tmp+'/'+fixture});
 assert(!Object.keys(result.outputs).some(p=>p.startsWith('fixtures/topics/')));
 results.push({fixture,passed:true,outputs:result.outputs});
}
const input=W+'/examples/standalone/proto/topics.proto',a=await generate({input,out:tmp+'/a'}),b=await generate({input,out:tmp+'/b'});assert.deepEqual(a,b);
for(const p of [...Object.keys(a.outputs),'fixtures/proto-topics/GENERATION.json'])assert.deepEqual(fs.readFileSync(tmp+'/a/'+p),fs.readFileSync(tmp+'/b/'+p));
await generate({input,out:W+'/examples/standalone',check:true});
const standalone=JSON.parse(fs.readFileSync(tmp+'/a/fixtures/proto-topics/browser-catalog.json'));assert.deepEqual(standalone.balances.schema.fields.map(f=>f.name),['quantity','risk']);
await assert.rejects(()=>generate({input,out:tmp+'/bad',compatibilityExamples:true}),/compatibility examples require/);
fs.copyFileSync(W+'/proto/view-options.proto',tmp+'/view-options.proto');fs.writeFileSync(tmp+'/topics.proto',fs.readFileSync(input,'utf8').replace('option (view.schema_id) = "balances";','option (view.schema_id) = "balances"; option (view.legacy_key) = "quantity";'));
await assert.rejects(()=>generate({input:tmp+'/topics.proto',out:tmp+'/bad'}),/legacy key metadata invalid/);
const compat=await generate({compatibilityExamples:true,out:tmp+'/compat'}),original=path.join(R,'repair-evidence/compatibility-baseline');
const historical=Object.keys(compat.outputs).filter(p=>p.startsWith('fixtures/topics/'));
for(const p of historical)assert.deepEqual(fs.readFileSync(tmp+'/compat/'+p),fs.readFileSync(original+'/'+p),p);
console.log(JSON.stringify({passed:true,protobufjs:a.version,fixtures:results,cleanStandaloneGenerations:2,standaloneOutputs:a.outputs,historicalByteIdentical:historical,additionalNegatives:2},null,2));
