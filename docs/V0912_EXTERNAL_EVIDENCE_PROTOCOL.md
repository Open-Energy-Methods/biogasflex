# BiogasFlex v0.9.12 — External price provenance and independent annual CHP observation checks

**Status:** externally sourced **retrospective data audit**, not CHP
dispatch validation. The 2020 Svk prices were traded historically, but
this archive lacks a preserved original 2020 delivery-specific
publication event. The independent CHP observations are published
**annual summaries from a different 440-kW generator**. No measured
hourly operating limits for the synthetic BiogasFlex CHP are available.
The `--require-operational-validation` gate therefore deliberately
**fails**. It must never be bypassed by changing a label.

## A. Source-verifiable retrospective electricity prices

Official source: Svenska kraftnät, *Dagen före-priser per elområde*,
public resource ID `cf392ef3-7345-4e98-970e-83088c185570`,
[official data resource](https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/cf392ef3-7345-4e98-970e-83088c185570),
CC BY 4.0.

The existing untouched source
`data/observed/svk_se3_2020_april_01_CC-BY-4.0.csv`
contains exactly 24 successive UTC hourly SE3 prices for
2020-04-01 Stockholm local date. The CSV SHA256 is
`560415b0b38fd764c64bf40c182737d60b94838a39db677da96f7649ba4661b0`,
identical to the frozen repository manifest. Its 24-row price
sum is **167.71 EUR/MWh** (arithmetic sum of hourly
EUR/MWh figures, NOT an energy-weighted total);
mean **6.9879166667 EUR/MWh**. No gaps,
interpolation, duplicate timestamps, incorrect time zones,
bidding zone substitution or unpinned data are accepted.

**Provenance red line:** Svk's relevant resource record
was created/published on **2026-04-09** and the specific
reformatted frozen CSV was retrieved **2026-11-05**.
The original 2020 price auction took place earlier, but
neither this resource nor the archived CSV contains
an independently preserved **per-delivery-day original
auction publication timestamp or participant receipt**
to verify an information set as of **2020-03-31**.
Therefore the result is **observed historical prices only**,
not historical bid-time forecasts, as-of-available
post-clear auction notifications or verified ex-ante data.
Recording the source today does not retroactively establish
a timestamp in 2020. The audit intentionally rejects
attempts to backdate this frozen resource or claim
`original_per_interval_publication_proof` when absent.

Original price data remain unmodified and are not
fed to the `contract-dispatch` as though the
observed price file were an ex-ante forecast.

## B. Independent measured CHP *annual* operating reference

Source: Ciuła, Kowalski, Generowicz, Barbusiński,
Matuszak and Gaska (2023), *Analysis of Energy
Generation Efficiency and Reliability of a Cogeneration
Unit Powered by Biogas*, **Energies 16(5), 2180**,
DOI [10.3390/en16052180](https://doi.org/10.3390/en16052180),
CC BY 4.0, published 2023-02-24.

A 440 kW_e / 520 kW_th **landfill-gas CHP** at a
municipal landfill in Poland. Source Table 1 contains
the **rated** capacities, not measured performance curves.
Tables 2 and 3 report 11 annual records (2012–2022)
based on plant operating logs and meter measurements:
runtime hours, recovered landfill gas (m³/year),
electricity generated (MWh/year), and heat generated
(MWh/year). The repository transcribes **each 11
annual row** in
`data/external_validation/ciula_lfg_chp_annual_2012_2022_CC-BY-4.0.csv`.
It provides source licence, DOI, source tables and
a SHA256-pinned immutable transcription.

The independent calculations are `annual_MWh/running_hours`
in MW of **mean output while the plant was recorded
running**, and percentages of *rated* nameplate.
Neither quantity is minimum load, a power
ramp measurement, a starting transient, a control
curve, gas-electric LHV conversion efficiency or
energy at the grid meter.

| Period | Years | Mean annual operating hours | Mean annual gas m³ | Mean annual electricity MWh | Mean annual heat MWh | Runtime-weighted electric MW |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2012–2017 | 6 | 7489 | 910,533 | 1219.3917 | 1615.935 | 0.162824 |
| 2018–2022 | 5 | 7848.2 | 1,267,253.2 | 2131.222 | 2799.444 | 0.271556 |

The article's **published Table 3 'Average' row**
gives 2018–2022 annual recovered gas **1,291,515 m³**,
**but the five underlying published annual figures
sum to 6,336,266 m³**, averaging **1,267,253.2 m³**.
That is **24,261.8 m³/year** lower than the reported
mean. The audit flags and preserves the inconsistency
rather than silently replacing the author's published
figure or claiming one is a verified metered reading.
Energy averages agree with the authors' rounded rows.

**External validity:** The 440-kW external landfill-gas
engine is *not* the same as the arbitrary **0.8-MW
synthetic CHP** in the BiogasFlex v0.9.11 test model.
Earlier and later study years also differ in landfill
gas composition and monitoring procedures. This dataset
is an **independent annual scale/plausibility reference**,
not a calibration of BiogasFlex hourly output,
thermal/electric efficiency or grid export.
It does not identify ramp limits, minimum stable load,
minimum dwell, actual startup fuel, heat uncertainty,
asynchronous storage dynamics or meter uncertainty.
Such values must remain hypothetical in the dispatch
model, irrespective of this source's peer-reviewed status.

## C. Strict operational-readiness gate

`python -m biogasflex evidence-audit` produces a
reproducible *retrospective-source verification*
summary. Use `--output evidence_report.json`
to opt into the complete provenance and annual
numeric evidence report. No file is produced by default.

The existing `python -m biogasflex contract-dispatch`
remains explicitly **synthetic** and reproducible.
Adding `--require-operational-validation` attempts
the evidence gate **before** the physical optimization.
It intentionally terminates with
`REAL_OPERATIONAL_VALIDATION_BLOCKED` because:
- archived day-ahead price records do not prove
  which day-ahead forecast/price notification
  was originally available at historical bid time
- the independently measured 2012–2022 CHP
  aggregates belong to a different plant
- annual records cannot validate generator-level
  15-min/hourly electrical/thermal/ramp/dwell envelopes
- no participant-specific historical accepted bids,
  actual net-export metering or balance settlements
  exist in the current BiogasFlex source library

The gate is a *negative* scientific result on
available evidence. It never self-certifies a
self-reported `published_at` timestamp or author-
claimed plant label as independent proof. **Even if all
result flags are manually toggled to true, v0.9.12
still refuses an operational certificate**; a future
source-integrity and time-matched experimental
validation protocol is required for any real pass.

## Reproduce offline, with inherited scientific freeze

```bash
python -m pip install -e .
bash scripts/reproduce_v0912.sh
python scripts/audit_v0912_external_evidence.py
python -m biogasflex evidence-audit
python -m biogasflex evidence-audit --output evidence_report.json
python -m biogasflex contract-dispatch --require-operational-validation
# the last command MUST fail closed as designed
```

Windows: `./scripts/reproduce_v0912.ps1`.

Original **286** pinned scientific sources/results
and all prior historical source, dual/LP certificates,
216+5 sensitivity/interruption cases, v0.9.5–v0.9.11
hypothetical optimization and adversarial checks
remain inherited version-specific release gates.

## D. What evidence would be needed for plant-specific scientific validity?

At minimum, independently documented:
1. Bid submission and market price/award **as-of**
   timestamps with preserved original payloads,
   source identities, corrections and licence
2. Participant-specific awarded MWh, net grid
   meter MWh, import/export boundaries, and
   settlement/imbalance terms
3. Hourly/15-minute or higher-frequency
   **site-matched** biogas input flow, pressure,
   methane concentration, gas LHV, power and
   recovered heat; instrument calibration,
   uncertainty, handling of downtime and missing
   data
4. Dedicated startup/stop/ramp/dwell test events
   with uncertainty, ambient/loading conditions
   and independent untouched validation sets
5. A holdout validation protocol with physical
   constraints, error bounds and explicit evidence
   of any negative/null results

Until these records exist, do **not** relabel the
v0.9.12 annual reference as a field-calibrated
rolling CHP dispatch model, financially validated
market participation, or a citable v1.0 scientific
result. Independent methodological review
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains open. No public release/DOI warranted.
