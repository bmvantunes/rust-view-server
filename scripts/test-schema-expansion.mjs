import fs from 'node:fs';import path from 'node:path';import os from 'node:os';import assert from 'node:assert/strict';import {spawnSync} from 'node:child_process';import {generate} from './generate-proto-topics.mjs';
const W=path.resolve(import.meta.dirname,'..'),E=W+'/evidence/schema-expansion',tmp=fs.mkdtempSync(path.join(os.tmpdir(),'schema-expansion-'));
const input=W+'/examples/schema-expansion/topics.proto';const a=await generate({input,out:tmp+'/a'}),b=await generate({input,out:tmp+'/b'});assert.deepEqual(a,b);await generate({input,check:true});
const n=tmp+'/negative';fs.cpSync(W+'/examples/schema-expansion',n,{recursive:true});const original=fs.readFileSync(n+'/topics.proto','utf8'),common=fs.readFileSync(n+'/common.proto','utf8');const cases=[];
for(const [label,file,change]of [
 ['cycle','common.proto',s=>s.replace('string name = 1;','Details name = 1;')],
 ['repeated','common.proto',s=>s.replace('string name = 1;','repeated string name = 1;')],
 ['map','common.proto',s=>s.replace('string name = 1;','map<string,string> name = 1;')],
 ['oneof','common.proto',s=>s.replace('string name = 1;','oneof choice { string name = 1; bool flag = 10; }')],
 ['metadata','common.proto',s=>s.replace('string name = 1;','string name = 1 [(view.optional) = true];')],
 ['missing-import','topics.proto',s=>s+'\nimport "not-supplied.proto";'],
 ['unknown-decimal-type','topics.proto',s=>s.replace('OtherShit oo = 1;','decimal price = 1;')],
 ['field-keyword','common.proto',s=>s.replace('string name = 1;','string constructor = 1;')],
 ['closed-syntax','common.proto',s=>s.replace('syntax = "proto3"','syntax = "proto2"')],
 ['bad-enum-default','other.proto',s=>s.replace('UNKNOWN = 0','UNKNOWN = 3')],
 ['leaf-bound','common.proto',s=>s.replace('string name = 1;',Array.from({length:65},(_,i)=>`string field${i} = ${i+20};`).join('\n'))],
 ['enum-bound','other.proto',s=>s.replace('UNKNOWN = 0; OPEN = 1;',Array.from({length:257},(_,i)=>`V${i} = ${i};`).join(' '))],
 ['metadata-type','common.proto',s=>s.replace('(view.optional) = true','(view.optional) = "yes"')],
 ['bad-null','common.proto',s=>s.replace('(view.null_for) = "price"','(view.null_for) = "missing"')],
]){fs.cpSync(W+'/examples/schema-expansion',n,{recursive:true});const p=n+'/'+file;fs.writeFileSync(p,change(fs.readFileSync(p,'utf8')));const attempt=spawnSync(process.execPath,[W+'/scripts/generate-proto-topics.mjs','--input',n+'/topics.proto','--out',tmp+'/bad'],{encoding:'utf8'});const error=attempt.stderr;assert.notEqual(attempt.status,0,label);assert(error,label);const reasons={'cycle':/cycle\/depth bound/,'repeated':/unsupported field\/name\/oneof/,'map':/unsupported field\/name\/oneof/,'oneof':/unsupported field\/name\/oneof/,'metadata':/implicit\/decimal presence conflict/,'missing-import':/ENOENT.*|not-supplied.proto/,'unknown-decimal-type':/no such Type or Enum 'decimal'/,'field-keyword':/unsupported field\/name\/oneof.*constructor/,'closed-syntax':/illegal token|expanded schemas require proto3/,'bad-enum-default':/invalid enum/,'leaf-bound':/expanded leaf\/parent bounds/,'enum-bound':/invalid enum/,'metadata-type':/boolean metadata required/,'bad-null':/nullable field needs marker/};assert.match(error,reasons[label],label+' must reach its intended validation');cases.push({label,error});}
const base=JSON.parse(fs.readFileSync(W+'/fixtures/proto-topics/browser-catalog.json'));await generate({compatibilityExamples:true});assert.deepEqual(JSON.parse(fs.readFileSync(W+'/fixtures/proto-topics/browser-catalog.json')),base);
const run=(label,args)=>{const p=spawnSync(process.execPath,[W+'/browser/node_modules/typescript/bin/tsc','--noEmit',...args],{cwd:W,encoding:'utf8'});fs.writeFileSync(E+'/'+label+'.log',p.stdout+p.stderr);return p;};
assert.equal(run('types-browser',['-p','browser/tsconfig.json']).status,0);assert.equal(run('types-contracts',['-p','browser/tsconfig.contracts.json']).status,0);
const file=W+'/browser/src/schema-expansion-contract.test-d.ts',source=fs.readFileSync(file,'utf8'),negative=W+'/browser/src/schema-expansion-unsuppressed.test-d.ts';const expected=source.split('\n').flatMap((l,i)=>l.includes('@ts-expect-error')?[i+2]:[]);
try{fs.writeFileSync(negative,source.split('\n').map(l=>l.includes('@ts-expect-error')?'':l).join('\n'));const p=run('types-unsuppressed',['-p','browser/tsconfig.json']);assert.notEqual(p.status,0);const observed=[...p.stdout.matchAll(/schema-expansion-unsuppressed.test-d.ts\((\d+),/g)].map(m=>Number(m[1]));assert.deepEqual([...new Set(observed)].sort((a,b)=>a-b),expected);fs.writeFileSync(E+'/type-diagnostics.json',JSON.stringify({expected,observed},null,2));}finally{fs.rmSync(negative,{force:true});}
fs.writeFileSync(E+'/generation-and-types.json',JSON.stringify({status:'PASS',reproducible:2,flatCatalogUnchanged:true,negatives:cases,unsuppressedDiagnostics:expected.length,identity:a},null,2));console.log(JSON.stringify({status:'PASS',negativeGeneration:cases.length,negativeTypes:expected.length}));
