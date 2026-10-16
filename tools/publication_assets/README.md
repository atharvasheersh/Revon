# Retained publication inputs

`reference_fonts/` and `reference_renderer_base.py` retain the selected document
layout and licensed font inputs. Rendering remains distinct from read-only
artifact verification; Word export is an optional Windows/Word QA step.

`selector_cost_source_20261016.py` is an exact byte copy of the original
post-campaign diagnostic script, preserved during the verification repair.
Its SHA-256 already appears in the unchanged diagnostic protocol under
`source_hashes["experiments/selector_cost.py"]`. It is provenance input, not a
new executed experiment. A Git attribute disables newline conversion for it.
The maintained checker validates this hash and the other archived dependencies,
then derives the expected function prefix from the main campaign's original
`versioned_db.py`. AST comparison ignores whitespace/comments/quote style but
requires the same signature, statements and expressions. No code from the
extracted prefix is executed during provenance checking.
