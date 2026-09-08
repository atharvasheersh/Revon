# Revon — Roadmap Beyond This Review

## Already deferred
- Branching (named pointer to a version) — near-free given the architecture, low risk
- Three-way merge with conflict detection — explicitly hard, open research territory
- Durable on-disk storage, WAL, buffer pool, transactions
- Rolling-hash chunk boundaries (replacing the fixed branching_factor=8/depth=4 tree)
- Evaluation on real-world (non-synthetic) datasets

## Candidate research directions for Review 3+ ("what Dolt doesn't do")
Ranked by how defensible the novelty claim is, with honest risk labels. Do not attempt more
than one of these without checking in first — depth on one beats breadth across three.

### 1. Near-duplicate node compression (similarity-based delta compression)
RISK: Medium. CONFIDENCE: High — well-grounded in real prior art, clearly not something
Dolt does.
Dolt's Prolly Trees only deduplicate BYTE-IDENTICAL chunks — two nodes that differ by even
one character get zero sharing benefit, full duplication. Idea: use a similarity-hashing
scheme (e.g. SimHash or MinHash) over node content to detect near-duplicate nodes across
versions, and delta-encode the difference instead of storing a full new copy. This is the
same family of technique used in rsync, LBFS, and dedup storage systems (TAPER, REBL) —
real, citable prior art — but applied to a content-addressed version tree specifically,
which as far as we've found, Dolt's public architecture does not do.
Benchmark to run: construct near-duplicate states (e.g. one field changed in many similar
rows) and measure storage with vs without similarity-based delta encoding.

### 2. Verifiable diff proofs (succinct proof a diff is correct, without full data access)
RISK: Medium. CONFIDENCE: High — real cryptographic technique, clean story.
Right now, verifying a diff between two versions requires having both full trees. Merkle
trees support succinct inclusion proofs (used in blockchains) — the same idea can produce
a compact proof that "these specific keys changed from X to Y between root A and root B"
that a third party can verify without holding the full dataset. Ties directly into the
tamper-evidence claim already in our report. Dolt does not publish or support verifiable
diff proofs.
Benchmark to run: proof size vs dataset size (should stay small/logarithmic, not grow with
dataset size).

### 3. Self-tuning adaptive diff strategy (extends Part 3 from this review)
RISK: Low. CONFIDENCE: High — direct extension of already-working infrastructure.
The smart_diff threshold (currently a hardcoded constant) could instead be learned per-table
from observed workload: track actual hit/miss cost of the log-based fast path vs the tree
fallback, and adjust the threshold automatically. Lower novelty ceiling than #1/#2 but very
low implementation risk since the plumbing already exists after this review.

### 4. Provenance-linked tamper-evident commits
RISK: Low. CONFIDENCE: Medium — closes a known gap, but Git already does something similar
for commit messages, so this is "catching up," not new ground.
Currently the attached SQL/audit metadata is NOT hashed into the commit object — someone
could edit it without invalidating anything. Fix: hash (tree_hash, message, parent) together
into the commit's own identity, same as Git's commit object model. Good for closing a
question we already flagged as a real gap, lower priority as a "beyond Dolt" claim.

### 5. Semantic/field-aware merge (stretch, do not attempt before Review 3 is secured)
RISK: High. CONFIDENCE: Low-Medium — genuinely open research territory (CRDT-adjacent).
Instead of flagging every same-key conflict for manual resolution (Dolt's approach), define
typed reducers per column (e.g. numeric counters auto-merge via sum/max instead of
conflicting). Real research value if it works, real risk of scope blowup if attempted
casually. Only pursue after branching + basic merge detection already work.

## Rule for this file
Before implementing anything from the "candidate research directions" section, write a
one-paragraph feasibility check and a benchmark plan FIRST, same discipline as the rest
of this project. Do not implement research-flavored features without a benchmark that can
prove or disprove the claim — an unmeasured "novel" feature is worth less than a measured
"known" one.
