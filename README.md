# Rust view-server

Complete source for the reviewed functional CP4 view-server: Rust service and ingestion, browser SDK/production Worker/React hooks, illustrative protobuf schemas, generated contracts, examples and tests.

Publication status — 2026-10-06: [bmvantunes/rust-view-server](https://github.com/bmvantunes/rust-view-server) is public. Repository creation, push and the subsequent public visibility change were explicitly authorized and completed; the published checkpoint was `2a7644408d2891cab924df7d11ef3743c3170797` on `main`. Public visibility does not establish completion of a public-release or security review; the [public-metadata caveat](PROVENANCE.md) remains applicable.

[REPOSITORY-VERIFICATION.md](REPOSITORY-VERIFICATION.md) is the unchanged **pre-publication verification record dated 2026-10-06**. Its pending-authorization and no-remote statements describe that earlier checkpoint, not the current publication status.

Start with [START-HERE.md](START-HERE.md) for pinned tools, generation, authoritative TypeScript7.0.2 checks, local builds and the private example. [PROVENANCE.md](PROVENANCE.md) distinguishes the exact reviewed CP4 source from subsequent handover and repository-usability changes. Existing contract documents retain their original scope; old experiment claims are not blanket qualification of this checkout.

Current functionality includes exact selected fields, nested/enum schemas, text predicates, grouped/global aggregates and HAVING, bounded INNER/LEFT joins, dependency reporting, opt-in selected-field patches, and compatible schema evolution/name diagnostics. Compression remains off; company-specific Decimal/Buf integration is input-pending.

Historical executable aliases, caches, broker data, archives and bulk evidence are preserved outside Git. No new license has been selected; inherited copyright and third-party notices remain intact. [LEGACY-TESTS.md](LEGACY-TESTS.md) identifies historical test prerequisites. [FUTURE-WORK.md](FUTURE-WORK.md) records deferred consumer work.
