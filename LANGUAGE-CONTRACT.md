# Language tranche contract (frozen before implementation)

F1 uses `contains`, `startsWith`, `endsWith` in TypeScript and wire JSON,
with `field` (admitted string leaf including nested path) and `value` (bounded
UTF-8 literal). Matching is case-sensitive and accent-sensitive. No Unicode
normalization or case folding occurs. Empty needle matches every present string;
missing/null never match. Existing `not` remains Boolean negation. Unsupported
mode/case/accent options are rejected as unknown members. No regex syntax.
Filter dependencies do not expand projection. Wire capability `text_predicates_v1`
is required only for queries containing these operators; old peers retain raw
and prior grouped forms. Replacements reject before disturbing the old query.

F2 planned contract: explicit `global: true` plus aggregates (no select/groupBy),
HAVING uses bounded predicate objects with result paths/aliases only; global
count/countDistinct/sum are zero on empty and avg/min/max null. Global identity
is separate `global1:` domain, stable by topic/schema independently of values.
HAVING applies before rank/window and totalRows. Capability `global_having_v1`.
Exact aggregate comparison uses existing numerical domains with aggregate-size
bounds (never source numeric narrowing). This section is a frozen target and
must not be represented as implemented until runtime, types, wire and tests pass.

## F2 implementation contract details

`global:true` is required (false/null rejected); global/groupBy/select are mutually
exclusive. Grouped forms retain nonempty keys. Optional `having` uses existing
bounded predicates and `field` references grouped leaves or aggregate aliases.
Exact count/sum/avg operands use aggregate output brands with aggregateCount,
aggregateInteger and aggregateDecimal constructors. Missing/null operands remain
state predicates, and numeric aggregate aliases cannot use text predicates.
Aggregate comparison bounds match result validation: u64 counts, signed256 sums,
18-place averages, 128-place decimal sums, finite binary64. Both +0/-0 compare as
canonical zero. HAVING is compiled once, applied only to touched finalized groups,
before ranked membership and pagination. Filtered-empty globals retain a row.

Global identity is `global1:` plus UTF-8 hex of `[1,topic,fingerprint]`; raw and
grouped domains retain their old identities. Global result kind is `global_v1`,
shape descriptor `[2,topic,fingerprint,null,sortedAggregateDescriptors]`. Grouped
HAVING retains grouped_v1 and version1 shape descriptor (HAVING changes admission,
not row shape). `global_having_v1` capability gates either extension. Every complete
replacement validates before prior acquisition is retired. Min/max/avg global
result types include null regardless of source requiredness.
