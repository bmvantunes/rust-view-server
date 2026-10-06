#!/bin/sh
# Pinned local feature tests; no broker or browser ports opened by this script.
set -eu
cd "$(dirname "$0")/.."
export RUSTC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc
export RUSTDOC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc
export PATH=/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin:$PATH
export CARGO_BUILD_JOBS=2
CARGO_TARGET_DIR=/private/tmp/functional-language-native-target /Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo test --offline --locked --manifest-path native/Cargo.toml --lib --test text_predicates --test global_having
CARGO_TARGET_DIR=/private/tmp/functional-language-target /Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo test --offline --locked --manifest-path ingestion/Cargo.toml --features kafka-canonical --test generic_owner --test schema_expansion
browser/node_modules/.bin/tsc --noEmit -p browser/tsconfig.json
node scripts/test-text-predicates.ts
node scripts/test-global-having.ts
