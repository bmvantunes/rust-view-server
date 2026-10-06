"""Verify every raw sample, fixed matrix, work counts and binding to the tested implementation."""
from pathlib import Path
import hashlib,json,math
root=Path(__file__).resolve().parent.parent;folder=root/'evidence/v10/measurements'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
actual={p.relative_to(root).as_posix():sha(p) for directory in ['native','ingestion'] for p in (root/directory).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/directory).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
# Verify that the baseline overlay adds counters only to the exact accepted implementation.
import zipfile
with zipfile.ZipFile(root/'rust-differential-product-20260929-review-checkpoint-v9.zip') as z:
 baseline=z.read('ingestion/src/durable.rs').decode()
baseline=baseline.replace('pub metadata_reads: u64,','pub metadata_reads: u64,\n    pub metadata_bytes_decoded: u64,\n    pub metadata_bytes_encoded: u64,\n    pub digest_bytes_hashed: u64,\n    pub partition_objects_read: u64,\n    pub partition_objects_written: u64,')
baseline=baseline.replace('if format != format_expected', 'work.metadata_bytes_decoded += payload.len() as u64;\n        work.digest_bytes_hashed += payload.len() as u64;\n        if format != format_expected')
baseline=baseline.replace('state.validate(source)?;\n        Ok(state)','work.partition_objects_read += state.partitions.len() as u64;\n        state.validate(source)?;\n        Ok(state)',1)
baseline=baseline.replace('work.bytes_encoded += bytes.len() as u64 + 32;', 'work.metadata_bytes_encoded += bytes.len() as u64;\n        work.digest_bytes_hashed += bytes.len() as u64;\n        work.partition_objects_written += state.partitions.len() as u64;\n        work.bytes_encoded += bytes.len() as u64 + 32;',1)
assert baseline==(folder/'v9-counter-overlay.rs.txt').read_text(),'Baseline changed beyond counters'
for label in ['v9','v10']:
 meta=json.loads((folder/(label+'-metadata.json')).read_text())
 if label=='v10':assert actual==meta['implementation_sha256'],'Measurement implementation changed'
 assert sha(root/'ingestion/examples/v10_measure.rs')==meta['harness_sha256']
 assert meta['baseline_archive_sha256']=='d2fe23ef4282e66a3ff4139be35a1303581026573f472b8a0e7133d4f4b6fc65'
 summary=json.loads((folder/(label+'-summary.json')).read_text());assert len(summary)==24
 assert {(s['rows'],s['partitions'],s['cap'],s['repeat']) for s in summary}=={(n,p,c,r) for n in [10000,20000] for p in [1,16,256] for c in [1,32] for r in [0,1]}
 for s in summary:
  name=f"{label}-n{s['rows']}-p{s['partitions']}-cap{s['cap']}-r{s['repeat']}"
  records=[json.loads(l) for l in (folder/(name+'.jsonl')).read_text().splitlines()];samples=[r for r in records if r['kind']=='sample'];assert len(samples)==32
  assert records[0]['partitions']==s['partitions'] and records[0]['rows']==s['rows']
  assert all(r['oracle']=='exact rows/order/totals/deep windows passed' for r in samples)
  for metric in ['available_ns','durable_ns','reconciliation_ns','guard_ns','broker_ns','batch_build_ns']:
   values=sorted(r[metric]/1e6 for r in samples)
   for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]:assert s[metric.replace('_ns','_ms')][k]==values[math.ceil(q*len(values))-1]
  for r in samples:
   w=r['work'];assert w['full_scans']==w['reconstructions']==0
   if label=='v10':
    assert w['partition_scans']==0 and w['partition_objects_read']==6 and w['partition_objects_written']==1
    assert w['metadata_reads']==12 and w['metadata_writes']==2
    assert w['metadata_bytes_encoded']<70000 and w['metadata_bytes_decoded']<420000
   else:assert w['partition_objects_read']==6*s['partitions'] and w['partition_objects_written']==s['partitions']
  resources=(folder/(name+'.resources.txt')).read_text();assert 'maximum resident set size' in resources and 'user' in resources and 'sys' in resources
 assert all(c['exit']==0 for c in meta['commands'])
print('48 release runs / 1536 exact-oracle samples; fixed partition matrix, work counters, current implementation and common harness verified')
