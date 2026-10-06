# Schema expansion v1 — current implementation handoff

Status: **IMPLEMENTED / locally QUALIFIED within the contract below**. This is implementation qualification, not independent acceptance. The accepted retention v1.1 review remains closed. Only the company-specific Decimal/Buf mapping remains input-pending.

## What changed

Portable schema version 3 adds fully qualified enum domains, scalar leaf paths and explicit parent/leaf presence metadata. The existing generator admits bounded acyclic singular-message graphs, reused/imported types and nested declarations. Rust admits the generated descriptors dynamically, preserves parent presence in canonical rows, and reconstructs selected nested trees. Queries retain incremental membership, ranking and aggregates. The production Worker/provider, both hooks, helpers and sinks preserve nested selection and readonly rowId. A2 dynamic selection and A1 aggregate correlations remain typed.

Formats 1/2 retain SOURCE-PRESENCE and the unchanged flat catalog fingerprints. New capabilities and fingerprints explicitly admit version 3; there is no state wipe, implicit migration or reinterpretation. Existing exact decimal strings and arithmetic, including nested decimal leaves, are implemented and tested. Decimal sum/average result types and rounding remain the existing domain. Enum values are `{domain, code}`; unknown signed codes survive, aliases compare equally, min/max retain their domain, and sum/avg reject enums.

The authoritative detail is `SCHEMA-EXPANSION-CONTRACT.md`, including the presence truth table declared before implementation, enum/decimal rules, limits, nested key and envelope scope. `examples/schema-expansion/README.md` contains runnable illustrative examples. They are not company schemas.

## Exact composition and deliverables

Apply this complete sparse overlay directly over grouped-aggregates-v1.2 plus topic-retention-v1.1. Do not apply the older retention overlay. The outer `APPLY.md` and `verify-schema-expansion-composition.py` verify complete archive manifests, accepted hashes, retention composition, every changed file and the full composed inventory before writing a fresh destination ending in `work`.

| Input | SHA-256 |
|---|---|
| grouped-aggregates-v1.2.zip, 71,661,293 bytes | e202466bc8e0c3b51a89963789802f812e3dc481b594330efe63d0818e239465 |
| topic-retention-v1.1.zip, 23,048,320 bytes | 3261f464757531d2283586f53c16154bea66232eed82d4ec983b05f6e5676fd0 |
| Accepted independent retention review | 74c2300d81b68f4efae39b87d87b8f863bd8f520c95cb4d08a5593dd25a4ac88 |

`SCHEMA-EXPANSION.diff` includes changed and newly added source. Complete changed files are under `work/`; new execution evidence is under the archive's `evidence/schema-expansion/`, and license notices under `evidence/licenses/`. The original composed work tree keeps its new execution evidence under `work/evidence/schema-expansion/`. `SCHEMA-EXPANSION-IDENTITIES.json` binds sources, generated catalogs, descriptors, browser assets and binaries. `COMPOSITION.json` and `FILES.sha256` bind the complete delivery. There is one current handoff: this file; inherited handoffs describe earlier accepted slices.

## Newly built and tested binaries

Use these new binaries, not similarly named inherited artifacts. All three final binaries were built offline with explicit Rust 1.96.1 cargo/rustc/rustdoc paths on aarch64-apple-darwin. Build receipts include command, compiler details, input hashes before/after and binary hashes. `final-build-input-verification.json` verifies the final Rust inputs still match all three receipts.

| File | SHA-256 |
|---|---|
| bin/view_server_expanded | d4715cf06cad0b870f74dea977613b2790230d11fbf305a01216f3e0d9105c20 |
| bin/view_server_expanded_faults | b59f5065cf58d4850149e5beea9e4c19186a919e7a8a9ac0e23dde21e2982762 |
| bin/generic_kafka_producer_expanded | d88ac2fc1f120c5199271be6bb3d62d9654a1d9abaa5f860d43a2162c29ba51a |

The ordinary binary is schema-configured. The third root was admitted on exactly the same binary without a rebuild or per-topic branch. The fault binary is only for maintenance barrier qualification.

## Qualification evidence

All eight finite gates are PASS within the stated local bounds; `SCHEMA-EXPANSION-GATES.json` names their evidence. Failed and preliminary attempts remain present and are classified in `SCHEMA-EXPANSION-ATTEMPTS.md`.

- Generation: two identical clean generations; 14 reason-checked unsupported/metadata negatives; unchanged flat catalog; legacy generation's nine negatives; exact-ID/F-01 helper/keyword/case collision regression.
- Types: actual browser and contract compiler checks pass. Ten unsuppressed unsafe accesses produce diagnostics at the expected lines, covering nested keys, siblings, readonly rowId, cross-domain enum operands, numeric aggregate rejection, alias ancestors and A2 parent/leaf narrowing.
- Native: 39 tests pass on Rust 1.96.1. Ingestion: 59 targeted tests pass, including 35 library tests, five new raw protobuf/nested tests and seven existing SOURCE-PRESENCE tests. Presence, merged messages, unknown fields, default values, null conflicts, exact decimal strings, unknown enum codes and nested-key tombstones are exercised.
- Browser: 81 Chromium regression tests pass across ten files, including R1/R1-MIXED/H1, numeric domains, lifecycle, grouped behavior, invalid replacement and reference safety. The production browser build succeeds. The explicit nested codec check preserves null-prototype maps and exact decimal/enum payloads and rejects wrong domains or numeric decimal values.
- Final ordinary integration: `schema-ac3ff292/result.json` reports PASS on the pinned ordinary SHA above: 10 observation cuts, 20 inputs, 1,618 received frames and 4,876,410 received bytes. Two schemas, two partitions each, one provider/service and production Worker exercise raw/grouped hooks, helpers and sinks. Independent fixed-point BigInt oracles check narrow projection, filtering/multi-sort, all six aggregate functions plus enum distinct/min/max, parent replacement, group movement, null/default/missing behavior, key-only deletion, count eviction and silent expiry. Old displayed references remain unchanged. Durable/derived NEXT is sampled at completed cuts; timer-only expiry leaves source NEXT unchanged.
- Recovery in that same run: SIGKILL, offline update/tombstone, ordinary successor in a fresh empty cwd with all file writes denied, a failed write probe, same-page reacquisition and later live delta. A third configured schema then produces the expected nested row on the identical ordinary binary.
- Final maintenance cleanup: `schema-cleanup-green-4511f7b6/result.json` reports PASS on the pinned fault binary. A 520-row expiry holds after the first 256, leaving 264 pending. Close, release, unmount and reentrant cleanup reduce native subscriptions from ten to zero while a peer stays live. Independent nested raw/group counts reconcile; source NEXT is unchanged.
- Telemetry: `telemetry-final.json` independently decodes 40 fresh binary exports from the final ordinary run: ten retention spans, five maintenance spans and 112 retention metric points, with bounded attributes. Counters are maxima per instance, never summed across cumulative exports. This is small corroboration, not a telemetry platform claim.
- Licenses: 264 resolved packages and every resolved edge audited; selected license branches pass and notices are included. No dependencies were installed.

The matched comparison uses 32 rows and 128 replacements in each shape, identical exact non-enum values and nine scalar cells per row. Both show exactly 128 changed rows and no reseeding (seed count stays 32); each retains 288 scalar slots. Nested adds 32 parent-presence entries. Canonical JSON is 3,299/3,331 bytes flat/nested, result JSON 3,331/3,363. These are finite work and representation measurements, not heap/RSS, zero-copy, saturation or latency/SLA claims.

## Company Decimal and existing Buf workflow

**Implemented/tested:** the established annotated-string exact-decimal contract, including nested leaves, exact arithmetic, aggregates, wire transport and recovery.

**Awaiting actual artifacts:** the company type referenced by `message MyShit { decimal price = 1; }` and its generated Buf representation. Workspace inspection found no buf.gen.yaml, buf.yaml or buf.lock. No available definition or descriptor connects that field to a Decimal type. The historical generated-style OrderValue fixture has price as double/number. A separate historical viewserver.v1.DecimalValue query-wire experiment has no demonstrated relationship to the company producer. Neither is used to invent a mapping. The concrete one-time list of minimal missing artifacts is in the contract's Buf boundary; no duplicate schema or producer change is required.

The existing company `buf generate` workflow remains authoritative. No plugin is inferred from that CLI command, and no universal Buf plugin/output support is claimed. Only a mapping grounded in the actual type/imports and documented numeric semantics may be added later.

## Reproduction and stop boundary

Use the commands in the example README and the recorded build/test scripts with the existing caches. Java was preflighted at `/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java`. All Kafka/HTTP/browser execution used private loopback resources and fresh isolated broker data. The repository's scoped permission requirement still applies; a blocked listener is never a passing test. No production/cloud infrastructure or dependency installation was used.

This completes the bounded implementation slice. Independent acceptance has not been performed here. Contains/startsWith/endsWith, global aggregates and HAVING remain the next language milestone; gRPC stays deferred. No deployment or further milestone is included.
