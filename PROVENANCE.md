# Source provenance and review boundary

This is a new repository import, not invented historical authorship. No Git repository or product history existed at the composed checkout. Neighboring repositories and historical vendor Git caches are unrelated and have not been modified. Local commits use the configured user identity; signing was attempted with the configured GPG key but noninteractive pinentry was unavailable. Local commits are unsigned through a per-command setting; machine signing configuration is unchanged.

Reviewed CP4 candidate tree: `ecb5c393d1618470a759e1907c2c3d3801b05bb3d6099216faa51e1b87e91578`.
Original `functional-roadmap.zip` SHA-256: `686ec5b937c4cea2e729d71d77838d7fcf235b70bd5e4d3f6d7b877a9cfd8ed9`.
All1066 files in the documented complete composition were reverified before importing947 required source, test, contract, notice and browser-runtime files. This is not a sparse overlay import. The119 exclusions are recorded individually.

`provenance/cp4-source-map.json` maps every included relative source path to its original path/hash and lists every intentional CP4 exclusion with its original hash. Binary aliases, duplicate build outputs, operations files and diagnostics remain in the original composition outside Git. Required generated TypeScript, descriptors, catalogs, wire bindings, two browser WASM assets and synthetic durable-format compatibility fixtures are intentionally retained. Do not blanket-ignore generated inputs.

The baseline import commit contains exact selected CP4 bytes. A second commit contains the ten independently reviewed handover files listed in `provenance/handover-source-map.json`: the TypeScript guard/entrypoints, existing React example and local source/launcher scripts. The subsequent repository-usability commit adjusts only documentation, tool/configuration paths and launch/build wrappers. It does not change the Rust product engine, SDK provider, production Worker, dependency locks or schema contracts. New local binaries are builds from current source, not asserted to match the sealed CP4 executable hashes.

Original reviews, captures, archives and executable aliases remain outside Git. `provenance/external-evidence-index.json` is a derived hash-bound locator; it is not a rewritten review or evidence claim. The original archives are not uploaded as Releases or LFS. CP4 acceptance applies to its exact baseline, not automatically to later changes. Repository verification and scoped source review are recorded separately.

Inherited copyright and third-party notices remain. No new project license is selected. This derived README/START-HERE/provenance documentation supersedes stale quickstart directions without rewriting sealed historical evidence. Existing historical reports retain their original scope.

Publication status — 2026-10-06: the user explicitly authorized creation and push to `bmvantunes/rust-view-server` as private, then explicitly authorized changing it to public. Both actions completed. GitHub public visibility and `main` at publication checkpoint `2a7644408d2891cab924df7d11ef3743c3170797` were verified. Repository creation/push authorization is no longer pending. Neither `bmvantunes/shadcn-table` nor `bmvantunes/effect-view-server` was used as a destination.

[REPOSITORY-VERIFICATION.md](REPOSITORY-VERIFICATION.md) and the hash-bound review/evidence records remain unchanged as dated pre-publication evidence. Their statements about pending authorization, absent remotes and unpublished status describe the state before publication; their results and review scope are not extended by publication.

Privacy metadata: inherited historical scripts/docs and retained WASM assets contain local developer filesystem/build paths. These were reviewed as build metadata, not secrets. They are intentionally preserved for exact lineage; this import is not claimed to be scrubbed for public publication. The repository is now publicly visible with that metadata retained. Public visibility is not evidence of a complete public-release or security review; any such assessment must explicitly revisit the retained metadata and its intended release scope.
