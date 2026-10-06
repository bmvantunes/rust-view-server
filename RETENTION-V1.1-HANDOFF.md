# Topic retention v1.1 — focused repair handoff

Status: RET-1 and RET-2 repairs and the directly affected bounded qualification are complete. This is implementation qualification, not independent acceptance. The accepted grouped-aggregates v1.2 baseline and its A1/A2 closure were not reopened.

## Composition and preservation

The accepted base archive SHA-256 is `e202466bc8e0c3b51a89963789802f812e3dc481b594330efe63d0818e239465`. The preceding retention v1 sparse overlay is `0b3ded9cf5f1c7ed2c93e46143965418ec36511752ed92246d22dce39a3b6453`. Its sealed archive and unrelated working directories were preserved. The original review, original v1 run attempts, available build records, and previous handoff remain in this delivery as identified historical evidence.

This v1.1 package is a complete sparse overlay directly onto the accepted base's **work/** tree. It includes the required v1 changes as well as this repair; the v1 zip is not an additional application step. Follow APPLY.md and use scripts/verify-retention-composition.py to compose into a new destination named work. COMPOSITION.json identifies every merged source/artifact file and verifies complete coverage. FILES.sha256 covers all package members except itself. The detached checksum identifies the zip.

## Repairs

RET-1: the typed Close command is exempt from the pending-retention fresh-result gate. It still runs the same fresh Kafka authority guard and normal native owner command. Authentication, request/acquisition bounds, obsolete-acquisition rejection, actual resource cleanup, and genuine cleanup failure propagation are unchanged. Open/query/window commands remain subject to retention serving safety. The provider was not changed.

The pinned v1 fault binary reproduced the defect on real Kafka and the production Worker: after the first256-row expiry chunk committed,264 rows were still due; releasing A returned the actual native `retention maintenance pending` rejection, and the unchanged provider failed B. The no-pending close control succeeded. Final green evidence uses520 due rows, three maintenance chunks, direct close, watched release, mounted unmount, StrictMode, health-callback reentrant cleanup, and healthy peer navigation. Ten native subscriptions remain after the selected releases; all subscriptions/connections return to zero at final disposal. A native owner integration test separately verifies shape counts2→1→0 and protects a successor acquisition from an obsolete close.

RET-2: live transactions now use apply_committed plus audit_live. Changed rows retain schema/ownership/metadata checks, digest/root updates, checked index removals and insertions, and manifest/root/NEXT/version/cardinality/order validation. No unchanged payload traversal or full index reconstruction occurs on each live commit. Full restore/reconstruction auditing remains. Corrupt affected indexes, mismatched manifests, malformed versions, and full-restore corruption tests remain fail-closed; authority and uncertainty protections were not cached or removed.

Nineteen diagnostic cases cover retention off/on, active cardinality and many sticky deletions, and fixed256-row expiry chunks. A one-row update at4096 sticky identities made4100 row hashes and4096 audit visits before repair; after repair it makes4 row hashes,1 row fold and0 full-image visits. A256-row expiry chunk makes1024 hashes,256 folds and0 full-image visits at every tested size. A full audit call still visits all K sticky rows. These are exact work counters, not a universal constant-time or latency claim.

## Semantics and durable contract

Delete-only count retention is topic-wide. Compact and compact,delete count retention is per serialized source-key identity. Repeated `(topic,rowId)` UPSERTs keep one current row; compact key-only caps above1 are nonbinding and do not promise history. The value-dependent delete identity/null-tombstone limitation remains.

TOPIC-DURABLE-FORMAT.md now specifies actual format3 key bytes, envelope and ROW digest inputs, normalized policy binding, age/order metadata, source/maintenance/content versions, root/NEXT audit, recovery, and explicit fresh namespace requirements. Format2 compatibility when policy is absent remains explicit. RETENTION-CONTRACT.md documents cleanup admission and live-versus-restore auditing.

## Fresh qualification and raw evidence

- Final native cleanup: `evidence/repair/repair-green-235013f4/`. The independent raw oracle checks completed whole/helper/sink cuts and the absence of partial expiry publication. Source NEXT and521 committed source records stay unchanged through three timer transactions removing520 rows.
- Final real Kafka/browser gate: `evidence/retention/retention-93677c24/`. It repeats exact startup rejection, effective configs, count/UPSERT/stale generation, source silence, selected pre/post-maintenance-commit crashes, and exact same-page recovery. Six raw cuts cover whole queries, viewport helpers and sinks, raw values/presence, all six aggregates, totals, ranking and identities. Raw producer inputs/timestamps, Worker commands/results/deltas, query definitions, health cuts, Prometheus and OTLP payloads are included.
- The cleaner comparison independently validates every captured envelope digest, folds latest canonical records, recomputes ROW roots and checks NEXT/manifests/metadata. Before and after cleaning/recovery, each topic has1 retained survivor and7 expired sticky entries. Canonical end offsets can advance for authority barriers; the logical image/root/retention metadata remain exact.
- An ordinary successor runs under `/usr/bin/sandbox-exec` with all application file writes denied, from a new empty cwd. Its touch probe fails, the directory remains empty through the later live update, and its instance differs from its predecessor. The actual launch/profile/config/binary identity is recorded. Broker storage and parent-captured evidence are outside this application sandbox. Same-page raw/grouped whole/helper/sink results reacquire exactly and then update live.
- Full pinned browser and contract type projects, A1/A2 safe and unsafe type fixtures,81 mounted browser regressions, and both A1/A2 production-Worker smoke gates pass. Native checks pass35 library and31 selected integration cases, plus the complete native core suite (28+2+1+3+5). Four independent reference cases and runtime retention policy checks pass.
- The mock integration target passes3 tests with scoped loopback permission. The fresh restricted-sandbox attempt instead failed with SIGSEGV. The original v1 report described a cluster-count assertion whose raw stdout was not retained; that historical failed target is not retroactively passed by either current mock or real-Kafka success.

GATE-INVENTORY.json distinguishes executed, expected-red, inherited and unavailable-original-log scopes. ATTEMPTS.md lists failed harness/build/environment attempts. Available original v1 build/run logs are preserved under evidence/inherited-v1; original full terminal unit/type logs that were never saved remain identified as unavailable.

## Measurement boundaries

The inherited290ms figure remains one due-boundary-to-maintenance-commit observation (395ms to its polling observation), not UI latency, a percentile or SLA. Its global128 source records and live_rows2 included both off/on sources; its64 index observations were only summarized and their raw values were not retained.

The fresh paired sample `retention-measure-d9e7f97c` retains all64 raw per-topic expiry-index samples, each with one payload/one sticky key/one scheduled entry during repeated updates. Silent expiry leaves zero payload/one sticky key/zero scheduled entries, with NEXT and source counters unchanged. Its single commit delay is242ms after due; polling observes the result951ms after due. CPU/RSS and cumulative counters are explicitly process-wide, not per-topic cost. Neither paired run establishes a performance guarantee. Application count limits do not bound historical Kafka log bytes or make broker cleaning synchronous.

## Current tested identities

- Ordinary service: `263f543caa75252d896bb23101f0d8411a22e61e86d176071156ab56434116b2`
- Fault service: `c9053a7e9d97d12aa1ec6b55b58778a88e37a394efed29a8efa32f41901dfd77`
- Timestamp-capable persistent qualification producer: `e09c92f1b0c40361ba88eef471c760d1185865af2f475cf8c0f4e509ee465e5f`

Compiler input-before/input-after receipts and logs are retained in evidence/grouped/build. FINAL-BINDINGS.json identifies source and browser/native artifacts. The read-only canonical snapshot utility is also included as a byte-identical copy of its executed build artifact. No subsequent feature or broad review is started.
