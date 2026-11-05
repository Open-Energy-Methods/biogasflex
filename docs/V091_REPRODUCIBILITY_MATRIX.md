# v0.9.1 — Environment and reproducibility matrix

**Updated:** 5 November 2026, after the first successful hosted cross-platform CI run. This record separates prior local verification from GitHub-hosted reproduction.

| Environment | Status | Evidence / limitation |
|---|---|---|
| Linux x86-64, Python 3.13.5, SciPy 1.17.0, project source | **PASS — observed locally** | Complete `bash scripts/reproduce_v091.sh`, 155 tests and scientific audits |
| Fresh local Git checkout on Linux, Python 3.13.5 | **PASS — observed locally** | Cloned historical archive and verified checkout/manifests; this older local attempt preceded the new `.gitattributes` portability fix |
| Ubuntu hosted, Python 3.11, 3.12 and 3.13 | **PASS — observed hosted (3/3)** | Complete reproduction, frozen scientific checks, 216 market and five emergency cases |
| macOS hosted, Python 3.11, 3.12 and 3.13 | **PASS — observed hosted (3/3)** | Complete reproduction after filesystem-case-variant test was made platform-aware |
| Windows hosted, Python 3.11, 3.12 and 3.13 | **PASS — observed hosted (3/3)** | Full PowerShell reproduction with installed Windows `tzdata`, UTF-8 provenance reading and LF checkout policy for SHA-256 pinned scientific files |
| GitHub Actions installed-wheel smoke, Ubuntu Python 3.13 | **PASS — observed hosted (1/1)** | Built wheel; installed dependencies into separate environment; smoke-tested CLI, installed metadata and HiGHS outside checkout |
| Original local wheel/sdist build | **PASS — qualified locally** | Separate local wheel environment borrowed preinstalled SciPy; this qualification is independent of the newer hosted wheel test |
| Fully disconnected fresh dependency installation | **NOT TESTED** | Hosted `pip install` obtains dependencies from online package indexes before the offline reproduction; full offline installation from a prepopulated wheelhouse is not claimed |
| Independent human scientific review, plant observation/black start and techno-economic validation | **NOT TESTED** | These are separate scientific, operational and governance gates |

## Primary GitHub evidence

- [Successful pull-request workflow: 10/10 jobs](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029027186) on commit `b881eecf59e42b13f1720ed93de19753164b70b3`.
- [Successful branch-push workflow: 10/10 jobs](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029018461) on the same commit.
- [Repair pull request #1](https://github.com/Open-Energy-Methods/biogasflex/pull/1), scoped to packaging/tests, Git LF policy, manifests and documentation.
- Final documented source tree after the LF policy addition had **358 Git-tracked release files** including `SHA256SUMS.txt`, with **357 hashed manifest entries**. Additional documentation changes on this PR must update manifest entries and pass CI again.

**Scope of success:** The hosted workflow installs software dependencies with network access, then runs the scientific tests and audits against included data without network requests. All 155 unit tests and the reproduced 216 + 5 cases were exercised by the full reproduction entry point. Inherited scientific hashes remain pinned to the original v0.9 research candidate. No probability/annual-profit/real plant resilience/field-validation or external review claim follows from green CI.
