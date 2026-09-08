# Commit note: Incremental Revon-H core

- Date: 2026-08-21
- Commit: `ef6ecaa`
- Author: atharvasheersh / Revon team
- Scope: core and evaluation

## Objective

Replace full-tree rebuilds on ordinary updates with atomic incremental Merkle
trie commits, and establish the Log, Merkle, and Hybrid diff modes required by
the final research evaluation.

## Changes

- Added copy-on-write batch updates that rebuild only unique affected paths.
- Added one-key `get`, `put`, and `delete` operations over immutable roots.
- Added content-addressed changesets and commit objects with hash parent links.
- Added structured added/modified/deleted diff entries.
- Added forced Log, forced Merkle, and adaptive Revon-H diff modes.
- Added stable instrumentation for nodes created, trie bytes written, nodes
  compared, leaf entries examined, log operations examined, and chosen mode.
- Added exact offline structural-sharing measurement between two roots.
- Changed the benchmark and CSV workflow to use atomic incremental batches.
- Added a HEAD-only write invariant until explicit branches are implemented.

## Verification

```text
python -m unittest discover -v
25 tests passed

python demo.py
3 changed keys created 12 new nodes at depth 4; 99.2% of v2's reachable
nodes were shared with v1; the hybrid selector examined 3 log operations.

python benchmarks.py --sizes 1000,10000,100000 --versions 5 --changes 10 --diff-repeats 3
All three models returned the same 40 changed keys at every dataset size.
At 100,000 rows, the observed median Revon-H incremental commit was 0.517 ms
on this development run. This is a smoke result, not a paper result.
```

## Design decisions

- The primary state index remains the fixed-depth Merkle hash trie.
- A user transaction is one batch commit, not one commit per changed key.
- Trie roots remain compatible with the original prototype's canonical hashes.
- Commits and changesets use separate versioned hash domains.
- Sequential version numbers are UI aliases; commit hashes are identities.
- Revon-M is a forced mode of Revon-H, not a separate product.
- The hybrid threshold is configurable and must be calibrated by benchmark.
- Expensive exact sharing analysis is deliberately outside the timed write path.

## Known limitations

- Stores are still in memory; SQLite persistence is the next backend layer.
- History is linear and writes must target HEAD; branches and merging are out of
  the current implementation scope.
- Values are stored inline in leaves rather than as separate addressed blobs.
- The default hybrid threshold of 128 operations is provisional, not a final
  experimentally selected value.
- Benchmark numbers above are only engineering smoke tests. Final results need
  warmups, repeated trials, raw CSV output, hardware metadata, and Dolt.

## Next action

Add durable storage and a reproducible experiment harness that calibrates the
hybrid crossover without using the final evaluation workloads.
