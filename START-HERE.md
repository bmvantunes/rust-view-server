# Start here

Definitive local project: `/Users/bruno/Projects/rust-view-server/developer-handover-20261006/work`.
This is the complete CP4 source import plus separately recorded developer-handover and repository-usability changes. No historical ZIP or predecessor checkout is needed for production source. See `PROVENANCE.md` and `provenance/` for the exact boundary.

The [GitHub repository](https://github.com/bmvantunes/rust-view-server) is public as of 2026-10-06; creation, push and visibility authorization are complete. See [PROVENANCE.md](PROVENANCE.md) for the retained public-metadata caveat and the distinction from a complete public-release/security review. The private local example below still runs on loopback; “private” there describes the example, not GitHub visibility.

## Qualified tools and dependencies

- macOS arm64 is the locally exercised host. Rust **1.96.1** (root `rust-toolchain.toml`), Node **26.1.0** (`.node-version`), Python **3.9.6**, CMake **4.4.3** and the existing Apple command-line C/C++ toolchain are used here.
- Browser dependencies: **pnpm 11.9.0**, TypeScript **7.0.2**, React **19.2.8**, `@types/react` **19.2.18**, `@types/react-dom` **19.2.4**, Vite Plus **0.3.0**. `browser/package.json` and `browser/pnpm-lock.yaml` are authoritative. TypeScript 5 is unsupported; the authoritative check rejects missing or mismatched local compilers and never downloads a fallback.
- Existing codec/generator dependencies use their existing npm lockfiles: `experiments/v131/package-lock.json` and the historical `experiments/v13/package-lock.json`. Keep this established layout; no package-manager migration.
- For the optional private example: Java **21.0.12.1** and the Kafka **2.13 / 4.1.0** distribution. Set `JAVA_HOME` and `KAFKA_HOME` explicitly. Neither is committed or installed by the launcher.

On a new machine, install those tool versions through your normal approved process. Populate dependencies with `pnpm --dir browser install --frozen-lockfile`, `npm --prefix experiments/v131 ci`, and (for legacy codec tests) `npm --prefix experiments/v13 ci`. These are setup instructions, not a claim of network installation testing. The ambient pnpm wrapper currently reports 12.9.1, so select the declared 11.9.0 before any fresh browser installation; no dependency install or lockfile rewrite was run here. This local preparation reuses already installed matching dependency caches; symlinks and caches are not tracked. Rust locked dependencies must be available in the Cargo cache for `--offline`.

## Generate, check, build, smoke

Run from the repository root with Node26.1.0 on PATH:

```sh
node scripts/generate-proto-topics.mjs --input examples/schema-expansion/topics.proto --out .
sh scripts/typecheck-all.sh
python3 scripts/build-local.py --offline
(cd browser && node node_modules/vite-plus/bin/vp build --config vite.join.config.ts)
node scripts/test-text-predicates.ts
node scripts/test-global-having.ts
node scripts/test-field-patches.mjs
```

Omit `--offline` only when normal dependency fetching is intended and permitted. The build uses Rust1.96.1 and locked manifests, writes `.local/bin/view_server` and `.local/bin/generic_kafka_producer`, and records binary hashes in `.local/bin/BUILD.json`. `CARGO_TARGET_DIR` may explicitly select an existing build cache; it supplies no missing source. Default target output is `.local/target`. The original historical binaries remain untouched outside Git.

For a bounded Rust behavior check:

```sh
CARGO_BUILD_JOBS=2 rustup run 1.96.1 cargo test --offline --locked --manifest-path native/Cargo.toml --test text_predicates --test global_having
```

The check entrypoints print the resolved **native executable path**, and verify its actual version. The package is `browser/node_modules/typescript/package.json`; its `lib/getExePath.js` resolves the platform compiler. Actual React declarations come from the installed `@types/react` and `@types/react-dom`, with no shim. The local verification receipt records full resolved paths. No global `tsc` is used.

## Private local example

On this Mac, the existing approved installations can be selected explicitly:

```sh
cd /Users/bruno/Projects/rust-view-server/developer-handover-20261006/work
export PATH="/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"
export KAFKA_HOME="/Users/bruno/Projects/rust-view-server/followups/kill-sqlite-hot-path-20261003/runtime/kafka_2.13-4.1.0"
python3 scripts/local-demo.py start
```

The Kafka path above is an existing **tool distribution**, not a source or broker-data dependency. Other machines supply their own installation path. First run the build and dependency setup above. The launcher checks prerequisites, type-checks, builds the existing page, creates a new private loopback broker and two illustrative sources, then reports:

**http://127.0.0.1:4173/**

A busy port fails without killing its owner; explicitly choose `--port 4174` if desired. The launcher prints the actual URL. Runtime data, process logs and configuration stay in this checkout's ignored `.local/`. Keep the foreground terminal open. Normal sandbox permission for local listeners may be needed; no permission bypass or persistent machine setup is performed.

Use Match / Update / Delete / Reset for the small controlled source flow. The page uses the real service, production Worker, `useLiveQuery` and `useLiveQueryViewport`, with exact selected fields and readonly `rowId`. It shows nested values/enums, text filtering, grouped/global aggregates with HAVING, a many-to-one LEFT join, and freshness/dependency status. Query calculation stays in the service. Compression and selected-field patches remain off.

Stop with Ctrl+C, or from another terminal in this repository:

```sh
python3 scripts/local-demo.py status
python3 scripts/local-demo.py stop
```

Stop authenticates to this checkout's run and signals only processes started by that launcher. It does not search for or kill other Kafka/Node/Java processes. Logs and private data are retained. The verification run is stopped before handover.

## Source locations and limits

- Application/service configuration: `.local/runtime/<run>/service.json`, reported by `status`; created by `scripts/local-demo.py`. Loopback broker template: `examples/local/broker.properties`.
- Example queries and hooks: `browser/src/join-demo.tsx`; controlled illustrative source values: `scripts/local-source.mjs`.
- Illustrative schema: `examples/schema-expansion/*.proto`; generator: `scripts/generate-proto-topics.mjs`; generated schema/catalog/bindings: `browser/src/generated/` and `fixtures/expanded-topics/`.
- Current contracts: `LANGUAGE-CONTRACT.md`, `AGGREGATE-CONTRACT.md`, `JOIN-CONTRACT.md`, `FIELD-PATCH-CONTRACT.md`, `SCHEMA-EXPANSION-CONTRACT.md`, `RETENTION-CONTRACT.md`, `TOPIC-DURABLE-FORMAT.md`.
- Legacy harnesses and their external fixtures are described in `LEGACY-TESTS.md`. Their presence does not mean every historical command is portable or was rerun.

Company Decimal/Buf mapping remains input-pending. Further demo consolidation and all shadcn-table integration are deferred. No new product features or broad qualification campaign are part of this handover.
