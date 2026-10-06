> Current checkpoint: v10 / durable format 3. See reports/V10-PARTITION-METADATA-AUDIT.md and CLOUD-HANDOFF.md. Earlier sections below retain historical architecture context.

# Checkpoint v5 architecture

V5 is a bounded, executable Rust/WASM product adapter. It repairs acquisition identity, terminal lifecycle, request settlement and delivery/acquisition accounting. It is not production service or frozen-package parity.

## Ownership and engine boundary

- `native/src/product.rs` owns product query specifications, exact integer/decimal values, keyed previous rows, predicate-shape sharing, validation, category counts, result versions and dirty subscriptions. `ProductCommand`, `Query`, `ProductResult` and `ProductCoreStats` are product types.
- `native/src/product_engine.rs` is the private selected execution boundary. Its product-owned `MembershipChange`, input batches and `Completion { frontier, changes }` contain no Differential/Timely types. One concrete `MembershipEngine` owns all `InputSession`, Worker, probe and captured output for the product path. A future backend experiment may implement that completion boundary without changing hooks, subscription lifetime, query grammar or Worker messages. This is a narrow membership-execution seam, not a claim that an alternative backend implements the full product query engine.
- Actual Differential execution is `InputSession -> to_collection -> inspect -> probe`. Rust outside that dataflow evaluates predicates, explicitly consolidates observed updates, and maintains counts/ranking. There are no Differential-owned predicate plans or arrangements in this product path. The separately retained legacy `differential/` benchmark module has its own implementation and is not the product evaluator.
- `ViewportHub` owns existing direction-specific ranked indexes and independent windows. Identical predicate/direction acquisitions share the index. A genuinely missing direction copies existing index records once. An existing empty index is still initialized and shared.
- `wasm_api.rs` exposes the same ProductCore through bounded JSON commands/results. Exact numbers stay strings/coefficient-scale values; no floating-point financial conversion occurs.
- The Worker owns one WASM instance, serialized command execution, native-to-browser extraction, acquisition correlation and one ACK per successful command. React owns render state, projection and committed-effect subscription registration.

No DBSP dependency, second production evaluator, generic backend registry or plugin framework is introduced. Experimental manifests live outside `native/`; an unused experimental build cannot affect the selected product build. Correctness compares completed observable results against independent test-only oracles, not enqueue rates or callback counts. Existing shared fixtures and benchmark code are preserved.

## Identity and delivery contract

A provider object is one Worker lifetime. A React `useId` identifies a consumer, not an acquisition. Each open/replacement allocates a provider-local acquisition number; requests bind it to native subscription strings, and ACKs carry an own-property-safe acquisition map. A request ID correlates settlement and its error with that command. Rust independently allocates non-resetting viewport generations for acquisitions in that core lifetime. Query shape identity is the canonical compiled predicate key and survives individual consumers. Navigation sequence and completed result version have separate roles; a later navigation at the same version is accepted.

Before callback delivery, provider lifetime, active acquisition, subscription metadata and freshness must match. Cleanup closes only the acquisition it owns; Worker checks close/navigation ownership. Old ACKs may settle their original caller, but cannot publish into a replacement listener. An invalid native change-query/window is validated before modifying the active acquisition; provider bookkeeping restores the prior identity on rejection. Viewport replacement validates supported query/window input before releasing its predecessor.

Hook state is keyed by provider, subscription and snapshotted query. The render that changes identity exposes loading with no attributed rows, without external render-time effects. Committed effect cleanup cancels delivery. Errors are acquisition scoped and successful acquisition clears them. Failed providers may retain rows for display, with status `error` and the terminal cause, never `ready`.

## Request protocol and completion

Public open/watch/apply snapshot inputs with `structuredClone` before awaiting readiness. Clone/admission failure allocates no pending request. After readiness, the pending promise is synchronously created and returned through the caller-owned promise; synchronous postMessage failure removes and rejects that record. ACK/error, terminal failure and disposal each remove/settle records exactly once. Initialization rejection is deliberately observed even with no ready caller. Cancellation stops delivery; it does not roll back a native mutation already applied.

One ACK carries the dirty result map, per-result acquisition map, traceparent and stats. There are no separate result messages. The provider settles the command, then safely fans the same local payload out to listeners. A direct open with no watcher receives its result. A no-op/nonmatching mutation ACK has an empty map and still completes. Callback failure cannot strand settlement or peer delivery.

ACK success means native apply and result extraction succeeded and the Worker postMessage succeeded. It does not mean every consumer accepted/rendered the snapshot. Post-apply extraction/publication failure is terminal with an explicit `Command applied ... no rollback` cause. Command admission failure is a request rejection. Results are versioned replacement snapshots, not reference wire deltas.

## Provider state machine

`initializing -> ready -> failed -> disposed`, with direct initializing/ready-to-disposed transitions. Failed and disposed never reopen. A useful first terminal cause is preserved. Every incoming message is gated before any work. Terminal transition invalidates registrations/freshness and clears pending records before notifying callbacks; it rejects pending/future requests and terminates the Worker. Disposal is idempotent. Active consumers receive a terminal error, including disposal before readiness.

Callback exceptions are retained in `consumerErrors`, and optionally reported through `onConsumerError`. Reporter exceptions are also retained there without recursive reporting. Throwing listeners/error reporters cannot interrupt peer notification. Expected cleanup rejections are observed; no global unhandled-rejection suppression exists.

## Scope

The native product schema supports exact typed predicates, amount ordering, windows, upsert/patch/delete and exact category counts. The React subset supports nonempty supported projections, AND of category equality filters and zero/one amount sort. Whole results use the WASM u32 ceiling; incompleteness reports error. Reference anchor/follow semantics, full grammar/grouped React results, native sources, transport, Kafka/Registry, authentication, retries/reconnect, telemetry export and production capacity remain deferred.

See `reports/V5-REPAIR-LEDGER.md` for executed evidence and `reports/INCREMENTAL-PATH-AUDIT.md` for actual work counters. The isolated COUNT DISTINCT finding is documented under `investigations/count-distinct/`; neither distinct/count operator chain is used by the v5 product path.

## CountDistinct guardrail addendum

`product_engine/distinct.rs` holds the private isize zero-aware threshold helper. It is reserved and tested by the isolated investigation; ProductCore still has no CountDistinct query path. Root Clippy configuration bans direct total-distinct methods in production, with a fail-fast CI entry point and deliberate-failure proof. The engine-neutral contract lives in `contract-tests/`, and its Differential adapter/operator tests live in the independent investigation workspace. No Differential type enters the shared contract, hooks or transport. See `reports/V5-DISTINCT-ADDENDUM.md` for exact versions, evidence and the closed original-Claude-artifact provenance limitation.

## V5.1 transactional delivery and reentrancy

A requested replacement changes the desired acquisition and suppresses predecessor delivery. It does not erase the last delivered freshness or the latest completed candidate. The provider keeps at most one candidate per registered subscription, replacing it only with a newer acquisition/result; it is normally the same object as the delivered snapshot. There is no per-command result history. Rejection restores the Worker's surviving acquisition synchronously at response handling, then publishes the matching candidate only if the operation still owns the desired acquisition. Earlier rejections cannot roll back a later intent. Successful replacements never replay their predecessors. No resnapshot, native recomputation or extra Worker message is needed. Release, successful close and termination discard retained candidates.

Each viewport invocation captures its registration and acquisition in a delivery guard. Before delivery, after setRowCount, and after setRowData/before ready, it checks that guard plus the viewport generation/released state and provider lifecycle. A callback's already-performed effects cannot be undone, but release, replacement or termination stops all following effects. This also detects low-level acquisition replacement that leaves the numerical viewport generation unchanged. Stale callback exceptions go to provider consumerErrors/reporting, not the replacement generation. Error routing rechecks ownership after external reporting; the reporter is nonrecursive even when it reenters termination. Terminal notifications respect peers explicitly released by another callback.

A direct apply(close) keeps ownership until its successful ACK. A guaranteed pre-send error therefore rejects the caller and clears pending bookkeeping while leaving the confirmed live subscription deliverable. No rollback can resurrect a newer/released lifetime. By contrast, release cancels local delivery immediately and owns native cleanup. If a cancelled speculative acquisition was never accepted, one rejected cleanup may retry the explicitly confirmed older acquisition, only when no local successor owns the subscription. Missing/already-superseded native acquisitions need no cleanup. Any unresolved cleanup failure, including pre-send failure, terminates the provider/Worker and reports an explicit release-cleanup error to healthy consumers. There is no unbounded retry or reconnection. Native statistics after Worker termination remain historical; no zero-resource ACK is fabricated.

## V6 retained/source and replaceable product boundary

The next major checkpoint adds `engine_contract::ProductEngine`, a concrete selected
alias, product-owned TopicStore, bounded ordered SourceBatch admission and a
snapshot/tail prototype. Source ownership, replay checkpoints and product versions
are independent of private engine progress. `reports/ENGINE-BOUNDARY-AUDIT.md` records
the pre-change audit; `ENGINE-CONTRACT.md`, `VERSIONING-MODEL.md` and
`RETAINED-TOPIC-AND-HANDOFF.md` define the current contracts and measured costs.
The v5.1 provider/hooks/Worker protocol remain the accepted transport behavior.
Source ingestion is a native API; no Kafka or new browser source command is claimed.

## V7 source boundary

`ingestion` is a separate native crate: Kafka SDK -> Confluent framing -> Registry
validation -> protobuf -> typed SourceMutation -> lease/replay/queue coordinator ->
existing TopicStore/ProductEngine contract. The SDK has no access to private
execution types. The bidirectional architecture guard and negative CI proofs cover
both directions. Core source changes are bounded replay fingerprints persisted in
TopicSnapshot and byte/event limits on handoff; no lifecycle/grammar reopening.
The source owner becomes terminal after an internal engine failure. A durable
provider acknowledgment is required before any Kafka commit; no production durable
provider is supplied in v7. See reports/V7-CHECKPOINT.md for evidence and limits.

## V8 durable canonical source state

The native ingestion path now has one concrete SQLite provider: source-neutral
records → durable coordinator → fenced canonical transaction → TopicStore/engine
reconciliation → broker commit authorization. ProductEngine signatures and all
private evaluator boundaries remain unchanged. Canonical transitions reuse
TopicStore admission without constructing an evaluator. Storage knows no Kafka,
Registry, viewport or Differential objects. See reports/DURABLE-SOURCE-PROTOCOL.md
for format 1, crash windows, ownership/recovery and the same-host SQLite deployment
boundary. V7's model-only durability statements are historical; its public model
APIs remain for accepted regression coverage and are rejected on the v8 Kafka path.
