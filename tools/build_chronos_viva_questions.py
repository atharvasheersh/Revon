from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Chronos_100_Viva_Cross_Questions.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2F6B9A")
GREEN = colors.HexColor("#4F8A5B")
PALE_BLUE = colors.HexColor("#EAF3F8")
PALE_GREEN = colors.HexColor("#EDF5EE")
INK = colors.HexColor("#17212B")
MUTED = colors.HexColor("#52606D")
RULE = colors.HexColor("#C8D3DC")


SECTIONS = [
    (
        "1. Project Fundamentals",
        [
            ("What is Chronos in one sentence?", "Chronos is a content-addressed versioned store for structured key/value data, using immutable commits and an incrementally updated Merkle hash trie."),
            ("What problem does Chronos solve?", "It preserves exact dataset versions while supporting sparse updates, historical checkout, integrity verification, and efficient comparison without copying every full state."),
            ("Why is Chronos described as Git-inspired?", "It borrows immutable objects, content-derived identities, parent-linked commits, HEAD, history, checkout, and diff; unlike Git, it versions structured records rather than files."),
            ("Why is ordinary file version control insufficient for structured data?", "File-oriented tools do not naturally expose record-level updates, typed change categories, key-based queries, or database-style version comparisons."),
            ("What does content addressing mean?", "An object's identifier is computed from its canonical content. Equal objects have equal hashes, enabling deduplication, structural sharing, and corruption checks."),
            ("What role does a Merkle structure play?", "Parent hashes summarize their descendants, so equal hashes prune unchanged regions and the root commits to the complete logical state."),
            ("What is a version in Chronos?", "A version is a commit object containing a root hash, parent commit, changeset, message, and timestamp; user-friendly aliases such as v1 point to commits."),
            ("What is the main research contribution?", "The contribution is an instrumentable hybrid design combining incremental fixed-trie hashing with adaptive operation-log or Merkle differencing."),
            ("What is Chronos-H?", "Chronos-H is the primary hybrid variant. It selects log aggregation for short or sparse intervals and Merkle comparison once accumulated operations exceed a calibrated boundary."),
            ("Why was Python retained?", "Python enabled a complete, testable prototype within the deadline and made instrumentation simple; runtime asymmetry with Dolt is explicitly treated as a limitation."),
        ],
    ),
    (
        "2. Data Structure and Design Choices",
        [
            ("What data structure is actually implemented?", "The evaluated core is a fixed-depth Merkle hash trie: SHA-256 bits route keys through a fixed number of levels, and leaves retain complete keys and values."),
            ("Why did you not switch to a Go Prolly Tree?", "A late rewrite would risk correctness and reproducibility. The fixed trie provides a controlled research design, while Dolt already supplies the production Prolly Tree comparison."),
            ("Is Chronos identical to the published Merkle Search Tree?", "No. It is Merkle-search-tree-inspired but uses fixed-depth hash routing, not the ordered balanced MST of Auvolat and Taiani; the distinction must be stated clearly."),
            ("What are the default trie parameters?", "The evaluated default uses branching factor b=8 and depth d=4, consuming three routing bits per level."),
            ("Why does b=8, d=4 produce 4,096 buckets?", "The number of possible leaf routes is b^d, so 8^4 equals 4,096; equivalently, twelve hash-routing bits are consumed."),
            ("What happens when two keys share the same routing prefix?", "Both remain as distinct full-key entries in the same leaf bucket. A routing collision affects occupancy and work, not correctness."),
            ("What does the root hash represent?", "It is a compact commitment to the complete trie state. Any changed record propagates new hashes from its leaf to the root."),
            ("Does the same logical state always have the same root?", "Yes, provided serialization and trie parameters are identical. Canonical encoding and deterministic routing make the state root reproducible."),
            ("Does the same state always produce the same commit hash?", "Not necessarily. A commit also includes its parent, changeset, message, and timestamp, so identical roots can belong to different historical commits."),
            ("What is structural sharing?", "A new version reuses unchanged content-addressed nodes from its parent and creates only affected leaves and ancestors, reducing duplicate storage."),
        ],
    ),
    (
        "3. Incremental Commit and Persistence",
        [
            ("What is incremental hashing?", "Chronos recomputes only changed leaf buckets and their ancestor paths rather than rebuilding and rehashing the entire tree for every commit."),
            ("Which nodes change after one key update?", "The affected leaf and one ancestor at each level up to the root change; unrelated subtrees keep their existing hashes and stored objects."),
            ("Why group mutations by shared prefixes?", "It prevents rewriting the same leaf or ancestor repeatedly when several keys in one batch follow overlapping trie paths."),
            ("Why is canonical JSON necessary?", "Hashing requires one stable byte representation. Sorted fields and consistent encoding prevent semantically identical objects from receiving different hashes."),
            ("Why use SHA-256?", "It is widely available, deterministic, and collision resistant enough for prototype integrity and content identity; the design does not depend on secret-key security."),
            ("What is stored by hash?", "Trie nodes, changesets, and commit objects are immutable addressed objects; aliases, HEAD, and operational measurements are stored as repository metadata."),
            ("Why use SQLite?", "SQLite offers zero-configuration durable persistence and transactions, matching a local prototype while keeping experiments reproducible and easy to reopen."),
            ("How is a commit made atomic?", "New objects, changeset, commit metadata, version alias, measurements, and the HEAD update are written inside one SQLite transaction."),
            ("What is HEAD?", "HEAD is the durable named reference to the latest commit. It is metadata, not the identity of the underlying state."),
            ("How does Chronos detect stored corruption?", "When reopening, it recomputes object hashes from stored payloads and checks references; a mismatch causes the repository to be rejected."),
        ],
    ),
    (
        "4. Diff, History, and Checkout",
        [
            ("How does Merkle diff work?", "It compares roots, prunes equal subtree hashes, recursively follows unequal paths, and inspects full leaf entries only below changed regions."),
            ("How does log diff work?", "It walks the ancestor chain and aggregates addressed changesets, preserving the net added, deleted, and updated records between two versions."),
            ("Why combine log and Merkle diff?", "Logs are efficient for short sparse histories, while Merkle pruning avoids replaying long histories when many operations accumulated between endpoints."),
            ("What is the current hybrid threshold?", "The frozen experimental boundary is 4,096 accumulated operations between versions; it is a measured policy for one environment, not a universal constant."),
            ("Is 4,096 included in the log path?", "Yes. Chronos-H chooses log aggregation at or below 4,096 operations and forced-Merkle comparison above it."),
            ("Can Chronos compare versions in reverse order?", "Yes. The reverse operation swaps additions and deletions and reverses old/new values for updates while preserving logical correctness."),
            ("What is Chronos-M?", "Chronos-M is a forced-Merkle ablation that uses the same durable trie as Chronos-H but disables adaptive selection, isolating the selector's effect."),
            ("What happens on a no-op commit?", "The root is reused, an empty addressed changeset is recorded, and a new historical commit may still be created without duplicating trie state."),
            ("How does checkout work?", "Chronos resolves the version to its root and materializes all key/value records reachable from that immutable trie state."),
            ("What is the expected diff complexity?", "It depends on changed paths and bucket occupancy, not only total records; the implementation reports examined node pairs rather than claiming one universal bound."),
        ],
    ),
    (
        "5. Backend, API, and Frontend",
        [
            ("What are the main system layers?", "The platform consists of a metrics-focused frontend, REST repository service, Chronos-H core, and SQLite content-addressed object store."),
            ("Which backend operations are exposed?", "The API supports create/open repository, import dataset, commit batch, history, checkout, version comparison, storage metrics, and diff metrics."),
            ("What is the frontend's purpose?", "It demonstrates the versioning workflow and presents evidence such as latency, storage, history, strategy choice, and comparison results in one workspace."),
            ("Why use a metrics-first interface?", "The project's main claim is experimental, so the interface prioritizes measurable behavior and reproducible comparisons over decorative application features."),
            ("What do the 10, 100, 10k, 100k, and 1m controls mean?", "They are workload-size selectors in the interface; only sizes present in the audited benchmark may be presented as measured research evidence."),
            ("How does the API protect correctness?", "It validates payloads and base versions, rejects duplicate or invalid operations, and returns structured errors without partially committing data."),
            ("Why support CORS and preflight requests?", "They let the separately hosted frontend call the local API safely through standard browser cross-origin controls."),
            ("How are unsafe repository names handled?", "Names are validated so they cannot escape the configured repository root through path traversal or malformed filesystem paths."),
            ("Why not PostgreSQL for this prototype?", "PostgreSQL would help multi-user concurrency and deployment, but SQLite is sufficient for a local atomic store and reduces operational variables in experiments."),
            ("What would the backend need for production use?", "It would need authentication, authorization, concurrency control, schema evolution, branch/merge semantics, remote synchronization, backups, and stronger observability."),
        ],
    ),
    (
        "6. Experimental Design",
        [
            ("Which five variants are compared?", "Snapshot, Log-only, forced-Merkle Chronos-M, adaptive Chronos-H, and Dolt 2.3.1 receive equivalent logical workloads."),
            ("Why include a Snapshot baseline?", "It represents complete state materialization per version, providing a simple reference for storage, import, checkout, and full-scan diff behavior."),
            ("Why include a Log-only baseline?", "It isolates the benefits and costs of storing an initial state plus operations, especially for sparse histories and reconstruction-heavy workloads."),
            ("Why compare with Dolt?", "Dolt is a mature version-controlled SQL database using content-addressed Prolly Trees, making it the most relevant production system-level comparator."),
            ("How is fairness maintained across implementations?", "All adapters receive regenerated workloads with identical logical states, mutation batches, seeds, and correctness oracles, while interface differences are disclosed."),
            ("What workloads are evaluated?", "The paper uses small sparse, medium sparse, medium dense, large sparse, and large hot scenarios up to 100,000 rows."),
            ("How many measured repetitions are used?", "Each final scenario uses seven measured trials after two warmups, and reported medians and quartiles exclude warmups."),
            ("Why use warmups?", "Warmups reduce one-time startup, import, cache, and process initialization effects from contaminating the measured trial summaries."),
            ("Why use fixed random seeds?", "A fixed base seed makes workloads reproducible; SHA-256 workload digests confirm that every adapter receives the intended mutations."),
            ("How is correctness established?", "Every final state and diff is checked against an independent changed-key oracle, with successful execution alone never treated as proof of correctness."),
        ],
    ),
    (
        "7. Metrics, Statistics, and Evidence",
        [
            ("Which metrics are recorded?", "Initial import, incremental commit, diff, checkout, repository storage, peak memory where comparable, work examined, selected strategy, and correctness."),
            ("Why report medians and interquartile ranges?", "Short system timings can be noisy; the median is robust to extreme values, while the 25th-75th percentile range shows dispersion."),
            ("What does nodes or operations examined mean?", "It reports each implementation's natural internal work unit; it is diagnostic and is not normalized as a cross-system equivalent counter."),
            ("How is storage measured?", "Storage is the sum of regular repository-file bytes after the evaluated history, so indexes, metadata, and content-addressed objects contribute."),
            ("Why is there no cross-system memory graph?", "Python tracemalloc and Dolt process memory are not equivalent measurement methods; presenting them together would imply false comparability."),
            ("Were outliers removed?", "No. The audit identified 83 Tukey candidates, retained every observation, and summarized all measured trials with medians and quartiles."),
            ("What does the 333-trial figure mean?", "The audited final paper profile contains 333 successful, correctness-true measurement rows across calibration and evaluation combinations."),
            ("What does the 45-trial sensitivity figure mean?", "Five trie configurations were evaluated with nine runs each, producing 45 correctness-verified sensitivity observations."),
            ("Why separate calibration from evaluation?", "A disjoint calibration workload freezes the hybrid policy before evaluation and reduces the risk of tuning directly to headline results."),
            ("Do seven trials prove statistical significance?", "No. They support descriptive medians and quartiles, but not strong distributional or population claims; more machines and repetitions are future work."),
        ],
    ),
    (
        "8. Results and Interpretation",
        [
            ("What is the main diff result against Dolt?", "Chronos-H's measured CLI-facing median diff latency was 5.8x to 554.2x lower across the five final workloads."),
            ("What is the incremental commit result?", "Chronos-H's incremental commit medians were 2.3x to 37.4x lower than Dolt under the evaluated protocol."),
            ("What is the checkout result?", "Chronos-H's historical checkout medians were 35.8x to 123.4x lower than Dolt in the tested workloads."),
            ("Did Chronos-H always import faster?", "No. It was faster on small sparse, roughly tied around medium dense, and about 2.73x to 2.79x slower at 100,000 rows."),
            ("What storage cost did Chronos-H pay?", "Its final repository footprint ranged from 1.83x to 6.43x Dolt's, reflecting JSON objects, fixed buckets, and no packing, compression, or garbage collection."),
            ("Why was the largest diff ratio so high?", "Sparse histories let the log path touch very little data while the measured Dolt path includes CLI and SQL invocation overhead; it is not a pure algorithm-only speedup."),
            ("What happened in the medium-dense workload?", "Both Chronos-H and Chronos-M selected or used Merkle comparison, and Chronos-H stayed within about 7.3% of the forced-Merkle variant."),
            ("Which strategy did Chronos-H select?", "It selected log for the four sparse or hot workloads and Merkle for the 10,000-operation medium-dense interval."),
            ("Does the result prove 4,096 is optimal?", "No. It is the largest sampled log-favorable calibration point on one machine, not a precisely measured universal crossover."),
            ("What result has the strongest publication value?", "The most defensible result is the measured trade-off: hybrid selection greatly reduces sparse diff work while fixed-trie storage and import costs remain visible."),
        ],
    ),
    (
        "9. Sensitivity Study and Literature Review",
        [
            ("Why run a trie-parameter sensitivity study?", "It prevents presenting b=8, d=4 as universally optimal and shows how depth and branching alter latency, bucket occupancy, node work, and storage."),
            ("Which parameter combinations were tested?", "The study evaluates five controlled branching-factor/depth configurations around the default, using identical workloads and seeds."),
            ("Why retain b=8, d=4 as the default?", "It used the least storage in the tested set, about 4.27 MiB, while providing a balanced rather than latency-only operating point."),
            ("What advantage did b=8, d=3 show?", "It had the lowest median diff latency, 20.15 ms versus 44.43 ms for b=8, d=4, and compared 84.3% fewer node pairs."),
            ("What was the cost of b=8, d=3?", "It consumed 61.2% more storage and examined about three times as many leaf entries because its shallower buckets were larger."),
            ("What did the over-deep configuration show?", "The b=8, d=5 design was slower for every timed operation and used 44.8% more storage, showing that additional depth is not automatically beneficial."),
            ("What is the sensitivity-study conclusion?", "Trie geometry must be chosen by workload objective: shallow routing may favor latency, while deeper routing can reduce occupancy but increase internal-node work and storage."),
            ("What does the literature review cover?", "It reviews content addressing and persistent structures, structured dataset versioning, and the design gap between research prototypes and Dolt's production Prolly Trees."),
            ("Are all 15 bibliography entries research papers?", "No. Eleven are scholarly papers or preprints; Noms documentation, Pro Git, Dolt documentation, and a DoltHub article are primary technical sources."),
            ("What bibliography corrections were found?", "The MST DOI, Silu Huang's name in two entries, Liqi Xu's name, and missing DOIs for dataset versioning, OrpheusDB, and LBFS require correction."),
        ],
    ),
    (
        "10. Difficult Defense Questions, Limitations, and Future Work",
        [
            ("Can you claim Chronos is better than Dolt?", "Only within the declared CLI-facing benchmark for selected operations. Dolt remains far more feature-complete, production-engineered, and storage efficient."),
            ("Is Python Chronos versus Go Dolt an apples-to-apples comparison?", "No. It is a system-level comparison through each tool's public interface; runtime and interface asymmetry are explicit threats to validity."),
            ("What are the largest technical limitations?", "Chronos lacks branches, merges, schema evolution, range indexes, concurrent writers, remotes, packing, compression, and garbage collection."),
            ("Why omit branches and merges from the final prototype?", "The project prioritizes the storage model, durable version history, diff strategy, and reproducible evidence; adding incomplete semantics would dilute the core contribution."),
            ("Was one million rows benchmarked?", "No. The audited paper evidence reaches 100,000 rows. A 1m interface option must not be described as a measured result until that experiment is completed."),
            ("What is the biggest threat to external validity?", "Results come from deterministic synthetic workloads on one Windows machine, so real schemas, skew, platforms, caching, and longer histories may change the outcome."),
            ("What storage improvement should come first?", "Compact binary node encoding and pack files should come first, followed by compression, content-defined value chunking, reachability analysis, and garbage collection."),
            ("What would you do with one additional week?", "Correct the bibliography, rerun on another machine and real dataset, add one-million-row evidence, profile I/O, and prototype packed binary objects without changing semantics."),
            ("What novelty claim is safe to defend?", "Chronos demonstrates a reproducible hybrid log/Merkle policy over an incremental fixed-trie store and quantifies its latency-storage-structure trade-offs against controlled baselines and Dolt."),
            ("What is the final takeaway?", "Incremental hashing avoids full-tree rebuilds, and adaptive differencing can exploit sparse histories; the gain is real in the tested protocol but purchased with storage and scope trade-offs."),
        ],
    ),
]


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    if doc.page > 1:
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.setFillColor(NAVY)
        canvas.drawString(18 * mm, height - 11.2 * mm, "CHRONOS VIVA PREPARATION")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawCentredString(width / 2, 9 * mm, f"Page {doc.page} | 100 concise cross-questions")
    canvas.restoreState()


def make_styles():
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=15,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=17,
            leading=20,
            textColor=NAVY,
            spaceAfter=10,
        ),
        "question": ParagraphStyle(
            "Question",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9.2,
            leading=11.3,
            textColor=NAVY,
            spaceAfter=2,
        ),
        "answer": ParagraphStyle(
            "Answer",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=11.2,
            textColor=INK,
            leftIndent=6 * mm,
            firstLineIndent=-6 * mm,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=INK,
            alignment=TA_LEFT,
        ),
        "contents": ParagraphStyle(
            "Contents",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=INK,
        ),
    }


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    total = sum(len(items) for _, items in SECTIONS)
    assert total == 100, f"Expected 100 questions, found {total}"

    styles = make_styles()
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=15 * mm,
        title="Chronos: 100 Viva and Cross-Questions",
        author="Chronos Project Team",
        subject="Concise oral-defense preparation for the Chronos research project",
    )
    story = []

    story.append(Spacer(1, 30 * mm))
    story.append(Paragraph("Chronos", styles["title"]))
    story.append(Paragraph("100 Viva and Cross-Questions", styles["title"]))
    story.append(Paragraph("Concise 1-2 line answers for the final project defense", styles["subtitle"]))

    note = Table(
        [[Paragraph(
            "<b>Coverage:</b> problem statement, fixed-depth Merkle hash trie, incremental hashing, "
            "SQLite persistence, hybrid diff, API/frontend, experimental design, Dolt comparison, "
            "results, literature review, limitations, and future work.",
            styles["small"],
        )]],
        colWidths=[160 * mm],
    )
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(note)
    story.append(Spacer(1, 9 * mm))

    contents_rows = []
    start = 1
    for title, items in SECTIONS:
        end = start + len(items) - 1
        contents_rows.append([
            Paragraph(title, styles["contents"]),
            Paragraph(f"Questions {start}-{end}", styles["contents"]),
        ])
        start = end + 1
    contents = Table(contents_rows, colWidths=[115 * mm, 45 * mm])
    contents.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -2), 0.35, RULE),
        ("TEXTCOLOR", (1, 0), (1, -1), GREEN),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(contents)
    story.append(Spacer(1, 8 * mm))
    warning = Table(
        [[Paragraph(
            "<b>Defense rule:</b> report measured results as system-level observations, not universal "
            "algorithmic superiority. The final evidence reaches 100,000 rows, and the current "
            "bibliography contains 11 scholarly works plus four primary technical sources.",
            styles["small"],
        )]],
        colWidths=[160 * mm],
    )
    warning.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.8, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(warning)

    number = 1
    for title, items in SECTIONS:
        story.append(PageBreak())
        story.append(Paragraph(title, styles["section"]))
        for question, answer in items:
            block = [
                Paragraph(f"Q{number}. {question}", styles["question"]),
                Paragraph(f"<b>A.</b> {answer}", styles["answer"]),
            ]
            story.append(KeepTogether(block))
            number += 1

    assert number == 101
    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(OUTPUT)


if __name__ == "__main__":
    build()
