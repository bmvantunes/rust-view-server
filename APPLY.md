# Apply and verify topic-retention-v1.1

This package is a complete sparse overlay for the accepted grouped-aggregates-v1.2 archive with SHA-256:

`e202466bc8e0c3b51a89963789802f812e3dc481b594330efe63d0818e239465`

Do not copy project files onto the baseline archive's outer directory. They belong inside its `work/` project tree. Do not overlay an unrelated checkout or infer that an old baseline binary is the repaired service.

1. Verify the detached zip checksum. Extract this small package into a review directory.
2. Choose a new, nonexistent destination ending in `work`.
3. Run the included verifier with absolute paths:

```sh
python3 topic-retention-v1.1/scripts/verify-retention-composition.py \
  --base /absolute/path/grouped-aggregates-v1.2.zip \
  --overlay /absolute/path/topic-retention-v1.1.zip \
  --dest /absolute/path/new-retention-candidate/work
```

The verifier checks the exact base hash, every overlay member and complete member coverage, then applies only the declared project-relative source/artifact files to a new extraction of the base's work tree. It verifies the complete merged source/artifact inventory. Evidence is separately covered by the package manifest. The original base and overlay are not modified. The previous retention-v1 overlay is provenance, not an additional application step.

The selected ordinary/fault/producer binaries in `bin/` are the newly qualified identities listed in RETENTION-V1.1-HANDOFF.md. Other inherited binaries are not substitutes. Build logs identify the local pinned Rust toolchain; browser logs identify the pinned Node/TypeScript/React/Playwright cache. Replay scripts intentionally target the documented local Java21/Kafka4.1/private-loopback environment. They require normal listener permission. The real gate's read-only snapshot command used `ingestion/target/release/examples/retention_snapshot`; build that example with the recorded Cargo command, or copy the byte-identical `bin/retention_snapshot` artifact to that path in the new candidate. No dependency installation is needed in the documented cached environment.

`RETENTION-REPAIR.diff` is the minimal v1-to-v1.1 product repair diff, including diagnostic-only work counters. Contracts, tests and harness changes are supplied as source. `COMPOSITION.json` covers the full merged source/artifact tree; `FILES.sha256` covers the complete sparse package, including raw evidence. Gate results and all retained failed attempts are classified in GATE-INVENTORY.json and ATTEMPTS.md.
