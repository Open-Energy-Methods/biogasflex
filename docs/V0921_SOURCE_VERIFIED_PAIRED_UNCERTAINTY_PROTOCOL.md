# BiogasFlex v0.9.21 — Verified SE3 forecast evidence and source-paired CHP uncertainty

**Research status:** independently source-hash-verified real **regional electricity
load forecast errors**, real historical day-ahead clearing prices, a transparent
seven-day-lagged **model price forecast baseline**, and **explicitly
hypothetical gas/heat coupling** for a two-stage CHP dispatch experiment.

**This is not** a site-calibrated three-variable covariance model, an
authenticated historical bid-time price-forecast archive, plant heat-demand
prediction, gas-production forecast model or a validated electricity-trading
system. Use of the term "correlated" means that two *observed regional
error series* remain paired by actual historical timestamp, and the two
*synthetic plant variables* are deterministic functions of the same two
residuals. It does **not** imply measured joint 3D biogas/heat/price errors.

## 1. Scientific source, hash and provenance

| Property | Reproducible evidence |
|---|---|
| Data publisher | **Open Power System Data (OPSD), with ENTSO-E Transparency upstream** |
| Frozen release | [2020-10-06; DOI: 10.25832/time_series/2020-10-06](https://doi.org/10.25832/time_series/2020-10-06) |
| Raw CSV | [Original 60-minute single-index file](https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv), approximately 124 MB |
| Publisher-source checksums | [OPSD repository `checksums.txt`](https://github.com/Open-Power-System-Data/time_series/blob/master/checksums.txt) |
| Independently published original SHA-256 | `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8` |
| Region | **SE3 Swedish electricity bidding zone**, NOT an identified CHP site |
| Complete observation year | **2019**; UTC hourly timestamp labels |
| Training-vs-holdout split | January–September 2019 versus October–December 2019 |
| Verified primary numerical execution | [Actions 43885759398](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43885759398) |
| Source register | `data/evidence/v0921_opsd_se3_forecast_error_source_register.json` |

`src/biogasflex/opsd_v0921.py` explicitly downloads the **exact
versioned URL**, verifies raw CSV bytes against the publisher's
**independently supplied** digest and **refuses** to analyze changed or
oversized files. It then verifies strict hourly UTC timestamps,
duplicate rejection, complete UTC-day requirements and the
training/holdout date boundary. It skips missing or invalid source
pairs, retaining the reason and count. Research data and derived
source blocks are written **outside** the tracked Git checkout.

The exact source field names and their roles are:

- `SE_3_load_forecast_entsoe_transparency`: **reported TSO
  day-ahead regional electricity-load forecast** in MW;
- `SE_3_load_actual_entsoe_transparency`: corresponding
  regional electricity-load observation in MW, as published
  in the frozen archive;
- `SE_3_price_day_ahead`: **cleared day-ahead auction price**
  in EUR/MWh, **NOT a price forecast**;
- `utc_timestamp`: explicit UTC delivery-time interval start.

Original source terms and descriptions are in the OPSD
[documentation and field register](https://data.open-power-system-data.org/time_series/2020-10-06)
and its upstream [download/provenance processing code](https://github.com/Open-Power-System-Data/time_series/blob/master/input/sources.yml).

The ENTSO-E [day-ahead load forecast rule](https://transparencyplatform.zendesk.com/hc/en-us/articles/16647979768084-Actual-Total-Load-Day-ahead-Per-Bidding-Zone-6-1-A-6-1-B)
describes publication in advance of day-ahead gate closure, but also
permits forecast updates. The released OPSD CSV **does not preserve
per-observation source publication/revision timestamps**. Therefore
none of these values is falsely labeled a proven exact archived
gate-closure forecast *vintage*. Correctness of raw digest and
published *forecast category* is not proof of bid-time observability
for every individual revised data point.

## 2. What is actually measured versus constructed?

### Genuine reported regional load forecast error

For each source hour `t` with a valid pair:

```text
e_load,t = (actual_SE3_electric_load,t
            - published_day_ahead_forecast_SE3_electric_load,t)
           / published_day_ahead_forecast_SE3_electric_load,t
```

This is **regional electrical demand**, never the biogas CHP's
thermal load. Its archived forecast revisions are not vintage-certified.

### Seven-day historical electricity-price persistence error

```text
p_hat_t = p_cleared_(t - 7 calendar days)
e_price,t = p_cleared_t - p_hat_t
```

`p_hat_t` is a simple, exactly reproducible **research baseline**
using **only prices already cleared a week before** the target.
It is **not** a historical market operator's predicted price,
a Nord Pool submitted bid, a vendor forecast or an experimentally
verified commercial forecast. The baseline's seven-day lag
is constructed by exact UTC timestamp subtraction, not
from day-of-week grouping. No same-day auction price may enter the
ex-ante optimization for that delivery day.

An exact per-source-UTC-hour pair is

```text
E_t = [ e_price,t (EUR/MWh), e_load,t (dimensionless) ].
```

Missing pairs are **omitted**, never silently interpolated,
imputed as zero or moved between dates. Each complete historical UTC
day contributes an **unaltered paired 24-hour error block**.
Shuffling price and load series separately would break the
identified historical cross-series alignment and is disallowed.

### Source-verified summary statistics, executed 2026-11-16

| Metric | Jan–Sep 2019 training | Oct–Dec 2019 holdout |
|---|---:|---:|
| Valid paired hourly observations | **6,548** | **2,208** |
| Full 24-hour UTC blocks | **271** | **92** |
| Reported TSO regional load error mean absolute percentage | **2.557%** | **2.209%** |
| Reported TSO load error RMSE relative | **3.255%** | **2.826%** |
| Price seven-day persistence error MAE | **€5.669/MWh** | **€4.749/MWh** |
| Price persistence error RMSE | **€8.840/MWh** | **€7.326/MWh** |
| Observed correlation `corr(e_price,e_load)` | **+0.0174** | **+0.1027** |

The observed region-level paired correlation is **small** in
this period, especially in the training partition. It is
inappropriate to market the data as demonstrating a strongly
correlated electricity-price/load system, or extrapolate these
statistics to gas production or CHP site heating.

The archive contains two missing source prices and two cases
where the seven-day-lagged source price could not be matched.
The 2019 accepted total is **8,756** of 8,760 hourly records.
The 363 complete 24-hour blocks are the only source days
used in full-day joint scenario generation.

## 3. Paired empirical-block scenario construction

The primary scenario study uses **six source hours, 08:00–14:00 UTC**,
per complete historical day. Each hour is **held constant for four
15-minute mathematical CHP intervals**. These 24 optimizer
intervals are **not** 24 independent observed data values.

Only eight predeclared **training-block ordinals**
`[0,20,40,60,80,100,120,140]` are used per target:
each produces one paired historical `[e_price,e_load]`
six-hour trajectory, with original serial ordering. These
are **eight discrete design scenarios**, not a statistically
representative ensemble or an empirically calibrated probability law.

Three predeclared held-out target-day ordinals
`[8,40,72]` from the **Oct–Dec source partition** correspond to
**2019-10-09, 2019-11-10 and 2019-12-12**. Their
observed residuals are not constructed until both ex-ante
binary schedules have been solved and SHA-fingerprinted.

Training-period standardization uses only training metrics:

```text
z_price,t = clip((e_price,t - μ_train_price) / σ_train_price, -2.5, 2.5)
z_load,t  = clip((e_load,t  - μ_train_load)  / σ_train_load,  -2.5, 2.5)
```

The source price scenario is `p_hat_target,t + e_price,sample,t`.
`p_hat_target` comes from the target day's **known seven-day
historical clearing-price lag**. It is computed without
access to the target's realized same-day price.

## 4. Site gas and heat: explicitly uncalibrated joint physical proxies

Because the source contains **NO measured digester
production forecast/errors or thermal end-use forecast/errors**,
these two plant quantities are synthetic sensitivity mappings.
With standardized historical *regional electric* error
coordinates as shared drivers:

```text
gas_production_t (MW_LHV) =
    clip(1.0 × (1 + 0.08 z_price,t − 0.06 z_load,t), 0.78, 1.22)

thermal_demand_t (MW_th) =
    clip(0.15 × (1 + 0.10 z_load,t + 0.03 z_price,t),
         0.105, 0.195)
```

The coefficient magnitudes, signs and clipping limits
are **invented testing assumptions**; they have no
independent causal, manufacturer, statistical or site
calibration basis. They are stated explicitly so a
different physically justified assumption can replace
them without changing the source error pair. The mapping
introduces *designed* multichannel covariation, not
discovered gas/thermal covariance. No standalone
gas/heat empirical uncertainty or chance-constraint
claims are justified.

Other fixed hypothetical engineering assumptions:
0.8 MW_e generator nameplate, 0.4 electrical and 0.2
thermal fuel-LHV efficiency, 1.5 MWh_LHV energy buffer
(initial/terminal 0.75 MWh_LHV), 0.2 MW_e
minimum-on generator output, 0.8 MW_e/h steady-on
midpoint ramp, 0.5h minimum on/off, 0.20 MW_th
external heat backup, 0.40 MW_th heat rejection,
€5 modeled start, €1 shutdown, €0.75/MWh_e
variable CHP cost, €6/MWh_th auxiliary heat and
€1/MWh_th heat-dump penalty. No gas-vessel pressure
or safety physics is asserted.

## 5. Nonanticipative binary commitment and idealized recourse

A single **here-and-now binary on/off/start/stop sequence**
is shared across ALL eight training scenarios. The model
optimizes the **minimum** of their eight hypothetical
scenario-specific operating cashflow contributions
minus shared switching costs:

```text
max_(y,z,v, x_s) min_{s=1..8} F_s(y,z,v,x_s)
```

where `x_s` contains *independent, scenario-specific*
gas fuel rate, gas stock, useful heat, auxiliary heat
and rejected heat. Constraints enforce gas inventory
balance and identical cyclic terminal stock for every
scenario, capacity, binary on/off limits, minimum dwell
and consecutive-ON ramps. No heat demand is abandoned:
it is met by CHP useful heat and hypothetical backup.

A matched nominal policy uses historical price persistence,
constant 1 MW_LHV gas and constant 0.15 MW_th heating,
optimized with the same physical formulation.
The held-out actual source errors are then revealed,
and a separate LP finds the best continuous dispatch
**conditional on each fixed binary schedule**.

**Crucial operational caveat:** The recourse is a *full
scenario future-known optimum*. In real electricity delivery,
fuel and thermal boundary measurements arrive gradually,
and accepted power awards may prohibit this freedom.
This recourse is an **optimistic two-stage idealization**,
not a fully information-causal real-time plant controller
or a viable day-ahead market dispatch strategy.

## 6. Independent mathematical certification

The source-independent
`scripts/audit_v0921_joint_independent.py`
imports **no BiogasFlex source module**. It independently
recreates target-day historical price persistence,
every paired training error block, regional-error
training normalization, hypothetical gas/heat mappings,
and all source/target partition boundaries. It then
independently checks:

- The unchanged shared binary first-stage sequence across
  all training scenarios and SHA256 before held-out reveal.
- Source-scenario prices/gas/heat, energy stock conservation,
  generator rating, minimum-on limit, dwell, midpoint
  ON-to-ON ramps, heat conversion, demand, backup capacity
  and cyclic gas inventory.
- All scenario cashflow components and the
  **minimum of the original scenario results** equal
  the reported maximin objective including startup costs.
- Independently constructed, conditional fixed-binary
  continuous LP optima and explicit **primal equalities,
  bounds, inequalities, dual feasibility, stationarity,
  complementarity and duality gap** using SciPy/HiGHS.
- The source-attested held-out path never modifies the
  pre-reveal binary sequence; each held-out conditional LP
  is independently re-solved and feasibility checked.
  An impossible recourse cannot be reported as achieved
  electricity or heat delivery.

For three target dates and nine LP checks per target
(eight training-block + one nominal conditional LP)
plus two additional held-out recourse LP checks,
the independent audit produces **33 conditional
LP optimality/feasibility checks**.

**Limitations of this certificate:** HiGHS remains the
common numerical LP engine and the 24-quarter
first-stage binary MILP global optimum is
**not independently enumerated or dual-certified**.
Only selected first-stage binaries receive independent
continuous recourse certificates.

## 7. Executed negative result and reproducibility

The full original on-source run
[43886979566](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43886979566)
showed **the same idealized held-out contribution**
for the nominal and eight-block maximin policy
on all three selected targets:

| Held-out day (UTC) | Nominal modeled 6h EUR | Joint maximin modeled 6h EUR |
|---|---:|---:|
| 2019-10-09 | 98.761 | 98.761 |
| 2019-11-10 | 98.122 | 98.122 |
| 2019-12-12 | 126.481 | 126.481 |

Do **not** infer that the empirical joint uncertainty
model yielded an observed economic or physical reliability
improvement. The current experiment demonstrates a
**source-backed uncertainty construction and numerically
verified dispatch formulation**, not a verified superiority
of scenario robustness. The result is not tuned away or
overwritten to manufacture a difference.

The follow-up [independent source-paired audit
43887439207](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43887439207)
passed the **three targets, six first-stage policies,
33 conditional LP certificates**. Final release
workflow links are tracked in the PR.

Reproduce the public real-source and modeled joint study
from the source repo, writing full data OUTSIDE Git checkout:

```powershell
git pull origin main
python -m pip install -e .

$raw = Join-Path $env:TEMP "OPSD_2020-10-06_60min_singleindex.csv"
$source = Join-Path $env:TEMP "biogasflex_v0921_verified_SE3.json"
$study = Join-Path $env:TEMP "biogasflex_v0921_joint_CHp.json"
$proof = Join-Path $env:TEMP "biogasflex_v0921_joint_KKT.json"

python -m biogasflex source-evidence-v0921 --csv $raw --download --output $source
python -m biogasflex joint-scenarios-v0921 --source $source --output $study
python scripts/audit_v0921_joint_independent.py --source $source --study $study --output $proof

.\scripts\reproduce_v0921.ps1
```

The separate GitHub Actions source workflow downloads
the 124-MB-class original CSV and checks its full publisher
SHA before producing the 2019 statistical report.
No raw OPSD observations or confidential site data
are committed to the Git repository. External source
download is **explicit and opt-in** for local users;
the standard cross-platform regression is offline
and uses fictional, explicitly named regression fixtures.

## 8. Outstanding scientific gates

1. **Historical as-of gate:** authoritative original
   electricity-price forecast revisions and publication
   timestamped load forecast vintages; current source does
   not establish that every original TSO value was visible
   exactly at historical gate closure.
2. **Real biogas production evidence:** site-level
   measured gas flow/composition and separately recorded
   operational gas-production forecasts with proper
   data provenance and permission.
3. **Real useful-heat delivery evidence:** actual site
   heat demand/flow/temperature and archived prediction
   vintages; the SE3 *electrical regional load*
   is not a site heating meter.
4. **Dynamic engine model:** validated starts, ramp,
   minimum on/off, buffer pressure/volume, measurement
   uncertainties and failure events.
5. **Causal dispatch:** rolling information revelation,
   physically admissible real-time recourse, contracted
   exports and costs; current full-day recourse uses
   future-known scenario paths.
6. **Independently certified hard MILP:** larger
   first-stage binary MILP global optima are not
   certified by exhaustive independent enumeration.

Until those gates have evidence, the correct description
is **source-verifiable two-factor regional error
evidence and uncalibrated coupled CHP scenario model**,
not experimentally validated 3D site uncertainty or
scientific v1.0 physical reliability.
