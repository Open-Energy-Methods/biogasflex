# BiogasFlex v0.9.9 — Internal historical-price replay audit

**Date:** 6 November 2026
**Status:** DEVELOPMENT-CANDIDATE, reproduced on hosted CI; no public
GitHub Release, Zenodo DOI, plant calibration or human peer review.

**Exact verified development branch:** `development/v0.9.9-causal-historical-replay`,
head `c13803b0002e3779204912060277cb9a9c51dabf` before this
evidence-note commit.

**CI evidence:**
- [Development branch run 42208624689](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42208624689): 10/10 green.
- [PR #11 run 42208631528](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42208631528): 10/10 green.
- Ubuntu, macOS, Windows × Python 3.11–3.13,
plus built/isolated wheel on Python 3.13 Ubuntu.
- **264 tests passed**; all inherited scripts and offline audits pass.
- **216** historical LP primal/dual certificates;
**96** independent solver-free LP comparisons;
**216** frozen historical sensitivity cases and **five**
explicitly hypothetical interruption cases independently reproduced.
- **286** original science source/result files unchanged;
**444** files SHA256-covered plus one manifest, **445** tracked files
before addition of this report.

## Study design and provenance

Actual **Svenska kraftnät SE3 2020 observed hourly electricity prices**,
CC BY 4.0, retained from the prior immutable original sources.
Jan 1 2020 (24h) is the temporally earlier anchor; April 1 and
October 1 2020 are **two selected 24h holdouts**.
No months-long continuous series, missing-price imputation,
general-purpose predictor fitting or representative annual
statistical inference.

Original archive source and licences:
`data/observed/README.md`, `docs/V08_DATA_PROVENANCE.md`.
SHA256 in hosted report for source files, in training/April/October
order, respectively:

```text
25734490a17b1c3506ae0b7ca873d38bfbf1991f4746afeeac1b39f93873bce8
560415b0b38fd764c64bf40c182737d60b94838a39db677da96f7649ba4661b0
a5e1a3dfb9407f91b124973c8c9ecf08d188b8c5833b057a4a378dd4d3988b22
```

All experimental controls use the exact v0.9.8.1
rolling CHP MILP with fixed terminal inventory, gas
and heat physical ledgers, startup costs and minimum-up/down
and ramp commitments. **All CHP, efficiencies, fixed gas
production, storage, heat, auxiliary costs and gas-control
assumptions are fabricated and independent of observed site operation.**

Predeclared, never target-fit price policies:
1. Last strictly observed price constant across the future horizon.
2. Mean of last three strictly observed prices constant across the future horizon.
3. Previous January local-clock-hour price shape + level adjustment from
   the *last completed* target slot; an actual time-varying hourly
   forecast curve, still wholly derived without access to future prices.

Each target price becomes "known" to the hypothetical controller
only **after** its slot is chosen and executed. This reveals
observations sequentially in an **artificial time regime**, not
a documented live market price-forecast feed or historically
feasible day-ahead bid schedule.

## Numerically reproduced outcomes

One-step price MAE/RMSE are in €/MWh_e.
Economic contributions/regrets are **hypothetical model euros**,
not earnings, market operating forecasts or real benefits.

| Holdout | Causal forecast | MAE | RMSE | Executed model contribution € | Ideal hindsight € | Regret € |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| April 2020 | last_observed | 2.760417 | 5.974299 | 67.038 | 71.680 | 4.642 |
| April 2020 | trailing_three_mean | 4.499583 | 7.912602 | 67.038 | 71.680 | 4.642 |
| April 2020 | diurnal_template_bias | 3.404583 | 6.701720 | 64.840 | 71.680 | 6.840 |
| October 2020 | last_observed | 4.094167 | 5.332784 | 292.108 | 301.862 | 9.754 |
| October 2020 | trailing_three_mean | 7.238194 | 8.876993 | 292.108 | 301.862 | 9.754 |
| October 2020 | diurnal_template_bias | 4.270833 | 5.699600 | 290.566 | 301.862 | 11.296 |

All six studies: `max_gas_balance_residual_mwh=0` in
the reproducible audit; full heat-service physical residual
is independently required to remain at or below 1e-7 MWh.
No modeled realized contribution exceeds the perfect-hindsight
MILP value. Source price MAEs have independent, exact
24-term CSV regression oracles.

## Critical negative results — do not conceal

1. **The two flat remaining-horizon price forecasts give
identical CHP dispatch outcomes on both selected days.**
This is structurally expected: with fixed terminal stock,
fixed assumed gas inflow/losses and constant price over
all remaining slots, the amount of electricity produced
over the horizon is fixed by gas conservation.
A constant forecast therefore contributes no
**temporal** marginal incentive to move gas use
between hours. Different constant price levels change
the *forecasted value*, but not this price-shifting
incentive. So the equality of model returns does
**not** show that either predictor is effective.

2. The causal **time-varying** January-hourly template
does change dispatch and performs **worse** than the
two flat baselines in both selected held-out days:
April executed contribution is €2.198 lower;
October is €1.542 lower. Worse model contributions
occur despite valid physical conservation. This is a
small, negative, case-specific finding—not evidence
about the performance of genuine statistical forecasts.

3. Price MAE and dispatch regret do not rank policies
interchangeably. The two flat predictors have
different one-step MAE yet the same dispatch. The
time-varying model has intermediate MAE on April
but worse dispatch outcome. No generic comparison
of forecasting effectiveness is justified by two
selected test days.

4. These figures are conditional on a counterfactual
price-revelation process. Day-ahead electricity prices
are typically published **before** delivery. The model
does not reconstruct the true historical information
set at bid time and cannot be labelled actual
price forecasting or realized CHP profit.

## Reproduction (no network)

```bash
python -m pip install -e .
bash scripts/reproduce_v099.sh
python scripts/audit_v099_historical.py
python -m biogasflex historical-replay
python -m biogasflex historical-replay --output replay.json
```

Windows: `./scripts/reproduce_v099.ps1`.
The `historical-replay` CLI is output-file opt-in.
All modelled source/market/physical assumptions and
forecast as-of cutoffs are disclosed in the report.

**Scientific release gate still open:**
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
Authentic as-of-published forecast feeds, more chronological
holdout days, measured CHP operating envelopes and independent
human review are necessary before a stronger scientific claim.
