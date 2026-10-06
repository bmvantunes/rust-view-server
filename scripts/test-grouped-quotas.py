#!/usr/bin/env python3
from pathlib import Path
import subprocess,json,hashlib,time
W=Path(__file__).resolve().parents[1];results=[]
for mode,limit in [('groups',65536),('values',16384)]:
 p=subprocess.Popen([W/'native/target/debug/examples/grouped_probe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 def call(op,fail=False,**kw):
  p.stdin.write(json.dumps(dict(op=op,topic='quota',schema=fp,**kw),separators=(',',':'))+'\n');p.stdin.flush();v=json.loads(p.stdout.readline());assert ('error'in v)==fail,v;return v
 schema=dict(format=1,id='quota',version=1,key='id',fields=[dict(name=n,kind='string',optional=False,nullable=False)for n in ['id','g','v']]);fp=hashlib.sha256(json.dumps(schema,separators=(',',':')).encode()).hexdigest();call('init',catalog=dict(format=1,schemas=[schema],topics=[dict(topic='quota',schema=fp)]))
 def row(i):return dict(id=str(i),g=str(i)if mode=='groups'else 'one',v=str(i))
 for start in range(0,limit,1024):call('apply',mutations=[dict(kind='upsert',row=row(i))for i in range(start,min(start+1024,limit))])
 aggs={'n':dict(aggFunc='count')}if mode=='groups'else {f'd{i}':dict(aggFunc='countDistinct',field='v')for i in range(16)}
 call('open',sub='g',query=dict(group_by=['g'],aggregates=aggs,order_by=[]));call('open',sub='raw',query=dict(select=['v'],order_by=[]));before=call('read',sub='g',offset=0,limit=1);call('apply',mutations=[dict(kind='upsert',row=row(limit))]);error=call('read',sub='g',fail=True);raw=call('read',sub='raw',offset=0,limit=1);assert raw['ok']['total_rows']==limit+1
 results.append(dict(mode=mode,limit=limit,before=before,error=error,raw=raw,metrics=call('metrics')));p.stdin.close();assert p.wait()==0
(W/'evidence/grouped/quotas.json').write_text(json.dumps(dict(status='PASS',results=results),indent=2));print('PASS live actual group and retained multiset limits; raw and source survive')
