F5 selected-field patches v1 — predeclared implementation contract

Optional `selected_field_patches_v1` capability, false unless mutually negotiated.
Existing positional snapshots, inserts, moves, removes, revisions, schema/shape,
incarnation/connection/acquisition/window identities retain their contracts.
A patch operation addresses one current row by key and index. `changes` contains
only selected leaf paths or their ancestor object paths. `set` carries an exact
leaf value (including null/zero/false/empty); `remove` removes a selected leaf or
ancestor object; `object` creates an absent ancestor as present-empty. Omission
means unchanged. Selected enum/domain objects remain scalar leaves.
Parent initialization precedes descendants. Duplicate paths reject. Unselected
paths, rowId changes, parent removal followed by child write, and unknown members
reject. Final full-row validation and full-batch validation precede any commit;
old objects are never mutated. Unchanged subtrees retain identity.
The producer derives patches solely from full projected result rows. It chooses
a patch only if its actual MessagePack operation encoding is at least 16 bytes
and 10 percent smaller than the full-row update. Existing dense snapshot fallback
remains. Full snapshots recover every unavailable/incompatible base; no canonical
or query execution state is changed by this transport optimization.

Nullable relation-parent transitions (LEFT join match/unmatch) deliberately use full-row updates. Selected leaf updates under matched parents remain patchable. No patch attempts to treat a null parent as a present-empty object.
