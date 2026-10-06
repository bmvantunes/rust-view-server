#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
export RUSTDOC=$(rustup which --toolchain 1.96.1 rustdoc)
export PATH="$(dirname "$RUSTC"):$PATH"
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-product-v7-target"
export CARGO_BUILD_JOBS=2
export CLIPPY_CONF_DIR="$ROOT"
cargo clippy --locked --offline --manifest-path "$ROOT/ingestion/Cargo.toml" --all-features --all-targets -- -D clippy::disallowed_methods
cargo test --locked --offline --manifest-path "$ROOT/ingestion/Cargo.toml" --all-features -- --nocapture
