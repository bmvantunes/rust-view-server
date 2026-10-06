#!/usr/bin/env python3
import importlib.util,json,subprocess,time,signal,socket
spec=importlib.util.spec_from_file_location('h',__file__.replace('adversarial-kill-sqlite.py','run-kill-sqlite.py'));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
try:
 c=h.topics('stale');a=h.launch(c,'stale-a',fault='kafka_before_commit');h.ready(a)
 h.feed(a['config'],[{'id':'a','amount':'7'}]);h.wait(lambda:(a['controls']/'kafka_before_commit.reached').exists(),'old txn prepared')
 a['proc'].send_signal(signal.SIGSTOP)
 b=h.launch({**c,'bind':'127.0.0.1:34502'},'stale-b');h.ready(b);cut=h.inspect(b['config']);assert len(cut['recovery']['snapshot']['rows'])==1
 (a['controls']/'kafka_before_commit.release').write_text('go');a['proc'].send_signal(signal.SIGCONT);a['proc'].wait(timeout=20)
 assert a['proc'].returncode!=0;assert '"state":"source_committed"' not in a['log'].read_text();assert h.inspect(b['config'])['recovery']==cut['recovery'];h.browser(b,['a']);h.record('old-process-wakes-after-successor',passed=True,old_log=a['log'].read_text(),cut=cut);h.kill(b)
 c=h.topics('engine');a=h.launch(c,'engine-a',fault='kafka_engine_applied');h.ready(a);(a['controls']/'kafka_engine_applied.arm').write_text('fail')
 h.feed(a['config'],[{'id':'a','amount':'7'}]);a['proc'].wait(timeout=20);assert a['proc'].returncode!=0;assert 'engine completion failure' in a['log'].read_text()
 cut=h.inspect(a['config']);assert len(cut['recovery']['snapshot']['rows'])==1;assert '"state":"source_committed"' not in a['log'].read_text()
 b=h.launch(c,'engine-b');h.ready(b);assert h.inspect(b['config'])['recovery']==cut['recovery'];h.browser(b,['a']);h.record('engine-failure-after-durable-commit',passed=True);h.kill(b)
 c=h.topics('tail');a=h.launch(c,'tail-a',fault='kafka_restore_audited');h.wait(lambda:(a['controls']/'kafka_restore_audited.reached').exists(),'restore audited')
 assert not any(v.get('state')=='ready' for v in h.events(a))
 sock=socket.socket();assert sock.connect_ex(('127.0.0.1',34501))!=0;sock.close()
 h.feed(a['config'],[{'id':'a','amount':'7'},{'id':'b','partition':1,'amount':'8'}]);(a['controls']/'kafka_restore_audited.release').write_text('go');h.ready(a);h.browser(a,['a','b']);h.record('traffic-during-restore-no-partial-readiness',passed=True);h.kill(a)
 for action in ['commit','abort']:
  c=h.topics('open-'+action,partitions=1);cp=h.save_config(c,'open-'+action);feedfile=h.RUN/('hold-'+action+'.jsonl');feedfile.write_text(json.dumps({'id':'a','amount':'7'})+'\n')
  producer=subprocess.Popen([str(h.RUNTIME/'kafka_probe'),'hold-source',str(cp),str(feedfile)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=h.ENV)
  try:
   assert producer.stdout.readline().strip()=='prepared'
   a=h.launch(c,'open-'+action);h.wait(lambda:any(v.get('phase')=='source_catchup' for v in h.events(a)),'catchup blocked by open source')
   h.ready(a);initial=h.inspect(a['config']);assert initial['recovery']['snapshot']['rows']==[];assert [v['metrics']['source_target'] for v in h.events(a) if v.get('state')=='restore_proven']==[{'0':0}];h.browser(a,[])
   producer.stdin.write(action+'\n');producer.stdin.flush();producer.wait(timeout=15);assert producer.returncode==0
   
   if action=='commit':h.committed(a,1)
   cut=h.inspect(a['config']);assert len(cut['recovery']['snapshot']['rows'])==(1 if action=='commit' else 0);h.browser(a,['a'] if action=='commit' else []);h.record('open-source-'+action,passed=True,cut=cut);h.kill(a)
   b=h.launch(c,'resolved-'+action);h.ready(b);resolved=h.inspect(b['config']);assert resolved['source_next']['0']==2;assert resolved['group_offsets']['0']=='Offset(2)';assert resolved['recovery']==cut['recovery'];h.record('resolved-source-'+action+'-cursor',passed=True,cut=resolved);h.kill(b)
  finally:
   if producer.poll() is None:producer.kill();producer.wait(timeout=10)
 h.record('adversarial-result',passed=True)
except BaseException as e:h.record('adversarial-failure',error=str(e));raise
finally:
 for p in h.processes:
  if p['proc'].poll() is None:p['proc'].send_signal(signal.SIGCONT);p['proc'].kill();p['proc'].wait(timeout=10)
  p['thread'].join(timeout=5);p['output'].close()
 print('EVIDENCE='+str(h.RUN),flush=True)
