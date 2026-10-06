# Historical test prerequisites

The complete test and experiment source is retained. The supported bounded repository checks are listed in START-HERE.md; old scripts are not all portable build entrypoints.

- `build-native-rowid.py`, `run-native-rowid.py`, historical `scripts/build-*.py`, and `scripts/test-language-local.sh` may name previous caches, binary aliases or host-specific tools. Use `scripts/build-local.py` for the current ordinary service/producer.
- `scripts/run-retention-kafka.py` and derived functional/join/evolution campaign harnesses assume an older directory layout, sealed binaries and private Kafka tooling. `scripts/local-demo.py` reuses helper definitions but explicitly replaces all runtime/tool paths with repository-local state and configured host tools. Do not run the historical campaigns as a fresh-clone quickstart.
- `scripts/test-ingestion.sh` / blanket all-features test runs include historical `f1_socket` integration tests requiring `KSQ_REVIEW_RUNTIME`, `F1_CONFIG_DIR`, broker configuration and optional TLS dependencies. Those prerequisites are not bundled, and those campaigns were not rerun here.
- `scripts/test-row-reference.mjs` additionally needs the external `../../reference` client fixture at its recorded commit; `verify-trace-wire.mjs` writes to an outside-checkout historical evidence path. Neither is a repository quickstart command. `test-join-contract.ts` needs a native `JOIN_VECTOR` log argument and is not an argument-free smoke.
- Old acceptance/Python/browser harnesses may compare missing executable aliases or archived evidence. Historical native executable aliases are indexed in provenance but excluded from Git; missing prerequisites are not passing tests.
- The synthetic `ingestion/fixtures/durable-format-v1.db`, `durable-format-v2.db`, and recovery JSON are retained as durable-format compatibility test inputs, not runtime databases. Generated catalogs, descriptors and TypeScript bindings are retained because consumers and tests use them.
- `browser/public/product_core.wasm` and `request_admission.wasm` are intentionally retained reviewed browser runtime assets. Their duplicate build-directory copies are excluded. Historical WASM rebuild scripts remain available but are not claimed freshly qualified by repository packaging.

No historical review verdict is extended to newly edited scripts. Read provenance and the repository verification receipt for exact executed checks.
