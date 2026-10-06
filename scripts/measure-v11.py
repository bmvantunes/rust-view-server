"""Bounded serial measurements. Build both candidates first; no concurrent tests/builds."""
from pathlib import Path
import hashlib,json,os,platform,random,subprocess,sys,tempfile,time
root=Path(__file__).resolve().parent.parent;out=root/'evidence/v11/measurements'
phase=sys.argv[1];assert phase in ['baseline','small','large']
combos=[(1,1),(16,1),(16,16),(256,1),(256,256)]
if phase=='baseline': jobs=[('v10',p,l,1,'dense',0) for p,l in combos]
elif phase=='small':
 cells=[(p,l,c,'dense') for p,l in combos for c in [1,32]]+[(16,16,c,'sparse') for c in [1,32]]
 jobs=[];rng=random.Random(90210)
 for repeat in range(2):
  rng.shuffle(cells)
  for p,l,c,mode in cells:
   labels=['v10','v11'];rng.shuffle(labels)
   jobs.extend((label,p,l,c,mode,repeat) for label in labels)
else:
 # 256 admitted only after the small-run resource inspection recorded in large-admission.json.
 assert (out/'large-admission.json').exists()
 jobs=[(label,16,16,256,mode,r) for r in range(2) for mode in ['dense','sparse'] for label in (['v10','v11'] if r==0 else ['v11','v10'])]
meta={'phase':phase,'seed':90210,'platform':platform.platform(),'jobs':jobs,'commands':[],'started_ns':time.time_ns(),'no_concurrent_builds_or_tests':True,'durability':'WAL FULL fullfsync ON checkpoint_fullfsync ON autocheckpoint 1000','warmup_batches':8,'samples_per_process':32,'dense_deadline_ms':1000,'sparse_deadline_ms':4}
meta_path=out/(phase+'-runs.json');assert not meta_path.exists(),'Never overwrite completed measurement runs'
meta_path.write_text(json.dumps(meta,indent=2)+'\n')
for label,p,l,c,mode,r in jobs:
 name=f'{phase}-{label}-p{p}-l{l}-cap{c}-{mode}-r{r}'
 binary=Path('/private/tmp/v11-measure-'+label)
 build=json.loads((out/(label+'-build.json')).read_text());assert hashlib.sha256(binary.read_bytes()).hexdigest()==build['binary_sha256']
 with tempfile.TemporaryDirectory(prefix='v11-measure-db-') as tmp:
  cmd=['/usr/bin/time','-l',str(binary),str(Path(tmp)/'source.db'),str(p),str(l),str(c),mode]
  result=subprocess.run(cmd,text=True,capture_output=True,timeout=240)
 (out/(name+'.jsonl')).write_text(result.stdout);(out/(name+'.resources.txt')).write_text(result.stderr)
 meta['commands'].append({'name':name,'argv':cmd,'exit':result.returncode,'binary_sha256':build['binary_sha256']});meta_path.write_text(json.dumps(meta,indent=2)+'\n')
 assert result.returncode==0,result.stderr
 records=[json.loads(line) for line in result.stdout.splitlines()];assert len(records)==34 and all(s['oracle'] for s in records[1:-1]);print(name, 'setup_s',round(records[0]['setup_ns']/1e9,2),'read_ms',round(sum(s['read_ns'] for s in records[1:-1])/32e6,2),flush=True)
meta['finished_ns']=time.time_ns();meta_path.write_text(json.dumps(meta,indent=2)+'\n')
