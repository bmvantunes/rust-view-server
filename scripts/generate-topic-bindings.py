#!/usr/bin/env python3
"""Build pinned protobuf descriptors from the authored portable catalog.
No dependencies or generated server code; generated descriptors are startup inputs.
Usage: generate-topic-bindings.py CATALOG OUTPUT BROKERS UNIQUE_PREFIX
"""
import hashlib,json,sys
from pathlib import Path

def vi(n):
    out=bytearray()
    while n>127:out.append((n&127)|128);n>>=7
    out.append(n);return bytes(out)
def field(tag,value):
    if isinstance(value,int):return vi(tag<<3)+vi(value)
    if isinstance(value,str):value=value.encode()
    return vi((tag<<3)|2)+vi(len(value))+value

def descriptor(name,fields,schema_id):
    message=field(1,name)
    for index,(name,tag,kind) in enumerate(fields):
        f=field(1,name)+field(3,tag)+field(4,1)+field(5,kind)+field(9,index)+field(17,1)
        message+=field(2,f)
    for name,_,_ in fields:message+=field(8,field(1,'_'+name))
    file=field(1,name+'.proto')+field(4,message)+field(12,'proto3')
    return dict(schema_id=schema_id,message_index=0,descriptor_hex=field(1,file).hex())

catalog=json.loads(Path(sys.argv[1]).read_text());output=Path(sys.argv[2]);brokers=sys.argv[3];prefix=sys.argv[4]
kinds={'string':9,'boolean':8,'number':1,'int64':3,'uint64':4,'decimal':9}
schemas={hashlib.sha256(json.dumps(s,separators=(',',':'),ensure_ascii=False).encode()).hexdigest():s for s in catalog['schemas']}
result=[]
for index,t in enumerate(catalog['topics']):
    s=schemas[t['schema']];fields=[];mapping=[]
    for n,f in enumerate(s['fields'],1):fields.append((f['name'],n,kinds[f['kind']]));mapping.append(dict(field=f['name'],tag=n))
    for f,m in zip(s['fields'],mapping):
        if f['nullable']:
            tag=len(fields)+1;fields.append(('null_'+f['name'],tag,8));m['null_tag']=tag
    result.append(dict(topic=t['topic'],schema=t['schema'],brokers=brokers,source_topic=prefix+'-'+t['topic'],source_incarnation=prefix+'-'+t['topic']+'-lifetime',group=prefix+'-'+t['topic']+'-owner',state_topic=prefix+'-'+t['topic']+'-canonical-v2',initialize_empty=True,partitions=[0,1],key_descriptor=descriptor('Key',[('id',1,9)],index*2+1),value_descriptor=descriptor(s['id'],fields,index*2+2),key_tag=1,mapping=mapping,readiness=dict(enter_offset_distance=64,exit_offset_distance=256,max_sample_age_ms=5000,enter_hold_ms=2000,exit_hold_ms=1000),max_rows=100000))
output.write_text(json.dumps(result,indent=2)+'\n')
