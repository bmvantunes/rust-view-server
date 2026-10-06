#!/usr/bin/env python3
"""Finite red/green actual-service cleanup witness using the pinned production Worker."""
from pathlib import Path
from copy import deepcopy
import types,json,uuid,subprocess,time,os,signal,sys,hashlib
W=Path(__file__).resolve().parents[1]
r=types.ModuleType('retention_gate');r.__file__=str(W/'scripts/run-retention-kafka.py')
exec(compile(Path(r.__file__).read_text().rsplit('\ntry:\n',1)[0],r.__file__,'exec'),r.__dict__)
mode=sys.argv[1] if len(sys.argv)>1 else 'red'
r.LABEL='repair-'+mode+'-'+uuid.uuid4().hex[:8];r.RT=W.parent/'runtime'/r.LABEL;r.OUT=W/'evidence/repair'/r.LABEL;r.CASE_PATH=r.RT/'retention-case.json'
r.RT.mkdir(parents=True);r.OUT.mkdir(parents=True);(r.RT/'faults').mkdir()
r.page_html=lambda:(W/'build/grouped/grouped-demo.html').read_bytes()
try:
 r.PORTS={n:r.free_port() for n in ('broker','controller','query','health')};r.start_http();r.BROKER='127.0.0.1:'+str(r.PORTS['broker']);r.start_broker()
 r.command([r.NODE,W/'scripts/generate-proto-source-config.mjs',r.RT/'bindings.json',r.BROKER,r.LABEL])
 sources=[s for s in json.loads((r.RT/'bindings.json').read_text()) if s['topic'] in ('orders','positions')]
 for s in sources:
  s['state_topic']=r.LABEL+'-'+s['topic']+'-canonical-retention-v3';s['max_rows']=10000
  s['retention']={'maxRetentionMinutes':0.5,'maxRetentionMessages':1000} if s['topic']=='orders' else {'maxRetentionMinutes':10,'maxRetentionMessagesPerKey':1}
  if s['topic']=='orders':s['identity']['components']=[{'source':'key','field':'tenant'},{'source':'key','field':'desk'},{'source':'value','field':'orderId'}]
  s['readiness']=dict(enter_offset_distance=2,exit_offset_distance=5,max_sample_age_ms=3000,enter_hold_ms=0,exit_hold_ms=0)
  r.create_topic(s['source_topic'],policy='delete' if s['topic']=='orders' else 'compact');r.create_topic(s['state_topic'],canonical=True)
 catalog=json.loads((W/'fixtures/proto-topics/catalog.json').read_text());catalog['topics']=[t for t in catalog['topics'] if t['topic'] in ('orders','positions')]
 browser_catalog=json.loads((W/'fixtures/proto-topics/browser-catalog.json').read_text());browser_catalog={k:v for k,v in browser_catalog.items() if k in ('orders','positions')}
 config=r.config_doc(sources,catalog,r.PORTS['query'],r.PORTS['health'],r.PORTS['web']);config_path=r.RT/'config.json';config_path.write_text(json.dumps(config,indent=2));(r.OUT/'configuration.json').write_text(json.dumps(config,indent=2))
 identities={str(p.relative_to(W)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [W/'bin/view_server_grouped_faults',W/'ingestion/src/generic_service.rs',W/'ingestion/src/generic_kafka.rs',W/'browser/src/product-provider.tsx',W/'browser/src/product.remote.worker.ts']};(r.OUT/'bindings.json').write_text(json.dumps(identities,indent=2))
 r.start_service(config_path,faults=True);r.wait_until(lambda:r.current_health().get('startup_complete'),'service ready',45)
 log=open(r.OUT/'producer.log','w');producer=r.record_process(subprocess.Popen([str(W/'ingestion/target/release/examples/generic_kafka_producer'),str(config_path),'transactions'],env=r.ENV,cwd=r.RT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,bufsize=1),log,'producer');assert json.loads(producer.stdout.readline())['producer_ready']
 records=[]
 def send(v):
  producer.stdin.write(json.dumps(v)+'\n');producer.stdin.flush();a=json.loads(producer.stdout.readline());records.append({'input':v,'ack':a});(r.OUT/'source-records.json').write_text(json.dumps(records,indent=2));return a
 send({'op':'begin'});origin=int(time.time()*1000)
 for i in range(520):send({'topic':'orders','partition':i%2,'ack':i,'key':r.make_key(i),'row':r.make_row('orders',i),'timestamp_ms':origin})
 send({'topic':'positions','partition':0,'ack':520,'key':r.make_key(0),'row':r.make_row('positions',0),'timestamp_ms':origin});send({'op':'commit'})
 r.wait_until(lambda:r.source_health(r.current_health(),'orders')['retention']['active_payload_rows']==520,'520 current rows',30)
 baseline=r.current_health();r.create_case(sources,browser_catalog,{'orders':[],'positions':[]},{'orders':[],'positions':[]},baseline)
 (r.OUT/'case.json').write_bytes(r.CASE_PATH.read_bytes());(r.RT/'phase.json').write_text(json.dumps({'phase':'control'}))
 browserlog=open(r.OUT/'browser-driver.log','w');node=r.record_process(subprocess.Popen([str(r.NODE),str(W/'scripts/retention-repair-browser.mjs'),f"http://127.0.0.1:{r.PORTS['web']}/retention-browser.html",str(r.OUT/'browser-raw.json'),mode],env=r.ENV,stdout=browserlog,stderr=subprocess.STDOUT),browserlog,'browser')
 r.wait_browser('cleanup_ready',30);(r.OUT/'control-health.json').write_text(json.dumps(r.current_health(),indent=2))
 gate=r.RT/'faults/orders-retention_before_publication';gate.with_suffix('.arm').write_text('hold')
 r.wait_until(lambda:gate.with_suffix('.reached').exists(),'first committed expiry chunk',40,.01)
 held=r.current_health();assert r.source_health(held,'orders')['retention']['pending_due'];assert r.source_health(held,'orders')['retention']['active_payload_rows']==264
 (r.OUT/'pending-health.json').write_text(json.dumps(held,indent=2));(r.RT/'phase.json').write_text(json.dumps({'phase':'release'}))
 r.wait_browser('release_queued',8);gate.with_suffix('.release').write_text('release');r.wait_browser('cleanup_complete',20);node.wait(timeout=10)
 r.wait_until(lambda:r.current_health()['subscriptions']==0,'final native cleanup',10)
 (r.OUT/'final-health.json').write_text(json.dumps(r.current_health(),indent=2));(r.OUT/'result.json').write_text(json.dumps({'mode':mode,'status':'REPRODUCED' if mode=='red' else 'PASS','actual_native':True,'original_fault_binary':identities['bin/view_server_grouped_faults'],'barrier':'orders-retention_before_publication','held_payload_rows':264,'due_total':520,'source_next_before':r.source_next(baseline),'source_next_after':r.source_next(r.current_health())},indent=2));print('RESULT='+str(r.OUT),flush=True)
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
