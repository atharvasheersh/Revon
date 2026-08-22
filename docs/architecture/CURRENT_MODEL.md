# Chronos-H current model

## One-sentence definition

Chronos-H is a content-addressed versioned key-value store whose state is held
in a persistent fixed-depth Merkle hash trie and whose version diff adaptively
uses either recorded operations or hash-pruned tree comparison.

## Incremental commit workflow

```text
Batch: put A, put B, delete C
             |
             v
      hash each changed key
             |
             v
 group changes by shared trie prefixes
             |
             v
 rewrite each affected leaf once
             |
             v
 rewrite the union of affected paths
             |
             v
      create one new root hash
             |
             v
 hash changeset + parent + root + metadata
             |
             v
      create one commit identity
```

Unchanged child hashes are copied into the new internal nodes. Their subtrees
are neither rebuilt nor re-hashed. With one changed key and depth `d`, at most
approximately `d + 1` new trie nodes are required. Multiple changes sharing a
prefix also share the rewritten ancestors.

## Fixed-trie configuration

For branching factor `b`, depth `d`, and `N` uniformly hash-routed keys, the
expected leaf occupancy is approximately:

```text
N / (b ^ d)
```

The current `b=8`, `d=4` configuration provides 4,096 possible leaf buckets,
or roughly 24 records per leaf at 100,000 records. The final paper must report
a parameter sweep rather than asserting that this choice is universally best.

## Addressed objects

```text
commit hash
  -> root trie hash
  -> parent commit hash
  -> changeset hash
  -> message and timestamp

root trie hash
  -> internal child hashes
  -> ...
  -> leaf containing canonical key/value entries
```

Sequential versions (`v1`, `v2`, ...) are display aliases. Commit hashes and
root hashes are the content-addressed identities.

## Diff modes

- `log`: aggregate changesets along an ancestor path.
- `merkle`: recursively compare roots and skip equal subtree hashes.
- `hybrid`: use the log while the ancestor operation count is at or below a
  configurable threshold; otherwise use Merkle comparison.

The final threshold must be selected using calibration workloads. Paper
results must then be measured on separate workloads to avoid evaluation bias.

## Measured work

The model exposes:

- changed keys per commit;
- new trie nodes and canonical trie bytes written;
- exact reachable-node overlap between two roots;
- Merkle node pairs compared and equal subtrees skipped;
- leaf entries examined;
- log operations examined; and
- the strategy selected by Chronos-H.

Exact structural sharing traverses both roots and is diagnostic only. It is not
included inside timed incremental commits.

## Persistence boundary

The deterministic model can run directly in memory for algorithm experiments.
`SQLiteChronosRepository` persists the same nodes, changesets, commits, metrics,
versions, and `HEAD` reference without changing trie or diff semantics. Each
version is one SQLite transaction, and reopening verifies canonical payloads,
content hashes, object references, version continuity, and the parent chain.

Repository management, the backend API, the final benchmark data pipeline, and
the frontend remain separate layers.
