# Schema expansion v1 — implementation contract

Status: implemented and locally qualified within the finite gates; no independent acceptance claimed. See SCHEMA-EXPANSION-GATES.json and the current handoff.
The accepted grouped v1.2 + retention v1.1 composition is unchanged in sealed inputs.
New semantics require portable schema format/version 3, explicit `view.expanded`
on a root message, a distinct fingerprint, and the `schema_expansion_v1` capability.
Formats 1/2 retain their strict SOURCE-PRESENCE contract and fingerprints.
Canonical format 3 retention policy binding is a separate version domain. There
is no migration, automatic wipe or reinterpretation of old canonical rows.

## Presence table (declared before implementation)

| Source state | Contract | Normalized full/projected row |
|---|---|---|
| Optional singular parent absent | default parent contract | Parent omitted; no descendants synthesized |
| Required singular parent absent | `view.required=true` | Reject |
| Parent present, zero payload bytes | singular message | Parent exists, including an empty selected subtree |
| Plain proto3 scalar omitted, parent present | implicit/defaulted | Scalar default is a value; no claim its tag occurred |
| Plain scalar explicitly carries default | implicit/defaulted | Same value as omitted scalar |
| Explicit optional scalar omitted | `view.optional=true` | Leaf omitted |
| Explicit optional scalar omitted | existing required-source contract | Reject, only when all parents exist |
| Explicit optional scalar present at default | explicit | Default value retained |
| Nullable optional scalar has true null marker only | existing nullable contract | Leaf is null |
| False marker or marker together with value | nullable contract | Reject |
| Logical decimal omitted | explicit, required/optional as declared | Reject/omit; never invent a decimal representation |

Implicit leaves cannot require observed tag presence, be optional or nullable.
Logical decimal string leaves require explicit presence; normalization and exact
arithmetic remain unchanged. Parent null is unsupported. Unknown protobuf fields
in the extended mode follow protobuf skip semantics; singular repeated wire
occurrences merge messages and last scalar occurrence wins. Legacy mode remains
unchanged. Every source event is still a whole-row UPSERT.

## Enum and decimal table

| Case | Contract |
|---|---|
| Enum value | `{domain: fullyQualifiedName, code: signedInt32}` |
| Known labels | Generated constants in exact fully qualified registry |
| Aliases | Same domain/code, same equality/group/distinct identity |
| Unknown open enum code | Preserved; never typed as exhaustively known |
| Implicit enum default | Domain with code zero |
| Comparison, inclusion, sort, grouping, countDistinct | Domain-aware; numeric code order within domain |
| min/max | Supported by code order, retaining domain |
| sum/avg of enum | Rejected in types and native admission |
| Annotated-string decimal | Existing exact canonical string, including nested leaves |
| Company Decimal message | INPUT-PENDING: no definition/import closure supplied |

Only proto3 open enums are added. No closed enum support is claimed. Scalar
paths drive queries; public/canonical objects retain nested shape and only selected
descendants appear in projected results. Missing/null stay separate states.
Grouping includes selected ancestor presence so absent parent and present empty
parent cannot produce an arbitrary representative tree. countDistinct of a leaf
counts missing once, null once and each value once, as before.

Bounds: at most 16 local files, 64 message/enum descriptors, depth 8, 64 scalar
leaves, 64 expanded parent paths, 512 bytes per path, 256 labels per enum, 64KiB
descriptor and row, 4096-byte strings, 512-byte rowId, 16 identity components.
Cycles, maps, repeated fields, general oneofs, missing imports, invalid metadata,
services and oversized graphs are rejected. Nested key paths require explicit,
non-null identity leaves and required ancestors. Compact identities remain key-only.

## Finite qualification matrix

These gates were declared NOT RUN before implementation. Their completed results are in SCHEMA-EXPANSION-GATES.json; the attempt ledger preserves PASS, FAIL and BLOCKED execution separately.

1. Deterministic generation, FQ imports/reuse/nested declarations, flat identity,
   naming and unsupported negatives.
2. Actual hook/helper/sink types: exact nested selection, enum domains, readonly
   rowId, alias prefixes, A1/A2 and unsuppressed negative diagnostics.
3. Raw protobuf source presence/default/merge/null/enum/decimal edges.
4. Two schemas × two Kafka partitions, one service/provider, production Worker,
   both hooks and independent raw/grouped completed-cut oracle; third schema on
   the identical ordinary binary.
5. Retention expiry/count eviction, maintenance cleanup and unchanged source NEXT.
6. SIGKILL/offline updates/tombstones, empty-cwd write-denied recovery, same-page
   reacquisition and later delta.
7. Affected source, codegen, numeric, codec, lifecycle, license, telemetry/progress.
8. Small matched flat/nested work/bytes/resource comparison.

Illustrative fixtures are not real company-schema qualification. Deferred:
contains/startsWith/endsWith, global aggregates, HAVING and gRPC.

## Buf and company input boundary

The user's existing `buf generate` workflow is authoritative for company input;
this slice extends the repository's existing protobufjs build-time generator,
and does not replace Buf or infer a plugin from the CLI name. No Buf plugin or
company-output compatibility is qualified here.

Workspace inspection found no buf.gen.yaml, buf.yaml or buf.lock. Two identical
historical `orders_pb.ts` files explicitly call themselves generated-style Kafka
test fixtures. They import @bufbuild/protobuf/codegenv2; the adjacent dependency
is @bufbuild/protobuf 2.13.0. Their embedded descriptor defines price as double,
not a decimal message. The separately found historical viewserver.v1.DecimalValue
is a query-wire experiment; no supplied field/import binds it to MyShit.price.
No mapping is inferred from either fixture.

Minimal remaining company artifacts: the relevant buf.gen.yaml (including plugin
versions/options), input module/import configuration and the proto definition/import
closure containing MyShit and its referenced decimal type; generated MyShit and
referenced type/import declarations; and any existing converter or comments that
specify numeric scale/rounding where the proto itself does not. Only genuinely
missing numeric semantics remain pending after those artifacts are supplied.
The user need not duplicate protobuf fields in another schema or change producers.

Extended key descriptors currently admit explicit string, bool, double, int64 and
uint64 leaves, with all key fields/ancestors required at source admission. Enum and
logical-decimal key leaves are rejected in this bounded extension. Existing flat
key behavior remains unchanged. Expanded envelope schema IDs and message index zero
are explicitly pinned to `message_name`, the fully qualified descriptor root;
this is not automatic registry discovery or a claim about arbitrary Buf framing.
