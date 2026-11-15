# BiogasFlex v0.9.16 — Public, real CHP time-series acquisition and strict transfer boundaries

**Date of source audit:** 2026-11-15  
**Research status:** external published-source acquisition and source-integrity audit,
**not** calibrated engine CHP, hardware ramp/turn-down validation or evidence
of participation in an electricity market.

## 1. Why these two external sources

Source inventory: `data/evidence/v0916_public_chp_source_registry.json`.
The two cases are **deliberately separate** in physical identity and fuel:

| Source | Technology and fuel | Measured data | What it cannot prove |
|---|---|---|---|
| RISE, Luleå, Sweden, [Zenodo 14163174](https://doi.org/10.5281/zenodo.14163174), November 2024, CC BY 4.0 | **Solid oxide fuel cells running on compressed automotive-grade biogas**, 2023-01-11 to 2023-06-16 | `FCData`: gas use and electric generation; `MeterData`: five independent meter channels; `ThermalData`: heat transfers; `DhSubstation`: heat delivered | **Not reciprocating engine CHP**; no measured engine minimum load, ramp or starts; no site-calibration certificate authenticated |
| Liao/Jin/Li, Kitakyushu, Japan, [Figshare 24978645.v2](https://doi.org/10.6084/m9.figshare.24978645.v2), April 2024, CC BY 4.0; described in [*Scientific Data* 11, 1400 (2024)](https://doi.org/10.1038/s41597-024-04244-6) | **160 kW gas-engine CHP plus separate fuel cell supplied by city gas**, 2001–2016 engine period | Hourly `Power.zip`, `Gas usage.zip`, `Heat recovery.zip`; archive spans 2001–2022 | **Not biogas**; cannot infer second/minute ramps from 1-hour mean; published gas volume reference/engine part-load calibration not independently documented |

The RISE case is a stronger *fuel and geographic* analogue, but its
fuel-cell conversion physics differs from the BiogasFlex reciprocating
engine. The Kitakyushu case is a stronger *equipment technology* analogue
but uses **city gas**, not Swedish anaerobic-digester or Polish
landfill gas. Do not splice the two data sets together as one fictional
site or estimate universal CHP operating limits from them.

The journal describes Kitakyushu gas-engine/FC electrical production,
separate equipment gas use and gas-engine heat recovery at **1-hour
resolution**. It identifies a nominal **160 kW** gas engine (rated
electrical efficiency **28.7%** in its article) and operation through
July 2016. Neither this value nor the measured series is evidence
for the previously studied **440 kWe Polish landfill CHP**, which is
separately source-audited in v0.9.12.

## Additional high-value, not-yet-retrieved match: NYSERDA Matlink Farm

The [NYSERDA project-516 Matlink Farm site](https://der.nyserda.ny.gov/facilities/567/?project=516)
describes a **145 kW Waukesha reciprocating generator using actual anaerobic
digester gas**, with documented monitoring October 2004 to July 2005.
Its [performance portal](https://der.nyserda.ny.gov/reports/view/performance/?project=516)
displays **225,083 kWh** aggregate generation and **13,407 Mcf**
biogas input, as well as source-flagged monthly efficiencies.
The [2006 measurement/database notes](https://dataint.s3.amazonaws.com/docs/proj_516/Database_Notes_-_Matlink_Farm.pdf)
describe **91 channels captured at 15-minute intervals**, including a generator
cumulative kWh meter and the engine-biogas cumulative gas meter, but do not
clarify every interval's heat-flow integration and local-time interpretation.
The public portal exposes an hourly/day/month CSV download interface;
in the current automated browser test, the direct export was challenged
by an access WAF. **No raw Matlink CSV has been received, source-hashed or
approved for BiogasFlex calibration**. The site's explicit redistribution
license has not yet been established.

Several monthly computed efficiencies shown on the portal appear physically
inconsistent (**2858.5% HHV** in October 2004, **545.8% HHV**
in December 2004), and a nonzero November electricity total is displayed
beside rounded or zero monthly gas input. These are a data-quality
**warning, not values to use**. The 91 signals are not independently
verified as calibrated, and published hourly data cannot prove actual
seconds-scale starts/ramps.

The machine-readable blocked candidate,
`data/evidence/v0916_matlink_biogas_engine_candidate.json`,
pins these constraints and an authorized manual export path.
Acquisition procedure: use NYSERDA's **Performance -> Data -> HR**
interface to export one **January 2005** month *both with and without*
automatic quality filtering; preserve the raw CSV, URL, filter state,
local-time/DST conversion, size and SHA256 under reviewed permitted-use
terms. Ideally obtain the original 15-minute records and instrument
calibration references from the data custodian.
**Do not bypass site access controls or assume a portal screenshot
constitutes source-verified numerical calibration**.

## 2. Acquisition contract and source files

Seven **published originals** are identified and SHA256 is computed
from their *actual received bytes* only after explicit network opt-in.

| Original file | Published checksum | Transfer |
|---|---|---|
| RISE `FCData_v2.xlsx` | MD5 `c9d0d97a0e16ccec9552ac7e8c17880e` | Source-retrieval only |
| RISE `MeterData_v2.xlsx` | MD5 `e59a10e63d1ae5379cae8dcac32543f5` | Source-retrieval only |
| RISE `ThermalData_v2.xlsx` | MD5 `1816bdbd305b8c4a5734157e916070b3` | Source-retrieval only |
| RISE `DhSubstation_v2.xlsx` | MD5 `781c92e932ff0b794d174e8d3863ed21` | Source-retrieval only |
| Japan `Power.zip` | MD5 `c005150c3da98c822ad7ad6818e98658` | Source-retrieval only |
| Japan `Gas usage.zip` | MD5 `ac5bdca572e3fd14ed9a506e2e4abb80` | Source-retrieval only |
| Japan `Heat recovery.zip` | MD5 `76dea6064810b26ffabf646a125ca487` | Source-retrieval only |

The **original file sizes**, source/provider URLs, DOI, license,
author names, dates, *fuel class*, *equipment type*, possible and
prohibited uses are stored in JSON. Source MD5 is an attributed
upstream file-identification check, **not** a high-security
signature. SHA256 calculated at retrieval is a reproducibility
fingerprint, not proof of calibrated physical accuracy or dataset
authenticity beyond the provider link.

The downloader refuses path traversal and archive expansions beyond
limits; it only inspects workbook sheet names, raw value cells,
declared dimensions and nested file inventories. A workbook's first
few cells are **not** a verified channel mapping or unit test.
No Excel serial-date conversions, time-zone assumptions, missing
value interpolations or fuel LHV conversions are silently made.
It retains neither source binary nor decrypted private data in Git;
hosted artifacts contain only SHA256/MD5, file names and structural
source profiles, never raw readings beyond small sheet header previews.

## 3. Offline use and external real source retrieval

Offline metadata/source-applicability inspection:

```powershell
python -m pip install -e .
python -m biogasflex public-chp-sources
python -m unittest tests.test_v0916_public_chp_sources -v
```

Explicit online retrieval of original, publicly CC-BY-licensed bytes:

```powershell
$dest = Join-Path $env:TEMP 'biogasflex-public-chp-audit.json'
python -m biogasflex public-chp-sources --source all --fetch --report $dest
```

Do **not** use `--fetch` in the numerical/offline CI gates.
Independent GitHub Actions workflow
`.github/workflows/public-chp-source-acquisition.yml` runs the
optional retrieval in an ephemeral runner and uploads only the
source-integrity report; no real-plant confidential records.

**Versioned status criteria**:
- `PASS_SOURCE_METADATA_SCOPE_NOT_YET_DOWNLOADED` — provider URLs and checksums identified, but bytes **not downloaded**.
- `PASS_REAL_PUBLISHED_SOURCE_RAW_BYTES_AND_SCHEMA_STRUCTURE_AUDIT_NO_ENGINE_CALIBRATION` — provider bytes actually received and matched their declared sizes/MD5, with a separate SHA256 fingerprint and workbook/ZIP structure preview. This is **not real CHP performance validation**.

A future distinct *source-specific parser* can be written only after
inspection of actual sheets, physical units and timestamp columns,
with trained and untouched periods, proper uncertainty assumptions
and independent validation. Never relabel output gas meter totals as
standard-dry `Nm³` until pressure, water content and reference
conditions are confirmed; do not treat grid import as net export.
For the Japanese case, city gas lower-heating value is **not** inferred
from nominal CHP efficiency. Fuel-cell and engine heat paths are not
interchangeable. Raw-data provenance is separated from fitted-engine
model support.

## 4. Required access to complete real biogas gas-engine validation

Neither public source has a **known, authenticated, complete**
combination of a reciprocating **biogas gas-engine CHP**, second-level
startup/ramp logs, calibration certificates, measured normalized
engine-inlet fuel/LHV, thermal and generator/PCC metering, gas-buffer
state and time-matched controller events. The official plant-specific
v0.9.15 schema remains the gating criterion for actual physical
dispatch validation. Source availability does not make an engine
automatically identical to the synthetic BiogasFlex equipment.

A future authorized data-sharing agreement should cover:
1. Named engine manufacturer, package revision, installed serial
   or pseudonym with source-verified technical specification; fuel
   type and composition.
2. Raw and unmodified generator-terminal and grid-export totalizer,
   actual fuel flow/composition/LHV, useful heat, digester/flare/
   buffer in/out and time-synchronized engine ON/START/STOP/TRIP
   and setpoint/power records, preferably **1–10 s** around events
   and consistent 15-minute energy integrals.
3. Meter model, calibration certificate and period, clock accuracy,
   accuracy/uncertainty and cross-correlation, site sensor boundary
   and data transformations.
4. Operator permission, licensing and privacy protection, secure
   transfer, a pre-agreed training/tuning holdout boundary and
   methodological review; no operational safety interventions.
5. Real independent generator/PCC electrical distinction and
   chronological electricity market award/settlement data before
   evaluating market performance.

### Suggested data-access inquiry (not sent)

> Subject: Research data collaboration — measured biogas CHP operating
> evidence and independent validation
>
> Dear Research/Plant Operations Team,
>
> I am developing an open-source engineering research model for
> gas-fired CHP flexibility, integrating gas-buffer constraints,
> useful-heat service and electricity delivery.
>
> I am seeking a permissioned, anonymized or otherwise shareable
> dataset from an identified biogas reciprocating-engine CHP plant:
> time-aligned electric generation and grid export, actual engine
> inlet gas flow and composition/LHV, recoverable/delivered heat,
> buffer inventory, on/off and start/stop events, and any available
> high-frequency ramp tests or controller records.
>
> The objective is independent physical validation with clearly
> declared instrument calibration, uncertainty and strict separation
> of training and untouched test periods. I can work under an
> institutionally approved data-sharing agreement and keep any
> restricted raw records outside the public repository.
> I would welcome a discussion of available signals, sampling
> intervals, permitted publication of aggregate non-sensitive
> validation findings and the appropriate collaboration process.
>
> Kind regards,
> BiogasFlex research project

This template is not an indication that an operator has consented,
a dataset has been granted, an email has been sent or that a formal
safety/measurement audit is complete.

## Release gate

A v0.9.16 *real-source acquisition* milestone can be accepted when
all original downloaded files pass provider source checks, their
per-source schema preview is archived as a generated research
artifact, inherited full offline regression/manifest gates pass and
no prohibited CHP calibration assertions are introduced.
**Scientific v1.0 remains blocked until a properly matched biogas
engine dataset, measured ramp/heat/fuel tests and independent human
review exist.**
