// Independent exact oracle: no WASM, native evaluator, index or shared comparator.
import assert from 'node:assert/strict';
import {isDeepStrictEqual} from 'node:util';
// Independent contract arithmetic. Canonicalization stops at the admitted scale
// floor; Rust canonical IDs compare UTF-8 bytes, not JavaScript UTF-16 code units.
// Match the existing ExactInteger parser's admitted ASCII decimal spellings.
// num-bigint permits underscores after the first digit, including repeated or
// trailing underscores. Do not narrow the product domain to JS BigInt syntax.
export function exactInteger(input){
 assert(typeof input==='string'&&input.length>0&&input.length<=10001,'integer length');
 assert(/^[+-]?[0-9][0-9_]*$/.test(input),'invalid exact integer');
 const canonical=String(BigInt(input.replaceAll('_','')));
 assert(canonical.length<=10001,'integer length');
 return canonical;
}
export function normalized(row){
 // Serde supplies Missing for an omitted label and ignores unknown struct fields.
 // Build only the admitted product fields; do not compare source JSON spelling.
 assert(typeof row.id==='string'&&typeof row.category==='string');
 const sourceLabel=Object.hasOwn(row,'label')?row.label:{state:'missing'};
 assert(sourceLabel&&['missing','null','value'].includes(sourceLabel.state),'invalid label');
 if(sourceLabel.state==='value')assert(typeof sourceLabel.value==='string','invalid label value');
 const label=sourceLabel.state==='value'?{state:'value',value:sourceLabel.value}:{state:sourceLabel.state};
 const r={id:row.id,category:row.category,label,quantity:row.quantity,amount:structuredClone(row.amount)};
 assert(Number.isInteger(r.amount.scale)&&Math.abs(r.amount.scale)<=10000);
 let n=BigInt(exactInteger(r.amount.coefficient)),s=r.amount.scale;
 if(n===0n)s=0;
 while(s>-10000&&n!==0n&&n%10n===0n){n/=10n;s--;}
 r.amount={coefficient:String(n),scale:s};r.quantity=exactInteger(r.quantity);return r;
}
function cmp(a,b,direction){
 const s=Math.max(a.amount.scale,b.amount.scale);
 const x=BigInt(a.amount.coefficient)*10n**BigInt(s-a.amount.scale);
 const y=BigInt(b.amount.coefficient)*10n**BigInt(s-b.amount.scale);
 const amount=x<y?-1:x>y?1:0;
 return (direction==='descending'?-amount:amount)||Buffer.compare(Buffer.from(a.id,'utf8'),Buffer.from(b.id,'utf8'));
}
export function check(result,rows,q){
 assert(q&&['ascending','descending'].includes(q.direction),'unsupported oracle direction');
 assert(Number.isSafeInteger(q.offset)&&q.offset>=0&&Number.isSafeInteger(q.limit)&&q.limit>=0,'unsupported oracle window');
 const expr=q.where_expr;
 assert(expr?.op==='true'||(expr?.op==='condition'&&expr.args?.field==='category_equals'&&typeof expr.args.condition==='string'),'unsupported oracle predicate');
 const selected=rows.filter(r=>q.where_expr.op==='true'||r.category===q.where_expr.args.condition)
  .map(normalized).sort((a,b)=>cmp(a,b,q.direction));
 assert.equal(result.total_rows,selected.length);assert.equal(result.start_rank,q.offset);
 const window=selected.slice(q.offset,q.offset+q.limit);
 if(q.projection){assert.deepEqual(result.keys,window.map(r=>r.id));assert.deepEqual(result.rows,window.map(r=>Object.fromEntries(q.projection.map(field=>[field,r[field]]))));}
 else assert.deepEqual(result.rows,window);
 return selected.length;
}
export function verifyLedger(events,cuts){
 const commands=new Map(),shapes=new Map(),queries=new Map();let checked=0,live=0;const connections=new Set();
 for(const event of events){
  const key=event.worker+':';
  if(event.type==='send'){const r=event.message;commands.set(key+r.id,r);if(r.command.command==='open'||r.command.command==='change_query')shapes.set(key+r.command.subscription+':'+r.acquisition,r.command.query);continue;}
  const m=event.message;if(!['ack','live'].includes(m.type))continue;
  for(const r of Object.values(m.results)){
   assert(r.remote);const meta=r.remote;connections.add(meta.incarnation+':'+meta.connection);assert.equal(m.acquisitions[r.subscription],meta.acquisition);assert(Number.isSafeInteger(r.version)&&r.version>=0);assert(Number.isSafeInteger(r.sequence));assert(Number.isSafeInteger(r.query_generation));
   const shapeKey=key+r.subscription+':'+meta.acquisition;
   let q=queries.get(shapeKey)??shapes.get(shapeKey);
   if(meta.requestId!==undefined){const request=commands.get(key+meta.requestId);assert(request);assert.equal(request.acquisition,meta.acquisition);if(request.command.command==='change_window')q={...q,offset:request.command.offset,limit:request.command.limit};else q=request.command.query;queries.set(shapeKey,q);}else live++;
   assert(q,`missing query for ${shapeKey}`);const rows=cuts[meta.sourceSequence];assert(rows,`missing cut ${meta.sourceSequence}`);check(r,rows,q);checked++;
  }
 }
 assert(checked>0);return {checked,live,connections:connections.size};
}
// Contract-level operation oracle, separate from the row/filter/order oracle above.
// Native's ordered operator log supplies operation order, not expected versions.
export function verifyVersions(events,serverEvents,cuts){
 let incarnation='',version=0,nextGeneration=0;const active=new Map(),commands=new Map(),live=new Map();
 let priorRows=[];
 for(const e of serverEvents){
  if(e.state==='ready'){incarnation=e.incarnation;version=0;nextGeneration=0;active.clear();priorRows=cuts[e.source_sequence];assert(priorRows);continue;}
  if(e.state==='source_committed'){
   const cut=String(e.offset+1);const rows=cuts[cut];assert(rows);
   const canonical=values=>values.map(normalized).sort((a,b)=>Buffer.compare(Buffer.from(a.id,'utf8'),Buffer.from(b.id,'utf8')));
   if(!isDeepStrictEqual(canonical(rows),canonical(priorRows)))version++;
   priorRows=rows;for(const [key,s] of active)live.set(incarnation+':'+cut+':'+key,{version,...s});
  }
  if(e.state==='profile_command'){
   const c=e.command,key=e.connection+':'+c.subscription,old=active.get(key);let state;
   if(c.command==='close'){assert(old);active.delete(key);version++;continue;}
   // Successful bounded preflight allocates one private generation for every read command.
   nextGeneration++;
   if(c.command==='open'){assert(!old);version++;state={generation:++nextGeneration,sequence:0,q:c.query,acquisition:e.acquisition};}
   else if(c.command==='change_query'){
    assert(old);if(!isDeepStrictEqual(c.query,old.q)){version++;state={generation:++nextGeneration,sequence:0,q:c.query,acquisition:e.acquisition};}else state={...old,acquisition:e.acquisition};
   }else{assert.equal(c.command,'change_window');assert(old);const changed=old.q.offset!==c.offset||old.q.limit!==c.limit;if(changed)version++;state={...old,sequence:old.sequence+(changed?1:0),q:{...old.q,offset:c.offset,limit:c.limit}};}
   active.set(key,state);commands.set(incarnation+':'+e.connection+':'+e.id,{version,...state});
  }
  if(e.state==='client_closed'){for(const key of [...active.keys()])if(key.startsWith(e.connection+':')){active.delete(key);version++;}}
 }
 let checked=0;
 for(const e of events)if(e.type==='receive'&&['ack','live'].includes(e.message.type))for(const r of Object.values(e.message.results)){
  const m=r.remote;const expected=m.requestId!==undefined?commands.get(m.incarnation+':'+m.connection+':'+m.requestId):live.get(m.incarnation+':'+m.sourceSequence+':'+m.connection+':'+r.subscription);
  assert(expected,`missing operation for ${JSON.stringify(m)}`);assert.equal(r.version,expected.version,'exact output version');assert.equal(r.query_generation,expected.generation,'exact query generation');assert.equal(r.sequence,expected.sequence,'exact navigation sequence');assert.equal(m.acquisition,expected.acquisition,'exact acquisition');checked++;
 }
 return {checked,status:'each ACK/live result is a completed ready snapshot; hook callback/error status checked separately'};
}
