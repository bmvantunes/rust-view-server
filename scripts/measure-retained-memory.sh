#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-differential-product-20260929-target"
export CARGO_BUILD_JOBS=1
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
rustup run 1.96.1 cargo build --locked --offline --manifest-path "$ROOT/native/Cargo.toml" --example retained_memory
for rows in 1000 10000; do
  "$CARGO_TARGET_DIR/debug/examples/retained_memory" "$rows"
done
