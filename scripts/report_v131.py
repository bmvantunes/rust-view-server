"""Acceptance-derived delivery reports. No speculative acceptance claims."""
import json
from pathlib import Path

def expected(root,state):
 assert state['status']=='accepted' and state['reused']==0 and not state['not_run']
 assert len(state['gates'])==40 and all(g['exit']==0 for g in state['gates'])
 m=json.loads((root/'evidence/v13.1/measurement-verification.json').read_text())
 assert m['decision']=='msgpack' and m['eligible']
 run=state['run_id']
 hashes={'bin/view_server':state['service_sha256'],'bin/view_server_faults':state['fault_service_sha256'],'browser/public/product_core.wasm':state['wasm_sha256'],'browser/public/request_admission.wasm':state['admission_wasm_sha256'],**state['browser_sha256']}
 identities='\n'.join(f'- `{name}`: `{h}`' for name,h in hashes.items())
 checkpoint=f'''# V13.1 accepted review checkpoint

V13.1 is complete: both repaired codecs are qualified, the NEW comparison selects MessagePack, one production MessagePack WebSocket path is integrated, and all 40 fresh acceptance gates passed with reused=0. Run: `{run}`. The original 34 command invocations remain in order, followed by codec build, candidate builds, full candidate qualification, measurement verification, production selection/no-fallback checks, and final evidence binding. No resume was used.

## Reproduction and repair

The preserved red reproduction in `evidence/v13.1/red` matches the failed V13: JSON passes all four cases; Protobuf and MessagePack pass quantity `1__1_`, but terminate on noncanonical decimal 110/scale0, forty NOTs, and invalid scale10001. The repaired peers pass all four plus full-envelope depth122 and a large admitted query limit. Depth123 and oversized source envelopes remain terminal, matching JSON.

The shared product-owned Rust admission crate reuses existing product deserializers and exact constructors before either codec. It preserves expression structure and full u64 query limits. The remote Worker calls the admission WASM facade; valid values reach single-codec encoders as canonical values. Invalid typed commands become server-visible sequenced rejection envelopes, never synthetic early rollbacks. The native owner returns its current confirmed acquisition in FIFO order. Malformed canonical wire frames remain terminal.

Real native/browser regressions prove previous-acquisition navigation and live updates after rejection, valid successor authority, four-command ordering, same-version navigation, close/disposal behavior, and final cleanup. Actual-Worker scripted schedules separately cover stale errors and disconnect before/after rejection. Both codecs pass exact/hostile suites, native slow-consumer schedules, 70+1 readiness/cleanup, and mounted crash/rollback/lifecycle tests. Full production acceptance repeats the preserved lifecycle checks against MessagePack.

## New decision

All 75 runs in the successful restarted collection passed. The unchanged rule selects MessagePack: pbAdv=false, mpAdv=true, unstable=false. MessagePack materially reduces bytes in four workloads and Worker decode/adaptation in all four large workloads. Protobuf's native encoding advantage remains within the predeclared 100 µs tolerance. Request/hook p95 meets the rule. MessagePack string-workload request p99 is higher in four runs, with three beyond timing equivalence (median 10.3 ms versus 9.2 ms); this does not reach the four-of-five material-repeatability threshold and remains a stated limitation. Queue bytes and median Worker p99 improve; native RSS is comparable. See `CODEC-DECISION.md` and the raw verifier for all repetitions and p50/p95/p99/max.

The interrupted readiness attempt and the disqualified second measurement collection are preserved separately and excluded. A source-decoder regression exposed Cargo feature unification: wire-only Protobuf recursion settings had disabled the existing ingestion guard. The repaired wire library uses a distinct package identity with unchanged upstream source; all peers now preserve source recursion depth100/101. The final full comparison was collected only after this repair passed complete requalification. Failed V13 measurements are historical only. The failed V13 ZIP remains SHA-256 `89b2961a6b2b4e6b0d6c785aa416ce2e075293db50c15b00cc6d521399f8ccfb`. The decision-rule SHA-256 remains `{m['rule_sha256']}`.

## Production and exact identities

Production uses `/v13`, protocol 13, `view-server.v13.msgpack`, and binary WebSocket application frames. The old endpoint and JSON application frames are rejected; healthy peers remain usable. There is no runtime codec switch. Protobuf WebSocket implementation remains experimental. The pre-existing source-ingestion Protobuf decoder remains separate and unchanged.

{identities}

These are the exact freshly built/tested delivered artifacts. Exact measured binaries and source/lock hashes are separately preserved in `evidence/v13.1/measured-artifacts`; different build directories can produce different executable identities. No bit-reproducible native/admission-WASM build claim is made. Earlier acceptance run b5a695bc-6837-421c-ab1c-1bc5c6e0b76f passed 39 gates but failed a byte-identity assumption for the rebuilt admission WASM. It remains failed. Measured WASM binds to the preserved measured image; fresh admission unit, candidate and production tests bind to the freshly built image, with unchanged source/lock and native product source checks. The accepted run restarted all 40 commands.

## Limits and handoff

Real Kafka/Linux were not executed on this macOS host; MockCluster coverage is separate. No allocation instrumentation or full Worker/process heap/CPU accounting is claimed. Browser clocks are quantized and cross-context transfer residuals are diagnostic only. The admission WASM links unused native evaluator ABI exports; the remote Worker calls only `admission_*`, creates no evaluator handle, and evaluates no rows. Local evaluator WASM remains separate.

Original closed reference-source provenance remains unavailable as recorded previously. SQLite, durability/source semantics, evaluator grammar, Differential privacy and CountDistinct exclusions remain unchanged. No Kafka canonical-store redesign, DBSP, gRPC-web, deployment, K8s or V14 work was performed. The future K8s requirement remains fully disposable pods, no writable local disk and no PVC; Kafka compacted canonical state remains a later preferred direction.

Use the adjacent archive `.sha256`, ZIP member manifest and exact gate records for verification. `NEXT-AGENT-TASK-V13.1-REVIEW.md` is the complete next task. MODEL/EFFORT of this execution were not exposed. NEW independent review is recommended to avoid inheriting implementation assumptions. Stop after that review unless the user authorizes more work.
'''
 handoff=f'''# Current handoff — V13.1 complete, MessagePack production

Read `V13.1-CHECKPOINT.md`, `QUERY-ADMISSION-AND-ERROR-CONTRACT.md`, `BINARY-WIRE-CONTRACT.md`, `CODEC-DECISION.md`, the unchanged `CODEC-DECISION-RULE.md`, and `V13.1-QUICKSTART.md`.

The shared admission/lifetime repair is qualified for both codecs. The NEW 75-run comparison justifies MessagePack. Production has one binary WebSocket path and no JSON application fallback. Fresh acceptance `{run}` passed all 40 gates, including the preserved 34 commands, with reused=0. Use `V13.1-ARTIFACT-IDENTITIES.json` and the per-member manifest for exact artifacts.

The failed V13 archive and raw data remain historical; never use their timing decision as this release's justification. The failed first V13.1 readiness collection and the second collection disqualified by source-decoder feature unification are also excluded. The isolated wire Protobuf dependency preserves the existing ingestion recursion guard, verified at depths100/101 for every peer. Exact measured executables are retained separately from fresh rebuilt acceptance executables and bound through identical source/lock inputs.

Recoverable typing errors go through a server-visible ordered rejection envelope. Previous confirmed acquisitions survive; stale errors cannot overwrite successors. Source depth122/123 and binary depth128/129 have explicit tests. Exact numerics and u64 request limits use magnitude bytes. The admission WASM has unused evaluator ABI exports inherited from its product dependency; the remote Worker never invokes them. Existing source-ingestion Protobuf remains independent of the selected WebSocket codec.

Real Kafka/Linux remain not-run. MockCluster is not a substitute. Original reference provenance remains closed. No SQLite removal, Kafka canonical-store redesign, DBSP, gRPC-web, deployment, K8s or V14 is authorized.

Next: the complete NEW independent review task in `NEXT-AGENT-TASK-V13.1-REVIEW.md`. Exact implementation-session model/effort were not exposed. A new review context provides independence. Stop after V13.1/review.
'''
 return {'V13.1-CHECKPOINT.md':checkpoint,'CLOUD-HANDOFF.md':handoff}

def write(root,state):
 for name,body in expected(root,state).items():(root/name).write_text(body)
def verify(root,state):
 for name,body in expected(root,state).items():assert (root/name).read_text()==body,'Acceptance-derived report changed: '+name
