#!/usr/bin/env python3
import importlib.util,json,signal,pathlib
spec=importlib.util.spec_from_file_location('h',__file__.replace('delete-fence-kill-sqlite.py','run-kill-sqlite.py'));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
try:
 c=h.topics('stale-delete');a=h.launch(c,'delete-seed');h.ready(a);h.feed(a['config'],[{'id':'a','amount':'7'}]);h.committed(a,1);h.kill(a)
 a=h.launch(c,'delete-old',fault='kafka_before_commit');h.ready(a);h.feed(a['config'],[{'id':'a','delete':True}]);h.wait(lambda:(a['controls']/'kafka_before_commit.reached').exists(),'old delete prepared');a['proc'].send_signal(signal.SIGSTOP)
 b=h.launch({**c,'bind':'127.0.0.1:34502'},'delete-new');h.ready(b);cut=h.inspect(b['config']);assert cut['recovery']['snapshot']['rows']==[];assert cut['sticky']==1;h.browser(b,[])
 (a['controls']/'kafka_before_commit.release').write_text('go');a['proc'].send_signal(signal.SIGCONT);a['proc'].wait(timeout=20);assert a['proc'].returncode!=0;assert h.inspect(b['config'])['recovery']==cut['recovery'];h.record('stale-typed-source-tombstone-fenced',passed=True,cut=cut,old_log=a['log'].read_text())
 h.feed(b['config'],[{'id':'a','partition':1,'amount':'8'}]);b['proc'].wait(timeout=15);assert b['proc'].returncode!=0;assert 'another partition' in b['log'].read_text();assert h.inspect(b['config'])['recovery']==cut['recovery'];h.record('deleted-sticky-key-cross-partition-rejected',passed=True)
 c=h.topics('retention',partitions=1);a=h.launch(c,'retention-seed');h.ready(a);h.kill(a);h.feed(a['config'],[{'id':'lost','amount':'7'}])
 deletion=h.RUN/'delete-records.json';deletion.write_text(json.dumps({'partitions':[{'topic':c['source']['topic'],'partition':0,'offset':1}],'version':1}))
 out=h.command([h.KAFKA/'kafka-delete-records.sh','--bootstrap-server','127.0.0.1:34492','--offset-json-file',deletion]);(h.RUN/'delete-records.log').write_text(out)
 b=h.launch(c,'retention-gap');b['proc'].wait(timeout=20);assert b['proc'].returncode!=0;assert 'RetentionGap' in b['log'].read_text();assert not any(v.get('state')=='ready' for v in h.events(b));h.record('source-retention-gap-fails-closed',passed=True,log=b['log'].read_text())
 h.record('delete-fence-retention-result',passed=True)
except BaseException as e:h.record('delete-fence-retention-failure',error=str(e));raise
finally:
 for p in h.processes:
  if p['proc'].poll() is None:p['proc'].send_signal(signal.SIGCONT);p['proc'].kill();p['proc'].wait(timeout=10)
  p['thread'].join(timeout=5);p['output'].close()
 print('EVIDENCE='+str(h.RUN),flush=True)
