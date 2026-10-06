from pathlib import Path
import os,subprocess,json,time
r=Path(__file__).resolve().parent.parent
result=r/'evidence/v13.1/candidate-qualification.json'
report={'status':'running','run_id':os.environ.get('ACCEPTANCE_RUN_ID'),'steps':[]}
def save():result.write_text(json.dumps(report,indent=2)+'\n')
def run(command,cwd=r,env=None):
 step={'command':command,'cwd':str(cwd),'codec':(env or {}).get('V13_CODEC'),'started_ns':time.time_ns()}
 process=subprocess.run(command,cwd=cwd,env=env)
 step.update(exit=process.returncode,finished_ns=time.time_ns());report['steps'].append(step);save()
 if process.returncode:raise RuntimeError(str(step))
save()
try:
 for cmd in [['python3','scripts/test-v131-source-isolation.py'],['node','scripts/test-v131-admission.mjs'],['python3','scripts/audit-v131-libraries.py'],['node','scripts/test-v131-semantic-family.mjs'],['node','scripts/test-v131-codecs.mjs'],['python3','scripts/run-v131-sockets.py'],['python3','scripts/run-v131-lifecycles.py']]:run(cmd)
 for b in json.loads((r/'evidence/v13.1/candidate-builds.json').read_text())['candidates']:
  env=dict(os.environ,V13_CODEC=b['codec'],V13_CANDIDATE_ROOT=b['root'])
  run(['node','scripts/test-v131-protocol.mjs'],env=env)
  run(['node','scripts/test-v131-admission-lifetimes.mjs'],env=env)
  run([str(r/'browser/node_modules/.bin/tsc'),'--noEmit'],cwd=Path(b['root'])/'browser',env=env)
 run(['python3','scripts/run-v131-query-admission.py'])
 report.update(status='passed',candidates=['json','protobuf','msgpack'],scope='native socket, mounted browser, actual Worker manual schedules, types, hostile bidirectional codecs, shared admission and independent semantic family');save()
except BaseException as error:
 report.update(status='failed',error=str(error));save();raise
