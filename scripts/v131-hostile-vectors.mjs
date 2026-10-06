import {viewwire} from '../experiments/v131/js/wire.generated.js';
import {encode as mp,ExtData} from '../experiments/v131/node_modules/@msgpack/msgpack/dist.esm/index.mjs';
import '../experiments/v131/js/codec.mjs';
let pb={integer:0},nested=0;for(let i=0;i<129;i++){pb={sequence:{items:[pb]}};nested=[nested];}
export const hostile={
 protobuf:{truncated:[0x3a,2,0x0a],impossible_tag:[0x48,1],conflicting_variants:[8,1,16,1],oversized_length:[0x22,0xff,0xff,0xff,0xff,0x0f],excessive_nesting:[...viewwire.Value.encode(pb).finish()],invalid_exact_sign:[0x42,1,2],negative_zero:[0x42,1,1],leading_zero:[0x42,2,0,0],invalid_utf8:[0x22,1,0xff]},
 msgpack:{truncated:[0x81,0xa1],impossible_tag:[0xc1],conflicting_keys:[0x82,0xa1,97,0,0xa1,97,1],oversized_length:[0xdb,0xff,0xff,0xff,0xff],excessive_nesting:[...mp(nested,{maxDepth:132})],invalid_extension:[0xc7,1,43,0],invalid_exact_sign:[0xc7,1,42,2],negative_zero:[...mp(new ExtData(42,Uint8Array.of(1)))],leading_zero:[...mp(new ExtData(42,Uint8Array.of(0,0)))],invalid_utf8:[0xa1,0xff]},
};
