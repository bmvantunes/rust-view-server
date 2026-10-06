#!/usr/bin/env python3
"""Verify supplied actual OTLP protobuf decodes and Prometheus for one ordinary run."""
from pathlib import Path
import json,sys,re
p=Path(sys.argv[1]); packets=json.loads((p/'otlp/decoded.json').read_text())
def attrs(xs): return {x['key']:next(iter(x['value'].values())) for x in xs}
spans=[];metrics=[]
for packet in packets:
 for r in packet['decoded'].get('resourceSpans',[]):
  for scope in r['scopeSpans']:
   for s in scope['spans']: spans.append({**s,'resource':attrs(r['resource']['attributes'])})
 for r in packet['decoded'].get('resourceMetrics',[]):
  for scope in r['scopeMetrics']:
   for m in scope['metrics']: metrics.append({**m,'resource':attrs(r['resource']['attributes'])})
by_id={s['spanId']:s for s in spans};checks=[]
for s in spans:
 assert s['resource']['service.name'] in ['view-server','view-server-browser','view-server-worker']
 assert len(s.get('attributes',[]))<=8 and len(s.get('links',[]))<=4
 assert not set(attrs(s.get('attributes',[])))&{'query','row','token','password','baggage'}
 names={'query_handle':'worker_command','hook_delivery':'worker_reconstruct','dom_observation':'hook_delivery','live_publish':'source_apply'}
 if s['name'] in names:
  parent=by_id.get(s.get('parentSpanId'))
  if parent:
   assert parent['name']==names[s['name']],(s,parent)
   assert parent['traceId']==s['traceId']
   checks.append({'edge':parent['name']+' -> '+s['name'],'trace':s['traceId']})
# Require complete cross-runtime chains all the way to DOM for both configured topics.
chains=[]
for dom in spans:
 if dom['name']!='dom_observation':continue
 chain=[dom];seen=set()
 while chain[-1].get('parentSpanId') in by_id and chain[-1]['spanId'] not in seen:
  seen.add(chain[-1]['spanId']);chain.append(by_id[chain[-1]['parentSpanId']])
 assert len({s['traceId'] for s in chain})==1
 native=next((s for s in chain if s['name'] in ['query_handle','live_publish']),None)
 if native:
  names=[s['name'] for s in chain];topic=attrs(native['attributes']).get('topic')
  assert names[:3]==['dom_observation','hook_delivery','worker_reconstruct']
  if native['name']=='query_handle':assert names[3:]==['query_handle','worker_command','query_acquisition'],names
  else:assert names[3:]==['live_publish','source_apply'],names
  chains.append({'topic':topic,'instance':native['resource']['service.instance.id'],'trace':dom['traceId'],'chain':names})
for topic in ['orders','positions']:
 assert any(c['topic']==topic and 'query_handle' in c['chain'] for c in chains),topic
 assert any(c['topic']==topic and 'live_publish' in c['chain'] for c in chains),topic
instances={c['instance'] for c in chains if c['topic'] in ['orders','positions']};assert len(instances)>=2
trace_sets={i:{c['trace'] for c in chains if c['instance']==i} for i in instances}
for a in instances:
 for b in instances:
  if a!=b:assert not trace_sets[a]&trace_sets[b]
# Compare an idle successor's exact per-topic source totals in both actual exporters.
prom=(p/'metrics.txt').read_text();instance=re.search(r'service_instance_id="([^"]+)"',prom).group(1)
counts={m.group(1):int(float(m.group(2))) for m in re.finditer(r'^view_server_source_records_total\{[^\n]*topic="([^"]+)"[^\n]*\} ([^\n]+)',prom,re.M)}
assert counts=={'orders':1,'positions':2},counts
samples=[]
for m in metrics:
 if m['resource'].get('service.instance.id')==instance and m['name']=='view_server.source.records':
  data={attrs(d.get('attributes',[]))['topic']:int(d.get('asInt',d.get('asDouble'))) for d in m['sum']['dataPoints']};samples.append(data)
assert counts in samples,(counts,samples)
probes=json.loads((p/'probes.json').read_text());successor=next(x['afterRecovery'] for x in probes if 'afterRecovery' in x)
assert successor['instance']==instance
assert str(successor['records_committed'])=='3',successor['records_committed']
after_recovery=next(x['afterRecovery'] for x in probes if 'afterRecovery' in x)
assert all(int(part['fetched_next'])>=int(part['durable_next']) for source in after_recovery['sources'] for part in source['partitions'])
assert int(successor['derived_ns'])>0
prom_derived=float(re.search(r'^view_server_derived_duration_seconds_total\{[^\n]*\} ([^\n]+)',prom,re.M).group(1))
assert prom_derived>0
assert abs(prom_derived-int(successor['derived_ns'])/1e9)<1e-9
matching_derived=[d.get('asDouble',float(d.get('asInt',0))) for m in metrics if m['resource'].get('service.instance.id')==instance and m['name']=='view_server.derived.duration' for d in m['sum']['dataPoints']]
assert any(abs(v-prom_derived)<1e-9 for v in matching_derived)
after_recovery=next(x['afterRecovery'] for x in probes if 'afterRecovery' in x)
assert after_recovery['connections']==1
result={'passed':True,'actual_network_export':True,'span_count':len(spans),'packet_count':len(packets),'native_instances':sorted(instances),'prometheus_instance':instance,'source_records':counts,'derived_duration_seconds':prom_derived,'actual_successor_connections':after_recovery['connections'],'matching_otlp_samples':sum(s==counts for s in samples),'complete_chains':chains,'limitations':'Requires captured complete chains; terminated workers can lose unexported spans. DOM observation is not physical paint; no cross-host clock accuracy claim.'}
(p/'telemetry-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='complete_chains'}))
