"""Partition scaling with an unchanged common release harness. Baseline runs precede storage edits."""
from pathlib import Path
import hashlib,json,os,subprocess,tempfile,math,platform,sys,shutil
root=Path(__file__).resolve().parent.parent
out=root/'evidence/v10/measurements'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def implementation():return {p.relative_to(root).as_posix():sha(p) for folder in ['native','ingestion'] for p in (root/folder).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/folder).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
label=sys.argv[1];assert label in ['v9','v10']
binary=Path('/private/tmp/v10-measure-'+label)
shutil.copy2('/private/tmp/v10-measure-target/release/examples/v10_measure',binary)
meta={'candidate':label,'machine':platform.platform(),'binary_sha256':sha(binary),'harness_sha256':sha(root/'ingestion/examples/v10_measure.rs'),'implementation_sha256':implementation() if label=='v10' else {},'baseline_archive_sha256':sha(root/'rust-differential-product-20260929-review-checkpoint-v9.zip'),'repetitions':2,'rows':[10000,20000],'partitions':[1,16,256],'caps':[1,32],'history':256,'samples':32,'warmup':16,'seed':90210,'profile':'release','durability':'WAL FULL fullfsync ON checkpoint_fullfsync ON autocheckpoint 1000','commands':[]}
for cmd in [['rustup','run','1.96.1','rustc','-Vv'],['rustup','run','1.96.1','cargo','-V'],['sysctl','-n','hw.memsize'],['sysctl','-n','machdep.cpu.brand_string']]:
 r=subprocess.run(cmd,text=True,capture_output=True);meta['commands'].append({'argv':cmd,'exit':r.returncode,'output':r.stdout+r.stderr})
summary=[]
# Bounded larger row matrix; P is the primary independent variable.
for n in [10000,20000]:
 for p in [1,16,256]:
  for cap in [1,32]:
   for repeat in range(2):
    name=f'{label}-n{n}-p{p}-cap{cap}-r{repeat}'
    with tempfile.TemporaryDirectory(prefix='v10-db-') as tmp:
     cmd=['/usr/bin/time','-l',str(binary),str(Path(tmp)/'source.db'),str(n),str(cap),'90210',str(p)]
     r=subprocess.run(cmd,text=True,capture_output=True)
    (out/(name+'.jsonl')).write_text(r.stdout);(out/(name+'.resources.txt')).write_text(r.stderr)
    meta['commands'].append({'argv':cmd,'exit':r.returncode})
    (out/(label+'-metadata.json')).write_text(json.dumps(meta,indent=2)+'\n')
    assert r.returncode==0,r.stderr
    records=[json.loads(l) for l in r.stdout.splitlines()]; samples=[x for x in records if x['kind']=='sample'];assert len(samples)==32
    entry={'candidate':label,'rows':n,'partitions':p,'cap':cap,'repeat':repeat,'samples':len(samples)}
    for metric in ['available_ns','durable_ns','reconciliation_ns','guard_ns','broker_ns','batch_build_ns']:
     values=sorted(x[metric]/1e6 for x in samples)
     entry[metric.replace('_ns','_ms')]={k:values[math.ceil(q*len(values))-1] for k,q in [('p50',.5),('p95',.95),('p99',.99),('max',1)]}
    entry['work']=samples[-1]['work'];entry['storage']=records[-1]['storage']
    summary.append(entry);(out/(label+'-summary.json')).write_text(json.dumps(summary,indent=2)+'\n');print(name,entry['durable_ms'],flush=True)
