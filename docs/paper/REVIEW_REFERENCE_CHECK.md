# Primary source checks for the review revision

Checked during the 2026-10-16 revision. This is a factual source audit, not a claim that every implementation has been independently benchmarked.

| Source | Primary evidence and supported use | Limits |
|---|---|---|
| Dolt storage architecture | https://www.dolthub.com/docs/architecture/storage-engine/ — Prolly Trees, Git-style commit graph, SQL tables, branching, merge and version diff | Documentation capabilities do not establish comparative engine speed; measured binary is Dolt 2.3.1 |
| ForkBase, PVLDB 2018 | https://www.vldb.org/pvldb/vol11/p1137-wang.pdf — POS-Tree/SIRI, content-addressed chunks, fork-on-demand/conflict, diff/three-way merge and extended key/value APIs | No ForkBase timing is collected here; do not infer absent general SQL support merely because this paper evaluates a lower-level API |
| Noms technical overview | https://github.com/attic-labs/noms/blob/master/doc/intro.md — history-independent content-addressed chunks, Prolly Trees and efficient diff/sync/merge over typed collections | A conceptual comparison; this revision does not run Noms |
| Git4Data preprint | https://arxiv.org/abs/2609.02106v1 — SQL extensions for snapshot/tag, branch, diff and merge, implemented in MatrixOne using immutable object storage and MVCC | Preprint claims and BranchBench results belong to that paper, not to Revon's experiment; its detailed implementation is not benchmarked here |
| UCI Wine Quality | https://archive.ics.uci.edu/dataset/186/wine+quality — red/white datasets, physicochemical fields, quality label, DOI 10.24432/C56S3T and CC BY 4.0 | Generated corrections are not specimen revision logs; keys use row ordinal |
| DataHub CO2 | https://github.com/datasets/co2-ppm and retained fixed-version `datapackage.json` — NOAA-derived monthly records and ODC-PDDL-1.0 | Published snapshot history includes an excluded header-only publication failure and unnamed trailing CSV fields; no atmospheric-science conclusions are inferred |
| Software Heritage | https://docs.softwareheritage.org/devel/swh-dataset/graph/dataset.html and https://docs.softwareheritage.org/devel/swh-export/graph/schema.html — graph export with content, directory and revision-history relations | Valid candidate for future sampled histories; bulk graph acquisition is unnecessary for this bounded local revision; fork-event counts alone are inadequate |

The reviewer attachment contains numbered references without its own complete reference list. Those numbers are not imported into the manuscript bibliography. New claims use the primary sources above and preserve the manuscript's citation identities when renumbered.
