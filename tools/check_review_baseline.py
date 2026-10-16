"""Verify local pre-edit protected bytes after the review revision."""
from pathlib import Path
import argparse,hashlib,json

ROOT=Path(__file__).resolve().parents[1]

def check(root=ROOT,portable=False):
    baseline=json.loads((root/'evidence/review-revision-20261016/baseline.json').read_text())['protected_files']
    # The original inventory also captured local scratch repositories/bytecode.
    # Keep strict local verification as the default. Portable mode explicitly
    # omits only those incidental paths; sealed scientific files stay required.
    incidental={name for name in baseline if '__pycache__' in Path(name).parts or '.work' in Path(name).parts}
    protected={name:h for name,h in baseline.items() if not portable or name not in incidental}
    allowed={f'paper/Revon Research Paper Springer.{suffix}' for suffix in ['pdf','docx']}
    changed=[]
    for name,digest in protected.items():
        path=root/name
        if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:changed.append(name)
    if set(changed)!=allowed:raise ValueError('unexpected protected file changes: '+str(changed))
    for suffix in ['pdf','docx']:
        name=f'Revon Research Paper Springer.{suffix}'
        path=root/'paper/previous versions/review-baseline-20261016'/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=baseline['paper/'+name]:raise ValueError('baseline manuscript backup differs')
    return {'passed':True,'mode':'portable' if portable else 'strict local','protected_files':len(protected),'unchanged':len(protected)-2,'authorised_replacements':changed,'baseline_pair_preserved':True,'excluded_local_paths':sorted(incidental) if portable else []}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--portable',action='store_true',help='omit original inventory entries under __pycache__ or .work only')
    args=parser.parse_args();print(json.dumps(check(portable=args.portable),indent=2))
