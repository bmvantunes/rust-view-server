#!/usr/bin/env python3
"""Finite private local broker runner. Retains every attempt; no installed services."""
from pathlib import Path
import subprocess,os,json,time,uuid,signal,socket,sys
R=Path(__file__).resolve().parents[2];W=R/'work';old=R.parent/'kill-sqlite-hot-path-20261003/runtime';label='topics-'+uuid.uuid4().hex[:8];rt=R/'runtime'/label;rt.mkdir(parents=True);out=R/'evidence'/label;out.mkdir();children=[]
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
 bindings=rt/'bindings.json';run(['python3',W/'scripts/generate-topic-bindings.py',W/'fixtures/topics/catalog.json',bindings,'127.0.0.1:'+str(ports['broker']),label]);sources=json.loads(bindings.read_text())
 for s in sources:
  s['readiness']=dict(enter_offset_distance=2,exit_offset_distance=5,max_sample_age_ms=3000,enter_hold_ms=100,exit_hold_ms=100)
  for topic,policy in [(s['source_topic'],'delete'),(s['state_topic'],'compact')]:
   (out/(topic+'-create.log')).write_text(run([kafka/'kafka-topics.sh','--bootstrap-server','127.0.0.1:'+str(ports['broker']),'--create','--topic',topic,'--partitions','2','--replication-factor','1','--config','cleanup.policy='+policy,'--config','min.compaction.lag.ms=3600000']))
 catalog=json.loads((W/'fixtures/topics/catalog.json').read_text());config=dict(bind='127.0.0.1:'+str(ports['query']),origin='http://127.0.0.1:1',catalog=catalog,sources=sources,health=dict(bind='127.0.0.1:'+str(ports['health']),readiness=sources[0]['readiness'],sample_ms=1000,stdout=True),subscription_limits=dict(per_client=16,total=64),run_ms=0,run_until_shutdown=True)
 cp=rt/'config.json';cp.write_text(json.dumps(config));(out/'run.json').write_text(json.dumps(dict(label=label,ports=ports,config=str(cp)),indent=2))
 command=[node,str(W/'scripts'/os.environ.get('TOPICS_HARNESS','test-configurable-kafka.mjs')),str(cp),str(out),str(rt)]+sys.argv[1:]
 with open(out/'harness.log','w') as f:
  p=subprocess.run(command,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 if p.returncode:raise RuntimeError((out/'harness.log').read_text())
 print((out/'harness.log').read_text())
 if os.environ.get('TOPICS_F1')=='1':
  f1env={**env,'F1_BROKERS':'127.0.0.1:'+str(ports['broker']),'KSQ_REVIEW_RUNTIME':str(old),'F1_SERVICE_BINARY':str(W/'bin/view_server_kafka_topics'),'F1_CONFIG_DIR':str(out/'f1-config'),'RUSTC':'/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc'}
  with open(out/'f1.log','w') as f:
   f1=subprocess.run(['/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo','test','--locked','--offline','--manifest-path',str(W/'ingestion/Cargo.toml'),'--features','kafka-canonical','--test','f1_socket','--','--test-threads=1','--nocapture'],env=f1env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  if f1.returncode:raise RuntimeError('F1 failed; see retained f1.log')
finally:
 print('EVIDENCE='+str(out),flush=True)
 for p,f in reversed(children):
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGTERM)
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait(timeout=10)
  f.close()
