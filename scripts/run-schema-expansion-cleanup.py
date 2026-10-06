#!/usr/bin/env python3
"""Finite red/green actual-service cleanup witness using the pinned production Worker."""
from pathlib import Path
from copy import deepcopy
import types,json,uuid,subprocess,time,os,signal,sys,hashlib
W=Path(__file__).resolve().parents[1]
r=types.ModuleType('retention_gate');r.__file__=str(W/'scripts/run-retention-kafka.py')
exec(compile(Path(r.__file__).read_text().rsplit('\ntry:\n',1)[0],r.__file__,'exec'),r.__dict__)
mode=sys.argv[1] if len(sys.argv)>1 else 'green'
r.LABEL='schema-cleanup-'+mode+'-'+uuid.uuid4().hex[:8];r.RT=W.parent/'runtime'/r.LABEL;r.OUT=W/'evidence/schema-expansion'/r.LABEL;r.CASE_PATH=r.RT/'retention-case.json'
r.RT.mkdir(parents=True);r.OUT.mkdir(parents=True);(r.RT/'faults').mkdir()
r.page_html=lambda:(W/'build/grouped/grouped-demo.html').read_bytes()
try:
 r.PORTS={n:r.free_port() for n in ('broker','controller','query','health')};r.start_http();r.BROKER='127.0.0.1:'+str(r.PORTS['broker']);r.start_broker()
 bindings=json.loads((W/'fixtures/expanded-topics/source-bindings.json').read_text());catalog={'format':1,'schemas':[],'topics':[]};browser_catalog={};sources=[]
 for topic,root in [('orders','example.Shit'),('positions','example.Position')]:
  v=bindings[root];k=bindings['example.common.Key'];schema=v['schema'];fp=hashlib.sha256(json.dumps(schema,separators=(',',':')).encode()).hexdigest();catalog['schemas'].append(schema);catalog['topics'].append(dict(topic=topic,schema=fp));browser_catalog[topic]=dict(schema=schema,fingerprint=fp)
  source=dict(topic=topic,schema=fp,brokers=r.BROKER,source_topic=r.LABEL+'-'+topic,source_incarnation=r.LABEL+'-'+topic+'-life',group=r.LABEL+'-'+topic+'-owner',state_topic=r.LABEL+'-'+topic+'-state',initialize_empty=True,partitions=[0,1],key_descriptor=k['descriptor'],value_descriptor=v['descriptor'],key_tag=0,key_fields=k['key_fields'],mapping=v['mapping'],identity=dict(source_policy='delete' if topic=='orders' else 'compact',components=[dict(source='key',field='account.id')]),readiness=dict(enter_offset_distance=2,exit_offset_distance=5,max_sample_age_ms=3000,enter_hold_ms=0,exit_hold_ms=0),max_rows=10000,retention={'maxRetentionMinutes':0.5,'maxRetentionMessages':1000} if topic=='orders' else {'maxRetentionMinutes':10,'maxRetentionMessagesPerKey':1})
  sources.append(source);r.create_topic(source['source_topic'],policy=source['identity']['source_policy']);r.create_topic(source['state_topic'],canonical=True)
 def frame(d,body):return (bytes([0])+int(d['schema_id']).to_bytes(4,'big')+bytes([0])+body).hex()
 def record(topic,i,origin):
  src=next(s for s in sources if s['topic']==topic);name=str(i).encode();key=bytes([10,len(name)+2,10,len(name)])+name;inner=bytes([10,len(name)])+name+bytes([26,1,49]);value=bytes([10,len(inner)])+inner
  return dict(topic=topic,partition=i%2,ack=i,raw_key_hex=frame(src['key_descriptor'],key),raw_value_hex=frame(src['value_descriptor'],value),timestamp_ms=origin)
 def start_new(config_path,faults=False):
  r.SERVICE_LOG=open(r.OUT/'fault-service.log','w');r.SERVICE=r.record_process(subprocess.Popen([str(W/'bin/view_server_expanded_faults'),str(config_path)],env=dict(r.ENV,V121_FAULT_DIR=str(r.RT/'faults')),cwd=r.RT,stdout=r.SERVICE_LOG,stderr=subprocess.STDOUT),r.SERVICE_LOG,'fault-owner')
 r.start_service=start_new
 config=r.config_doc(sources,catalog,r.PORTS['query'],r.PORTS['health'],r.PORTS['web']);config_path=r.RT/'config.json';config_path.write_text(json.dumps(config,indent=2));(r.OUT/'configuration.json').write_text(json.dumps(config,indent=2))
 identities={str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [W/'bin/view_server_expanded_faults',W/'ingestion/src/generic_service.rs',W/'ingestion/src/generic_kafka.rs',W/'browser/src/product-provider.tsx',W/'browser/src/product.remote.worker.ts']};(r.OUT/'bindings.json').write_text(json.dumps(identities,indent=2))
 r.start_service(config_path,faults=True);r.wait_until(lambda:r.current_health().get('startup_complete'),'service ready',45)
 log=open(r.OUT/'producer.log','w');producer=r.record_process(subprocess.Popen([str(W/'bin/generic_kafka_producer_expanded'),str(config_path),'transactions'],env=r.ENV,cwd=r.RT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1),log,'producer');assert json.loads(producer.stdout.readline())['producer_ready']
 records=[]
 def send(v):
  producer.stdin.write(json.dumps(v)+'\n');producer.stdin.flush();a=json.loads(producer.stdout.readline());records.append({'input':v,'ack':a});(r.OUT/'source-records.json').write_text(json.dumps(records,indent=2));return a
 send({'op':'begin'});origin=int(time.time()*1000)
 for i in range(520):send(record('orders',i,origin))
 send(record('positions',0,origin));send({'op':'commit'})
 r.wait_until(lambda:r.source_health(r.current_health(),'orders')['retention']['active_payload_rows']==520,'520 current rows',30)
 baseline=r.current_health();definitions={}
 for topic,parent in [('orders','oo'),('positions','details')]:
  definitions[topic+'Raw']=dict(topic=topic,query=dict(select=[parent+'.name',parent+'.price'],orderBy=[dict(field=parent+'.name',direction='asc')]))
  definitions[topic+'Group']=dict(topic=topic,query=dict(groupBy=[parent+'.status'],aggregates={'count':dict(aggFunc='count'),'sum':dict(aggFunc='sum',field=parent+'.price')},orderBy=[]))
 r.CASE_PATH.write_text(json.dumps(dict(wsUrl='ws://127.0.0.1:'+str(r.PORTS['query'])+'/v15',token=r.TOKEN,catalog=browser_catalog,definitions=definitions)))
 (r.OUT/'case.json').write_bytes(r.CASE_PATH.read_bytes());(r.RT/'phase.json').write_text(json.dumps({'phase':'control'}))
 browserlog=open(r.OUT/'browser-driver.log','w');node=r.record_process(subprocess.Popen([str(r.NODE),str(W/'scripts/schema-expansion-cleanup-browser.mjs'),f"http://127.0.0.1:{r.PORTS['web']}/retention-browser.html",str(r.OUT/'browser-raw.json'),mode],env=r.ENV,stdout=browserlog,stderr=subprocess.STDOUT),browserlog,'browser')
 r.wait_browser('cleanup_ready',30);(r.OUT/'control-health.json').write_text(json.dumps(r.current_health(),indent=2))
 gate=r.RT/'faults/orders-retention_before_publication';gate.with_suffix('.arm').write_text('hold')
 r.wait_until(lambda:gate.with_suffix('.reached').exists(),'first committed expiry chunk',40,.01)
 held=r.current_health();assert r.source_health(held,'orders')['retention']['pending_due'];assert r.source_health(held,'orders')['retention']['active_payload_rows']==264
 (r.OUT/'pending-health.json').write_text(json.dumps(held,indent=2));(r.RT/'phase.json').write_text(json.dumps({'phase':'release'}))
 r.wait_browser('release_queued',8);gate.with_suffix('.release').write_text('release');r.wait_browser('cleanup_complete',20);node.wait(timeout=10)
 r.wait_until(lambda:r.current_health()['subscriptions']==0,'final native cleanup',10)
 (r.OUT/'final-health.json').write_text(json.dumps(r.current_health(),indent=2));(r.OUT/'result.json').write_text(json.dumps({'mode':mode,'status':'REPRODUCED' if mode=='red' else 'PASS','actual_native':True,'original_fault_binary':identities['bin/view_server_expanded_faults'],'barrier':'orders-retention_before_publication','held_payload_rows':264,'due_total':520,'source_next_before':r.source_next(baseline),'source_next_after':r.source_next(r.current_health())},indent=2));print('RESULT='+str(r.OUT),flush=True)
finally:
 r.stop_service()
 for p,log,name in reversed(r.CHILDREN):
  if p.poll() is None:
   try:
    if name=='broker':os.killpg(p.pid,signal.SIGTERM)
    else:p.terminate()
    p.wait(timeout=10)
   except subprocess.TimeoutExpired:p.kill();p.wait()
  log.close()
 if r.HTTP:r.HTTP.shutdown();r.HTTP.server_close()
