"""Record a read-only baseline before the 2026-10-16 review revision."""
from pathlib import Path
from hashlib import sha256
import json,shutil,subprocess
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'evidence'/'review-revision-20261016'

def digest(path):
    h=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def main():
    OUT.mkdir(exist_ok=False)
    paths=[p for p in (ROOT/'evidence').rglob('*') if p.is_file() and OUT not in p.parents]
    paths += [ROOT/'paper'/'Revon Research Paper Springer.docx',ROOT/'paper'/'Revon Research Paper Springer.pdf',ROOT/'paper'/'Revon_Linux_Reproducibility_Supplement.zip']
    hashes={p.relative_to(ROOT).as_posix():digest(p) for p in sorted(paths)}
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'protected_files':hashes}
    (OUT/'baseline.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    backup=ROOT/'paper'/'previous versions'/'review-baseline-20261016';backup.mkdir()
    for suffix in ['docx','pdf']:
        shutil.copy2(ROOT/'paper'/f'Revon Research Paper Springer.{suffix}',backup/f'Revon Research Paper Springer.{suffix}')
    print(json.dumps({'protected_files':len(hashes),'baseline':str(OUT/'baseline.json')},indent=2))

if __name__=='__main__':main()
