from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "architecture"
AUTHOR = "Atharva Sheersh Pandey; Adhyan Jain; Poornima Nedunchezhian"
BUILD_DATE = "9 September 2026"
PAGE_WIDTH, PAGE_HEIGHT = A4
LEFT_MARGIN = 17 * mm
RIGHT_MARGIN = 17 * mm
TOP_MARGIN = 17 * mm
BOTTOM_MARGIN = 17 * mm
CONTENT_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

INK = colors.HexColor("#111827")
MUTED = colors.HexColor("#52606D")
LIGHT = colors.HexColor("#F4F6F8")
LIGHT_BLUE = colors.HexColor("#EAF3F8")
BLUE = colors.HexColor("#2F6B9A")
GRID = colors.HexColor("#D9DEE3")
WHITE = colors.white


def make_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle(
            "Kicker",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=MUTED,
            spaceAfter=5,
            uppercase=True,
        ),
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=25,
            textColor=INK,
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=MUTED,
            spaceAfter=14,
        ),
        "h1": ParagraphStyle(
            "Heading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=15,
            leading=18,
            textColor=INK,
            spaceBefore=8,
            spaceAfter=7,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "Heading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=INK,
            spaceBefore=7,
            spaceAfter=4,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=13,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=10.5,
            textColor=INK,
        ),
        "small_center": ParagraphStyle(
            "SmallCenter",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.4,
            leading=9.2,
            textColor=INK,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=INK,
        ),
        "table_body": ParagraphStyle(
            "TableBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
            textColor=INK,
        ),
    }


STYLES = make_styles()


def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def h1(text: str) -> Paragraph:
    return p(text, "h1")


def h2(text: str) -> Paragraph:
    return p(text, "h2")


def bullets(items: list[str]) -> Table:
    table = Table(
        [[p(f"- {item}")] for item in items],
        colWidths=[CONTENT_WIDTH],
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    return table


def matrix(headers: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    if len(headers) != len(widths) or any(len(row) != len(headers) for row in rows):
        raise ValueError("table geometry does not match its content")
    data = [
        [p(value, "table_header") for value in headers],
        *[[p(value, "table_body") for value in row] for row in rows],
    ]
    table = Table(
        data,
        colWidths=[CONTENT_WIDTH * width for width in widths],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("GRID", (0, 0), (-1, -1), 0.45, GRID),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT]),
            ]
        )
    )
    return table


def pipeline(items: list[tuple[str, str]]) -> Table:
    data: list[Paragraph] = []
    widths: list[float] = []
    box_width = 0.205 if len(items) == 4 else 0.145
    arrow_width = (1.0 - box_width * len(items)) / (len(items) - 1)
    for index, (label, detail) in enumerate(items):
        data.append(p(f"<b>{label}</b><br/>{detail}", "small_center"))
        widths.append(box_width)
        if index < len(items) - 1:
            data.append(p("&gt;", "small_center"))
            widths.append(arrow_width)
    table = Table([data], colWidths=[CONTENT_WIDTH * width for width in widths])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for column in range(0, len(data), 2):
        style.extend(
            [
                ("BACKGROUND", (column, 0), (column, 0), LIGHT_BLUE),
                ("BOX", (column, 0), (column, 0), 0.8, BLUE),
            ]
        )
    table.setStyle(TableStyle(style))
    return table


def title_block(kicker: str, title: str, subtitle: str) -> list:
    return [
        p(kicker.upper(), "kicker"),
        p(title, "title"),
        p(subtitle, "subtitle"),
        Table([[""]], colWidths=[CONTENT_WIDTH], rowHeights=[1], style=[("BACKGROUND", (0, 0), (-1, -1), BLUE)]),
        Spacer(1, 12),
    ]


def page_callback(short_title: str, subject: str):
    def draw(canvas, doc):
        canvas.saveState()
        canvas.setTitle(short_title)
        canvas.setAuthor(AUTHOR)
        canvas.setSubject(subject)
        canvas.setCreator("Revon architecture PDF generator")
        canvas.setStrokeColor(GRID)
        canvas.setLineWidth(0.5)
        canvas.line(LEFT_MARGIN, 11 * mm, PAGE_WIDTH - RIGHT_MARGIN, 11 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(LEFT_MARGIN, 7.5 * mm, "REVON | CURRENT ARCHITECTURE")
        canvas.drawRightString(
            PAGE_WIDTH - RIGHT_MARGIN,
            7.5 * mm,
            f"{BUILD_DATE} | {doc.page}",
        )
        canvas.restoreState()

    return draw


def build_pdf(path: Path, title: str, subject: str, story: list) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        leftMargin=LEFT_MARGIN,
        rightMargin=RIGHT_MARGIN,
        topMargin=TOP_MARGIN,
        bottomMargin=BOTTOM_MARGIN,
        title=title,
        author=AUTHOR,
        subject=subject,
    )
    callback = page_callback(title, subject)
    doc.build(story, onFirstPage=callback, onLaterPages=callback)


def architecture_explanation_story() -> list:
    story = title_block(
        "Architecture explanation",
        "Revon Architecture",
        "How the implemented platform stores versions, commits incrementally, and compares history without overstating the prototype.",
    )
    story += [
        h1("The idea in one sentence"),
        p(
            "Revon is a content-addressed versioned key-value store whose state is indexed by a persistent fixed-depth Merkle hash trie. Normal mutation batches rewrite only touched paths, and Revon-H chooses between operation-log and hash-pruned Merkle differencing."
        ),
        h1("Implemented system"),
        pipeline(
            [
                ("Frontend", "Import, history, checkout, compare, metrics"),
                ("Local REST API", "Validation, repository isolation, write coordination"),
                ("Revon-H core", "Incremental commits, checkout, Log/Merkle diff"),
                ("SQLite store", "Objects, versions, metrics, HEAD in one transaction"),
            ]
        ),
        Spacer(1, 10),
        matrix(
            ["Layer", "Responsibility", "Current status"],
            [
                ["Frontend", "Operates repositories and presents version, diff, storage, work, and integrity data.", "Implemented for the local workflow."],
                ["HTTP API", "Validates JSON/CSV requests, constrains repository paths, and maps structured errors.", "Implemented; binds to loopback."],
                ["Revon-H", "Creates immutable versions, copies affected trie paths, checks out history, and selects a diff path.", "Implemented and tested."],
                ["Persistence", "Stores addressed objects and advances version metadata and HEAD atomically.", "Implemented with SQLite."],
                ["Evaluation", "Runs deterministic baselines, forced-Merkle, Revon-H, and Dolt workloads with an oracle.", "Audited evidence is versioned."],
            ],
            [0.18, 0.54, 0.28],
        ),
        h2("What exists now"),
        bullets(
            [
                "Durable repositories survive process exit and are verified when reopened.",
                "Each commit records a root hash, parent commit hash, addressed changeset, message, and timestamp.",
                "Unchanged trie nodes are reused by hash; normal mutations do not rebuild the complete state.",
                "Log, Merkle, and Hybrid diff modes return the same structured added, modified, and deleted result.",
            ]
        ),
        PageBreak(),
        *title_block("Mechanics", "Incremental commit and durable storage", "The data model remains content-addressed; SQLite supplies atomic durability."),
        h1("Commit workflow"),
        pipeline(
            [
                ("Validate", "Reject conflicts, invalid deletes, and stale bases"),
                ("Route", "Hash changed keys into fixed trie paths"),
                ("Rewrite", "Create affected leaves and ancestor union only"),
                ("Address", "Hash nodes, changeset, and commit"),
                ("Persist", "Insert objects and advance HEAD atomically"),
            ]
        ),
        Spacer(1, 10),
        p(
            "For branching factor <b>b</b>, depth <b>d</b>, and uniformly routed keys, expected leaf occupancy is approximately <b>N / (b^d)</b>. The paper configuration uses b=8 and d=4, yielding 4,096 possible leaf buckets. A sensitivity study reports other geometries instead of treating this choice as universal."
        ),
        h1("Stored objects and references"),
        matrix(
            ["Record", "Meaning"],
            [
                ["objects", "Canonical immutable node, changeset, and commit payloads keyed by content hash."],
                ["versions", "Human-readable version numbers mapped to addressed commit identities."],
                ["commit_stats", "Changed-key, new/reused-node, byte, and timing measurements outside commit identity."],
                ["refs", "Mutable named reference; the current implementation maintains HEAD."],
                ["metadata", "Schema version, branching factor, depth, and Hybrid threshold."],
            ],
            [0.22, 0.78],
        ),
        h1("Diff paths"),
        matrix(
            ["Mode", "Decision and work", "Best fit"],
            [
                ["Log", "Aggregate addressed changesets along an unbroken ancestor path; work follows intervening operations.", "Nearby versions with short or sparse histories."],
                ["Merkle", "Compare roots recursively, prune equal subtree hashes, and inspect entries only below unequal leaves.", "Longer histories or cases where log aggregation becomes expensive."],
                ["Hybrid", "Count ancestor operations and select Log at or below the configured boundary; select Merkle above it.", "One policy over both exact algorithms."],
            ],
            [0.16, 0.53, 0.31],
        ),
        p(
            "The runtime default is 128 operations for demos and repositories created without an override. The audited paper profile uses a separately calibrated frozen boundary of 4,096 operations. Neither value is claimed to be hardware-independent.",
            "small",
        ),
        PageBreak(),
        *title_block("Evidence and scope", "What the project proves", "The strongest explanation pairs measured behavior with explicit prototype boundaries."),
        h1("Verified evidence"),
        matrix(
            ["Evidence", "Result"],
            [
                ["Final comparison", "333 measured rows passed the shared correctness oracle; all 83 Tukey outlier candidates were retained."],
                ["Sensitivity", "45 measured trials across five trie geometries were correct; b=8, d=4 minimized storage in the tested set."],
                ["Durability", "Tests reopen SQLite repositories and reproduce history, checkout, diffs, metrics, and HEAD."],
                ["Failure handling", "Injected transaction failure rolls back SQLite and restores the last durable in-memory HEAD."],
            ],
            [0.24, 0.76],
        ),
        h1("Current boundaries"),
        bullets(
            [
                "History has one linear HEAD; named branches, merge commits, and conflict reporting are not implemented.",
                "Repositories allow one writer at a time; deployment-grade multi-host coordination is not implemented.",
                "Values remain inline in leaf nodes, and unreachable-object garbage collection is not implemented.",
                "The API is local-only and does not provide authentication, TLS, rate limiting, or public-service hardening.",
                "Dolt comparisons measure the declared CLI and SQL protocol, not isolated tree-algorithm speed.",
            ]
        ),
        h1("A concise explanation"),
        p(
            "Revon stores each structured version behind a content-addressed root. A mutation batch rewrites the changed leaves and their shared ancestor paths, while unchanged subtrees keep their hashes. The new objects, changeset, commit, metrics, version alias, and HEAD are committed in one SQLite transaction. For comparison, Revon-H uses recorded operations for short histories and switches to hash-pruned traversal when the configured operation boundary is exceeded."
        ),
        h2("Reproduce locally"),
        p(
            "Run <font name='Courier'>python revon_sqlite_demo.py --database revon_demo.revon.db --reset</font> for the durable reopen flow, and <font name='Courier'>python -m unittest -v</font> for the complete automated test suite.",
            "small",
        ),
    ]
    return story


def incremental_brief_story() -> list:
    story = title_block(
        "Revon-H core brief",
        "Incremental Merkle Hash Trie",
        "Implemented path copying, addressed history, durable transactions, and adaptive exact differencing.",
    )
    story += [
        h1("Commit mechanics"),
        pipeline(
            [
                ("Atomic batch", "puts and deletes"),
                ("Hash routing", "fixed trie paths"),
                ("Path copying", "affected union only"),
                ("New root", "old root unchanged"),
                ("Commit", "parent plus changeset"),
            ]
        ),
        Spacer(1, 10),
        matrix(
            ["Invariant", "Meaning"],
            [
                ["Incremental update", "Every affected leaf is rewritten once; only the union of its ancestor paths is rebuilt."],
                ["Structural sharing", "Unchanged child hashes are copied into new internal nodes; their subtrees are neither rebuilt nor re-hashed."],
                ["Addressed identity", "Canonical node, changeset, and commit payloads determine their SHA-256 identities."],
                ["Historical stability", "Earlier roots and commits remain immutable and continue to reproduce their complete states."],
                ["Atomic durability", "New objects, version mapping, commit statistics, and HEAD advance in one SQLite transaction."],
            ],
            [0.25, 0.75],
        ),
        h1("Geometry and selection"),
        p(
            "The default geometry is b=8 and d=4. It exposes 4,096 possible leaf buckets and twelve SHA-256 routing bits. Full keys stay in leaves, so keys sharing a routing prefix remain distinguishable."
        ),
        matrix(
            ["Policy", "Boundary", "Purpose"],
            [
                ["Runtime default", "128 operations", "Practical default for demos, the API, and repositories without an override."],
                ["Audited paper profile", "4,096 operations", "Frozen from separate calibration before the 333-row evaluation."],
            ],
            [0.27, 0.22, 0.51],
        ),
        PageBreak(),
        *title_block("Correctness and measurement", "What Revon-H reports", "Each optimization is paired with an equality check or an explicit work measure."),
        h1("Correctness contract"),
        bullets(
            [
                "Incremental roots are checked against canonical clean rebuilds in randomized mutation sequences.",
                "Forced Log, forced Merkle, and Hybrid comparisons must return identical structured differences.",
                "Every experimental result is checked against a shared deterministic changed-key oracle.",
                "Repository reopen verifies canonical encoding, object hashes, references, version continuity, metrics, parent links, and HEAD.",
            ]
        ),
        h1("Instrumentation"),
        matrix(
            ["Measure", "Interpretation"],
            [
                ["new trie nodes / bytes", "Incremental write amplification for the mutation batch."],
                ["reachable-node overlap", "Exact diagnostic structural sharing between two roots; excluded from commit timing."],
                ["log operations", "Natural work unit for changeset aggregation."],
                ["node pairs / equal subtrees", "Merkle traversal work and pruning effectiveness."],
                ["leaf entries", "Entry-level scan work below unequal leaf paths."],
                ["selected strategy", "The path chosen by Revon-H for the requested interval."],
            ],
            [0.31, 0.69],
        ),
        h1("Current limits"),
        p(
            "The implementation has a linear HEAD-only history, one-writer local storage, inline leaf values, and no garbage collection, branches, merges, remotes, schema evolution, or deployment-grade public API security. These are stated limits, not implemented features."
        ),
        h2("Run the verified flows"),
        p(
            "<font name='Courier'>python revon_cli_demo.py --show-changes</font><br/>"
            "<font name='Courier'>python revon_sqlite_demo.py --database revon_demo.revon.db --reset</font><br/>"
            "<font name='Courier'>python -m unittest -v</font>",
            "small",
        ),
    ]
    return story


def system_architecture_story() -> list:
    story = title_block(
        "Technical architecture",
        "Revon-H System Architecture",
        "How the frontend, local API, content-addressed core, SQLite persistence, and reproducible evidence pipeline fit together.",
    )
    story += [
        h1("End-to-end platform"),
        pipeline(
            [
                ("React / Vinext", "Repository workspace and metrics"),
                ("Python REST API", "Validation, CORS, repository services"),
                ("Revon-H engine", "Hash trie, commits, checkout, adaptive diff"),
                ("SQLite repository", "Addressed objects, versions, stats, HEAD"),
            ]
        ),
        Spacer(1, 10),
        matrix(
            ["Component", "Primary responsibility", "Implementation"],
            [
                ["Frontend", "Collect actions and visualize history, differences, work, storage, and integrity.", "React / Vinext and a typed fetch client."],
                ["HTTP API", "Validate requests, constrain repository names, map errors, and serialize writes.", "Python standard-library HTTP server."],
                ["Revon-H", "Create versions, incrementally copy trie paths, check out history, and compare versions.", "VersionedDatabase."],
                ["Persistence", "Store immutable objects and mutable references in one durable transaction.", "SQLiteRevonRepository."],
                ["Evaluation", "Execute fixed-seed workloads over baselines, Revon variants, and Dolt.", "experiments/final_benchmark.py."],
            ],
            [0.17, 0.50, 0.33],
        ),
        h1("Trust and deployment boundary"),
        p(
            "The complete interactive demo is intentionally local-first. The backend binds to 127.0.0.1, validates repository names, verifies stored hashes, and accepts configured browser origins. Authentication, TLS, rate limiting, and multi-host coordination are outside the current prototype."
        ),
        h2("Research contribution boundary"),
        p(
            "The research contribution is the inspectable combination of a fixed-depth Merkle hash trie, incremental copy-on-write updates, addressed changesets, and adaptive Log/Merkle selection. SQLite supplies durability; the frontend supplies interaction; the benchmark harness supplies comparative evidence."
        ),
        PageBreak(),
        *title_block("State and transactions", "Object model and commit path", "Immutable identities are separated from mutable aliases and operational measurements."),
        h1("Addressed graph"),
        matrix(
            ["Object or reference", "Contains or points to", "Identity behavior"],
            [
                ["Commit", "Root hash, parent commit, changeset hash, message, timestamp.", "Canonical payload determines commit hash."],
                ["Trie root/internal node", "Numbered child slots containing child hashes.", "Canonical child map determines node hash."],
                ["Leaf", "Canonical key/value entries for one route bucket.", "Canonical entries determine leaf hash."],
                ["Changeset", "Addressed put/delete records for one commit.", "Canonical operations determine changeset hash."],
                ["Version alias", "Monotonic display number mapped to a commit hash.", "Human-readable alias; not content identity."],
                ["HEAD", "Latest commit hash.", "Mutable reference advanced transactionally."],
            ],
            [0.23, 0.48, 0.29],
        ),
        h1("Commit request"),
        pipeline(
            [
                ("API validation", "input, repository, base version"),
                ("Incremental core", "route changes and copy affected paths"),
                ("Address objects", "nodes, changeset, commit"),
                ("SQLite transaction", "versions, stats, HEAD"),
            ]
        ),
        Spacer(1, 10),
        p(
            "A failed persistence statement causes a complete SQLite rollback. The wrapper then reloads the last durable state, preventing the in-memory HEAD from moving ahead of the repository file. Reopen verification rejects corrupted payloads or broken references."
        ),
        h1("Read requests"),
        matrix(
            ["Request", "Core path", "Result"],
            [
                ["Checkout", "Resolve version to commit, then materialize the addressed root.", "Historical key/value state plus pagination metadata."],
                ["Compare", "Resolve endpoints, then run forced Log, forced Merkle, or Hybrid.", "Added, modified, and deleted keys plus natural work metrics."],
                ["Metrics", "Read commit and repository statistics; optionally run a version comparison.", "Storage, sharing, write, and diff measurements."],
                ["Open", "Load metadata and objects, verify hashes and graph invariants.", "HEAD, integrity counts, and a usable repository handle."],
            ],
            [0.18, 0.50, 0.32],
        ),
        PageBreak(),
        *title_block("Selection and reproducibility", "Hybrid diff and evidence flow", "Runtime defaults and paper parameters are intentionally distinguished."),
        h1("Hybrid decision"),
        pipeline(
            [
                ("Resolve versions", "find ancestor direction"),
                ("Count operations", "sum addressed changesets"),
                ("Select path", "Log at/below threshold; Merkle above"),
                ("Return result", "same structured diff contract"),
            ]
        ),
        Spacer(1, 10),
        matrix(
            ["Configuration", "Value", "Scope"],
            [
                ["Runtime Hybrid threshold", "128 operations", "Default in the core, durable store, API, and CLI demo."],
                ["Paper Hybrid threshold", "4,096 operations", "Frozen calibrated boundary for the audited paper machine and workload family."],
                ["Trie geometry", "b=8, d=4", "Runtime and paper default; evaluated against four other configurations."],
            ],
            [0.30, 0.20, 0.50],
        ),
        h1("Evidence pipeline"),
        pipeline(
            [
                ("Fixed seeds", "deterministic workloads"),
                ("Shared oracle", "same expected changes"),
                ("Raw trials", "status, correctness, metrics"),
                ("Independent audit", "rebuild summaries and retain outliers"),
            ]
        ),
        Spacer(1, 10),
        p(
            "The versioned final evidence bundle contains 333 successful and correct measured rows. The separate sensitivity bundle contains 45 correct trials across five geometries. Paper tables and figures are generated from reviewed summary CSV files and checked against raw results and manifests."
        ),
        h1("Local run sequence"),
        p(
            "Start <font name='Courier'>python -m revon_api</font>, then run <font name='Courier'>npm run dev</font> from <font name='Courier'>frontend/</font>. For automated verification, run <font name='Courier'>python -m unittest -v</font> and <font name='Courier'>npm test</font>.",
            "small",
        ),
        h2("Repository"),
        p(
            "Source, evidence, and reproduction instructions: "
            "<link href='https://github.com/atharvasheersh/Revon' color='#111827'>https://github.com/atharvasheersh/Revon</link>",
            "small",
        ),
    ]
    return story


def build_all() -> list[Path]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [
        (
            OUT_DIR / "Revon_Architecture_Explanation.pdf",
            "Revon Architecture",
            "Current implementation explanation and responsible claim boundary",
            architecture_explanation_story(),
        ),
        (
            OUT_DIR / "Revon_H_Incremental_Merkle_Trie_Brief.pdf",
            "Revon-H Incremental Merkle Hash Trie",
            "Current incremental core, durability, correctness, and instrumentation brief",
            incremental_brief_story(),
        ),
        (
            OUT_DIR / "Revon_System_Architecture.pdf",
            "Revon-H System Architecture",
            "Current frontend, API, core, persistence, and evidence architecture",
            system_architecture_story(),
        ),
    ]
    for path, title, subject, story in outputs:
        build_pdf(path, title, subject, story)
        print(path)
    return [path for path, _, _, _ in outputs]


if __name__ == "__main__":
    build_all()
