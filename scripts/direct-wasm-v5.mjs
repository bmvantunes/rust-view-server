import fs from 'node:fs';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const root = process.argv[2] ?? path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../checkpoint-v3');
const bytes = fs.readFileSync(`${root}/browser/public/product_core.wasm`);
const { instance } = await WebAssembly.instantiate(bytes, {});
const e = instance.exports;
const read = (p, l) => new TextDecoder().decode(new Uint8Array(e.memory.buffer, p, l));
const withInput = (text, fn) => {
  const bytes = new TextEncoder().encode(text), p = e.product_core_alloc(bytes.length);
  if (!p) throw Error('allocation failed');
  new Uint8Array(e.memory.buffer, p, bytes.length).set(bytes);
  try { return fn(p, bytes.length); } finally { e.product_core_dealloc(p, bytes.length); }
};
const makeCore = () => {
  const h = e.product_core_new();
  const call = (fn, text) => {
    const status = withInput(text, (p,l) => e[fn](h,p,l));
    if (status) throw Error(read(e.product_core_error_ptr(h),e.product_core_error_len(h)));
  };
  return {
    apply(c) { call('product_core_apply', JSON.stringify(c)); },
    result(s) { call('product_core_result', s); return JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h))); },
    stats() { assert.equal(e.product_core_stats(h),0); return JSON.parse(read(e.product_core_output_ptr(h),e.product_core_output_len(h))); },
    free() { e.product_core_free(h); }
  };
};
const row = (id, coefficient, scale=0, category='c0') => ({command:'upsert',row:{id,category,quantity:'9007199254740993',amount:{coefficient:String(coefficient),scale}}});
const query = (offset=0, limit=10, direction='ascending') => ({where_expr:{op:'true'},direction,offset,limit});
const ids = (c,s='q')=>c.result(s).rows.map(r=>r.id);
const report = {};
{
 const c=makeCore(); const corpus=JSON.parse(fs.readFileSync(`${root}/fixtures/product-core-100.json`));
 for(const cmd of corpus.commands) c.apply(cmd);
 report.corpus={};
 for(const name of ['all','c0']) {
  const r=c.result(name), expected=corpus.expect[name];
  assert.deepEqual(r.rows.map(x=>x.id),expected.ids);
  assert.equal(r.total_rows,expected.total_rows); assert.equal(r.version,expected.version);
  report.corpus[name]={ids:r.rows.map(x=>x.id),total:r.total_rows,version:r.version};
 }
 c.free();
}
{
 const c=makeCore(); c.apply(row('minus-one','-1')); c.apply(row('minus-one-point-zero-one','-101',2));
 c.apply({command:'open',subscription:'q',query:query()});
 report.negativeDecimalSort={expected:['minus-one-point-zero-one','minus-one'],actual:ids(c),rows:c.result('q').rows}; c.free();
}
{
 const c=makeCore(); c.apply(row('a',1));c.apply(row('b',1));
 c.apply({command:'open',subscription:'q',query:query(0,10,'descending')});
 report.descendingEqualAmounts={actual:ids(c),expectedCanonicalIdAscending:['a','b']};c.free();
}
{
 const c=makeCore();for(let i=0;i<10;i++)c.apply(row(`p${i}`,i));
 c.apply({command:'open',subscription:'q',query:query(9,3)});
 report.offsetNearEnd={requestedOffset:9,requestedLimit:3,total:10,actual:ids(c)};
 c.apply({command:'change_window',subscription:'q',offset:99,limit:3});
 report.offsetBeyondEnd={requestedOffset:99,requestedLimit:3,total:10,actual:ids(c)};c.free();
}
{
 const c=makeCore();for(let i=0;i<10;i++)c.apply(row(`p${i}`,i));
 const initial=query(0,3);c.apply({command:'open',subscription:'q',query:initial});
 c.apply({command:'change_window',subscription:'q',offset:5,limit:3});
 const afterWindow=ids(c);
 c.apply({command:'change_query',subscription:'q',query:initial});
 report.restoreOriginalQueryAfterWindow={afterWindow,afterRestore:ids(c),expectedAfterRestore:['p0','p1','p2']};c.free();
}
{
 const c=makeCore();for(let i=0;i<10;i++)c.apply(row(`p${i}`,i));
 c.apply({command:'open',subscription:'q',query:query(0,3)});
 let firstError;try {c.apply({command:'change_window',subscription:'q',offset:0,limit:0});}catch(e){firstError=e.message;}
 const afterError=c.result('q');
 let nextError;try {c.apply(row('new-row',20));}catch(e){nextError=e.message;}
 report.zeroLimitFailure={firstError,afterError,nextError,afterNext:c.result('q')};c.free();
}
{
 const c=makeCore();c.apply(row('p0',0));c.apply({command:'open',subscription:'q',query:query()});
 let error;try {c.apply({command:'open',subscription:'q',query:query()});}catch(e){error=e.message;}
 report.duplicateOpen={error};
 const before=c.stats();c.apply({command:'delete',id:'p0'});const after=c.stats();report.deleteCounters={before,after};c.free();
}
console.log(JSON.stringify(report,null,2));
assert.deepEqual(report.negativeDecimalSort.actual, report.negativeDecimalSort.expected);
assert.deepEqual(report.descendingEqualAmounts.actual, report.descendingEqualAmounts.expectedCanonicalIdAscending);
assert.deepEqual(report.offsetNearEnd.actual, ['p9']);
assert.deepEqual(report.offsetBeyondEnd.actual, []);
assert.deepEqual(report.restoreOriginalQueryAfterWindow.afterRestore, report.restoreOriginalQueryAfterWindow.expectedAfterRestore);
assert.equal(report.zeroLimitFailure.firstError, undefined);
assert.equal(report.zeroLimitFailure.nextError, undefined);
assert.equal(report.zeroLimitFailure.afterNext.total_rows, 11);
assert.deepEqual(report.zeroLimitFailure.afterNext.rows, []);
assert.match(report.duplicateOpen.error, /already open/);
