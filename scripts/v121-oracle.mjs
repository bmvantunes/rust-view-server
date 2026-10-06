// Independent exact oracle: no WASM, native evaluator, index or shared comparator.
import assert from 'node:assert/strict';
export function normalized(row){const r=structuredClone(row);let n=BigInt(r.amount.coefficient),s=r.amount.scale;if(n===0n)s=0;while(n!==0n&&n%10n===0n){n/=10n;s--;}r.amount={coefficient:String(n),scale:s};r.quantity=String(BigInt(r.quantity));return r;}
function cmp(a,b){const s=Math.max(a.amount.scale,b.amount.scale);const x=BigInt(a.amount.coefficient)*10n**BigInt(s-a.amount.scale),y=BigInt(b.amount.coefficient)*10n**BigInt(s-b.amount.scale);return x<y?-1:x>y?1:a.id<b.id?-1:a.id>b.id?1:0;}
export function check(result,rows,q){let selected=rows.filter(r=>q.where_expr.op==='true'||r.category===q.where_expr.args.condition).map(normalized).sort(cmp);if(q.direction==='descending')selected.reverse();assert.equal(result.total_rows,selected.length);assert.equal(result.start_rank,q.offset);assert.deepEqual(result.rows,selected.slice(q.offset,q.offset+q.limit));return selected.length;}
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
   if(JSON.stringify(rows)!==JSON.stringify(priorRows))version++;
   priorRows=rows;for(const [key,s] of active)live.set(incarnation+':'+cut+':'+key,{version,...s});
  }
  if(e.state==='profile_command'){
   const c=e.command,key=e.connection+':'+c.subscription,old=active.get(key);let state;
   if(c.command==='close'){assert(old);active.delete(key);version++;continue;}
   // Successful bounded preflight allocates one private generation for every read command.
   nextGeneration++;
   if(c.command==='open'){assert(!old);version++;state={generation:++nextGeneration,sequence:0,q:c.query,acquisition:e.acquisition};}
   else if(c.command==='change_query'){
    assert(old);if(JSON.stringify(c.query)!==JSON.stringify(old.q)){version++;state={generation:++nextGeneration,sequence:0,q:c.query,acquisition:e.acquisition};}else state={...old,acquisition:e.acquisition};
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
