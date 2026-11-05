"""Confirm v0.9.1 preserves inherited scientific inputs, model core and outputs byte-for-byte."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT/'docs/V091_INHERITED_FROZEN_HASHES.json'

def verify(root: Path = ROOT) -> int:
    pins=json.loads((root/'docs/V091_INHERITED_FROZEN_HASHES.json').read_text(encoding='utf-8'))['files']
    for relative, expected in pins.items():
        path=root/relative
        if not path.is_file():
            raise ValueError(f'Inherited research file absent: {relative}')
        observed=hashlib.sha256(path.read_bytes()).hexdigest()
        if observed!=expected:
            raise ValueError(f'Inherited research file changed: {relative}')
    return len(pins)

if __name__=='__main__':
    try:
        n=verify()
    except (ValueError,OSError) as e:
        raise SystemExit(f'INHERITED RESEARCH FREEZE FAILED: {e}')
    print(f'INHERITED RESEARCH FREEZE PASS: {n} inherited scientific files unchanged from v0.9')
