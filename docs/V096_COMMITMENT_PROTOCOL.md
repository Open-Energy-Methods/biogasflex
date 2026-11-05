# BiogasFlex v0.9.6 — Binary on/off CHP commitment experiment

**Status:** prerelease research-code experiment. Not calibrated to any
CHP generator, gas vessel, grid interconnection, actual electricity
bidding strategy, or field operational dataset. This is **not** an
independent scientific review, engineering equipment guarantee,
public GitHub Release, DOI or publication.

## What changed

Version v0.9.5 used a **continuously on**, min-power-constrained LP.
That model could not decide whether to shut down or restart a CHP unit.
v0.9.6 introduces `src/biogasflex/experimental_v096.py`, an **explicitly
opt-in binary MILP**, instead of editing the frozen v0.7 source model
or reinterpreting the original 216 saved market scenarios.

For each time interval with duration `dt_t`, the new binary variables
are `y_t` (on), `z_t` (startup) and `v_t` (shutdown). Fuel use
`u_t` is MW_LHV; electrical output `P_t=eta_e*u_t` is MW_e.
All gas-production, storage balance, cyclic terminal stock,
instantaneous CHP heat conversion, heat rejection and auxiliary heat
service constraints are retained **exactly** from the original heat LP.

### On/off and transition accounting

```text
y_t ∈ {0,1}; z_t ∈ {0,1}; v_t ∈ {0,1}
minimum_on_power_mw_e * y_t <= eta_e * u_t <= rating_mw_e * y_t
z_t - v_t = y_t - y_(t-1)
z_t <= y_t,  z_t <= 1-y_(t-1)
v_t <= y_(t-1),  v_t <= 1-y_t
z_t + v_t <= 1
```

For `t=0`, `y_(t-1)` is the user-declared `initial_on` and
`initial_power_mw_e` is the output at the initial interval boundary.

When **both consecutive time intervals are on**, their midpoint
electrical outputs obey independently declared up/down ramp rates.
The elapsed time is `(dt_(t-1)+dt_t)/2`, or `dt_0/2` at the first
midpoint from the initial operating boundary.

**Crucial approximation:** startup and shutdown transitions are
*exempt* from these steady-on power ramps using a tight
`rated_power_mw_e` big-M envelope. Their physical transients are
not modeled. There is no startup fuel, ignition timing, thermal
mechanical stress, minimum pressure, power export, generator breaker,
or synchronized-grid behavior.

### Minimum up/down time

A startup must stay on for at least `minimum_up_intervals` entire
intervals; a shutdown must stay off for at least
`minimum_down_intervals` entire intervals. Both are **counts of
intervals**, not elapsed hours. The final horizon is treated
strictly: a startup or shutdown is forbidden unless its complete
minimum dwell fits within the modeled horizon.

**Initial boundary condition:** `initial_on` is the status at
the start of the horizon with **no pre-horizon unfulfilled dwell-time
obligation**. The on/off state *after* the final midpoint is not
otherwise specified; cyclic gas inventory is still enforced.

The objective maximizes modeled electricity contribution less assumed
auxiliary heat, dump and variable electric costs **and** fictional
per-event startup/shutdown charges. No observed CHP starting-cost
estimate is implied.

## Reference and mathematical safeguards

The inherited constant-stock, fixed-gas-use dispatch may **not**
satisfy a binary minimum-power or minimum-time constraint. Results
therefore always report whether the fixed reference is
`fixed_reference_feasible`. Its signed modeled uplift is included
**only when that reference is feasible**. Otherwise the field
`increment_over_feasible_fixed_eur` is `null`.

The original unconstrained heat-aware LP is still a mathematical
**upper bound** on the MILP net objective, because MILP operating
constraints can only shrink its feasible set and switching costs are
nonnegative. MILP output receives an independent gas/heat/contribution
ledger, checks exact integer transitions, min up/down times, initial
state, and steady-on ramp constraints. Nonoptimal or infeasible
problems fail, not silently replaced with zero returns.

### Synthetic three-hour numerical oracle

The fully invented toy scenario in `examples/v096_commitment_toy.json`
with made-up zero/zero/€100-MWh prices has:

- 0.5 MW_LHV/h fixed gas inflow, zero initial gas and a
  1 MWh_LHV gas buffer; terminal stock must be zero.
- 0.4 electrical efficiency, 0.8 MW_e nameplate, minimum-on
  output 0.2 MW_e, initially off.
- Hypothetical €5 per startup and €2 per shutdown. Directional
  ramps set sufficiently high to be nonbinding **while on**.
- Zero thermal CHP conversion and zero heat demand, deliberately
  isolating the gas and commitment mathematics from heat assumptions.

| Minimum continuous on-duration | Net modeled 3-hour contribution | Optimal on flags |
|---|---:|---|
| 1 interval | €55 | 0, 0, 1 |
| 2 intervals | €35 | 0, 1, 1 |
| 3 intervals | €15 | 1, 1, 1 |

A separate standard-library **exhaustive half-MW_LHV fuel-grid
enumeration** tests all feasible combinations in this particular
small fixture without calling the MILP solver. The constructed
geometry has its extreme points on that grid. The enumeration
does **not** independently prove all general LP/MILP cases.

In addition, the read-only audit generates a 24-interval **fully synthetic**\ncommitment horizon with two-interval minimum up/down dwell and\n0.2 MW_e/h assumed steady-on ramps. This checks conservation,\nfinite-horizon operation and ledger residuals, without introducing\nnew original research scenarios or field measurements.\n\nFurther adversarial cases test shutdown/restart costs, minimum
downtime-induced infeasibility, positive CHP heat conversion,
invalid initial state, impossible late starts, nonphysical numeric
inputs, and avoidance of false comparisons to a physically
infeasible fixed baseline.

## Reproduction

```bash
python -m pip install -e .
bash scripts/reproduce_v096.sh
python scripts/audit_v096_commitment.py
python -m biogasflex unit-commitment
```

Windows PowerShell: `./scripts/reproduce_v096.ps1`.

The new CLI writes **no files by default**. To save a full report,
supply `--output path.json`. The old `operating-surrogate`,
`forecast-regret`, `heat-dispatch` and `emergency-service`
commands are not replaced.

The complete inherited gates remain part of reproduction:
286 original frozen scientific-file hashes, 216 historical market
dual LP certificates, 216+5 original scenario reproductions, 96
solver-free two-interval synthetic tests, v0.9.5 operational/price
stress, environment/wheel smoke, strict full-tree SHA-256 manifest
and Git coverage.

Hosted CI evidence and exact numerical outcomes are recorded in\n[the v0.9.6 reproducibility matrix](V096_REPRODUCIBILITY_MATRIX.md).\n\n## Claims boundary and open research

The new MILP represents a *mathematical commitment surrogate*,
not CHP start physics or an empirically calibrated control model.
There are **no** measured physical ramp/start data, gas vessel
hydraulics, realistic CHP heat exchanger transients, electrical
interconnection or exports, forecast-error distributions, CAPEX/NPV,
real plant profit or guaranteed outage islanding.

The original three 2020 price windows, annual Lövsta reference
and all stored original scientific results remain frozen. The 216
market scenarios are not a probabilistic plant-operation sample.
Independent human review is still open in
[GitHub issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No public GitHub Release or Zenodo DOI follows automatically.
