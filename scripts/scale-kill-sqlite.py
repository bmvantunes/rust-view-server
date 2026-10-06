#!/usr/bin/env python3
import importlib.util,json,subprocess,time,threading,signal
spec=importlib.util.spec_from_file_location('h',__file__.replace('scale-kill-sqlite.py','run-kill-sqlite.py'));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
samples=[]
def sample(p):
 while p['proc'].poll() is None:
  r=subprocess.run(['ps','-o','rss=,time=','-p',str(p['proc'].pid)],text=True,capture_output=True)
  if r.returncode==0:
   samples.append({'process':p['label'],'elapsed':time.monotonic()-p['started'],'rss_cpu':r.stdout.strip()})
   parts=r.stdout.split()
   if parts and int(parts[0])>1024*1024:p['proc'].kill();h.record('rss-safety-stop',limit_kib=1024*1024);return
  time.sleep(.05)
def launch(c,label):
 p=h.launch(c,label);threading.Thread(target=sample,args=(p,),daemon=True).start();h.ready(p);return p
try:
 hardware=h.command(['sysctl','-n','hw.memsize','hw.logicalcpu','hw.model']);h.record('host',values=hardware)
 c=h.topics('scale',partitions=1);p=launch(c,'seed-100k')
 n=100000
 # Bounded ten 10k producer calls and a hard 1 GiB native-process RSS stop.
 for start in range(0,n,10000):h.feed(p['config'],[{'id':f'r{i:06d}','amount':str(i)} for i in range(start,start+10000)])
 h.wait(lambda:any(v.get('records_committed',0)>=n for v in h.events(p)),'100k committed',180)
 baseline=h.inspect(p['config']);assert len(baseline['recovery']['snapshot']['rows'])==n;h.kill(p)
 p=launch(c,'restore-100k');cut=h.inspect(p['config']);assert cut['recovery']==baseline['recovery'];assert cut['source_next']==baseline['source_next'];assert cut['group_offsets']==baseline['group_offsets']
 query=json.loads(h.command([h.NODE,h.ROOT/'scripts/bench-kill-sqlite-browser.mjs',p['config']]));assert query['result']['total_rows']==n;assert [r['id'] for r in query['result']['rows']]==[f'r{i:06d}' for i in range(16)]
 h.record('first-query-100k',measurement=query);h.kill(p);h.record('100k-restore',passed=True,records=cut['records'],source_next=cut['source_next'])
except BaseException as e:h.record('scale-failure',error=str(e));raise
finally:
 for p in h.processes:
  if p['proc'].poll() is None:p['proc'].kill();p['proc'].wait(timeout=10)
  p['thread'].join(timeout=5);p['output'].close()
 (h.RUN/'resources.json').write_text(json.dumps(samples,indent=2));print('EVIDENCE='+str(h.RUN),flush=True)
