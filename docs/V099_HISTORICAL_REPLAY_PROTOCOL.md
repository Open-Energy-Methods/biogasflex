# BiogasFlex v0.9.9 — Causal chronological historical-price replay

**Status:** opt-in **research experiment**. Original Svk SE3 historical
prices are **observed**, but the CHP equipment, gas flows, heat, costs and
commitment assumptions remain **entirely fictional**. Most importantly,
the sequential hourly reveal of prices is a **hypothetical information
regime**. Real day-ahead auction prices may be available in advance
of power delivery. Do **not** present this as an attainable trading
forecast or validated historical plant profitability.

## Research question and boundary

Does the v0.9.8.1 synthetic receding-horizon CHP MILP preserve gas/heat
conservation, timing causal separation and a perfect-hindsight ceiling
when connected to *actual preserved 2020 electricity prices*
instead of fabricated price trajectories?

The new version does **not** train a production forecaster,
demonstrate forecast skill, model historical energy bidding decisions,
simulate actual gas production or validate hardware control.

## Frozen, attributed market observations

Source: Svenska kraftnät, "Dagen före-priser per elområde",
SE3, resource `cf392ef3-7345-4e98-970e-83088c185570`;
Creative Commons Attribution 4.0. All original reformatted,
immutable files are in `data/observed/`, with provenance
in `data/observed/README.md`.

| Role | Market local date | UTC span | Records |
| --- | --- | --- | ---: |
| Earlier training anchor | 2020-01-01 | 2019-12-31 23:00–2020-01-01 23:00 (end excluded) | 24 |
| Chronological holdout A | 2020-04-01 | 2020-03-31 22:00–2020-04-01 22:00 (end excluded) | 24 |
| Chronological holdout B | 2020-10-01 | 2020-09-30 22:00–2020-10-01 22:00 (end excluded) | 24 |

January is used solely as **earlier historical context** for both
holdouts. October is **never** used to forecast April.
Each holdout has 24 one-hour intervals. This is **two chosen days**,
not two representative months, an annual validation, or evidence
of generalized forecasting accuracy.

We never refetch, update, round, interpolate or fill the original
market data. Explicit UTC end boundaries, zone, row count,
no gaps/duplicates and existing SHA256 pins are all audited.

## Declared predictors

All three predictor definitions, their three-observation window and
the earlier-day local-hour template are
declared before the held-out comparison, not tuned on the target days.

**last_observed:** At decision t, repeat the most recently
available price across all remaining t..N−1 intervals.
Before the first target observation this is the last
January training price.

**trailing_three_mean:** At decision t, use the arithmetic mean
of the latest three strictly known prices. Before first target
observation use the final three January records.

**diurnal_template_bias:** Use the **January training day**
to make a 24-hour `Europe/Stockholm` local-clock price
template. The forecast of each future slot uses the
January price for its local clock hour plus a bias
equal to the **previous completed** holdout interval's
observed price minus its corresponding January
local-hour template price. At the first holdout
decision there is no target observation and bias=0.
Require one unique record for each of local hours 0–23
on the single earlier training civil day and reject
DST/missing/duplicate-clock-hour histories. No
target-holdout prices are used to fit the template.
The resulting remaining-horizon forecast **varies
across the future hours**, allowing direct tests
of price-shape-responsive dispatch.

For all three methods, the forecast for target slot `t`
depends on training and observed target slots `0..t-1`
ONLY. The actual target slot price is appended **after**
the forecast is constructed. The future UTC calendar/slot
durations are assumed known in advance, not future
price values. Forecast snapshots remain full suffix
triangles with exactly matching UTC and bidding zone.

As-of ledger for every prediction records forecast
information cutoff, number of prior holdout observations
and zero future holdout observations used.
Adversarial regression deliberately changes prices for
current and future slots and checks that earlier
predictions remain identical. A noncausal predictor,
overlapping train/target periods or a source missing
a UTC slot fails the tests.

## Optimization / scoring

Each entire 24-hour holdout uses the **same** existing
`receding_horizon_commitment_milp_v098` model as v0.9.8.1.
Only the forecast matrix is new. At each step reoptimize
for the remaining horizon, execute one interval, carry
on/off, power observation age, dwell and gas stock.
End gas target is **fixed from the initial study**.

Compute mean absolute and root mean squared error of
the **one-step** predicted price against the
observed price. Independently rederive physical
gas and heat service ledgers using actually executed
controls and actual observed market prices.
Perfect-hindsight full MILP is a mathematical
upper bound **under the hypothetical same model**.
Negative regret beyond solver tolerance fails closed;
no result implies an operationally available strategy.

Hand-computed expected MAEs from the original immutable
CSV source are these regression reference values:

| Held-out day | last_observed | trailing_three_mean | diurnal_template_bias |
| --- | ---: | ---: | ---: |
| 2020-04-01 | 2.760416667 | 4.499583333 | 3.404583333 |
| 2020-10-01 | 4.094166667 | 7.238194444 | 4.270833333 |

Units: EUR/MWh_e. These values verify the **price accounting
algorithm** and source series. They are not meaningful
evidence of model superiority from two days, and their
first-step histories are months old.

Read the [executed v0.9.9 internal numerical audit](../reports/V099_INTERNAL_AUDIT.md)
for all six study values and the negative forecast-shape finding.

## Reproduction

```bash
python -m pip install -e .
bash scripts/reproduce_v099.sh
python scripts/audit_v099_historical.py
python -m biogasflex historical-replay
python -m biogasflex historical-replay --output replay.json
```

Windows PowerShell: `./scripts/reproduce_v099.ps1`.

The command **does not write** by default. Only explicit
`--output` saves all six 24-hour replay studies,
as-of histories, study scores and optional executed
CHP ledgers. Scripts are offline, sources frozen.

Version-specific comparison is **experimental** and
not a replacement for historic v0.7 dispatch or
v0.8 outage results. v0.9.8.1's first-slot
ramp-history and invalid fixed-baseline corrections
remain in force. All 286 frozen science file hashes,
216 historic dual certificates, 96 independent LP
comparisons and five explicitly hypothetical
resilience cases remain inherited release gates.

**Remaining work before v1.0:** authentic time-stamped,
as-of available ex-ante electricity forecast feeds,
larger chronological samples, plant gas/thermal input
forecast uncertainty, calibrated CHP start/ramp
physics and genuinely independent scientific review.
No site profit, secure grid islanding, annual value
or DOI follows from this version.
