# BiogasFlex v0.9.8 — internal synthetic rolling-price study audit

**Prepared:** 5 November 2026. **Status:** software
development candidate pending CI and independent human
methodological review. No actual CHP operation measured.

## Scope and freeze

A new **opt-in** module implements receding-horizon CHP
mixed-integer commitment using a supplied triangular matrix
of assumed forecast electricity prices. The original
v0.7 heat-aware dispatch, v0.9.5 ramp surrogate,
v0.9.6 on/off commitment and v0.9.7 clock-hour
commitment source all remain unchanged. Original 286
scientific input and result pins are not modified.

## Audit plan and independent oracles

1. Full remaining-horizon mixed-integer solve at every
   interval; only the first control action is executed.
2. Carry forward actual gas inventory, ON/OFF, output
   midpoint observation age, and residual minimum dwell.
3. Explicit original terminal gas target is held fixed
   despite updated initial inventory every replan.
   No false cyclic stock reset.
4. An independent end-to-end physical ledger recalculates
   gas supply, flaring, losses, used gas, storage
   change, electric/heat generation, aux/dump heat,
   cost and startup/shutdown charges from *executed* controls.
5. Correct matched-boundary continuous LP relaxation
   provides an upper bound on MILP objective even
   for noncyclic rolling suffixes.
6. Reconcile ex-post actual step contribution to full
   realized physical ledger, then compare against
   same-constraints full perfect foresight; regret
   must be nonnegative within strict numeric tolerance.
7. Independent two-slot analytic price reversal: €40
   executed vs €60 hindsight, €20 regret, with
   no phantom borrowing from future gas inflow.
8. Independent three-slot analytical source/storage
   calculation: revised forecast €70, stale €60,
   full hindsight €80; revised regret €10 and stale €20.
9. Forced [ON,OFF,ON] synthetic gas supply audit:
   one actual €5 start and one €2 stop, €33 net
   at final synthetic €100/MWh_e spot price.
10. Invalid forecast windows, price/time mismatches,
    nonfinite inputs, negative prices, noncyclic
    target and initial inventory validation fail closed.
11. Original 286 hashes, 216+5 results, all 216
    dual certificates and old solver-independent
    tests remain part of every Linux/macOS/Windows run.

## Required release-engineering conditions

- Expected **242 passing unit tests**: prior 224 plus
  new 15 rolling scientific tests and three CLI tests.
- Reproduce all inherited historical tests, dual bounds,
  96 solver-free synthetic v0.9.3 oracles, and
  v0.9.5/v0.9.6/v0.9.7 experiments.
- Full distribution SHA256 manifest and Git tracked
  coverage, with original 286 scientific hashes unchanged.
- GitHub Actions 10/10 successful: Ubuntu/macOS/Windows,
  Python 3.11/3.12/3.13, and clean installed-wheel smoke.
- Record numerical outcome, scientific boundary and
  outstanding human review before merging.

## Explicitly missing engineering validity

No actual price-forecast model, electricity forecast
errors derived from data, random scenario probabilities,
price settlement, weather/heat/fuel disturbance,
stochastic MPC, engine startup dynamics, pressure
constraints, electrical network safety/exports,
real operating costs, CAPEX/NPV, islanding/black start
or independent scientific review. Issue #3 remains
unresolved; a public Release or Zenodo DOI is not
automatically justified by internal CI.
