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
