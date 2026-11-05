# BiogasFlex v0.9.5 — Hosted computational verification evidence

**Date:** 5 November 2026. The [GitHub Actions branch run 42042375641](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42042375641)
completed **10/10 PASS** at commit
`d73dff74db8228ffb0dba3abf6ec1c3d2f494471`.
This is CI-backed *software verification*, not independent scientific peer
review or measured CHP operating validation.

| Hosted system | Python | Result |
|---|---|---|
| Ubuntu | 3.11 | PASS |
| Ubuntu | 3.12 | PASS |
| Ubuntu | 3.13 | PASS |
| macOS | 3.11 | PASS |
| macOS | 3.12 | PASS |
| macOS | 3.13 | PASS |
| Windows (PowerShell) | 3.11 | PASS |
| Windows (PowerShell) | 3.12 | PASS |
| Windows (PowerShell) | 3.13 | PASS |
| Ubuntu installed wheel outside checkout | 3.13 | PASS |

## Observed numerical contracts, Ubuntu Python 3.12

| Computational gate | Observed result |
|---|---:|
| Regression tests, including 18 new experimental tests | **192 PASS** |
| Original market cases with v0.9.2 dual certificates | **216 PASS** |
| v0.9.3 two-interval solver-free synthetic comparisons | **96 PASS** |
| Original frozen scientific files | **286 byte-identical** |
| Branch-snapshot distribution manifest | **389 entries PASS** |
| Git-tracked files including checksum manifest | **390** |
| Synthetic 24-hour midpoint ramp violation | **0 MW_e** |
| Synthetic forecast reversal, loose ramp | **€20 regret** |
| Synthetic forecast reversal, 0.1 MW_e/h ramp | **€5 regret** |
| Realized forecast-plan increment over fixed baseline | **€0** |

### Toy ramp sensitivity

The entirely synthetic 2-hour scenario uses zero starting gas
inventory, 1 MW_LHV/hour fixed supply, 0.4 electric efficiency, a
0.5 MWh_LHV gas store, and prices €0 then €100/MWh_e.

| Ramp limit (MW_e/h) | Incremental modeled contribution |
|---:|---:|
| 0 | €0 |
| 0.05 | €2.50 |
| 0.10 | €5 |
| 0.20 | €10 |
| 100 (nonbinding) | €20 |

With a nonbinding ramp, tightening the continuously-on minimum
power from 0 to 0.20 then 0.36 MW_e produced €20, €20 and €4 of
modeled increment respectively, verifying nonincreasing value as the
feasible dispatch set shrinks.

The separate 24-interval synthetic stress reported
`max_ramp_violation_mw_e=0.0` and validated gas stock conservation.

## Corrected gas-inventory reasoning

The initial reversal-regret estimate incorrectly allowed using fuel
not yet generated. Because the toy gas stock starts at **zero**, the
forecast cannot advance gas production to a first-hour high-price
interval: the stock balance prohibits it. CI exposed this faulty
hand calculation, and the expected regret was corrected to the
above €20/€5 values before this successful workflow. The frozen
scientific computations were not changed.

The 389-manifest count corresponds to the run referenced above.
Adding this documentation creates a new entry and requires its own
full re-verification before merge.

## Scientific and operational limitations

- The CHP is **always on**, with continuous minimum-output and
  midpoint ramp constraints. There is **no** integer on/off commitment,
  start cost, min up/down time, fuel-vessel dynamic, or measured plant
  equipment limit.
- All new cases/prices are made up. No actual day-ahead forecast or
  operational dispatch is demonstrated.
- The original three 2020 market observations and 2022 Lövsta
  annual plant reference remain unchanged. No annual profit,
  representativeness, CAPEX/NPV, verified thermal service or real
  islanding capability is established.
- The external human scientific review is still open in
  [issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
  A public GitHub Release or DOI is not justified by this QA alone.
