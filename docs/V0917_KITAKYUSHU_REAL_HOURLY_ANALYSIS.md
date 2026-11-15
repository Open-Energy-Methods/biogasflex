# BiogasFlex v0.9.17 — Independently measured 2005 Kitakyushu hourly CHP data study

**Scope:** independent three-archive source retrieval, timestamp-aligned
2005 **city-gas** reciprocating-engine electricity, gas-meter and recovered
heat description. Not a site-calibrated biogas dispatch model.

## Source and checked spreadsheet structure

Publisher: Liao, Jin and Li, *20-year Data of Energy Station at
Kitakyushu Campus*, figshare version 2, CC BY 4.0,
[DOI 10.6084/m9.figshare.24978645.v2](https://doi.org/10.6084/m9.figshare.24978645.v2).
The underlying study describes a campus multi-technology installation
in Kitakyushu, Japan: city-gas reciprocating engine, fuel cells and
district-energy equipment. These components have **different** electrical,
fuel and thermal boundaries.

Three published archives are actually source verified (published MD5 and
bytes plus independently observed SHA-256) by the earlier v0.9.16
[acquisition audit](../reports/V0916_REAL_PUBLIC_CHP_SOURCE_ACQUISITION_AUDIT.md).
The workbooks named below were independently inspected **inside the real
published archives** (not assumed from titles) before writing the parser:

| Archive | 2005 source workbook | Relevant exact publisher headers |
|---|---|---|
| `Power.zip` | `Power_time series__2005.xlsx` | `Date`, `Gas engine (kW)` plus separate `Fuel cell (kW)`, solar and **grid import** |
| `Gas usage.zip` | `Gas usage_Time series__2005.xlsx` | `Date`, `Gas engine (m3)` plus separate fuel cell/boiler/chiller gas volumes |
| `Heat recovery.zip` | `Heat recovery_time series__2005.xlsx` | `Date`, `Gas 1(GJ/h)`, `Gas 2(GJ/h)` and distinct fuel-cell recovered heat rates |

All three publisher workbooks' source previews contain literal time
labels of the form `2005 01-01 00:00`. The parser requires exact
hourly continuity over **8,760 non-leap-year records**, strict
source columns/labels, finite numbers and one-to-one date alignment.
It refuses duplicated/missing hours, changed header names, altered
provider bytes or source year. It decodes original XLSX shared-string
cells without pandas or openpyxl.

The original `m3` is explicitly **source volume units**, NOT
authenticated dry `Nm³`. Converting fuel gas volume to energy needs
an actual gas LHV/HHV, temperature/pressure, dry/wet state and
calibration, which are not independently authenticated in the
publication; the program **does not calculate energy efficiency**.

Similarly `Gas 1(GJ/h)` and `Gas 2(GJ/h)` are reported
as separate source heat recovery categories, **not automatically
declared useful engine heat**. Their direct allocation to the
electrical gas engine or end-use thermal services is unproven.
The sum of a `GJ/h` heat rate over 1 h is nominal `GJ` under
a piecewise constant hourly convention, but the original source
integration/processing requires metrological review.

The source clock labels are treated as **naive source local hours**.
No timezone or UTC mapping is manufactured. A source archive with
8,760 consecutive 2005 labels is not evidence for verified physical
clock synchronization.

## Reproduction

Offline, tests use **clearly synthetic fixture rows only**:
```powershell
python -m pip install -e .
python -m unittest tests.test_v0917_kitakyushu_real -v
.\scripts\reproduce_v0917.ps1
```

The actual published observational analysis requires **opt-in source
download** and checks *all three* original publisher MD5/byte
counts **and independently computed SHA256**, recorded in the
versioned module from the previous successful network acquisition:
```powershell
$report=Join-Path $env:TEMP "biogasflex_kitakyushu_2005_real.json"
python -m biogasflex real-chp-analysis --fetch --report $report
```
The direct CLI call without `--fetch` is intentionally rejected:
it cannot fabricate real source data or imply an online test was run.

Continuous source-retrieval/analysis is executed in the *separate*
`.github/workflows/v0917-kitakyushu-real.yml` and retains only the
aggregate research JSON, not multi-year original archives.

[Executed real 2005 descriptive source audit](../reports/V0917_KITAKYUSHU_EXECUTED_REAL_HOURLY_RESULTS.md):
8,760 full source-local hours; 686.38 MWh engine electric generation;
199,510.35 m³ source gas input; 4,263 jointly active engine-hour
records; 27 positive-power/zero-gas hours and 316 zero-power/positive-gas
hours. These **343 discordant hours** require instrumentation and
process context review before any physical parameter estimation.
The maximum published engine power source record was 166 kW, slightly
above a nominal 160 kWe engine article rating, which likewise needs
measurement-definition review. Do not interpret either as a measured
startup ramp, verified overrating or physical impossibility without
independent technical evidence.

## Measured-data analysis and quality gates

For each source hour, inspect the true engine-specific channels:

- Power: `Gas engine (kW)` (generator source, not export meter);
  the report's sum over one-hour slots is **kWh_e**.
- Gas: `Gas engine (m3)` (meter volume per reported hourly row,
  not energy); the sum is only raw source **m³**.
- Heat: `Gas 1(GJ/h)`, `Gas 2(GJ/h)` kept **separate**
  from fuel-cell recovery. Summed source rates integrated over
  one-hour bins are reported as **GJ**, conditional on original
  interpretation.
- Counts: source-hour coverage, paired electricity/gas hours,
  electricity-positive/gas-zero and reverse anomalies, missing
  or negative values, complete four-measurement hours, per-channel
  maximum; sample anomalous timestamps for source review.

No forward filling, assigning gas inlet LHV, interpolating operating
hours, projecting engine starts, forecasting electricity prices,
reallocating fuel-cell production or fitting MILP engine parameters.

The study must first establish whether actual measurement QA passes,
then identify trustworthy model-comparison outputs without claiming
BiogasFlex's **Swedish biogas reciprocating plant** has equivalent
hardware, fuel or dispatch boundaries. The Kitakyushu gas engine's
reported 160 kWe nominal rating is **source-identified** but
not sufficient for engineering calibration of distinct equipment.

## Scientific limits and future work

This v0.9.17 milestone is intended as **external, descriptive measured
CHP energy-accounting analysis**, not physical model verification.
It cannot validate a synthetic BiogasFlex gas buffer, ramp, minimum
generation, short start-stop events, heat delivery or site electricity
contract settlement. Those require a properly matched, independently
documented, authorized biogas-engine data package (the Matlink
access handoff remains open).

A later model-comparison study should distinguish independent
held-out observation periods, equipment parameters fitted on other
periods, process-measurement uncertainty and proper independent
source-specific channel definitions. No valid held-out engine
prediction accuracy is claimed here.
