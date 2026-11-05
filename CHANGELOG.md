# v0.9.1 — 2026-11-05 — release-engineering increment (pre-v1.0)

- Carry forward all v0.9 model formulas, frozen scientific input data and 216+5 numerical results without recalibration or altered findings. Added 286-file inherited scientific SHA-256 pin set.
- Correct `.gitignore` to track the existing CC BY 4.0 historical market file `data/external/svk_se3_20200101.csv` rather than silently excluding a file required by the manifest.
- Harden `scripts/verify_v09_manifest.py`: reject traversal/absolute paths, duplicate entries, unsafe symlinks, mismatched hashes and unexpected distributed files; exclude only enumerated Git/cache/build metadata. Add adversarial unit tests.
- Add `scripts/verify_v091_git_coverage.py`: a real checkout must track exactly the release files. ZIP extractions report NOT_TESTED for Git coverage.
- Add `scripts/verify_v091_environment.py` and version/CLI/HiGHS checks; align metadata in `pyproject.toml`, `CITATION.cff`, and `src/biogasflex/__init__.py` to `0.9.1`.
- Add Linux/macOS Bash and Windows PowerShell v0.9.1 reproducibility scripts and configure multi-OS Python 3.11/3.12/3.13 GitHub Actions plus separate wheel-install smoke.
- Build wheel and sdist; document actual local environment and untested hosted runners truthfully. No GitHub release, Zenodo DOI, human peer review or physical validation.

---

# Changelog

## 0.9.0 — 2026-11-05 (pre-release scientific and reproducibility audit)

- Pinned hashes of the original v0.8 scenario registry, reference configuration and three attributed CC BY 4.0 Svenska kraftnät price snapshots.
- Introduced a standard-library strict input/scenario-identity validator independent of the optimization core; checks all 216 market case inputs, all five emergency case assumptions, fixed/optimized heat/gas/cost ledgers and study summary statistics.
- Added 21 analytical/adversarial tests and a clean isolated full recomputation across all 221 solved cases; 138 total regression tests.
- **Resolved major defect:** a claimed total gas supply interruption now rejects positive gas inflow rather than silently treating it as eligible.
- **Resolved metadata defect:** package version is 0.9.0; archived study/core JSON retains its original methodological version identifier.
- Added claims-to-evidence matrix, severity-tracked issue register, external reviewer questionnaire, citation metadata and SHA256-manifest verification.
- Updated GitHub Actions from obsolete v0.7 gates to the full v0.9 offline reproduction matrix (Python 3.11–3.13); ignore Git checkout metadata in archive integrity enumeration.
- **No new operating-price value, real plant validation, externally reviewed result, DOI, published GitHub release or verified black start is claimed.**

# BiogasFlex changelog

## 0.8.0 — Predeclared market sensitivity and hypothetical interruption service (2026-11-05)

- Preserved all v0.5–v0.7 code, tests, model and historical analysis outputs.
- Added a frozen, internally registered 216-configuration scenario matrix (three valid 2020 SE3 price windows × 72 hypothetical plant/heat/storage configurations) and its SHA-256 provenance.
- Retrieved additional Svk CC BY 4.0 SE3 April 1 and October 1, 2020 day-ahead price extracts. Preselected July 1 was **rejected for incomplete hourly sequence**, not interpolated or chosen again after looking at outcomes.
- Evaluated perfect-foresight incremental scenario contribution under price-window, heat demand, assumed backup cost, electrical efficiency, CHP rating and gas buffer changes. Saved **all 216 results**, including 120 zero-uplift cases; no a posteriori success-only filtering.
- Added five separate, synthetic gas-supply-interruption and critical-service cases with no grid input/backup heat, noncyclic precharged storage, and explicit hypothetical islanding/CHP availability gates. No observed outage or black-start claim.
- Added self-contained output ledger auditor, full-source market price matching, 36 new regressions including tamper detection and service bounds, 117 total passing tests.
- Added dated source/provenance documents, results and plots, v0.8 audit and model-boundary report, Windows/Unix repro scripts and optional emergency CLI.
- **No** plant calibration, human peer review, regional supply-security validation, probabilistic market inference, economic CAPEX/NPV, GitHub tag or Zenodo DOI is claimed.

## 0.7.0 and older

For original historical change records see the preserved v0.7 results, docs, and reports shipped unchanged in this package. Core heat-LP module retains its v0.7 version identity; v0.8 adds a separate orchestration/interpretation and emergency-service model.
