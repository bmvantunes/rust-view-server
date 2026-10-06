> Current checkpoint: v11 / durable format 3. See ../reports/V11-CHECKPOINT.md and ../reports/V11-OWNED-READS-AND-BATCHING.md. Full owned-history guards remain; batch-tail sizing is incremental.

> Current checkpoint: v10 / durable format 3. See ../reports/V10-PARTITION-METADATA-AUDIT.md and CLOUD-HANDOFF.md. Earlier sections below retain historical architecture context.

# V9 current durable path

See `../reports/V9-CHECKPOINT.md` and `../CLOUD-HANDOFF.md` for format 2,
explicit offline format-1 migration, transactional touched-key receipts and bounded
batch configuration. Set `KafkaSource::set_batch_limits(BatchLimits { records: 32,
bytes: 1048576, latency_ms: 10 })` before polling for a bounded deployment choice;
cap=1 remains the compatibility default. The building tail shares the queue budget.
Shutdown discards unfinished work for replay without authorizing its offsets.

Use fresh `scripts/validate-v9.py` and `scripts/package-v9.py` from the project root.
The older notes below describe the accepted v8 API context; full-image persistence
and v8 acceptance instructions are superseded by the current report/handoff.

# Product source ingestion (checkpoint v7)

Native-only adapter crate. ProductEngine remains engine-neutral; this crate depends
on its contract and cannot import backend types. See reports/V7-CHECKPOINT.md and
the ownership, checkpoint, Registry and handoff reports in the parent directory.

Run `sh scripts/test-ingestion.sh` from the checkpoint root. This builds the Kafka
TLS feature, executes deterministic semantic tests, a loopback HTTP Registry
fixture and the actual client with librdkafka's **mock** protocol cluster. The real
Kafka test is ignored by default. Its opt-in command requires a fresh empty topic
with exactly two partitions on an isolated disposable broker:

```sh
V7_KAFKA_BROKERS=127.0.0.1:19092 V7_KAFKA_TOPIC=v7-empty-fixture \
  cargo test --manifest-path ingestion/Cargo.toml --features kafka \
  --test kafka_client real_isolated_kafka -- --ignored --nocapture
```

Do not point this gate at a user's existing cluster. It produces records and uses
a test consumer group. v7 does not provision or launch any cluster.

Embedding sequence:

1. Create one shared Authority and one Coordinator per configured topic. Restore
   each from its complete Recovery, or an empty TopicStore snapshot for full replay.
2. Build HttpRegistry from deployment configuration (URL and credentials separately),
   wrap it in CachedRegistry, and configure KafkaSource. Supply `starts` from those
   same Recovery offsets plus one; missing partitions begin at the start.
3. Call poll at least every max.poll.interval (300 s), including when downstream is
   blocked. Use next_topic to select a coordinator, then apply_next when ready.
   Errors stop the source; do not ignore them or skip poison messages.
4. Capture detached coherent Recovery for an actual DurableStore implementation.
   Only successful atomic persist permits commit_durable. This repository supplies
   the contract and models, **not a production storage provider**.
5. On shutdown call shutdown, then drop the adapter. Unapplied records replay on
   recovery. Rebuild failed engines and reacquire subscriptions before publication.

`Config.options` accepts an explicit security/static-membership allowlist. Supply
credentials at runtime; never serialize Config to evidence. Native dependencies:
C/C++ compiler + CMake; `kafka-tls` additionally needs pkg-config/OpenSSL 3 headers
and shared libraries. macOS build verified, Linux CI recipe provided. IAM token
refresh, distributed retained shard migration and a network browser transport are
not implemented in this checkpoint.

## V8 durable source loop

Use `durable::SqliteStore` with an explicit `SourceIdentity { incarnation, topic,
schema: "product-v1" }`. `create` requires an absent file and is for deliberate new
source bootstrap only. `open` never resets/migrates existing state on error. Do not
write `open(...).or_else(|_| create(...))` as an automatic recovery policy.

Construct `Arc<Mutex<Session<SqliteStore>>>` using the store, process identity and
one shared Authority. Construct `DurableCoordinator<SelectedProductEngine,
SqliteStore>` from that session, then `KafkaSource::connect_durable(config, registry,
session.clone())`. Config must contain that single topic. Do not manually acquire
Kafka partitions: the assignment callback acquires durable ownership.

Poll with `source.poll_durable(&mut coordinator, timeout)` and drain using
`source.apply_next_durable(&mut coordinator)`. Poll first even when there is no
queued data: assignment recovery rebuilds the evaluator while partitions are
paused, seeks the durable required offsets, then resumes. After completed drains,
obtain the coordinator checkpoint and session's current leases. For each active
partition with an applied offset, `source.commit_checkpoint(&mut coordinator,
&lease)` synchronously commits its durable next offset. Release the session mutex
before invoking source/coordinator methods. No record/queue count authorizes a
broker commit. All source errors stop consumption; inspect `recovery_failure()`
for typed watermark recovery errors and reconstruct a fresh owner after correction.

Query methods on the coordinator reject direct row mutation. `read` returns a
ResultEnvelope with server_incarnation and the complete product result. Reacquire
subscriptions when the incarnation changes. Historical coordinator/model APIs are
retained for regression tests but durable sources reject their poll/apply/commit
entry points.

Run `python3 scripts/validate-v8.py` from the product directory. The provider tests
need local temporary storage; mock/HTTP tests need loopback sockets. A–G crash tests
spawn and SIGKILL only their own fixture subprocesses. The ignored `crash_child`
entry point is invoked by its parent and is not a skipped crash test. The frozen
v1 SQLite fixture is portable across the admitted macOS/Linux format boundary.

Operational rules, full-image costs and same-host deployment restrictions are in
reports/DURABLE-SOURCE-PROTOCOL.md and reports/DURABLE-STORE-DECISION.md. A plain copy
of a live SQLite main file is not a backup; use SqliteStore::backup. Restored copies
must never compete with still-running owners of the original database.
