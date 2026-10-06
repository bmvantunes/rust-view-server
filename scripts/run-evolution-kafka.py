#!/usr/bin/env python3
from pathlib import Path
import types,json,os,uuid,signal,hashlib
source=Path(__file__).with_name('run-retention-kafka.py');h=types.ModuleType('h');h.__file__=str(source.resolve());exec(compile(source.read_text().rsplit('\ntry:\n    main()',1)[0],str(source),'exec'),h.__dict__)
h.LABEL='evolution-'+uuid.uuid4().hex[:8];h.RT=h.ROOT/'runtime'/h.LABEL;h.OUT=h.ROOT/'evidence'/h.LABEL;h.CASE_PATH=h.RT/'case.json';h.page_html=lambda:(h.W/'build/grouped/grouped-demo.html').read_bytes()
def main():
 h.RT.mkdir(parents=True);h.OUT.mkdir(parents=True);h.PORTS={n:h.free_port() for n in ['broker','controller','query','health']};h.start_http();h.PORTS['web']=h.HTTP.server_address[1];h.BROKER=f"127.0.0.1:{h.PORTS['broker']}";h.start_broker()
 b=json.loads((h.W/'fixtures/evolution/bindings.json').read_text());old=b['old']['evolution.Row'];new=b['next']['evolution.Row'];key=b['old']['evolution.Key'];fp=lambda s:hashlib.sha256(json.dumps(s,separators=(',',':')).encode()).hexdigest()
 s=dict(topic='evolved',schema=fp(old['schema']),brokers=h.BROKER,source_topic=h.LABEL+'-source',source_incarnation=h.LABEL,group=h.LABEL+'-owner',state_topic=h.LABEL+'-state',initialize_empty=True,partitions=[0,1],key_descriptor=key['descriptor'],value_descriptor=old['descriptor'],key_fields=key['key_fields'],mapping=old['mapping'],identity=dict(source_policy='compact',components=[dict(source='key',field='id')]),readiness=dict(enter_offset_distance=1,exit_offset_distance=3,max_sample_age_ms=3000,enter_hold_ms=100,exit_hold_ms=100),max_rows=100,retention=dict(maxRetentionMessagesPerKey=1))
 h.create_topic(s['source_topic'],policy='compact');h.create_topic(s['state_topic'],canonical=True)
 catalogs={};configs={}
 for label,v in [('old',old),('new',new)]:
  source=json.loads(json.dumps(s));source['schema']=fp(v['schema']);source['value_descriptor']=v['descriptor'];source['mapping']=v['mapping']
  if label=='new':source['initialize_empty']=False;source['evolution']=dict(definition=old['schema'],value_descriptor=old['descriptor'],mapping=old['mapping'])
  catalog=dict(format=1,schemas=[v['schema']],topics=[dict(topic='evolved',schema=fp(v['schema']))]);catalogs[label]={'evolved':dict(schema=v['schema'],fingerprint=fp(v['schema']))};config=h.config_doc([source],catalog,h.PORTS['query'],h.PORTS['health'],h.PORTS['web']);configs[label]=str(h.RT/(label+'.json'));Path(configs[label]).write_text(json.dumps(config))
 case=dict(runtime=str(h.RT),evidence=str(h.OUT),ports=h.PORTS,token=h.TOKEN,configs=configs,catalogs=catalogs);h.CASE_PATH.write_text(json.dumps(case));(h.OUT/'case.json').write_text(json.dumps(case,indent=2))
 inputs=[h.W/'bin/view_server_evolution',h.W/'bin/view_server_evolution_faults',h.W/'bin/generic_kafka_producer_evolution',h.W/'scripts/test-evolution-kafka.mjs',*list((h.W/'build/grouped/assets').glob('*'))];(h.OUT/'identities.json').write_text(json.dumps({str(p.relative_to(h.W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2))
 p=h.command([h.NODE,h.W/'scripts/test-evolution-kafka.mjs',h.CASE_PATH],timeout=240,check=False);(h.OUT/'run.log').write_text(p.stdout+p.stderr);print(p.stdout,p.stderr,flush=True);assert p.returncode==0;print('PASS',h.OUT)
try:main()
finally:
 for p,log,name in reversed(h.CHILDREN):
  if p.poll() is None:
   if name=='broker':os.killpg(p.pid,signal.SIGTERM)
   else:p.terminate()
   try:p.wait(timeout=15)
   except: p.kill();p.wait(timeout=10)
  if log:log.close()
 if h.HTTP:h.HTTP.shutdown()
