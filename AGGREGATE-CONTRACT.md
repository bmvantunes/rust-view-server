# Grouped aggregates v1 — implementation contract (predeclared)

This document declares the implementation target, not a passing qualification.
Source schemas remain proto-derived. Raw contracts and identity bytes are unchanged.
Effective generated logical schema IDs remain limited to 61 characters at runtime.

## Rust / TypeScript / MessagePack result table

| Function | Input domain | Rust result | TS result | Wire |
|---|---|---|---|---|
| count | no field | checked u64 | AggregateCount | canonical nonnegative integer string |
| countDistinct | string, boolean, number, int64, uint64, decimal | checked u64 | AggregateCount | canonical nonnegative integer string |
| sum | int64, uint64 | checked signed 256-bit integer | AggregateInteger | canonical integer string |
| sum | decimal | checked base-10 coefficient, scale 128 | AggregateDecimal | canonical decimal string |
| sum | number | correctly rounded binary64 | number | finite binary64 |
| avg | int64, uint64, decimal | decimal rounded to 18 fractional places, ties to even | AggregateDecimal (nullable if input optional/nullable) | canonical decimal string or null |
| avg | number | correctly rounded binary64 | number (nullable if input optional/nullable) | finite binary64 or null |
| min, max | all six scalar domains | source scalar | source scalar (nullable if input optional/nullable) | original representation or null |

Count counts matching source rows. Distinct includes missing and null as separate
values from empty string, false and zero. Sum/average/extrema skip missing/null.
Empty-contributor sum is zero; average/extrema are null. Empty source groups disappear.
All aliases are required. Group keys preserve source optionality and nullability.

Integer sums are checked against [-2^255,2^255-1]. Decimal accumulation uses integer
units of 10^-128, bounded to 512 decimal digits (absolute coefficient). Decimal sum
is exact; exact-domain average divides that unrounded accumulator then rounds once
to 18 fractional places, ties to even, strips trailing zeros and normalizes zero.
Binary64 inputs represent their actual binary values. Accumulation uses integer
units of 2^-1074 with at most 2200 bits. Final sum/average rounds the exact rational
to nearest binary64, ties to even; overflow fails the query. Retractions are exact,
and mutation order/rebuild does not change final values. No NaN/Infinity is emitted.

## Bounds and failure

1–8 unique group fields; 1–16 aggregate aliases; at most 8 unique order terms.
Aliases use existing names, exclude rowId and group fields. Sort terms address
only group fields or declared aliases. Source where precedes grouping; pagination
follows ranked grouping; totalRows counts groups. Group ID breaks all ties.
Maximum 65,536 groups and 262,144 retained distinct/extremum entries per shape.
A complete group ID must fit the existing 512-byte key bound. Result row limit and
1 MiB owner output limit remain. Checked resource/numeric failures make that query
unavailable; canonical committed state and other query shapes continue. Failed
admission preserves the prior acquisition. No partial cut or truncated result.

## Identity and protocol

Group IDs use a separate gid1 domain: lowercase hex of canonical UTF-8 JSON
[1,topic,sourceFingerprint,[[fieldName,scalarKind,state,value],...]]. State is 0
for missing, 1 for null, 2 for present; missing/null value is null. Present number
values use their canonical IEEE754 bits as 16 lowercase hex characters; other
values use source JSON representation. Group field order is significant. Strings
are not Unicode-normalized. IDs exclude membership, aggregate values, query sort,
filters, viewport and process incarnation. Recreating a group reproduces its ID.
Unmounted React rows have no state preservation guarantee.

Grouped results require negotiated grouped_aggregates_v1 on v15 MessagePack.
They carry result_kind=grouped_v1 and result_shape equal to canonical JSON
[1,topic,sourceFingerprint,groupBy,[[alias,aggFunc,fieldOrNull],...]] with aliases
sorted ASCII. Worker derives and verifies this descriptor from the admitted query,
validates complete rows, and verifies IDs separately from rid2. Raw frames stay
unchanged. Existing positional atomic row deltas and delivery lifetimes remain.

## Incremental costs

Admission scans the relation once. Each source replacement retracts old and adds
new contributions for each admitted shape on that topic. O(A log D + log G) per
affected group plus bounded integer arithmetic, where A <= 16, D retained values,
G groups. Each cut finalizes only touched groups. Shared shapes reuse state across
windows. Ranked windows cost O(log G + W); wire window differencing retains its
existing bounded cost. State O(G*A + retained distinct/extremum entries). Fanout
across different admitted shapes is unavoidable. No query state is durable.

## Ordering, quotas and qualification notes

Min/max admit string (UTF-8 lexical), boolean (false < true), finite number
(numeric), int64/uint64 (exact numeric), and decimal (exact numeric). CountDistinct
admits all six, using canonical scalar equality; source normalization identifies
-0 and +0. Missing/null remain separate distinct states, and are skipped only by
sum/average/extrema. Group sorting places missing before null before values in
ascending order and reverses that order for descending; group-ID tie breaking is
always ascending. No Unicode normalization is performed.

Quotas apply per shared shape. Different shapes multiply retained state up to the
existing admitted-shape/subscription bounds. A transient intermediate accumulator
or state insertion that exceeds a bound fails the affected shape even if a later
operation in that batch could reduce it; no partial result is published. Retractions
run before additions. Failed shapes remain unavailable until closed/reacquired;
source commits and healthy shapes continue. Final close releases all retained
shape state and therefore costs O(G + retained entries).

The pinned serde_json dependency now enables its existing float_roundtrip feature.
This fixes JSON decode/recovery rounding of finite binary64 values; dependency
versions, lockfiles, source field definitions, fingerprints, canonical format and
raw identity encoding are unchanged. Source binary64 values are not exact original
decimal literals. Qualification is recorded separately in the current handoff.
