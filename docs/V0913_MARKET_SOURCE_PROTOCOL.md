# BiogasFlex v0.9.13 — Source-verified retrospective market prices and bid-time evidence refusal

**Software evidence milestone only:** original 2020 SE3 market prices
are real archived observations. The source archive was created and
retrieved in 2026 and does **not** prove what individual historical
auction price information or participant-specific accepted awards
were available by 2020 D−1. This extension never invents
market-result publication timestamps, auction clearings,
real forecasts or plant grid-export measurements.

The independent published **2012–2022** annual landfill-gas CHP
reference and its discrepancies are already independently
verified and merged in **v0.9.12**:
[annual CHP source protocol](V0912_EXTERNAL_CHP_EVIDENCE_PROTOCOL.md).
v0.9.13 **reuses that exact SHA256-pinned source and its independent
audit**. No duplicate representation of the same paper
as a second plant validation was added.

## 1. Grounded Swedish historical data

Provider: **Svenska kraftnät**, `Dagen före-priser per elområde`,
resource `cf392ef3-7345-4e98-970e-83088c185570`,
[official source](https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/cf392ef3-7345-4e98-970e-83088c185570),
licence CC BY 4.0. Source records include
`start_time_utc`, `bidding_zone`, `price` and `price_unit`.
The original frozen BiogasFlex 2020-04-01 SE3 historical
sample is **24 hourly records**, UTC 2020-03-31T22:00 through
2020-04-01T21:00 (last observation start).
The exact source archive SHA256 is
`560415b0b38fd764c64bf40c182737d60b94838a39db677da96f7649ba4661b0`.
No data modifications, interpolation or extra assumptions.

Independent arithmetic oracle: simple sum of 24 prices
**167.71 EUR/MWh** (mathematical sum of quoted price
numbers, not revenue), mean **6.9879166667 EUR/MWh**.
Source-date, zone, time grid, unit, source hash and
the repository's own manifest entry are verified offline.
Naive timestamps, DST misalignment, duplicated UTC
hours and missing or wrong price-source units reject.

### Why 2020 day-ahead 'as-of' is not verified

The **retrospective dataset record** was published
**2026-04-09**. The frozen CSV copy was retrieved
**2026-11-05**, as documented by the existing attributed
repository snapshot. Its rows are genuine past
prices, but the archive does not carry proof of
the **original 2020 D−1 auction publication
time or a participant-specific award receipt**.
A 2026 resource-copy date does not imply the
historical auction only occurred in 2026;
conversely it does not prove the exact 2020 time
at which a participant had usable data.

The test hypothetical **2020-03-31T09:00Z** preauction
decision precedes the local 2020-04-01 delivery day.
The source's 2026 creation/retrieval dates cannot
be backdated to provide an ex-ante forecast or
D−1 participant information proof. Strict rejection
of `original_per_interval_publication_proof`
fabrication and source publication date manipulation
is part of the test suite.

**Allowed:** retrospective observed price benchmark.
**Not allowed:** claims of retrospectively trained
true ex-ante forecaster accuracy or real matched
awarded MWh just because 2020 prices are known today.

## 2. Interface to the already-source-audited annual CHP

v0.9.12's annual CHP source:
Ciuła et al., *Energies* (2023) 16(5), 2180,
DOI [10.3390/en16052180](https://doi.org/10.3390/en16052180),
CC BY 4.0; a **440-kW_e / 520-kW_th Polish
municipal landfill-gas CHP**, annual running hours,
gross electricity, useful heat and recovered gas
2012–2022. It is not digester gas, not Swedish
site data, and not a calibration of the synthetic
BiogasFlex CHP `examples/v0911_synthetic_chp.json`
(**0.8 MW_e** nameplate).

v0.9.13 invokes the **same existing independent
v0.9.12 annual source auditor**, which preserves
original source-reported arithmetic conflicts
(2018–2022 published mean recovered gas
1,291,515 m³/y vs recomputed 1,267,253.2 m³/y).
No second CSV, independently sampled plant,
new electrical efficiency estimate or hourly
SCADA trace is invented.

These two evidence classes are incommensurate:
2020 price data are historical observed electricity
trading outcomes; 2012–2022 published annual CHP
logs concern a different physical plant.
Combining them **does not calibrate either
a 2020 day-ahead bid or the v0.9.11
hourly/15-minute contractual MILP**.

## 3. Explicit fail-closed operational gate

`python -m biogasflex market-provenance` produces
source-verified ex-post pricing and the linked
published annual CHP study's identity, reported
arithmetic discrepancies, unit and rated-power
information, all without network access.

The original `contract-dispatch` default remains
an explicitly hypothetical solver demo.
An optional flag
`python -m biogasflex contract-dispatch --require-operational-validation`
requires a different evidentiary standard and must
fail with **REAL_OPERATIONAL_VALIDATION_BLOCKED**.
No override by setting a JSON boolean or retyping
`published_at` is accepted. This does not
prevent exploratory synthetic runs; it prevents
false escalation to field validity.

Before this gate could ever pass, it needs
a separate future evidence class based on:
1. independently timestamped bid-time forecast
   feed and original auction result/participant
   receipt snapshots with as-of and correction logs
2. matched CHP plant identity, measured fuel
   volumes, LHV/CH₄, generator/heat power,
   startups and ramps at sufficient resolution
3. metered grid delivery (net export/import),
   site parasitic electrical demand and
   actual participant-awarded contract volumes
4. control instrumentation uncertainty,
   gas store history and separate untouched
   time-matched validation data
5. real market settlement and imbalance
   tariffs if economic profitability is claimed

The licence and chronology of the *retrospective*
datasets do not satisfy these requirements.

## 4. Offline cross-platform reproduction

```bash
python -m pip install -e .
bash scripts/reproduce_v0913.sh
python scripts/audit_v0913_market_provenance.py
python -m biogasflex market-provenance
python -m biogasflex market-provenance --output market_evidence.json
# Must fail closed, by design:
python -m biogasflex contract-dispatch --require-operational-validation
```

On Windows: `./scripts/reproduce_v0913.ps1`.

All frozen original 286 scientific files, inherited
216 historical LP primal-dual certificates, 96
solver-free LP tests, original 216+5 scenarios,
v0.9.5–v0.9.12 synthetic commitment and external
annual CHP audits remain release requirements.

This is **not** a peer-reviewed scientific v1.0,
realized power-market profitability, field control
validation, measured storage calibration or
an actual site-operator contract. The external
human review gate [issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains open; no public Release or DOI.
