"""Adversarial release-engineering checks, independent of the SciPy optimizer."""
from __future__ import annotations
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('manifest_v091', ROOT/'scripts/verify_v09_manifest.py')
manifest = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(manifest)

class ManifestAdversarialTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='v091-integrity-')
        self.root = Path(self.tmp.name)
        self.src = self.root/'src'
        self.src.mkdir()
        (self.src/'module.py').write_text('print("model")\n', encoding='utf-8')
        self._seal()

    def tearDown(self):
        self.tmp.cleanup()

    def _seal(self):
        files = manifest.release_files(self.root)
        rows = []
        for name in sorted(files):
            rows.append(f'{hashlib.sha256((self.root/name).read_bytes()).hexdigest()}  {name}')
        (self.root/'SHA256SUMS.txt').write_text('\n'.join(rows)+'\n', encoding='utf-8')

    def _replace_entry(self, new_value):
        lines = (self.root/'SHA256SUMS.txt').read_text().splitlines()
        lines[0] = new_value
        (self.root/'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')

    def test_valid_manifest(self):
        self.assertEqual(manifest.verify(self.root),1)

    def test_modified_content_rejected(self):
        (self.src/'module.py').write_text('print("tampered")\n')
        with self.assertRaisesRegex(manifest.ManifestFailure, 'Checksum mismatch'):
            manifest.verify(self.root)

    def test_untracked_source_rejected(self):
        (self.src/'unexpected.json').write_text('{}')
        with self.assertRaisesRegex(manifest.ManifestFailure,'unrecorded'):
            manifest.verify(self.root)

    def test_missing_source_rejected(self):
        (self.src/'module.py').unlink()
        with self.assertRaisesRegex(manifest.ManifestFailure,'absent'):
            manifest.verify(self.root)

    def test_duplicate_manifest_entry_rejected(self):
        path=self.root/'SHA256SUMS.txt'
        path.write_text(path.read_text()*2)
        with self.assertRaisesRegex(manifest.ManifestFailure,'Duplicate'):
            manifest.verify(self.root)

    def test_parent_traversal_rejected(self):
        self._replace_entry('0'*64+'  ../other')
        with self.assertRaisesRegex(manifest.ManifestFailure,'Unsafe'):
            manifest.verify(self.root)

    def test_windows_traversal_rejected(self):
        self._replace_entry('0'*64+'  ..\\other')
        with self.assertRaisesRegex(manifest.ManifestFailure,'Unsafe'):
            manifest.verify(self.root)

    def test_absolute_path_rejected(self):
        self._replace_entry('0'*64+'  /tmp/outside')
        with self.assertRaisesRegex(manifest.ManifestFailure,'Unsafe'):
            manifest.verify(self.root)

    def test_python_cache_and_git_metadata_ignored(self):
        for path in ['.git/config','src/__pycache__/module.cpython-313.pyc','src/biogasflex.egg-info/PKG-INFO',
                     '.pytest_cache/v/cache','build/output.txt','dist/output.whl','src/.coverage']:
            file=self.root/path
            file.parent.mkdir(parents=True,exist_ok=True)
            file.write_text('generated')
        self.assertEqual(manifest.verify(self.root),1)

    def test_case_preserving_unlisted_file_rejected(self):
        alternate = self.src/'MODULE.py'
        alternate.write_text('unexpected', encoding='utf-8')
        # On case-insensitive filesystems, MODULE.py aliases module.py and is
        # a checksum mutation; on case-sensitive filesystems it is unlisted.
        if alternate.samefile(self.src/'module.py'):
            with self.assertRaisesRegex(manifest.ManifestFailure, 'Checksum mismatch'):
                manifest.verify(self.root)
        else:
            with self.assertRaisesRegex(manifest.ManifestFailure, 'unrecorded'):
                manifest.verify(self.root)

    def test_symlink_in_source_rejected(self):
        target=self.root/'README.md'
        target.write_text('external')
        self._seal()
        link=self.src/'alias.py'
        try:
            link.symlink_to(target)
        except (OSError,NotImplementedError):
            self.skipTest('Source symlink creation unavailable on platform')
        with self.assertRaisesRegex(manifest.ManifestFailure,'Symlink'):
            manifest.verify(self.root)

    def test_bad_hash_rejected(self):
        path=self.root/'SHA256SUMS.txt'
        path.write_text('f'*64+'  src/module.py\n')
        with self.assertRaisesRegex(manifest.ManifestFailure,'Checksum'):
            manifest.verify(self.root)

class VersionAndDocumentationTests(unittest.TestCase):
    def test_release_version_consistency(self):
        from biogasflex import __version__
        self.assertEqual(__version__, '0.9.7')
        self.assertIn('version = "0.9.7"',(ROOT/'pyproject.toml').read_text(encoding='utf-8'))
        self.assertIn('version: "0.9.7"',(ROOT/'CITATION.cff').read_text(encoding='utf-8'))

    def test_expected_release_scripts_exist(self):
        for name in ('reproduce_v091.sh','reproduce_v091.ps1','verify_v091_environment.py'):
            self.assertTrue((ROOT/'scripts'/name).is_file(),name)
        workflow=(ROOT/'.github/workflows/ci.yml').read_text(encoding='utf-8')
        for literal in ('windows-latest','macos-latest','ubuntu-latest','3.13','reproduce_v097.sh','reproduce_v097.ps1'):
            self.assertIn(literal,workflow)

if __name__ == '__main__':
    unittest.main()

class InheritedFreezeTests(unittest.TestCase):
    def test_inherited_files_match_original_v09(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('frozen_v091',ROOT/'scripts/verify_v091_inherited_frozen.py')
        frozen=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(frozen)
        self.assertGreaterEqual(frozen.verify(ROOT), 200)

    def test_gitignore_does_not_hide_licensed_input(self):
        text=(ROOT/'.gitignore').read_text(encoding='utf8')
        self.assertIn('!data/external/svk_se3_20200101.csv',text)

    def test_git_coverage_script_exists(self):
        self.assertTrue((ROOT/'scripts/verify_v091_git_coverage.py').is_file())
