# v0.9.1 — Release engineering and reproducibility audit

**Date:** 2026-11-05  
**Basis:** unchanged v0.9 research release-candidate ZIP and its original `SHA256SUMS.txt`.  
**Nature:** internal engineering audit and regression tests, not independent human review or plant validation.

## Scope

This increment changes installation metadata, CI workflow, manifest security, release scripts and audit documentation. It **does not introduce new scientific scenarios**, optimize different physics, alter assumptions or improve previously reported numerical outcomes.

## Specific repairs

1. **Checkout completeness:** the inherited `.gitignore` excluded `data/external/svk_se3_20200101.csv` despite its inclusion in the release manifest. The ignore rule is corrected, and the v0.9.1 checkout check requires all distributed files to be Git tracked. A local ZIP extraction has no Git metadata and therefore reports that part as NOT TESTED.
2. **Manifest integrity:** the verifier rejects traversal, absolute and Windows-style unsafe paths, case-colliding/untracked files, duplicate entries, missing or changed files, and symlinks. Known environment caches and packaging artifacts are explicitly excluded rather than suppressing arbitrary unknown paths.
3. **Package and CI:** Python package and citation versions are consistently 0.9.1. CI is configured for Linux, Windows and macOS on Python 3.11–3.13; a separate wheel installation job tests packaging. **No hosted CI workflow has been executed by this local audit**.
4. **Scientific preservation:** a new independently generated freeze list pins 286 unchanged original-v0.9 research files using SHA-256. Historical solver/result version labels remain unchanged; the current package version increases independently.

## Verification results

**Observed on Linux x86-64 / Python 3.13.5 / SciPy 1.17.0:**

| Gate | Result |
|---|---|
| Automated regression suite | **155/155 PASS** (138 inherited + 17 new release-engineering and security checks) |
| Recompute all market scenario outputs | **216/216 PASS** within prescribed 2×10⁻⁶ tolerance |
| Recompute all conditional emergency results | **5/5 PASS** |
| Independent v0.8 output-ledger audit | **PASS** |
| v0.9 frozen assumptions and input-provenance audit | **PASS**; reports historical audit version 0.9.0 by design |
| Frozen original-v0.9 scientific file checksums | **286/286 PASS** |
| Strict release manifest integrity | **356/356 PASS** in initial snapshot |
| Fresh local `git clone` and run full reproduction | **PASS** (357 tracked release files including manifest) |
| Wheel and sdist build with local installed build tools | **PASS** |
| Installed-wheel CLI and HiGHS smoke test | **PASS, qualified** (isolated package installation, borrowed preinstalled SciPy 1.17.0) |
| Actual hosted GitHub CI | **NOT TESTED** (workflow is configured only) |
| Windows PowerShell runtime / macOS | **NOT TESTED** (OS and PowerShell unavailable here) |
| Python 3.11 and 3.12 runtime | **NOT TESTED** (interpreters unavailable here) |

**Reproduction method:** the release files were committed into a temporary local Git repository, cloned to a separate directory, then `bash scripts/reproduce_v091.sh` was run in the clone. No authentication or live market/API access was involved. An additional Linux wheel smoke was executed outside the project source tree; this was not a from-scratch SciPy installation, since the offline runner lacks a cached SciPy wheel. The system-global `pip check` is affected by an unrelated MoviePy/Pillow dependency mismatch, so no unconditional full-environment dependency-health claim is made.

## Scientific findings preserved

- 216 predeclared market/assumption cases: 96 positive, 120 approximately zero conditional incremental electricity-and-heat-service contributions; maximum €15.7953 per selected day. These outcomes are not a probability, annual profit or representative Swedish plant result.
- Five hypothetical critical-service interruption cases, including negative control cases with CHP or islanding capability absent. These are conditional theoretical services, not demonstrated real resilience.
- The source-mixed Lövsta reference uses published 2022 annual plant quantities and observed 2020 SE3 price data. Hourly operational records, site heat telemetry and plant electricity exports are not available.

## Outstanding release issues

- Only local Linux Python 3.13 has executed; GitHub-hosted Windows/macOS and other Python versions require actual CI execution before claiming multi-platform reproduction.
- Full clean isolation from preinstalled SciPy cannot be demonstrated offline on this runner because its wheel is not cached. The installed-wheel smoke is qualified accordingly.
- Human technical peer review, real CHP validation, black-start and islanding hardware, techno-economic CAPEX/NPV and publication/DOI remain outside this increment.

## v0.9.1 decision boundary

This is a **release-engineering development increment**. It may be accepted for continued v0.9.x stabilization if clean-extraction reproducibility, local Git checkout coverage, manifest checks and inherited research audits pass. It does not authorize a v1.0 release on its own.

---

## GitHub-hosted verification addendum — 5 November 2026

The earlier `NOT TESTED` statements in this report describe the **pre-upload local-only audit**. They are superseded for cross-platform hosted CI by successful [PR run 42029027186](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029027186) and [branch run 42029018461](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029018461) at commit `b881eecf59e42b13f1720ed93de19753164b70b3`.

**Observed hosted result: 10/10 jobs PASS** — a 3 × 3 matrix (Ubuntu, macOS, Windows × Python 3.11–3.13) plus independent wheel-install smoke on Ubuntu/Python 3.13. Each matrix job runs the full 155-test suite and release scripts, recomputing 216 market cases and five synthetic interruption cases with the frozen input and output audits.

The initial workflow failures identified real cross-platform release-engineering defects:

1. macOS case-insensitive filesystems treated the adversarial `MODULE.py` variant as a checksum mutation rather than an extra unlisted file. The test now requires rejection for the platform-appropriate reason.
2. Windows `zoneinfo` lacked the `Europe/Stockholm` zone database: a conditional `tzdata` dependency now supplies it.
3. Windows default text encoding misread a Swedish attribution string: the test now explicitly reads UTF-8.
4. Windows Git checkouts changed line endings of SHA-256-frozen files despite clean source commits: `.gitattributes` fixes checkout text line endings to LF on all hosted OSes.

All fixes preserve the original 286 inherited research-file SHA-256 pins and the mathematical/scientific result records. The strict manifest is regenerated when metadata/tests/docs change. Green CI validates **software reproducibility in the tested hosted environments**, not independently reviewed physics, the representativeness of the three market-price days, real CHP dispatch or plant economics. No GitHub release or Zenodo deposit was created as part of this work.

For status by host, Python version and scope, consult `docs/V091_REPRODUCIBILITY_MATRIX.md`.
