#!/usr/bin/env python3
"""Bounded native scaling probe; IPC timings are not DOM latency."""
from pathlib import Path
import subprocess,json,hashlib,time,math
W=Path(__file__).resolve().parents[1];records=[]
schema=dict(format=1,id='scale',version=1,key='id',fields=[dict(name=n,kind=k,optional=False,nullable=False)for n,k in [('id','string'),('g','string'),('v','int64')]])
fp=hashlib.sha256(json.dumps(schema,separators=(',',':')).encode()).hexdigest();catalog=dict(format=1,schemas=[schema],topics=[dict(topic='scale',schema=fp)])
for size in [128,1024,8192]:
 for mode in ['raw','count-sum','distinct-extrema','high-cardinality','shared-windows']:
  p=subprocess.Popen([W/'native/target/debug/examples/grouped_probe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
  def call(op,**kw):
   v=dict(op=op,topic='scale',schema=fp,**kw);p.stdin.write(json.dumps(v,separators=(',',':'))+'\n');p.stdin.flush();r=json.loads(p.stdout.readline());assert 'ok'in r,r;return r['ok']
  def row(i,revision=0):return dict(id=str(i),g=str(i if mode=='high-cardinality'else i%8),v=str(i+revision))
  call('init',catalog=catalog)
  for start in range(0,size,1024):call('apply',mutations=[dict(kind='upsert',row=row(i))for i in range(start,min(size,start+1024))])
  q=dict(select=['v'],order_by=[])if mode=='raw'else dict(group_by=['g'],aggregates=dict(n=dict(aggFunc='count'),s=dict(aggFunc='sum',field='v')),order_by=[dict(aggregate='s',direction='desc')])
  if mode=='distinct-extrema':q['aggregates'].update(d=dict(aggFunc='countDistinct',field='v'),lo=dict(aggFunc='min',field='v'),hi=dict(aggFunc='max',field='v'))
  start=time.perf_counter_ns();call('open',sub='a',query=q);build=time.perf_counter_ns()-start
  if mode=='shared-windows':call('open',sub='b',query=q)
  before=call('metrics');samples=[]
  for i in range(40):
   start=time.perf_counter_ns();call('apply',mutations=[dict(kind='upsert',row=row(0,i+1))]);call('read',sub='a',offset=0,limit=2)
   if mode=='shared-windows':call('read',sub='b',offset=5,limit=2)
   samples.append(time.perf_counter_ns()-start)
  after=call('metrics');assert after['seed_rows']==before['seed_rows'];assert after['changed_rows']-before['changed_rows']==40;assert after['groups_touched']-before['groups_touched']<81;assert after['shapes']==1
  ps=subprocess.check_output(['/bin/ps','-o','%cpu=,rss=','-p',str(p.pid)],text=True).strip();a=sorted(samples);records.append(dict(size=size,mode=mode,initial_build_ns=build,samples_ns=samples,p50_ns=a[math.ceil(.5*len(a))-1],p95_ns=a[math.ceil(.95*len(a))-1],metrics_before=before,metrics_after=after,cpu_percent_rss_kib=ps))
  p.stdin.close();assert p.wait()==0
out=W/'evidence/grouped/native-performance.json';out.write_text(json.dumps(dict(scope='persistent native subprocess; whole JSON RPC apply + bounded ranked read; no broker/DOM claim',quantile='nearest rank ceil(p*N)-1',records=records),indent=2));print('PASS',len(records),'conditions x 40 updates')
