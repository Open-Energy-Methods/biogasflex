# BiogasFlex v0.9.19 — Endogenous CHP flexibility, finite design and LP dual verification

**Scientific scope:** completely **synthetic** quarter-hour CHP dispatch research,
using the inherited, unchanged `experimental_v097` binary commitment MILP
and `experimental_v095` heat-constrained, always-on ramp LP. No actual
biogas equipment, compressor response, gas composition, gas vessel or
electricity orders are represented.

## Research questions

1. Can gas inventory and electricity-price variation create economically
   competing **on/off** schedules when the CHP commitment is **not**
   dictated by zero-storage gas-flow equality?
2. How do declared buffer capacity, external backup heat capacity and
   startup penalties affect the optimum, useful CHP heat fraction,
   backup heat reliance and start counts?
3. Can the computed original solution be checked by a **separately
   constructed** linear model with numerically verified primal and dual
   KKT arithmetic? For a small commitment horizon, can **every**
   binary pattern be independently enumerated to certify the global
   objective rather than trusting a single MILP run?
4. What limitations prevent these finite-design observations from
   becoming claims about equipment reliability or stochastic uncertainty?

The project already contains a **zero-buffer forced MILP with an
algebraically predetermined optimal switching pattern** (v0.9.18).
The present experiment has **positive buffer capacity** and continuous
fuel burn, so the optimizer can independently choose its operating
pattern when market prices vary. It is more difficult and scientifically
distinct from a unique solution induced by pulsating gas supply.

## Experimental design: 3 × 3 × 2 × 2 = 36 MILPs

| Quantity | Predeclared assumptions |
|---|---|
| Source | Constant 1 MW_LHV fictional fuel production |
| Generator | 0.8 MW_e rating, 0.4 assumed electric LHV efficiency |
| Thermal | 0.2 assumed thermal LHV efficiency, 0.15 MW_th instantaneous heat demand |
| Buffer capacity | **0, 0.5, 1.5 MWh_LHV** |
| Initial/terminal stock | Exactly 50% of each declared capacity |
| External heat capacity | **0 or 0.15 MW_th** |
| Startup cost | **€5 or €15 per modeled start** |
| Shutdown cost | €1 |
| First-period status | ON at 0.4 MW_e, no residual pre-horizon dwell |
| Operating limits | 0.2 MW_e minimum ON, 0.8 MW_e/h midpoint ramps, 0.5h min ON and OFF |
| Service and expense | 0.35 MW_th heat dump maximum; backup heat €6/MWh_th, heat dump €1/MWh_th, electric CHP variable cost €0.75/MWh_e |
| Time | 24 × 15min = **6 hours**, strictly UTC |
| Price sequences | **3 deterministic, deliberately selected illustrative patterns** with identifiers 11, 37, 83; NOT observed prices or random draws |

The economic objective is the model's hypothetical generator-terminal
electricity-price contribution **minus modeled CHP variable, heat
backup, dump and binary switching costs**. It is not actual
market settlement or net plant profit. Marginal backup/dump prices
are synthetic and no capacity CAPEX, gas procurement costs or
electricity transportation/auxiliary metering are included.

Every scenario uses the same six-hour base price sequence:

```text
hour 0–1:   5 EUR/MWh
hour 1–2.5: 120 EUR/MWh
hour 2.5–4: 15 EUR/MWh
hour 4–6:   110 EUR/MWh
```

A **predeclared integer arithmetic offset** depending on seed,
quarter-hour index and four-quarter block adds ±4 EUR/MWh. This
makes a small, **nonprobabilistic finite set of different inputs**.
No real price uncertainty distribution, forecasting algorithm or
stochastic confidence interval is inferred from three labels.

The two heat capacities represent **different hypothetical equipment
configurations**. Because the optimizer exactly enforces every interval's
thermal service (using CHP heat or backup), any feasible schedule has
**100% modeled heat service**. The useful heat share, backup energy and
number of starts are indicators of *operational dependence* and
modeled cycling, **not reliability, availability, forced outage
probability or component lifetime**.

## Separate 96-slot buffered LP dual experiment

Nine additional continuous LPs are solved across 3 seeds × 3 gas-buffer
capacities. The same physical and price setup is repeated over
**96 quarter-hour intervals** with auxiliary heat capacity 0.15 MW_th
and a continuous always-ON lower power bound 0.2 MW_e.
The inherited v0.9.5 LP uses midpoint ramp bounds `0.8 MW_e/h`,
gas conservation with cyclic inventory, instantaneous CHP heat
generation/service and the same objective without switching costs.

This is **not the LP relaxation of the on/off MILP**, because the
always-ON floor and transition constraints differ. It is a
**separate** LP problem, suitable for explicitly checking primal/dual
optimality arithmetic.

## Independent numerical certificate

The standalone `scripts/audit_v0919_independent.py` imports
**no `biogasflex` module**. It independently:

- Reconstructs the exact synthetic prices using their deterministic
  integer formula and exact `2020-01-01T00:00:00+00:00` quarter-hour
  timestamps, gas production and all configuration coefficients.
- Independently verifies all original solver output rows:
  gas stock updates `s_(i+1)-s_i=(g_i-u_i)×0.25h`,
  `P_e=η_e u`, `Q_heat=η_th u`,
  contemporaneous heat service, ramp limit, capacity bounds,
  end-of-horizon cyclic gas stock, binary transitions and elapsed
  two-quarter minimum up/down dwell.
- Recalculates the economic objective **without reading the original
  solver's objective function or matrix**.
- Independently constructs the **five-block LP** decision vector
  `[fuel use, end gas stock, CHP delivered heat, auxiliary heat, dumped heat]`.
  For each MILP case it **fixes the returned binary sequence** and
  solves that continuous restricted LP. This checks whether the
  original selected pattern's continuous dispatch is optimal
  **conditional on the pattern**, but alone does not prove the
  original MILP globally optimal.
- Calls SciPy/HiGHS on that separately assembled LP and explicitly
  checks **primal equalities, inequalities, lower and upper bounds,
  dual multiplier signs, dual stationarity, complementary slackness,
  and primal–dual objective agreement** under a declared 3e-5
  absolute numerical tolerance. The dual objective is computed from
  constraint right-hand sides, lower/upper bounds and *reported*
  multipliers; it is **not** accepted merely because a solver returns
  success.
- The LP is implemented **independently but solved with the same
  SciPy/HiGHS numerical engine** as the original. This is a
  cross-formulation optimality and KKT audit, **not independent solver
  implementation or an analytic proof for 96-quarter-hour LP**.

### Genuine global MILP witness at 8 quarter-hours

In one additional case (`seed=11, C=0.5 MWh_LHV,
backup=0.15 MW_th, startup cost €5`) the auditor enumerates
**all 2⁸=256 binary state strings** and rejects those
violating declared 0.5h minimum ON/OFF dwell. For each remaining
sequence it rebuilds the appropriate **fixed-pattern LP** with
state-constrained fuel flows and ON–ON ramp limits, tests feasibility
and obtains the optimal continuous dispatch. The **maximum** of all
feasible fixed-pattern LP contributions is then compared with the
original MILP objective.

This gives a **numerically dual-certified exhaustive binary
global optimum over the precise 8-slot synthetic formulation**,
at stated tolerance. It does not automatically prove the larger
24-slot, 672-slot or stochastic problem globally optimal
independently of the MILP solver.

## Operational design frontier — not reliability statistics

For each of the three fixed price seeds and **startup cost €5**, all
six `3 storage × 2 external heat` designs are compared under the
same modeled fuel/electricity/heat service and cost assumptions.
Non-dominated candidate designs maximize synthetic economic
contribution while minimizing backup heat fraction and number of
starts. The Pareto calculation uses explicit weak/strict dominance
and is independently reconstructed in the audit.

The objective does **not** subtract the capital costs of larger
gas storage or external heat capacity, and the three criteria
are not commensurate in units. Thus the frontier is a finite
mathematical **operational-design trade-off** — not a plant
investment frontier, a guarantee of CHP reliability, a causal
identification of equipment flexibility or a probabilistic
robustness envelope.

## Execution and reproduction

```powershell
git pull origin main
python -m pip install -e .

# Quick eight-slot dynamic/duality smoke test
python -m biogasflex benchmark-v0919 --smoke

# Full 46-case finite research design
$raw = Join-Path $env:TEMP 'biogasflex_v0919_design.json'
$cert = Join-Path $env:TEMP 'biogasflex_v0919_certificate.json'
python -m biogasflex benchmark-v0919 --output $raw
python scripts/audit_v0919_independent.py --input $raw --output $cert

# Inherited numerical regression, provenance, packaging and hashes
.\scripts\reproduce_v0919.ps1
```

The independent GitHub workflow,
`.github/workflows/v0919-endogenous-frontier.yml`,
runs the full computational design, full KKT verification,
eight-quarter exhaustive binary oracle and archived source/proof
JSON as distinct artifacts. The cross-platform regression
workflow executes the short case and inherited suite without
requiring internet access or new plant measurements.

**Next release gates:** physically documented CHP gas/electric/heat
source metrology and empirical calibration, actual startup and
gas-vessel dynamics; a higher-complexity multi-day endogenous
commitment study with multiple objective-gap stress tests; and
properly sourced operational electricity awards/forecast timing
if market claims are pursued. None is established by this
synthetic mathematical benchmark.
