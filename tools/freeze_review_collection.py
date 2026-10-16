"""Seal new evidence, never rewriting an already sealed collection."""
from pathlib import Path
import hashlib,json

ROOT=Path(__file__).resolve().parents[1]

def main():
    bundle=ROOT/'evidence/review-revision-20261016'
    target=bundle/'SHA256SUMS.json'
    if target.exists():raise FileExistsError('collection already sealed; verify instead of replacing it')
    hashes={p.relative_to(bundle).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
      for p in sorted(bundle.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p!=target}
    target.write_text(json.dumps(hashes,indent=2),encoding='utf8')
    print(f'Sealed {len(hashes)} collection files')

if __name__=='__main__':main()
