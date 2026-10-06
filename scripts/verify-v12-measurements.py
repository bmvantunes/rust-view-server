from pathlib import Path
import hashlib,json,math
from measurement_v12 import rate
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v12/measurements'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def quantiles(values):
 values=sorted(values);return {k:values[math.ceil(q*len(values))-1] for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]}
def verify():
 manifest=json.loads((out/'runs.json').read_text());source={p.relative_to(root).as_posix():sha(p) for d in ['native','ingestion'] for p in (root/d).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/d).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])};assert source==manifest['source'],'source binding'
 assert [r['P'] for r in manifest['runs']]==[1,16,256];summary=[]
 for run in manifest['runs']:
  assert run['exit']==0 and run['finished_ns']>run['started_ns'];assert sha(out/run['raw'])==run['raw_sha256'],'raw bytes binding'
  raw=[json.loads(l) for l in (out/run['raw']).read_text().splitlines()];setup=raw[0];assert (setup['P'],setup['L'],setup['rows'],setup['H'])==(run['P'],run['P'],10000,256);samples=raw[1:];assert len(samples)==24
  for i in range(12):
   pair=samples[2*i:2*i+2];assert {s['grouped'] for s in pair}=={True,False};assert pair[0]['result_sha256']==pair[1]['result_sha256'];assert all(s['sample']==i and s['oracle'] is True and s['results']==4 and s['rows']==10048 and type(s['elapsed_ns']) is int and s['elapsed_ns']>0 for s in pair)
   for s in pair:
    guards=1 if s['grouped'] else 4;w=s['work'];assert w['global_records_validated']==guards and w['partition_records_validated']==guards*run['P'];assert w['partition_history_entries_decoded']==guards*run['P']*256;assert w['global_history_entries_decoded']==guards*256
  for grouped in [False,True]:
   selected=[s for s in samples if s['grouped']==grouped];summary.append(dict(P=run['P'],L=run['P'],grouped=grouped,samples=12,elapsed_ns=quantiles([s['elapsed_ns'] for s in selected]),results_rate=rate([s['results'] for s in selected],[s['elapsed_ns'] for s in selected]),metadata_bytes=selected[0]['work']['metadata_bytes_decoded'],result_bytes=selected[0]['result_bytes']))
 return summary
if __name__=='__main__':
 summary=verify();expected=out/'summary.json'
 if expected.exists():assert json.loads(expected.read_text())==summary,'exact summary'
 else:expected.write_text(json.dumps(summary,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
