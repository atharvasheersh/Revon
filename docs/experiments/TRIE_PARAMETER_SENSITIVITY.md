# Fixed-depth trie parameter sensitivity

Date: 2026-08-24

Evidence bundle: `output/benchmarks/trie-sensitivity-20260824/`

## Question

Does the current `branching_factor=8`, `tree_depth=4` configuration provide a
reasonable balance, or is it universally optimal?

The experiment is an ablation of the Chronos fixed-depth Merkle trie. It does
not compare Chronos with Dolt and does not change the final comparison bundle.

## Controlled design

- Workload: 10,000 initial rows, 10 commits, 100 changes per commit
- Locality: spread
- Payload: 32 bytes
- Seed: 20260824
- Repetitions: 2 warmups and 7 measured trials
- Diff strategy: forced Merkle
- Durability: `SQLiteChronosRepository`
- Correctness: exact initial checkout, final checkout, and changed-key oracle
- Workload identity: one SHA-256 digest reused by all 45 trials
- Reporting: median, p25, and p75; warmups excluded

Run it again with:

```powershell
python -m experiments.trie_sensitivity --output-dir output/benchmarks/trie-sensitivity-20260824 --rows 10000 --commits 10 --changes-per-commit 100 --warmups 2 --trials 7 --seed 20260824
```

## Configuration rationale

The study contains two complementary comparisons:

1. `b=8` with depths 3, 4, and 5 varies leaf occupancy while holding fanout
   constant.
2. `b=4,d=6`, `b=8,d=4`, and `b=16,d=3` each provide 4,096 leaf buckets and
   consume twelve routing bits. This isolates the shape of the tree while
   holding theoretical bucket count constant.

## Validation

- Raw rows: 45 as expected (`5 configurations x 9 repetitions`)
- Successful rows: 45
- Correct rows: 45
- Workload digests: one
- Summary rows: five
- Failed or unavailable rows: zero

## Median results

| Config | Buckets | Expected occupancy | Import ms | Commit ms | Diff ms | Checkout ms | Storage MiB | Node pairs | Leaf entries |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| b4-d6 | 4,096 | 2.441 | 1,502.72 | 130.94 | 37.595 | 9.40 | 4.34 | 3,628 | 5,682 |
| b8-d3 | 512 | 19.531 | 921.99 | 116.91 | 20.152 | 2.76 | 6.88 | 585 | 17,048 |
| **b8-d4** | **4,096** | **2.441** | **1,681.82** | **138.42** | **44.431** | **10.44** | **4.27** | **3,729** | **5,682** |
| b8-d5 | 32,768 | 0.305 | 3,112.58 | 188.99 | 59.224 | 24.76 | 6.18 | 6,089 | 2,426 |
| b16-d3 | 4,096 | 2.441 | 1,828.34 | 148.01 | 40.456 | 9.66 | 8.15 | 3,929 | 5,682 |

## Interpretation

### Latency-optimized configuration

`b8-d3` was fastest on this 10,000-row spread workload. Relative to the current
`b8-d4` default, its median import was 45.2% lower, commit time 15.5% lower,
Merkle diff 54.6% lower, and checkout 73.6% lower. The shallower tree compared
84.3% fewer node pairs.

This speed comes with a clear trade-off: storage was 61.2% higher and the diff
examined three times as many leaf entries because each bucket held more keys.
It is therefore a latency-oriented point, not a universal replacement.

### Current default

`b8-d4` used the least storage of the five configurations (about 4.27 MiB). In
the constant-4,096-bucket comparison, it also created fewer new nodes per
incremental commit than `b4-d6` and used dramatically less storage than
`b16-d3`.

It was not the fastest configuration. The result supports describing `b8-d4`
as a storage-conscious balanced default, not as an optimum.

### Constant-bucket comparison

Compared with `b8-d4`, `b4-d6` was 15.4% faster for Merkle diff and wrote 8.9%
fewer trie bytes per incremental commit, but created 39.7% more new nodes and
used 1.6% more repository storage. `b16-d3` reduced diff latency by 8.9% and
created 21.2% fewer new nodes, but used 91.0% more storage and wrote 19.7% more
trie bytes per commit.

### Over-deep configuration

`b8-d5` reduced examined leaf entries by 57.3%, but it compared 63.3% more node
pairs, used 44.8% more storage, and was slower on every timed operation. At
this scale, the extra internal-node traversal outweighed the smaller buckets.

## Paper-ready conclusion

The sensitivity experiment rejects the claim that one fixed-depth geometry is
universally optimal. A shallower `b8-d3` trie favors latency by accepting
larger leaf buckets and higher storage, while the current `b8-d4` configuration
minimizes storage in the tested set and provides lower bucket occupancy. The
paper should retain `b8-d4` as the evaluated default because it is a defensible
balance, and report `b8-d3` as a latency-oriented alternative. Results are
specific to the controlled 10,000-row spread workload; a larger or skewed
dataset may move the preferred point.
