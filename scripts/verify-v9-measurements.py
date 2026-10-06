"""Bind bounded comparison samples to this exact implementation and common harness."""
from pathlib import Path
import hashlib,json,math
root=Path(__file__).resolve().parent.parent
folder=root/'evidence/v9/measurements'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads((folder/'metadata.json').read_text())
actual={p.relative_to(root).as_posix():sha(p) for directory in ['native','ingestion'] for p in (root/directory).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/directory).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
assert actual==meta['implementation_sha256'],'Measurement implementation changed'
assert sha(root/'ingestion/examples/v9_measure.rs')==meta['harness_sha256']
assert meta['baseline_archive_sha256']=='901f7c5959e856c8002b11b40b621c57982d5eaa72a6228ac948a7f6c0966811'
summary=json.loads((folder/'summary.json').read_text());assert len(summary)==16
expected={(v,n,c,r) for v in ['v8.1','v9'] for n in [1000,10000] for c in [1,32] for r in [0,1]}
assert {(s['candidate'],s['rows'],s['cap'],s['repeat']) for s in summary}==expected
for s in summary:
 name=f"{s['candidate']}-n{s['rows']}-cap{s['cap']}-r{s['repeat']}"
 records=[json.loads(line) for line in (folder/(name+'.jsonl')).read_text().splitlines()]
 samples=[r for r in records if r['kind']=='sample'];assert len(samples)==64
 assert all(r['oracle']=='exact rows/order/totals/deep windows passed' for r in samples)
 values=sorted(r['available_ns']/1e6 for r in samples)
 for label,p in [('p50_ms',.5),('p95_ms',.95),('p99_ms',.99)]:assert s[label]==values[math.ceil(p*len(values))-1]
 assert s['max_ms']==max(values)
 resources=(folder/(name+'.resources.txt')).read_text()
 assert 'maximum resident set size' in resources and 'user' in resources and 'sys' in resources
assert all(c['exit']==0 for c in meta['commands'])
print('16 bounded release runs, 1024 exact-oracle samples, same harness and current implementation verified')
