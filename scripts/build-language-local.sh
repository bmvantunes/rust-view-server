#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export RUSTC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc
export RUSTDOC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc
export CARGO_TARGET_DIR=/private/tmp/functional-language-target
export CARGO_BUILD_JOBS=2
export PATH=/Users/bruno/.vite-plus/js_runtime/node/26.1.0/bin:$PATH
/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo build --offline --locked --manifest-path ingestion/Cargo.toml --features kafka-canonical --bin view_server --example generic_kafka_producer
mkdir -p bin
cp "$CARGO_TARGET_DIR/debug/view_server" bin/view_server_expanded
cp "$CARGO_TARGET_DIR/debug/examples/generic_kafka_producer" bin/generic_kafka_producer_expanded
cd browser
node node_modules/vite-plus/bin/vp build --config vite.grouped.config.ts
