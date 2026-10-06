#!/usr/bin/env python3
"""Independent Python Fraction/Decimal full rescan oracle; candidate is native Rust."""
from pathlib import Path
import subprocess,json,hashlib,random,struct,decimal,time
from fractions import Fraction
W=Path(__file__).resolve().parents[1];out=W/'evidence/grouped/oracle';out.mkdir(parents=True,exist_ok=True)
log=open(out/f'cuts-{time.time_ns()}.jsonl','w');proc=subprocess.Popen([W/'native/target/debug/examples/grouped_probe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
def call(v,fail=False):
 proc.stdin.write(json.dumps(v,separators=(',',':'))+'\n');proc.stdin.flush();r=json.loads(proc.stdout.readline());log.write(json.dumps({'request':v,'response':r},ensure_ascii=False)+'\n');log.flush()
 if fail: assert 'error'in r,r;return r
 assert 'ok'in r,r
 return r['ok']
def compact(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
fields=[dict(name='id',kind='string',optional=False,nullable=False),dict(name='g',kind='string',optional=True,nullable=True),dict(name='active',kind='boolean',optional=False,nullable=False)]+[dict(name=k,kind=k,optional=True,nullable=True)for k in ['string','boolean','number','int64','uint64','decimal']]
schema=dict(format=1,id='oracle',version=1,key='id',fields=fields);fp=hashlib.sha256(compact(schema).encode()).hexdigest();catalog=dict(format=1,schemas=[schema],topics=[dict(topic='oracle',schema=fp)])
call(dict(op='init',catalog=catalog));source={};queries={};cuts=0;checks=0
for k in ['string','boolean','number','int64','uint64','decimal']:
 aggs={op:dict(aggFunc=op,**({}if op=='count'else dict(field=k)))for op in ['count','countDistinct','min','max']+(['sum','avg']if k not in ['string','boolean']else [])}
 q=dict(group_by=['g'],aggregates=aggs,where=dict(op='eq',field='active',value=True),order_by=[dict(aggregate='count',direction='desc'),dict(field='g',direction='asc')]);queries[k]=q;call(dict(op='open',sub=k,topic='oracle',schema=fp,query=q))
call(dict(op='open',sub='raw',topic='oracle',schema=fp,query=dict(select=['id'],order_by=[dict(field='id',direction='asc')])))
def tag(r,k):return (0,None)if k not in r else (1,None)if r[k]is None else (2,r[k])
def exact(k,v):return Fraction.from_float(v)if k=='number'else Fraction(v)
def canonical(v):
 s=format(v,'f');s=s.rstrip('0').rstrip('.')if'.'in s else s
 return '0'if s in ['-0','']else s
def gid(group):
 state,value=group;return 'gid1:'+compact([1,'oracle',fp,[['g','string',state,value]]]).encode().hex()
def expected(k):
 groups={}
 for r in source.values():
  if r['active']:groups.setdefault(tag(r,'g'),[]).append(r)
 ans=[]
 for g,rs in groups.items():
  row={}if g[0]==0 else {'g':g[1]};present=[r[k]for r in rs if k in r and r[k]is not None];row['count']=str(len(rs));row['countDistinct']=str(len({compact(tag(r,k))for r in rs}))
  key=(lambda v:exact(k,v))if k not in ['string','boolean']else lambda v:v
  row['min']=min(present,key=key)if present else None;row['max']=max(present,key=key)if present else None
  if k not in ['string','boolean']:
   total=sum((exact(k,v)for v in present),Fraction(0));avg=total/len(present)if present else None
   if k=='number':row.update(sum=float(total),avg=float(avg)if avg is not None else None)
   else:
    with decimal.localcontext()as c:
     c.prec=800;c.rounding=decimal.ROUND_HALF_EVEN
     to_dec=lambda v:decimal.Decimal(v.numerator)/decimal.Decimal(v.denominator)
     row.update(sum=canonical(to_dec(total)),avg=canonical(to_dec(avg).quantize(decimal.Decimal('1e-18')))if avg is not None else None)
  ans.append((g,gid(g),row))
 ans.sort(key=lambda x:(-int(x[2]['count']),x[0][0],x[0][1]or'',x[1]));return ans
def verify():
 global checks
 for k in queries:
  want=expected(k)
  for off,lim in [(0,1024),(1,2),(7,1),(40,0),(40,3)]:
   got=call(dict(op='read',sub=k,offset=off,limit=lim));window=want[off:off+lim];assert got['total_rows']==len(want),(k,got,want);assert got['keys']==[r[1]for r in window],(k,got,want);assert got['rows']==[r[2]for r in window],(cuts,k,got,want);checks+=1
 got=call(dict(op='read',sub='raw'));assert got['rows']==[{'id':k}for k in sorted(source)]
def apply(ms):
 global cuts
 call(dict(op='apply',topic='oracle',schema=fp,mutations=ms))
 for m in ms:
  if m['kind']=='upsert':source[m['row']['id']]=m['row']
  else:source.pop(m['key'],None)
 cuts+=1;verify()
def put(i,**kw):return dict(kind='upsert',row=dict(id=str(i),active=True,**kw))
def delete(i):return dict(kind='delete',key=str(i))
# Fixed lifecycle, missing/null/blank, duplicate final removal, exact extremes.
for ms in [[put(1,g='雪',string='',boolean=False,number=0,int64='-9223372036854775808',uint64='18446744073709551615',decimal='999999999999999999999.000000000000000001')],[put(2,g='雪',string='',boolean=False,number=0,int64='-9223372036854775808',uint64='18446744073709551615',decimal='999999999999999999999.000000000000000001')],[delete(1)],[delete(2)],[put(1,g=None),put(2),put(3,g='',string=None),put(4,g='',string='')],[put(3,g='moved',string='x')],[put(3,g='moved',string='x')],[delete(3),put(3,g='moved',string='x')],[put(5,g='cancel',number=1e16),put(6,g='cancel',number=1),put(7,g='cancel',number=-1e16)],[delete(5),delete(7)],[put(8,g='third',int64='1'),put(9,g='third',int64='0'),put(10,g='third',int64='0')]]:apply(ms)
rng=random.Random(751112);gs=[None,'','a','ab','雪','é','e\u0301','🙂']
values={'string':['','x','é','雪','\u0000'], 'boolean':[False,True], 'number':[-1e16,1e16,-0.0,5e-324,1.5,-2.25,1.7976931348623157e308/16], 'int64':['-9223372036854775808','9223372036854775807','0','1','-7'],'uint64':['18446744073709551615','0','1','8'],'decimal':['-1','0','0.0000000000000000000000000000000000000001','999999999999999999999999999.7','1.5']}
for cut in range(160):
 ms=[]
 for _ in range(rng.randrange(1,7)):
  i=rng.randrange(24)
  if rng.random()<.2:ms.append(delete(i));continue
  row=dict(id=str(i),active=rng.random()>.2)
  if rng.random()>.2:row['g']=rng.choice(gs)
  for k,vs in values.items():
   state=rng.randrange(5)
   if state==1:row[k]=None
   elif state>1:row[k]=rng.choice(vs)
  ms.append(dict(kind='upsert',row=row))
 apply(ms)
# Rebuild same canonical state in a separate runtime/process, compare complete IDs/values.
proc.stdin.close();assert proc.wait()==0
proc=subprocess.Popen([W/'native/target/debug/examples/grouped_probe'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True);call(dict(op='init',catalog=catalog))
call(dict(op='apply',topic='oracle',schema=fp,mutations=[dict(kind='upsert',row=r)for r in reversed(list(source.values()))]))
for k,q in queries.items():call(dict(op='open',sub=k,topic='oracle',schema=fp,query=q))
call(dict(op='open',sub='raw',topic='oracle',schema=fp,query=dict(select=['id'],order_by=[dict(field='id',direction='asc')])));verify()
apply([delete(k)for k in list(source)]);apply([put(1,g='reinsert',int64='3',number=1)])
# Failed replacement preserves old raw acquisition, grouped overflow does not poison source/raw.
call(dict(op='open',sub='raw',topic='oracle',schema=fp,query=dict(group_by=['g'],aggregates={'g':dict(aggFunc='count')},order_by=[])),True)
call(dict(op='apply',topic='oracle',schema=fp,mutations=[put(2,g='overflow',number=1.7976931348623157e308),put(3,g='overflow',number=1.7976931348623157e308)]));call(dict(op='read',sub='number'),True);assert len(call(dict(op='read',sub='raw'))['rows'])==3
proc.stdin.close();assert proc.wait()==0
(out/'result.json').write_text(json.dumps(dict(status='PASS',completed_cuts=cuts,window_comparisons=checks,seed=751112,oracle='Python full-rescan Fraction/Decimal, native Rust persistent subprocess',rebuild=True),indent=2));print('PASS',cuts,checks)
