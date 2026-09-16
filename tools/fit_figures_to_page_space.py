from pathlib import Path
import hashlib
import os
import re
import shutil
import zipfile


DOCX = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column.docx")
OUTPUT = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column_Figure_Fit.docx")
BACKUP = Path(r"C:\Users\admin\Desktop\Revon\.codex_tmp\Revon_Final_Research_Paper_Single_Column_before_space_fit.docx")
TEMP = OUTPUT.with_suffix(".building.docx")
DOCUMENT_XML = "word/document.xml"

# Layout-aware sizes, in EMU, preserving each figure's original aspect ratio.
# Figures 3, 4, and 6 share pages with dense surrounding material, while
# Figure 5 has more vertical room and benefits from a slightly larger size.
TARGETS = [
    (5029200, 2950464),  # Figure 1: 5.50 in
    (5029200, 2615183),  # Figure 2: 5.50 in
    (4800600, 2700338),  # Figure 3: 5.25 in
    (4800600, 2728762),  # Figure 4: 5.25 in
    (5120640, 2641172),  # Figure 5: 5.60 in
    (4800600, 2700338),  # Figure 6: 5.25 in
]

INLINE_PATTERN = re.compile(rb"<wp:inline\b.*?</wp:inline>", re.DOTALL)
EXTENT_PATTERN = re.compile(rb'cx="\d+" cy="\d+"')


BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(DOCX, BACKUP)

with zipfile.ZipFile(DOCX, "r") as source_zip:
    members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

original = {info.filename: data for info, data in members}
document = original[DOCUMENT_XML]
inline_matches = list(INLINE_PATTERN.finditer(document))
if len(inline_matches) != len(TARGETS):
    raise RuntimeError(f"Expected {len(TARGETS)} inline figures; found {len(inline_matches)}")

parts = []
cursor = 0
for index, (match, (target_cx, target_cy)) in enumerate(zip(inline_matches, TARGETS), start=1):
    block = match.group(0)
    extents = list(EXTENT_PATTERN.finditer(block))
    if len(extents) != 2:
        raise RuntimeError(f"Figure {index}: expected two extent pairs; found {len(extents)}")
    replacement = f'cx="{target_cx}" cy="{target_cy}"'.encode("ascii")
    rebuilt = []
    block_cursor = 0
    for extent in extents:
        rebuilt.append(block[block_cursor:extent.start()])
        rebuilt.append(replacement)
        block_cursor = extent.end()
    rebuilt.append(block[block_cursor:])
    new_block = b"".join(rebuilt)
    parts.append(document[cursor:match.start()])
    parts.append(new_block)
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
    raise RuntimeError(f"Unexpected changes outside figure extents: {unexpected}")

os.replace(TEMP, OUTPUT)
print(f"Updated: {OUTPUT}")
print("Applied layout-aware widths to 6 figures")
print("Changed package parts: word/document.xml only")
