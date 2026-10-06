#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
export RUSTC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustc
export RUSTDOC=/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/rustdoc
export CARGO_TARGET_DIR=/private/tmp/schema-expansion-v1-target
export CARGO_BUILD_JOBS=2
/Users/bruno/.rustup/toolchains/1.96.1-aarch64-apple-darwin/bin/cargo test --offline --locked --manifest-path ingestion/Cargo.toml --features kafka-canonical --lib --test generic_owner --test source_identity --test generic_source_config --test source_presence --test schema_expansion -- --nocapture
