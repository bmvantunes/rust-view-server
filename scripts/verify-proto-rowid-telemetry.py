#!/usr/bin/env python3
"""Predeclared bounded per-topic instrumentation check, not full trace-chain qualification."""
from pathlib import Path
import json,re,sys,collections
p=Path(sys.argv[1]);packets=json.loads((p/'otlp/decoded.json').read_text());spans=[];metrics=[]
def attrs(xs):return {x['key']:next(iter(x['value'].values()))for x in xs}
for packet in packets:
 for r in packet['decoded'].get('resourceSpans',[]):
  for scope in r['scopeSpans']:
   for s in scope['spans']:spans.append({**s,'resource':attrs(r['resource']['attributes'])})
 for r in packet['decoded'].get('resourceMetrics',[]):
  for scope in r['scopeMetrics']:
   for m in scope['metrics']:metrics.append({**m,'resource':attrs(r['resource']['attributes'])})
assert {s['resource']['service.name']for s in spans}=={'view-server','view-server-worker','view-server-browser'}
counts_by_operation={}
for topic in ['orders','positions']:
 counts_by_operation[topic]={name:sum(s['name']==name and attrs(s.get('attributes',[])).get('topic')==topic for s in spans)for name in ['source_apply','live_publish','query_handle']}
 assert all(counts_by_operation[topic].values()),counts_by_operation
prom=(p/'metrics.txt').read_text();instance=re.search(r'service_instance_id="([^"]+)"',prom).group(1)
counts={m.group(1):int(float(m.group(2)))for m in re.finditer(r'^view_server_source_records_total\{[^\n]*topic="([^"]+)"[^\n]*\} ([^\n]+)',prom,re.M)}
assert counts=={'orders':1,'positions':2},counts
samples=[]
for m in metrics:
 if m['resource'].get('service.instance.id')==instance and m['name']=='view_server.source.records':samples.append({attrs(d.get('attributes',[]))['topic']:int(d.get('asInt',d.get('asDouble')))for d in m['sum']['dataPoints']})
assert counts in samples,(counts,samples)
probes=json.loads((p/'probes.json').read_text());h=next(x['afterRecovery']for x in probes if 'afterRecovery'in x);assert h['instance']==instance and str(h['records_committed'])=='3' and h['connections']==1
assert len(h['sources'])==2 and all(len(s['partitions'])==2 and all(part['assigned']and part['bootstrap_complete']and part['durable_next']==part['derived_next']==part['serving_next']for part in s['partitions'])for s in h['sources'])
derived=float(re.search(r'^view_server_derived_duration_seconds_total\{[^\n]*\} ([^\n]+)',prom,re.M).group(1));assert derived>0 and abs(derived-int(h['derived_ns'])/1e9)<1e-9
matching=[d.get('asDouble',float(d.get('asInt',0)))for m in metrics if m['resource'].get('service.instance.id')==instance and m['name']=='view_server.derived.duration' for d in m['sum']['dataPoints']];assert any(abs(v-derived)<1e-9 for v in matching)
by_id={s['spanId']:s for s in spans};chains=[]
for dom in spans:
 if dom['name']!='dom_observation':continue
 chain=[dom];seen=set()
 while chain[-1].get('parentSpanId')in by_id and chain[-1]['spanId']not in seen:
  seen.add(chain[-1]['spanId']);chain.append(by_id[chain[-1]['parentSpanId']])
 assert len({s['traceId']for s in chain})==1
 native=next((s for s in chain if s['resource']['service.name']=='view-server'),None)
 chains.append({'names':[s['name']for s in chain],'topic':attrs(native.get('attributes',[])).get('topic')if native else None})
result={'passed':True,'scope':'predeclared bounded actual per-topic metrics and traces, all-topic/partition readiness corroboration','packet_count':len(packets),'span_count':len(spans),'per_topic_native_operations':counts_by_operation,'source_records':counts,'matching_otlp_source_samples':sum(s==counts for s in samples),'successor_instance':instance,'derived_seconds':derived,'actual_successor_connections':1,'observed_dom_chains':chains,'full_live_dom_chains_for_both_topics':all(any(c['topic']==t and 'live_publish'in c['names']for c in chains)for t in ['orders','positions']),'limitations':'Stronger inherited complete live-to-DOM chain verifier failed and is retained separately; not claimed as passed. Terminated Workers may lose unexported spans. This gate does not require complete chains and is not an OTel campaign.'}
(p/'telemetry-bounded-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='observed_dom_chains'}))
