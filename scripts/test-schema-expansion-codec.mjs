import assert from 'node:assert/strict';
import fs from 'node:fs';
import {encodeGeneric,decodeGeneric} from '../experiments/v131/js/msgpack.mjs';
import {validateRow,validateQuery,enumValue} from '../browser/src/topic-schema.ts';
import {schemas,enums} from '../browser/src/generated/expanded-topics.ts';
const row={oo:{name:'',status:enumValue('example.common.Status',-2147483648),price:'9007199254740993.0000000000000000001',note:''}};
const bytes=encodeGeneric(row),decoded=decodeGeneric(bytes);
// The established decoder intentionally uses null-prototype maps.
assert.equal(Object.getPrototypeOf(decoded),null);
assert.deepEqual(JSON.parse(JSON.stringify(decoded)),row);
validateRow(schemas.shit,decoded,['oo.name','oo.status','oo.price','oo.note']);
assert.deepEqual(enums['example.common.Status'].ACTIVE,enums['example.common.Status'].OPEN);
validateQuery(schemas.shit,{select:['oo.status'],orderBy:[],where:{op:'eq',field:'oo.status',value:enums['example.common.Status'].OPEN}});
assert.throws(()=>validateQuery(schemas.shit,{select:['oo.status'],orderBy:[],where:{op:'eq',field:'oo.status',value:enums['other.Status'].OPEN}}));
assert.throws(()=>validateRow(schemas.shit,{oo:{name:'',status:enums['other.Status'].OPEN}},['oo.name','oo.status']));
assert.throws(()=>validateRow(schemas.shit,{oo:{price:9007199254740993}},['oo.price']));
fs.writeFileSync(new URL('../evidence/schema-expansion/nested-codec.json',import.meta.url),JSON.stringify({status:'PASS',bytes:bytes.length,row,decoded,checks:['null-prototype map preserved','nested decimal bytes exact','signed unknown enum','alias equality','same-domain operand accepted','cross-domain operand/row rejected','numeric decimal rejected']},null,2));
console.log('PASS nested MessagePack codec and enum/decimal runtime admission');
