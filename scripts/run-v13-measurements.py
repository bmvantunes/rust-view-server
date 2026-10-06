"""Fixed 75-run, alternating-order actual-pipeline collection. No parallel builds/tests."""
from pathlib import Path
import json,subprocess,os,time,hashlib
r=Path(__file__).resolve().parent.parent;builds=json.loads((r/'evidence/v13/candidate-builds.json').read_text())['candidates'];roots={b['codec']:b['root'] for b in builds};records=[]
rule=hashlib.sha256((r/'CODEC-DECISION-RULE.md').read_bytes()).hexdigest();start=time.time_ns()
for repeat in range(5):
 order=['json','protobuf','msgpack'] if repeat%2==0 else ['msgpack','protobuf','json']
 for large,distribution in [(False,'mixed'),(True,'integers'),(True,'decimals'),(True,'strings'),(True,'mixed')]:
  for codec in order:
   name=f'pipeline-{codec}-{distribution}-'+('large' if large else 'compat')+f'-{repeat}'
   assert not (r/('evidence/v13/'+name+'.json')).exists(),'Do not overwrite collected measurements'
   env=dict(os.environ,V13_CANDIDATE_ROOT=roots[codec],V13_CODEC=codec,V13_REPEAT=str(repeat),V13_DISTRIBUTION=distribution,V13_LARGE='1' if large else '0')
   with (r/('evidence/v13/'+name+'.gate.log')).open('w') as f:p=subprocess.run(['node','scripts/profile-v13-pipeline.mjs'],cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT)
   records.append({'name':name,'exit':p.returncode});print(records[-1],flush=True)
   (r/'evidence/v13/measurement-collection.json').write_text(json.dumps({'status':'running' if p.returncode==0 else 'failed','started_ns':start,'rule_sha256':rule,'records':records},indent=2)+'\n')
   if p.returncode:raise RuntimeError(name)
assert hashlib.sha256((r/'CODEC-DECISION-RULE.md').read_bytes()).hexdigest()==rule
(r/'evidence/v13/measurement-collection.json').write_text(json.dumps({'status':'complete','started_ns':start,'finished_ns':time.time_ns(),'rule_sha256':rule,'records':records},indent=2)+'\n')
subprocess.run(['node','scripts/verify-v13-measurements.mjs'],cwd=r,check=True)
