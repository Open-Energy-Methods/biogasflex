# BiogasFlex v0.9.15 — CHP time-resolved metering and independent field-validation protocol

**Milestone:** scientifically explicit *acquisition-readiness*, not successful
measurement of a real CHP unit and not a real-plant validated dispatch model.

**Data collected in this research release: ZERO real-plant observations.**
The four 15-minute records in
`examples/v0915_synthetic_chp_metering.csv` are **invented for CI QA**,
never Polish landfill measurements, Swedish Lövsta operating evidence,
manufacturer specifications, or real contract settlements.

The new offline `telemetry-qa` command validates data provenance,
mandatory time/physical units, measurement registry, instrument validity
*metadata*, time continuity and conservative first-law/balance
**screening** only. It **does not** authenticate uploaded calibration
documents, fit a model, infer a ramp MW/min from interval averages, or
certify equipment safety or performance.

## Independent source foundations and scope

- [JCGM 100:2008 — GUM, BIPM](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e)
  sets principles for measurement uncertainty; a GUM-compliant combined
  uncertainty requires an appropriate model, correlations, systematic
  corrections, calibration status and traceability.
- [NIST Technical Note 1297, Section 5](https://www.nist.gov/pml/nist-technical-note-1297/nist-tn-1297-5-combined-standard-uncertainty):
  standard uncertainties combine using sensitivity coefficients and
  **covariances as appropriate**. This program's simple bound is **not**
  offered as a substitute for a calibrated covariance model.
- [ISO 20675:2018](https://www.iso.org/standard/68794.html) is a biogas
  terminology/classification standard, **not a calibration or engine
  performance method**; use it for fuel-category clarity only.
- Keep the merged v0.9.14-A distinction between a Polish **landfill**
  CHP plant, unrelated Caterpillar/Jenbacher catalogue products, and
  a Swedish anaerobic-digestion CHP case. Their evidence is not
  interchangeably applicable.

## 1. Measurement boundaries and acquisition plan

| Measurand/channel | Location, unit and time basis | Required field evidence |
|---|---|---|
| Generator active electrical energy | Generator terminal kWh_e integrated over each **[UTC start, UTC end)** interval | Revenue-grade or adequately calibrated meter, CT/PT ratios, nameplate, instrument latency, source timestamp |
| Net imported/exported grid electricity | Point of common coupling (PCC), signed kWh_e, exported positive and imported negative | Independent bidirectional meter and site boundary |
| Non-CHP site load and CHP auxiliaries | kWh_e over the same interval, including compression/parasitic consumers where relevant | Independent meter allocation and avoid double-counting |
| Actual **engine inlet** dry gas | Nm³ at a **declared** normalization state | Meter, moisture/dry-basis correction, gas pressure/temp, calibration and known sample timing; **not** landfill gas recovered |
| Biogas produced into buffer | Separate dry-normalized Nm³ in | Metered upstream of buffer |
| Gas flared/bypassed | Separate dry-normalized Nm³ | Calibrated or otherwise independently verified totalizer; zero requires measurement support |
| Fuel lower heating value | Time-matched MJ per **dry Nm³**, with sampling transport lag documented | Gas analyzer or representative laboratory gas composition, temperature/pressure, calibration & LHV method |
| Useful recovered heat | Delivered-heat `kWh_th` at declared customer/process boundary | Commissioned heat meter; fluid flow, temperature sensors, glycol/brine composition and enthalpy correction documented |
| Buffer inventory start/end | **Directly measured** dry-normalized Nm³ at each boundary | Storage geometry, level/volume sensing, dynamic pressure/temperature and uncertainties; **do not** turn gauge pressure into inventory using an unstated tank model |
| Engine run fraction | 0..1 of interval, explicitly measured/logged | Controller/engine state timestamps; fractional interval alone does **not** identify starts, minimum dwell or ramp rates |
| Sensor clock offset | Maximum clock offset in seconds across relevant channels | NTP/PTP/DAQ verification log, clock drift and daylight-saving conversions before aggregation |

**Synchronized acquisition:** Collect raw source timestamps and meter
totalizers before resampling; align instruments to a common UTC timeline.
Check resets/rollovers, duplicate readings, exact interval boundaries,
missing SCADA rows, synchronization offsets and sign conventions.
Do **not** silently forward-fill or linearly interpolate missing electrical,
gas or heat data; maintain raw original bytes and a separate quality-flag ledger.

**Units:** 1 kWh = **3.6 MJ**. An engine fuel interval is
`E_fuel,kWh_LHV = V_engine,Nm3_dry × LHV,MJ/Nm3_dry / 3.6`.
Gas volume must be consistently dry at **273.15 K, 101325 Pa** in
this version. Other normal/standard reference conventions need
**explicit declared conversion**, not a renamed CSV header.

## 2. Monitoring resolution and actual physical validation

**15-minute interval source:** Suitable for integrated energy and
gas-volume balance screening, efficiency *descriptions* and site-export
differences after meter validation. It cannot resolve actual seconds-to-minutes
startup, short ramp sequences, minimum stable power or protection trips.

**High-frequency event source:** The *separate unimplemented design*
`data/schemas/v0915_high_rate_event_data_contract.json` specifies
controller state, independent generator power, setpoint, fuel flow,
recoverable heat, alarm/first-out, timestamps and quality flags.
The initial **1-second sampling goal is provisional**: it must be
reassessed against device frequency response, engine dynamics, sensor
lag, noise, anti-alias filtering, available acquisition channels and
site safety. Start/stop/ramp studies require event-triggered
high-frequency records and commissioning approval; do not induce trips
or override controls for this software milestone.

**Identifiability:** Distinguish no-run/starting/on/stopping/tripped
intervals, ramp-hold windows, warm-up, derating, fuel changes,
auxiliary/hot-water cycling and real constraints. Compare time-aligned
engine power to fuel flow, thermal heat recovery and initial/terminal
gas storage with stated thermodynamic boundaries. Minimum loading
requires documented stable runs; transitions require actual
high-frequency controller and meter event logs. No real data were
received, so **all physical-identifiability results remain blocked**.

## 3. Model validation and independent withholding

A credible future physical test requires:

1. Permission and instrument/tag lists from the operator; confirmed
   engine make/model and fuel gas type; no private instrument IDs or
   individual operational logs in the public GitHub repo.
2. Calibration certificates or traceable calibration procedures, instrument
   ranges, accuracy/resolution/response times, source-specific corrections,
   drift and synchronization uncertainty, and explicit covariance handling.
   The software can only check that document references **are present**.
   It **does not authenticate** the documents or assert ISO 17025 compliance.
3. Keep intact raw data, signed or operator-approved source references,
   SHA256 hashes, data license/access terms and any data redactions.
   Store confidential source files **outside the repository working tree**
   to preserve strict full-tree SHA256 release checks.
4. Predeclare equipment-specific validation tasks and load/ambient/fuel
   regimes. Hold out complete operating periods and independent starts
   or load steps from any parameter fit. Do not retrospectively tune
   on the untouched validation/test periods.
5. Report prediction error with defined power/heat/fuel boundaries,
   time-shift and sensor-lag sensitivity, residual distributions,
   bias/MAE/RMSE, uncertainty budgets and comparisons against a
   declared fixed/steady baseline. Specify accept/reject thresholds
   **before** viewing untouched test data and justify them from physical
   use cases and instrument accuracy, not arbitrary post-hoc choices.
6. Independent engineering review for safety/plant envelope,
   measurement uncertainty, model identifiability and deployment;
   separately verify any market bidding, net export and settlement
   information before claiming contract delivery.

**No model-performance metrics are computed in v0.9.15**—none could
be justified without acquired synchronized measurements.

## 4. Machine-readable quality checks and limitations

`examples/v0915_synthetic_acquisition_manifest.json` is a
**demo-only** example with 11 synthetic meter channels, each
`SYNTHETIC_UNCALIBRATED`, no certificate IDs and a frozen
CSV SHA256. The independent standard-library witness recomputes
generator/PCC/local/aux, producer/engine/flare/buffer and the 3.6
MJ/kWh LHV conversion independently from the package.

The accepted real-data manifest format requires declared engine and
nameplate provenance, source authorization, instrument tags,
calibration references and validity times, plus at least 96
contiguous quarter-hour observations (24 hours). The `--csv`
path may point to authorized data **outside the checkout**.
Even then the only possible success status is
`PASS_REAL_DATA_SCHEMA_AND_BALANCE_SCREEN_PENDING_HUMAN_VERIFICATION`.
The code never accepts a manually asserted "plant model validated" flag.

**Screening allowance:** For each quantity `x`, the declared
single-measurand "standard-u" numerical input is
`u(x) = |x| × u_rel + u_abs`, only as entered in the instrument
metadata. For a balance `R=Σ signed x`, accept the screening
if `|R| ≤ 3 × Σ u(x)`. This linear envelope is a cautious
**quality-screening heuristic**, not a JCGM combined standard
uncertainty, a confidence region, a 99.7% probability, or a guarantee
when calibration/covariance metadata are wrong. Buffer start/end
correlations are **not independently determined** by this rule.
For fuel `E=V×LHV/3.6`, a simple algebraic product bound includes
`LHV u_V + V u_LHV + u_V u_LHV` / 3.6.
A real GUM budget requires the joint covariance matrix or validated
Monte Carlo/analytical propagation and systematic corrections.

The QA screens enforce:
- Exact column/physical-unit contract; source bytes fixed by SHA256,
  finite numbers, no negative input/heat/volumes, and signed net export.
- Strict UTC [start,end) 15-minute duration, chronological contiguity,
  no duplicates/gaps/overlaps/DST ambiguity, clock offset ≤2 s.
- Nonmissing `GOOD` quality; no energy from an OFF engine, no
  generation/heat from zero measured fuel, no unexplained gas
  buffer discontinuities.
- Generator terminal electricity equals net PCC export +
  non-CHP load + CHP auxiliaries within screen allowance; generator
  interval rating check is separate from the **grid** boundary.
- Gas production = engine inlet + flare + change of dry-normalized
  buffer volume within screening allowance; measured gas normalized
  on a compatible dry basis is a prerequisite.
- Electric generation + useful delivered heat does not exceed
  engine inlet LHV plus screening allowance (necessary, not
  sufficient for CHP calibration).

The schema cannot detect false site origin, forged certificates, a
biased-but-internally-consistent sensor bundle or a fictitious
independently authored CSV. It cannot determine covariance or uncertainty
distributions from supplier brochure numbers.

## 5. Reproducible demonstration (no site data)

```bash
python -m pip install -e .
python -m biogasflex telemetry-qa
python -m biogasflex telemetry-qa --output qa_v0915_demo.json
python scripts/audit_v0915_telemetry_qa.py
python -m unittest discover -s tests -q
bash scripts/reproduce_v0915.sh
```

Windows PowerShell: `./scripts/reproduce_v0915.ps1`.

**Actual field acquisition is a future external human/site task.**
The next research gate after this package is an independently documented
and authorized real measurement campaign, high-rate event ingestion,
uncertainty-reviewed source data, and untouched-test model validation.
Neither v0.9.15 nor any earlier revision is independently peer-reviewed
scientific v1.0, and no field performance, output export contract or
actual profit is demonstrated.
