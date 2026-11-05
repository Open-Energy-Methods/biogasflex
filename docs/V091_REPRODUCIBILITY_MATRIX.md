# v0.9.1 — Environment and reproducibility matrix

**As of:** 5 November 2026. Distinguish actual executions from configured expectations.

| Environment | Status | Evidence / limitation |
|---|---|---|
| Linux x86-64, Python 3.13.5, SciPy 1.17.0, project source | **PASS — observed** | `bash scripts/reproduce_v091.sh`, full unit tests and all audits (final-run log in release report) |
| Fresh local Git checkout on Linux, Python 3.13.5 | **PASS — observed** | Created a separate local Git repository, committed release files, cloned it into a new directory and ran the complete `reproduce_v091.sh` script successfully; 357 tracked release paths, 356 entries in the checksum manifest |
| Linux, Python 3.13.5, built `biogasflex-0.9.1` wheel | **PASS — qualified** | Install wheel in separate virtual environment; borrow preinstalled SciPy because no cached SciPy wheel was available for an entirely offline isolated environment. Test CLI/HiGHS from `/tmp` outside source tree |
| Linux, Python 3.11 / 3.12 | **NOT TESTED** | These interpreters are not present in this execution environment; configured for hosted CI |
| Windows, Python 3.11 / 3.12 / 3.13 | **NOT TESTED** | PowerShell script and three hosted jobs configured, but `pwsh` and Windows are not available locally |
| macOS, Python 3.11 / 3.12 / 3.13 | **NOT TESTED** | macOS CI jobs configured; macOS unavailable locally |
| GitHub Actions hosted CI | **NOT TESTED** | No GitHub repository push/workflow execution performed; a YAML file is not a green CI check |
| Fully independent virtual environment with SciPy installed from wheel cache | **NOT TESTED** | Offline SciPy wheel not available; standard PyPI install is intended for hosted CI |
| Python wheel and source distribution build | **PASS — observed** | `python -m pip wheel --no-deps --no-build-isolation` and `uv build --no-build-isolation`; does not constitute plant validation |

**Interpretation:** No claim of cross-platform validation, independent human review or operational plant validation. `pip install -e .` may use a network package index to acquire dependencies. **All scientific reproduction after dependency installation uses the included, source-attributed data offline**.
