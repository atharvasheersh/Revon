# Commit note: Self-checking CLI and incremental brief

- Date: 2026-08-21
- Commit: `ef6ecaa`
- Author: atharvasheersh / Revon team
- Scope: core, evaluation, and docs

## Objective

Provide a small command-line demonstration that independently checks the core
incremental claims, plus a one-page PDF suitable for sharing with a partner or
reviewer.

## Changes

- Added `examples/revon_cli_demo.py` with deterministic mixed updates.
- Verified that the incremental root equals a clean canonical rebuild.
- Verified exact checkout of both versions.
- Verified that Log, Merkle, and Hybrid modes return identical structured diffs.
- Added CLI controls for rows, updates, Hybrid threshold, and change display.
- Added one automated test for the complete CLI verification path.
- Created and visually inspected the one-page incremental-core PDF.

## Verification

```text
python -m unittest discover -s tests -v
25 tests passed

python -m examples.revon_cli_demo --show-changes
PASS: 1,000 rows, 5 changes, 19 new nodes, 98.64% exact sharing,
incremental root equals rebuild, all diff modes agree, both checkouts agree.

python -m examples.revon_cli_demo --hybrid-threshold 2
PASS: Hybrid selected Merkle and compared 87 node pairs.

PDF validation
1 page; required CLI and verified metrics present; final PNG inspected with no
clipping, overlap, missing text, or unreadable elements.
```

## Design decisions

- The demo performs its own assertions and exits with an error if a claim fails.
- Timings are printed for observation but explicitly excluded from paper claims.
- The PDF reports deterministic structural results from the verified default run.

## Known limitations

- Runtime timings vary by machine and are not research benchmark results.
- The PDF describes the in-memory core; it does not claim persistence or Dolt
  evaluation has been completed.

## Next action

Implement persistence, then produce the controlled benchmark data pipeline.
