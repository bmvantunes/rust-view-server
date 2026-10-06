# Schema expansion v1 — attempt ledger

Evidence paths below are relative to `evidence/schema-expansion/` in the delivery. Raw failures are retained. Final qualification uses Rust 1.96.1 binaries; preliminary host-compiler results are explicitly superseded.

| Attempt | Outcome and resolution |
|---|---|
| native-check-initial | PASS initial compile, superseded by pinned tests. |
| ingestion-check-initial / source-tests-initial | FAIL missing new Descriptor members/exhaustive enum test arms; fixed without relaxing old presence assertions. |
| source-tests-second | FAIL unresolved descriptor message references. Generator now emits fully qualified references; source-tests-third passed, later pinned tests supersede it. |
| typecheck-initial | FAIL runtime validator narrowing; fixed. Subsequent typecheck files pass. |
| generation-types-attempt1 | Harness terminated on the intentionally unknown decimal type; negatives isolated in child processes. |
| generation-types-attempt2/final/bounds | Preliminary PASS was insufficient: macOS temporary-directory aliases triggered import containment checks before intended negatives. Original `generation-and-types-pre-path-fix.json` preserves those diagnostics. Canonicalizing the local root fixes this; final test asserts a case-specific error for each of 14 negatives. |
| ingestion-tests | FAIL incompatible build outputs in a shared target directory. Isolated targets resolve it. |
| ingestion-tests-isolated | 34 pass / one listener BLOCKED by sandbox; not a pass. Scoped loopback rerun passed. Final pinned run passes all 59 targeted tests. |
| browser-build | FAIL nonexistent vite wrapper; use the already cached vp build wrapper. browser-build-second passes. |
| browser-regressions-attempt1 | PASS 81 Chromium tests; no assertion changes. |
| work-comparison | FAIL Rust character/string replacement typo. Corrected; pinned work-comparison-pinned passes. |
| kafka-attempt1 | BLOCKED private listener during accidental execution of the inherited harness entry point. Wrapper now loads its definitions without launching its main routine. No passing execution claimed. |
| kafka-attempt2 / schema-b3da6793 | FAIL independent oracle ordered absent parent as an empty-string default. Corrected the oracle to the declared missing-before-value ordering; raw observations retained. |
| kafka-attempt3 / schema-3f404376 | Preliminary PASS on host Rust 1.98.1; not final pinned qualification. |
| kafka-attempt4 / schema-90041a81 | Preliminary fuller PASS (filters and enum aggregates) on host Rust 1.98.1; telemetry-preliminary is tied only to it. |
| cleanup-attempt1 / schema-cleanup-green-d0440ee9 | Preliminary cleanup PASS on host Rust 1.98.1. |
| build.log vs build-pinned.log | Initial RUSTUP_TOOLCHAIN setting did not override the host compiler selected by absolute cargo. All three deliverable binaries rebuilt with explicit cargo, RUSTC and RUSTDOC 1.96.1 paths. Both receipt sets retained; only pinned binaries delivered as new artifacts. |
| kafka-pinned / schema-03037451 | FAIL initial raw acquisition raced source updates; maintenance-pending rejection was visible in last-observation. Added a bounded initial empty-acquisition readiness wait before producing input. Query assertions unchanged. |
| kafka-pinned-retry / schema-31535bf9 | Harness FAIL: the initial-empty wait was accidentally inserted a second time after populated cuts. Removed only the duplicate wait; original failure retained. |
| kafka-pinned-final / schema-ac3ff292 | PASS all ten checkpoints on final pinned ordinary binary; exact configs, inputs, raw observations, wire counts, source progress, denial probe and binary/browser/script bindings retained. |
| cleanup-pinned / schema-cleanup-green-4511f7b6 | PASS actual pending-maintenance cleanup on final pinned fault binary. |
| Interactive nested codec assertion | Initial deepStrictEqual rejected the established decoder's null-prototype object maps despite equal payloads. This was an interactive tool result, not a separately captured raw log. Runnable codec test now explicitly asserts the null prototype and compares normalized payloads; nested-codec PASS. |
| generation-types-final-qualified | PASS clean reproducibility, all 14 intended rejection reasons, browser/contracts compiler and ten unsuppressed type failures. |
| telemetry-final | PASS independent decoding of actual final pinned-run exports, separate from preliminary telemetry. |
| final-build-input-verification | PASS all final Rust source inputs match the three pinned build receipts and remained unchanged during each build. |

The later generator path-canonicalization fix changes build-time validation and generation provenance only; emitted schema/descriptors and browser TypeScript remain the same tested content. Final identities and manifests include the corrected generator. No server source changed after pinned build/test qualification.

Packaging attempt 1 failed because cached license files have timestamps before ZIP's 1980 lower bound. The partial archive failed complete-manifest verification, as expected. Packaging now clamps unsupported archive timestamps with Python's strict_timestamps=False; file contents and hashes are unchanged. The final archive must pass the full composition verifier. The failures were captured in the tool transcript; this ledger does not label them as passing archives.
