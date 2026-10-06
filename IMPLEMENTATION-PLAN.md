# Checkpoint v5 repair plan and outcome

V5 correctness gates are implemented and executed. Production milestones remain separate and incomplete.

| Stage | Delivered | Evidence |
|---|---|---|
| V5.A | Provider-local acquisition identity, non-resetting native generation, query-owned hook state/errors, owned cleanup and replacement admission. | FIFO and A/B/A publication assertions, pending/queued release, provider replacement, independent viewports, staggered consumers, development StrictMode, native generation tests. |
| V5.B | Absorbing provider failure/disposal, cause propagation, reentrant-safe invalidation, callback isolation and observable reporter failures. | 3 registered failure entry points × 3 lifecycle phases, late ready/ACK/result/error, mounted peer status and settlement counts. |
| V5.C | Synchronous snapshot/send failure cleanup and caller-owned settlement. | Real structuredClone and Worker.postMessage failure, pre-readiness failure/disposal, empty pending maps, no unhandled rejections in final suite. |
| V5.D | One data-bearing ACK used for direct completion and listener publication; actual extraction/message/row counters. | Six-row message inspection, selected quantity patch, no-op/nonmatching/offscreen changes, whole result growth, navigation and throwing listeners. |
| V5.E | Share existing directed indexes, including empty indexes, before collecting records. | 64-row native/browser acquisition counter smoke and independent-window/final-close tests. |
| V5.F | Input snapshots, prototype-safe subscription maps, zero/one sort type, validation before destructive replacement. | Nested mutable inputs including pre-ready requests; ordinary/empty/prototype-like IDs; positive and uncast negative type contracts. |

The complete command/exit/log mapping is in `reports/V5-REPAIR-LEDGER.md`. The selected product engine now has a narrow concrete private boundary using product-owned signed input batches and completed output changes. It introduces no new backend or production evaluator.

The isolated COUNT DISTINCT investigation does not participate in v5 acceptance. It reproduces a cached Differential 0.25.1 `distinct_total()` final-retraction failure and tests alternatives; see its README and logs. The product path uses neither `distinct_total` nor `count_total`.

Deferred production work remains native source adapters, Kafka/Schema Registry, backend transport selection, authentication, reconnect/retry, exported tracing, complete reference grammar/status/anchor parity, production resource limits and capacity validation. No unrelated milestone is declared complete.

The distinct addendum centralizes the tested nonzero callback in the private backend helper, adds enforced Clippy bans with exit-101 negative proof, preserves an engine-neutral 18-epoch contract and separate operator tests, and prepares an unpublished upstream report. Product gates remain green; Original Claude Code artifacts are unavailable by user constraint. No further request is required or permitted for this checkpoint. The preserved reproducer and execution evidence are independent; screenshots are supplementary. This is not an outstanding acceptance requirement. See `reports/V5-DISTINCT-ADDENDUM.md`.

V5.1 repairs H1 transactional rejection rollback, H2 callback reentrancy, and H3 direct-close/release cleanup ownership. See `reports/V5.1-REPAIR-LEDGER.md` for red/green execution and the independent-review availability limitation. Native implementation and Worker protocol are unchanged.

## V6 architecture checkpoint

Implemented: focused engine audit and neutral contract; sole retained TopicStore;
atomic bounded source batches; ordered replay/checkpoint and snapshot/tail prototype;
independent persisted golden corpus and test-only reference implementation; semantic
shape canonicalization; architecture guard/negative proof; measured native allocation
costs; future engine shootout and grammar roadmap. See `reports/V6-CHECKPOINT.md` for
fresh gate results, delivered artifacts and explicit limits. Future work remains
durable source coordination/storage, Kafka/Registry, transport and controlled grammar
expansion. Lifecycle regressions are preserved rather than replaced by a v5.2 task.

## V7 source ingestion checkpoint

Implemented source adapter, Registry/protobuf admission, ownership/replay/commit
contracts, capture quotas and executable fault/pressure models. Kafka remains a
native source dependency isolated from product APIs. Delivery and gates are recorded
in reports/V7-CHECKPOINT.md and evidence/v7/validation.json. Next deployment work:
atomic durable checkpoint provider, distributed fencing/shard transfer, isolated real
Kafka/MSK/Linux qualification, security/IAM integration and capacity tuning. No v6.1.

## V8 durable source checkpoint

Implemented one SQLite provider, explicit format/lifetime admission, durable
partition fencing, partition-scoped canonical truth, acquisition/revoke recovery,
durable-before-engine protocol, engine rebuild and incarnation-tagged results,
Kafka offset authorization/watermark recovery, executable SIGKILL crash matrix,
Registry URL correction/recovery failure coverage, and bounded durable-IO pressure
measurements. See reports/V8-CHECKPOINT.md for exact verification and limits.

Production deployment still requires local-volume durability qualification and a
capacity policy. Cross-host shared fencing, distributed global product views,
external rebuild/migration, browser reconnection and high-throughput incremental
storage are not delivered or inferred from the truncated section 24.
