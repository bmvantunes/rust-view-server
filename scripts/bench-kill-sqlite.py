#!/usr/bin/env python3
import importlib.util,json,subprocess,time,threading,signal
spec=importlib.util.spec_from_file_location('h',__file__.replace('bench-kill-sqlite.py','run-kill-sqlite.py'));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
samples=[]
def sample(p):
 while p['proc'].poll() is None:
  r=subprocess.run(['ps','-o','rss=,time=','-p',str(p['proc'].pid)],text=True,capture_output=True)
  if r.returncode==0:samples.append({'process':p['label'],'elapsed':time.monotonic()-p['started'],'rss_cpu':r.stdout.strip()})
  time.sleep(.05)
def launch(c,label):
 p=h.launch(c,label);threading.Thread(target=sample,args=(p,),daemon=True).start();h.ready(p);return p
try:
 c=h.topics('bench',partitions=1);p=launch(c,'seed')
 n=10000
 h.feed(p['config'],[{'id':f'r{i:05d}','amount':str(i)} for i in range(n)])
 h.wait(lambda:any(v.get('records_committed',0)>=n for v in h.events(p)),'seed committed',120)
 baseline=h.inspect(p['config']);assert len(baseline['recovery']['snapshot']['rows'])==n;h.kill(p)
 p=launch(c,'latest-10k');assert h.inspect(p['config'])['recovery']==baseline['recovery']
 query=json.loads(h.command([h.NODE,h.ROOT/'scripts/bench-kill-sqlite-browser.mjs',p['config']]));assert query['result']['total_rows']==n;h.record('first-query-differential-materialization-and-transport',measurement=query)
 # Four updates per key, before cleaner is allowed to run.
 for cycle in range(4):h.feed(p['config'],[{'id':f'r{i:05d}','amount':str(i+cycle+1)} for i in range(n)])
 h.wait(lambda:any(v.get('records_committed',0)>=4*n for v in h.events(p)),'churn committed',180)
 history=h.inspect(p['config']);h.kill(p)
 p=launch(c,'history-10k');assert h.inspect(p['config'])['recovery']==history['recovery']
 h.feed(p['config'],[{'id':f'r{i:05d}','delete':True} for i in range(8000)])
 h.wait(lambda:any(v.get('records_committed',0)>=8000 for v in h.events(p)),'deletes committed',120)
 deleted=h.inspect(p['config']);assert len(deleted['recovery']['snapshot']['rows'])==2000;assert deleted['sticky']==10000;h.kill(p)
 p=launch(c,'deleted-10k');assert h.inspect(p['config'])['recovery']==deleted['recovery'];h.kill(p)
 state=c['mode']['config']['state_topic']
 h.command([h.KAFKA/'kafka-configs.sh','--bootstrap-server','127.0.0.1:34492','--entity-type','topics','--entity-name',state,'--alter','--add-config','min.compaction.lag.ms=0,max.compaction.lag.ms=1000,min.cleanable.dirty.ratio=0.01,segment.ms=100,segment.bytes=1048576'])
 # Restart/guard writes roll the active segment, then give the actual broker cleaner time.
 p=launch(c,'cleaner-trigger');time.sleep(4);h.kill(p)
 time.sleep(4);p=launch(c,'cleaned-10k');cleaned=h.inspect(p['config']);assert cleaned['recovery']==deleted['recovery'];h.kill(p)
 h.record('compaction-observation',before_records=deleted['records'],after_records=cleaned['records'],actually_reduced=cleaned['records']<deleted['records'])
 h.record('bounded-bootstrap-benchmark',passed=True,rows=10000,latest=baseline['records'],history=history['records'],delete_heavy=deleted['records'],cleaned=cleaned['records'])
except BaseException as e:h.record('benchmark-failure',error=str(e));raise
finally:
 for p in h.processes:
  if p['proc'].poll() is None:p['proc'].kill();p['proc'].wait(timeout=10)
  p['thread'].join(timeout=5);p['output'].close()
 (h.RUN/'resources.json').write_text(json.dumps(samples,indent=2));print('EVIDENCE='+str(h.RUN),flush=True)
