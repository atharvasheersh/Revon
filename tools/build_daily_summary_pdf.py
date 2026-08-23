from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "Chronos_Daily_Work_Summary_2026-08-23.pdf"

NAVY = colors.HexColor("#17324D")
BLUE = colors.HexColor("#2563A6")
INK = colors.HexColor("#1E2933")
MUTED = colors.HexColor("#5F6C78")
LINE = colors.HexColor("#D6DEE6")
PALE_BLUE = colors.HexColor("#EAF2FA")
PALE_GREEN = colors.HexColor("#EAF5EE")
PALE_AMBER = colors.HexColor("#FFF4D8")
PALE_GRAY = colors.HexColor("#F5F7F9")
WHITE = colors.white


def register_fonts() -> tuple[str, str]:
    regular = Path(r"C:\Windows\Fonts\calibri.ttf")
    bold = Path(r"C:\Windows\Fonts\calibrib.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ChronosSans", str(regular)))
        pdfmetrics.registerFont(TTFont("ChronosSans-Bold", str(bold)))
        return "ChronosSans", "ChronosSans-Bold"
    return "Helvetica", "Helvetica-Bold"


REGULAR, BOLD = register_fonts()


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            parent=base["Title"],
            fontName=BOLD,
            fontSize=27,
            leading=31,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontName=REGULAR,
            fontSize=12,
            leading=16,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=BOLD,
            fontSize=17,
            leading=21,
            textColor=BLUE,
            spaceBefore=4,
            spaceAfter=8,
            keepWithNext=True,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=BOLD,
            fontSize=12,
            leading=15,
            textColor=NAVY,
            spaceBefore=8,
            spaceAfter=5,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=REGULAR,
            fontSize=9.5,
            leading=13.2,
            textColor=INK,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName=REGULAR,
            fontSize=8,
            leading=10.5,
            textColor=MUTED,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["BodyText"],
            fontName=REGULAR,
            fontSize=8.2,
            leading=10.5,
            textColor=INK,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=base["BodyText"],
            fontName=BOLD,
            fontSize=8.2,
            leading=10.5,
            textColor=NAVY,
        ),
        "metric": ParagraphStyle(
            "Metric",
            parent=base["BodyText"],
            fontName=BOLD,
            fontSize=20,
            leading=22,
            alignment=TA_CENTER,
            textColor=NAVY,
        ),
        "metric_label": ParagraphStyle(
            "MetricLabel",
            parent=base["BodyText"],
            fontName=REGULAR,
            fontSize=7.5,
            leading=9,
            alignment=TA_CENTER,
            textColor=MUTED,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["BodyText"],
            fontName=REGULAR,
            fontSize=9.2,
            leading=12.6,
            textColor=INK,
            leftIndent=13,
            firstLineIndent=-8,
            bulletIndent=3,
            spaceAfter=4,
        ),
        "code": ParagraphStyle(
            "Code",
            parent=base["Code"],
            fontName="Courier",
            fontSize=7.4,
            leading=10,
            textColor=INK,
            leftIndent=7,
            rightIndent=7,
            spaceBefore=3,
            spaceAfter=3,
        ),
    }


S = styles()


def P(text: str, kind: str = "body") -> Paragraph:
    return Paragraph(text, S[kind])


def bullet(text: str) -> Paragraph:
    return Paragraph(f"- {text}", S["bullet"])


def header_footer(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(18 * mm, height - 15 * mm, width - 18 * mm, height - 15 * mm)
    canvas.setFont(BOLD, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, height - 11.5 * mm, "CHRONOS  |  DAILY WORK SUMMARY")
    canvas.setFont(REGULAR, 7.5)
    canvas.drawString(18 * mm, 10 * mm, "23 AUGUST 2026  |  FINAL-SUBMISSION BRANCH")
    canvas.drawRightString(width - 18 * mm, 10 * mm, f"PAGE {doc.page}")
    canvas.restoreState()


def card_grid():
    data = [
        [P("40", "metric"), P("2", "metric"), P("14", "metric"), P("5", "metric")],
        [
            P("Python tests passed", "metric_label"),
            P("Rendered frontend tests passed", "metric_label"),
            P("Research-draft PDF pages", "metric_label"),
            P("Benchmark variants specified", "metric_label"),
        ],
    ]
    table = Table(data, colWidths=[41 * mm] * 4, rowHeights=[15 * mm, 12 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, WHITE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def timeline():
    rows = [
        [P("1", "cell_bold"), P("Backend API", "cell_bold"), P("Durable repository workflows exposed and tested.", "cell")],
        [P("2", "cell_bold"), P("Integrated frontend", "cell_bold"), P("Repository, import, commit, history, checkout, diff, and metrics UI.", "cell")],
        [P("3", "cell_bold"), P("Visual refinement", "cell_bold"), P("Professional project styling, then a white metrics-first research layout.", "cell")],
        [P("4", "cell_bold"), P("Paper draft", "cell_bold"), P("Architecture, methodology, literature matrix, preliminary CSV evidence, and completion gate.", "cell")],
        [P("5", "cell_bold"), P("Handoff", "cell_bold"), P("Verified PDFs, commit notes, reproducible generators, and exact Git staging plan.", "cell")],
    ]
    table = Table(rows, colWidths=[11 * mm, 39 * mm, 116 * mm], repeatRows=0)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), BLUE),
                ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
                ("BACKGROUND", (1, 0), (-1, -1), PALE_GRAY),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def section_table(rows):
    data = [[P("Area", "cell_bold"), P("Delivered today", "cell_bold"), P("Evidence / status", "cell_bold")]]
    for row in rows:
        data.append([P(row[0], "cell_bold"), P(row[1], "cell"), P(row[2], "cell")])
    table = Table(data, colWidths=[30 * mm, 96 * mm, 40 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, -1), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_GRAY]),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def callout(title: str, text: str, fill=PALE_AMBER):
    table = Table([[P(f"<b>{title}</b><br/>{text}", "body")]], colWidths=[166 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), fill),
                ("BOX", (0, 0), (-1, -1), 0.8, BLUE),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=22 * mm,
        leftMargin=22 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Chronos Daily Work Summary - 23 August 2026",
        author="Chronos Project Team",
        subject="Backend, frontend, experimental, documentation, and paper progress",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates(PageTemplate(id="standard", frames=[frame], onPage=header_footer))

    story = []
    story.append(Spacer(1, 18 * mm))
    story.append(P("Chronos", "title"))
    story.append(P("Daily Work Summary - 23 August 2026", "subtitle"))
    story.append(HRFlowable(width="100%", thickness=1.2, color=BLUE, spaceAfter=12))
    story.append(
        P(
            "Today converted Chronos from a storage-engine prototype into a coherent final-submission platform: a durable backend API, an integrated metrics-first frontend, a reproducible benchmark path, and a paper-ready research draft. The core remains the Python fixed-depth Merkle hash trie with incremental hashing and Chronos-H adaptive diff selection.",
            "body",
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(card_grid())
    story.append(Spacer(1, 8 * mm))
    story.append(P("Work sequence", "h1"))
    story.append(timeline())
    story.append(Spacer(1, 8 * mm))
    story.append(
        callout(
            "Current position",
            "The demonstrable platform and paper structure are ready. The only major evidence gap is the final paper-profile benchmark with Dolt installed; no state-of-the-art performance claim has been made prematurely.",
            PALE_GREEN,
        )
    )

    story.append(PageBreak())
    story.append(P("1. Backend and platform delivery", "h1"))
    story.append(
        section_table(
            [
                (
                    "Repository API",
                    "Added server-controlled create, list, open, and integrity verification. Repository names resolve beneath one server-owned root rather than accepting arbitrary client paths.",
                    "Committed as d3c9593.",
                ),
                (
                    "Data ingest",
                    "Added keyed JSON state, JSON row, and raw UTF-8 CSV import paths.",
                    "Integrated through API and frontend.",
                ),
                (
                    "Version writes",
                    "Added atomic puts/deletes with optimistic base-version conflict detection and per-repository write locking.",
                    "SQLite remains the durable source of truth.",
                ),
                (
                    "History operations",
                    "Exposed history, paginated checkout, structured comparison, construction metrics, storage size, and log/Merkle work metrics.",
                    "Covers every final UI action.",
                ),
                (
                    "HTTP controls",
                    "Added dependency-free threaded serving, loopback default, CORS allowlist, structured errors, request-size limits, and OpenAPI output.",
                    "Auth/TLS/rate limits remain out of local-demo scope.",
                ),
            ]
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(P("2. Frontend delivery and redesign", "h1"))
    story.append(
        section_table(
            [
                (
                    "Integrated workspace",
                    "Built the React/Vinext repository workspace and typed Chronos API client for create/open, import, commit, history, checkout, compare, and metrics.",
                    "Committed as 3f55bd6.",
                ),
                (
                    "Interaction states",
                    "Added loading, offline, empty, success, and error states; persistent API URL settings; visible keyboard focus; and reduced-motion behavior.",
                    "Accessibility behavior preserved through redesigns.",
                ),
                (
                    "Professional pass",
                    "Reduced promotional styling, tightened hierarchy, simplified labels, and introduced restrained project-oriented controls.",
                    "Committed as 682b13a.",
                ),
                (
                    "Metrics-first layout",
                    "Finalized an all-white research dashboard with high-contrast typography, thin rules, square metric cards, cobalt accents, and a compact top navigation.",
                    "Committed as 688b523.",
                ),
                (
                    "Scale selector",
                    "Added selectable 10, 100, 10K, 100K, and 1M record targets while explicitly separating requested scale from measured repository results.",
                    "No fabricated benchmark values shown.",
                ),
            ]
        )
    )

    story.append(PageBreak())
    story.append(P("3. Research, experiments, and documentation", "h1"))
    story.append(P("Experimental position", "h2"))
    for item in [
        "Kept the primary comparison focused on Snapshot, Log-only, Chronos-H, and Dolt; Chronos-M remains a forced-Merkle ablation.",
        "Defined deterministic shared workloads, disjoint calibration and evaluation phases, fixed seeds, warmups, repeated trials, medians, interquartile ranges, correctness checks, and raw CSV evidence.",
        "Retained the latest 1,000-row smoke run only as pipeline validation. All four available Python variants were correct; Dolt was unavailable.",
        "Preserved the 128-operation selector threshold as a smoke calibration result, not a proven universal crossover.",
    ]:
        story.append(bullet(item))

    story.append(P("Paper-ready working draft", "h2"))
    story.append(
        section_table(
            [
                (
                    "Architecture",
                    "Documented the content-addressed object model, b=8/d=4 fixed trie, incremental copy-on-write path rewriting, adaptive diff workflow, SQLite transaction boundary, API layer, and current scope.",
                    "Includes two architecture/workflow diagrams.",
                ),
                (
                    "Literature review",
                    "Built a nine-source matrix spanning Merkle trees, Git, Dolt, DataHub, Decibel, OrpheusDB, dataset versioning, Noms, and ForkBase.",
                    "Primary/official sources cited.",
                ),
                (
                    "Methodology",
                    "Specified variants, workload grid, calibration policy, timing contracts, storage/memory/work measures, correctness oracle, repetition protocol, and fairness rules.",
                    "Ready for final experiment data.",
                ),
                (
                    "Preliminary results",
                    "Generated the smoke result table and chart directly from output/benchmarks/check-again/summary.csv.",
                    "Clearly labeled non-final; Dolt absent.",
                ),
                (
                    "Final sections",
                    "Added evidence-gated discussion, limitations, provisional conclusion, references, and reproducible benchmark commands.",
                    "Final claims intentionally deferred.",
                ),
            ]
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(P("Documents and reproducibility", "h2"))
    for item in [
        "Generated an editable 14-page DOCX and a matching tagged PDF for the research draft.",
        "Kept a reproducible Python builder for the paper and a dated Markdown commit record.",
        "Previously generated the platform changes summary and system architecture handoff PDFs.",
        "Stored raw benchmark CSV outputs outside Git according to the repository ignore policy.",
    ]:
        story.append(bullet(item))

    story.append(PageBreak())
    story.append(P("4. Verification, Git state, and next actions", "h1"))
    story.append(P("Verification completed", "h2"))
    verification = [
        [P("Check", "cell_bold"), P("Result", "cell_bold")],
        [P("Python unit/integration suite", "cell"), P("40 tests passed", "cell_bold")],
        [P("Frontend lint", "cell"), P("Passed with zero errors", "cell_bold")],
        [P("Frontend production test", "cell"), P("Build passed; 2 rendered-page tests passed", "cell_bold")],
        [P("Research DOCX tables", "cell"), P("12 exact-width geometry checks passed", "cell_bold")],
        [P("Research DOCX accessibility", "cell"), P("Zero findings", "cell_bold")],
        [P("Research PDF", "cell"), P("14 pages rendered and visually inspected", "cell_bold")],
    ]
    vt = Table(verification, colWidths=[79 * mm, 87 * mm], repeatRows=1)
    vt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE_GRAY]),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(vt)
    story.append(Spacer(1, 7 * mm))
    story.append(P("Committed today", "h2"))
    for item in [
        "d3c9593 - feat(api): expose durable Chronos workflows",
        "3f55bd6 - feat(frontend): deliver final Chronos workspace",
        "4b32f24 - docs(final): record platform delivery and architecture",
        "682b13a - style(frontend): refine project workspace presentation",
        "688b523 - feat(frontend): redesign as white metrics workspace",
    ]:
        story.append(bullet(item))

    story.append(P("Ready for the next commit", "h2"))
    story.append(
        callout(
            "Recommended scope: research paper and daily handoff",
            "Stage the research-paper builder, paper DOCX/PDF, its Markdown record, this daily-summary builder, and this PDF. Do not use git add . because the worktree also contains unrelated PDFs and temporary Word lock files.",
            PALE_BLUE,
        )
    )

    story.append(P("Remaining final-submission work", "h2"))
    for item in [
        "Install and pin Dolt; verify its adapter and historical correctness path.",
        "Extend threshold calibration beyond 128 operations and freeze the selected value.",
        "Run the paper profile with two warmups and seven measured trials on an idle machine.",
        "Review the raw CSV bundle, run the trie parameter sensitivity sweep, and optionally add the declared 1M-row stress extension.",
        "Replace preliminary paper results, then finalize discussion, abstract, conclusion, and the submission package.",
    ]:
        story.append(bullet(item))

    doc.build(story)
    print(OUTPUT)


if __name__ == "__main__":
    build()
