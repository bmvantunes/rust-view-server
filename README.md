# Generic raw and grouped queries

This work copy extends the accepted proto-first/public-rowId implementation with
incremental count, countDistinct, sum, min, max and avg. Start with
`AGGREGATE-CONTRACT.md`, `examples/grouped/README.md` and the delivery's current
`HANDOFF.md`. Other baseline contracts/evidence retain their original scope and
verdicts; their historical statements excluding aggregates describe the baseline.

`createTopicHooks(catalog)` binds both raw and grouped result inference to generated
source schemas. Source rows remain authored only in .proto. Remote grouped queries
use the v15 WebSocket/MessagePack service and negotiate grouped_aggregates_v1.
The local legacy WASM mode is unchanged and does not execute generic grouped queries.

Use `bin/view_server_grouped` for the newly qualified ordinary service.
`bin/view_server_grouped_faults` is for isolated fault qualification only.
The old baseline executables remain preserved under their original names.
