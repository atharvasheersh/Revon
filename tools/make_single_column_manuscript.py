from pathlib import Path
import hashlib
import zipfile


SOURCE = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper.docx")
OUTPUT = Path(r"C:\Users\admin\Desktop\Revon\paper\Revon_Final_Research_Paper_Single_Column.docx")
DOCUMENT_XML = "word/document.xml"

OLD = b'<w:cols w:num="2" w:space="346" w:equalWidth="1"/>'
NEW = b'<w:cols w:num="1" w:space="346" w:equalWidth="1"/>'


with zipfile.ZipFile(SOURCE, "r") as source_zip:
    members = [(info, source_zip.read(info.filename)) for info in source_zip.infolist()]

original = {info.filename: data for info, data in members}
document = original[DOCUMENT_XML]

count = document.count(OLD)
if count != 1:
    raise RuntimeError(f"Expected exactly one two-column section setting; found {count}")

updated_document = document.replace(OLD, NEW, 1)

with zipfile.ZipFile(OUTPUT, "w") as output_zip:
    for info, data in members:
        output_zip.writestr(info, updated_document if info.filename == DOCUMENT_XML else data)

with zipfile.ZipFile(OUTPUT, "r") as revised_zip:
    revised = {info.filename: revised_zip.read(info.filename) for info in revised_zip.infolist()}

if list(original) != list(revised):
    raise RuntimeError("DOCX package member order or membership changed")

unexpected = []
for name, original_data in original.items():
    revised_data = revised[name]
    if name == DOCUMENT_XML:
        if revised_data != updated_document:
            unexpected.append(name)
    elif hashlib.sha256(original_data).digest() != hashlib.sha256(revised_data).digest():
        unexpected.append(name)

if unexpected:
    raise RuntimeError(f"Unexpected package changes: {unexpected}")

if len(updated_document) != len(document):
    raise RuntimeError("Document XML length changed unexpectedly")

diff_positions = [i for i, (a, b) in enumerate(zip(document, updated_document)) if a != b]
if len(diff_positions) != 1:
    raise RuntimeError(f"Expected one byte-level XML change; found {len(diff_positions)}")

print(f"Created: {OUTPUT}")
print("Changed package parts: word/document.xml only")
print("Changed XML bytes: 1")
print("Column setting: 2 -> 1")
