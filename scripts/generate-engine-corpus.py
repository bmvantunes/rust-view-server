"""Independent integer arithmetic oracle. --check verifies the persisted fixture.
No selected engine imports, sort tokens, ranking helpers or threshold implementation.
"""
from pathlib import Path
from copy import deepcopy
from functools import cmp_to_key
import json, sys

def decimal(c, s=0):
    c=int(c)
    if c==0:s=0
    while c and c%10==0 and s>-10000:c//=10;s-=1
    return {'coefficient':str(c),'scale':s}
def number(a,b):
    s=max(a['scale'],b['scale'])
    x=int(a['coefficient'])*10**(s-a['scale']); y=int(b['coefficient'])*10**(s-b['scale'])
    return (x>y)-(x<y)
def cmp(op,c):return {'equal':c==0,'greater_than':c>0,'greater_than_or_equal':c>=0,'less_than':c<0,'less_than_or_equal':c<=0}[op]
def empty(e):return e['op'] in ['and','or'] and not e['args']
def matches(e,r):
    op=e['op'];a=e.get('args')
    if op=='true':return True
    if op=='false':return False
    if op in ['and','or']:
        xs=[matches(x,r) for x in a if not empty(x)]
        return all(xs) if op=='and' else (not xs or any(xs))
    if op=='not':return True if empty(a) else not matches(a,r)
    f=a['field'];v=a.get('condition')
    if f=='category_equals':return r['category']==v
    if f=='label_equals':return r['label']=={'state':'value','value':v}
    if f in ['label_blank','label_not_blank']:
        blank=r['label']['state']!='value' or r['label']['value']==''
        return blank if f=='label_blank' else not blank
    if f=='quantity':c=(int(r[f])>int(v['value']))-(int(r[f])<int(v['value']))
    elif f=='amount':c=number(r[f],v['value'])
    else:raise ValueError(f)
    return cmp(v['op'],c)
def row(i,c,s=0,cat='a',label=None,q='9007199254740993'):
    return {'id':i,'category':cat,'quantity':q,'amount':decimal(c,s),'label':label or {'state':'missing'}}
def cond(f,v=None):return {'op':'condition','args':{'field':f,**({'condition':v} if v is not None else {})}}
def query(e=None,o=0,n=3,d='ascending'):return {'where_expr':e or {'op':'true'},'offset':o,'limit':n,'direction':d}
steps=[]
def add(name,command,error=False):steps.append({'name':name,'command':command,**({'error':True} if error else {})})
def put(r,name='upsert'):add(name,{'command':'upsert','row':r})
def opening(i,q):add('open '+i,{'command':'open','subscription':i,'query':q})
def window(i,o,n):add('window '+i,{'command':'change_window','subscription':i,'offset':o,'limit':n})
for r in [row('n-prefix',-12,1),row('n-long',-121,2),row('tie-b',125,2),row('tie-a',1250,3),row('zero',0),row('tiny',1,10000),row('huge',1,-10000),row('other',2,cat='b',label={'state':'null'})]:put(r,'initial '+r['id'])
opening('first',query());opening('middle',query(o=2));opening('end',query(o=7,n=4));opening('beyond',query(o=100));opening('zero-window',query(n=0));opening('desc',query(d='descending',n=20))
a=cond('category_equals','a');b=cond('category_equals','b')
opening('singleton-in',query({'op':'or','args':[a]}));opening('multi-in',query({'op':'or','args':[a,b]}));opening('unaffected',query(cond('category_equals','never')))
opening('range',query({'op':'and','args':[cond('amount',{'op':'greater_than_or_equal','value':decimal(-12,1)}),cond('amount',{'op':'less_than','value':decimal(2)})]}))
opening('quantity',query(cond('quantity',{'op':'equal','value':'9007199254740993'})))
opening('blank',query(cond('label_blank')))
put(row('tie-a',12500,4),'normalized equivalent no-op')
steps[-1]['command']['row']['amount']={'coefficient':'12500','scale':4}
put(row('tie-a',125,2,q='9223372036854775807'),'selected field only')
put(row('outside',900,cat='a'),'offscreen total');put(row('outside',900,cat='z'),'predicate membership replacement')
put(row('before',-9),'insert before');put(row('inside',-119,2),'insert inside')
add('delete before',{'command':'delete','id':'before'});add('delete inside',{'command':'delete','id':'inside'})
put(row('tie-b',-5),'rank replacement');add('delete/reinsert deletion',{'command':'delete','id':'zero'});put(row('zero',0),'delete/reinsert insertion')
window('first',3,3);window('first',3,3);window('first',20,3);window('first',0,0);window('first',0,20)
add('failed replacement',{'command':'change_query','subscription':'first','query':query(o=18446744073709551615,n=1)},True)
add('successful replacement',{'command':'change_query','subscription':'first','query':query(b,n=8)})
put(row('other',2,cat='b',label={'state':'value','value':'hi'}),'null to value');put(row('other',2,cat='b',label={'state':'missing'}),'value to missing')
for i in ['middle','singleton-in','range']:add('staggered close',{'command':'close','subscription':i})
for i in ['n-prefix','n-long','tie-a','tie-b','zero','tiny','huge','other','outside']:add('shrink delete '+i,{'command':'delete','id':i})
add('absent delete no-op',{'command':'delete','id':'absent'})
for i in ['first','end','beyond','zero-window','desc','multi-in','unaffected','quantity','blank']:add('final release '+i,{'command':'close','subscription':i})
opening('reopened',query());add('final close reopened',{'command':'close','subscription':'reopened'})

rows={};subs={};version=topic=gen=0
for step in steps:
    c=step['command'];op=c['command'];dirty=[];changed=False
    if not step.get('error'):
        if op in ['upsert','delete']:
            key=c['row']['id'] if op=='upsert' else c['id'];old=rows.get(key);new=deepcopy(c.get('row'))
            if new:new['amount']=decimal(new['amount']['coefficient'],new['amount']['scale']);new['quantity']=str(int(new['quantity']))
            changed=old!=new
            if changed:
                dirty=[s for s,(q,_,_) in subs.items() if (old and matches(q['where_expr'],old)) or (new and matches(q['where_expr'],new))]
                if new:rows[key]=new
                else:rows.pop(key,None)
                topic+=1
        elif op in ['open','change_query']:
            s=c['subscription'];q=c['query'];changed=s not in subs or subs[s][0]!=q
            if changed:gen+=1;subs[s]=(q,gen,0);dirty=[s]
        elif op=='change_window':
            s=c['subscription'];q,g,seq=subs[s];changed=(q['offset'],q['limit'])!=(c['offset'],c['limit'])
            if changed:q={**q,'offset':c['offset'],'limit':c['limit']};subs[s]=(q,g,seq+1);dirty=[s]
        elif op=='close':del subs[c['subscription']];changed=True
        if changed:version+=1
    results={}
    for s,(q,g,seq) in sorted(subs.items()):
        def order(a,b):
            v=number(a['amount'],b['amount'])*(1 if q['direction']=='ascending' else -1)
            return v or ((a['id']>b['id'])-(a['id']<b['id']))
        rr=sorted([r for r in rows.values() if matches(q['where_expr'],r)],key=cmp_to_key(order))
        results[s]={'subscription':s,'query_generation':g,'sequence':seq,'start_rank':q['offset'],'version':version,'total_rows':len(rr),'rows':deepcopy(rr[q['offset']:q['offset']+q['limit']])}
    step['expected']={'product_version':version,'topic_version':topic,'dirty_subscriptions':sorted(dirty),'results':results}
fixture={'format':'product-engine-contract-v1','oracle':'scripts/generate-engine-corpus.py (independent scaled integers)','steps':steps,'unsupported':[{'command':'open','subscription':'x','query':query({'op':'join','args':[]})},{'command':'aggregate','function':'count_distinct'},{'command':'open','subscription':'x','query':query({'op':'condition','args':{'field':'regex','condition':'.*'}})}]}
fixture['unsupported'].append({'command':'open','subscription':'x','query':{**query(),'multiple_sort':['amount','quantity']}})
out=Path(__file__).resolve().parent.parent/'contract-tests/engine-golden.json'
text=json.dumps(fixture,indent=2)+'\n'
if '--check' in sys.argv:
    assert out.read_text()==text,'golden fixture differs from independent generator'
else:out.write_text(text)
print(json.dumps({'steps':len(steps),'completed_results':sum(len(s['expected']['results']) for s in steps),'unsupported':len(fixture['unsupported'])}))
