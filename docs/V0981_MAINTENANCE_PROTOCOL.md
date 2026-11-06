# BiogasFlex v0.9.8.1 — Rolling-state consistency patch

**Scope:** narrowly targeted reproducible maintenance patch to the
**existing opt-in, synthetic price-only v0.9.8 CHP on/off model**.
No additional modeled equipment physics, historical price forecasts,
new claims about profit/resilience, physical site validation, journal
review, GitHub Release or Zenodo deposit.

## Defect 1 — initial power-observation age overwritten

**Before:** The single-horizon v0.9.8 optimization correctly reads
`experimental_v098.initial_power_observation_age_hours`. The
rolling-horizon controller then replaced that initial value with
zero at **t=0** (while carrying `dt[t-1]/2` on subsequent steps).
This could turn a feasible first step into an infeasible MILP
under strict continuous-ON power ramp assumptions, or change
the first dispatch schedule and hindsight comparison.

**Now:** At **t=0** the original explicit declared observation age
is carried unmodified. For **t>0**, the observation remains
the preceding slot's half duration, representing the prior
slot midpoint observation. The previous v0.9.8 model and
physical midpoint ramp convention are unchanged.

**Independent one-slot oracle:** Initial electrical output
0.2 MW_e, forced next-slot output 0.4 MW_e, ramp limit
0.1 MW_e/h and declared initial observation age 2 h.
At a one-hour interval midpoint elapsed time is
2.0 + 0.5 = 2.5 h; permitted increase is 0.25 MW_e,
larger than the required 0.2 MW_e. Gas production is
1 MW_LHV, storage=0, eta_e=0.4, resulting in exactly
€40 fictional revenue at €100/MWh_e. Resetting age to
zero would incorrectly allow only 0.05 MW_e of increase.
This specific regression would fail under the old code.

## Defect 2 — physically invalid fixed comparator aborts feasible MILP

**Before:** v0.9.8 solved the optimal flexible model but
unconditionally called the **must-run fixed gas-use**
reference ledger. The inherited physical validator
correctly rejects references exceeding electrical
nameplate power, backup-heat capacity, dumped heat
capacity, etc. But the exception aborted the whole
**valid optimized flexible** result, even when the
flexible schedule's complete physical ledger passed.

**Now:** Only the optional fixed reference
`_fixed_scenario` is guarded against its own
`DispatchError` failure. The **optimized MILP
and all of its gas/heat, ramp, dwell, terminal and
matched-boundary LP-relaxation audits remain strict**.
When a reference is unavailable,
`fixed_reference_feasible=false`,
`fixed_reference_status="PHYSICALLY_INFEASIBLE"`,
`fixed_reference_net_contribution_eur=null`
and both incremental metrics are `null`.
The solver does not fabricate an uplift relative to
an invalid baseline. Where the arithmetic reference
is physically valid but operating constraints prevent
it, the existing non-null *descriptive* reference
remains, separately marked `COMMITMENT_INFEASIBLE`
or `DIFFERENT_TERMINAL_INVENTORY`.

**Independent gas oracle:** Two hourly slots with gas
production [3, 1] MW_LHV, storage capacity 1 MWh_LHV,
zero initial/final gas stock, electrical conversion
efficiency 0.4 and CHP nameplate 0.8 MW_e.
Fixed output in slot 1 would require
3×0.4 = **1.2 MW_e**, above nameplate.
Feasible optimized use is [2, 2] MW_LHV,
end-of-slot stock [1, 0] MWh_LHV and power
[0.8, 0.8] MW_e. At fictional prices
[€20, €50]/MWh_e this is
`0.8×20 + 0.8×50 = €56`, with
zero total storage or heat balance residual
and zero hindsight regret under perfect
synthetic forecasts. Fixed comparator is null.

**Additional heat comparator test:** A fully synthetic
two-slot case with initial/final stock 1 MWh_LHV,
production [0.25,1.75] MW_LHV and 0.3 MW_th
heat demand requires >0.1 MW_th auxiliary
capacity from the original fixed first-slot
output, but can be satisfied by optimized
variable dispatch drawing existing gas stock.
The invalid fixed heat reference must not
abort the feasible optimized heat service.

## Reproduce

```bash
python -m pip install -e .
bash scripts/reproduce_v0981.sh
python scripts/audit_v0981_maintenance.py
python -m biogasflex rolling-forecast
```

On Windows use `./scripts/reproduce_v0981.ps1`.

The full suite retains every inherited historical market
and original source/result freeze, 216 dual certificates,
96 independent LP comparisons, v0.9.5/v0.9.6/v0.9.7
experimental audits and the original v0.9.8 analytical
€70/€60/€80 and €20 regret toy oracles. Six new
maintenance tests bring the regression suite to
**248 expected passing tests**, pending hosted verification.

The model identifier intentionally remains
`receding_horizon_commitment_milp_v098` because these
corrections change neither the formulated model,
baseline gas/heat evidence nor assumptions. Only the
software package/report version advances to **0.9.8.1**.

Independent human scientific review remains open under
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No scientific v1.0, measured profit, or DOI is warranted
by CI alone.
