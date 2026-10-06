"""Verify fixed P/L matrix, exact counters/oracles, raw quantiles, and both source bindings."""
from pathlib import Path
import hashlib,json,math,re,zipfile
from v11_counter_overlay import overlay,NAMES
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v11/measurements'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quantiles(values):
 values=sorted(values);return {k:values[math.ceil(q*len(values))-1] for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]}
def verify():
 archive=root/'rust-differential-product-20260929-review-checkpoint-v10.zip';assert sha(archive)=='621193770c1869e49aa4d660a08543c958e807e591ab615899c5c29db7574cb3'
 with zipfile.ZipFile(archive) as z:
  for name in NAMES:assert overlay(name,z.read(name).decode())==(out/('v10-'+Path(name).stem+'-counter-overlay.txt')).read_text()
  baseline={name:hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist() if name.startswith(('native/','ingestion/')) and (name.endswith('.rs') or Path(name).name in ['Cargo.toml','Cargo.lock'])}
  for name in NAMES:baseline[name]=sha(out/('v10-'+Path(name).stem+'-counter-overlay.txt'))
  baseline['ingestion/examples/v11_measure.rs']=sha(root/'ingestion/examples/v11_measure.rs')
 actual={p.relative_to(root).as_posix():sha(p) for folder in ['native','ingestion'] for p in (root/folder).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/folder).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
 builds={label:json.loads((out/(label+'-build.json')).read_text()) for label in ['v10','v11']}
 for label,build in builds.items():
  assert build['implementation_sha256']==(actual if label=='v11' else baseline),'Measured implementation differs: '+label
  assert build['harness_sha256']==sha(root/'ingestion/examples/v11_measure.rs') and build['exit']==0
 groups={};ends={};total=0
 for phase in ['baseline','small','large']:
  meta=json.loads((out/(phase+'-runs.json')).read_text());assert meta['finished_ns']>meta['started_ns'];assert len(meta['jobs'])==len(meta['commands']);assert meta['seed']==90210
  combos=[(1,1),(16,1),(16,16),(256,1),(256,256)]
  if phase=='baseline':expected={('v10',p,l,1,'dense',0) for p,l in combos}
  elif phase=='small':expected={(v,p,l,c,'dense',r) for v in builds for p,l in combos for c in [1,32] for r in range(2)}|{(v,16,16,c,'sparse',r) for v in builds for c in [1,32] for r in range(2)}
  else:expected={(v,16,16,256,m,r) for v in builds for m in ['dense','sparse'] for r in range(2)}
  assert {tuple(j) for j in meta['jobs']}==expected and len(expected)==len(meta['jobs'])
  for job,cmd in zip(meta['jobs'],meta['commands']):
   v,p,l,c,mode,rep=job;assert cmd['exit']==0 and cmd['binary_sha256']==builds[v]['binary_sha256']
   raw=[json.loads(line) for line in (out/(cmd['name']+'.jsonl')).read_text().splitlines()];setup=raw[0];samples=raw[1:-1];end=raw[-1];assert len(samples)==32 and setup['samples']==32 and setup['warmup_batches']==8
   assert (setup['P'],setup['L'],setup['H'],setup['rows'],setup['cap'],setup['mode'])==(p,l,256,10000,c,mode)
   assert setup['row_distribution']==[len(range(i,10000,p)) for i in range(p)] and min(setup['row_distribution'])>0
   key=(v,p,l,c,mode)
   if phase!='baseline':groups.setdefault(key,[]).extend(samples);ends.setdefault((p,l,c,mode),set()).add(end['full_recovery_sha256'])
   count=1 if mode=='sparse' else c
   assert end['records_committed']==40*count and end['batches_committed']==40
   for index,s in enumerate(samples):
    assert s['sample']==index and s['oracle'] is True and s['records']==count and s['batches']==1 and s['batch_sizes']==[count]
    assert len(s['record_latency_ns'])==len(s['record_wait_ns'])==count
    assert all(lat>=wait for lat,wait in zip(s['record_latency_ns'],s['record_wait_ns']))
    assert s['source_to_result_ns']>=s['service_ns'] and s['queue_bytes']<=2*1024*1024 and s['building_bytes']<=s['queue_bytes']
    assert s['spill_bytes']==s['paused_ns']==0 # local harness; real SDK pressure is a different test
    assert 1<=s['K']<=count and s['target']<l
    if mode=='dense':assert s['queue_records_serialized']==2*c+1+(c*(c-1)//2 if v=='v10' else 0)
    for name,w in [(name,s[name]) for name in ['apply_work','query_work','authorize_work']]:
     assert w['full_scans']==w['reconstructions']==w['partition_scans']==0
     global_n,part_n={'apply_work':(2,2),'query_work':(4,4*l),'authorize_work':(1,1)}[name]
     assert w['global_records_validated']==global_n and w['partition_records_validated']==part_n
     assert w['global_history_entries_decoded']==256*global_n and w['partition_history_entries_decoded']==256*part_n
     assert w['partition_objects_read']==part_n and w['metadata_reads']==global_n+part_n
    assert s['query_work']['guarded_leases']==4*l and s['query_work']['sql_operations']==4*(l+3)
    assert s['apply_work']['receipt_coordinates_copied']==3*p and s['apply_work']['row_lookups']==s['K']
   resources=(out/(cmd['name']+'.resources.txt')).read_text();assert 'maximum resident set size' in resources and 'user' in resources and 'sys' in resources
   total+=len(samples)
 assert all(len(values)==1 for values in ends.values()),'Final complete Recovery differs between candidates/repetitions'
 summary=[]
 for (v,p,l,c,mode),samples in sorted(groups.items()):
  row={'candidate':v,'P':p,'L':l,'H':256,'cap':c,'mode':mode,'samples':len(samples),'records':sum(s['records'] for s in samples),'batches':sum(s['batches'] for s in samples)}
  for metric in ['durable_ns','reconciliation_ns','read_ns','authorize_ns','service_ns','source_to_result_ns','batch_build_ns']:
   row[metric.replace('_ns','_ms')]=quantiles([s[metric]/1e6 for s in samples])
  for metric in ['record_latency_ns','record_wait_ns']:
   row[metric.replace('_ns','_ms')]=quantiles([t/1e6 for s in samples for t in s[metric]])
  for metric in ['guard_validation_ns','guard_action_ns']:
   row[metric.replace('_ns','_ms')]=quantiles([s['query_work'][metric]/1e6 for s in samples])
  row['commit_ms']=quantiles([s['apply_work']['sqlite_commit_ns']/1e6 for s in samples])
  row['records_per_service_second']=row['records']/sum(s['service_ns']/1e9 for s in samples)
  row['batches_per_service_second']=row['batches']/sum(s['service_ns']/1e9 for s in samples)
  row['query_metadata_bytes']=quantiles([s['query_work']['metadata_bytes_decoded'] for s in samples]);row['queue_records_serialized']=quantiles([s['queue_records_serialized'] for s in samples])
  summary.append(row)
 return {'runs':61,'oracle_samples':total,'cells':summary,'quantiles':'nearest rank; 64 per cell, p99=max; per-record samples within batches are correlated'}
if __name__=='__main__':
 summary=verify()
 expected=json.loads((out/'summary.json').read_text())
 assert summary==expected,'Summary does not match raw measurements'
 print(f"{summary['runs']} release processes / {summary['oracle_samples']} oracle samples; P/L/history/work/complete Recovery/source/harness bindings verified")
