# Fixed-Fanout Trie vs Content-Defined Chunking (Dolt's approach)

Reproduce with `python compare_engines.py`. Prolly target chunk size 32.

Both engines are content-addressed, both share unchanged subtrees, both diff by
skipping matching hashes. They differ in exactly one decision: **where a node
ends.** Everything below isolates that decision.

| | `VersionedDatabase` (trie) | `ProllyStore` (Dolt-style) |
|---|---|---|
| Boundary rule | hash the key, route to a fixed slot | hash the item, cut where it hits a target |
| Shape | fixed depth 4, max `8^4 = 4096` leaves | depth grows with `n`, chunk size stays ~32 |
| Key order | destroyed | preserved |
| Range scans | impossible | native |

---

## 1. Cost of changing one key, as the table grows

| Rows | trie keys/leaf | trie bytes/put | trie depth | prolly keys/leaf | prolly bytes/put | prolly depth |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 1.1 | 2,075 | 5 | 32.3 | 3,542 | 3 |
| 10,000 | 2.7 | 2,513 | 5 | 30.6 | 4,676 | 3 |
| 100,000 | 24.4 | 3,103 | 5 | 30.8 | 8,050 | 4 |
| 400,000 | **97.7** | 4,661 | 5 | **31.6** | 11,983 | 4 |

The chunking claim holds exactly as predicted: prolly leaf occupancy is flat at
~31 entries across a 400x range, while the trie's grows linearly once it hits
its 4,096-leaf ceiling (1.1 -> 97.7).

**But the bytes-per-write conclusion is the opposite of what was predicted, at
these scales.** The trie writes *fewer* bytes per single-key update at every
size tested (4,661 vs 11,983 at 400k). Two reasons:

- The trie's depth is fixed at 5 nodes; prolly's grew to 4 levels and its
  internal nodes are large (~32 children x a 12-char key + a 64-char hex hash).
- Storing hashes as 64-char hex rather than 20 raw bytes inflates every
  internal node by ~3x. Dolt stores raw bytes.

Extrapolating the two curves: the trie grows linearly (`~n/4096` entries per
leaf) and prolly grows logarithmically, so the crossover is around **1-2M
rows**. Below that the trie is genuinely cheaper per write; above it the trie
degrades without bound. The earlier claim that the trie's fat leaves were an
immediate flaw was wrong — it is a flaw that arrives at ~1M rows.

## 2. Bulk append: 200 consecutive new keys onto a 100,000-row table

| Engine | New nodes | Time |
|---|---:|---:|
| trie | 1,000 | 21.1 ms |
| prolly | 800 | 2,821.9 ms |

Prolly touches fewer nodes (adjacent keys land in adjacent chunks; the trie
scatters 200 adjacent keys across 195 different leaves). But it is **134x
slower per write**, which is an implementation gap, not an architectural one —
see the limitation below.

## 3. Ordered range scan, 1,000 keys out of 100,000

| Engine | Time | Method |
|---|---:|---|
| trie | 35.15 ms | full materialize + sort (no alternative) |
| prolly | **0.23 ms** | ordered walk, subtrees pruned by key range |

**152x**, and it is a capability difference rather than a constant factor: the
trie hashes keys into random slots, so ordered access is impossible by
construction. Every `WHERE id BETWEEN`, `ORDER BY`, and index scan in a real
SQL workload is this shape.

## 4. Diff after 5 scattered edits on 100,000 rows

| Engine | Time | Keys | Diff statistics |
|---|---:|---:|---|
| trie | 0.22 ms | 5 | 121 node pairs compared, 101 subtrees skipped |
| prolly | 0.46 ms | 5 | 14 node pairs compared, 274 subtrees skipped |

Effectively a tie, as expected — both prune by hash equality. Prolly compares
far fewer node pairs (14 vs 121) because its wider nodes mean fewer levels to
descend; the wall-clock difference is Python overhead on larger nodes, not
algorithmic.

---

## Known limitation in this implementation

`ProllyStore.put()` and `.delete()` produce **exactly** the root hash a full
rebuild produces — verified by property tests over random mutations, and by a
test that inserts 300 keys one at a time in random order and lands on the same
hash as a single bulk commit.

The leaf-level work is local, but the internal levels are currently rebuilt
from the full ordered leaf list, making a write **O(leaves)** instead of the
**O(depth)** a real Prolly cursor achieves. That is the entire reason for the
134x gap in section 2.

Closing it requires a cursor that splices the affected leaf and walks the
ascent locally, including the awkward case where a merge-forward crosses a
parent boundary (the successor leaf lives under a different parent, so it must
be removed from that parent during the ascent). This is the single highest-value
next task on this engine, and it is a speed fix with an existing correctness
oracle already in place to check it against.

## What actually transferred

Verified properties the trie does not have:

- **History independence** — the same key set yields the same root hash
  regardless of insertion order, whether bulk-loaded or inserted one key at a
  time (`test_prolly_db.py`).
- **Scale-stable chunks** — ~31 entries per leaf from 1k to 400k rows.
- **Ordered access** — `range_scan()` and `get()` by key order.
- **Depth adapts** — 3 levels at 1k rows, 4 at 100k, instead of a fixed 4.
