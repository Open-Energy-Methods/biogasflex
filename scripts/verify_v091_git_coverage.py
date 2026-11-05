"""Check all release-manifest paths actually exist in a tracked Git checkout.

A ZIP extraction has no Git metadata: reports NOT_TESTED rather than PASS.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess
from verify_v09_manifest import verify, ManifestFailure

def check(root: Path) -> dict:
    root = root.resolve()
    tracked = root/'.git'
    if not tracked.exists():
        return {'status': 'NOT_TESTED', 'reason': 'No Git metadata in ZIP/extracted directory'}
    n = verify(root)
    result = subprocess.run(['git','-C',str(root),'ls-files','-z','--cached'],
        text=False,capture_output=True,check=True,timeout=20)
    got = {name.decode('utf8') for name in result.stdout.split(b'\x00') if name}
    listed = set()
    for line in (root/'SHA256SUMS.txt').read_text(encoding='utf8').splitlines():
        listed.add(line.partition('  ')[2])
    expected = listed | {'SHA256SUMS.txt'}
    if expected != got:
        raise ManifestFailure(
            f'Git checkout and release manifest disagree: missing tracked {sorted(expected-got)}, '
            f'unexpected tracked {sorted(got-expected)}'
        )
    return {'status':'PASS','tracked_release_files':len(expected),'manifest_entries':n}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    args=p.parse_args()
    try:
        x=check(args.root)
    except (ManifestFailure,OSError,subprocess.CalledProcessError) as e:
        p.exit(1,f'GIT COVERAGE FAILED: {e}\n')
    print(x)
