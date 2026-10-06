#!/bin/sh
set -eu
WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-differential-product-20260929-target"
export CARGO_BUILD_JOBS=1
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
export RUSTDOC=$(rustup which --toolchain 1.96.1 rustdoc)
rustup run 1.96.1 cargo test --locked --offline --manifest-path "$WORKSPACE_ROOT/native/Cargo.toml" -- --nocapture
