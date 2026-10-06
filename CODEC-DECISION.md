# V13.1 codec decision — MessagePack

MessagePack is the justified winner of the NEW repaired-candidate comparison. Both candidates passed correctness qualification before collection. The frozen `CODEC-DECISION-RULE.md` is unchanged (SHA-256 `de98833cd1556ce63f722e3e53f21eab0a67c9afbc03b4f4f0c1856f73e2f95e`). The verifier reports `eligible=true`, `pbAdv=false`, `mpAdv=true`, `unstable=false` across 75 process runs.

These are medians of five independent process p95 summaries, not pooled-sample percentiles. Bytes are median complete-schedule encoded totals; heartbeat traffic can vary with elapsed time. Compression is off.

| Workload | JSON bytes | Protobuf bytes | MessagePack bytes | PB / MP Worker decode+adapt µs | PB / MP native prepare+encode µs |
|---|---:|---:|---:|---:|---:|
| mixed-compat | 834,903 | 956,958 | 674,366 | 200 / 200 | 14.459 / 17.333 |
| integers-large | 2,733,817 | 2,353,782 | 1,701,936 | 1400 / 1200 | 75.042 / 88.417 |
| decimals-large | 2,646,620 | 2,319,833 | 1,667,987 | 1500 / 1200 | 71.917 / 86.709 |
| strings-large | 11,581,636 | 11,916,033 | 11,217,072 | 1000 / 700 | 65.250 / 82.208 |
| mixed-large | 1,642,116 | 1,907,062 | 1,255,216 | 900 / 600 | 63.374 / 81.668 |

MessagePack is materially smaller in four workloads in all five paired runs; the string workload is within byte equivalence. Worker decode/adaptation improves materially in four of five integer pairs and all five pairs for the other three large workloads. Protobuf has lower native preparation/encoding times, but every pair is within the predeclared 100 µs absolute tolerance. Same-clock request receipt and hook observation meet the rule’s repeatability/equivalence criteria; the table below reports their medians from this collection.

Tail/resource review: median per-process Worker p99 is lower for MessagePack in every workload. Request p99 is higher for MessagePack in four of five string runs, with three differences beyond the 1 ms/10% timing tolerance (median 10.3 ms versus 9.2 ms). This does not meet the rule’s four-of-five material-repeatability requirement, but is a retained tail limitation; it is not described as an improvement. Integer and decimal p99 also sometimes increase. No workload has four of five materially worse receipt-tail pairs. Queue-byte peaks are lower throughout; native RSS is comparable (roughly 12–16 MiB). Raw p50/p95/p99/max, individual repetitions, queue observations, ps samples and available page metrics are retained. These bounded fixture runs do not establish production capacity.

The completed collection independently checked 40,020 publications, including 34,875 live observations. The separately labeled Rust/Node phase study has 70 series (five processes, 100 retained samples per series after ten warmups); it is not browser Worker timing.

A first V13.1 attempt stopped on Node 26.1.0’s Undici `setTypeOfService EINVAL` during readiness, before its next workload. That failed collection remains under `evidence/v13.1/development/measurement-attempt-1` and contributes no selection samples. A second completed collection was disqualified when Protobuf wire configuration was found to remove the existing source decoder recursion guard through Cargo feature unification. Its raw records, exact binaries, and superseded selection remain under `evidence/v13.1/development/measurement-attempt-2`. The final third collection uses the isolated, provenance-verified wire Protobuf package, preserves source depths100/101, and started after full requalification. The node:http readiness probe avoids the first attempt’s runtime defect. Failed V13 raw data and its sealed archive remain historical and were not used for this decision.

Production selection: one MessagePack WebSocket path, protocol 13 and subprotocol `view-server.v13.msgpack`; no runtime codec selector or JSON application fallback. Protobuf WebSocket code remains experimental. The pre-existing source-ingestion Protobuf decoder is a separate responsibility and remains intact. Local evaluator WASM remains separate from remote admission and result delivery.

Exact measured executables and sources are frozen under `evidence/v13.1/measured-artifacts`. Fresh acceptance rebuilds and executes both candidates and production. Native and admission-WASM rebuilds in different directories can have different hashes; binding verifies source/lock identities and preserves both measured and freshly tested executable identities. It does not claim bit-reproducible native or admission-WASM builds.

Limitations: Chromium clock quantization; signed cross-context residuals have the documented ±200 µs uncertainty plus a 1 µs representation margin and are not selection metrics. postMessage call duration is not an isolated transfer-engine measurement. CDP page metrics omit full Worker/browser-process CPU and heap. RSS is not an allocation count. Real Kafka/Linux have not been executed on this macOS host. The admission WASM links unused evaluator ABI exports from the native crate; the remote Worker calls only admission functions and never creates/evaluates a local core.

| Workload | PB / MP receipt p95 ms | PB / MP hook p95 ms | PB / MP Worker p99 µs | PB / MP native peak RSS KiB |
|---|---:|---:|---:|---:|
| mixed-compat | 8.600 / 8.600 | 0.500 / 0.500 | 300.000 / 200.000 | 12960.000 / 12640.000 |
| integers-large | 9.000 / 8.800 | 0.500 / 0.500 | 1700.000 / 1400.000 | 14384.000 / 14176.000 |
| decimals-large | 8.900 / 8.900 | 0.500 / 0.500 | 1700.000 / 1400.000 | 14704.000 / 14288.000 |
| strings-large | 9.000 / 8.900 | 0.500 / 0.500 | 1300.000 / 800.000 | 16640.000 / 16000.000 |
| mixed-large | 9.100 / 9.200 | 0.500 / 0.500 | 1100.000 / 700.000 | 14016.000 / 13648.000 |

The first complete acceptance attempt passed 39 gates, then failed a verifier assumption that a newly built admission WASM must match the measured WASM byte for byte. Both exact images are preserved in `evidence/v13.1/development/acceptance-binding-failure`. The corrected binding retains the measured image for raw measurement identity, verifies unchanged source/lock inputs, and separately binds fresh admission unit, candidate and production tests to the rebuilt image. Poison tests reject replacing measured bytes with rebuilt bytes or changing source identity. Acceptance must restart all 40 commands; the failed run remains failed.
