// Experimental comparison adapter only. Each built Worker imports exactly one codec module.
import * as protobuf from './protobuf.mjs';
import * as msgpack from './msgpack.mjs';
export {prepare,exactBytes,exactBigInt} from './values.mjs';
const select=codec=>{if(codec==='protobuf')return protobuf;if(codec==='msgpack')return msgpack;throw Error('codec');};
export const encode=(value,codec)=>select(codec).encode(value);
export const encodePrepared=(value,codec)=>select(codec).encodePrepared(value);
export const decodeNative=(value,codec)=>select(codec).decodeNative(value);
export const adapt=(value,codec)=>select(codec).adapt(value);
export const decode=(value,codec)=>select(codec).decode(value);
