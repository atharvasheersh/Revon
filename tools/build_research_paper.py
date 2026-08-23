from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT_DOCX = ROOT / "output" / "docs" / "Chronos_Research_Paper_Working_Draft.docx"
ASSET_DIR = ROOT / "tmp" / "paper_assets"
SUMMARY_CSV = ROOT / "output" / "benchmarks" / "check-again" / "summary.csv"
RAW_CSV = ROOT / "output" / "benchmarks" / "check-again" / "raw_results.csv"
MANIFEST_JSON = ROOT / "output" / "benchmarks" / "check-again" / "manifest.json"

DOC_SKILL = Path(
    r"C:\Users\admin\.codex\plugins\cache\openai-primary-runtime\documents\26.819.11345\skills\documents"
)
sys.path.insert(0, str(DOC_SKILL / "scripts"))
from table_geometry import apply_table_geometry, column_widths_from_weights  # noqa: E402


BLUE = "2E74B5"
DARK_BLUE = "1F4D78"
INK = "202A33"
MUTED = "5C6873"
PALE_BLUE = "E8EEF5"
PALE_GREEN = "EAF4EC"
PALE_AMBER = "FFF3D6"
PALE_RED = "FCE8E6"
WHITE = "FFFFFF"


def pcolor(value: str) -> str:
    return value if value.startswith("#") else f"#{value}"


def load_evidence():
    manifest = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    with SUMMARY_CSV.open(newline="", encoding="utf-8") as handle:
        summary = list(csv.DictReader(handle))
    with RAW_CSV.open(newline="", encoding="utf-8") as handle:
        raw = list(csv.DictReader(handle))
    evaluation = {
        row["model"]: row
        for row in summary
        if row["phase"] == "evaluation" and row["scenario"] == "smoke-spread"
    }
    calibration = [row for row in summary if row["phase"] == "calibration"]
    unavailable = sorted(
        {
            row["model"]
            for row in raw
            if row["status"] == "unavailable"
        }
    )
    return manifest, evaluation, calibration, unavailable


def font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype(r"C:\Windows\Fonts\calibri.ttf", size)
    except OSError:
        return ImageFont.load_default()


def rounded_box(draw, xy, fill, outline=BLUE, radius=16, width=3):
    draw.rounded_rectangle(
        xy, radius=radius, fill=pcolor(fill), outline=pcolor(outline), width=width
    )


def centered(draw, xy, text, fnt, fill=INK):
    left, top, right, bottom = xy
    bbox = draw.multiline_textbbox((0, 0), text, font=fnt, spacing=4, align="center")
    x = (left + right - (bbox[2] - bbox[0])) / 2
    y = (top + bottom - (bbox[3] - bbox[1])) / 2
    draw.multiline_text(
        (x, y), text, font=fnt, fill=pcolor(fill), spacing=4, align="center"
    )


def arrow(draw, start, end, color=DARK_BLUE, width=4):
    color = pcolor(color)
    draw.line([start, end], fill=color, width=width)
    x2, y2 = end
    x1, y1 = start
    angle = math.atan2(y2 - y1, x2 - x1)
    for delta in (2.55, -2.55):
        p = (x2 + 14 * math.cos(angle + delta), y2 + 14 * math.sin(angle + delta))
        draw.line([end, p], fill=color, width=width)


def make_architecture_diagram(path: Path):
    image = Image.new("RGB", (1500, 740), "white")
    draw = ImageDraw.Draw(image)
    title = font(34, True)
    label = font(25, True)
    body = font(21)
    draw.text((50, 25), "Chronos layered architecture", font=title, fill=pcolor(INK))

    boxes = [
        ((70, 130, 340, 290), "React workspace\nmetrics + repository UI", PALE_BLUE),
        ((420, 130, 690, 290), "REST API\nrepository operations", PALE_GREEN),
        ((770, 130, 1050, 290), "Chronos-H core\ncommit · checkout · diff", PALE_AMBER),
        ((1130, 130, 1430, 290), "SQLite object store\nobjects · versions · HEAD", "EEF0F2"),
    ]
    for xy, text, fill in boxes:
        rounded_box(draw, xy, fill)
        centered(draw, xy, text, label if "Chronos-H" in text else body)
    for a, b in zip(boxes, boxes[1:]):
        arrow(draw, (a[0][2] + 10, 210), (b[0][0] - 10, 210))

    core = (370, 415, 1130, 665)
    rounded_box(draw, core, "F8FAFC", outline=DARK_BLUE, radius=20, width=4)
    draw.text((400, 438), "Research contribution boundary", font=label, fill=pcolor(DARK_BLUE))
    sub = [
        ((410, 505, 610, 625), "Fixed-depth\nMerkle hash trie"),
        ((650, 505, 850, 625), "Copy-on-write\nincremental hashing"),
        ((890, 505, 1090, 625), "Adaptive log /\nMerkle diff"),
    ]
    for xy, text in sub:
        rounded_box(draw, xy, WHITE, outline=BLUE, radius=12, width=2)
        centered(draw, xy, text, body)
    arrow(draw, (510, 500), (510, 320))
    arrow(draw, (750, 500), (900, 320))
    arrow(draw, (990, 500), (990, 320))
    image.save(path, quality=95)


def make_workflow_diagram(path: Path):
    image = Image.new("RGB", (1500, 650), "white")
    draw = ImageDraw.Draw(image)
    title = font(34, True)
    body = font(21)
    draw.text((50, 25), "Incremental commit and adaptive diff workflow", font=title, fill=pcolor(INK))
    steps = [
        "Canonical\nbatch",
        "Hash keys +\ngroup routes",
        "Rewrite affected\nleaves once",
        "Rewrite union of\nancestor paths",
        "Persist objects +\ncommit + HEAD",
    ]
    x_positions = [55, 345, 635, 925, 1215]
    for idx, (x, text) in enumerate(zip(x_positions, steps)):
        xy = (x, 125, x + 225, 260)
        rounded_box(draw, xy, PALE_BLUE if idx < 4 else PALE_GREEN, radius=15, width=3)
        centered(draw, xy, text, body)
        if idx < len(steps) - 1:
            arrow(draw, (x + 235, 192), (x_positions[idx + 1] - 10, 192))

    draw.line((750, 295, 750, 360), fill=pcolor(DARK_BLUE), width=4)
    arrow(draw, (750, 295), (750, 360))
    left = (360, 405, 675, 565)
    right = (825, 405, 1140, 565)
    rounded_box(draw, left, PALE_GREEN, outline="4B8A5A")
    rounded_box(draw, right, PALE_AMBER, outline="B47B12")
    centered(draw, left, "≤ calibrated operation threshold\naggregate changesets", body)
    centered(draw, right, "> calibrated operation threshold\nhash-pruned tree comparison", body)
    draw.text((636, 365), "DIFF", font=font(24, True), fill=pcolor(DARK_BLUE))
    arrow(draw, (730, 390), (620, 405))
    arrow(draw, (770, 390), (880, 405))
    image.save(path, quality=95)


def make_results_chart(path: Path, evaluation: dict[str, dict[str, str]]):
    models = ["Snapshot", "Log-only", "Chronos-M (forced Merkle)", "Chronos-H"]
    values = [float(evaluation[m]["diff_ms_median"]) for m in models]
    labels = ["Snapshot", "Log-only", "Chronos-M", "Chronos-H"]
    colors = ["#8B96A3", "#65A879", "#E0A33A", "#2E74B5"]
    image = Image.new("RGB", (1500, 720), "white")
    draw = ImageDraw.Draw(image)
    draw.text((55, 30), "Preliminary smoke diff latency (median, ms)", font=font(34, True), fill=pcolor(INK))
    draw.text((55, 82), "1,000 rows · 4 commits · 10 changes/commit · n=3 measured trials", font=font(22), fill=pcolor(MUTED))
    left, right, top, bottom = 150, 1435, 155, 590
    max_v = max(values) * 1.12
    draw.line((left, top, left, bottom), fill=pcolor(INK), width=3)
    draw.line((left, bottom, right, bottom), fill=pcolor(INK), width=3)
    for tick in range(0, 7):
        val = max_v * tick / 6
        y = bottom - (bottom - top) * tick / 6
        draw.line((left, y, right, y), fill="#E5E9ED", width=1)
        draw.text((52, y - 12), f"{val:.1f}", font=font(18), fill=pcolor(MUTED))
    slot = (right - left) / len(values)
    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        x0 = left + idx * slot + 62
        x1 = left + (idx + 1) * slot - 62
        y0 = bottom - (bottom - top) * value / max_v
        draw.rounded_rectangle((x0, y0, x1, bottom), radius=8, fill=color)
        draw.text((x0 + 8, y0 - 34), f"{value:.3f}", font=font(21, True), fill=pcolor(INK))
        bbox = draw.textbbox((0, 0), label, font=font(20))
        draw.text(((x0 + x1 - (bbox[2] - bbox[0])) / 2, bottom + 20), label, font=font(20), fill=pcolor(INK))
    draw.text((55, 665), "Source: output/benchmarks/check-again/summary.csv. Dolt absent; not a final comparison.", font=font(19), fill=pcolor(MUTED))
    image.save(path, quality=95)


def set_cell_shading(cell, fill: str):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_border(cell, color="D7DEE5", size="4"):
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), size)
        node.set(qn("w:color"), color)


def keep_row(row, repeat=False):
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)
    if repeat:
        tbl_header = OxmlElement("w:tblHeader")
        tbl_header.set(qn("w:val"), "true")
        tr_pr.append(tbl_header)


def add_table(doc, headers, rows, weights, font_size=8.3, header_fill=PALE_BLUE):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    header = table.rows[0]
    for index, text in enumerate(headers):
        cell = header.cells[index]
        cell.text = text
        set_cell_shading(cell, header_fill)
        set_cell_border(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        for paragraph in cell.paragraphs:
            paragraph.paragraph_format.space_after = Pt(0)
            for run in paragraph.runs:
                run.bold = True
                run.font.size = Pt(font_size)
                run.font.color.rgb = RGBColor.from_string(INK)
    keep_row(header, repeat=True)
    for row_data in rows:
        row = table.add_row()
        keep_row(row)
        for index, value in enumerate(row_data):
            cell = row.cells[index]
            cell.text = str(value)
            set_cell_border(cell)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.TOP
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.05
                for run in paragraph.runs:
                    run.font.size = Pt(font_size)
                    run.font.color.rgb = RGBColor.from_string(INK)
    widths = column_widths_from_weights(weights, 9360)
    apply_table_geometry(table, widths, table_width_dxa=9360, indent_dxa=120)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_caption(doc, text):
    p = doc.add_paragraph(style="Caption")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run(text)
    return p


def add_picture_with_alt(doc, path: Path, alt_text: str, width=Inches(6.35)):
    shape = doc.add_picture(str(path), width=width)
    shape._inline.docPr.set("descr", alt_text)
    shape._inline.docPr.set("title", alt_text.split(".")[0])
    return shape


def add_bullets(doc, items, style="List Bullet"):
    for item in items:
        p = doc.add_paragraph(style=style)
        p.add_run(item)


def add_numbered(doc, items):
    numbering = doc.part.numbering_part.element
    existing_ids = [
        int(node.get(qn("w:numId")))
        for node in numbering.findall(qn("w:num"))
        if node.get(qn("w:numId")) is not None
    ]
    num_id = max(existing_ids, default=0) + 1
    style_num_id = doc.styles["List Number"]._element.pPr.numPr.numId.val
    style_num = next(
        node
        for node in numbering.findall(qn("w:num"))
        if int(node.get(qn("w:numId"))) == style_num_id
    )
    abstract_id = style_num.find(qn("w:abstractNumId")).get(qn("w:val"))
    num = OxmlElement("w:num")
    num.set(qn("w:numId"), str(num_id))
    abstract = OxmlElement("w:abstractNumId")
    abstract.set(qn("w:val"), abstract_id)
    num.append(abstract)
    override = OxmlElement("w:lvlOverride")
    override.set(qn("w:ilvl"), "0")
    start = OxmlElement("w:startOverride")
    start.set(qn("w:val"), "1")
    override.append(start)
    num.append(override)
    numbering.append(num)
    for item in items:
        p = doc.add_paragraph(style="List Number")
        num_pr = p._p.get_or_add_pPr().get_or_add_numPr()
        num_pr.get_or_add_numId().val = num_id
        p.add_run(item)


def add_page_number(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = paragraph.add_run()
    fld_char1 = OxmlElement("w:fldChar")
    fld_char1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char2 = OxmlElement("w:fldChar")
    fld_char2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char1, instr_text, fld_char2])


def set_repeat_table_header(row):
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_doc_defaults(doc: Document):
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(1)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)
    section.header_distance = Inches(0.492)
    section.footer_distance = Inches(0.492)

    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.line_spacing = 1.25

    for name, size, color, before, after in (
        ("Title", 28, DARK_BLUE, 0, 14),
        ("Subtitle", 13, MUTED, 0, 10),
        ("Heading 1", 16, BLUE, 18, 10),
        ("Heading 2", 13, INK, 14, 7),
        ("Heading 3", 12, DARK_BLUE, 10, 5),
    ):
        style = styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(size)
        style.font.bold = name != "Subtitle"
        style.font.color.rgb = RGBColor.from_string(color)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    caption = styles["Caption"]
    caption.font.name = "Calibri"
    caption.font.size = Pt(9)
    caption.font.italic = True
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.paragraph_format.space_before = Pt(4)
    caption.paragraph_format.space_after = Pt(9)

    for name in ("List Bullet", "List Number"):
        style = styles[name]
        style.font.name = "Calibri"
        style.font.size = Pt(11)
        style.paragraph_format.left_indent = Inches(0.375)
        style.paragraph_format.first_line_indent = Inches(-0.188)
        style.paragraph_format.space_after = Pt(4)
        style.paragraph_format.line_spacing = 1.25

    if "Callout" not in [s.name for s in styles]:
        callout = styles.add_style("Callout", WD_STYLE_TYPE.PARAGRAPH)
    else:
        callout = styles["Callout"]
    callout.font.name = "Calibri"
    callout.font.size = Pt(10.5)
    callout.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    callout.paragraph_format.left_indent = Inches(0.18)
    callout.paragraph_format.right_indent = Inches(0.18)
    callout.paragraph_format.space_before = Pt(7)
    callout.paragraph_format.space_after = Pt(7)

    for sec in doc.sections:
        header = sec.header
        p = header.paragraphs[0]
        p.text = "CHRONOS  |  RESEARCH PAPER WORKING DRAFT"
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.space_after = Pt(2)
        for run in p.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(8)
            run.font.bold = True
            run.font.color.rgb = RGBColor.from_string(MUTED)
        p_pr = p._p.get_or_add_pPr()
        borders = OxmlElement("w:pBdr")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), "6")
        bottom.set(qn("w:space"), "3")
        bottom.set(qn("w:color"), "CBD3DA")
        borders.append(bottom)
        p_pr.append(borders)
        footer = sec.footer
        fp = footer.paragraphs[0]
        fp.add_run("WORKING DRAFT · 23 AUGUST 2026                                      ")
        for run in fp.runs:
            run.font.name = "Calibri"
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor.from_string(MUTED)
        add_page_number(fp)


def add_status_banner(doc, text, fill=PALE_AMBER):
    table = doc.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    cell.text = text
    set_cell_shading(cell, fill)
    set_cell_border(cell, color="D6AA54", size="8")
    for p in cell.paragraphs:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        for run in p.runs:
            run.bold = True
            run.font.size = Pt(10)
            run.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    apply_table_geometry(table, [9360], table_width_dxa=9360, indent_dxa=120)
    keep_row(table.rows[0], repeat=True)


def add_source_note(doc, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    r = p.add_run(text)
    r.font.size = Pt(8.5)
    r.font.italic = True
    r.font.color.rgb = RGBColor.from_string(MUTED)


def page_break(doc):
    doc.add_page_break()


def build():
    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    manifest, evaluation, calibration, unavailable = load_evidence()

    architecture = ASSET_DIR / "architecture.png"
    workflow = ASSET_DIR / "workflow.png"
    results_chart = ASSET_DIR / "results_chart.png"
    make_architecture_diagram(architecture)
    make_workflow_diagram(workflow)
    make_results_chart(results_chart, evaluation)

    doc = Document()
    set_doc_defaults(doc)
    doc.core_properties.title = "Chronos: A Content-Addressed Versioned Data Store"
    doc.core_properties.subject = "Research paper working draft"
    doc.core_properties.author = "Chronos Project Team"
    doc.core_properties.keywords = "Merkle trie, content-addressed storage, structured data versioning, Dolt"

    # Cover
    p = doc.add_paragraph(style="Title")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Chronos")
    p = doc.add_paragraph(style="Subtitle")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("A Content-Addressed Versioned Data Store")
    r.bold = True
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("A Git-Inspired Approach to Structured Data Versioning Using Merkle Search Trees")
    r.font.size = Pt(16)
    r.font.color.rgb = RGBColor.from_string(DARK_BLUE)
    p.paragraph_format.space_after = Pt(20)
    add_status_banner(doc, "WORKING DRAFT · ARCHITECTURE AND METHODOLOGY COMPLETE · FINAL RESULTS PENDING")
    doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Chronos Project Team\n23 August 2026").bold = True
    p.paragraph_format.space_after = Pt(18)
    doc.add_heading("Draft status", level=1)
    add_table(
        doc,
        ["Component", "Status", "What this draft contains"],
        [
            ("Architecture", "Complete", "System boundary, object model, persistence, and workflows."),
            ("Methodology", "Complete", "Variants, workloads, metrics, fairness, and reproducibility protocol."),
            ("Literature review", "Working complete", "Nine-source matrix and synthesis; supervisor review still recommended."),
            ("Results", "Preliminary only", "Imported solely from the latest smoke benchmark CSV export."),
            ("Final claims", "Gated", "Require paper-profile runs with Dolt installed and reviewed CSVs."),
        ],
        [1.35, 1.2, 3.95],
        font_size=9,
    )
    p = doc.add_paragraph(style="Callout")
    p.add_run("Evidence rule. ").bold = True
    p.add_run(
        "No performance value in this document was invented or transcribed from memory. "
        "The preliminary table and chart are generated from output/benchmarks/check-again/summary.csv."
    )

    page_break(doc)
    doc.add_heading("Abstract", level=1)
    doc.add_paragraph(
        "Versioning structured datasets requires a balance between cheap writes, compact storage, rapid historical reconstruction, "
        "and efficient comparison. Chronos is a Python research prototype that stores immutable state in a persistent fixed-depth "
        "Merkle hash trie. Each commit rewrites only the affected leaf buckets and their ancestor paths, while unchanged subtrees are "
        "reused by content hash. Chronos-H augments this tree with content-addressed changesets and adaptively selects either operation-log "
        "aggregation or hash-pruned tree comparison for a version diff. SQLite provides atomic persistence for addressed objects, version "
        "aliases, measurements, and HEAD without defining the indexing semantics. This paper specifies the architecture and an experimental "
        "methodology comparing Snapshot, Log-only, forced-Merkle Chronos-M, Chronos-H, and Dolt. A preliminary 1,000-row smoke run validates "
        "correctness and the measurement pipeline, but Dolt was unavailable; consequently, this draft makes no state-of-the-art performance "
        "claim. Final conclusions are reserved for repeated paper-profile experiments using identical deterministic workloads."
    )
    p = doc.add_paragraph()
    p.add_run("Keywords—").bold = True
    p.add_run("content-addressed storage; dataset versioning; Merkle trie; copy-on-write; adaptive differencing; SQLite; Dolt")

    doc.add_heading("1. Introduction", level=1)
    doc.add_paragraph(
        "Dataset versioning is not merely file archival. A useful system must preserve exact history while supporting incremental updates, "
        "historical checkout, and change inspection without repeatedly scanning or copying every record. Git demonstrates how immutable, "
        "content-addressed objects and commit graphs make history reproducible [2]. Structured data introduces different access patterns: "
        "records have stable keys, updates are often sparse, and diffs may span either a few nearby commits or a large history distance."
    )
    doc.add_paragraph(
        "Chronos tests a deliberately narrow research hypothesis: whether a fixed-depth, hash-routed Merkle trie with incremental path "
        "rewriting can be combined with an operation index so that the system chooses an efficient diff path for the observed history distance. "
        "It is not presented as a SQL database or a replacement for Dolt. Dolt is the state-of-the-art production comparator because it combines "
        "SQL semantics with Git-style history over Prolly Trees [3]. Chronos instead exposes a smaller, instrumentable design whose internal work "
        "can be measured directly."
    )
    doc.add_heading("1.1 Research questions", level=2)
    add_numbered(
        doc,
        [
            "RQ1: Does incremental copy-on-write hashing reduce work relative to full-state snapshotting as datasets grow?",
            "RQ2: When does changeset aggregation outperform hash-pruned Merkle comparison, and can a calibrated selector capture that boundary?",
            "RQ3: What latency, storage, memory, and examined-work trade-offs does Chronos-H exhibit against Snapshot, Log-only, Chronos-M, and Dolt?",
        ],
    )
    doc.add_heading("1.2 Claimed contributions", level=2)
    add_bullets(
        doc,
        [
            "A deterministic fixed-depth Merkle hash trie with canonical SHA-256 addressing and incremental multi-key path rewriting.",
            "A hybrid diff policy combining explicit changesets for short ancestor paths with hash-pruned tree comparison for larger histories.",
            "A SQLite durability layer that atomically commits immutable objects, metrics, version aliases, and HEAD while verifying hashes on reopen.",
            "A reproducible harness that runs shared workloads across four implemented variants and a native Dolt adapter, exporting raw and summarized CSV evidence.",
        ],
    )

    doc.add_heading("2. Literature Review", level=1)
    doc.add_paragraph(
        "A literature review maps what prior systems already solve, how they solve it, and which unresolved design question motivates the present work. "
        "For Chronos, the relevant line runs from authenticated hash structures and Git object identity to database-native branching, dataset-version "
        "storage trade-offs, and modern content-addressed structured stores."
    )
    doc.add_heading("2.1 Foundations", level=2)
    doc.add_paragraph(
        "Merkle's authenticated tree construction established the principle that a compact root digest can commit to a much larger collection [1]. "
        "Git operationalizes content-addressed objects, trees, and commits in a developer-facing version-control model [2]. Chronos borrows immutable "
        "object identity and parent-linked commits, but routes structured keys through a fixed-depth trie rather than representing a directory tree."
    )
    doc.add_heading("2.2 Dataset and relational versioning", level=2)
    doc.add_paragraph(
        "DataHub framed collaborative dataset management as a first-class platform problem [4]. Decibel integrated branching into a relational storage "
        "engine and evaluated version-first, tuple-first, and hybrid layouts [5]. OrpheusDB instead provided bolt-on relational versioning and emphasized "
        "the storage-versus-recreation trade-off [6], a trade-off formalized more generally by dataset-versioning research [7]. These systems motivate "
        "Chronos's explicit measurement of commit, checkout, storage, and diff costs rather than a single throughput metric."
    )
    doc.add_heading("2.3 Content-addressed structured stores", level=2)
    doc.add_paragraph(
        "Noms organizes typed data into content-addressed chunks [8], while ForkBase offers immutable, tamper-evident storage and fork semantics for "
        "blockchain and forkable applications [9]. Dolt uses a Git-style commit graph whose table state is represented by Prolly Trees, content-addressed "
        "B-tree-like structures designed for structural sharing and efficient diff [3]. Chronos differs by fixing trie depth and exposing both operation- "
        "and tree-based diff work. This makes the model simpler to instrument, but it also sacrifices Dolt's ordered range behavior, SQL surface, mature "
        "branching, merge, and production engineering."
    )
    doc.add_heading("2.4 Literature-review matrix", level=2)
    matrix_rows = [
        ("Merkle [1]", "Authenticated hash tree", "Root digest commits to a set", "Foundation; not a data-versioning system"),
        ("Git [2]", "Content-addressed objects + commit DAG", "Trees, parents, object reuse", "File/tree oriented; no structured query model"),
        ("Dolt [3]", "Git-style history over Prolly Trees", "Ordered structural sharing; native diff", "Production SOTA comparator; much broader SQL scope"),
        ("DataHub [4]", "Collaborative dataset platform", "Dataset history and workflows", "Platform vision rather than Chronos's tree/diff mechanism"),
        ("Decibel [5]", "Relational branching engine", "Version-/tuple-first and hybrid layouts", "Built-in relational engine; different storage model"),
        ("OrpheusDB [6]", "Bolt-on relational versioning", "Partitioned version storage/retrieval", "Focuses version recreation, not Merkle pruning"),
        ("Dataset versioning [7]", "Version graph optimization", "Formal storage/recreation trade-off", "Analytical basis; not an executable adaptive diff"),
        ("Noms [8]", "Typed content-addressed chunks", "Decentralized immutable data", "Broader data model; Chronos evaluates fixed trie + logs"),
        ("ForkBase [9]", "Forkable immutable storage engine", "Content addressing and fork semantics", "Distributed/forking scope exceeds current Chronos"),
    ]
    add_table(
        doc,
        ["Work", "Representation", "Key contribution", "Gap / relationship to Chronos"],
        matrix_rows,
        [1.05, 1.65, 1.75, 2.05],
        font_size=7.6,
    )
    add_source_note(doc, "Matrix entries are analytical summaries of primary papers or official project documentation; full citations appear in Section 9.")

    doc.add_heading("3. Chronos Architecture", level=1)
    doc.add_paragraph(
        "Chronos is separated into interface, service, model, and durability layers. The research contribution is the versioned storage model and "
        "its instrumented diff policy; the React frontend and REST API make the prototype demonstrable but are not treated as algorithmic contributions."
    )
    add_picture_with_alt(
        doc,
        architecture,
        "Layered Chronos architecture: React workspace connects to the REST API, Chronos-H core, and SQLite object store. The core contains a fixed-depth Merkle hash trie, copy-on-write incremental hashing, and adaptive log/Merkle diff.",
    )
    add_caption(doc, "Figure 1. Layered Chronos architecture and the research contribution boundary.")
    doc.add_heading("3.1 Content-addressed object model", level=2)
    add_table(
        doc,
        ["Object", "Identity / reference", "Purpose"],
        [
            ("Trie node", "SHA-256 of canonical node JSON", "Internal child hashes or a canonical leaf bucket."),
            ("Changeset", "SHA-256 of canonical operation list", "Records the exact batch used by log-based diff."),
            ("Commit", "SHA-256 over root, parent, changeset, message, timestamp", "Immutable version identity and linear history link."),
            ("Version alias", "Sequential integer v1, v2, …", "Human-readable pointer to a commit; not the content identity."),
            ("HEAD", "Named SQLite reference", "Points to the latest durable commit."),
        ],
        [1.25, 2.0, 3.25],
        font_size=8.6,
    )
    doc.add_heading("3.2 Fixed-depth Merkle hash trie", level=2)
    doc.add_paragraph(
        "The default trie has branching factor b=8 and depth d=4. SHA-256(key) supplies three routing bits per level, selecting one of 4,096 possible "
        "leaf buckets after twelve bits. Full keys remain in the leaf, so routing-prefix collisions preserve correctness. Under uniform routing, expected "
        "leaf occupancy is approximately N / b^d; at 100,000 records this is about 24.4 records per bucket. The value is a tunable design point, not a "
        "universal optimum, and the final study must sweep depth and branching factor."
    )
    doc.add_heading("3.3 Incremental hashing", level=2)
    doc.add_paragraph(
        "A commit does not rebuild the tree. Changed keys are routed and grouped by common prefixes; every affected leaf is rewritten once, and only the "
        "union of affected ancestor paths is rebuilt. Unchanged child hashes are copied into the new internal nodes, preserving structural sharing. For a "
        "single changed key, the model creates roughly d+1 trie nodes; batched keys sharing a prefix also share rewritten ancestors."
    )

    doc.add_heading("3.4 Commit and diff workflow", level=2)
    add_picture_with_alt(
        doc,
        workflow,
        "Incremental commit workflow from canonical batch through key hashing, affected-leaf rewriting, ancestor-path rewriting, and atomic persistence, followed by an adaptive choice between changeset aggregation and Merkle comparison.",
    )
    add_caption(doc, "Figure 2. Incremental commit path and Chronos-H adaptive diff decision.")
    doc.add_heading("3.5 Diff algorithms", level=2)
    add_table(
        doc,
        ["Mode", "Procedure", "Measured work", "Expected strength"],
        [
            ("Log", "Walk the ancestor path and aggregate key operations.", "Operations examined", "Short history distance or few accumulated operations."),
            ("Merkle", "Compare roots recursively; skip equal subtree hashes.", "Node pairs + leaf entries", "Large histories with substantial unchanged structure."),
            ("Hybrid", "Count ancestor operations; choose log at or below threshold, otherwise Merkle.", "Selected mode's unit", "Avoid a single diff mechanism across all regimes."),
        ],
        [0.9, 2.25, 1.35, 2.0],
        font_size=8.4,
    )
    doc.add_paragraph(
        "The current threshold is calibrated independently of evaluation workloads. In the latest smoke export, the selected threshold was 128 operations. "
        "Because the calibration points ended at 128 operations and log diff was still faster there, this value is a policy boundary derived from the sampled "
        "grid—not proof of a true performance crossover. The final paper should extend the calibration range."
    )
    doc.add_heading("3.6 SQLite durability boundary", level=2)
    doc.add_paragraph(
        "SQLite stores, but does not compute, Chronos semantics. The schema contains metadata, addressed objects, version-to-commit mappings, commit statistics, "
        "and refs. A BEGIN IMMEDIATE transaction inserts new objects, the version and metrics, and the updated HEAD atomically. On reopen, Chronos verifies "
        "canonical payloads, object hashes, child and commit references, contiguous versions, the parent chain, metrics, and HEAD. Failed persistence reloads "
        "the last durable in-memory model so volatile state cannot advance beyond disk."
    )
    doc.add_heading("3.7 Current scope", level=2)
    add_bullets(
        doc,
        [
            "Single linear HEAD; named branches, merge commits, and conflict resolution are not implemented.",
            "One serialized writer; SQLite is used as an embedded object container, not as the versioning algorithm.",
            "Values are stored inline in leaf nodes; blob chunking and garbage collection are not implemented.",
            "The API supports repository creation/opening, CSV import, batch commits, history, checkout, comparison, and metrics.",
        ],
    )

    doc.add_heading("4. Methodology", level=1)
    doc.add_heading("4.1 Experimental variants", level=2)
    add_table(
        doc,
        ["Variant", "Durable representation", "Diff mechanism", "Role"],
        [
            ("Snapshot", "Canonical full-state JSON/version", "Full key scan", "Storage/time lower-bound baseline for simple implementation."),
            ("Log-only", "Base state + fsynced JSONL changesets", "Replay / aggregate operations", "Operation-log baseline."),
            ("Chronos-M", "SQLite fixed-depth Merkle trie", "Forced hash-pruned tree diff", "Ablation isolating adaptive selection."),
            ("Chronos-H", "Same trie + addressed changesets", "Calibrated log/Merkle selection", "Primary proposed system."),
            ("Dolt", "Native repository and keyed SQL table", "Native dolt diff", "Production SOTA comparator."),
        ],
        [1.0, 2.15, 1.7, 1.65],
        font_size=8.1,
    )
    doc.add_paragraph(
        "Chronos-M is an ablation, not a separate product claim. The main comparison remains Snapshot, Log-only, Chronos-H, and Dolt; Chronos-M answers "
        "whether adaptive selection changes the forced-Merkle design."
    )
    doc.add_heading("4.2 Workloads", level=2)
    doc.add_paragraph(
        "Each scenario is generated once from a fixed seed and reused byte-for-byte across adapters and repetitions. Initial keys are deterministic, values "
        "are deterministic SHA-256-derived payloads, and each batch contains updates with insert/delete operations when the batch size permits. Spread and "
        "hot-key locality are tested separately. The current paper profile is:"
    )
    add_table(
        doc,
        ["Scenario", "Rows", "Commits", "Changes/commit", "Locality"],
        [
            ("small-sparse", "1,000", "10", "10", "spread"),
            ("medium-sparse", "10,000", "10", "10", "spread"),
            ("medium-dense", "10,000", "10", "1,000", "spread"),
            ("large-sparse", "100,000", "10", "100", "spread"),
            ("large-hot", "100,000", "10", "100", "hot"),
        ],
        [1.55, 1.15, 1.0, 1.55, 1.25],
        font_size=8.6,
    )
    add_source_note(doc, "A 1,000,000-row stress point may be added if the machine completes it reliably; it must be reported as an extension, not silently mixed into the preset profile.")
    doc.add_heading("4.3 Calibration and evaluation separation", level=2)
    doc.add_paragraph(
        "Calibration sweeps operation counts using workloads that are not reused for final evaluation. The selector chooses the largest tested count at which "
        "median log diff is no slower than median Merkle diff. The frozen threshold is then used for all Chronos-H evaluation trials. This prevents selecting "
        "the policy after observing the headline workloads."
    )

    doc.add_heading("4.4 Metrics and measurement contract", level=2)
    add_table(
        doc,
        ["Metric", "Operational definition"],
        [
            ("Initial import", "Time to create the first durable state and version; repository setup excluded."),
            ("Incremental commit", "Median duration of durable commits within one trial."),
            ("Diff", "Time to consume a complete comparison from the initial to final version."),
            ("Checkout", "Time to fully materialize the target historical version."),
            ("Storage", "Total regular-file bytes inside the fresh adapter repository directory."),
            ("Peak memory", "Python allocations via tracemalloc in current exports; Dolt RSS only if externally sampled."),
            ("Work examined", "Natural unit: keys, operations, log operations, or trie-node pairs; units are not interchangeable."),
            ("Correctness", "Exact initial/final checkout and changed-key oracle where structured keys are exposed."),
        ],
        [1.45, 5.05],
        font_size=8.7,
    )
    doc.add_heading("4.5 Repetition and reporting", level=2)
    add_bullets(
        doc,
        [
            "Run on an idle, AC-powered machine using fresh repositories for every trial.",
            "Use two warmups and seven measured paper-profile trials; exclude warmups from summaries.",
            "Report median, 25th percentile, and 75th percentile rather than only the fastest run.",
            "Record seed, workload digest, platform, Python version, Dolt version, selected strategy, and metric method in every export.",
            "Retain raw_results.csv, summary.csv, and manifest.json together; treat the manifest as part of the evidence.",
        ],
    )
    doc.add_heading("4.6 Fairness and reproducibility", level=2)
    doc.add_paragraph(
        "The same logical states and mutation batches are presented to every adapter. Chronos and baselines use native durable representations; Dolt uses a "
        "keyed SQL table, commits/tags each version, checks history with AS OF, and invokes native dolt diff. This is a repeatable CLI-facing workflow, not an "
        "isolated engine microbenchmark. Python tracemalloc and external process RSS are different memory quantities and must not appear on one comparative "
        "chart unless all variants are rerun under the same external monitor. Dolt exposes no comparable internal node counter, so work-examined remains blank."
    )
    doc.add_heading("4.7 Analysis plan", level=2)
    add_numbered(
        doc,
        [
            "Verify correctness and workload digests before interpreting speed.",
            "Plot median and interquartile range against rows, mutation density, history distance, and locality.",
            "Compare Chronos-H with Chronos-M to isolate the selector; compare both with simple baselines to expose overheads.",
            "Compare Chronos-H with Dolt conservatively, reporting where it wins, ties, or loses and separating prototype scope from SQL capability.",
            "Repeat any anomalous cell and preserve both the original and confirmation exports.",
        ],
    )

    page_break(doc)
    doc.add_heading("5. Preliminary Results: Pipeline Validation Only", level=1)
    add_status_banner(doc, "NOT FINAL PAPER EVIDENCE · SMOKE PROFILE · DOLT UNAVAILABLE", fill=PALE_RED)
    doc.add_paragraph(
        f"The latest reviewed export ({manifest['created_utc']}) used Python {manifest['python_version']} on {manifest['platform']}, one warmup, "
        f"and {manifest['measured_trials']} measured trials. The evaluation scenario contained 1,000 rows, four commits, and ten changes per commit "
        "with spread locality. All four available implementations passed the correctness oracle. Dolt produced no timing rows because it was not installed."
    )
    result_rows = []
    for model in ("Snapshot", "Log-only", "Chronos-M (forced Merkle)", "Chronos-H"):
        row = evaluation[model]
        result_rows.append(
            (
                model.replace(" (forced Merkle)", ""),
                f"{float(row['initial_import_ms_median']):.2f}",
                f"{float(row['incremental_commit_ms_median']):.2f}",
                f"{float(row['diff_ms_median']):.3f}",
                f"{float(row['checkout_ms_median']):.2f}",
                f"{float(row['storage_bytes_median']) / 1024:.1f}",
                row["strategy_selected"],
            )
        )
    add_table(
        doc,
        ["Model", "Import ms", "Commit ms", "Diff ms", "Checkout ms", "Storage KiB", "Diff path"],
        result_rows,
        [1.4, 0.82, 0.88, 0.75, 0.9, 0.92, 0.83],
        font_size=7.7,
    )
    add_source_note(doc, "Source: output/benchmarks/check-again/summary.csv; medians over three measured trials. Values are reproduced programmatically from the CSV.")
    add_picture_with_alt(
        doc,
        results_chart,
        "Bar chart of preliminary smoke diff latency medians: Snapshot 5.453 milliseconds, Log-only 0.770, Chronos-M 1.125, and Chronos-H 0.275. Dolt was unavailable.",
    )
    add_caption(doc, "Figure 3. Preliminary smoke-profile diff latency. The chart is diagnostic, not a Dolt comparison.")

    doc.add_heading("5.1 What the smoke run supports", level=2)
    snapshot_diff = float(evaluation["Snapshot"]["diff_ms_median"])
    hybrid_diff = float(evaluation["Chronos-H"]["diff_ms_median"])
    merkle_diff = float(evaluation["Chronos-M (forced Merkle)"]["diff_ms_median"])
    add_bullets(
        doc,
        [
            "The end-to-end harness, CSV summarization, correctness oracle, and four implemented adapters execute successfully.",
            f"Chronos-H selected log for 40 accumulated operations and recorded a {hybrid_diff:.3f} ms median diff, versus {merkle_diff:.3f} ms for forced Merkle.",
            f"On this single small scenario, Chronos-H diff was {snapshot_diff / hybrid_diff:.1f}× lower than Snapshot; this ratio must not be generalized beyond the smoke workload.",
            "The Chronos variants incurred materially higher initial-import latency and storage than the simple baselines, demonstrating a real prototype overhead that the final discussion must retain.",
        ],
    )
    doc.add_heading("5.2 What the smoke run does not support", level=2)
    add_bullets(
        doc,
        [
            "No claim that Chronos is faster, smaller, or more scalable than Dolt.",
            "No claim that 128 operations is the true log/Merkle crossover; the calibration grid did not sample beyond 128 in this run.",
            "No asymptotic conclusion from one dataset size, one locality pattern, four commits, and three trials.",
            "No fair cross-process memory comparison because the current Python and Dolt measurement methods differ.",
        ],
    )

    doc.add_heading("6. Discussion", level=1)
    doc.add_heading("6.1 Interpretation of the design", level=2)
    doc.add_paragraph(
        "Chronos's value is not that it reproduces Dolt with fewer features. Its research value lies in making three costs explicit: incremental structural "
        "rewrite, log aggregation, and hash-pruned tree traversal. A fixed-depth trie gives predictable routing and a compact implementation, while a separate "
        "changeset index gives the system a second diff path. The ablation determines whether that second path improves the Merkle-only model."
    )
    doc.add_paragraph(
        "The smoke results are consistent with the motivation: when only 40 operations separate versions, aggregating those operations examines less work than "
        "traversing 362 trie-node pairs. The same export also shows the cost of the design: Chronos initial import and storage exceed the Snapshot and Log-only "
        "baselines at 1,000 rows. A credible final paper must present both sides and identify the regions in which structural sharing repays its metadata overhead."
    )
    doc.add_heading("6.2 Relationship to Dolt", level=2)
    add_table(
        doc,
        ["Dimension", "Chronos-H", "Dolt"],
        [
            ("Core structure", "Fixed-depth Merkle hash trie + changesets", "Prolly Trees in a Git-style commit graph"),
            ("Interface", "Key/value repository, REST API, research UI", "SQL database, CLI, branches, merges, remotes"),
            ("Diff", "Instrumented adaptive log/Merkle selection", "Native structural diff over production engine"),
            ("Purpose", "Controlled prototype for mechanism-level evaluation", "General production database and collaboration system"),
            ("Current maturity", "Linear history; Python; single writer", "Mature cross-platform SQL product"),
        ],
        [1.2, 2.55, 2.75],
        font_size=8.4,
    )
    doc.add_paragraph(
        "Therefore, absolute latency is only one axis. The paper must avoid presenting feature disparity as an algorithmic advantage: Dolt performs SQL parsing, "
        "schema management, and production durability work outside Chronos's current scope. The strongest defensible result would identify specific workload "
        "regions where Chronos-H's simplified mechanism reduces measured diff work while openly reporting its missing capabilities and overheads."
    )
    doc.add_heading("6.3 Decision rules for final claims", level=2)
    add_bullets(
        doc,
        [
            "Use 'outperformed on scenario X' only when the reviewed median and IQR support it; avoid an unqualified 'faster than Dolt.'",
            "Treat Chronos-M versus Chronos-H as the mechanism ablation; do not inflate the headline comparison with unnecessary variants.",
            "Report losses and ties with the same prominence as wins.",
            "Separate statistical observations from architectural explanations; label explanations as hypotheses unless directly measured.",
        ],
    )

    doc.add_heading("7. Limitations and Threats to Validity", level=1)
    add_table(
        doc,
        ["Threat", "Why it matters", "Mitigation / reporting rule"],
        [
            ("Language/runtime asymmetry", "Chronos is Python; Dolt is a mature Go product.", "Frame as system-level comparison and add work counters where available."),
            ("Feature asymmetry", "Dolt includes SQL, branches, merges, and production features.", "Do not convert lower prototype overhead into a universal superiority claim."),
            ("Fixed trie parameters", "b=8, d=4 may favor some sizes/distributions.", "Run a branching-factor/depth sensitivity sweep."),
            ("Linear history", "Current log diff assumes ancestor traversal and no merges.", "State scope; future work adds named branches and merge-aware diff."),
            ("Work-unit mismatch", "Keys, operations, and node pairs are different quantities.", "Plot within-unit trends; never treat them as one normalized count."),
            ("Memory instrumentation", "tracemalloc omits non-Python allocations; Dolt needs RSS.", "Rerun all systems under one external sampler before comparison."),
            ("OS and cache effects", "Windows scheduling and filesystem cache affect timings.", "Idle machine, fresh repositories, warmups, repeated trials, median/IQR."),
            ("Synthetic data", "Uniform hashed keys may not capture real skew or payload diversity.", "Add at least one public structured dataset and a declared key mapping."),
            ("Smoke evidence", "Current results cover one small workload and no Dolt.", "Keep as pipeline validation; replace tables after paper-profile export review."),
        ],
        [1.35, 2.25, 2.9],
        font_size=7.8,
    )
    doc.add_heading("8. Completion Plan and Provisional Conclusion", level=1)
    doc.add_heading("8.1 Evidence gate before submission", level=2)
    add_numbered(
        doc,
        [
            "Install a pinned Dolt release, confirm dolt version is recorded, and run the adapter correctness path independently.",
            "Extend threshold calibration beyond 128 operations; freeze the selected threshold before evaluation.",
            "Run the paper profile with two warmups and seven measured trials on an idle machine.",
            "Review raw_results.csv for failures/outliers, verify every workload SHA-256, and regenerate summary.csv without manual edits.",
            "Run the trie parameter sweep and, if feasible, the declared 1,000,000-row stress extension.",
            "Replace Section 5 with final tables/plots; then finalize results, discussion, limitations, abstract, and conclusion.",
            "Archive the exact harness commit, Dolt version, manifests, reviewed CSVs, and plotting script used for the submitted paper.",
        ],
    )
    doc.add_heading("8.2 Provisional conclusion", level=2)
    doc.add_paragraph(
        "Chronos demonstrates a coherent architecture for content-addressed structured-data versioning: immutable canonical objects, incremental copy-on-write "
        "Merkle trie updates, durable commits in SQLite, and a diff path that can select between changeset aggregation and structural hash pruning. The smoke "
        "experiment confirms functional correctness and the evidence pipeline, and it illustrates why adaptive selection is worth evaluating. It does not yet "
        "establish comparative performance against Dolt. The final contribution will depend on the reviewed paper-profile results and on a restrained account "
        "of where the hybrid design helps, where it costs more, and how its limited prototype scope differs from a production SQL database."
    )

    page_break(doc)
    doc.add_heading("9. References", level=1)
    references = [
        "[1] R. C. Merkle, “A Digital Signature Based on a Conventional Encryption Function,” Advances in Cryptology—CRYPTO ’87, LNCS 293, pp. 369–378, 1988. https://doi.org/10.1007/3-540-48184-2_32",
        "[2] S. Chacon and B. Straub, “Git Internals—Git Objects,” Pro Git, 2nd ed. https://git-scm.com/book/en/v2/Git-Internals-Git-Objects",
        "[3] DoltHub, “Dolt Storage Engine Architecture.” https://www.dolthub.com/docs/architecture/storage-engine/",
        "[4] A. Bhardwaj et al., “DataHub: Collaborative Data Science & Dataset Version Management at Scale,” arXiv:1409.0798, 2014. https://arxiv.org/abs/1409.0798",
        "[5] A. Maddox et al., “Decibel: The Relational Dataset Branching System,” Proceedings of the VLDB Endowment, vol. 9, no. 9, pp. 624–635, 2016. https://doi.org/10.14778/2947618.2947619",
        "[6] S. Huang et al., “OrpheusDB: Bolt-on Versioning for Relational Databases,” Proceedings of the VLDB Endowment, vol. 10, no. 10, pp. 1130–1141, 2017. https://arxiv.org/abs/1703.02475",
        "[7] S. Bhattacherjee et al., “Principles of Dataset Versioning: Exploring the Recreation/Storage Tradeoff,” Proceedings of the VLDB Endowment, 2015. https://pmc.ncbi.nlm.nih.gov/articles/PMC5526644/",
        "[8] Attic Labs, “Noms: Introduction.” https://github.com/attic-labs/noms/blob/master/doc/intro.md",
        "[9] S. Wang et al., “ForkBase: An Efficient Storage Engine for Blockchain and Forkable Applications,” Proceedings of the VLDB Endowment, vol. 11, no. 10, pp. 1137–1150, 2018. https://www.vldb.org/pvldb/vol11/p1137-wang.pdf",
    ]
    for ref in references:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.28)
        p.paragraph_format.first_line_indent = Inches(-0.28)
        p.paragraph_format.space_after = Pt(7)
        p.add_run(ref)

    doc.add_heading("Appendix A. Reproducible Commands", level=1)
    p = doc.add_paragraph()
    p.add_run("Smoke verification\n").bold = True
    r = p.add_run("python -m experiments.final_benchmark --profile smoke --warmups 1 --trials 3")
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    p = doc.add_paragraph()
    p.add_run("Final paper run\n").bold = True
    r = p.add_run("python -m experiments.final_benchmark --profile paper --warmups 2 --trials 7")
    r.font.name = "Consolas"
    r.font.size = Pt(9)
    p = doc.add_paragraph(style="Callout")
    p.add_run("Run discipline. ").bold = True
    p.add_run("Do not edit benchmark CSVs manually. Preserve raw results, summary, and manifest as one evidence bundle.")

    # First-page header is intentionally quiet; cover carries the editorial identity.
    for paragraph in doc.paragraphs:
        paragraph.paragraph_format.widow_control = True
        if paragraph.style.name.startswith("Heading"):
            paragraph.paragraph_format.keep_with_next = True

    doc.save(OUT_DOCX)
    print(OUT_DOCX)


if __name__ == "__main__":
    build()
