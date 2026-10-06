#!/usr/bin/env python3
from pathlib import Path
import json,sys,statistics
p=Path(sys.argv[1]);r=json.loads((p/'performance.json').read_text());assert r['passed'] and len(r['results'])==9
logs=json.loads((p/'performance-logs.json').read_text());rows=[]
for x in r['results']:
 values=sorted(s['domObservationMs'] for s in x['samples']);resource=[s['sample'].split() for s in x['resources'] if s['sample']];peaks=[]
 labels={l['label'] for l in logs if l['label'].endswith(x['mode']+'-'+str(x['repetition'])) and not l['label'].startswith('producer')}
 for label in labels:
  for line in ''.join(l['text'] for l in logs if l['label']==label).splitlines():
   try:
    obj=json.loads(line)
    if 'queue_peak_bytes'in obj:peaks.append(obj)
   except ValueError:pass
 rows.append(dict(mode=x['mode'],repetition=x['repetition'],binary_sha256=x['sha256'],startup_ms=x['startupMs'],dom_median_ms=statistics.median(values),dom_p95_ms=values[int(.95*(len(values)-1))],dom_max_ms=max(values),rss_peak_mib=max(float(s[1])/1024 for s in resource),cpu_sample_mean_percent=statistics.mean(float(s[0]) for s in resource),source_bytes=x['sourceBytes'],result_wire_bytes=sum(z.get('encodedBytes',0) for z in x['wire'] if z),result_frames=len(x['wire']),queue_peak_frames=max(z['queue_peak_frames'] for z in peaks),queue_peak_bytes=max(z['queue_peak_bytes'] for z in peaks)))
(p/'performance-summary.json').write_text(json.dumps({'passed':True,'results':rows},indent=2))
text=['# Small-fixture measurements','',f'Raw nine-repetition evidence: `{p.name}/performance.json`, all producer acknowledgements, process samples and logs retained. 256 rows per topic, two partitions, 64 paced updates per run, one persistent producer, same selected full hook and two-row viewport DOM harness. Accepted and generic products use the same five-field source-compatible fixture and selection. The two-topic fixture uses different fields/schemas and alternating updates.','', '| Mode / repetition | Startup ms | DOM median / p95 ms | RSS peak MiB | CPU sample mean % | Source / result bytes | Queue peak frames / bytes |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
for x in rows:text.append(f"| {x['mode']} / {x['repetition']} | {x['startup_ms']:.0f} | {x['dom_median_ms']:.2f} / {x['dom_p95_ms']:.2f} | {x['rss_peak_mib']:.1f} | {x['cpu_sample_mean_percent']:.1f} | {x['source_bytes']} / {x['result_wire_bytes']} | {x['queue_peak_frames']} / {x['queue_peak_bytes']} |")
text+=['','DOM timing starts before producer send and ends at an independently checked React observation; it includes broker work and polling, and is not physical paint. CPU is the operating system process `%cpu` sample (lifetime average), not interval utilization or total CPU instructions. RSS excludes Kafka, browser and child libraries in other processes. Samples every100ms can miss peaks. Source bytes are protobuf key+payload; result bytes are MessagePack application payloads, excluding health/control/TCP overhead. Queue peaks include initial snapshots and updates; source channel/fetch budgets are separately fixed in the contract.','', 'These are paced correctness workloads, not maximum throughput benchmarks. Modes run in fixed order without randomized trials; brokers/filesystem and the host may be warm. Earlier superseded runs overlapped other qualification on this shared host; the current selected run is identified in the handoff. Three repetitions do not establish statistical superiority. Accepted and generic result framing/content suppression differ, so their frame counts need not match. No large-relation, WAN, 50M-row or500k-update/s claim follows.','']
(p/'PERFORMANCE.md').write_text('\n'.join(text));print(json.dumps(rows,indent=2))
