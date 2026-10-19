"""Apply reviewed prose only when the generated source still matches its inputs.

This layer changes no executed source or measured evidence. Its guards prevent
an editorial override from concealing a changed experiment or source paragraph.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / 'tools/publication_assets/first_submission_editorial.json'

# Exactly one historical metadata cell is reworded; all identifiers, data cells
# and other historical table text retain their independent baseline comparison.
HISTORICAL_CELL = (3, 6, 1,
    'linux-validation-20261008: archived repaired source, fixed before measurement',
    'linux-validation-20261008: executed source, fixed before measurement')


def historical_editorial_cells(table_number, cells):
    result = deepcopy(cells)
    table, row, col, old, new = HISTORICAL_CELL
    if table_number == table and len(result) > row and len(result[row]) > col:
        if result[row][col] == old:
            result[row][col] = new
    return result


def apply_editorial(doc, path=ASSET):
    spec = json.loads(Path(path).read_text(encoding='utf8'))
    if spec.get('schema') != 1:
        raise ValueError('unsupported first-submission editorial schema')
    paragraphs = list(doc.paragraphs)
    seen = set()
    # Complete preflight before mutating even one paragraph.
    for entry in spec['paragraphs']:
        index = entry['index']
        if index in seen or not 0 <= index < len(paragraphs):
            raise ValueError('duplicate or invalid editorial paragraph index')
        seen.add(index)
        original = paragraphs[index].text
        if original != entry['source_text'] or sha256(original.encode()).hexdigest() != entry['source_sha256']:
            raise ValueError(f'editorial input changed at source paragraph {index}')
        if not entry['text'].strip():
            raise ValueError('editorial replacement may not remove a paragraph')
    for entry in spec['table_edits']:
        cell = doc.tables[entry['table']-1].cell(entry['row'], entry['column'])
        if cell.text != entry['old']:
            raise ValueError(f'editorial table input changed at table {entry["table"]}')
    for entry in spec['paragraphs']:
        paragraphs[entry['index']].text = entry['text']
    for entry in spec['table_edits']:
        doc.tables[entry['table']-1].cell(entry['row'], entry['column']).text = entry['new']
    return {'paragraphs': len(spec['paragraphs']), 'table_text_cells': len(spec['table_edits']),
            'asset_sha256': sha256(Path(path).read_bytes()).hexdigest()}
