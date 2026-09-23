from pathlib import Path
import hashlib
import os
import shutil
import zipfile


DOCX = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column.docx")
BACKUP = Path(r"C:\Users\admin\Desktop\Revon\.codex_tmp\Revon_Final_Research_Paper_Single_Column_before_figure_resize.docx")
TEMP = DOCX.with_suffix(".resizing.docx")
DOCUMENT_XML = "word/document.xml"

# Resize each inline figure from its two-column width to 5.75 inches while
# preserving its existing aspect ratio. Each extent appears once in wp:extent
# and once in the corresponding DrawingML transform.
REPLACEMENTS = [
    (b'cx="2706624" cy="1587886"', b'cx="5257800" cy="3084576"', 2),
    (b'cx="2706624" cy="1407444"', b'cx="5257800" cy="2734055"', 2),
    (b'cx="2706624" cy="1522476"', b'cx="5257800" cy="2957512"', 4),
    (b'cx="2578608" cy="1465735"', b'cx="5257800" cy="2988644"', 2),
    (b'cx="2706624" cy="1396048"', b'cx="5257800" cy="2711918"', 2),
]


BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(DOCX, BACKUP)

with zipfile.ZipFile(DOCX, "r") as source_zip:
    members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

original = {info.filename: data for info, data in members}
document = original[DOCUMENT_XML]
updated = document

for old, new, expected_count in REPLACEMENTS:
    actual_count = updated.count(old)
    if actual_count != expected_count:
        raise RuntimeError(
            f"Expected {expected_count} occurrences of {old!r}; found {actual_count}"
        )
    updated = updated.replace(old, new)

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

os.replace(TEMP, DOCX)
print(f"Updated: {DOCX}")
print("Figures resized: 6")
print("Target width: 5.75 inches")
print("Changed package parts: word/document.xml only")
