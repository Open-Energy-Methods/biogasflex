# BiogasFlex v0.9.16 — Executed external real CHP source retrieval audit

**Execution:** 2026-11-15; GitHub Actions independent online run
[43704165251](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43704165251).
**Acquisition:** successful source-size/MD5 and computed SHA256 verification
of **seven genuinely published original source files**, not just metadata.
No private raw data have been committed; GitHub Actions artifacts retain
the compact provenance/structure report, not the original source binary.

## Independently observed published original file fingerprints

| Identity | Original source | Received bytes | Calculated SHA-256 | Publisher MD5 verified? |
|---|---|---:|---|---|
| RISE, Swedish **biogas SOFC** | `FCData_v2.xlsx` | 2,862,185 | `e7d430db98196428e06864c8c3b35eb8a46d081b381d59415bcb87e17217bcc4` | Yes |
| RISE, Swedish **biogas SOFC** | `MeterData_v2.xlsx` | 1,469,441 | `38e54d310458efe87b0ab81d2dca42a7a5715ba6c8b71dfb252f4ef5f021848b` | Yes |
| RISE, Swedish **biogas SOFC** | `ThermalData_v2.xlsx` | 1,749,672 | `373cac127043a9c1f10103358b2af48e99715ca4b0ac114fd8a893bafab0ce80` | Yes |
| RISE, Swedish **biogas SOFC** | `DhSubstation_v2.xlsx` | 9,341,756 | `9a8e39f0cc0b4e3116fac53b829f2bee2fa1b54d9571da546c7cf5a0048da703` | Yes |
| Kitakyushu, Japanese **city-gas engine/FC** | `Power.zip` | 5,272,497 | `07080996e8f1686c79d06c6a37a76a775b534d92c94f9d57d623e3ad77156444` | Yes |
| Kitakyushu, Japanese **city-gas engine/FC** | `Gas usage.zip` | 6,996,876 | `c69525c06785fe4e3ccf6f54edc57d3ccd4ea6c6b9f1e8d3631dec4f30fc1f1a` | Yes |
| Kitakyushu, Japanese **city-gas engine/FC** | `Heat recovery.zip` | 5,642,319 | `7d4bec1a873f7a4603b446ac248fc2679345b34c396b57759f8826345b4f57fa` | Yes |

The above SHA256 values are **download-derived observations**, not
publisher SHA256 values; the repository also pins the published MD5 and
byte counts in `data/evidence/v0916_public_chp_source_registry.json`.
Re-running the online workflow checks byte-for-byte equivalence to
these provider-published MD5s and reports new SHA256 for each file.
A changed source file should cause an explicit **failure** until
source version/revision and licensing are reviewed.

## Data structures confirmed

RISE workbook counts in the downloaded original files:
`FCData_v2.xlsx` **12 worksheets**,
`MeterData_v2.xlsx` **7 worksheets**,
`ThermalData_v2.xlsx` **3 worksheets** and
`DhSubstation_v2.xlsx` **6 worksheets**.
All three Kitakyushu provider ZIP files contained nested original
workbook data which passed the bounded structure inspection.

**This is NOT channel-level value/units/timestamp validation.** The
XLSX inspector deliberately reports literal Excel cells and sheet
structures without inferring shared strings, dates, instrument sign
conventions, gas-normalization state or accurate electrical/heat
balances. Recovered/downloaded evidence is **not proof** of physical
calibration, fuel quality, start/stop events or actual electricity
market participation.

## Most directly relevant unmatched source still pending

The NYSERDA [Matlink Farm 145 kW Waukesha digester-gas engine](https://der.nyserda.ny.gov/facilities/567/?project=516)
is a stronger match of **both hardware class and fuel**.
Its project portal and instrumentation notes document historical
2004–05 15-minute monitored channels and hourly performance.
However **no raw CSV was obtained or checksum verified**:
the remote browser was challenged by website access controls, the
raw-data reuse terms and instrument calibration information have
not been verified, and the portal shows anomalous monthly calculated
efficiencies. See
`data/evidence/v0916_matlink_biogas_engine_candidate.json`.

## Strict claim boundary

- **Completed:** public-source discovery, source attribution/CC BY
  licensing of RISE and Kitakyushu, retrieval of seven original
  published files, provider MD5/file-length matching, computed SHA256,
  safe ZIP/XLSX structure inspection and downloadable provenance
  reports from the linked workflow.
- **Not completed:** acquisition of source-matched **biogas
  reciprocating-engine** complete raw gas/heat/electric interval
  records, external calibration certificates, high-frequency
  engine startup/ramp traces, GUM uncertainty budget and independent
  held-out biogas-engine performance validation.
- **Never equate** a SOFC operated on biogas with a reciprocating
  engine, or a city-gas reciprocating engine with an
  anaerobic-digester gas engine.
- **No v1.0 scientific release claim** is warranted by source
  integrity alone.

The only defensible publication-language result is **verified
retrieval of two distinct publicly licensed real CHP measurement
archives**, with carefully scoped potential to test generalized
meter-data processing after a separate channel-level source audit.
