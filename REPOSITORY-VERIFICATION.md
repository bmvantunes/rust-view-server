# Repository verification — 2026-10-06

This is a derived local verification record, not a replacement for sealed CP4 evidence. Tested source commit: `beed30c0ede3516daa0f46f2d74b0c18c9f6d5eb`, following baseline import `2cb3d4b6f6876e7d91330a978ca8583a34bcd21d` and exact reviewed handover commit `197fa6b52e793e6d74cb03724836b3d7f0ff96cf`. Later verification/guide edits are documentation only.

A fresh independent clone was created with `git clone --no-hardlinks . ../repository-verification-clone`. No source overlays were copied into it. Existing browser and v131 dependency caches were copied with APFS `cp -cR` into the clone; its compiler/React resolution is recorded in `provenance/local-tool-resolution.json`. The optional v13 cache was unavailable; its attempted copy failed and no legacyv13 execution is claimed. Production Cargo path dependencies and all39 literal Rust include inputs resolve inside tracked source. Native Cargo caches were explicitly selected, not copied as source.

All commands below ran from that clone with Node26.1.0 first on PATH; exit0 unless stated otherwise:

| Command | Result |
| --- | --- |
| `node scripts/generate-proto-topics.mjs --input examples/schema-expansion/topics.proto --out .` | PASS; no tracked diff |
| `sh scripts/typecheck-all.sh` | PASS both scopes; native TypeScript7.0.2 and actual React declarations |
| `(cd browser && node node_modules/vite-plus/bin/vp build --config vite.join.config.ts)` | PASS |
| `node scripts/test-text-predicates.ts` | PASS |
| `node scripts/test-global-having.ts` | PASS |
| `node scripts/test-field-patches.mjs` | PASS |
| `CARGO_TARGET_DIR=/private/tmp/schema-expansion-v1-target python3 scripts/build-local.py --offline` | PASS; explicit aarch64-apple-darwin host build; 2m50s |
| `CARGO_BUILD_JOBS=2 CARGO_TARGET_DIR=/private/tmp/functional-language-native-target rustup run 1.96.1 cargo test --offline --locked --manifest-path native/Cargo.toml --test text_predicates --test global_having` | PASS5tests;0failed/ignored |
| `python3 scripts/local-demo.py start` with documented PATH/JAVA_HOME/KAFKA_HOME | PASS preflight, new private Kafka/service, browserURL http://127.0.0.1:4173/ |
| Existing handover Playwright smoke, adapted only to clone/output paths | PASS6cuts: unmatched/matched, filter, update, delete, reset; production Worker/public hooks and health/dependencies; no browser errors; patch opt-in absent |
| `python3 scripts/local-demo.py stop` | PASS; all7task-owned process handles exited, cleanup errors empty; launcher exit0; active-run record removed |

The wrapper source and its Cargo-host repair were independently reviewed (`ACCEPT_SOURCE_PORTABILITY_LOCAL`). The earlier ten-file handover source review accepted the compiler guard and four mismatch/absence rejection checks, public API typing and controlled producer/cleanup behavior. The cleanup race repair also passed independent simulated-process checks. Final fresh-clone startup/stop exercises that repaired path with actual owned processes. These scoped reviews do not claim another full CP4 review.

The native build emitted two existing prost deprecation warnings; no product changes were made to suppress them. Reviewed CP4 production Rust/vendor files, provider/Worker, manifests and browser lockfile remain byte-identical (156 checked files in the preservation receipt). New native outputs differ from historical sealed binaries and are never labelled exact CP4 binaries:

- service: `0e2149c5d9bb95095cf6542dc0716ff43fd6cc5b1494bbfaff4ae8fc91b86153`
- producer: `dfa5ee59bba6bae750a754ed1814c70c738679a9397cfe130a48145432152a5d`

No dependency network installation, historical Kafka/fencing/retention/load campaign, fault build, optional TLS, WASM rebuild, company Buf/Decimal integration, table compatibility audit or deployment was run. The ambient pnpm12.9.1 wrapper is not the declared11.9.0; frozen fresh installation requires the latter. Existing caches suffice for all checks above. Missing legacy executable/reference prerequisites are documented separately, not counted as passing tests.

Content review covered the proposed947-file CP4 import before its first commit and all reachable baseline/handover/usability blobs afterward. No credential findings or excluded runtime/cache/native executable content were found. Required assets and203license/notice-named files were retained. Inherited developer filesystem/build paths are disclosed in PROVENANCE.md. The sealed CP4 archive hash still matches. No project license was invented.

Git signing was attempted using the configured key; noninteractive pinentry was unavailable, so local commits use a per-command unsigned setting without changing machine configuration. GitHub authentication succeeded under normal network permission. No remote was created/configured and nothing was pushed: owner/name and visibility confirmation remain required. Further demo and table work are deferred, not resumed automatically.

Full command logs, snapshots and review reports remain outside Git under the adjacent `repository-preparation`, `repository-audit` and `repository-build-audit` directories. Selected exact evidence hashes are in `provenance/external-evidence-index.json`. Bulk captures and runtime configuration are not committed.
