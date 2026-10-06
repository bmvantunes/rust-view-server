import {readFile,writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import assert from 'node:assert/strict';
import {root,hash} from './v121-browser-support.mjs';
import {verifyLedger,verifyVersions} from './v121-oracle.mjs';
const raw=JSON.parse(await readFile(join(root,'evidence/v12.1/browser-profile.json')));
assert.equal(raw.status,'passed');assert.equal(raw.release_binary_sha256,await hash(join(root,'bin/view_server')));
for(const [p,digest] of Object.entries(raw.source_hashes))assert.equal(await hash(join(root,p)),digest,p);
assert.deepEqual(verifyLedger(raw.ledger,raw.cuts),raw.oracle);assert(raw.oracle.live>200);
const versions=verifyVersions(raw.ledger,raw.server_events,raw.cuts);
const negatives=[];
for(const field of ['quantity','order','total_rows','start_rank','version','query_generation','sequence','acquisition']){
 const changed=structuredClone(raw.ledger);const frame=changed.find(e=>e.type==='receive'&&Object.values(e.message.results??{}).some(r=>r.rows.length>=2));const result=Object.values(frame.message.results).find(r=>r.rows.length>=2);
 if(field==='quantity')result.rows[0].quantity='0';else if(field==='order')result.rows.reverse();else if(field==='acquisition')result.remote.acquisition++;else result[field]++;
 assert.throws(()=>{verifyLedger(changed,raw.cuts);verifyVersions(changed,raw.server_events,raw.cuts);},undefined,'oracle accepted '+field+' poisoning');negatives.push(field);
}
const send=new Map(),settled=new Set(),durations=[];
for(const e of raw.ledger){const id=e.worker+':'+e.message.id;if(e.type==='send')send.set(id,e.mainThreadNs);else if(['ack','request_error'].includes(e.message.type)){assert(!settled.has(id),'duplicate settlement');settled.add(id);assert(send.has(id));const ns=e.mainThreadNs-send.get(id);assert(Number.isSafeInteger(ns)&&ns>=0);durations.push(ns);}}
const peers=raw.profile.filter(p=>p.state==='profile_peer'),sources=raw.profile.filter(p=>p.state==='profile_source');
for(const p of peers){assert(p.queue_peak_frames<=86);assert(p.queue_peak_bytes<=8388608);for(const k of ['encoded_bytes','encode_ns','queue_residence_sum_ns','socket_send_call_ns'])assert(Number.isSafeInteger(p[k])&&p[k]>=0);}
for(const s of sources)for(const k of ['admission_ns','durability_ns','reconciliation_ns','grouped_extraction_ns','source_to_enqueued_ns'])assert(Number.isSafeInteger(s[k])&&s[k]>=0);
assert(sources.length>=120);assert(raw.resources.length>1);assert(raw.resources.every(v=>Number.isInteger(v.rssKiB)&&v.rssKiB>0));
const quantile=(values,numerator,denominator)=>{const sorted=values.toSorted((a,b)=>a-b);return sorted[Math.ceil(sorted.length*numerator/denominator)-1];};
const phase={};for(const s of raw.samples)(phase[s.phase]??=[]).push(s.node_boundary_ns);
const report={status:'passed',raw_sha256:await hash(join(root,'evidence/v12.1/browser-profile.json')),binary_sha256:raw.release_binary_sha256,oracle:raw.oracle,versions,oracle_poisoning_rejected:negatives,worker_request_to_main_receipt:{count:durations.length,p50_ns:quantile(durations,1,2),p95_ns:quantile(durations,95,100),max_ns:Math.max(...durations)},node_phase_ns:Object.fromEntries(Object.entries(phase).map(([k,v])=>[k,{count:v.length,p50:quantile(v,1,2),max:Math.max(...v)}])),rss_peak_kib:Math.max(...raw.resources.map(v=>v.rssKiB)),actual_encoded_bytes:peers.reduce((a,p)=>a+p.encoded_bytes,0),queue_peak_frames:Math.max(...peers.map(p=>p.queue_peak_frames)),queue_peak_bytes:Math.max(...peers.map(p=>p.queue_peak_bytes)),boundaries:raw.boundaries};
await writeFile(join(root,'evidence/v12.1/profile-verification.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
