from pathlib import Path
import subprocess,os,json,shutil
r=Path(__file__).resolve().parent.parent
builds=json.loads((r/'evidence/v13.1/candidate-builds.json').read_text())['candidates'];records=[]
for b in builds:
 codec=b['codec'];dest=Path(b['root']);env=dict(os.environ,V13_CODEC=codec,V13_CANDIDATE_ROOT=str(dest))
 output=r/'evidence/v13.1/lifecycle'/codec;output.mkdir(parents=True,exist_ok=True)
 for name in ['row-browser','integer-browser','exact-values','barriers','browser']:
  cmd=['node','scripts/test-v131-'+name+'.mjs'];log=output/(name+'.gate.log')
  with log.open('w') as f:p=subprocess.run(cmd,cwd=r,env=env,stdout=f,stderr=subprocess.STDOUT)
  record={'codec':codec,'gate':name,'exit':p.returncode};records.append(record);print(record,flush=True)
  if p.returncode:raise RuntimeError(str(record))
  evidence={'browser':'browser-profile','integer-browser':'integer-browser','row-browser':'row-browser','exact-values':'exact-values','barriers':'barriers'}[name]
  for ext in ['json','log']:shutil.copy2(r/('evidence/v13.1/'+evidence+'.'+ext),output/(evidence+'.'+ext))
(r/'evidence/v13.1/lifecycles.json').write_text(json.dumps({'status':'passed','records':records},indent=2)+'\n')
