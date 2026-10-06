#!/bin/sh
set -eu
WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-product-count-distinct-investigation-target"
export CARGO_BUILD_JOBS=1
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
rustup run 1.96.1 rustc --version --verbose
rustup run 1.96.1 cargo tree --locked --offline --manifest-path "$WORKSPACE_ROOT/investigations/count-distinct/Cargo.toml"
rustup run 1.96.1 cargo run --locked --offline --manifest-path "$WORKSPACE_ROOT/investigations/count-distinct/Cargo.toml"
