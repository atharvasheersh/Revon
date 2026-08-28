# Final Chronos platform architecture

Date: 2026-08-23

Chronos is a content-addressed, versioned data store for structured state. The
final platform keeps the fixed-depth Merkle search trie and adds a durable
SQLite object store, operation changesets, adaptive Chronos-H diff selection, a
dependency-free local HTTP API, and a final React/Vinext frontend.

## Runtime layers

1. `frontend/` provides repository creation, CSV/JSON import, atomic commits,
   history, checkout, comparison modes, storage/work metrics, and integrity
   status.
2. `chronos_api/` validates HTTP inputs and maps requests to isolated
   repositories under the configured repository root.
3. `versioned_db.py` implements the fixed-depth Merkle hash trie, incremental
   path copying, immutable changesets/commits, checkout, Merkle diff, Log diff,
   and Chronos-H selection.
4. `sqlite_store.py` persists nodes, changesets, and commits by hash; version
   mappings, commit statistics, and `HEAD` are updated in the same transaction.
5. `experiments/` runs the reproducible Snapshot, Log-only, forced-Merkle,
   Chronos-H, and optional Dolt evaluation.

## Incremental commit invariant

For a mutation batch, SHA-256 key routes identify the affected trie paths.
Chronos reconstructs those paths from leaf to root and reuses every unchanged
sibling by hash. It then creates a content-addressed changeset and commit. New
objects, version mapping, statistics, and `HEAD` are persisted atomically.

The default trie uses branching factor 8 and depth 4. The paper-profile
Chronos-H threshold selects Log diff at or below 4,096 intervening operations
and Merkle diff above it. This is a frozen calibration boundary for the audited
machine, not a universal crossover. Forced modes exist for the paper's ablation
study, and all modes must produce the same structured result.

## Deployment boundary

The final frontend has a private hosted preview, but the complete interactive
demo remains local because the Python API deliberately binds to loopback and
does not yet provide authentication, TLS, rate limiting, or multi-host locking.
The correct final demonstration is two local processes: `python -m chronos_api`
and `npm run dev` from `frontend/`.

The visual companion is `docs/architecture/Chronos_System_Architecture.pdf`.
