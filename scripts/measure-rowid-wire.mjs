import assert from 'node:assert/strict';import {encodeGeneric} from '../experiments/v131/js/msgpack.mjs';
const rows=Array.from({length:8},(_,i)=>({customer:'C'+i,price:String(i+1)}));const keys=rows.map((_,i)=>'r'+i);
const encodedIds=keys.map(k=>'rid2:'+Buffer.concat([Buffer.from([1,1,1,0,0,0,2]),Buffer.from(k)]).toString('hex'));
const make=keys=>({kind:'snapshot',subscription:'s',query_generation:1,sequence:1,start_rank:0,version:1,contentVersion:1,total_rows:8,revision:1,windowId:1,effectiveEnd:8,projection:['customer','price'],keys,rows});
const old=encodeGeneric(make(keys)).length,current=encodeGeneric(make(encodedIds)).length;
const duplicated=encodeGeneric({...make(encodedIds),rows:rows.map((r,i)=>({...r,rowId:encodedIds[i]}))}).length;
assert(current>old&&duplicated>current);
console.log(JSON.stringify({scope:'actual MessagePack encoding, fixed 8-row snapshot and telemetry disabled, application bytes only',rows:8,legacyStringKeyBytes:old,compositeKeyBytes:current,publicPropertyWireDuplicationBytes:0,hypotheticalDuplicatedRowIdBytes:duplicated,compositeIdentityDelta:current-old,avoidedDuplication:duplicated-current}));
