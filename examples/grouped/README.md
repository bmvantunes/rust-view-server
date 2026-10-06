# Proto-first grouped example

`proto/topics.proto` is the only authored row/key type definition. The ordinary
existing generator derives this standalone catalog, including nullable/optional
scalar descriptors. No result proto or per-query code generation is needed.

Using the pinned Node runtime and the existing locked dependencies:

```
node scripts/generate-proto-topics.mjs --input examples/grouped/proto/topics.proto --out examples/grouped --check
node examples/grouped/generate-config.mjs /tmp/grouped-sources.json 127.0.0.1:9092 fresh-local-prefix
node examples/grouped/generate-config.mjs /tmp/grouped-retention-sources.json 127.0.0.1:9092 fresh-retention-prefix retention-v1
```

The `retention-v1` generator mode emits a fresh `canonical-rowid-retention-v3`
state namespace with an explicit typed per-topic policy. Its compact key-only
identity has at most one current row per source key; the example's
`maxRetentionMessagesPerKey: 1` is therefore nonbinding and promises no history.

`query.ts` exports a typed six-aggregate query and both hook entry points. Supply
its generated catalog to one remote BrowserProductProvider connected to `/v15`.
The query returns optional/nullable `group`, six required aliases and readonly
`rowId`. Exact sums and averages are branded aggregate decimal strings; an empty
contributor set yields total `"0"`, average/lowest/highest null. Distinct counts
missing and explicit null separately. A raw query can share the same provider.

For a complete private-broker qualification using the ordinary generated examples,
run `python3 scripts/run-grouped-kafka.py --f1`. It uses private loopback resources,
two partitions per source, the production Worker and both mounted hooks. See the
current delivery handoff for required cached tool locations and binary hashes.
