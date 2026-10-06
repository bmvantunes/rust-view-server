"""Seal explicitly FAILED V13 experimental work, never certify a production migration.

The normal package-v13.py still refuses this state. This command requires every
preserved baseline gate to have executed successfully in the current snapshot,
and requires the specific reproduced candidate admission regression to remain red.
"""
from pathlib import Path
import json,zipfile,tempfile,shutil
import acceptance_v13 as a

root=Path(__file__).resolve().parent.parent
with a.lock(root):
 state=a.read_json(root/'evidence/v13/validation.json')
 assert state['policy']==a.POLICY and state['status']=='failed' and state['reused']==0
 assert state['error']=='Gate failed: candidate-qualification'
 run=root/'evidence/v13/runs'/state['run_id']
 assert a.read_json(run/'validation.json')==state
 manifest=a.read_json(run/'inputs.json');a.unchanged(root,manifest)
 assert a.fingerprint(manifest)==state['input_fingerprint']
 assert state['baseline_sha256']==a.baselines(root)
 assert [g['gate'] for g in state['gates']]==[n for n,_ in a.GATES[:37]]
 assert state['not_run']==[n for n,_ in a.GATES[37:]]
 for i,(result,(name,command)) in enumerate(zip(state['gates'],a.GATES)):
  assert result==a.read_json(run/(name+'.json'))
  assert result['command']==command and result['run_id']==state['run_id'] and result['input_fingerprint']==state['input_fingerprint']
  assert result['status']=='executed' and result['exit']==(1 if i==36 else 0)
  assert a.sha(run/(name+'.log'))==result['log_sha256']
  assert result['finished_ns']>=result['started_ns']
 for name,h in state['artifacts'].items():assert a.sha(run/name)==h,name
 for p,k in [('bin/view_server','service_sha256'),('bin/view_server_faults','fault_service_sha256'),(a.WASM,'wasm_sha256')]:assert a.sha(root/p)==state[k]
 for p,h in state['browser_sha256'].items():assert a.sha(root/p)==h
 identities=a.read_json(root/'V13-ARTIFACT-IDENTITIES.json');assert identities['run_id']==state['run_id']
 assert identities['sha256']=={'bin/view_server':state['service_sha256'],'bin/view_server_faults':state['fault_service_sha256'],a.WASM:state['wasm_sha256'],**state['browser_sha256']}
 q=run/'generated/evidence/v13'
 admission=a.read_json(q/'query-admission.json')
 assert admission['status']=='failed' and admission['run_id']==state['run_id']
 assert admission['records']==[{'codec':'json','exit':0},{'codec':'protobuf','exit':1},{'codec':'msgpack','exit':1}]
 for codec in ['json','protobuf','msgpack']:
  result=a.read_json(q/('query-admission-'+codec+'.json'))
  assert result['run_id']==state['run_id'] and result['finalZeroSubscriptions']
  assert [c['correct'] for c in result['cases']]==([True]*4 if codec=='json' else [True,False,False,False])
 archive=root/(a.PREFIX+'v13.zip');sidecar=Path(str(archive)+'.sha256')
 assert not archive.exists() and not sidecar.exists(),'Never overwrite a sealed delivery'
 files=[]
 for p in a.walk(root):
  name=p.relative_to(root).as_posix()
  if '.zip' in p.name or ('/' not in name and name.endswith('.sha256')):continue
  if name in ['evidence/v13/.lock','evidence/v13/package-result.json']:continue
  if name.split('/')[0] in {'logs','evidence'} and not name.startswith('evidence/v13/'):continue
  if '/' in name and name.split('/')[0] not in a.TREES:continue
  assert not p.is_symlink() and not p.name.startswith('.env') and not p.name.endswith(('-wal','-shm'))
  files.append((name,p))
 with tempfile.TemporaryDirectory(prefix='v13-partial-package-') as d:
  stage=Path(d);entries={}
  for name,p in files:
   dest=stage/name;dest.parent.mkdir(parents=True,exist_ok=True);a.private_copy(p,dest);entries[name]=a.sha(dest)
  a.unchanged(stage,manifest);a.unchanged(root,manifest)
  output=stage/'delivery.zip'
  with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6,strict_timestamps=False) as z:
   for name in sorted(entries):z.write(stage/name,name)
   z.writestr('evidence/v13/manifest.sha256',''.join(h+'  '+name+'\n' for name,h in sorted(entries.items())))
  with zipfile.ZipFile(output) as z:
   assert z.testzip() is None
   for name,h in entries.items():assert a.digest(z.read(name))==h
  a.unchanged(root,manifest)
  with archive.open('xb') as f:shutil.copyfileobj(output.open('rb'),f)
 digest=a.sha(archive)
 with sidecar.open('x') as f:f.write(digest+'  '+archive.name+'\n')
 receipt={'status':'partial-unqualified-no-production-switch','archive':str(archive),'sha256':digest,'run_id':state['run_id'],'manifest_entries':len(entries),**{k:state[k] for k in ['input_fingerprint','service_sha256','fault_service_sha256','wasm_sha256','browser_sha256']}}
 a.write_json(root/'evidence/v13/package-result.json',receipt);print(json.dumps(receipt,indent=2))
