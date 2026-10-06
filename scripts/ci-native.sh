#!/bin/sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$SCRIPT_DIR/check-engine-boundary.py"
sh "$SCRIPT_DIR/lint-native.sh"
sh "$SCRIPT_DIR/test-native.sh"
