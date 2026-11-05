# BiogasFlex v0.9.6 — observed hosted software reproducibility

**Date:** 5 November 2026.
The complete [GitHub Actions branch workflow 42046779132](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42046779132)
passed **10 of 10 jobs** at commit
`8f2cc250f29ca6322f711468a8d9164311122a23`.

| Hosted system | Python runtime | Result |
|---|---|---|
| Ubuntu | 3.11 | PASS |
| Ubuntu | 3.12 | PASS |
| Ubuntu | 3.13 | PASS |
| macOS | 3.11 | PASS |
| macOS | 3.12 | PASS |
| macOS | 3.13 | PASS |
| Windows PowerShell | 3.11 | PASS |
| Windows PowerShell | 3.12 | PASS |
| Windows PowerShell | 3.13 | PASS |
| Ubuntu installed wheel, outside checkout | 3.13 | PASS |

## Observed numerical checks (Ubuntu Python 3.12)

| Gate | Verified result |
|---|---:|
| Automated regression tests | **208 passed** |
| Original market-case primal/dual certificates | **216 passed** |
| Inherited v0.9.3 synthetic solver-free LP comparisons | **96 passed** |
| Original frozen scientific-file hashes | **286 byte-identical** |
| Snapshot strict distribution SHA-256 manifest | **402 files passed** |
| Git-tracked release files including manifest | **403** |
| Synthetic three-hour minimum-up period 1 | **€55 net** |
| Synthetic three-hour minimum-up period 2 | **€35 net** |
| Synthetic three-hour minimum-up period 3 | **€15 net** |
| Synthetic 24-hour gas conservation residual | **0 MWh_LHV** |
| Synthetic 24-hour steady-on ramp violation | **0 MW_e** |

The three-hour synthetic minimum-up results exactly match an
independently implemented pure-Python exhaustive half-MW_LHV
fuel-grid enumeration, which is exact for the specially constructed
toy geometry but **not** an independent general MILP solver.

The 24-hour synthetic test uses two-interval minimum up/down
constraints and assumed steady-on ramp limits. It is not historical
plant operation. Independently checked gas conservation and
instantaneous heat service match the underlying CHP model.

All original 216 market and five hypothetical outage cases were
recomputed using the inherited verification pipeline. The original
286 protected scientific files, original source inputs and outcomes
were not edited.

**Snapshot note:** The manifest had 402 entries during the green
run above. This matrix itself is a new additional distribution file
that increases the final manifest count to **403**, requiring a
subsequent full CI verification of the final commit.

## Scientific limits

This verifies the internal consistency of a binary on/off mathematical
model with assumed operating thresholds, costs and event
transitions. It provides no measured startup/stop transient,
calibrated CHP ramp capability, gas-vessel mechanics, electrical
grid/export permission, realistic forecast error, site annual
profits, CAPEX/NPV, islanding or blackstart capability.
No general independent 24-hour MILP proof or external human
scientific methodological review has occurred.

External review remains open in
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
This is development verification, not a public release or DOI.
