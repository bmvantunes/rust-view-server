"""Independent Prometheus parser + standard OTLP protobuf-decoded captures."""
from pathlib import Path
import json,sys,statistics
from prometheus_client.parser import text_string_to_metric_families
root=Path(sys.argv[1]);captures=json.loads((root/'otlp/decoded.json').read_text());series=[]
for c in captures:
 if c['type']!='metrics':continue
 for resource in c['decoded'].get('resourceMetrics',[]):
  attrs={a['key']:a['value'].get('stringValue') for a in resource['resource']['attributes']}
  for scope in resource.get('scopeMetrics',[]):
   for metric in scope.get('metrics',[]):
    if metric['name']=='view_server.source.records':
     assert metric['sum']['aggregationTemporality']=='AGGREGATION_TEMPORALITY_CUMULATIVE'
     series.extend((attrs['service.instance.id'],int(p['asInt'])) for p in metric['sum']['dataPoints'])
families=list(text_string_to_metric_families((root/'otlp.metrics').read_text()));samples=[s for f in families for s in f.samples];value=next(s.value for s in samples if s.name=='view_server_source_records_total');instance=next(s.labels['service_instance_id'] for s in samples if s.name=='target_info');network=max(v for ident,v in series if ident==instance);assert value==network==24,(value,network)
for path in root.glob('*.metrics'):
 parsed=list(text_string_to_metric_families(path.read_text()));assert parsed or path.name=="disabled.metrics"
 for family in parsed:
  for s in family.samples:
   assert not set(s.labels)&{'row','row_id','query_id','trace_id','span_id','token'}
e=json.loads((root/'kafka-health.json').read_text());summaries=[]
for r in e['results']:
 ms=[s['triggerToObservedMs'] for s in r['samples']];ages=[s['diagnosticAgeMs'] for s in r['samples']]
 before={m['name']:m['value'] for m in r['browserBefore']['metrics']};after={m['name']:m['value'] for m in r['browserAfter']['metrics']}
 allowed={'0',*[str((['disabled','metrics','otlp'].index(r['mode'])+1)*100+i) for i in range(24)]}
 for observation in r['observation']['deliveries']:
  if observation['whole']['status']=='ready':
   rows=observation['whole']['rows'];assert len(rows)==1 and rows[0]['id']=='health-row' and rows[0]['quantity'] in allowed
 for rows in r['observation']['rows']:
  assert list(rows)==['0'] and rows['0']['id']=='health-row' and rows['0']['quantity'] in allowed
 for q in allowed:
  assert any(v['whole'].get('rows')==[{'id':'health-row','quantity':q}] for v in r['observation']['deliveries'])
  assert any(v=={'0':{'id':'health-row','quantity':q}} for v in r['observation']['rows'])
 summaries.append({'browser_task_seconds':after['TaskDuration']-before['TaskDuration'],'browser_js_heap_bytes':after['JSHeapUsedSize'],'worker_reconstruction_max_ns':max(v['remote']['applyNs'] for v in r['worker']),'worker_encoded_bytes':sum(v['remote']['encodedBytes'] for v in r['worker']),'mode':r['mode'],'updates':len(ms),'median_ms':statistics.median(ms),'p95_ms':sorted(ms)[int(.95*(len(ms)-1))],'max_ms':max(ms),'max_sample_age_ms':max(ages),'max_queue_bytes':max(s['queue'] for s in r['samples']),'max_rss_kib':max(int(s.split()[0]) for s in r['resources']),'max_management_ms':max(x for group in r['management'] for x in group),'ps_samples':r['resources']})
result={'passed':True,'prometheus_value':value,'otlp_value':network,'aligned_instance':instance,'independent_parser':'prometheus-client 0.22.1','temporality':'cumulative','performance':summaries,'boundary':'same browser clock immediately before writing to an already running persistent producer stdin, to mounted result observed by browser predicate; includes polling/evaluation. No cross-clock subtraction; not physical paint.'}
(root/'metrics-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
