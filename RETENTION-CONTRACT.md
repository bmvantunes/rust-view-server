# Per-topic retention contract (v1)

This feature retains the latest accepted row for each `(logical topic, rowId)`.
It applies an age limit, a message-count limit, or both. Either limit can evict a
row; the limits are not combined as a minimum or used to refill a history.

## Configuration

`retention` is optional on a source binding. Its JSON keys are camelCase and the
native Rust config validates them again at startup.

| Effective source `cleanup.policy` | Allowed count limit | Count scope |
| --- | --- | --- |
| `delete` | `maxRetentionMessages` | all active rows in the logical topic, across partitions |
| `compact` | `maxRetentionMessagesPerKey` | active rows sharing the configured source-key identity |
| `compact,delete` | `maxRetentionMessagesPerKey` | active rows sharing the configured source-key identity |

`maxRetentionMinutes` may be combined with the allowed count limit or used by
itself. A count limit may be used by itself. Count fields are mutually
exclusive. Durations must be finite, positive, and at most 5,256,000 minutes
(ten years); conversion rounds up to whole milliseconds. Counts must be positive
integers no greater than both `maxRows` and 10,000,000. The per-key count is not
a distinct-key limit.

For compact key-only identities, a source key currently identifies at most one
rowId. A per-key cap above one is therefore nonbinding and does not retain
overwritten values as history. The service does not invent identities from
values or evict a different source key to make the cap appear useful. Existing
null tombstones for value-dependent delete identities remain unsupported.

`examples/grouped/retention-topic-config.ts` shows typed configuration, and the
grouped generator's `retention-v1` mode chooses the fresh
`canonical-rowid-retention-v3` namespace. Use a fresh prefix so the Kafka group
has no prior source progress. The ordinary generator mode remains retention
off.

## Kafka startup admission

Before any source owner subscribes, reads, initializes its transactional
producer, or writes canonical state, startup performs a bounded read-only
`DescribeConfigs` pass for every configured source. It reads effective
`cleanup.policy`, accepting a value reported from a broker default or a topic
override, and compares normalized policy sets. Missing or unknown required
configuration is an error.

For a source policy containing `delete`, a finite application age horizon must
not exceed the effective Kafka `retention.ms`. `retention.ms=-1` has no
time-delete ceiling. A compact-only source does not use `retention.ms` for time
deletion and the service does not require that value. No Kafka configuration is
changed. The comparison says nothing about historical coverage against size
retention, compaction, or tombstone cleanup; those remain asynchronous broker
behaviors.

For example, a 24-hour application horizon against a three-hour broker setting
fails before source consumption or canonical writes with:

```text
Invalid retention for logical topic 'orders' (Kafka topic 'orders.v1'): maxRetentionMinutes=1440 requests 24 hours (86400000 ms), but Kafka retention.ms=10800000 (3 hours). Reduce the application horizon or change Kafka retention before starting this service. No configuration was changed.
```

The canonical topic remains compact-only. There is no direct-source bootstrap,
offset-only state replacement, policy reconfiguration, or automatic migration.
Existing V2 canonical bytes remain V2 when retention is absent. Retention
metadata uses incompatible canonical format 3, binds the normalized policy,
and requires a fresh canonical namespace. A V2/V3 mismatch fails closed; it does
not wipe or reinterpret the old state.

## Age origin, reference time, and order

- For an age-enabled UPSERT, `age_origin_ms` is the nonnegative Kafka record
  timestamp, whether Kafka reports CreateTime or LogAppendTime. Poll/receipt
  time and replay time never replace it. An unavailable or negative timestamp
  fails the source owner before its record and NEXT are committed.
- A timestamp up to five minutes ahead of the current reference time is
  accepted. A larger future timestamp fails closed before commit. A past
  timestamp is accepted; if it is already expired, the UPSERT is represented as
  a delete in the same source transaction. Delete records need no age origin.
- `referenceTime` is epoch milliseconds, nondecreasing within an owner, and is
  the maximum of observed wall time and the last committed
  `last_reference_time_ms`. The reference is persisted in the canonical
  manifest with source or maintenance transactions. On restart, the saved
  reference prevents time from moving behind the last committed cut. A wall
  clock moving backwards does not rewind the active owner or durable reference;
  forward jumps make rows due. Only committed reference time is recovery
  authority.
- Expiry is inclusive: a row is due exactly when
  `referenceTime >= age_origin_ms + maxRetentionMinutes`. Both addition and
  duration conversion are checked.
- `retention_order` is a monotonically increasing per-owner admission number,
  persisted with each active row. Within one Kafka partition, admitted records
  retain their Kafka offset order. When partitions interleave, the order is the
  sequence in which the single owner admits records; it is not a fabricated
  global Kafka offset or event-time watermark. This persisted order breaks
  cross-partition count-cap ties deterministically for a given durable image.
- Each accepted UPSERT replaces the one current row for that rowId and gets a
  new age origin/order. A replay below canonical NEXT is not admitted again. An
  old expiry generation cannot delete a newer UPSERT. If a replacement later
  expires or is count-evicted, the overwritten value is not resurrected.

The reference model in `scripts/retention_reference.py` intentionally scans
current rows instead of using the production indexes. The native integration
oracle in `native/tests/retention_oracle.rs` independently recomputes raw rows
and all six grouped aggregates at every completed retraction cut.

## Maintenance, publication, and bounds

Age maintenance runs on the serialized source owner at a 250 ms cadence. Each
transaction admits up to 256 due rows; an expiry chunk contains only bounded
row tombstones and stays below the 2 MiB transaction-write budget. Expiry,
recency, and per-key indexes contain current active rows only. A replacement
removes the old expiry generation. Maintenance work and these indexes are
bounded by the configured `maxRows` ceiling; sticky rowId/source-key ownership
metadata also remains subject to that ceiling.

The owner commits canonical row deletion and manifest changes in one Kafka
transaction with the source group's existing offsets unchanged. Timer work
does not advance source NEXT, create user records, or increment source-record
counters. Source sequence, maintenance sequence, and content version are
separate: content version equals source sequence plus maintenance sequence in
format 3. Expiry transactions are counted and traced separately from source
transactions.

The derived runtime applies committed row deletes through the same incremental
mutation path as source deletes. That retracts raw membership and all six
aggregate contributions, including the final distinct value, extrema, and last
group member. `rid2` row identity and surviving `gid1` group identity do not
change when neighboring rows expire. Complete derived changes publish only
after the durable image is committed and all due chunks are applied. While due
work remains, health readiness is false, fresh acquisitions are rejected, and
the browser's retained display stays stale until the next complete acquisition.
Liveness remains separate.

There is no hard real-time expiry promise. Observed delay includes up to one
maintenance cadence, transaction time, derived application/acknowledgement, and
backlog ahead of a row. Health exposes pending backlog, oldest overdue age,
active payload rows, sticky keys, scheduled expiries, canonical/derived
versions, maintenance sequence, last commit, and last observed expiry delay.
Metrics and health scrapes only read cached state; they never initiate
maintenance. The active payload count cap does not bound historical Kafka log
bytes or promise immediate physical erasure by the broker.

If commit outcome is uncertain, the owner stops. If a committed expiry is not
published before failure, restart restores and audits canonical state, catches
up derived state, and completes currently due expiry work before opening the
listener. Canonical root/manifest checks and the existing `RetentionGap`
fail-closed protection remain authoritative.

## Finite implementation gates

The current qualification is bounded to:

1. Rust and TypeScript policy validation, duration conversion, branch checks,
   24-hour versus three-hour startup rejection, effective default/override
   values, `-1`, and delete/compact policy semantics.
2. Global N/N+1 across partitions, repeated rowId replacement, topic isolation,
   per-key cap behavior, exact expiry, late/future timestamps, clock rollback,
   replay/restart age, stale generations, and no history refill.
3. Independent raw and grouped recomputation at every completed cut, covering
   all six aggregates, missing/null presence, totals, rank, windows, and stable
   IDs.
4. A private two-topic/two-partition Kafka run using one ordinary service
   process, the production browser Worker, and both mounted hooks; include
   source silence, updates, tombstones, reconnect, selected crash cuts, unchanged
   source NEXT during timer maintenance, and canonical cleaner/recovery equality.
5. Existing affected type, lifecycle, source-presence, identity, generator,
   numeric, codec, telemetry, and safety gates, plus bounded maintenance
   workload/retained-memory measurements. No saturation or 150 ms SLA claim.

Kafka semantics are checked against the pinned Apache Kafka 4.1 topic-config
and log-design references:

- <https://kafka.apache.org/41/configuration/topic-configs/>
- <https://kafka.apache.org/41/design/design/>

## Cleanup admission and live integrity checks (v1.1)

Pending ordinary maintenance blocks commands that acquire or navigate fresh
results. A valid close still reaches the normal owner command, with the same
authentication, request/acquisition identity, authority transaction and native
resource cleanup. An obsolete close remains rejected. Cleanup failures still
propagate to the provider's existing terminal fallback. No readiness flag is
forced true and no synthetic acknowledgement is sent.

A full canonical row/root/index reconstruction audit runs at restore boundaries.
Live commits validate changed rows and index removals/insertions, then check the
maintained manifest/root/NEXT/content versions and bounded index metadata. They
do not enumerate all sticky identities or reconstruct every active index per
source update or expiry chunk. The focused work-count test records row folds,
hashes and full-audit visits separately from restore; it is not a latency SLA.
