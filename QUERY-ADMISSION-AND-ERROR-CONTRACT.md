# V13.1 request admission and ordered errors

Both candidates are qualified, and MessagePack is selected for production by the new comparison. Final fresh acceptance and exact delivered identities are recorded separately in the checkpoint and validation record.

## Three boundaries

The product-owned `admission` Rust crate imports the existing `ProductCommand`, `Query`, `Expr`, `ExactInteger`, and `ExactDecimal` deserializers from the native product crate. Its admission-only WASM artifact is loaded by both experimental remote Workers before opening their sockets. It creates no ProductEngine and evaluates no rows. Local evaluator WASM is a separate artifact and mode.

Raw request → existing full-envelope source parser → typed product command → canonical ABI value → Protobuf or MessagePack encoder. Native binary peers call the same admission crate after structural decoding. The codecs contain no source spelling parser. `1__1_` becomes exact 11; coefficient 110/scale 0 becomes coefficient 11/scale -1. Boolean expression structure is preserved: simplifying it here could change observable query-generation behavior.

JSON is used only inside the local admission WASM ABI and existing native in-memory adapters. WebSocket application messages are binary trees. Exact values use minimal sign/magnitude bytes, never decimal text or floats. Canonical u64 request limits also cross the JS ABI as strings to avoid rounding, then use magnitude bytes on the wire. This corrects the earlier assumption that every request window value was a safe JS integer: JSON admits very large requested query limits when the actual result fits the existing extraction bound. Navigation retains its existing stricter resource limit.

## Source and wire bounds

The remote source envelope retains its existing 65,536-byte bound and serde_json default recursion limit. A full command envelope admits 122 nested NOT expressions around true; 123 exceeds that existing parser boundary. The exact envelope and actual-peer boundary tests are recorded in V13.1 evidence. No product expression-depth rule is added.

Both binary codecs use semantic tree depth 128 (root depth zero), 65,536 values including map keys, 8,192 entries per collection, and 4 MiB maximum frame. Structural preflight checks lengths and depth before library allocation/recursion. Protobuf wrapper recursion needs a separate internal allowance: JavaScript permits 3×128+4 wrapper levels; the separately identified vendored `view-wire-prost` package disables its wrapper guard only behind the finite shared preflight; registry `prost` used by source ingestion retains its default recursion guard. MessagePack's Rust library receives 2×128+4 internal levels. Both have exact-boundary and boundary+1 tests for arrays and maps.

Binary input allows 4 MiB because schema overhead may expand an admitted 64 KiB source envelope. The native peer rechecks the reconstructed source envelope byte/recursion bounds. Output queue accounting uses actual encoded bytes. This changes wire resource accounting without narrowing source capability.

## Recoverable rejection

Typing failures (invalid decimal scale, invalid exact value, unsupported predicate, invalid typed window) produce a fixed `command_rejected` envelope carrying only request ID, traceparent, subscription, and code `invalid_query`. The invalid query and source spelling are absent from the frame. No client-authored error text is trusted.

The native owner processes this envelope in the same WebSocket order as ordinary commands, advances the connection's monotonic request ID, and enqueues one `request_error` with the owner's current confirmed acquisition. It makes no acquisition mutation. The Worker keeps its pending entry until that response and does not synthesize an early error. Stateful resource/identity rejections continue through the native owner.

The provider restores the previous acquisition only while the rejected invocation still owns that subscription. A successor acquisition prevents stale rollback. Duplicate error responses find no pending request and cannot settle again. Live results remain tied to confirmed acquisitions. A same-version navigation still gets a solicited result and ACK.

Four requests may be dispatched together. Valid A / invalid B / valid replacement C settles in server order, and C remains authoritative. Navigation or close submitted before B's rejection captures B's proposed acquisition; JSON rejects that obsolete navigation/close too. After B settles, a subsequent navigation uses restored A. The tests preserve that existing behavior rather than retargeting an in-flight command.

## Terminal failure

Truncated/ambiguous envelopes, impossible tags, conflicting variants or keys, hostile lengths/depth, invalid extensions, noncanonical exact magnitudes, invalid UTF-8, incompatible versions, and broken identity/framing remain terminal. Frame preflight or canonical-wire failure is not a query spelling error. The peer is closed, acquisitions are invalidated, and pending completion is reported uncertain.

A source envelope exceeding the pre-existing byte/JSON recursion bound remains terminal. Disposal and connection loss settle outstanding work once and prohibit later delivery. Native socket tests and actual-Worker deterministic schedules report terminal vectors separately from recoverable product-command tests.

## Evidence and scope

`evidence/v13.1/red` preserves the unchanged V13 reproduction. Admission tests use the real WASM module. Query and lifecycle tests use actual native peers, WebSockets, Workers, providers, mounted hooks, and source mutations. Deterministic stale-response/disconnect schedules execute actual Worker source with a scripted socket and are explicitly labeled separately. None substitutes for the other.

The admission artifact currently links the native crate's existing evaluator ABI exports as well as its admission exports. The remote Worker calls only `admission_*`, never `product_core_*`; no evaluator handle is created and no rows are evaluated locally. This is an unused-code/download-size limitation, not a remote-result fallback. Its actual 1.4 MiB artifact and cold initialization are included in the tested/benchmarked peers. The original local evaluator Worker/artifact remains separate.

V13.1 dependency isolation regression: the first repair attempt unified `no-recursion-limit` into ingestion’s source Protobuf decoder. The unchanged JSON source decoder admits 100 nested unknown groups and rejects 101; the defective Protobuf candidate admitted 101 and 120. Those red logs and the disqualified measurement attempt are preserved. The final candidate gate tests depths 0, 99, 100, 101, and 120 in every peer and checks distinct Cargo package identities/features. Vendored source files match pinned prost 0.14.4 byte for byte; only the Cargo package name changes. `experiments/v131/vendor/PROVENANCE.json` records upstream checksums and the Apache-2.0 license is included.
