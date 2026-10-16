# Revon revision verification report

Date: 16 October 2026. Workspace: `C:\Users\admin\Desktop\Revon`.

## Completion status

**Local revision complete for the requested bounded scope.** All three review
findings are fixed, 25 new regression tests pass, and the rebuilt final archive
passes the complete publication gate in both the local workspace and an
explicitly selected clean snapshot. The revision was committed and pushed to `atharvasheersh/Revon` as
`atharvasheersh`. All four GitHub Actions jobs passed for the published
artifact commit; the exact commit and run are recorded below. Author approval remains
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
frontend was unchanged and was not retested locally. Subsequent authorised
GitHub Actions ran its checks and Python 3.10/3.14 tests on Ubuntu, as recorded
below. Independent timing reproduction and journal submission are not claimed.

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

At completion of the verification repairs, all 1,925 remediation-baseline
protected files were unchanged. The later authorised title restoration changes
the current PDF/DOCX only; all 1,923 scientific/historical protected files,
including sealed collections, raw records, executed sources and the original
Linux ZIP, remain unchanged. All six moved figure files retain exact bytes.
The strict historical check separately confirms 1,327 unchanged baseline files,
the two earlier authorised manuscript replacements and exact original backups.

The reference PDF remains 27 pages, with 17 tables, 10 figures and 33 references.
The preceding revision inspected all 27 PDF pages and 28 Word-export pages.
For the later title restoration, both artifacts were rendered again: only the
two first-page images changed and were inspected at full size. The remaining
53 page images are byte-identical to their previously inspected versions.
Historical eleven tables and seven original figure assets retain their gates.
Word rendering is an optional separate QA step, not required for artifact checks.

## Final artifact identities

The final ZIP contains **1,477 manifested files**, plus its manifest,
and is **18,406,977 bytes**. This report is excluded from the ZIP
to avoid a circular ZIP/hash dependency. Final status documentation is written
after successful gates; it does not alter verified code, artifacts or evidence.

| Artifact under `paper/` | SHA-256 |
|---|---|
| Revon Research Paper Springer.pdf | `729e916a432f36fbca4af08a9e80edbd501855b6c7de49e47d9ba0be58ac9121` |
| Revon Research Paper Springer.docx | `bdf1f3a6bf180ae806577d260b5d96d96a7e8760f4e8929127f646e685eb34fb` |
| Revon_Review_Revision_Reproducibility_20261016.zip | `76f6f86639f5e870dcc48f9b2b6ad7915a2e3a95000b97d0ad03628536fadf38` |

## Publication and remaining research limits

Local revision: **complete**. Repository publication: **complete**.
Remote CI: **passed for published artifact commit `5f57bd2`**. Journal submission:
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
PDF/DOCX and figures retain their verified bytes. Remote CI completed successfully; details follow. Journal submission and corresponding-author approval
remain separate.

### Published commits and GitHub Actions

- `a4ffa56` — Add the frozen local review campaign and correctness controls
- `7855132` — Retain the complete review evidence and frozen experimental protocols
- `25ecfc8` — Publish the revised manuscript with portable evidence verification
- `daa8c37` — Document reviewer responses, claim boundaries and reproduction steps
- `5f57bd2` — Package the reproducibility revision and record verified artifact hashes

All five artifact/revision commits have author and committer `atharvasheersh`
with the verified GitHub noreply address. GitHub also associates their attribution
with that account. The remote `main` SHA matched the published local SHA, and
the remote archive blob matched the committed blob and its 18,413,793-byte size.
A direct Git-object check confirmed 621 frozen/artifact/source files retained
their exact working bytes after staging and committing.

[GitHub Actions run 38838041579](https://github.com/atharvasheersh/Revon/actions/runs/38838041579) completed successfully
for `5f57bd2f641577a0faa363aabb34c6d0ed3b9931`. Jobs:

- **Frontend: passed.**
- **Python 3.14: passed.**
- **Publication artifacts: passed.**
- **Python 3.10: passed.**

The hosted Python jobs do not install Dolt and skip native-Dolt tests when
unavailable; actual Dolt equivalence passed in the preceding local suites.
Hosted CI is artifact/unit verification, not a new timing reproduction.

This report-only follow-up records the completed publication. It is excluded
from the ZIP, so it changes no packaged input or artifact hash. Its own HEAD
workflow can be checked in the [main-branch Actions history](https://github.com/atharvasheersh/Revon/actions?query=branch%3Amain).
Whitespace checks accept preserved CRLF in frozen data and retain the third-party
GUST font licence verbatim; maintained source/document checks pass. The unrelated
untracked file was not added. Journal author approval remains outstanding.

## Author-requested title restoration

On 16 October 2026 the author requested the exact title **Revon: Log and Merkle
Differencing for Durable Structured Data Versioning**. The current source,
canonical PDF/DOCX, title metadata, publication model and documentation now
use that title. Historical documents and frozen experimental sources retain
their original titles. The reproducibility ZIP was rebuilt with the new pair.

Independent comparison with the preceding published pair confirms that only
the title paragraph changed: the other 188 paragraphs, all 17 tables, all 10
figure byte streams, references and section geometry are identical. Both
renderings retain their 27/28 page counts and zero replacement glyphs. The
two revised first pages were inspected; the other 53 page images are unchanged.
The preferred renderer could not find LibreOffice, so Word COM export supplied
the editable-document rendering. No scientific result or timing was changed.

The publication model was refreshed only after the title-only comparison;
its tables, figures, reference identities, citation mapping and analysis SHA
are unchanged. Full hosted verification for this title revision is available
in the [main-branch Actions history](https://github.com/atharvasheersh/Revon/actions?query=branch%3Amain).
Earlier run links above identify the earlier artifact commits explicitly.

Local verification of the title revision passed all 44 publication tests,
new-table numerical derivation and exact rebuilt-package correspondence.
All 1,922 baseline evidence files remain byte-identical.
