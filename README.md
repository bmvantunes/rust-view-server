# Rust view-server

Complete source for the reviewed functional CP4 view-server: Rust service and ingestion, browser SDK/production Worker/React hooks, illustrative protobuf schemas, generated contracts, examples and tests.

Start with [START-HERE.md](START-HERE.md) for pinned tools, generation, authoritative TypeScript7.0.2 checks, local builds and the private example. [PROVENANCE.md](PROVENANCE.md) distinguishes the exact reviewed CP4 source from subsequent handover and repository-usability changes. Existing contract documents retain their original scope; old experiment claims are not blanket qualification of this checkout.

Current functionality includes exact selected fields, nested/enum schemas, text predicates, grouped/global aggregates and HAVING, bounded INNER/LEFT joins, dependency reporting, opt-in selected-field patches, and compatible schema evolution/name diagnostics. Compression remains off; company-specific Decimal/Buf integration is input-pending.

Historical executable aliases, caches, broker data, archives and bulk evidence are preserved outside Git. No new license has been selected; inherited copyright and third-party notices remain intact. [LEGACY-TESTS.md](LEGACY-TESTS.md) identifies historical test prerequisites. [FUTURE-WORK.md](FUTURE-WORK.md) records deferred consumer work.
