# BiogasFlex v0.9.7 — clock-hour commitment and carried initial operating obligations

**Scope:** Explicitly synthetic, opt-in verification of an on/off
CHP *mathematical model*. These checks do not provide plant
commissioning, equipment minimum running-time evidence, market
profitability, real gas vessel physics or third-party scientific
validation. Historical published-number candidate files stay frozen.

## Why v0.9.7 exists

The separate v0.9.6 commitment MILP introduced binary CHP
on/off, startup/shutdown, costs, and minimum up/down **interval
counts**. When the time grid mixes 15-minute and 60-minute slots,
one interval has no consistent physical duration. v0.9.7 corrects
this in a **new opt-in model**, leaving v0.9.6 available for
reproduction without rewriting its assumptions.

The new model `experimental_v097.py` is chosen only when the
configuration has exactly an explicit `experimental_v097` block
with `model="clock_hour_on_off_milp_v097"`. New parameters:
`minimum_up_hours>0`, `minimum_down_hours>0`, and
`initial_remaining_dwell_hours>=0` (no greater than the relevant
declared minimum). `initial_on` and `initial_power_mw_e` remain
mandatory. Boolean and nonfinite numeric values are rejected.

## Exact elapsed-clock logic

For contiguous interval boundaries `T_0,...,T_n` measured in
elapsed **hours**, each startup/shutdown occurs at a **slot start**,
and each binary operating flag applies throughout that entire slot.
For an event at interval `t`, its due time is:

```
due_t = T_t + (minimum_up_hours if startup else minimum_down_hours)

for each slot k >= t whose start T_k < due_t:
  on_k = 1 on startup
  on_k = 0 on shutdown
```

An event cannot occur if `due_t` extends past `T_n` by more
than `1e-9 hours`. If the dwell deadline falls *within* a slot,
that entire slot remains in the new state, rather than pretending
the unit switches mid-interval. Equality at a slot boundary permits
a transition at the following boundary. This implements elapsed
minimum durations **on the model's time grid**; it does not simulate
continuous-time equipment behavior.

**Initial carry-in:** `initial_remaining_dwell_hours` is a
known obligation from a startup (if `initial_on=true`) or
shutdown (if `initial_on=false`) that happened *before* the
modeled horizon. Every slot starting before that residual deadline
must preserve the initial on/off state. A carry-in obligation
extending past the model horizon remains enforceable throughout
the horizon; residual after the final boundary is explicitly
reported as `carry_in_remaining_after_horizon_hours`.
A **new event** near the horizon end is instead forbidden if its
entire commitment could not be honored inside the horizon.
There are no unverified pre-horizon residual costs, starts, or
thermal trajectories.

Gas inventory, exact cyclic terminal stock, electrical rating,
minimum power while ON, instantaneous heat service, CHP cost,
start/stop penalties, and the steady-ON interval midpoint ramp
surrogate are unchanged from the v0.9.6 *experimental model*.
Startup/shutdown transitions still bypass the steady-ON ramp,
so mechanical transient feasibility remains **unverified**.

The fixed-operation reference is reported as economically
comparable **only when feasible under the new binary and clock
constraints**. The original continuous heat-aware LP, which
ignores on/off switching charges, is an unconditional modeled
upper bound. All gas/heat/transition residuals are recomputed
independently from the numerical objective.

## Independent exact two-slot oracle

`tests/test_v097_hourly.py` constructs a narrow exact
solver-free oracle using only the Python standard library.
The fabricated example has:

- First interval **0.25 h**, second interval **1.0 h**;
  price €0 and €100/MWh_e, respectively.
- Uniform net gas source **1 MW_LHV**, empty initial and
  final stock, gas buffer cap **0.25 MWh_LHV**.
- Electrical efficiency 0.4, generator rated 0.8 MW_e,
  minimum ON output 0.2 MW_e.
- Initial state OFF, no historical obligation, assumed €5
  per startup and €2 per shutdown, nonbinding ON-mode ramps.
- Zero thermal CHP conversion and zero heat demand to isolate
  inventory/commitment logic from heat variables.

For the intermediate stock `S_1 in [0,0.25]`:

```
u_0 = 1 - 4*S_1
u_1 = 1 + S_1
on=0: u_t = 0
on=1: 0.5 <= u_t <= 2.0
net value = 0.4*(0.25*price_0*u_0 + price_1*u_1)
          - 5*(starts) - 2*(stops)
```

Enumerating all four binary on/off configurations and evaluating
feasible affine inventory **endpoints** gives an exact optimum
for this deliberately two-period, zero-heat toy problem without
calling SciPy/HiGHS or the source optimizer.

| Assumed minimum ON hours | Net modeled two-slot value | On/off |
|---:|---:|---|
| 0.25 | €45 | OFF, ON |
| 1.00 | €45 | OFF, ON |
| 1.01 | €40 | ON, ON |
| 1.26 | **Infeasible** | No complete startup fits |

A 0.25-hour prior OFF obligation enforces OFF in the first
quarter hour. A 0.2501-hour prior OFF obligation intersects the
second slot and, with insufficient buffer, makes this **particular
fixed-source scenario infeasible**.

The test suite also verifies exact enumerated objectives with
reversed and negative synthetic electricity prices, positive
CHP heat demand, prior ON obligations, over-horizon residual
reporting, and three equal-hour cases that reproduce v0.9.6's
€55/€35/€15 results for minimum ON 1/2/3 hours.

## Synthetic 24-hour mixed-resolution horizon

`scripts/audit_v097_hourly.py` checks a made-up **36-slot**
horizon comprising 16 quarter-hour slots and 20 one-hour slots,
totaling exactly 24h. The synthetic minimum ON duration is
1.25h and minimum OFF duration 0.75h; assumed steady-ON
electrical ramps are 0.2 MW_e/hour. The test checks model
integrality, duration boundaries, cyclic gas inventory and
heat/ramp residuals. It is not a field plant dispatch,
independent general MILP solver, or statistically representative
grid-market simulation.

## Reproduce

```bash
python -m pip install -e .
bash scripts/reproduce_v097.sh
python scripts/audit_v097_hourly.py
python -m biogasflex hourly-commitment
```

PowerShell uses `./scripts/reproduce_v097.ps1`. The
`hourly-commitment` command writes **nothing by default**;
`--output path.json` writes a full opt-in synthetic report.

All original 286 frozen research hashes, original 216 market
dual certificates, 216 market and five explicitly hypothetical
outage cases, 96 solver-free v0.9.3 comparisons, v0.9.5
ramp/forecast stress and v0.9.6 binary commitment oracles
remain in the full offline and cross-platform CI reproduction.

### Scientific nonclaims

Time-based minimum dwell is a mathematical scheduling
constraint, **not validated equipment operating data**.
This work does not validate physical startup/shutdown
transients, min fuel pressure, CHP control performance, grid
injection rights, day-ahead forecast skill, real economic
profitability, or islanding. Human scientific independent
review remains open in
[GitHub issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No public GitHub Release or DOI should be inferred.
