from pathlib import Path
import hashlib
import os
import re
import zipfile


INPUT = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column_Figure_Fit.docx")
OUTPUT = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column_Tables_Fixed.docx")
TEMP = OUTPUT.with_suffix(".building.docx")
DOCUMENT_XML = "word/document.xml"

# Widths are in twips. 8,500 twips (5.90 in) fits comfortably inside the
# manuscript's 6.27-inch single-column text area.
TABLE_WIDTHS = {
    1: [2500, 1300, 1200, 1700, 1800],  # Table 2
    2: [2500, 1250, 1450, 1700, 1600],  # Table 3
}

TABLE_PATTERN = re.compile(rb"<w:tbl>.*?</w:tbl>", re.DOTALL)
GRID_PATTERN = re.compile(rb"<w:tblGrid>.*?</w:tblGrid>", re.DOTALL)
TCW_PATTERN = re.compile(rb'<w:tcW\b[^>]*/>')


def resize_table(block: bytes, widths: list[int], table_number: int) -> bytes:
    total = sum(widths)

    block, count = re.subn(
        rb'<w:tblW\b[^>]*/>',
        f'<w:tblW w:type="dxa" w:w="{total}"/>'.encode("ascii"),
        block,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Table {table_number}: table width element not found")

    block, count = re.subn(
        rb'<w:jc\s+w:val="[^"]+"\s*/>',
        b'<w:jc w:val="center"/>',
        block,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Table {table_number}: alignment element not found")

    block, count = re.subn(
        rb'<w:tblInd\b[^>]*/>',
        b'<w:tblInd w:type="dxa" w:w="25"/>',
        block,
        count=1,
    )
    if count != 1:
        raise RuntimeError(f"Table {table_number}: indent element not found")

    grid = b"<w:tblGrid>" + b"".join(
        f'<w:gridCol w:w="{width}"/>'.encode("ascii") for width in widths
    ) + b"</w:tblGrid>"
    block, count = GRID_PATTERN.subn(grid, block, count=1)
    if count != 1:
        raise RuntimeError(f"Table {table_number}: table grid not found")

    tcws = list(TCW_PATTERN.finditer(block))
    if not tcws or len(tcws) % len(widths) != 0:
        raise RuntimeError(
            f"Table {table_number}: unexpected cell-width count {len(tcws)}"
        )

    pieces = []
    cursor = 0
    for index, match in enumerate(tcws):
        width = widths[index % len(widths)]
        pieces.append(block[cursor:match.start()])
        pieces.append(f'<w:tcW w:type="dxa" w:w="{width}"/>'.encode("ascii"))
        cursor = match.end()
    pieces.append(block[cursor:])
    return b"".join(pieces)


with zipfile.ZipFile(INPUT, "r") as source_zip:
    members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

original = {info.filename: data for info, data in members}
document = original[DOCUMENT_XML]
tables = list(TABLE_PATTERN.finditer(document))
if len(tables) != 3:
    raise RuntimeError(f"Expected 3 tables; found {len(tables)}")

page_break = b'<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
parts = []
cursor = 0
for index, match in enumerate(tables):
    block = match.group(0)
    if index in TABLE_WIDTHS:
        block = resize_table(block, TABLE_WIDTHS[index], index + 1)
    parts.append(document[cursor:match.start()])
    if index == 2:
        parts.append(page_break)
    parts.append(block)
    cursor = match.end()
parts.append(document[cursor:])
updated = b"".join(parts)

with zipfile.ZipFile(TEMP, "w") as output_zip:
    for info, data in members:
        output_zip.writestr(info, updated if info.filename == DOCUMENT_XML else data)

with zipfile.ZipFile(TEMP, "r") as revised_zip:
    revised = {info.filename: revised_zip.read(info.filename) for info in revised_zip.infolist()}

if list(original) != list(revised):
    raise RuntimeError("DOCX package membership or order changed")

unexpected = []
for name, original_data in original.items():
    revised_data = revised[name]
    if name == DOCUMENT_XML:
        if revised_data != updated:
            unexpected.append(name)
    elif hashlib.sha256(original_data).digest() != hashlib.sha256(revised_data).digest():
        unexpected.append(name)

if unexpected:
    raise RuntimeError(f"Unexpected changes outside document.xml: {unexpected}")

os.replace(TEMP, OUTPUT)
print(f"Updated: {OUTPUT}")
print("Table 2 width: 8,500 twips")
print("Table 3 width: 8,500 twips")
print("Table 3 moved to a new page")
print("Changed package parts: word/document.xml only")
