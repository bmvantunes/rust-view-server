import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {generate} from './generate-proto-topics.mjs';
import {schemaId,RUNTIME_SCHEMA_NAME_LIMIT} from './schema-id.mjs';
const W=path.resolve(import.meta.dirname,'..'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'schema-name-diagnostics-'));
// Bind this expectation to the actual native bound, not merely the helper itself.
assert.match(fs.readFileSync(W+'/native/src/schema.rs','utf8'),/value\.len\(\)<=64/);
assert.equal(RUNTIME_SCHEMA_NAME_LIMIT,64);
let accepted=0,rejected=0;
for(const expanded of [false,true]) {
 const dir=tmp+'/'+(expanded?'expanded':'flat');fs.mkdirSync(dir);
 fs.copyFileSync(W+'/proto/view-options.proto',dir+'/view-options.proto');
 for(const length of [1,61,62,63,64,65]) {
  const id='a'.repeat(length),out=dir+'/out'+length;
  fs.writeFileSync(dir+'/topics.proto',`syntax="proto3"; package topics; import "view-options.proto"; message Row { option (view.schema_id)="${id}"; ${expanded?'option (view.expanded)=true;':''} optional string name=1; }`);
  if(length<=61) {
   await generate({input:dir+'/topics.proto',out});
   const catalog=JSON.parse(fs.readFileSync(out+`/fixtures/${expanded?'expanded':'proto'}-topics/browser-catalog.json`));
   assert.equal(catalog[id].schema.id,id+(expanded?'_v3':'_v2'));accepted++;
  } else {
   await assert.rejects(()=>generate({input:dir+'/topics.proto',out}),e=>e.message.includes(`has ${length} characters; maximum 61`)&&e.message.includes('topics.Row')&&e.message.includes(expanded?'_v3':'_v2'));
   assert(!fs.existsSync(out),'rejection must precede generated output');rejected++;
  }
 }
}
assert.equal(schemaId('a'.repeat(60),10,'future'),'a'.repeat(60)+'_v10');
assert.throws(()=>schemaId('a'.repeat(61),10,'future'),/maximum 60/);
for(const id of ['', 'rowId','constructor','prototype','__proto__','A-B','é'])assert.throws(()=>schemaId(id,2,'fixture'),/Invalid.*view.schema_id/);
// All previously accepted public schemas, binding bytes, fingerprints and generated
// TS stay identical. Only generation provenance changes with generator source.
for(const [input,dest,compatibilityExamples] of [['proto/topics.proto','',true],['examples/schema-expansion/topics.proto','',false],['examples/standalone/proto/topics.proto','examples/standalone',false],['examples/grouped/proto/topics.proto','examples/grouped',false],['examples/symbol-collisions/proto/topics.proto','examples/symbol-collisions',false]]) {
 const out=tmp+'/stable'+accepted++;
 const result=await generate({input:W+'/'+input,out,compatibilityExamples});
 for(const relative of Object.keys(result.outputs))assert.deepEqual(fs.readFileSync(out+'/'+relative),fs.readFileSync(path.join(W,dest,relative)),relative);
}
console.log(JSON.stringify({status:'PASS',boundaryAccepted:4,boundaryRejected:rejected,existingCatalogsUnchanged:5,futureSuffixBound:true,temp:tmp}));
