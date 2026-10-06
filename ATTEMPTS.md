# Attempt inventory

Final gates and exact scopes are in GATE-INVENTORY.json. Passing a different gate does not erase a failed attempt.

| Attempt | Classification | Evidence |
|---|---|---|
| Original v1 attempts and build records | Historical; preserved without relabeling | evidence/inherited-v1/ |
| repair-red-1c5c1d0c | Harness failure: asynchronous phase wait released before pending state; this did not reproduce the product defect | evidence/repair/repair-red-1c5c1d0c/ |
| repair-red-ab375ce4 | Expected native red: pending close rejected and peer/provider failed | evidence/repair/repair-red-ab375ce4/ |
| ret2-red | Expected diagnostic red: full-image traversal at every live commit | evidence/repair/ret2-red.log |
| repair-green-80e3653c | Harness variable reference failure; preserved | evidence/repair/repair-green-80e3653c/ |
| repair-green-eb279d1d | Passed initial whole/sink cleanup gate | evidence/repair/repair-green-eb279d1d/ |
| repair-green-235013f4 | Passed final whole/helper/sink and cleanup gate | evidence/repair/repair-green-235013f4/ |
| browser-regressions-attempt1 | Launcher used project root rather than browser package; no tests ran | evidence/repair/browser-regressions-attempt1.log |
| native-affected-attempt1 | New test used unwrap_err on a non-Debug success type; fixture corrected | evidence/repair/native-affected-attempt1.log |
| mock-sandbox-attempt | Restricted-sandbox native SIGSEGV, exit101 | evidence/repair/mock-sandbox-attempt.log |
| mock-approved-loopback | Same test target passed3 tests with scoped loopback permission; original v1 assertion is not retroactively reclassified | evidence/repair/mock-approved-loopback.log |
| build-final-launch | Shared cache after compiling another manifest produced incompatible serde_json artifact types; source was unchanged, targeted cache invalidation and rebuild passed | evidence/repair/build-final-launch.log and evidence/grouped/build/ |
| retention-931c9a32 | Passed expanded whole/sink, survivor cleaner and denied-write successor; superseded by added helper captures | evidence/retention/retention-931c9a32/ |
| retention-93677c24 | Final expanded gate passed with whole/helper/sink raw evidence | evidence/retention/retention-93677c24/ |
| retention-measure-d9e7f97c | Fresh paired workload passed; all64 index samples retained | evidence/retention/retention-measure-d9e7f97c/ |

The fresh restricted-sandbox mock failure was a SIGSEGV, not the historically reported v1 cluster-count assertion. The permission-sensitive comparison is recorded, but the unavailable original assertion output prevents an exact original root-cause claim.
