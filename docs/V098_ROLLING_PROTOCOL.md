# BiogasFlex v0.9.8 — Synthetic rolling-horizon electricity-price decision experiment

**Status:** research-development software model, not plant-validated operational
model predictive control (MPC), statistical electricity-price forecasting,
measured profitability, peer-reviewed result, GitHub Release or Zenodo DOI.
All market forecasts and CHP parameters in the new example are entirely invented.

## Problem addressed

The separate experimental v0.9.7 mixed-integer model can decide ON/OFF
CHP unit commitment with elapsed-hour dwell and initial history, but is
a single **perfect-foresight** optimization over one fixed electricity-price
trajectory. v0.9.8 adds an **opt-in rolling price-only forecast evaluation**
to examine how an optimized dispatch changes when forecasts for later
market intervals are revised.

The original 216 historical market cases, five hypothetical outage
cases, 286 pinned scientific research files, and v0.9.5/v0.9.6/v0.9.7
experimental implementations remain unchanged. This v0.9.8 module is
an isolated new analytical branch with explicitly synthetic data.

## New model: `src/biogasflex/experimental_v098.py`

`optimize_commitment_milp(config, intervals)` is a v0.9.8 copy of the
hour-based CHP commitment MILP with one crucial boundary correction:
its `experimental_v098.terminal_gas_inventory_mwh_lhv` is separate
from `initial_gas_inventory_mwh_lhv`.

**Why:** With every replan, actual initial inventory changes, but the
original end-of-study gas target MUST remain the same. Erroneously
setting the end stock equal to the changing beginning stock would
create gas or destroy comparability between the receding-horizon
execution and a perfect-foresight full-horizon schedule.

Gas inventory remains a complete exact balance:

```text
S_(t+1) = S_t + (gas production - fixed flaring - fixed losses - gas use)*dt_t
S_initial = actual measured-as-assumed inventory at the replan
S_final = ORIGINAL declared terminal target, NOT current S_initial
0 <= S_t <= gas-storage capacity
```

All previously experimental binary ON/OFF, startup/shutdown costs,
minimum ON output, elapsed-hour dwell, startup residual history,
instantaneous heat service, cost terms and nameplate limits remain
the same.

A separate independent `_ledger` recomputes full gas/heat balances
from solved controls. Its old cyclic terminal residual is preserved
under `legacy_initial_inventory_cycle_residual_mwh`; the new
`terminal_inventory_residual_mwh` checks the **explicit unchanged
terminal target**. This is not a hidden relaxation of conservation.

The old v0.7 continuous heat LP assumes cyclic terminal inventory
equal to the current initial inventory; therefore its score **cannot
be reused as an unconditional upper bound** when those stocks differ.
Instead the new model solves its **own exactly matched-constraint
continuous relaxation** (same gas target, heat, time/dwell, and
costs; binary indicators relaxed). Its objective must bound the
integer MILP objective from above, otherwise the run fails.

Similarly, a legacy must-run fixed-output comparator is considered
a feasible comparator **only when** original and current target
inventories match and all operating/dwell/ramp constraints pass.
The API explicitly returns `null` rather than a fabricated
increment when the fixed reference is infeasible.

## Rolling experiment, forecast snapshots and physical state carryover

`evaluate_rolling_prices(config, realized_intervals, forecast_snapshots)`
requires one **explicitly provided remaining-horizon forecast snapshot
per executable interval**:

```text
t=0  forecast prices for intervals 0,1,2,...
t=1  forecast prices for intervals   1,2,...
t=2  forecast prices for intervals     2,...
```

All forecast and realized timestamps, zones and durations must
match **exactly**. There is no fitted statistical forecast model,
no probabilistic confidence interval, and no lookahead at realized
future prices when constructing decisions.

At each iteration:

1. Optimize the **full remaining horizon** using the supplied
   forecast prices and the unchanged gas/heat assumptions and
   original final gas inventory target.
2. Commit and physically account for **only the first interval**
   of gas fuel use, CHP electrical output, auxiliary heat,
   heat dumped, binary state, startup/shutdown and event costs.
3. Advance the clock and carry the inventory at interval end,
   current ON/OFF state, electrical output observation, and
   **unfulfilled minimum-up or minimum-down dwell hours**.
4. At the next step update forecast prices, maintain all frozen
   gas/heat assumptions and original final inventory, and reoptimize.
5. At the end independently **rebuild the entire realized physical
   and economic ledger** from the actually executed interval
   actions using **realized synthetic prices**. Compare to a
   full-horizon same-constraints perfect-foresight MILP under
   those realized prices.

This is **price-only** forecast sensitivity: plant outages,
gas inflow/weather/heat demand forecast errors, subsequent
realized fuel availability and equipment failure are not modeled.

**Midpoint ramp detail:** At the first horizon boundary, the
previously declared initial electrical output is interpreted
as a boundary observation. At later replans, the last available
power is the previous *interval midpoint* output and its age
is half the preceding interval duration. The next steady-ON
ramp therefore uses `previous_dt/2 + next_dt/2` rather than
mistakenly resetting the elapsed time to `next_dt/2`.
This is still a surrogate: startup/shutdown transients bypass
steady-ON midpoint ramps as in v0.9.7.

**Finite horizon:** Every newly modeled start/stop must complete
its minimum dwell inside the remaining global study horizon;
a carried prior obligation can continue beyond it. This policy
is an explicit optimization convention, not equipment practice.

## Exact synthetic oracles (not measured)

The synthetic toy is **3 hourly intervals**, with €0/€50/€100
*realized* prices, constant fuel production 1 MW_LHV,
zero initial/final gas inventory, 0.5 MWh_LHV gas storage,
eta_e=0.4 and CHP initially ON. A negative/positive
price variation is included separately.

The **independent analytical fuel balance** sets
`u_0=1-S_1` and `u_1=1+S_1-S_2`,
`u_2=1+S_2` with `0 <= S_1,S_2 <= 0.5`.
Therefore, with zero startup/shutdown events in this fixture:

| Decision rule | Total realized synthetic contribution |
|---|---:|
| Full perfect-foresight on €0/€50/€100 | €80 |
| Replan after first slot: initial forecast €100/€0/€0, updated forecast €0/€100 | €70 |
| Keep stale forecast €100/€0 after slot 1 | €60 |

Thus rolling **hindsight regret** versus perfect-foresight
is €10 with the updated forecast versus €20 for the stale
forecast. This does **not** prove real-world forecasting
accuracy or that rolling always improves returns.

In the separate two-interval toy with initial forecast €100/€0
but realized €0/€100, one cannot borrow future gas at
the first interval (zero initial buffer). Realized value
is €40, perfect hindsight €60, regret **€20**.
All of these are **fully fabricated** toy calculations.

Additional adversarial tests verify exact forecast UTC and
zone alignment, negative realized prices, noncyclic suffix
gas targets, real full-horizon ledger reconstruction,
ON/OFF transition history, startup/shutdown costs charged
once, thermal service, midpoint timing under rolling,
and declared operating assumptions.

## Reproduce offline

```bash
python -m pip install -e .
bash scripts/reproduce_v098.sh
python scripts/audit_v098_rolling.py
python -m biogasflex rolling-forecast
```

On Windows PowerShell use `./scripts/reproduce_v098.ps1`.
The command reads the included fictional config, fictional
observed-price **stand-in** CSV, and synthetic triangular
forecast matrix JSON. It prints a compact result and **writes
no files by default**; `--output path.json` is opt-in.
The legacy CLI commands stay available and unchanged.

The full reproduction includes original 286 scientific hashes,
216 original historical market dual certificates, 216 market
plus five explicitly hypothetical outages, 96 inherited
solver-free short-case oracles, v0.9.5 ramps and price regret,
v0.9.6 commitment tests, v0.9.7 hour-based constraints,
strict full-tree SHA-256 manifest, Git coverage, and platform/
wheel install smoke.

## Research limitations and next work

Synthetic price-only receding-horizon results are not
measured net electricity revenue, profitability, energy
security, islanding, forecast accuracy, or verified real CHP
controller feasibility. There are no physically calibrated
startup/shutdown transients, heat storage, gas pressure and
vessel dynamics, imperfect future gas/heat observations,
scenario probabilities, or explicit terminal plant state.
External human scientific methodological review remains open
in [issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No public GitHub Release/Zenodo DOI follows from software CI.
