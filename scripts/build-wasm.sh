#!/bin/sh
set -eu
WORKSPACE_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_TARGET_DIR=/private/tmp/rust-differential-product-wasm-20260929-target
export CARGO_BUILD_JOBS=1
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
rustup run 1.96.1 cargo build --offline --release --target wasm32-unknown-unknown --manifest-path "$WORKSPACE_ROOT/native/Cargo.toml" --lib
mkdir -p "$WORKSPACE_ROOT/browser/public"
cp "$CARGO_TARGET_DIR/wasm32-unknown-unknown/release/rust_differential_product_core.wasm" "$WORKSPACE_ROOT/browser/public/product_core.wasm"

shasum -a 256 "$WORKSPACE_ROOT/browser/public/product_core.wasm" | cut -d ' ' -f 1 > "$WORKSPACE_ROOT/browser/public/product_core.sha256"
