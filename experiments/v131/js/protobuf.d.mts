export function encode(input:unknown,codec:string):Uint8Array<ArrayBuffer>;
export function decodeNative(input:Uint8Array,codec:string):unknown;
export function adapt(input:unknown,codec:string):unknown;
export function decode(input:Uint8Array,codec:string):unknown;
