# Revon revision verification report

Date: 16 October 2026. Workspace: `C:\Users\admin\Desktop\Revon`.

## Completion status

**Local revision complete for the requested bounded scope.** All three review
findings are fixed, 25 new regression tests pass, and the rebuilt final archive
passes the complete publication gate in both the local workspace and an
explicitly selected clean snapshot. Git publication is now authorised as `atharvasheersh`; commit/push and
remote CI verification are being completed as a separate publication phase. Author approval remains
required before journal submission. Research limitations below remain open.

## Repairs completed in chronological order

1. Captured 1,925 protected file hashes and six figure hashes;
   reproduced all three failures on disposable copies before changing code.
2. Copied six exact figure assets to `paper/review-assets/figures/`; package
   construction now fails when any required figure is absent. Updated manuscript
   builder/replot instructions. Excluded the ignored local review document
   `ALL_21_ISSUES_RECHECK.md` and all output paths from package membership.
3. Independently recomputed calibration scores, minimizing threshold and exact
   tie-break from the 12 calibration cases only. Checked configurations, valid
   positive timings, seed separation and protocol/calibration/freeze/validation
   chronology. Relative score tolerance 1e-12, absolute zero; winner/tie exact.
   The actual retained scores match and T=65,536 remains the winner.
4. Validated five retained diagnostic source identities and compared the archived
   prefix AST with the prefix independently derived from archived production
   code. Preserved the original hash-matched benchmark script in publication
   assets with newline conversion disabled. Frozen collections are unchanged.
5. Added 25 isolated controls for the three defects and baseline portability.
   Altered/resigned calibration scores, incorrect winner/tie, invalid timing or
   chronology, missing configurations/assets, wrong prefix/source/history and
   incorrect batch accounting are rejected. Harmless prefix formatting passes.
6. Ran final local suites/audits; rebuilt the archive after code/docs settled.
7. Constructed the final clean snapshot and verified it in an isolated runtime.
8. Rechecked protected bytes, package membership, intended file selection and
   Git whitespace. No canonical manuscript regeneration was necessary.

## Actual final commands and results

Logs and machine-readable command manifests are under
`output/review_revision/remediation/`. Each `*-checks.json` records exact command,
root, exit status, elapsed time and log path. No benchmark campaign was rerun;
tests execute their own small temporary fixtures and the auditor regenerates
semantic histories without repeating timing observations.

| Check | Actual result | Local log |
|---|---|---|
| Final local: runtime | Passed; exit 0; 0.621 s | `final-local-runtime.log` |
| Final local: dolt | Passed; exit 0; 0.334 s | `final-local-dolt.log` |
| Final local: core | Passed; exit 0; 36.451 s | `final-local-core.log` |
| Final local: publication-tests | Passed; exit 0; 37.46 s | `final-local-publication-tests.log` |
| Final local: aggregate | Passed; exit 0; 245.963 s | `final-local-aggregate.log` |
| Final local: baseline | Passed; exit 0; 0.475 s | `final-local-baseline.log` |
| Final local: package | Passed; exit 0; 0.601 s | `final-local-package.log` |
| Final clean snapshot: runtime | Passed; exit 0; 0.718 s | `final-clean-runtime.log` |
| Final clean snapshot: dolt | Passed; exit 0; 0.259 s | `final-clean-dolt.log` |
| Final clean snapshot: core | Passed; exit 0; 66.908 s | `final-clean-core.log` |
| Final clean snapshot: publication-tests | Passed; exit 0; 51.384 s | `final-clean-publication-tests.log` |
| Final clean snapshot: baseline | Passed; exit 0; 9.756 s | `final-clean-baseline.log` |
| Final clean snapshot: package | Passed; exit 0; 0.828 s | `final-clean-package.log` |
| Final clean snapshot: aggregate | Passed; exit 0; 166.086 s | `final-clean-gate-aggregate.log` |

The local core suite used Python 3.14.3; local publication tooling used the
bundled Python 3.12.14 runtime. The clean snapshot used a new Python 3.14.3 venv
with `include-system-site-packages=false`. Both environments completed **79 core
tests and 44 publication tests, no skips**, including real local Dolt 2.3.1.
The publication suite includes the 25 new regression controls.

The final aggregate gate validates the historical IEEE/Discover formats, current
Springer PDF/DOCX content and geometry, original evidence/uncertainty/adverse
results, exact historical tables/figures, new numerical tables, all 93 campaign
cases / 3,402 queries / 2,646 measured queries, 594 collection hashes, independent
calibration, prefix provenance/accounting and final ZIP correspondence.
The diagnostic retains 18 histories and 252,000 measured prefix calls.

`git diff --check` passed; its CRLF conversion notices are warnings. The
frontend was unchanged and was not retested. No new Linux or Python 3.10 remote
CI run, independent timing reproduction or journal submission is claimed.

## Clean snapshot construction and dependencies

`create_snapshot.py` exported 1,481 existing versioned files
plus 675 explicitly allowed new revision files:
**2,156 files total**. It did not stage, commit or copy Git metadata.
The manifest lists every file and source/destination SHA-256. It excluded the
unrelated untracked file, ignored working output, local scratch repositories,
Python caches and private downloads. All required ZIP members were present.
Seventy ordinary live text files were LF-normalised to exercise checkout newline
portability; frozen evidence, binaries and explicit `-text` inputs retained bytes.

The final clean root is
`output/review_revision/remediation/clean_snapshot_final/`.
Selection and hashes are in `clean-snapshot-final-manifest.json`. Commands ran
with that root as their working directory and the isolated interpreter outside
the snapshot. Before testing, it contained no `output/` or `.git/` directory.
Tests may create their own temporary files afterward.

Installed the pinned `requirements-publication.txt` and `requirements-test.txt`
in the fresh environment and confirmed against the exact final snapshot copies.
`clean-dependency-install.json` records exit 0; `clean-dependency-install.log`,
`clean-environment-freeze.txt` and `clean-environment-pip-check.txt` record the
installation and eight installed packages. `pip check` found no broken
requirements. No Word, font installation, plot generation, TLC download or
historical machine-specific data directory was used for verification.

## Failure found during clean verification

The first clean attempt passed both suites but failed the optional historical
inventory check because its original manifest included **35 local scratch and
bytecode files**. The default checker remains strict and verifies all 1,329
inventoried files locally. Added explicit `--portable` mode excludes only
inventory paths under `.work` or `__pycache__`; it verifies the remaining 1,294
protected files and original manuscript backups. Three additional controls
verify this distinction and reject changed scientific evidence. No frozen
manifest was edited and no sealed collection check was disabled. A newly
constructed final snapshot passed every requested check with that mode.
The failed first attempt and intermediate runs remain in the local logs.

## Protected artifacts and layout

All 1,925 remediation-baseline protected files are unchanged,
including all sealed collections, raw records, executed sources, canonical PDF
and DOCX and original Linux ZIP. All six moved figure files retain exact bytes.
The strict historical check separately confirms 1,327 unchanged baseline files,
the two earlier authorised manuscript replacements and exact original backups.

The unchanged reference PDF remains 27 pages, with 17 tables, 10 figures and
33 references. The preceding revision visually inspected all 27 PDF pages and
all 28 Word-export pages; these manuscript byte hashes are identical. This
repair did not regenerate or claim a new visual inspection of those 55 pages.
Historical eleven tables and seven original figure assets retain their gates.
Word rendering is an optional separate QA step, not required for artifact checks.

## Final artifact identities

The final ZIP contains **1,477 manifested files**, plus its manifest,
and is **18,413,793 bytes**. This report is excluded from the ZIP
to avoid a circular ZIP/hash dependency. Final status documentation is written
after successful gates; it does not alter verified code, artifacts or evidence.

| Artifact under `paper/` | SHA-256 |
|---|---|
| Revon Research Paper Springer.pdf | `6f1fcf57b8480c23c9dc5ad79a40bb1637d6f9fe3fde79c1633e1cab397e4b9b` |
| Revon Research Paper Springer.docx | `7be3f7340fc79a43ffb495d13d152feaf30e753ff1049c617f2877a5293b5853` |
| Revon_Review_Revision_Reproducibility_20261016.zip | `465a47c354b7122690e49dd6251da3a9579b13a8847a7863c7c3c4b3a75599a4` |

## Publication and remaining research limits

Local revision: **complete**. Repository publication: **authorised and in progress**.
Remote CI: **pending the publication push**. Journal submission:
**pending author/corresponding-author approval**. The local verification phase did not change Git history; subsequent publication
uses the verified repository-local `atharvasheersh` identity. No cloud resources,
paid services, email or external submission were used.

The contribution remains incremental engineering and a bounded empirical study.
T=65,536 behaves as always-log in the primary matrix; adaptive switching benefit
and an optimal crossover remain unestablished. One Windows host, small seed
coverage, one observed publication sequence, generated histories, API/CLI
differences and whole-worker telemetry limit generality. These repairs add no
algorithmic novelty or independent-party reproduction. See the claim register,
skeptical audit and `REVIEW_REMEDIATION.md` for the precise research boundaries.

## Authorised publication phase

The user authorised commits and a push to `atharvasheersh/Revon` on
16 October 2026, with author and committer `atharvasheersh`
(`<171888881+atharvasheersh@users.noreply.github.com>`). This supersedes the
local-only Git scope of the preceding revision. Publication-status documentation
was updated and the ZIP rebuilt; experiment code, measurements, manuscript
PDF/DOCX and figures retain their verified bytes. Remote CI results will be
recorded after the push. Journal submission and corresponding-author approval
remain separate.
