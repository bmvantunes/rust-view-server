#!/usr/bin/env python3
"""Finite private local broker runner. Retains every attempt; no installed services."""
from pathlib import Path
import subprocess,os,json,time,uuid,signal,socket,sys
R=Path(__file__).resolve().parents[2];W=R/'work';old=Path('/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime');label='grouped-'+uuid.uuid4().hex[:8];rt=R/'runtime'/label;rt.mkdir(parents=True);out=W/'evidence/grouped'/label;out.mkdir();children=[]
node='/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin/node'
env={**os.environ,'JAVA_HOME':'/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home','KAFKA_HEAP_OPTS':'-Xms256m -Xmx512m','V12_SESSION_TOKEN':'configurable-local-test-token-000000000000','PATH':str(Path(node).parent)+':'+os.environ['PATH']}
def port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
ports={name:port() for name in ['broker','controller','query','health']}
def run(cmd):
 p=subprocess.run(list(map(str,cmd)),env=env,text=True,capture_output=True,timeout=120)
 if p.returncode:raise RuntimeError(p.stdout+p.stderr)
 return p.stdout
try:
 kafka=old/'kafka_2.13-4.1.0/bin';env['TOPICS_KAFKA_BIN']=str(kafka);props=(old/'broker.properties').read_text().replace('34492',str(ports['broker'])).replace('34493',str(ports['controller'])).replace(str(old/'broker-data'),str(rt/'broker-data'));(rt/'broker.properties').write_text(props)
 cluster=run([kafka/'kafka-storage.sh','random-uuid']).strip();(out/'format.log').write_text(run([kafka/'kafka-storage.sh','format','--standalone','-t',cluster,'-c',rt/'broker.properties']))
 log=open(out/'broker.log','w');broker=subprocess.Popen([str(kafka/'kafka-server-start.sh'),str(rt/'broker.properties')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);children.append((broker,log))
 end=time.monotonic()+60
 while 'Kafka Server started' not in (out/'broker.log').read_text():
  if broker.poll() is not None or time.monotonic()>end:raise RuntimeError('broker startup failed')
  time.sleep(.1)
 bindings=rt/'bindings.json';run([node,W/'scripts/generate-proto-source-config.mjs',bindings,'127.0.0.1:'+str(ports['broker']),label]);sources=[s for s in json.loads(bindings.read_text()) if s['topic']!='wide'];run([node,W/'examples/standalone/generate-config.mjs',rt/'standalone-bindings.json','127.0.0.1:'+str(ports['broker']),label]);sources+=json.loads((rt/'standalone-bindings.json').read_text());sources=[s for s in sources if s['topic'] in ['orders','positions','balances']];run([node,W/'examples/symbol-collisions/generate-config.mjs',rt/'collision-bindings.json','127.0.0.1:'+str(ports['broker']),label]);sources += [s for s in json.loads((rt/'collision-bindings.json').read_text()) if s['topic']=='catalog']
 for s in sources:
  if s['topic']=='orders':s['identity']['components']=[{'source':'key','field':'tenant'},{'source':'key','field':'account'}]
  s['readiness']=dict(enter_offset_distance=2,exit_offset_distance=5,max_sample_age_ms=3000,enter_hold_ms=100,exit_hold_ms=100)
  for topic,policy in [(s['source_topic'],s['identity']['source_policy']),(s['state_topic'],'compact')]:
   (out/(topic+'-create.log')).write_text(run([kafka/'kafka-topics.sh','--bootstrap-server','127.0.0.1:'+str(ports['broker']),'--create','--topic',topic,'--partitions','2','--replication-factor','1','--config','cleanup.policy='+policy,'--config','min.compaction.lag.ms=3600000']))
 catalog=json.loads((W/'fixtures/proto-topics/catalog.json').read_text());extra=json.loads((W/'examples/standalone/fixtures/proto-topics/catalog.json').read_text());collision=json.loads((W/'examples/symbol-collisions/fixtures/proto-topics/catalog.json').read_text());catalog['schemas']+=extra['schemas']+collision['schemas'];catalog['topics']+=extra['topics']+[t for t in collision['topics'] if t['topic']=='catalog'];catalog['topics']=[t for t in catalog['topics'] if t['topic'] in [s['topic'] for s in sources]];used={t['schema'] for t in catalog['topics']};import hashlib;catalog['schemas']=[s for s in catalog['schemas'] if hashlib.sha256(json.dumps(s,separators=(',',':')).encode()).hexdigest() in used];config=dict(bind='127.0.0.1:'+str(ports['query']),origin='http://127.0.0.1:1',catalog=catalog,sources=sources,health=dict(bind='127.0.0.1:'+str(ports['health']),readiness=sources[0]['readiness'],sample_ms=1000,stdout=True),subscription_limits=dict(per_client=32,total=64),run_ms=0,run_until_shutdown=True)
 cp=rt/'config.json';cp.write_text(json.dumps(config));(out/'run.json').write_text(json.dumps(dict(label=label,ports=ports,config=str(cp)),indent=2))
 command=[node,str(W/'scripts/test-grouped-kafka.mjs'),str(cp),str(out),str(rt)]+sys.argv[1:]
 with open(out/'harness.log','w') as f:
  p=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 if p.returncode:raise RuntimeError((out/'harness.log').read_text())
 print((out/'harness.log').read_text())
 if '--f1' in sys.argv:
  fenv={**env,'KSQ_REVIEW_RUNTIME':str(old),'F1_BROKERS':'127.0.0.1:'+str(ports['broker']),'F1_CONFIG_DIR':str(out/'f1-configs'),'F1_SERVICE_BINARY':str(W/'bin/view_server_grouped')}
  with open(out/'f1.log','w') as f:
   result=subprocess.run(['/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo','test','--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical','--locked','--offline','--test','f1_socket','--','--nocapture','--test-threads=1'],env=fenv,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert result.returncode==0,'F1 failed; see preserved log'
finally:
 print('EVIDENCE='+str(out),flush=True)
 for p,f in reversed(children):
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
  f.close()
