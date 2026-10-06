// Isolated phase timings. Fixture IPC is excluded from the timed codec calls.
import fs from 'node:fs';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {createInterface} from 'node:readline';
import {createHash} from 'node:crypto';
import {decodeNative,adapt} from '../experiments/v131/js/codec.mjs';
const binary=process.env.V13_CODEC_BINARY??'/private/tmp/v131-codec-target/release/v13-codec-experiment';
const records=[];
for(let repeat=0;repeat<5;repeat++){
 const child=spawn(binary,[],{stdio:['pipe','pipe','inherit']}),lines=createInterface({input:child.stdout})[Symbol.asyncIterator]();
 const request=async q=>{child.stdin.write(JSON.stringify(q)+'\n');const v=JSON.parse((await lines.next()).value);assert(!v.error,v.error);return v;};
 try{for(const distribution of ['integers','decimals','strings','mixed','synthetic-bytes']){
  const value={rows:Array.from({length:32},(_,i)=>({id:'r'+i,category:'a',quantity:distribution==='integers'?'1234567890'.repeat(10)+i:String(i),amount:{coefficient:distribution==='decimals'?'-'+'987654321'.repeat(10)+(i+1):String(i+1),scale:0},label:{state:'value',value:distribution==='strings'?'日本語😀|'.repeat(64):'label'}}))};
  // Normalize coefficients exactly as the product does before wire preparation.
  for(const r of value.rows){let n=BigInt(r.amount.coefficient);while(n!==0n&&n%10n===0n){n/=10n;r.amount.scale--;}r.amount.coefficient=String(n);}
  for(const codec of (repeat%2?['msgpack','protobuf','json']:['json','protobuf','msgpack'])){
   if(distribution==='synthetic-bytes'&&codec==='json')continue;
   const q=distribution==='synthetic-bytes'?{op:'encode_binary',codec,bytes:Array.from({length:4096},(_,i)=>i%256)}:{op:'encode',codec,value};
   const samples=[];
   for(let i=-10;i<100;i++){
    const r=await request(q),bytes=Uint8Array.from(r.bytes);let t=process.hrtime.bigint();
    const native=codec==='json'?JSON.parse(new TextDecoder().decode(bytes)):decodeNative(bytes,codec);const decodeNs=Number(process.hrtime.bigint()-t);t=process.hrtime.bigint();
    const decoded=codec==='json'?native:adapt(native,codec);const adaptNs=Number(process.hrtime.bigint()-t);
    if(distribution==='synthetic-bytes')assert.deepEqual([...decoded],q.bytes);else assert.deepEqual(decoded,value);
    if(i>=0)samples.push({prepareNs:r.prepare_ns,encodeNs:r.encode_ns,decodeNs,adaptNs,bytes:bytes.length});
   }
   records.push({repeat,codec,distribution,samples});
  }
 }}finally{child.stdin.end();await new Promise(r=>child.on('exit',r));}
}
const sha=p=>createHash('sha256').update(fs.readFileSync(p)).digest('hex');
fs.writeFileSync(new URL('../evidence/v13.1/phase-measurements.json',import.meta.url),JSON.stringify({status:'passed',records,warmup:10,samplesPerProcess:100,processes:5,binary_sha256:sha(binary),harness_sha256:sha(new URL(import.meta.url)),rule_sha256:sha(new URL('../CODEC-DECISION-RULE.md',import.meta.url)),scope:'Rust release encode; Node JS decoder phases. Browser Worker measurements are collected separately. Synthetic byte fixture has no product semantics.'},null,2)+'\n');
console.log('phase measurements passed: '+records.length+' series');
