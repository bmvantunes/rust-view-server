#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cp "$SCRIPT_DIR/../fixtures/product-core-100.json" "$SCRIPT_DIR/../browser/public/product-core-100.json"
cd "$SCRIPT_DIR/../browser"
./node_modules/.bin/vitest run

PREFIX=${EVIDENCE_PREFIX:-v5}
cp v5-browser-runtime.json "../evidence/$PREFIX-browser-runtime.json"
cp v5-browser-counters.json "../evidence/$PREFIX-browser-counters.json"
