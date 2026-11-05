"""Strict offline SHA-256 integrity check for a BiogasFlex release tree.

The manifest covers every distributed file except itself. A small allow-list
of environment-generated paths is ignored, to support both ZIP extractions
and normal Git checkouts without silently accepting unexpected source files.
This script requires only the Python standard library.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re

IGNORED_DIRS = frozenset({
    '.git', '.venv', '.tox', '.pytest_cache', '.mypy_cache', '.ruff_cache',
    '__pycache__', 'build', 'dist',
})
IGNORED_FILE_SUFFIXES = frozenset({'.pyc', '.pyo'})
IGNORED_FILES = frozenset({'.coverage', '.DS_Store'})
SHA_PATTERN = re.compile(r'^[0-9a-f]{64}$')

class ManifestFailure(ValueError):
    pass

def ignored(relative: Path) -> bool:
    parts = relative.parts
    return (
        any(part in IGNORED_DIRS or part.endswith('.egg-info') for part in parts[:-1])
        or relative.name in IGNORED_FILES
        or relative.suffix in IGNORED_FILE_SUFFIXES
    )

def release_files(root: Path) -> set[str]:
    found: set[str] = set()
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if ignored(rel):
            continue
        if path.is_symlink():
            raise ManifestFailure(f'Symlink in release tree is disallowed: {rel.as_posix()}')
        if path.is_file() and rel.as_posix() != 'SHA256SUMS.txt':
            found.add(rel.as_posix())
    return found

def validated_path(path_string: str) -> PurePosixPath:
    path = PurePosixPath(path_string)
    if (
        not path_string or '\\' in path_string or '//' in path_string
        or path.is_absolute() or path_string != path.as_posix()
        or any(part in {'.', '..'} for part in path_string.split('/'))
        or ignored(Path(*path.parts)) or path_string == 'SHA256SUMS.txt'
    ):
        raise ManifestFailure(f'Unsafe or excluded manifest path: {path_string!r}')
    return path

def verify(root: Path) -> int:
    root = root.resolve(strict=True)
    manifest = root / 'SHA256SUMS.txt'
    if not manifest.is_file() or manifest.is_symlink():
        raise ManifestFailure('SHA256SUMS.txt is missing or a symlink')
    entries: dict[str, str] = {}
    for line_num, line in enumerate(manifest.read_text(encoding='utf-8').splitlines(), start=1):
        digest, sep, relative = line.partition('  ')
        if not sep or not SHA_PATTERN.fullmatch(digest):
            raise ManifestFailure(f'Invalid SHA-256 entry on line {line_num}')
        name = validated_path(relative).as_posix()
        if name in entries:
            raise ManifestFailure(f'Duplicate manifest entry: {name}')
        entries[name] = digest
        file_path = root / name
        if not file_path.is_file() or file_path.is_symlink():
            raise ManifestFailure(f'Manifest target absent or symlink: {name}')
        observed = hashlib.sha256(file_path.read_bytes()).hexdigest()
        if observed != digest:
            raise ManifestFailure(f'Checksum mismatch: {name}')
    actual = release_files(root)
    if set(entries) != actual:
        raise ManifestFailure(
            f'Manifest paths mismatch: unrecorded={sorted(actual-set(entries))}, '
            f'missing={sorted(set(entries)-actual)}'
        )
    return len(entries)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        n = verify(args.root)
    except (ManifestFailure, OSError, UnicodeError) as exc:
        parser.exit(1, f'SHA256 CHECK FAILED: {exc}\n')
    print(f'SHA256 CHECK PASS: {n} distributed files, no omissions')

if __name__ == '__main__':
    main()
