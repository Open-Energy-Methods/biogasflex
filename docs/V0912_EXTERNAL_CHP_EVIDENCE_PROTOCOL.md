# BiogasFlex v0.9.12 — Independently published annual CHP evidence

**Scope: externally reported equipment capacity and annual performance only.**
This is a source-grounded evidence gate, **not** equipment calibration and
not a validation of the v0.9.11 hourly/15-minute contractual MILP.

## Primary source and attribution

Ciuła, J.; Kowalski, S.; Generowicz, A.; Barbusiński, K.;
Matuszak, Z.; Gaska, K. (2023).
*Analysis of Energy Generation Efficiency and Reliability of a
Cogeneration Unit Powered by Biogas*, Energies **16**(5), 2180.
DOI: https://doi.org/10.3390/en16052180.
Source Tables 1–3 and contextual Table 8.
Paper open-access (MDPI, Creative Commons Attribution 4.0).
The CSV is a numerical transcription of its original published annual rows;
original data remain traceable to their source and are not represented
as first-hand measurements by this repository.

**Fuel is landfill gas** from a municipal solid-waste landfill in
Poland, NOT gas from a farm/municipal anaerobic digester.
The paper describes recovered gas volumes and annual CHP generation.
Do **not** assume 100% of recovered volume was combusted in the engine,
that gas volume is standardized to Nm³, or that monthly/hourly CHP operation
can be reconstructed from the published annual data.

## Source-backed facts and deliberate exclusions

Published equipment: 440 kW gross electrical and 520 kW thermal rated
output (Table 1); published nameplate electrical/thermal efficiencies
37.6% and 42.8% are catalogue parameters, not observed part-load curves.
Tables 2–3: annual running hours, recovered landfill gas in m³,
electricity MWh, heat MWh for **every year 2012–2022**.
Article text gives *period-average* landfill-gas heating values
16,548.7 kJ/m³ (2012–2017) and 19,635.2 kJ/m³ (2018–2022);
these are not simultaneous annual fuel consumption measurements.

For each year the audit computes:
- calendar-year operating fraction using 8,784 h in **leap year 2020**;
- arithmetic mean generated power **conditional on annual running hours**;
- annual generated energy relative to rated power × running hours.
These are derived annual aggregates, NOT instantaneous loads or lower
operating power bounds. No per-year LHV efficiency is declared measured.
Annual capacity checks reject impossible rows and malformed data.

Source-reported annual averages and comparisons are preserved, while the
arithmetic average of the **published annual observations** is recomputed.

## Reproducible source inconsistencies — must remain visible

1. 2018–2022 annual recovered-gas values average **1,267,253.2 m³/y**,
   versus **1,291,515 m³/y** printed in Table 3/8; difference
   **−24,261.8 m³/y**. Both quantities are retained with attribution.
2. The article describes the increase in gas yield as **29.5%**.
   The tabulated period means imply approximately **39.2%** relative to
   2012–2017. Neither 29.5% nor the paper's printed post-period average
   should be substituted for the annual observations.
3. Article conclusions report a **42.78%** increase in electricity;
   the conventional percentage change with the earlier period as
   denominator is approximately **74.8%**. 42.78% corresponds closely
   to expressing the change as a share of the *later* period, i.e.,
   a different percentage denominator. We preserve both conventions.

These are a source-quality warning, not grounds to fabricate replacement
measurements. Audit status: `PASS_WITH_PUBLISHED_SOURCE_DISCREPANCIES`.
The article's use of 8,760 h as a nominal year also differs from actual
2020 leap-year hours; our yearly calendar fraction uses 8,784 h for 2020.

## Strict validity boundary for dispatch

The dataset may justify a nominal electrical/thermal **rating** in a
separately labelled Polish landfill-CHP illustration. It does **not**
identify: minimum stable electric load, ramp MW/min, warm-up,
startup cost, minimum uptime/downtime, biogas buffer capacity,
digester gas output, useful heat demand, hourly outages, gross-to-net
electricity export, hourly fuel consumption, or actual gas storage.

**Do not overwrite the inherited Lövsta/Swedish configurations, synthetic
CHP assumptions, or 2020 SE3 spot prices with these Polish annual rows.**
The plant, operating period, gas origin and market jurisdiction differ.
Do not use annual mean running power as an operating minimum and do not
run 8760 identical hourly dispatch observations from these yearly sums.

## Verification (offline)

```bash
python -m biogasflex annual-chp-evidence
python -m biogasflex annual-chp-evidence --output annual_evidence_report.json
python scripts/audit_v0912_external_chp.py
python -m unittest tests.test_v0912_external_chp -v
```

The independent witness uses standard-library CSV/arithmetic and does not
import the BiogasFlex model or optimizer. The source CSV is included in
the full SHA256SUMS release manifest and tested against tampering,
nonfinite/missing values, duplicates and infeasible nameplate outputs.

**v1.0 scientific outstanding:** time-resolved metered CHP operating
constraints, independent temperature/heat-service data, external
human methodological review, verified real market transactions
and settlement, field validation, reproducible uncertainty budgets.
Neither a public GitHub Release nor Zenodo DOI is implied by this stage.
