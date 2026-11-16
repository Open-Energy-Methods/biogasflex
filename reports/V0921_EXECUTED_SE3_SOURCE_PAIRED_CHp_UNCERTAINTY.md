# BiogasFlex v0.9.21 — Executed SE3 forecast evidence and source-paired CHP scenario results

**Observation period:** full calendar year **2019** (historical).
**Computational execution:** **2026-11-16**.
**Original data source:** fixed Open Power System Data time series
release 2020-10-06, [DOI 10.25832/time_series/2020-10-06](https://doi.org/10.25832/time_series/2020-10-06).

**Original 60-min SE3 source CSV SHA-256:**
`6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`;
the same hash is independently published in
[OPSD's repository `checksums.txt`](https://github.com/Open-Power-System-Data/time_series/blob/master/checksums.txt).

These are measured **regional electricity load** and
archived day-ahead **price observations**, plus a
constructed *seven-day persistence price baseline*.
The plant biogas/heat channels are **synthetic,
uncalibrated sensitivity assumptions**.

## Verified measured/constructed forecast-error evidence

The [source-data verification run
43885759398](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43885759398)
downloaded the actual frozen OPSD hourly CSV, verified its
full SHA-256 against the publisher's separate checksum, and
computed the following exact metrics after strict UTC,
paired-field, missing and chronological checks.

| Source metric | Training: January–September 2019 | Holdout: October–December 2019 |
|---|---:|---:|
| Valid paired hourly records | **6,548** | **2,208** |
| Strict complete 24-hour UTC blocks | **271** | **92** |
| Published SE3 TSO load forecast relative MAE | **2.557%** | **2.209%** |
| Published SE3 TSO load forecast relative RMSE | 3.255% | 2.826% |
| Seven-day price persistence error MAE | **€5.669/MWh** | **€4.749/MWh** |
| Seven-day price persistence error RMSE | €8.840/MWh | €7.326/MWh |
| Paired price persistence-vs-regional load error Pearson correlation | **+0.0174** | **+0.1027** |

8,756 paired valid hours of the 8,760 delivery-hour
calendar year survived. The timestamp/quality register
reports two missing original prices and two
missing seven-day-lagged price comparisons; 363 of the
365 calendar days had a complete usable 24-hour UTC block.

The price baseline is **not the original price forecast**
available at historical day-ahead gate closure: it is the
**recorded price exactly seven days before** each target.
The TSO forecast class is genuine, but the OPSD archive
does **not** preserve per-observation
publication or revision timestamps. Individual load
forecast vintages are therefore **not independently
verified as precisely pre-gate**.

Neither error series measures site heat, gas composition,
digester gas production or plant equipment failures.
The observed regional two-error Pearson correlation is
small, not evidence of strong gas/heat/electricity
interdependence.

## Constructed 2D empirical paired blocks → synthetic 3D plant inputs

The scenario study selects eight training days at frozen
indices `0,20,40,60,80,100,120,140`. In each day,
the real paired six-hour regional error vectors for 08:00–14:00
UTC retain their original time ordering and cross-variable
alignment. The original 6 × hourly values are repeated
four times to form 24 optimizer quarter-hours. This
is a **piecewise-constant model conversion**, not
new quarter-hour observations.

The shared standardised real source coordinates
`z_price,z_load` drive **assumed**, explicitly
non-empirical plant proxies:

```text
gas_input = clip(1.0 × (1 + 0.08 z_price − 0.06 z_load), 0.78, 1.22) MW_LHV
heat_demand = clip(0.15 × (1 + 0.10 z_load + 0.03 z_price),
                   0.105, 0.195) MW_th
```

No credible site statistical distribution or
measured three-dimensional covariance can be
inferred from these arbitrary coefficients.
The original electric/thermal CHP efficiencies, gas
energy-buffer, backup service, startup and ramp
constraints are **illustrative and uncalibrated**.

## Two-stage endogenous CHP scenario results

An original 24-quarter-hour **two-stage MILP**
optimises a **common binary on/off/start/stop
schedule across all eight paired training-block
scenarios**; gas use, gas stock, CHP thermal
allocation and electricity output can vary by
scenario. The objective is a **maximin** fictional
six-hour operating contribution after start/stop
penalties. A separate nominal source-based price
persistence policy uses constant hypothetical
gas and heat demand.

Only after **both** first-stage commitments are
solved and SHA-256 fingerprinted does the program
construct each target's held-out original
regional price/load error block. It then
allows a best-possible *full-future-aware*
continuous LP recourse conditional on each
**unchanged** binary commitment. That makes
the conditional outcome optimistic. It is **not**
a causal online dispatch scheme or a real accepted
electricity-award compliance result.

The independently computed results on the
actual original-source held-out regional error
patterns (but synthetic site heat/gas) were:

| Source-heldout day UTC | Nominal first-stage, fictional idealized EUR/6h | Joint source-block maximin, fictional idealized EUR/6h |
|---|---:|---:|
| **2019-10-09** | **98.761** | **98.761** |
| **2019-11-10** | **98.122** | **98.122** |
| **2019-12-12** | **126.481** | **126.481** |

The original multi-scenario MILP model worst-case
objectives for the respective **eight TRAINING
error blocks** were approximately **€26.738,
€29.988, and €36.331**. These are not
guarantees on real electricity-price,
gas-production or thermal-service uncertainty
outside those eight selected source-backed/
proxy-generated scenarios.

**Central negative result:** In the three
predeclared held-out cases, the joint
eight-scenario commitment and nominal
single-scenario commitment produced **exactly
the same modeled held-out contribution**
(up to floating point tolerance). No
demonstrated performance benefit, statistical
reliability or superiority of the joint model
has been established. This null finding is
recorded rather than discarded.

## Independent numerical verification

The completed [source-backed separate mathematical
audit run 43887439207](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43887439207)
reported

`PASS_INDEPENDENT_SOURCE_PAIRED_CORRELATED_STRESS_AND_IDEALIZED_RECOURSE`.

It independently reconstructed the original
source training/heldout day selection, paired
observed price/load residuals and fully
*assumed* gas/heat sensitivity formulas.
It verified conservation, CHP output/heat
and binary dwell/ramp limits, alternative
fixed-binary LP conditional optima and
KKT primal/dual residuals. Executed coverage:
**271 source training days, 92 heldout
days, 3 selected heldout target evaluations,
6 fixed first-stage policies, and 33
conditional LP optimum/feasibility checks**.

The independent audit imports **no BiogasFlex
model code**, but uses the same SciPy/HiGHS
numerical optimizer for the alternative LP
formulation. The **24-slot binary MILP global
optimum** is solver-reported, not
independently enumerated over every pattern.

## What this increment established

It established source-authenticated, reproducible,
time-aligned real forecast/observation **regional
electricity-load error measurements** and
an explicitly defined, honest historical
electricity-price baseline. A paired block
sampling method now preserves source serial
and cross-series structure, and a two-stage
CHP hypothetical model can consume it with
reproducible gas/heat perturbations.

It **did not** establish measured 3D gas/
heat/price uncertainty, operator gate-closure
forecast vintage correctness, an estimated
probability law or v1.0 physical CHP
operational reliability. Physical gas and
useful heat source meters, source-calibrated
forecast vintages and a fully causal online
dispatch are still necessary before
industrial/scientific validation claims.

The full [methodological protocol](../docs/V0921_SOURCE_VERIFIED_PAIRED_UNCERTAINTY_PROTOCOL.md)
states every selection and coefficient and
provides exact local reproduction commands.
The strict source and independent model
output JSON artifacts are generated outside
the repository and retained on Actions.
