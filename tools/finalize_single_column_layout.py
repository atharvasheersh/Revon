from pathlib import Path
import hashlib
import os
import re
import shutil
import zipfile


DOCX = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column.docx")
BACKUP = Path(r"C:\Users\admin\Desktop\Revon\.codex_tmp\Revon_Final_Research_Paper_Single_Column_before_final_layout.docx")
TEMP = DOCX.with_suffix(".finalizing.docx")
DOCUMENT_XML = "word/document.xml"

# Use a slightly more compact full-column width so the enlarged figures remain
# readable without creating a nearly empty trailing page. Aspect ratios remain
# unchanged. Each extent appears once in wp:extent and once in a:xfrm/a:ext.
REPLACEMENTS = [
    (b'cx="5257800" cy="3084576"', b'cx="5029200" cy="2950464"', 2),
    (b'cx="5257800" cy="2734055"', b'cx="5029200" cy="2615183"', 2),
    (b'cx="5257800" cy="2957512"', b'cx="5029200" cy="2828925"', 4),
    (b'cx="5257800" cy="2988644"', b'cx="5029200" cy="2858703"', 2),
    (b'cx="5257800" cy="2711918"', b'cx="5029200" cy="2594008"', 2),
]


def add_caption_spacing(document: bytes, caption: bytes) -> bytes:
    marker = b"<w:t>" + caption + b"</w:t>"
    marker_pos = document.find(marker)
    if marker_pos < 0:
        raise RuntimeError(f"Caption marker not found: {caption!r}")
    starts = [match.start() for match in re.finditer(rb"<w:p(?:\s|>)", document[:marker_pos])]
    paragraph_start = starts[-1] if starts else -1
    ppr_end = document.find(b"</w:pPr>", paragraph_start, marker_pos)
    if paragraph_start < 0 or ppr_end < 0:
        raise RuntimeError(f"Caption paragraph properties not found: {caption!r}")
    spacing = b'<w:spacing w:before="80"/>'
    if spacing in document[paragraph_start:marker_pos]:
        raise RuntimeError(f"Caption spacing already present: {caption!r}")
    return document[:ppr_end] + spacing + document[ppr_end:]


BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(DOCX, BACKUP)

with zipfile.ZipFile(DOCX, "r") as source_zip:
    members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

original = {info.filename: data for info, data in members}
updated = original[DOCUMENT_XML]

for old, new, expected_count in REPLACEMENTS:
    actual_count = updated.count(old)
    if actual_count != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} occurrences of {old!r}; found {actual_count}"
        )
    updated = updated.replace(old, new)

# These two charts have content close to the lower image edge. A small caption
# gap prevents the caption from visually touching the chart legend/axis label.
updated = add_caption_spacing(updated, b"Figure 4: Final diff latency from the audited CSV bundle; lower is better.")
updated = add_caption_spacing(updated, b"Figure 6: Fixed-trie sensitivity; the preferred point depends on the objective.")

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

os.replace(TEMP, DOCX)
print(f"Updated: {DOCX}")
print("Figures resized: 6")
print("Target width: 5.50 inches")
print("Caption spacing adjusted: Figures 4 and 6")
print("Changed package parts: word/document.xml only")
