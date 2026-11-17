# BiogasFlex v0.9.22 research branch: time-causal hourly CHP replay

**Status: research candidate, not a released v0.9.22 and NOT real biogas CHP validation.**

## Scope and evidence boundary

The v0.9.21 input is the independently publisher-SHA-256-verified OPSD
2020-10-06 SE3 hourly archive for 2019. Its real source errors comprise
(1) regional electrical-load reported day-ahead forecast versus actual
and (2) a constructed 7-day-lagged SE3 auction-price persistence baseline
versus cleared auction price. It does **not** contain a provider's original
price forecast vintage, original per-record published load-forecast
revision times, plant-specific biogas production forecast errors or site
heat-demand forecast errors. These exclusions remain binding.

The hypothetical plant gas and heat trajectories are the **same explicit,
uncalibrated** functions of paired source errors used in v0.9.21. That
does not make the resulting gas/heat coupling empirical or causal.
The six-hour target window is 08:00-14:00 UTC. A single historical hourly
record is held constant for four 15-minute mathematical intervals.
Those four intervals are NOT independently measured observations.

## Ex-ante sequence and comparison

For every chronologically eligible full held-out date, the controller
first assembles its seven-day historical price-persistence baseline
from the **source day seven calendar days earlier**, NOT by reading
target-day actual price minus residual. Both commitment policies are
solved and SHA-256-locked before the target's residual vector and
synthetic plant signals are constructed:

- A nominal one-scenario 24-quarter-hour MILP.
- The inherited eight-training-block joint maximin MILP, with the same
  v0.9.21 assumptions and a shared binary on/start/stop sequence.

The day is eligible only if both its own source day and its complete
UTC day exactly seven days earlier exist in the report. The full
holdout target contains 92 source-complete days; the eligible
denominator is independently recomputed and missing-prior-day
exclusions are reported, not imputed. The production runner processes
*all* eligible days by default. A requested first-N run is explicitly
a smoke subset, not a representative performance estimate.

## Online information set

The first-stage binary commitment remains fixed. At the start of
source hour h, a model controller is hypothetically told the realized
**synthetic** gas production rate and heat demand for that source hour.
It knows only the frozen nominal gas/heat forecasts for later hours and
only the seven-day-lagged historical electricity-price baseline at
every hour. The full realized source-day price, gas and heat trajectory
is not passed to the linear optimizer.

A 15-minute LP computes the remaining target-horizon plan, commits the
next four quarter-hour actions for the current hour and then discards
its forecast actions for later source hours. The next hour's newly
revealed synthetic gas/heat rates cause replanning. The simulated
stock state and prior generator electrical output are carried between
hours. The exact v0.9.21 fixed-binary physical formulation is matched
as closely as possible: 0.5 to 2 MW_LHV fuel for ON, 0 for OFF,
electric/thermal efficiency 0.4/0.2, 1.5 MWh_LHV stock capacity,
0.8 MW_e/h consecutive-ON ramp (including half-initial-interval
convention), 0.20 MWth backup-heat capacity and 0.40 MWth heat-dump
capacity. No process-dynamic startup, vessel pressure or genuine
real-time flow-sensor response is claimed.

**Important sensing limitation:** an entire synthetic source-hour
gas/heat rate is treated as observable at the start of that hour.
The OPSD dataset does not support this plant observation. Thus the
policy is *information-causal conditional on that declared fictional
hour-start sensing assumption*, not a demonstrated practical plant
controller.

## Terminal inventory / matched-service protocol

To prevent forecast infeasibility from being concealed, each rolling
LP uses an explicit EUR 50/MWh_LHV *planning-only* penalty for a
terminal-stock mismatch. This is an uncalibrated numerical controller
parameter and **is not charged as actual plant OPEX**. Actual terminal
stock is reported. The hindsight comparison retains the v0.9.21
**hard cyclic terminal stock** and optimizes perfect-future continuous
recourse for the *same frozen binary commitment*.

The resulting perfect-future bound is only mathematically comparable
when the causal trajectory also achieves the initial terminal stock
(within 5e-5 MWh_LHV). The independent auditor refuses bound claims
otherwise. Economic differences between nominal and joint policies
are computed **only** on days when both causal policies (a) serve all
24 mathematical intervals feasibly and (b) finish at matched terminal
gas inventory. All infeasible or unmatched-service days remain
separately counted, with no invented zero-profit substitution.
No actual award or settled export equality is enforced in this track:
it is a *hypothetical modeled-generation* operating-contribution
comparison, NOT a day-ahead trading strategy.

## Independent review and failure gates

A standard-library-only independent auditor uses source JSON and
study JSON, imports **no BiogasFlex package code**, reconstructs the
paired historical source error -> synthetic gas/heat mapping, prior
seven-day source, first-stage SHA-256, all 24 modeled quarter-hour
energy/thermal/stock/ramp constraints, economic ledger and strict
matched-service comparisons. The independent auditor cannot prove
algorithmic nonanticipativity solely from a final JSON. Adversarial
tests separately perturb future realized price/gas/heat and verify
that already-committed actions remain unchanged. A report's true/false
chronology labels are not independent time-vintage authentication.

No v1.0 industrial physical reliability, original historical bidding
availability, stochastic forecast probability law or site calibration
follows from a PASS.

## Reproduce (after source verification and installing SciPy)

~~~powershell
$raw = Join-Path $env:TEMP 'OPSD_2020-10-06_60min_singleindex.csv'
$source = Join-Path $env:TEMP 'biogasflex_v0921_verified_SE3.json'
$study = Join-Path $env:TEMP 'biogasflex_v0922_causal.json'
$proof = Join-Path $env:TEMP 'biogasflex_v0922_independent.json'

python -m biogasflex source-evidence-v0921 --csv $raw --download --output $source
python -m biogasflex.causal_v0922 --source $source --output $study
python scripts/audit_v0922_causal_independent.py --source $source --study $study --output $proof
~~~

Source-dependent complete 92-day testing is computationally
substantially more costly than the frozen three v0.9.21 study days.
Run the opt-in smoke first to establish end-to-end mathematical
feasibility, then execute the complete eligible holdout and archive
the report and independent certificate before any result claims.

## Next research steps (NOT yet implemented)

1. Complete cross-platform automated release integrity and separate
   full source-backed backtest, including reproducible confidence
   intervals adjusted for time dependence.
2. Evaluate strict actual electricity-award equality with causal
   physical balancing; this changes the model and requires a separate
   feasibility/market-assumption protocol.
3. Obtain calibrated real CHP gas, power and useful-heat field
   measurements and archived issue-time forecasts; keep them off
   public Git if reuse or confidentiality is not established.
4. Model realistic gas-vessel pressure and minimum on/off/engine
   startup transitions before operational reliability assertions.
