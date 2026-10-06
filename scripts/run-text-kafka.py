#!/usr/bin/env python3
"""Finite new-schema qualification using the accepted private Kafka harness resources."""
from pathlib import Path
import types,json,subprocess,os,uuid,signal,hashlib
source=Path(__file__).with_name('run-retention-kafka.py');h=types.ModuleType('retention_harness');h.__file__=str(source.resolve());exec(compile(source.read_text().rsplit('\ntry:\n    main()',1)[0],str(source),'exec'),h.__dict__)
h.LABEL='text-'+uuid.uuid4().hex[:8];h.RT=h.ROOT/'runtime'/h.LABEL;h.OUT=h.ROOT/'evidence'/h.LABEL;h.CASE_PATH=h.RT/'case.json'
h.page_html=lambda:(h.W/'build/grouped/grouped-demo.html').read_bytes()
def main():
 h.RT.mkdir(parents=True);h.OUT.mkdir(parents=True);h.PORTS={n:h.free_port() for n in ['broker','controller','query','health']};h.start_http();h.PORTS['web']=h.HTTP.server_address[1];h.BROKER=f"127.0.0.1:{h.PORTS['broker']}"
 h.command([Path(h.JAVA_HOME)/'bin/java','-version']);h.start_broker()
 b=json.loads((h.W/'fixtures/expanded-topics/source-bindings.json').read_text());catalog=json.loads((h.W/'fixtures/expanded-topics/catalog.json').read_text());sources=[]
 roots={'shit':'example.Shit','nested_positions':'example.Position','nested_third':'example.Third'}
 for topic,root in roots.items():
  v=b[root];k=b['example.common.Key'];policy='delete' if topic=='shit' else 'compact';fingerprint=next(t['schema'] for t in catalog['topics'] if t['topic']==topic)
  s=dict(topic=topic,schema=fingerprint,brokers=h.BROKER,source_topic=h.LABEL+'-'+topic,source_incarnation=h.LABEL+'-'+topic+'-life',group=h.LABEL+'-'+topic+'-owner',state_topic=h.LABEL+'-'+topic+'-state',initialize_empty=True,partitions=[0,1],key_descriptor=k['descriptor'],value_descriptor=v['descriptor'],key_tag=0,key_fields=k['key_fields'],mapping=v['mapping'],identity=dict(source_policy=policy,components=[dict(source='key',field='account.id')]),readiness=dict(enter_offset_distance=2,exit_offset_distance=5,max_sample_age_ms=3000,enter_hold_ms=100,exit_hold_ms=100),max_rows=10000)
  if topic!='nested_third':s['retention']=dict(maxRetentionMinutes=0.5,**({'maxRetentionMessages':3} if policy=='delete' else {'maxRetentionMessagesPerKey':1}))
  sources.append(s);h.create_topic(s['source_topic'],policy=policy,retention_ms=10800000);h.create_topic(s['state_topic'],canonical=True)
 full=h.config_doc(sources,catalog,h.PORTS['query'],h.PORTS['health'],h.PORTS['web']);(h.RT/'full.json').write_text(json.dumps(full))
 first=json.loads(json.dumps(full));first['sources']=sources[:2];first['catalog']['topics']=catalog['topics'][:2];ids={x['schema'] for x in first['catalog']['topics']};first['catalog']['schemas']=[s for s in catalog['schemas'] if hashlib.sha256(json.dumps(s,separators=(',',':')).encode()).hexdigest() in ids];(h.RT/'first.json').write_text(json.dumps(first))
 case=dict(runtime=str(h.RT),evidence=str(h.OUT),first=str(h.RT/'first.json'),full=str(h.RT/'full.json'),ports=h.PORTS,token=h.TOKEN);h.CASE_PATH.write_text(json.dumps(case));(h.OUT/'run.json').write_text(json.dumps(case,indent=2))
 for name in ['first.json','full.json','case.json']:(h.OUT/name).write_bytes((h.RT/name).read_bytes())
 (h.OUT/'bindings.json').write_text(json.dumps({str(p.relative_to(h.W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [h.W/'scripts/test-text-kafka.mjs',h.W/'bin/view_server_expanded',h.W/'bin/generic_kafka_producer_expanded',*list((h.W/'build/grouped/assets').glob('*'))]},indent=2))
 p=h.command([h.NODE,h.W/'scripts/test-text-kafka.mjs',h.CASE_PATH],timeout=300,check=False);(h.OUT/'browser.log').write_text(p.stdout+p.stderr);print(p.stdout,p.stderr,flush=True)
 (h.OUT/'telemetry-receipts.json').write_text(json.dumps(h.OTLP,indent=2));(h.OUT/'events.json').write_text(json.dumps(h.EVENTS,indent=2));assert p.returncode==0
 print('PASS',h.OUT,flush=True)
try:main()
finally:
 for p,log,name in reversed(h.CHILDREN):
  if p.poll() is None:
   if name=='broker':os.killpg(p.pid,signal.SIGTERM)
   else:p.terminate()
   try:p.wait(timeout=15)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=10)
  if log:log.close()
 if hasattr(h,'HTTP'):h.HTTP.shutdown()
