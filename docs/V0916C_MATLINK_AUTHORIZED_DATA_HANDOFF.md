# BiogasFlex v0.9.16-C — Matlink Farm authorized historical data-access handoff

**2026-11-15. Acquisition status: no Matlink raw CSV obtained.**
The target is a historically monitored **145 kWe Waukesha
anaerobic-digester-gas reciprocating CHP** at Matlink Farm, New York,
NYSERDA DER project **516**, not the previously downloaded Japanese
city-gas engine or Swedish biogas fuel-cell installation.

## What was independently established

- Official [NYSERDA Matlink Farm facility](https://der.nyserda.ny.gov/facilities/567/?project=516)
  and [performance data](https://der.nyserda.ny.gov/reports/view/performance/?project=516)
  describe this real biogas reciprocating-engine project.
- Original March 2006
  [Matlink Farm database/instrumentation notes](https://dataint.s3.amazonaws.com/docs/proj_516/Database_Notes_-_Matlink_Farm.pdf)
  describe 91 instrument fields, recorded as **daily 15-minute CSV**.
  Public hour/day/month views are a **derivative**, not an
  independently verified equivalent of original instrument time series.
- Cumulative generator electrical and biogas volume totalizers need
  differencing, meter-reset/rollover checks and source timestamps.
- Original logging had Eastern local clock dates; fixed EST
  presentation is not a trivial gap-free mapping across DST.
- The recorded heat-recovery channels have unresolved instantaneous-rate
  versus integrated-energy semantics; no unreviewed conversion into
  `kWh_th` is admissible.
- The March 2006 notes include a gas heating-value conversion
  expressed as **0.600 MBtu per cubic foot**. This wording must be
  confirmed against the source's actual physical unit, numerator,
  normal/dry volume reference and gas composition. **Do not silently
  correct or implement it based on expected gas LHV.**
- The public monthly reporting contains apparent electric-efficiency
  errors well above 100%. No historical published efficiency is used
  to calibrate engine performance until raw records, meter boundaries
  and fuel energy accounting have been independently rechecked.

## Documented access outcome

The official portal provides a Data/Download selection with hourly,
daily and monthly periods. The prior automated direct download was
blocked by a website access-control response. **No attempt to bypass
its access controls is part of BiogasFlex.** The appropriate request
goes to the [NYSERDA DER data-management program](https://der.nyserda.ny.gov/resources/data-submissions/):
the referenced data submissions document gives
`der@frontierenergy.com` as a contact. Frontier Energy describes
its [DER program role](https://frontierenergy.com/distributed-generationchp-integrated-data-system).

A tailored email has been **saved as a user Gmail draft only**;
no outbound message was sent and no recipient consent or response has
been received. This GitHub project keeps **no private email body,
account IDs or personal contact information**. The source-access
register contains the institution's **public** data-contact address
and the boolean `contact_attempt_sent: false`.

## Required evidence before scientific reuse

The versioned [access register](../data/evidence/v0916c_matlink_source_access_register.json)
specifies nine acquisition conditions:

1. **M1:** Original Oct 2004–Jul 2005 15-minute CSV (January 2005
   minimum sample) or explicitly authorized export with raw bytes
   and a newly measured SHA-256 digest.
2. **M2:** Measurement tag dictionary and exact generator-terminal,
   grid and process/fuel/gas meter boundaries.
3. **M3:** Cumulative meter rollover/reset, sampling versus
   rate/energy integration, missing readings and quality-flag rules.
4. **M4:** Local-clock/DST source semantics and reproducible UTC alignment
   without undocumented row insertion/interpolation.
5. **M5:** Actual dry/wet/normal gas-volume reference, gas
   LHV/HHV/composition and the anomalous published BTU conversion.
6. **M6:** Confirmed useful-heat and auxiliary boundaries, flare and
   buffer measurements, and source plant architecture.
7. **M7:** Instrument calibration, validity, response time, data
   acquisition and reproducible uncertainty assumptions.
8. **M8:** Permission for storage, derived analysis, publication and
   redistribution; raw data never uploaded publicly without permission.
9. **M9:** Independent high-rate power and controller-state records
   if available; 15-minute averages are insufficient to identify
   second-level starts/ramps or trip permissives.

A downloadable hourly series alone is **not sufficient** to certify
startup, minimum power, ramp limits or gas storage. During acquisition,
keep a distinction between *receipt of source bytes*, *source
hash/permission*, *unit/time/instrument metrology*, *independent
time-series audits* and ultimately *untouched-holdout model validation*.

## What to do once access is granted

Store the original acquired files **outside the repository checkout**,
preserve their exact bytes and an acquisition ledger with source URL,
request/filter parameters, local time, source permission and computed
SHA-256. Do not publish files unless rights expressly permit it.
Review instrument dictionary and time basis before importing.
Generate an independent data-quality report, map only channels whose
units and physical boundaries have been verified, then test fuel
energy/heat/electric balances with a complete traceable uncertainty
budget. Independently reserve a holdout period before fitting any
CHP parameters. Do not use the synthetic demo's 15-minute QA success
status as proof of industrial predictive accuracy.

**Blocker:** A source custodian must provide or authorize the Matlink
original data and its metrology/reuse information. Until then:
`data_received=false`, `source_license_verified=false`,
`biogasflex_engine_model_site_calibrated=false` and
`v1_physical_validation_completed=false`. These are intentional
scientific gates, not software defects.
