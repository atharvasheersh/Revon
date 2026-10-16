"""Check exact revision ZIP membership, bytes and correspondence with local files."""
from pathlib import Path,PurePosixPath
import hashlib,json,zipfile
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.build_review_package import FIGURE_DIRECTORY,FIGURE_NAMES,required_assets

ROOT=Path(__file__).resolve().parents[1]

def check(path=None,root=ROOT):
    path=path or root/'paper/Revon_Review_Revision_Reproducibility_20261016.zip'
    with zipfile.ZipFile(path) as archive:
        hashes=json.loads(archive.read('PACKAGE_SHA256SUMS.json'))
        if set(archive.namelist())!=set(hashes)|{'PACKAGE_SHA256SUMS.json'}:raise ValueError('review package membership mismatch')
        if len(archive.namelist())!=len(set(archive.namelist())):raise ValueError('review package duplicate path')
        expected_assets={FIGURE_DIRECTORY+'/'+name for name in FIGURE_NAMES}
        if not expected_assets.issubset(hashes):raise ValueError('review package required figure missing')
        if any(name.startswith('output/') or name.endswith('/ALL_21_ISSUES_RECHECK.md') for name in hashes):raise ValueError('review package contains local-only input')
        required_assets(root)
        for name,h in hashes.items():
            if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts:raise ValueError('unsafe package path')
            data=archive.read(name)
            if hashlib.sha256(data).hexdigest()!=h:raise ValueError('review package checksum mismatch: '+name)
            if not (root/name).is_file():raise ValueError('review package file missing from repository: '+name)
            actual=(root/name).read_bytes()
            # The ZIP preserves exact historical bytes. Git may normalise live
            # helper/docs line endings across Windows/Linux; only those files
            # permit CRLF/LF equivalence. Collected evidence and binary artifacts
            # remain strictly byte-for-byte, including their source snapshots.
            if not name.startswith('evidence/') and Path(name).suffix in ['.py','.md','.txt','.json','.ps1']:
                actual=actual.replace(b'\r\n',b'\n');data=data.replace(b'\r\n',b'\n')
            if actual!=data:raise ValueError('review package differs from repository: '+name)
    return {'passed':True,'files':len(hashes),'bytes':path.stat().st_size}

if __name__=='__main__':print(json.dumps(check(),indent=2))
