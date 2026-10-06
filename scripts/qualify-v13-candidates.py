from pathlib import Path
import os,subprocess,json
r=Path(__file__).resolve().parent.parent
result=r/'evidence/v13/candidate-qualification.json'
result.write_text(json.dumps({'status':'running','run_id':os.environ.get('ACCEPTANCE_RUN_ID')})+'\n')
try:
 cmds=[['python3','scripts/audit-v13-libraries.py'],['node','scripts/test-v13-semantic-family.mjs'],['node','scripts/test-v13-codecs.mjs'],['python3','scripts/run-v13-sockets.py'],['python3','scripts/run-v13-lifecycles.py']]
 for cmd in cmds:
  subprocess.run(cmd,cwd=r,check=True)
 for b in json.loads((r/'evidence/v13/candidate-builds.json').read_text())['candidates']:
  env=dict(os.environ,V13_CODEC=b['codec'],V13_CANDIDATE_ROOT=b['root'])
  subprocess.run(['node','scripts/test-v13-protocol.mjs'],cwd=r,env=env,check=True)
  # The same hook/provider type contracts are checked against each actual Worker.
  subprocess.run([str(r/'browser/node_modules/.bin/tsc'),'--noEmit'],cwd=Path(b['root'])/'browser',env=env,check=True)
 subprocess.run(['python3','scripts/run-v13-query-admission.py'],cwd=r,check=True)
 (r/'evidence/v13/candidate-qualification.json').write_text(json.dumps({'status':'passed','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'candidates':['json','protobuf','msgpack'],'scope':'native socket, mounted browser, actual Worker manual schedules, types, hostile bidirectional codecs and independent semantic family'},indent=2)+'\n')
except BaseException as error:
 result.write_text(json.dumps({'status':'failed','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'error':str(error)},indent=2)+'\n')
 raise
