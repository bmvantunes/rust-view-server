#!/bin/sh
# Separate diagnostic suite: not a v5 product acceptance gate.
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
export CARGO_BUILD_JOBS=1
export CARGO_TARGET_DIR="${TMPDIR:-/tmp}/rust-product-count-distinct-investigation-target"
export RUSTC=$(rustup which --toolchain 1.96.1 rustc)
export RUSTDOC=$(rustup which --toolchain 1.96.1 rustdoc)
export PATH="$(dirname "$RUSTC"):$PATH"
export CLIPPY_CONF_DIR="$ROOT"
MANIFEST=investigations/count-distinct/Cargo.toml
mkdir -p logs
rustc --version --verbose > logs/count-distinct-toolchain.log
cargo --version --verbose >> logs/count-distinct-toolchain.log
cargo clippy --version >> logs/count-distinct-toolchain.log
cargo tree --locked --offline --manifest-path "$MANIFEST" >> logs/count-distinct-toolchain.log
cargo clippy --locked --offline --manifest-path "$MANIFEST" --all-targets -- -D clippy::disallowed_methods -D unfulfilled_lint_expectations > logs/count-distinct-clippy.log 2>&1
cargo test --locked --offline --manifest-path "$MANIFEST" --test count_distinct --test operator -- --nocapture > logs/count-distinct-contract.log 2>&1
cargo run --locked --offline --manifest-path "$MANIFEST" > logs/count-distinct-investigation-addendum.log 2>&1
cargo run --locked --offline --manifest-path "$MANIFEST" --bin six_customers > logs/count-distinct-six-customers.log 2>&1
set +e
cargo run --locked --offline --manifest-path "$MANIFEST" --bin minimal > logs/count-distinct-minimal-addendum.log 2>&1
code=$?
set -e
test "$code" -eq 101
grep -q 'distinct_total must retract its final occurrence' logs/count-distinct-minimal-addendum.log
printf '\nEXPECTED_DEFECT_EXIT=%s\n' "$code" >> logs/count-distinct-minimal-addendum.log
printf 'PASS: isolated lint, contract/operator tests, nine-epoch comparison, six-customer case; minimal defect assertion fails as expected (101).\n'
