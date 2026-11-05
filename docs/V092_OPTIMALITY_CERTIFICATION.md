# BiogasFlex v0.9.2 — Dual optimality and scientific scope

**Status:** development candidate. This increment adds independent mathematical
**formulation** of a dual upper bound for all 216 frozen market scenarios.
The unchanged primal heat-CHP solver and new dual verifier both use
SciPy/HiGHS, so this is **not a second solver implementation** or human peer review.

## Why a new verification gate?

The inherited v0.9 provenance, output-ledger and scratch-reproduction audits
establish traceability, physical-balance checks, and repeatable solver outputs.
These are not logically sufficient, by themselves, to prove a saved feasible
dispatch is optimal. v0.9.2 adds a weak-duality certificate.

## Formulation

For each hourly (or declared-duration) scenario, independently reconstruct
the bounded primal from the frozen saved input profile:

\[
\min_x c^T x,\qquad Ax=b,\qquad 0\le x\le u,
\]

where blocks of \(x\) are gas use, end gas inventory, useful CHP heat,
auxiliary heat and rejected heat. The coefficient \(c\) is negative
electricity contribution plus assumed marginal heat and variable costs.
The balance equations enforce gas inventory, co-produced heat, heat service
and cyclic terminal stock.

A dual that provides an **upper bound** on the *maximized*
economic-contribution proxy \(-c^Tx\) is

\[
\min_{y,z}\ b^Ty+u^Tz
\quad\text{subject to}\quad
-A^Ty-z\le c,\quad y\ \text{free},\quad z\ge0.
\]

When the primal flow and bounds are feasible and the independently
assembled dual is feasible, weak duality guarantees
\(-c^Tx\le b^Ty+u^Tz\). An approximately zero duality gap then
certifies optimality of the **mathematical model under the declared
assumptions**, to numerical tolerance. It does *not* establish plant realism.

## Gate contract

- All 216 frozen V08-S000..V08-S215 case records must be present.
- Check saved hourly gas stock continuity, every linear equality, lower and
  upper bounds, and reconstructed contribution from saved interval prices.
- Independently assemble and solve the dual, inspect dual feasibility,
  require absolute primal/dual gap at most €5×10⁻⁶ (with a small relative
  allowance for scaling).
- Negative tests tamper gas use, reported contribution, nameplate rating and
  market-price finiteness. A two-interval analytical heat-aware oracle has
  exactly **€8.25 modeled incremental contribution**.
- Preserve original 286 v0.9 frozen research-file SHA-256 pins, inherited
  216 market and five hypothetical outage results and source price snapshots.
- Run `bash scripts/reproduce_v092.sh` or
  `./scripts/reproduce_v092.ps1` after installation.
- The historical emergency cases are verified through inherited independent
  conservation and input-contract auditors, **not** this economic LP dual.

## Interpretation and limitations

The original primal and new dual are written as different mathematical
formulations but invoke the same SciPy/HiGHS library. Correlated numerical
implementation defects remain possible. No real plant operational trajectory,
heat telemetry, gas-vessel physics, startup/ramp limits, CAPEX/NPV,
black-start/islanding hardware, observed sales, annual market
representativeness or human peer review is established. The 96/216
positive cases are a finite-grid count, not a probability. The maximum
€15.7953 is a selected-day *conditional incremental contribution*, not
annual profit.

See [observed hosted reproducibility](V092_REPRODUCIBILITY_MATRIX.md) and [internal audit evidence](../reports/V092_OPTIMALITY_AUDIT.md).\n\nThis increment does **not** create a GitHub Release or Zenodo DOI.
