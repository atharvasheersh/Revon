# Revon — Benchmark Results After Incremental put()/delete()

Raw numbers, no interpretation beyond what the measurements support.

Reproduce with `python incremental_benchmark.py`.

Configuration: `branching_factor=8`, `tree_depth=4` (unchanged — `_route()`,
`_node_hash()`, and `_canonical_bytes()` were not modified, so these numbers are
directly comparable to the previously reported ones).

Machine: Linux 7.1.2-arch3-1, CPython 3.14. Times are medians over 5 repeats
(headline) / 3 repeats (per-scale). Single run, one machine — treat the ratios
as order-of-magnitude, not as three-significant-figure claims.

---

## Headline result 1 — 3-key change at 100,000 rows

This was the original acceptance target for the incremental-update work.

| Measure | Full rebuild (old `commit()`) | Incremental (`put()`) |
|---|---:|---:|
| New nodes created | 13 | **15** |
| Commit time (ms) | 742.926 | **0.702** |
| Speedup | — | **~1058x** |

Full tree size at 100,000 rows: **4,681 nodes**. The incremental path created
15 nodes, i.e. `3 x (tree_depth + 1) = 15` — exactly the budget, and 0.3% of the
tree. It did not touch the other 4,666 nodes.

Note on 13 vs 15: the full rebuild applies all three changes in one pass, so the
three routed paths share some ancestor internal nodes and it produces 13. The
incremental path applies three separate `put()` calls, each its own version, so
it materializes two extra intermediate root nodes. 15 is the correct number for
three sequential single-key commits and is at (not over) the stated budget.

The old path's ~743 ms is not a rebuild of 13 nodes' worth of work — it is
re-hashing and re-interning all 4,681 nodes plus re-routing all 100,000 keys.
That is the cost the incremental path removes.

## Headline result 2 — commit time by scale, before vs after

5 versions, 10 mutations per version, from `benchmarks.py`'s workload.

| Rows | Before (full rebuild, ms) | After (incremental, ms) | Speedup |
|---:|---:|---:|---:|
| 1,000 | 17.026 | **0.758** | 22.5x |
| 10,000 | 85.168 | **0.832** | 102.4x |
| 100,000 | 652.417 | **1.367** | 477.4x |

The previously reported figure was 307 ms at 100k rows; this run measured the
old path at 652 ms on this machine. The old-path absolute number is therefore
machine-dependent and should not be quoted across reports — the before/after
pair measured in the *same* run is the defensible comparison.

The shape is the point: the old path is O(rows) per commit and its cost climbs
roughly linearly with table size (17 -> 85 -> 652 ms). The new path is O(changes
x tree_depth) and stays roughly flat (0.76 -> 0.83 -> 1.37 ms) across a 100x
increase in table size. It does not grow with the size of the table.

## Sanity check 3 — hot-key diff cost (expected: flat)

Same 5 keys touched on every commit, diffed from v1 out to 100 commits away.
10,000 base rows.

| Commit distance | Changed keys | Node pairs compared | Subtrees skipped |
|---:|---:|---:|---:|
| 1 | 5 | 117 | 97 |
| 10 | 5 | 117 | 97 |
| 50 | 5 | 117 | 97 |
| 100 | 5 | 117 | 97 |

Flat, as expected and unchanged. Diff cost is a function of the *final tree
content*, not of how many commits separate the two roots — rewriting the same 5
keys 100 times leaves the same 5 divergent paths as rewriting them once.

## Sanity check 4 — spread-key diff cost (expected: grows)

5 brand-new, never-repeated keys per commit. Same 10,000 base rows.

| Commit distance | Changed keys | Node pairs compared | Subtrees skipped |
|---:|---:|---:|---:|
| 1 | 5 | 118 | 98 |
| 10 | 50 | 678 | 542 |
| 50 | 250 | 2,002 | 1,494 |
| 100 | 500 | 2,854 | 2,007 |

Grows with the number of distinct changed keys, as before. Growth is sublinear
in changed keys (100x the keys costs ~24x the node comparisons) because
divergent paths increasingly share ancestor internal nodes as the changed set
gets denser. Unchanged by this work, as expected — `diff()` was not modified.

---

## What this data does NOT yet decide

The hot-key/spread-key split above is the input to the deferred diff fast-path
question. **No fast-path, hot/cold routing, or `smart_diff` design has been
started**, per the scope decision for this session. That decision gets made from
this data in the next planning session — see `PLANS.md`.
