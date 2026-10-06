#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
export CARGO_BUILD_JOBS=1
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-product-v5-clippy-target"
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
export PATH="$(dirname "$RUSTC"):$PATH"
export CLIPPY_CONF_DIR="$ROOT"
cd "$ROOT"
cargo clippy --version
cargo clippy --locked --offline --manifest-path native/Cargo.toml --all-targets -- -D clippy::disallowed_methods
