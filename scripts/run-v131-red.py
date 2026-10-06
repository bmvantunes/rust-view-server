from pathlib import Path
import json,subprocess,os
root=Path(__file__).resolve().parent.parent
records=[]
for b in json.loads((root/'evidence/v13/candidate-builds.json').read_text())['candidates']:
 env=dict(os.environ,V13_CODEC=b['codec'],V13_CANDIDATE_ROOT=b['root'])
 with (root/('evidence/v13.1/red/query-admission-'+b['codec']+'.gate.log')).open('w') as f:
  p=subprocess.run(['node','scripts/test-v131-red.mjs'],cwd=root,env=env,stdout=f,stderr=subprocess.STDOUT)
 records.append({'codec':b['codec'],'exit':p.returncode})
result={'status':'passed' if all(r['exit']==0 for r in records) else 'failed','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'records':records}
(root/'evidence/v13.1/red/query-admission.json').write_text(json.dumps(result,indent=2)+'\n')
print(result)
assert result['status']=='passed','candidate query admission/lifetime regression'
