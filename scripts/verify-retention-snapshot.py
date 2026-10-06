#!/usr/bin/env python3
"""Independent JSON/digest/root fold of captured read-committed canonical records."""
import json,hashlib,sys
from pathlib import Path

def encoded(v):return json.dumps(v,separators=(',',':'),ensure_ascii=False).encode()
def fold(path):
 result={}
 for topic in map(json.loads,Path(path).read_text().splitlines()):
  if topic['kind']!='state_topic':continue
  latest={};binding=None;checked=0
  for record in sorted(topic['records'],key=lambda r:(r['partition'],r['offset'])):
   envelope=json.loads(record['payload_utf8']);p=record['partition'];key=bytes.fromhex(record['key_hex']);value=envelope['value'];b=envelope['binding'];fmt=envelope['format']
   assert fmt==3 and b['format']==3
   if binding is None:binding=b
   assert binding==b
   expected=hashlib.sha256(encoded([fmt,b,p,list(key),value])).digest()
   assert list(expected)==envelope['digest'],('envelope digest',p,record['offset'])
   kinds={'row':1,'next':2,'manifest':3,'barrier':4};assert key==bytes([3,kinds[value['kind']]])+(value['key'].encode() if value['kind']=='row' else b'')
   latest[p,key]=value;checked+=1
  rows={};nexts={};manifest=None;root=bytearray(32)
  for (p,key),v in latest.items():
   if v['kind']=='row':
    assert p==v['owner'];assert v['key'] not in rows;rows[v['key']]=v
    contribution=hashlib.sha256(encoded([v['key'],v['owner'],v['key_identity'],v['row'],v.get('age_origin_ms'),v.get('retention_order')])).digest()
    for i,b in enumerate(contribution):root[i]^=b
   elif v['kind']=='next':nexts[str(p)]=v['next']
   elif v['kind']=='manifest':assert p==0;manifest=v
  assert manifest and manifest['next']==nexts and manifest['root']==list(root)
  assert manifest['content_version']==manifest['sequence']+manifest['maintenance_sequence']
  active={k:v for k,v in rows.items() if v['row'] is not None};deleted={k:v for k,v in rows.items() if v['row'] is None}
  for v in active.values():assert 'retention_order'in v and v['retention_order']<=manifest['next_order'] and 'age_origin_ms'in v
  for v in deleted.values():assert 'retention_order'not in v and 'age_origin_ms'not in v
  result[topic['logical_topic']]={'binding':binding,'rows':rows,'next':nexts,'manifest':manifest,'active_count':len(active),'sticky_deleted_count':len(deleted),'root_hex':root.hex()}
  print('FOLDED',topic['logical_topic'],'envelopes',checked,'active',len(active),'sticky_deleted',len(deleted),file=sys.stderr)
 return result
if __name__=='__main__':
 before=fold(sys.argv[1]);after=fold(sys.argv[2]) if len(sys.argv)>2 else before
 assert before==after,'canonical logical image/root/metadata changed across cleaner/recovery'
 assert all(t['active_count']>0 and t['sticky_deleted_count']>0 for t in before.values())
 print(json.dumps({'status':'PASS','logical_images':before},indent=2))
