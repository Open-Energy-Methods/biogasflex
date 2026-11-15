# BiogasFlex v0.9.17 — Executed real 2005 Kitakyushu CHP measurement audit

**Source:** Liao, Jin & Li, [figshare dataset
10.6084/m9.figshare.24978645.v2](https://doi.org/10.6084/m9.figshare.24978645.v2),
published CC BY 4.0. **Technology/fuel:** original Japanese
**city-gas reciprocating engine** (with separate fuel cells), not
anaerobic-digestion biogas.

**Execution:** Actual original three source archives downloaded,
provider MD5 and byte count plus previously independently observed SHA-256
verified, exact original `2005` workbooks decoded and all hourly
records aligned successfully in
[online source-audit run 43711923353](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43711923353).
This report summarizes real source measurements, **not test fixture values**.

## Reported measured 2005 source statistics

| Measured published channel or consistency metric | Recorded result | Scope |
|---|---:|---|
| Complete aligned source-local hourly timestamps | **8,760** | One full 2005 nonleap calendar year; source-local naive timestamps, UTC offset not independently authenticated |
| `Gas engine (kW)`: annual 1h-bin electricity integral | **686,380 kWh** (686.38 MWh) | Engine-labelled electricity; **not** net exported electricity |
| `Gas engine (m3)`: annual engine fuel source-volume sum | **199,510.35 m³** | Unit label from provider; **not** authenticated dry-normal `Nm³` and **not** fuel energy |
| `Gas 1(GJ/h)`: heat-rate integral over 1h bins | **1,485.885 GJ** | Engine heat allocation and end-use metering **not verified** |
| `Gas 2(GJ/h)`: heat-rate integral over 1h bins | **3,746.6145 GJ** | Independently retained source channel; not automatically useful delivered heat |
| Electricity-positive hours | **4,290** | Source `Gas engine (kW)>0`; not verified engine ON controller |
| Engine gas-volume-positive hours | **4,579** | Source `Gas engine (m3)>0` |
| Both engine electricity and gas-volume positive | **4,263** | Two-channel overlap, not calibrated efficiency |
| Electricity positive, gas volume **zero** | **27 hours** | **Potential source signal inconsistency** |
| Electricity **zero**, gas volume positive | **316 hours** | Could reflect source timing, standby/fuel or metering; not inferred as starts |
| Matched electricity/gas channel records | **8,760** | Complete in source without missing hour labels |
| Maximum engine electrical power recorded | **166 kW** | Exceeds 160 kWe nominal article value; requires ratings/meter/normalization review |
| Maximum engine gas input source reading | **50.5 m³/h** | Descriptive source rate only; measurement reference standard unknown |
| Maximum Gas 1 source heat rate | **0.997 GJ/h** | Not physically calibrated |
| Maximum Gas 2 source heat rate | **1.531 GJ/h** | Not physically calibrated |

**Selected quality flag:** The first recorded power-positive/gas-zero
hour is source-local **2005-02-28 08:00**. Subsequent hours on the same
date also show this mismatch. The full original source should be
reviewed for source meter delays, instrumentation or plant operation
before interpreting these as genuine physical states.

The two separate heat-recovery channels are *not proven to correspond
exclusively to the single generator engine* and thus must **not** be
combined with the gas-engine electricity/fuel totals to calculate
one CHP first-law efficiency. The source has fuel-cell and auxiliary
equipment whose thermal flows must remain separate.

## Monthly measured electricity, engine-gas volume and measurement conflicts

These values were independently extracted from the original
published 2005 source workbooks by
[online measurement run 43712197151](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43712197151),
using monthly groups of the source's 8,760 hourly rows. They are
**not hypothetical CHP model output**.

| Month 2005 | Engine electricity (kWh) | Engine gas (source m³) | Both power and gas positive (h) | Power positive / gas zero (h) | Power zero / gas positive (h) |
|---|---:|---:|---:|---:|---:|
| Jan | 65,648 | 18,888.00 | 413 | 0 | 31 |
| Feb | 66,837 | 18,835.60 | 410 | 6 | 29 |
| Mar | 62,774 | 18,224.90 | 392 | 0 | 23 |
| Apr | 54,351 | 15,658.90 | 342 | 0 | 25 |
| May | 49,799 | 14,744.90 | 312 | 0 | 24 |
| Jun | 58,132 | 17,452.10 | 362 | 0 | 27 |
| Jul | 56,293 | 16,984.00 | 350 | 0 | 26 |
| Aug | 58,481 | 16,687.40 | 343 | 21 | 29 |
| Sep | 53,447 | 15,757.80 | 334 | 0 | 25 |
| Oct | 55,368 | 16,138.20 | 346 | 0 | 26 |
| Nov | 53,756 | 15,447.70 | 336 | 0 | 24 |
| Dec | 51,494 | 14,690.85 | 323 | 0 | 27 |
| **Year** | **686,380** | **199,510.35** | **4,263** | **27** | **316** |

These anomalies are notably concentrated in **February and August**
for positive electricity without reported gas; gas-positive
power-zero readings occur across all months. Possible meter timing,
cumulative-processing, quality rules, standby usage or different physical
boundaries need independent investigation; the source alone cannot
identify the cause. The variation also confirms why an annual aggregate
cannot reveal actual starts, ramp speeds or gas-engine dynamic parameters.

## Reproducible derived charts

The dedicated online workflow uses
`scripts/plot_v0917_real.py` to produce three source-labelled
SVG figures directly from the measured monthly report:
`engine_electricity_mwh.svg`,
`engine_gas_source_m3.svg` and
`electric_gas_conflict_hours.svg`.
It checks that 8,760 monthly records and the source volume/electricity
totals agree with the independently observed annual measurements
before any plot can be generated. The CI artifact contains figures
and aggregate results **only**; no raw publisher files are committed.

## Calculation conventions

- `kW` on hourly bins integrated as `kWh`, one hour per row.
- `m3` is **the provider's literal source-volume label**. No dry
  normalization, chemical composition or gas LHV/HHV assumed.
- `GJ/h` integrated over one-hour source bins yields GJ *only under
  the source's nominal hourly-rate interpretation*. Actual sensor
  integration conventions/heat allocation are not documented here.
- Twelve monthly groups and counts are now produced to distinguish
  patterns and source anomalies without inventing subhour ramps
  or start/stop events.
- Original source dates have no asserted time-zone offset.
  No equivalent bid-time forecasting or market return is claimed.
- All original source file hashes are recorded in code and the
  v0.9.16 executed source report; they are re-verified in every online run.

## Claims and blockers

**Supported:** reproducible analysis of real externally published
hourly gas-engine electrical source data, engine gas source-volume
data and independently labelled recovered-heat channels; source
provenance, exact year, record counts, per-channel totals and
descriptive contradictions.

**Not supported:** fuel-to-electric or total CHP efficiency on an
authenticated LHV/HHV basis, measurement uncertainty covariance,
independent engine commission/test curve, verified ramp/start/stop
limits, measured Swedish anaerobic-digester biogas plant behavior,
gas storage or heat demand, grid delivery, real market profit,
independent generalizable model predictive accuracy.

The physical biogas-engine data-access plan remains
[Matlink Farm v0.9.16-C](../docs/V0916C_MATLINK_AUTHORIZED_DATA_HANDOFF.md).
This result **does not close the scientific v1.0 field-validation gate**.
