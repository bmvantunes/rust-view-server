"""Bounded same-toolchain release comparison; never changes an accepted archive.
Run after correctness. Exact fixture harness added to a disposable baseline only.
"""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,tempfile,time,zipfile,math
root=Path(__file__).resolve().parent.parent
out=root/'evidence/v9/measurements';out.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def command(argv,**kw):
 r=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,**kw);return {'argv':argv,'exit':r.returncode,'output':r.stdout}
metadata={'machine':platform.platform(),'seed':90210,'repetitions':2,'rows':[1000,10000],'caps':[1,32],'samples_per_run':64,'profile':'release','features':'default (SQLite, no Kafka network in timed harness)','durability':'WAL / FULL / fullfsync ON / checkpoint_fullfsync ON / auto-checkpoint 1000','baseline_archive_sha256':sha(root/'rust-differential-product-20260929-review-checkpoint-v8.1.zip'),'harness_sha256':sha(root/'ingestion/examples/v9_measure.rs'),'rustflags':os.environ.get('RUSTFLAGS',''),'commands':[],'baseline_instrumentation':'unchanged accepted durable/engine metrics; no new row counters injected','quantiles':'nearest rank, ceil(p*n)-1','boundary':'apply durable transaction + engine completion + three guarded observable reads; broker authorization checked just after timing; input construction separately timed; synchronous queue wait 0','cpu_rss':'time -l process including bootstrap, independent full-sort oracles and output, not just timed intervals','cold_restore':'new connection and engine after seed; OS cache not evicted; no hardware cold-cache claim'}
metadata['implementation_sha256']={p.relative_to(root).as_posix():sha(p) for folder in ['native','ingestion'] for p in (root/folder).rglob('*') if p.is_file() and 'target' not in p.relative_to(root/folder).parts and (p.suffix=='.rs' or p.name in ['Cargo.toml','Cargo.lock'])}
assert metadata['baseline_archive_sha256']=='901f7c5959e856c8002b11b40b621c57982d5eaa72a6228ac948a7f6c0966811'
for argv in [['rustup','run','1.96.1','rustc','-Vv'],['rustup','run','1.96.1','cargo','-V'],['sysctl','-n','hw.memsize'],['sysctl','-n','machdep.cpu.brand_string'],['df','-h',str(root)]]:metadata['commands'].append(command(argv))
env=dict(os.environ,RUSTC=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustc'],text=True).strip(),RUSTDOC=subprocess.check_output(['rustup','which','--toolchain','1.96.1','rustdoc'],text=True).strip(),CARGO_BUILD_JOBS='2',CARGO_TARGET_DIR=str(Path(tempfile.gettempdir())/'v9-release-measure-target'))
summaries=[]
with tempfile.TemporaryDirectory(prefix='v9-comparison-') as directory:
 temp=Path(directory);baseline=temp/'baseline';baseline.mkdir()
 with zipfile.ZipFile(root/'rust-differential-product-20260929-review-checkpoint-v8.1.zip') as z:
  for name in z.namelist():
   if name.startswith(('native/','ingestion/')):z.extract(name,baseline)
 shutil.copy2(root/'ingestion/examples/v9_measure.rs',baseline/'ingestion/examples/v9_measure.rs')
 binaries={}
 for label,tree in [('v8.1',baseline),('v9',root)]:
  argv=['rustup','run','1.96.1','cargo','build','--locked','--offline','--release','--manifest-path',str(tree/'ingestion/Cargo.toml'),'--example','v9_measure']
  result=command(argv,env=env);(out/(label+'-build.log')).write_text(result['output']);assert result['exit']==0,result['output']
  metadata['commands'].append({k:v for k,v in result.items() if k!='output'})
  target=temp/('measure-'+label);shutil.copy2(Path(env['CARGO_TARGET_DIR'])/'release/examples/v9_measure',target);binaries[label]=target
  metadata[label]={'binary_sha256':sha(target),'cargo_lock_sha256':sha(tree/'ingestion/Cargo.lock')}
 for n in [1000,10000]:
  # Bounded only: 15 GiB free at preflight; two temporary DBs per run, no scale escalation.
  for cap in [1,32]:
   for repeat in range(2):
    for label in (['v8.1','v9'] if repeat==0 else ['v9','v8.1']):
     name=f'{label}-n{n}-cap{cap}-r{repeat}'
     with tempfile.TemporaryDirectory(prefix='v9-db-') as dbdir:
      argv=['/usr/bin/time','-l',str(binaries[label]),str(Path(dbdir)/'source.db'),str(n),str(cap),'90210']
      started=time.time();r=subprocess.run(argv,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
      (out/(name+'.jsonl')).write_text(r.stdout);(out/(name+'.resources.txt')).write_text(r.stderr)
      metadata['commands'].append({'argv':argv,'exit':r.returncode,'wall_seconds':time.time()-started})
      (out/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
      assert r.returncode==0,r.stderr
      records=[json.loads(line) for line in r.stdout.splitlines()];samples=[v for v in records if v['kind']=='sample'];assert len(samples)==64
      values=sorted(v['available_ns']/1e6 for v in samples)
      summary={'candidate':label,'rows':n,'cap':cap,'repeat':repeat,'samples':len(values),'p50_ms':values[math.ceil(.5*len(values))-1],'p95_ms':values[math.ceil(.95*len(values))-1],'p99_ms':values[math.ceil(.99*len(values))-1],'max_ms':max(values),'process_wall_s':metadata['commands'][-1]['wall_seconds'],'batch_build_p50_ms':sorted(v['batch_build_ns']/1e6 for v in samples)[31],'restore_ns':records[0]['new_connection_engine_restore_ns'],'storage_start':records[0]['storage'],'storage_end':records[-1]['storage']}
      summaries.append(summary);print(json.dumps(summary),flush=True)
      (out/'summary.json').write_text(json.dumps(summaries,indent=2)+'\n')
 (out/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
