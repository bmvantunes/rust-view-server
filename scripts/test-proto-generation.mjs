import assert from 'node:assert/strict';import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import {generate} from './generate-proto-topics.mjs';
const W=path.resolve(import.meta.dirname,'..'),tmp=fs.mkdtempSync(path.join(os.tmpdir(),'proto-generation-'));let negatives=0;
const original=fs.readFileSync(W+'/proto/topics.proto','utf8');fs.copyFileSync(W+'/proto/view-options.proto',tmp+'/view-options.proto');
const a=await generate({compatibilityExamples:true,out:tmp+'/a'}),b=await generate({compatibilityExamples:true,out:tmp+'/b'});assert.deepEqual(a,b);await generate({compatibilityExamples:true,check:true});
for(const [label,change]of [
 ['reserved-rowId',s=>s.replace('optional string customer =','optional string rowId =')],
 ['implicit-presence',s=>s.replace('optional double risk =','double risk =')],
 ['repeated',s=>s.replace('optional string customer =','repeated string customer =')],
 ['bytes',s=>s.replace('optional string customer =','optional bytes customer =')],
 ['bad-option',s=>s.replace('optional string customer = 2;','optional string customer = 2 [(view.surprise) = true];')],
 ['null-marker-missing',s=>s.replace('[(view.optional) = true, (view.nullable) = true]','[(view.optional) = true]')],
 ['decimal-number',s=>s.replace('optional string price','optional double price')],
 ['nested',s=>s.replace('message Orders {','message Orders { message Nested { optional string x=1; }')],
 ['service',s=>s+'\nservice Unexpected {}\n'],
]){fs.writeFileSync(tmp+'/topics.proto',change(original));await assert.rejects(()=>generate({input:tmp+'/topics.proto',out:tmp+'/bad'}),undefined,label);negatives++;}
console.log(JSON.stringify({passed:true,cleanRegenerations:2,negativeCases:negatives,outputs:Object.keys(a.outputs).length,temporaryDirectory:tmp}));
