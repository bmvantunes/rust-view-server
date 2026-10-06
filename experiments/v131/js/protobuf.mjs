import protobuf from 'protobufjs/minimal.js';
import {viewwire} from './wire.generated.js';
import {preflight,MAX_FRAME,MAX_DEPTH} from './scan.mjs';
import {Exact,prepare,adaptValue} from './values.mjs';
const SAFE=9007199254740991n;
const variants=['nil','boolean','integer','text','binary','sequence','object','exact'];
protobuf.util.recursionLimit=3*MAX_DEPTH+4;protobuf.Reader.recursionLimit=3*MAX_DEPTH+4;
function pb(v){if(v===null)return {nil:true};if(typeof v==='boolean')return{boolean:v};if(typeof v==='number')return{integer:v};if(typeof v==='string')return{text:v};if(v instanceof Exact)return{exact:v.bytes};if(v instanceof Uint8Array)return{binary:v};if(Array.isArray(v))return{sequence:{items:v.map(pb)}};return{object:{entries:Object.entries(v).map(([key,v])=>({key,value:pb(v)}))}};}
function unpb(v){const keys=variants.filter(k=>Object.hasOwn(v,k));if(keys.length!==1)throw Error('variant');const k=keys[0],x=v[k];switch(k){case'nil':if(x!==true)throw Error('nil');return null;case'boolean':case'text':case'binary':return x;case'integer':{const n=BigInt(x.toString());if(n< -SAFE||n>SAFE)throw Error('metadata overflow');return Number(n);}case'exact':return new Exact(x);case'sequence':return(x.items??[]).map(unpb);case'object':{const o=Object.create(null);for(const e of x.entries??[]){if(Object.hasOwn(o,e.key)||!e.value)throw Error('duplicate/missing entry');o[e.key]=unpb(e.value);}return o;}}}

export function encodePrepared(value){const b=viewwire.Value.encode(pb(value)).finish();if(b.length>MAX_FRAME)throw Error('frame budget');return b;}
export function encode(value){return encodePrepared(prepare(value));}
export function decodeNative(bytes){preflight(bytes,'protobuf');return viewwire.Value.decode(bytes);}
export function adapt(value){return adaptValue(unpb(value));}
export function decode(bytes){return adapt(decodeNative(bytes));}
