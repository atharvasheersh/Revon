"""Validate the checked-in final paper and its supplemental telemetry evidence."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from docx import Document


ROOT = Path(__file__).resolve().parents[1]
PAPER_DOCX = ROOT / "paper" / "Revon_Final_Research_Paper.docx"
PAPER_PDF = ROOT / "paper" / "Revon_Final_Research_Paper.pdf"
TELEMETRY = ROOT / "evidence" / "paper-issues14-windows-telemetry-20260924"
COUNTERS = (
    "process_tree_peak_rss_bytes",
    "process_tree_cpu_seconds",
    "process_tree_read_bytes",
    "process_tree_write_bytes",
    "commit_operations_per_second",
)
REQUIRED_DISCLOSURES = (
    "A separate Windows sensitivity telemetry run has 405 rows (315 measured)",
    "These counters include setup and correctness work, not only timed operations",
    "No external researcher or clean clone has independently reproduced the timings",
    "internal audit checks evidence consistency but does not reproduce wall-clock results",
    "None of these experiments measures ordered range queries, concurrent reads or writes, or production throughput",
)


def main() -> None:
    audit = json.loads((TELEMETRY / "audit.json").read_text(encoding="utf-8"))
    assert audit["passed"] and not audit["issues"], audit
    assert audit["rows"] == 405 and audit["measured_rows"] == 315, audit
    assert audit["all_correct"], audit

    with (TELEMETRY / "raw_results.csv").open(
        newline="", encoding="utf-8"
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 405, len(rows)
    assert all(row["status"] == "ok" and row["correctness"] == "True" for row in rows)
    for counter in COUNTERS:
        assert all(row[counter] for row in rows), f"missing {counter} telemetry"

    document = Document(PAPER_DOCX)
    content = [paragraph.text for paragraph in document.paragraphs]
    content.extend(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    manuscript_text = "\n".join(content)
    assert document.paragraphs[0].text == (
        "Revon: Evaluating Hybrid Diffing in a Versioned Key-Value Prototype"
    ), "paper title does not match the bounded prototype contribution"
    assert "These are workflow-level results" in manuscript_text, (
        "abstract must identify the cross-system ratios as workflow-level"
    )
    assert len(document.tables) >= 3, "missing a paper comparison table"
    literature_widths = [
        int(column.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w"))
        for column in document.tables[0]._tbl.tblGrid.gridCol_lst
    ]
    assert literature_widths == [2100, 2300, 4620], literature_widths
    assert document.tables[0].cell(11, 2).text == "Mature production comparator"
    workload_table = document.tables[1]
    assert len(workload_table.rows) == 9 and len(workload_table.columns) == 5
    grid_widths = [
        int(column.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w"))
        for column in workload_table._tbl.tblGrid.gridCol_lst
    ]
    assert grid_widths == [2100, 1100, 800, 900, 4120], grid_widths
    assert sum(grid_widths) == 9020, grid_widths
    assert all(
        cell.paragraphs[0]._p.pPr is not None
        and cell.paragraphs[0].runs
        and cell.paragraphs[0].runs[0]._r.rPr is not None
        for row in workload_table.rows[1:]
        for cell in row.cells
    ), "workload rows are missing the table's paragraph or font formatting"
    results_table = document.tables[2]
    results_widths = [
        int(column.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}w"))
        for column in results_table._tbl.tblGrid.gridCol_lst
    ]
    assert results_widths == [2050, 750, 900, 1250, 4070], results_widths
    assert all(
        cell.paragraphs[0]._p.pPr is not None
        and cell.paragraphs[0].runs
        and cell.paragraphs[0].runs[0]._r.rPr is not None
        for row in results_table.rows[1:]
        for cell in row.cells
    ), "results rows are missing the table's paragraph or font formatting"
    bookmark_names = {
        bookmark.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}name")
        for bookmark in document._element.xpath(".//w:bookmarkStart")
    }
    hyperlink_anchors = {
        link.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor")
        for link in document._element.xpath(".//w:hyperlink")
        if link.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor")
    }
    assert hyperlink_anchors <= bookmark_names, (
        f"citation links point to missing bibliography bookmarks: {hyperlink_anchors - bookmark_names}"
    )
    assert len([name for name in bookmark_names if name and name.startswith("ref_")]) == 15, (
        "expected bookmarks for all 15 bibliography entries"
    )
    for disclosure in REQUIRED_DISCLOSURES:
        assert disclosure in manuscript_text, f"missing manuscript disclosure: {disclosure}"

    pdf = PAPER_PDF.read_bytes()
    assert pdf.startswith(b"%PDF-") and b"%%EOF" in pdf[-1024:], PAPER_PDF
    assert len(pdf) > 10_000, f"unexpectedly small manuscript PDF: {len(pdf)} bytes"

    print(
        "Final paper validated: DOCX disclosures present; PDF structure present; "
        "Windows telemetry audit passed (405 rows, 315 measured, all counters available)."
    )


if __name__ == "__main__":
    main()
