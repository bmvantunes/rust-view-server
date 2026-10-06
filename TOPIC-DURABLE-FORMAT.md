# Generic Kafka canonical formats 2 and 3

## Format 2 compatibility

This is a new incompatible canonical namespace. The accepted product Kafka format 1 and its product-v1 payloads remain on the original code path. The SQLite product format number is unrelated. No migration, reinterpretation of product ROW bytes, state wipe, or seamless schema upgrade is implemented.

A configuration with a catalog selects the explicit v15 generic service. A configuration without a catalog selects the accepted v14 product service. Generic service startup rejects a v14 handshake. The new ordinary binary contains both built-in paths; a process chooses one at startup. Existing product integer/decimal/missing/null semantics remain unchanged at that boundary. Generic local-WASM API support is not implemented.

Every configured source uses a separate Kafka canonical topic, group and whole-source owner. A manifest binds format 2, logical topic, schema fingerprint, configured source incarnation, actual source topic, canonical topic, group, complete partition count, and the hash of pinned key/value FileDescriptorSets and field mappings. Endpoint credentials are never in the portable browser catalog. The configured source incarnation represents the operator's cluster/topic lifetime; it is not inferred from a row key, source schema ID or broker hostname.

Canonical records have keys prefixed with byte 2. ROW keys additionally contain the topic-local decoded row key; the namespace is already isolated by the configured canonical topic. A ROW retains its source partition, SHA-256 of the complete serialized source key, and either a complete validated row or an explicit logical deletion. A deletion preserves key ownership. Canonical Kafka tombstones are forbidden. Resource exhaustion rejects the source; it does not evict rows, delete sticky ownership, or implement retention.

NEXT records store the next required source offset per partition. A partition-zero manifest stores source sequence, the complete NEXT vector, and the XOR of SHA-256 contributions for every canonical ROW including logical deletions and ownership. Each envelope also authenticates its configured binding, partition, key and value with a deterministic SHA-256 digest. These hashes detect inconsistent input/canonical state; they are not a security signature against a writer with Kafka access.

A source owner validates every after-image and key/partition ownership, stages only touched keys, then transactionally writes changed ROWs, NEXT and the manifest with the source group's offsets. Only a certain broker commit permits folding the canonical image and dispatching the complete after-images. The query owner applies the batch, obtains a fresh authority barrier for that source, publishes, and acknowledges derived completion over an internal bounded channel. No browser ACK reaches canonical progress. A live selected-result row/byte quota retires only the offending browser connection; valid committed rows still complete the derived acknowledgement and other connections continue. The canonical retained-key budget remains a source admission failure, not a retention policy. Any uncertain transaction, fencing, invalid canonical history, malformed source record or internal evaluator failure is process-fatal. Another process reconstructs committed state; it does not guess the failed outcome.

Startup obtains a complete eager assignment, initializes the stable transactional producer identity for that canonical namespace, and replays the read-committed canonical history to captured partition cuts. Existing bytes are decoded and the final rows/root/NEXT vector audited before writing a new authority barrier. A mismatched format/schema/source binding is rejected without writing into that mismatched history. Only a wholly empty canonical topic with no existing source-group progress can be initialized with the explicit initialize_empty setting. Source NEXT must lie within Kafka's current low/high boundary; a retention gap or truncation fails closed.

The captured source bootstrap cut includes all configured partitions. Read-committed EOF/statistics proof can advance NEXT over aborted/control gaps without inventing a row mutation or source sequence. All row-bearing records returned ahead of publication are represented either in the committed batch or the single bounded pending lookahead; serving progress never passes that pending record.

A source has one bounded owner thread and one independent end-observer thread. The owner drains at most 256 records and 2 MiB per transaction. Its dispatch channel holds at most two events; a row event waits for the single query owner's derived acknowledgement before another source transaction. A restore chunk holds at most 256 rows and 2 MiB. Source-native fetch queues are bounded at 8 MiB. There is no task per record. The shared query thread polls source channels round-robin and uses one generic evaluator. One hot source cannot grow an unbounded cross-thread queue. New query shapes require a one-time relation visit; updates check changed keys against the topic's active shapes and maintain the existing AVL rank index, without sorting or scanning the entire relation per update. Window extraction is O(log matching rows + window rows). The existing transport window comparison can be quadratic in the bounded window (maximum 1024 delivered rows).

The end observer uses the same read-committed Kafka client for bounded ListOffsets requests at a one-second cadence, with request-start timestamps. It writes only readable-end/fetched/high-watermark/queue diagnostics. The source owner exclusively controls assignment/bootstrap/durable/derived/serving progress. Failed samples retain their original age. Readiness is false while a canonical commit has not completed derived application, or while any configured required source partition lacks fresh evidence or exceeds its policy. The common health progress clock is the oldest required source owner turn, advanced by the query owner; a healthy HTTP thread cannot indefinitely hide a stalled source owner.

Query acquisition and live publication use a fresh authority transaction for the query's single source. Startup obtains authority for every configured source. A query reads the last complete derived committed cut of its topic; an owner can have one newer canonical event awaiting derived dispatch. The result's source sequence identifies its actual complete cut. Readiness is false during that durability/derivation gap. Sources are independently atomic. A startup progress vector is a vector of source cuts, not a globally atomic cross-source snapshot.

Control channels have four slots per source. Synchronous authority checks have a 30-second caller deadline; the pinned native transaction calls have nominal 10-second timeouts which are not forcibly cancellable wall-clock guarantees. Owners also check authority periodically. The independent observer has a bounded 1.5-second caller shutdown wait. Process shutdown stops new source admissions; a native call already executing can require process termination, followed by ordinary canonical reconstruction. No unsafe degraded-serving mode, distributed sharding, live catalog mutation or online migration is present.

Live committed batches accumulate measured evaluator application time in `derived_ns`/`view_server.derived.duration`; initial reconstruction is excluded, as in the accepted coordinator counter lifecycle. Failed application attempts are timed before fatal propagation. Fetch diagnostics cannot precede the successfully established startup seek or subsequently committed NEXT, even while native statistics still report a pre-seek cursor. Neither diagnostic adjustment changes serving progress or readiness decisions. Blocked-peer and queued-output gauges include the same pending health-frame accounting as the product service.

## Retention format 3

An explicit per-topic retention policy selects format 3. An absent policy keeps
format 2, including its existing serialized fields and digest inputs. Format 3
requires a fresh, explicitly configured canonical namespace; there is no automatic
migration, wipe, or interpretation of format-2 bytes as retention metadata.
Canonical topics remain compact-only. Application expiry writes an explicit
logical deletion, never a Kafka tombstone, and preserves sticky ownership.

The format-3 `Binding` serializes these fields in order: `format`, `topic`, `schema`,
`source_incarnation`, `source_topic`, `state_topic`, `group`, `descriptor`,
`partitions`, and `retention`. The normalized retention object contains the present
`max_age_ms`, `max_messages`, and `count_scope` fields. The scopes are `whole_topic`
for a delete-only source and `per_source_key` for compact or compact,delete.
The binding must match exactly, including policy, on every replayed envelope.
The descriptor digest retains the accepted rowId tuple version, descriptors,
value mapping, typed key fields, and configured identity selector binding.

Canonical keys begin with byte 3. Their second byte is 1 for ROW (followed by the
UTF-8 rowId), 2 for partition-local NEXT, 3 for the partition-zero manifest, or 4
for an authority barrier. The JSON envelope has `format`, `binding`, `value`, and
`digest`. Its digest is SHA-256 of serde_json's compact serialization of
`[format, binding, partition, canonical_key_bytes, value]`. The key bytes and
partition are therefore part of the integrity check. These hashes detect
inconsistent records; they are not signatures against an authorized Kafka writer.

ROW contains `key`, `owner`, `key_identity`, `row`, and, for active retained rows,
`retention_order` plus `age_origin_ms` when age retention is enabled. `owner` is
the source partition and `key_identity` is the SHA-256 of the serialized source
key. A deleted ROW has `row: null` and omits both retention fields. Its sticky
key/partition ownership remains subject to `max_rows`. An active row requires
exactly the metadata appropriate to its bound policy. Replacing a row removes
its previous recency, per-key, and expiry entries.

A ROW's root contribution is SHA-256 of compact serde_json serialization of
`[key, owner, key_identity, row, age_origin_ms, retention_order]`, using null for
absent optional values. The manifest `root` is the XOR of these contributions for
all current ROW records, including sticky deletions. Format 2 continues to hash
`[key, owner, key_identity, row]` and omits the format-3 metadata from envelopes.

The format-3 manifest includes the existing `sequence`, complete `next` vector,
and `root`, plus required `content_version`, `maintenance_sequence`, `next_order`,
and `last_reference_time_ms`. `sequence` counts source batches; timer work does
not increment it or advance source NEXT. `maintenance_sequence` counts expiry
chunks. `content_version = sequence + maintenance_sequence` identifies the
canonical and derived cut acknowledged internally. `next_order` is the persisted
owner admission-order high-watermark. `last_reference_time_ms` is the persisted
reference-time high-watermark. Versions, order, and reference time cannot regress;
all increments and duration sums are checked.

The age origin, inclusive expiry boundary, timestamp skew rules, and reference
clock are specified in RETENTION-CONTRACT.md. Replay preserves those values; it
does not assign a new receipt time. Due work runs under the serialized source
owner, in at most 256-row/2-MiB chunks at the configured 250-ms cadence. Commit
certainty precedes folding and derived application. Only a completed retained cut
may publish fresh results. Existing acquisition cleanup remains valid while
ordinary retention is pending, with identity checks and fresh authority guards
still enforced. An uncertain commit, malformed metadata, root/NEXT mismatch,
fencing failure, or unexpected derived acknowledgement fails closed.

Restore validates every envelope, rebuilds indexes, and performs a full row/root/
index audit at the captured canonical cut. It completes overdue retention before
fresh readiness and results. Live source/maintenance commits fold only changed
ROWs, checking old index membership and new insertion invariants. They compare the
maintained root/NEXT/versions with the committed manifest and check index
cardinalities/order without rescanning unchanged rows. Full reconstruction audits
remain at restore boundaries. This distinction does not cache serving authority:
query guards and Kafka transaction fencing remain live operations.
