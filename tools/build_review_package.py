"""Package the local revision without changing frozen collections or Linux ZIP."""
from pathlib import Path
import hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'paper/Revon_Review_Revision_Reproducibility_20261016.zip'
FIGURE_NAMES=('Fig2.svg','Fig2.png')+tuple(f'Fig{number}.{suffix}' for number in (8,9,10) for suffix in ('pdf','png'))
FIGURE_DIRECTORY='paper/review-assets/figures'

def required_assets(root=ROOT):
    paths=[root/FIGURE_DIRECTORY/name for name in FIGURE_NAMES]
    missing=[p.relative_to(root).as_posix() for p in paths if not p.is_file()]
    if missing:raise FileNotFoundError('required publication figure missing: '+', '.join(missing))
    return paths

def build(root=ROOT,target=None):
    target=target or root/'paper'/TARGET.name
    # Explicit membership must fail before writing a partial archive. Never glob
    # an ignored output directory whose absence would silently lose figures.
    assets=required_assets(root)
    paths=set()
    for directory in ['evidence/review-revision-20261016','evidence/selector-cost-20261016','evidence/linux-validation-20261008','evidence/linux-final-supplement-20261008','tools/publication_assets']:
        paths.update(p for p in (root/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for directory in ['docs/paper','docs/experiments','tests','tools/tests','experiments','examples','revon_api']:
        paths.update(p for p in (root/directory).glob('*') if p.is_file() and p.suffix in ['.py','.md'] and p.name not in {'REVISION_VERIFICATION_REPORT.md','ALL_21_ISSUES_RECHECK.md'})
    names=['README.md','LICENSE','requirements-publication.txt','requirements.txt','requirements-test.txt',
      'versioned_db.py','sqlite_store.py','experiments/__init__.py','experiments/adapters.py','experiments/workloads.py',
      'experiments/threshold_validation.py','experiments/review_revision.py','experiments/review_revision_data.py',
      'experiments/selector_cost.py','experiments/analyze_review_revision.py',
      'tools/check_review_campaign.py','tools/check_review_manuscript.py','tools/check_selector_cost.py',
      'tools/check_review_package.py','tools/check_final_paper.py','tools/check_springer_paper.py',
      'tools/check_review_baseline.py',
      'experiments/evidence_audit.py','experiments/paired_uncertainty.py',
      'tools/revise_review_manuscript.py','tools/render_review_manuscript.py','tools/render_review_qa.py',
      'tools/first_submission_editorial.py',
      'tools/freeze_review_publication.py','tools/build_review_package.py',
      'tools/publication_assets/selector_cost_source_20261016.py',
      'tools/render_docx_with_word.ps1','paper/README.md','paper/Revon_Review_Publication_Model_20261016.json',
      'paper/Revon_Linux_Reproducibility_Supplement.zip','paper/Revon Research Paper Springer Nature.docx','paper/Revon Research Paper Springer Nature.pdf',
      'paper/previous versions/review-baseline-20261016/Revon_Manuscript_Source.docx']
    paths.update(root/name for name in names)
    paths.add(root/'tests/test_data/.gitkeep')
    for form in ['IEEE','Discover_Computing']:
        for suffix in ['pdf','docx']:paths.add(root/f'paper/previous versions/Revon_Research_Paper_{form}.{suffix}')
    # Only reproducible publication inputs: no reviewer attachment, SSH material,
    # private cloud download, generated repository or hidden Git state.
    paths.update(assets)
    blobs={p.relative_to(root).as_posix():p.read_bytes() for p in sorted(paths)}
    hashes={n:hashlib.sha256(b).hexdigest() for n,b in blobs.items()}
    blobs['PACKAGE_SHA256SUMS.json']=json.dumps(hashes,indent=2).encode()
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for name,data in blobs.items():
            entry=zipfile.ZipInfo(name,date_time=(2026,10,16,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,data)
    print(json.dumps({'package':str(target),'entries':len(blobs),'bytes':target.stat().st_size},indent=2))

if __name__=='__main__':build()
