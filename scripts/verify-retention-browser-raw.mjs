import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';
const dir=process.argv[2],requiredHelpers=process.argv.includes('--helpers'),read=n=>JSON.parse(fs.readFileSync(path.join(dir,n),'utf8'));
const c=read('case-initial.json'),inputs=read('source-records.json'),events=read('browser-events.json'),config=read('configuration.json');
const gate=fs.readFileSync(new URL('./retention-browser-gate.js',import.meta.url),'utf8');const body=gate.slice(gate.indexOf('function groupId('),gate.indexOf('async function verifyStage('));const {oracle}=new Function(body+';return {oracle};')();
const stable=v=>JSON.stringify(v,(_k,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.entries(x).sort(([a],[b])=>a.localeCompare(b))):x);const checked=[];
for(const event of events){if(!event.raw||!event.health)continue;const h=event.health;const rows={};
 for(const source of config.sources){const current=new Map(),age=source.retention.maxRetentionMinutes*60000;const health=h.sources.find(s=>s.topic===source.topic);const next=Object.fromEntries(health.partitions.map(p=>[p.partition,Number(p.durable_next)]));let order=0;
  for(const {input:v,ack}of inputs){if(v.topic!==source.topic||ack.offset>=next[v.partition])continue;assert.equal(v.timestamp_ms,ack.timestamp_ms);for(const[k,r]of current)if(r.origin+age<=v.timestamp_ms)current.delete(k);current.set(ack.key,{row:{...v.row,rowId:ack.key},origin:v.timestamp_ms,order:++order});if(source.retention.maxRetentionMessages)while(current.size>source.retention.maxRetentionMessages){const oldest=[...current].sort((a,b)=>a[1].order-b[1].order)[0][0];current.delete(oldest);}}
  for(const[k,r]of current)if(r.origin+age<=h.sampled_at_unix_ms)current.delete(k);rows[source.topic]=[...current.values()].map(r=>r.row);
 }
 c.stages.recomputed=rows;const expectations={};
 for(const[name,definition]of Object.entries(c.definitions)){const expected=oracle(name,definition,c,'recomputed');expectations[name]=expected;const observed=event.raw.observed;for(const surface of ['latest',...(requiredHelpers?['helpers']:[])]){const value=observed[surface]?.[name];assert.ok(value,event.stage+' missing '+surface);assert.equal(value.status,'ready');assert.equal(value.totalRows,expected.length);assert.equal(stable(value.rows),stable(expected),event.stage+' '+name+' '+surface);}
  assert.equal(stable(observed.windows[name].rows),stable(Object.fromEntries(expected.slice(0,2).map((row,i)=>[String(i),row]))),event.stage+' sink '+name);
 }
 checked.push({stage:event.stage,sourceRows:Object.fromEntries(Object.entries(rows).map(([t,r])=>[t,r.length])),expected:expectations});
}
assert.equal(checked.length,6);const result={status:'PASS',scope:'Independent fold of raw producer inputs, timestamps, source NEXT and observation time; rowId keys independently checked by runner; raw/grouped all-six aggregates, totals, ranking and sink windows',helpersRequired:requiredHelpers,cuts:checked};fs.writeFileSync(path.join(dir,'independent-browser-oracle.json'),JSON.stringify(result,null,2));console.log(JSON.stringify({status:'PASS',cuts:checked.length,helpers:requiredHelpers}));
