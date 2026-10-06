"""Write review tables from raw observations, before fresh acceptance freezes reports."""
from pathlib import Path
import json,math,re,statistics
root=Path(__file__).resolve().parent.parent;folder=root/'evidence/v10/measurements'
def samples(v,n,p,c):
 result=[]
 for r in [0,1]:result += [x for x in map(json.loads,(folder/f'{v}-n{n}-p{p}-cap{c}-r{r}.jsonl').read_text().splitlines()) if x['kind']=='sample']
 return result
def q(values,p=.5):return sorted(values)[math.ceil(len(values)*p)-1]
def ms(s,k,p=.5):return q([x[k]/1e6 for x in s],p)
lines=['\n## Observed partition-scaling results\n','64 pooled samples per cell, nearest-rank quantiles. Times in milliseconds. All 1,536 measured samples passed the independent exact oracle. Complete per-phase quantiles and raw observations are retained.\n','| Rows | P | Cap | Candidate | Durable p50 | p95 | p99 | max | Reconcile p50 | Guard (3 reads) p50 | Authorize p50 | Service p50 |','|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for n in [10000,20000]:
 for p in [1,16,256]:
  for c in [1,32]:
   for v in ['v9','v10']:
    s=samples(v,n,p,c);nums=[ms(s,'durable_ns',x) for x in [.5,.95,.99,1]]+[ms(s,k) for k in ['reconciliation_ns','guard_ns','broker_ns','available_ns']]
    lines.append(f'| {n:,} | {p} | {c} | {v} | '+' | '.join(f'{x:.3f}' for x in nums)+' |')
lines += ['\nFor 10k rows/cap=1, the following work covers one commit, its reconciliation fence, three guarded result reads and one broker authorization (six transactions):\n','| Candidate | P | Partition objects read / written | Metadata decoded bytes (median) | Encoded bytes (median) | Metadata digest bytes (median) |','|---|---:|---:|---:|---:|---:|']
for v in ['v9','v10']:
 for p in [1,16,256]:
  s=samples(v,10000,p,1);w=s[0]['work'];values=[q([x['work'][k] for x in s]) for k in ['metadata_bytes_decoded','metadata_bytes_encoded','digest_bytes_hashed']]
  lines.append(f"| {v} | {p} | {w['partition_objects_read']} / {w['partition_objects_written']} | "+' | '.join(f'{x:,}' for x in values)+' |')
lines+=['\nProcess resources below include bootstrap, recovery, warmup, full-sort oracles and output, not just normal commits. Two independent process values are shown.\n','| Candidate | Rows | P | Cap | CPU user+system s | Peak RSS MiB | DB/WAL end bytes |','|---|---:|---:|---:|---|---|---|']
for v in ['v9','v10']:
 for p in [1,16,256]:
  cpu=[];rss=[];storage=[]
  for r in [0,1]:
   name=f'{v}-n20000-p{p}-cap32-r{r}';t=(folder/(name+'.resources.txt')).read_text();m=re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys',t);assert m,t
   cpu.append(float(m[2])+float(m[3]));rss.append(int(re.search(r'(\d+)\s+maximum resident set size',t)[1])/1024**2)
   end=json.loads((folder/(name+'.jsonl')).read_text().splitlines()[-1])['storage'];storage.append(f"{end['db_bytes']:,}/{end['wal_bytes']:,}")
  lines.append(f'| {v} | 20,000 | {p} | 32 | '+ ' / '.join(f'{x:.2f}' for x in cpu)+' | '+' / '.join(f'{x:.2f}' for x in rss)+' | '+'; '.join(storage)+' |')
p=root/'reports/V10-CHECKPOINT.md';s=p.read_text().split('\n## Observed partition-scaling results')[0];p.write_text(s+'\n'.join(lines)+'\n')
s=samples('v10',10000,256,32)
phase={k:q([x['work'][k]/1e6 for x in s]) for k in ['global_write_ns','sqlite_commit_ns']}
road=f'''# V10 throughput roadmap

The measured win is removal of unrelated partition replay-envelope work, proved by deterministic work counts and byte-for-byte untouched partition metadata. These local release timings are observations, not production capacity qualification. Source/network/decode is excluded, candidate runs are sequential, and some baseline setup/timing overlapped development tests/builds. See V10-CHECKPOINT.md for the matrix and full limitations.

## Remaining costs at 10k rows, P=256, cap=32

64 pooled samples, nearest-rank medians:

| Component | Observed milliseconds | Boundary |
|---|---:|---|
| Durable transaction | {ms(s,'durable_ns'):.3f} | Admission, BEGIN wait, local/global metadata, touched keys, COMMIT |
| SQLite COMMIT | {phase['sqlite_commit_ns']:.3f} | COMMIT call; includes sync/checkpoint work, not a direct physical fsync measurement |
| Global-object write | {phase['global_write_ns']:.3f} | Validate, clone bounded metadata, serialize/hash and issue UPDATE; excludes COMMIT |
| Engine reconciliation | {ms(s,'reconciliation_ns'):.3f} | Exact pre/post receipts, engine completion and final durable guard |
| Three query reads | {ms(s,'guard_ns'):.3f} | Three guards plus result extraction |
| Broker authorization | {ms(s,'broker_ns'):.3f} | Local authorized callback, no Kafka network |
| Full service interval | {ms(s,'available_ns'):.3f} | Apply plus three completed reads; excludes oracle/broker callback |
| Batch construction | {ms(s,'batch_build_ns'):.3f} | Synchronous fixture construction; queue wait is zero in this harness |

Medians are not additive. Reconciliation includes a guard; durable transaction includes both recorded subphases. COMMIT time does not prove all elapsed time was fsync. CPU/RSS cover entire processes including bootstrap/oracles; no per-stage CPU attribution is claimed.

## Retained global cut and contention

Every fresh partition commit updates one bounded global version/batch-history object. This is a local compatibility/coherence counter, not a global Kafka order. The source and golden tests require sequential cut/replay semantics. It was retained deliberately. SQLite serializes all writers to the same file even if this UPDATE were removed. The deterministic SDK test holds an independent BEGIN IMMEDIATE for 200 ms and proves the admitted transaction waits at least 100 ms. That is writer-lock evidence, not a measurement isolating contention on the global row; no multi-coordinator throughput gain is inferred.

Full offset receipts and the engine's offset maps still clone/compare O(P) coordinates in memory. This preserves all v9 reconciliation checks while eliminating the much larger O(P*H) durable JSON/hash envelope. This residual metadata work needs an equivalent immutable/persistent cut representation and adversarial equality tests before any stronger end-to-end constant-work claim.

## Evidence-backed next steps

1. Evaluate larger bounded transaction batches before changing durability. Cap 1 versus 32 is measured under identical durability; amortize COMMIT while reporting batch wait and sparse-traffic latency. Preserve the current 1024-record/2-MiB hard limits unless separately justified.
2. Separate the small sequence/identity/ownership read headers from bounded global and target replay history, so query guards need not decode approximately 63 KB. Keep history/checksum admission in the same transaction and add corruption/race tests before adopting this change.
3. Preserve exact whole-cut receipt semantics using structurally shared immutable offset metadata if P-only reconciliation work becomes material. Do not simply drop unrelated offset checks.
4. Measure independent local partition sharding only with explicit ownership and coherent-view reconstruction rules. Multiple SQLite files can remove a shared writer bottleneck but do not automatically provide the existing topic cut or cross-shard atomic snapshots.
5. Multiple coordinators/partition-owner parallelism on one file currently contend for the writer lock and invalidate stale whole-topic cuts. Measure scheduler/reconstruction cost first; a parallelism headline without equivalent view semantics is not valid.
6. Real Kafka source/network/decode, group rebalances and Linux behavior remain unqualified. Execute the isolated broker/Linux gates when that runtime exists before choosing a deployment architecture.
7. Alternate durability cadence/group commit would change loss/acknowledgment policy unless an equivalent durable batch boundary is retained. Keep WAL/FULL/fullfsync unchanged here. Do not substitute NORMAL/OFF or acknowledge Kafka before durable authorization.

Global queue pressure and synchronous SQLite work can delay all partitions. The queue tests prove bounded buffers, lease separation and replay correctness, not a per-partition real-time liveness SLA. Timed broker callbacks contain no network and cannot quantify Kafka overhead. Real traffic batch formation, serialization/transport and query demand require separate measurements.

No 200k–500k records/sec result is claimed. This checkpoint stops at the measured local metadata normalization and its qualification evidence; it does not start a new evaluator, transport or distributed consensus project.
'''
(root/'reports/V10-THROUGHPUT-ROADMAP.md').write_text(road)
