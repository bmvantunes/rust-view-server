# Contract matrix — checkpoint v5.1

This is a bounded adapter, not full frozen reference-package parity. Frozen reference commit: `8aa77efabe59da335c5a5de321c6ac41b242fb34`. Seven relevant original files are included under `evidence/reference-8aa77ef/` with per-file hashes in `evidence/reference-v5-manifest.json`.

| Area | Reference evidence relative to the included reference directory | Implemented product contract and executed evidence |
|---|---|---|
| Public hooks and inference | `packages/react/src/index.tsx`, `index.test-d.ts`, `live-query-viewport.test-d.ts` | `useLiveQuery(products, query)` and topic-only viewport hook preserve selected-field inference for the fixed product schema. Static positive/negative tests pass, including rejection of unselected fields, unknown topics/fields, quantity sort and multiple sort keys. |
| Query grammar | `docs/query-semantics.md` | React admits nonempty product projections, category equality AND and zero/one amount sort. Runtime validation remains for untyped callers. Broader recursive/filter/grouped reference grammar is not claimed. |
| Exact values | `docs/query-semantics.md` | Quantity strings and coefficient/scale amounts preserve exact arithmetic, negative ordering, canonical ID ASC ties in both sort directions. Native, direct-WASM oracle and mounted tests execute. |
| Totals and whole results | `docs/query-semantics.md`, `packages/react/src/index.tsx` | Pre-pagination totalRows; complete hook results through 257 rows and live growth beyond 100. WASM u32-sized maximum; incomplete full result reports error. |
| Acquisition ownership | `docs/query-semantics.md`, `packages/react/src/live-query-viewport.ts` | Inputs snapshotted before async work; provider-local acquisition identity separate from consumer ID and native shared shape; only current acquisition publishes. FIFO/A-B-A/every-publication tests, release, provider replacement, development StrictMode and staggered consumers pass. |
| Query transition/errors | `packages/react/src/index.tsx`, `packages/client/src/live-query-state.ts` | New query/provider render returns loading with no old rows; errors scoped to identity, successful correction clears error. No render-time external cancellation. |
| Navigation/results | `packages/react/src/live-query-viewport.ts`, `packages/client/src/live-query-state.ts` | Independent sparse windows use returned absolute rank; navigation sequence distinct from data version; same-version navigation accepted. Non-resetting native generation. Results are replacement snapshots, not reference wire deltas. Full anchor/follow and range-diff parity remain deferred. |
| Failure and disposal | Reference lifecycle code is supporting context; product protocol is documented in `ARCHITECTURE.md` | Initializing/ready/failed/disposed; first terminal cause retained; mounted subscriptions become error even without pending commands. All late messages ignored. Disposal idempotent and notifies active consumers once. 9 fault-injection cases exercise genuine registered handlers. |
| Request completion | Product-owned bounded protocol | Snapshot/readiness/send/error/ACK/failure/disposal all settle caller-owned requests without orphan records. Command ACK does not assert successful rendering. No rollback claim after applied mutation. |
| Direct low-level API | Product-owned bounded protocol | Direct open without watcher returns result; empty, `__proto__`, `constructor`, `toString` and ordinary IDs supported with safe maps. Invalid native change-query/window preserves old acquisition. |
| Delivery and cost | Product-specific evidence | One row-carrying ACK, no duplicate result message; shared direction acquisition performs no full-index copy. Actual counter units in incremental audit; bounded smoke executed. |
| Category aggregate | Product-specific native API | Rust-maintained exact bigint category counts; direct-WASM oracle checks completed grouped results. COUNT DISTINCT is not a supported product aggregate. |
| Native sources/operations | Broader reference documents listed in historical v4 matrix are not parity claims | Kafka/Registry, gRPC/WebSocket transport, auth, reconnect, exported telemetry and production-capacity targets remain unimplemented here. |

The included frozen reference is evidence of original semantics, not proof that this subset implements every clause. Original reference files, fixture and previous archives were preserved. No external reference checksums alone are presented as standalone parity evidence.

V5.1 adds transactional rollback on rejected low-level replacements, retaining a bounded latest completed candidate; callbacks revalidate the captured acquisition, generation and provider lifetime after every external call. Direct close is committed locally only on ACK. Release cancels immediately, retries a confirmed predecessor cleanup at most once, and terminates explicitly on unresolved cleanup failure. The exact tests and current evidence are in `reports/V5.1-REPAIR-LEDGER.md`. These are adapter guarantees, not reference wire-delta parity.

V6 extends the native contract with retained snapshots, ordered bounded source
batches, net-change completion, duplicate suppression and a deterministic snapshot/tail
prototype. It adds a persisted engine-independent command corpus and a test-only
reference engine, plus documented canonical predicate sharing. Browser grammar,
provider semantics and Worker messages retain v5.1 behavior. See
`reports/ENGINE-CONTRACT.md` and `reports/RETAINED-TOPIC-AND-HANDOFF.md` for exact scope.

## V7 source additions

| Contract | Implementation / evidence |
|---|---|
| Native Kafka source | Separate rust-rdkafka adapter with topics/partitions/offsets, tombstones, explicit assignment positions, pause/resume and shutdown; SDK mock protocol test, real broker gate separately reported |
| Protobuf/Registry | Admitted Confluent message indexes, static fixture layouts + dynamic ID validation, bounded/coalescing cache, actual loopback HTTP fixture, exact int64/decimal mapping |
| Source ownership | Per-partition epoch, serialized commit/revoke fence, stale queued deliveries discarded, reassignment and terminal failure models |
| Checkpoint/replay | Inclusive last applied, durable-only next-offset commit, bounded persistent wire/batch fingerprints, corruption and horizon rejection |
| Handoff/memory | Vector cut, independent tails and empty/new/revoked partitions, three checked quotas, explicit overflow/restart |
| Production limits | Real Kafka/MSK/Linux integration not locally established; no shipped durable provider, distributed shard transfer, IAM refresh or new browser transport |

## V8 durable source additions

| Contract | Implementation / evidence |
|---|---|
| Atomic durable truth | Versioned SQLite canonical envelope; exact rows, partition mapping, offsets, replay hashes, topic/source versions and ownership epochs in one fenced transaction |
| Restart and transfer | Strict admission, persisted epochs, crash without release, restore-before-live seek, forced engine/subscription reconstruction under a fresh result incarnation |
| Crash evidence | A–G SIGKILL subprocesses; separate-connection races; fixture readability; rollback and lost-acknowledgment windows; engine failure after durable commit |
| Broker safety | Concrete durable authorization after engine coherence; replay verification; broker-ahead recovery; typed retention/truncation errors; no automatic reset |
| Registry/pressure | Registry root URL normalization and identity rejection; outage/decode recovery tests; slow SQLite IO contention with bounded Kafka/decoded queues and separate timings |
| Limits | Same local database/host fencing, full-image O(dataset) storage, no cross-host consensus/real-broker/power-loss/throughput claim; section 24 capacity request was truncated |

Exact final gates and preservation evidence: reports/V8-CHECKPOINT.md and
evidence/v8/validation.json. Accepted v5.1/v6/v7 query/source/lifecycle behavior is
retained; new result identity is native-only and does not claim browser continuity.
