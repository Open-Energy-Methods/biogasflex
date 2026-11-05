# BiogasFlex v0.9.7 — observed hosted research-software verification

**Date:** 5 November 2026.
The complete [branch-push workflow 42052149427](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052149427)
and [matching pull-request workflow 42052216953](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052216953)
both finished successfully, each **10/10 jobs**, at reviewed scientific-code
commit `2f33bb9c71ad4adda12927f6ade3e0ab8958f46d`.

| Runner | Python version | Branch / PR |
|---|---|---|
| Ubuntu | 3.11 | PASS / PASS |
| Ubuntu | 3.12 | PASS / PASS |
| Ubuntu | 3.13 | PASS / PASS |
| macOS | 3.11 | PASS / PASS |
| macOS | 3.12 | PASS / PASS |
| macOS | 3.13 | PASS / PASS |
| Windows (PowerShell) | 3.11 | PASS / PASS |
| Windows (PowerShell) | 3.12 | PASS / PASS |
| Windows (PowerShell) | 3.13 | PASS / PASS |
| Ubuntu installed wheel outside checkout | 3.13 | PASS / PASS |

## Verified Ubuntu Python 3.12 reproduction

| Gate | Observed evidence |
|---|---:|
| Regression tests (including 13 new hourly + 3 CLI) | **224 PASS** |
| Original 216-case market LP primal-dual certificates | **216 PASS** |
| v0.9.3 original synthetic solver-free LP oracle comparisons | **96 PASS** |
| Frozen original research input/result file hashes | **286 unchanged** |
| Scientific-code snapshot SHA-256 distribution manifest | **415 file entries, PASS** |
| Git tracked release files, including manifest | **416** |
| Exact synthetic two-slot minimum ON 0.25h | **€45**, OFF→ON |
| Exact synthetic two-slot minimum ON 1.00h | **€45**, OFF→ON |
| Exact synthetic two-slot minimum ON 1.01h | **€40**, ON→ON |
| Synthetic minimum ON 1.26h, zero initial inventory | **infeasible, correctly rejected** |
| Initial OFF obligation 0.25h | **OFF, ON**, respected |
| Mixed-resolution synthetic day | **24h / 36 intervals** |
| Mixed day maximum gas balance residual | **5.551115123125783e-17 MWh_LHV** |
| Mixed day maximum steady-ON ramp violation | **2.636779683484747e-16 MW_e** |

The residuals are near machine floating-point roundoff
and below the declared numerical thresholds, **not** measured
equipment performance. All toy prices and CHP coefficients
are fabricated. The 36-slot day has 16 quarter-hour intervals
and 20 hour-long intervals, with 1.25h ON and 0.75h OFF
minimum dwell, not observed CHP unit commitment.

The exact solver-free oracle enumerates all four binary
sequences and feasible intermediate-stock endpoints for
a declared two-slot, zero-thermal CHP toy. It is exact
*only* for that limited geometry; no general
HiGHS-independent MILP verification is claimed.

The original 216 market cases and five hypothetical outage
case reproductions and both prior v0.9.5/v0.9.6 experimental
audits remain included in the full gate.

## SHA-256 manifest accounting

The successful workflows above checked **415** distributed
source/research files plus the manifest itself, 416 tracked
release files. Adding *this evidence record* adds one
new distribution file; the final count is **416 manifest
entries** and requires a fresh verification on the final
documentation commit before merger. No original frozen
research files were modified to create this matrix.

## Research status and remaining gaps

This is computational and mathematical software QA only.
There is no measured CHP startup or shutdown transient,
gas pressure/vessel capacity calibration, physical heat
demand, actual electricity-grid trading validation,
real financial profit, annual NPV, observed dispatch
or robust blackout/islanding result. The inferred
synthetic gains are NOT empirical operating gains.
Independent scientific human review is still open in
[GitHub issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No GitHub Release or Zenodo DOI is implied by CI success.
