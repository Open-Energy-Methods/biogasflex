# BiogasFlex v0.9.2 — hosted reproducibility evidence

**Date:** 5 November 2026. This matrix records an observed GitHub Actions
development-branch run, not an independently replicated laboratory study.

| Hosted environment | Python versions | Gate status |
|---|---|---|
| Ubuntu Linux | 3.11, 3.12, 3.13 | **PASS (3/3)** |
| macOS | 3.11, 3.12, 3.13 | **PASS (3/3)** |
| Windows PowerShell | 3.11, 3.12, 3.13 | **PASS (3/3)** |
| Ubuntu built-wheel installation | 3.13 | **PASS (1/1)** |

**Observed source:** [GitHub Actions run 42034376782](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42034376782) for branch commit
`2310e0ae155995a27004c91da942391db3004469`. All ten jobs
completed successfully. The dedicated v0.9.2 environment verifier and documentation changes
subsequently passed all ten hosted jobs in [run 42034834791](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42034834791)
on commit `1513772d3a876f749aa129ae80849557e0d9d5cb`.

## Core checks observed on Linux Python 3.12

- **163 automated tests passed:** 155 inherited plus eight new v0.9.2
  dual-bound and adversarial tests.
- **216 of 216 saved market dispatch cases:** independently assembled
  primal/dual certification passed.
- **Maximum absolute duality gap:** €4.263256414560601e-13.
- **Maximum primal equality residual:** 1.1102230246251565e-16
  in the mixed constraint units; do not treat it as a physical uncertainty.
- **Maximum dual constraint violation:** 5.329070518200751e-15.
- **286 unchanged frozen original research files:** SHA-256 checks passed.
- **363 manifest-listed distribution files** verified in that observed
  snapshot (364 tracked files including the manifest).
- Inherited source, saved-output and clean-scratch audits successfully
  re-evaluated 216 market and five *hypothetical* interruption cases.

These numbers are numerical-computation residuals, not confidence intervals,
experimental error bars, or external review evidence. Dual and primal
implementations use the **same HiGHS backend**. Their mathematical model
excludes observed hourly plant operation, validated heat demand, startup and
ramp constraints, physical storage vessel design, market participation,
CAPEX/NPV, and verified islanding/black-start capacity.

The Python package may download dependencies from the package index.
Once installed, the supplied offline tests and research data need no external
network fetch. Do not claim fully disconnected fresh dependency installation.

No GitHub Release, DOI, or peer-reviewed manuscript has been published here.
