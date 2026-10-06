from pathlib import Path
import json,sys,base64
p=Path(sys.argv[1]);e=json.loads((p/'kafka-health.json').read_text());spans=e['spans'];by_id={s['spanId']:s for s in spans};checks=[]
for s in spans:
 assert s['resource']['service.name'] in ['view-server','view-server-browser','view-server-worker']
 assert len(s.get('attributes',[]))<=8 and len(s.get('links',[]))<=4
 assert not any(a['key'] in ['query','row','token','password','baggage'] for a in s.get('attributes',[]))
 if s['name']=='query_handle':
  parent=by_id.get(s.get('parentSpanId'));assert parent and parent['name']=='worker_command',s
  acquisition=by_id.get(parent.get('parentSpanId'));assert acquisition and acquisition['name']=='query_acquisition',parent
  assert s['traceId']==parent['traceId']==acquisition['traceId'];checks.append({'operation':'acquisition','trace':s['traceId'],'server_instance':s['resource']['service.instance.id'],'worker_instance':parent['resource']['service.instance.id']})
 if s['name']=='hook_delivery':
  parent=by_id.get(s.get('parentSpanId'));assert parent and parent['name']=='worker_reconstruct';assert parent['traceId']==s['traceId'];up=by_id.get(parent.get('parentSpanId'))
  if up:assert up['name'] in ['query_handle','live_publish'];assert up['traceId']==s['traceId'];checks.append({'operation':'returned_snapshot' if up['name']=='query_handle' else 'live_delivery','trace':s['traceId'],'server_instance':up['resource']['service.instance.id']})
 if s['name']=='dom_observation':
  parent=by_id.get(s.get('parentSpanId'));assert parent and parent['name']=='hook_delivery';assert parent['traceId']==s['traceId'];checks.append({'operation':'DOM_observed_not_paint','trace':s['traceId']})
superseded=[s for s in spans if any(a['key']=='outcome' and a['value'].get('stringValue')=='superseded' for a in s.get('attributes',[]))];assert superseded
assert not any(s['name']=='worker_command' and s['traceId'] in {x['traceId'] for x in superseded} for s in spans),'superseded local operation must not be dispatched'
instances={c['server_instance'] for c in checks if c['operation']=='acquisition'};assert len(instances)==2,instances
traces_per={i:{c['trace'] for c in checks if c.get('server_instance')==i} for i in instances};a,b=list(traces_per.values());assert not a&b,'new incarnation must reacquire with new operation contexts'
assert all(any(c['operation']==name for c in checks) for name in ['acquisition','returned_snapshot','live_delivery','DOM_observed_not_paint'])
# Distinct overlapping requests are observable even when native handling is serial.
acquisitions=[s for s in spans if s['name']=='query_acquisition'];overlap=any(a['traceId']!=b['traceId'] and max(int(a['startTimeUnixNano']),int(b['startTimeUnixNano']))<min(int(a['endTimeUnixNano']),int(b['endTimeUnixNano'])) for n,a in enumerate(acquisitions) for b in acquisitions[n+1:]);assert overlap
result={'passed':True,'actual_network_export':True,'span_count':len(spans),'server_instances':sorted(instances),'overlapping_distinct_traces':overlap,'superseded_not_dispatched':len(superseded),'checks':checks,'limitations':'Worker termination may drop unexported spans. This verifier requires complete captured operation chains used as evidence; no clock correlation claim.'};(p/'trace-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='checks'}))
