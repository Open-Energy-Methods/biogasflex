## v0.9.19 — 2026-11-15 — Endogenous CHP on/off flexibility and independent primal–dual verification

- Executed **46 actual mathematical optimization cases** in
  the dedicated research workflow, with **1,736 quarter-hour
  observations**, 46 independently reconstructed LP KKT
  tests and an exhaustive 2^8=256 binary-pattern global
  case witness. **Six** solver-optimal MILP schedules actually
  chose OFF/restart; the maximum was 2 starts per 6h case.
  Full source-derived results and three distinct price-path
  Pareto tables in
  `reports/V0919_EXECUTED_ENDOGENOUS_FLEXIBILITY_KKT.md`.
- A reproducible `scripts/plot_v0919_frontiers.py` produces
  three separate, source-attested **SVG** visualizations of
  synthetic backup-heat fraction versus operating objective.
  Marker radius encodes modeled start count; non-dominated
  options marked. No plant-reliability figure asserted.
- Eliminated a duplicate scenario seed from a modular arithmetic
  collision (seed 83 duplicated seed 11); now **11, 37, 59**
  give three distinct validated synthetic price paths.
- Introduced finite **36-case** (3 seeds × 3 buffer capacities ×
  2 backup-heat capacities × 2 startup-cost coefficients)
  15-minute commitment study with endogenous on/off/heat and
  energy-inventory decisions, without altering the inherited v0.9.7 MILP.
- Nine matched **96-quarter-hour ramp LP** cases using the
  inherited v0.9.5 continuously-on CHP surrogate. Separate independent
  reconstruction and **primal/dual KKT residual verification**
  with explicitly scoped same-SciPy/HiGHS numerical backend.
- Independent **2^8=256 binary pattern enumeration** and
  separately reconstructed fixed-pattern LP optimum checks for an
  eight-quarter-hour MILP, rather than mislabelling an unchanged
  zero-buffer forced schedule as an endogenous optimum.
- Three nonprobabilistic finite operational-design Pareto sets
  (synthetic contribution, modeled backup heat reliance, startup
  counts). Different backup/capacity assumptions are **equipment design
  counterfactuals**, not repeated samples of one physical plant.
- All market prices, plant coefficients, electricity revenues,
  switching penalties and weather profiles fictional.
  No physical reliability/availability probability, manufacturer
  validation, site calibration, stochastic confidence interval
  or actual investment net present value is inferred.
- Preserved measured v0.9.17 city-gas CHP source identification and
  v0.9.18 168h LP/MILP research benchmark, full inherited model
  tests and strict SHA256 release coverage.

---

## v0.9.18 — 2026-11-15 — Quarter-hour 168h optimization and independent verification

- Dedicated 96/192/672 run 43719038048 **PASSED independent
  2,880-row stdlib verification**: exact zero-buffer binary MILP
  objective €681/€1,360/€4,755 for 24/48/168h; paired zero-buffer
  vs 0.75-MWh-buffer always-ON ramp LP values
  €4,110.40 vs €4,526.275 (168h). No actual plant revenue claims.
  Full results in `reports/V0918_EXECUTED_QUARTER_HOUR_WEEK_BENCHMARK.md`.
- Introduced 96/192/672 15-minute synthetic research benchmark for
  inherited v0.9.7 binary commitment and v0.9.5 buffered ramp LP.
- Validated forcing and globally unique algebraic solution in a
  **zero-buffer** periodic gas-arrival case, with explicitly fictional
  CHP efficiency, heat service, gas input, startup/dwell and prices.
- Added paired flexible LP with/no storage, identical gas and service,
  cyclic inventory and independent per-interval gas/heat/electric ledger.
  LP global optimum **not independently dual certified**.
- Three 96-slot independently motivated infeasibility controls:
  insufficient backup heat, too-low electrical rating and mandatory
  uptime passing the terminal horizon.
- Dedicated full-week CI job, synthetic-only complete solver report
  and standard-library independent JSON auditor plus adversarial tests.
- Existing v0.9.17 measured **Japanese city-gas** CHP audit retained
  strictly apart from synthetic Swedish-price-zone cases; no real
  biogas-engine calibration, actual price forecast or contract revenue.
- Full prior source-provenance, 533-file original research tree, CI
  numerical/LP/MILP witnesses and 2005 measured data unaffected.

---

## v0.9.17 — 2026-11-15 — Measured external CHP hourly channel study

- Actual published Kitakyushu 2005 source results from independent online
  run 43711923353: 8,760 aligned hourly records, 686,380 kWh engine
  electrical output, 199,510.35 source m³ engine gas, 27
  power-positive/gas-zero hours and 316 gas-positive/power-zero
  hours. Original `Gas 1` and `Gas 2` heat recovery rate sums
  remain separately reported with source heat allocation unverified.
  Evidence recorded in the versioned executed research report.
- First separately executed actual published Kitakyushu 2005 city-gas engine
  **three-source** analysis, not merely metadata/ZIP structure preview:
  engine electricity `Gas engine (kW)`, engine gas use `Gas engine (m3)`,
  separately labelled `Gas 1/2(GJ/h)` heat recovery.
- Rigorously check all original Figshare provider MD5/byte counts against
  official metadata and observed SHA256 from an earlier successful real
  download, exact 2005 nested workbook filename and source column labels.
- Decode shared-string XLSX; verify all 8760 source-local hourly
  timestamps and complete one-to-one three-workbook matches; count
  missing, negative and conflicting engine electricity/gas reading
  combinations; preserve descriptive measured totals and sample anomalies.
- **Do not** assume source gas is normalized dry `Nm3`, assign
  hypothetical city-gas LHV, equate `Gas 1/2` to useful end-use heat,
  infer subhour ramp/starts or fit Swedish biogas engine parameters.
- New isolated online reproducibility workflow generates **actual real
  source** aggregate audit report; no large raw archives committed;
  offline adversarial XLSX source and 8760-hour analytical fixture tests.
- Preserve prior v0.9.16/15 physical source-validation refusal,
  v0.9.14-B 81-cell sensitivity oracle, full inherited LP/MILP
  numerical checks and market bid-time provenance gates.

---

## v0.9.16-C — Matlink authorized source request and physical evidence blockers (2026-11-15)

- Sourced the NYSERDA Matlink Farm biogas reciprocating-engine monitoring notes, distinguishing the original 91-channel 15-minute daily CSV logs from the derivative public hourly reports.
- Explicitly block unverified source license, private raw data receipt, Eastern local-clock/DST conversion, cumulative meter rollovers, useful-heat measurement integration, suspicious published gas heating-value units and >100% reported monthly electrical efficiencies.
- Added nine documented acquisition dependencies, a fail-closed machine-readable evidence register and five adversarial non-validation tests.
- Prepared but **did not send** a targeted inquiry to the public program data custodian; no unauthorized access or bypass of download restrictions.
- Preserve v0.9.16 software version and all prior physical and market validation gates. No real Matlink CSV, engine-fit evidence or scientific v1.0 claims.

---

# v0.9.16 — 2026-11-15 — External measured CHP source inventory and acquisition

- Discover/pin real published CC BY 4.0 CHP sources with **distinct
  equipment and fuel**: 2023 RISE Swedish biogas solid-oxide fuel-cell
  energy-flow data and 2001–2022 Kitakyushu Japanese **city-gas**
  reciprocating-engine/fuel-cell electricity, gas and heat data.
- Additional **not-yet-acquired**, more directly matched candidate:
  NYSERDA Matlink Farm, 145 kW Waukesha anaerobic-digester-gas
  reciprocating CHP, originally 15-minute/91-point monitoring (2004–2005).
  Raw download challenged by WAF, license not established and anomalous
  public efficiency computations flagged; candidate **blocked from model
  calibration** pending authorized export/source checks.
- Source DOI, provenance class, source paper, license, measured periods,
  original filenames, provider byte sizes and MD5 digests for seven
  distributed original measurement archives recorded in the source registry.
- The dedicated online acquisition run **43704165251 PASSED for both
  providers**: seven actual original downloaded sources verified against
  provider MD5 and bytes, independent SHA256 fingerprints and bounded
  workbook/ZIP profiles retained in
  `reports/V0916_REAL_PUBLIC_CHP_SOURCE_ACQUISITION_AUDIT.md`.
- Explicit network-opt-in `public-chp-sources --fetch` retrieves actual
  publication bytes, checks size+MD5, computes independent SHA256 and
  profiles ZIP/XLSX structures with path-traversal and expansion limits.
  Offline metadata-only mode never retrieves or fabricates any observations.
- Independently maintained online-acquisition workflow: source-specific
  provenance JSON reports archived; **raw source files not committed**,
  numeric solver CI stays independent of network.
- Adversarial provenance and archive safety tests; full documentation,
  source-transfer restrictions, measured-data incompleteness and
  an **unsent** authorized gas-engine dataset request.
- Full v0.9.15 telemetry QA, v0.9.14-B factorial/identifiability,
  v0.9.13 market provenance and all older frozen physical oracle audits
  retained without importing either unrelated source into CHP MILP.
- No biogas reciprocating-engine high-rate operation dataset or
  authenticated calibration certificates; independent human validation,
  physical engine parameter fit, field partnership and scientific v1.0
  remain explicitly pending.

---

# v0.9.15 — 2026-11-15 — CHP field telemetry acquisition readiness and uncertainty metadata

- New documented 15-minute raw-measurement **data contract** distinguishing
  CHP generator terminals, signed PCC export/import, on-site electric
  consumption and auxiliaries, actual engine fuel dry-normalized flow,
  production, flared gas, LHV, useful delivered heat and gas-buffer volumes.
- Four-row SHA-pinned **invented synthetic** fixture and 11-entry
  **uncalibrated synthetic** instrument registry for offline QA demonstration.
  No real plant instrument data, real field measurements or certificates.
- Fail-closed `biogasflex telemetry-qa` supports a separately authorized
  real input manifest only for source/schema/energy-balance screening;
  requires all UTC periods aligned, no gaps/suspect records, synchronized
  meter clocks and 24-hour minimum coverage, plus calibration **metadata**
  with declared validity, not independently authenticated certificates.
- Linear sum of individual meter standard-u inputs as a **non-GUM,
  non-probabilistic screening allowance**, without claiming covariance
  estimation, physical bounds or measurement traceability.
- Reject plant identity and calibration claim laundering, invalid
 /modified SHA, fuel/heat mismatch, impossible electrical balances,
  unaccounted flare/buffer gas and false generator-versus-grid equivalence.
- Separate not-yet-implemented high-rate startup/ramp data contract,
  testable independent Decimal witness, adversarial regression tests,
  full-tree release manifest and multi-platform reproducibility.
- No high-frequency engine tests, calibrated CHP partload,
  physically validated dispatch, actual market trade, net profit
  or external human review. Scientific v1.0 remains blocked.

---

# v0.9.14-B — 2026-11-15 — Predeclared hypothetical contract-constraint sensitivity

- New opt-in 81-cell `3^4` factorial of storage, steady-on upward ramp,
  minimum-on generation and auxiliary heat capacity, retaining the original
  synthetic 2-hour accepted-electricity schedule and gas/heat/commitment MILP.
- Derive independent algebraic feasibility witness, compare each scenario
  directly to SciPy/HiGHS and fail if infeasibility differs or unexpected
  solver status occurs. Predeclared exact witness: 16 feasible, 65 infeasible.
- Nine one-factor tests of electric/thermal efficiency and prior ramp-down:
  verify terminal-inventory coupling, first-hour heat backup and inherited
  midpoint-ramp semantics. Invalid contracts have NULL profit/revenue claims.
- Finite-design main/pair/higher-order variance decomposition with explicit
  **no probability interpretation**. Two conditional rectangular analytical
  certificates: broad box not robust, restricted box robust **only within
  the locked synthetic always-on 2-slot model**.
- Constructive non-identifiability witness confirms annual power integrals
  and running hours cannot recover unique ramp/start traces.
- Add independent no-solver-import 81-cell check, adversarial provenance
  tests, optional JSON report, versioned methods/results and cross-platform
  reproduction with all v0.9.14-A and v0.9.13 source gates intact.
- No physical calibration, real market accepted awards or energy sales,
  statistical plant-reliability inference, source reviewer sign-off or v1.0.

---

# v0.9.14-A — 2026-11-15 — Source-scoped manufacturer / plant CHP evidence

- Extend (do **not replace**) merged v0.9.13 dated market provenance and
  v0.9.12 source-verified annual landfill CHP records.
- Introduce 29 traceable parameter records and three explicitly unmatched
  engine identities: Ciuła published Polish landfill CHP, Caterpillar
  CG132B-8 catalogue, and Jenbacher J312 catalogue.
- Declare 14 site-specific dynamic/operational parameters unidentified:
  minimum load, upward/downward ramps, min up/down times, startup costs,
  part-load electricity/heat, storage, heat demand, time-resolved engine
  fuel consumption, net export, outages and fuel calorific variability.
- Fail-closed source/scope validation; independent standard-library oracle
  and mathematical examples proving annual integrals cannot identify
  ramps or start counts. Manufacturer maxima never installed as site
  parameters; no automatic solver import or new equipment validation claim.
- Opt-in `chp-evidence-register` CLI, cross-platform 10-job CI matrix,
  existing v0.9.13 market audit retained in full offline reproduction,
  and strict SHA256 coverage extended to all new source files.
- v0.9.14-B bounded sensitivity, actual site calibration and independent
  human methodological review remain pending.

---

# v0.9.13 — 2026-11-15 — Historical market as-of provenance with existing published CHP annual evidence

- Add immutable Svk day-ahead 2020-04-01 SE3
  source/zone/UTC grid audit to the already independently
  published v0.9.12 CHP annual evidence layer.
  Preserve frozen price source SHA256, source CC BY licence,
  2026-04-09 dataset record publication and
  2026-11-05 archived retrieval.
- Source-supplied prices lack original 2020
  participant-specific publication/award timestamps:
  reject backdating and false bid-time data availability
  claims, do not invent true price forecasts.
- **Reuse without duplication** the v0.9.12 independently
  audited 2012–2022 landfill-gas 0.44-MW CHP records,
  their original source paper and published arithmetic
  discrepancies; compare nameplate identity only.
- Opt-in `market-provenance` CLI with detailed audit
  only by explicit `--output`. Add strict
  `contract-dispatch --require-operational-validation`
  refusal until genuine same-plant high-frequency
  measurements, metered export, as-of market data
  and participant awards exist. A status flag cannot
  override this gate.
- No original 286 scientific inputs/results or
  the inherited physical MILP, data and earlier
  market experiments modified. Cross-platform
  source manifest/tests/audits preserved.
- No market trading, site calibration, real
  economic return, human science review,
  public GitHub Release or Zenodo DOI claimed.

---

# v0.9.12 — 2026-11-15 — Published annual CHP evidence with source-quality audit

- Transcribed independently published 2012–2022 annual running hours,
  recovered landfill-gas volumes, electric and thermal generation
  for a 440 kW_e / 520 kW_th Polish landfill CHP (Ciuła et al., 2023).
- Validate 11 distinct chronological annual records, positivity,
  finite numbers, rated energy output and leap-year 2020 hours.
- Retain raw annual rows and independently recompute period aggregates.
  Flag source Table 3/8 2018–2022 gas mean mismatch
  (1,267,253.2 versus 1,291,515 m³/y), the claimed 29.5% gas
  change and 42.78% electric change denominator discrepancy.
- No imputed hourly plant time series, no empirical CHP ramp/minimum,
  no inferred verified gas-storage vessel or dispatch profitability.
- Opt-in `annual-chp-evidence` CLI; independent pure-Python arithmetic
  witness, adversarial data rejection tests and full inherited CI gates.
- v0.9.11 contract model and Swedish synthetic configurations retained;
  external scientific review and real operating/market validation remain open.

---

# v0.9.11 — 2026-11-15 — Contracted electricity equality inside CHP MILP

- Opt-in **hard accepted-volume** equality constraint:
  per slot `η_e × fuel_MW_LHV × duration_h = awarded_MWh_e`;
  included in the original gas/heat/commitment MILP
  matrix AND its identically constrained LP relaxation.
- Previously v0.9.10 postclear required the
  *uncontracted optimal* schedule to coincide with
  an accepted award; valid nonoptimal physical
  schedules were rejected. New mode can solve them.
- Distinct explicit model and `contract-dispatch`
  CLI; preserve all prior v0.9.10 API default behavior.
  Keep source-of-information and participant receipt
  boundaries strict, no assumed auction clear.
- Conditional reference feasible only when it
  satisfies the **same award**; unawarded fixed
  operation cannot invalidate the contracted optimum.
- Independent synthetic hour/quarter-hour MWh, gas
  inventory and heat-service/LP checks, plus
  intentionally infeasible storage, gas, ramp, heat,
  terminal-stock and zero-award cases. No invented
  imbalance volume or revenue.
- Full historical data/source preservation, earlier
  experimental study results, original 216 duals,
  96 solver-free LP oracles, all prior adversarial
  tests, cross-OS reproduction, and strict SHA256
  package manifest inherited.
- No real bid acceptance, forecast validation,
  electrically metered export, balancing fees,
  calibrated physical plant, real profit, externally
  reviewed research release or DOI.

---

# v0.9.10 — 2026-11-15 — Market-information staging and no-imbalance matching

- Strictly separate pre-clearing **synthetic assumed forecasts/energy
  offers** from post-clearing **fictional exogenous auction
  acceptance/clearing-price reports**. No postgate information
  enters the preclear API.
- Reject missing or inconsistent forecast issuance, bid time,
  gate closure, price publication, participant receipt or
  dispatch-plan creation times. Use explicit UTC and verify
  Europe/Stockholm D−1 vs local delivery day, with DST checks.
- Compute only **gross contracted cashflow proxy**:
  `Σ(accepted_MWh × clearing_price_EUR_per_MWh)`. No
  real market fee/imbalance settlement, intraday trading,
  grid export, accepted-volume optimizer or true profit.
- Independently verify original CHP gas/heat/ramp/dwell and
  explicit terminal-stock constraints, then fail closed unless
  every exogenous accepted MWh equals modelled delivered MWh.
  Contracted awards are **not** optimized as hard constraints.
- Synthetic analytical oracles €32 (two one-hour deliveries)
  and €20 (four quarter-hour deliveries) plus negative-award
  and incomplete/ambiguous market-data rejection cases.
- Preserve all original frozen scientific files, prior historical
  data and results, source attribution, v0.9.5–v0.9.9 models,
  independently verified dual/LP oracles and full offline
  multi-platform reproduction.
- No scientific v1.0/independent human review, real trading
  claims, public GitHub Release or DOI.

---

# v0.9.9 — 2026-11-06 — Chronological historical-price/synthetic-CHP replay

- New **opt-in** observed-market-price replay. Previously
  attributed and frozen Svk 2020 SE3 January, April and October
  24-hour price snapshots used without modifications.
- Chronological January **training anchor**, April/October
  **held-out** daily experiments. No October-to-April peeking.
- Three predeclared, untuned **causal** naive price forecasts:
  last known observation, mean of latest three known observations,
  and January local-hour price profile shifted by the strictly
  previous target observation. The latter provides a time-varying
  forecast shape rather than a flat objective; full-suffix forecasting for the existing
  v0.9.8.1 MILP with execution of only the first interval.
- New as-of price-observation ledger, one-step MAE/RMSE
  (with independently calculated historical price oracles);
  preserved actual gas and heat conservation and perfect
  hindsight MILP bound. Strict reject-on-failure of gap,
  duplicate, zone, UTC and training-overlap violations.
- **Reproduced negative finding:** Constant-price forecasts
  produce equal execution values on both selected days because
  total horizon gas utilization is fixed. The time-varying
  January local-hour template changes decisions but performs
  worse in both test windows. See `reports/V099_INTERNAL_AUDIT.md`.
- **Major scientific boundary:** 2020 price observations
  are real, but CHP plant and its control, gas, heat and
  economic inputs are synthetic; prices are revealed
  sequentially only under a counterfactual information
  regime that is NOT an available day-ahead trading
  forecast. Two days do NOT establish prediction skill.
- Preserve original 286 scientific source/result file
  hashes, all inherited experimental regressions, 216
  historical dual certificates, and 96 solver-free
  LP comparisons. Extend cross-OS reproduction and
  installed-wheel smoke tests, strict full-tree SHA256.
- No new real-world claims, external human review,
  GitHub Release, Zenodo DOI or science v1.0.

---

# v0.9.8.1 — 2026-11-06 — Rolling-commitment maintenance

- Preserve the user-declared first-slot power-observation age.
  In v0.9.8, the rolling evaluator reset it to zero,
  which could incorrectly invalidate a feasible ramp
  schedule despite the single-horizon solver accepting it.
- Handle a physically invalid must-run reference as
  **optional**. If fixed gas use would exceed nameplate
  or heat backup/dump resources, the flexible MILP may
  still be entirely physically feasible. Do not abort
  that valid result; return `null` for the unavailable
  fixed comparator and uplift.
- Add explicit reason code `fixed_reference_status`,
  distinguishing physical, terminal, and commitment
  feasibility rather than labelling a fabricated gain.
- Six additional adversarial tests including independently
  computed single-slot ramp (€40) and two-slot
  storage-shifting (€56) witnesses; expected suite
  **248 tests**, to be confirmed by hosted CI.
- Preserve v0.9.8 price-only synthetic forecast
  experiments, 286 frozen scientific artifacts,
  216 historic dual certificates, 96 solver-free
  comparison cases, 216+5 reproduced scenarios, and
  prior v0.9.5/v0.9.6/v0.9.7 audits.
- Update package and citation metadata, full
  cross-platform reproduction, installed-wheel CI
  and SHA-256 integrity coverage.
- Remains a development release: no equipment-
  calibrated controller, trained market forecast,
  peer review, public Release or DOI.

---

# v0.9.8 — 2026-11-05 — Synthetic rolling-horizon forecast price study

- New separate opt-in CHP on/off MILP extension with
  explicit **unchanging terminal gas inventory target**
  despite receding-horizon replans updating starting stock.
- For each forecast snapshot optimize full remaining
  horizon, execute only the first interval, update
  gas and commitment state, then replan. Maintain
  known initial ON/OFF and residual dwell obligations.
- Carry prior interval midpoint observation age into
  steady-ON ramp constraints rather than spuriously
  resetting the elapsed time at each replan.
- Recompute actual electricity and CHP heat/cost
  ledger from concatenated executed actions at
  **synthetic realized** electricity prices.
- Compute a mathematically valid matched-boundary
  continuous LP relaxation at each replan; refuse
  infeasible fixed comparators and hindsight
  contradictions rather than fabricating uplift.
- New independent analytic price-error oracles:
  two-slot reversed forecast €20 regret;
  three-slot updated forecast €70 versus
  stale €60 and perfect hindsight €80 (all
  invented data, not actual market revenue).
- Add 15 adversarial mathematical and 3 CLI
  tests, full Windows/Unix offline reproduction,
  10-job GitHub Actions matrix, data fixtures,
  checksum coverage and scientific protocol.
- Preserve original 286 research file hashes,
  216 market plus five hypothetical interruptions,
  216 market dual certificates, 96 solver-free
  comparisons, and v0.9.5–v0.9.7 experimental
  code and audits.
- No public GitHub Release, DOI, field operation
  validation, actual trained forecast, or
  independent human peer review.

---

# v0.9.7 — 2026-11-05 — Elapsed-hour CHP commitment with carried prior obligations

- Introduced separate opt-in continuous-time-unit **hour-based**
  minimum up/down limits on discrete interval-boundary commitments.
  Prior v0.9.6 interval-count model retained unchanged.
- Added `initial_remaining_dwell_hours` with enforced carried ON/OFF
  operating state, complete-horizon rule for all **new** events,
  and remaining carry-in obligation reported after the horizon.
- New exact standard-library, **solver-free** two-interval
  binary-stock oracle checks €45 at 1h, €40 at 1.01h, and
  infeasibility at 1.26h. Additional negative/reversed
  price and boundary cases check numerical feasibility.
- Added synthetic **24h / 36 slots**, alternating 15-minute
  and one-hour resolution, with gas, heat, steady-ramp and
  min-hour constraints; no observed data.
- **Hosted software verification:** two independent workflow triggers\n  (branch push and PR) both passed **10/10** hosted jobs for the\n  reviewed scientific code. 224 regression tests, all 216 historical\n  dual certificates, 96 prior solver-free comparisons, 286 original\n  pinned research files, and 415 original-branch manifest entries passed.\n  See [v0.9.7 observed matrix](docs/V097_REPRODUCIBILITY_MATRIX.md).\n- New synthetic 24h / 36-slot tests measured gas and steady-ON\n  ramp numerical residuals 5.55e-17 MWh_LHV and 2.64e-16 MW_e,\n  respectively, within declared tolerances.\n- Added 13 unit tests, 3 CLI tests, opt-in `hourly-commitment`
  endpoint, versioned Bash/PowerShell full reproduction,
  package/CFF metadata and 10-job OS/Python/wheel CI.
- Retained original 286 frozen research hashes, original
  216+5 results, 216 primal-dual checks, 96 prior
  solver-free comparisons, v0.9.5 and v0.9.6 model audits.
- No public GitHub Release/DOI, equipment commissioning,
  real field calibration or independent human peer review.

---

# v0.9.6 — 2026-11-05 — Experimental on/off CHP commitment and independent toy oracle

- Added opt-in binary on/off/startup/shutdown MILP with synthetic
  startup/shutdown event costs and strict finite-horizon min up/down
  interval counts.
- Enforced zero electrical generation when off and nonzero minimum
  electrical output when on, plus midpoint ramps across ON/ON
  transitions only (switching transients are unmodelled).
- Included full gas/heat/temperature-independent dispatch
  conservation ledger and economic objective reconstruction.
- Explicit fixed reference feasibility: only report an increment
  for a genuinely feasible on/off baseline; preserve the original
  heat LP as a mathematical upper bound on net committed value.
- **Observed hosted verification:** 10/10 jobs green on Ubuntu, macOS, Windows Python 3.11–3.13 and a wheel smoke; all 208 regression tests, 216 original dual cases, 96 v0.9.3 solver-free cases, 286 original research hashes and 402-file pre-final manifest passed. See [v0.9.6 matrix](docs/V096_REPRODUCIBILITY_MATRIX.md).\n- Synthetic 24-hour commitment audit checked two-interval min up/down periods with zero gas/steady-on ramp residuals.\n- Added 13 operating MILP and 3 CLI tests and a pure-Python
  exhaustive 3h toy oracle (€55/€35/€15 for minimum up-time
  1/2/3), plus read-only verification script and mock data.
- Added versioned Python environment MILP smoke, Bash/PowerShell
  reproduction scripts and 10-host CI matrix, strict manifest
  and new research documentation; preserved all 286 original
  scientific pins, 216 old market + five emergency outputs,
  original dual certificates and 96 solver-free toy checks.
- No observed plant performance, equipment-calibrated on/off
  behavior, external human peer review, GitHub Release or DOI.

---

# v0.9.5 — 2026-11-05 — experimental CHP power envelopes and forecast regret

- Added a separate opt-in **continuous always-on** heat-aware CHP LP:
  minimum electric power, up/down MW_e/hour midpoint ramps, declared
  starting power; an infeasible fixed comparator is explicitly rejected.
- Added synthetic **fixed-schedule forecast-vs-realization** valuation
  with no replanning and an ex-post perfect-foresight regret bound.
- Added fully invented 2-hour toy examples, deterministic 24-hour
  ramp audit, 15 operating and 3 user CLI tests.
- Extended active package version, CITATION, reproducibility scripts,
  3×3 hosted CI and independent wheel-install smoke, strict manifest.
- Retained all 286 frozen scientific source pins, original 216+5
  research results, 216 dual certificates and 96 solver-free synthetic
  comparisons.
- Explicitly **skipped 0.9.4**: no intervening version/release is
  claimed. No physical plant validation, realistic on/off commitment,
  actual profitability, public GitHub Release, or Zenodo DOI is implied.

---

# v0.9.3 — 2026-11-05 — independent two-interval oracle and deterministic stress

- New standard-library exact 2-interval optimum by breakpoint
  enumeration; no SciPy/HiGHS, original solver import or new measured data.
- New 96-case deterministic synthetic test across prices, heat and
  storage; metamorphic invariants for price/cost shifts and buffer size.
- **Observed hosted CI:** all 10 Linux/macOS/Windows × Python 3.11–3.13 and wheel jobs passed; 174 tests, 96 synthetic comparisons, 216 dual bounds and 286 pinned scientific files verified. Details: [v0.9.3 reproducibility matrix](docs/V093_REPRODUCIBILITY_MATRIX.md).\n- Eleven new unit/adversarial tests; retain all 216 dual bounds and 286\n  pinned scientific-file hashes.
- Update current package/CFF, cross-platform Bash/PowerShell CI and
  installed-wheel smoke; preserve old scripts and frozen 216+5 results.
- No human review, real-plant validation, representative annual sampling,
  full general LP solver replacement, GitHub Release or Zenodo DOI.

---

# v0.9.2 — Dual mathematical optimality checking (development candidate)

- Added an independently **formulated**, bounded-LP dual for all 216 frozen CHP market cases, with primal feasibility, dual feasibility and economic-contribution gap checks.
- Added adversarial edits of gas dispatch, CHP rating, cost claim and nonfinite input, plus an analytical two-interval €8.25 oracle.
- Kept the same SciPy/HiGHS solver backend; this is **not independent solver implementation** or external reviewer certification.
- Updated version metadata, full Bash/PowerShell reproduction gates and hosted Python 3.11–3.13 cross-platform CI. The first hosted 10-job matrix passed; see [observed v0.9.2 evidence](docs/V092_REPRODUCIBILITY_MATRIX.md). A dedicated v0.9.2 environment checker preserves the historic v0.9.1 checker separately. No frozen model, observed source, simulation result or scientific claim altered.
- Human scientific review, realistic CHP dynamics and site-economic/critical-service evidence remain out of scope. No GitHub Release or Zenodo DOI is being made.

---

# v0.9.1 — 2026-11-05 — release-engineering increment (pre-v1.0)

- Carry forward all v0.9 model formulas, frozen scientific input data and 216+5 numerical results without recalibration or altered findings. Added 286-file inherited scientific SHA-256 pin set.
- Correct `.gitignore` to track the existing CC BY 4.0 historical market file `data/external/svk_se3_20200101.csv` rather than silently excluding a file required by the manifest.
- Harden `scripts/verify_v09_manifest.py`: reject traversal/absolute paths, duplicate entries, unsafe symlinks, mismatched hashes and unexpected distributed files; exclude only enumerated Git/cache/build metadata. Add adversarial unit tests.
- Add `scripts/verify_v091_git_coverage.py`: a real checkout must track exactly the release files. ZIP extractions report NOT_TESTED for Git coverage.
- Add `scripts/verify_v091_environment.py` and version/CLI/HiGHS checks; align metadata in `pyproject.toml`, `CITATION.cff`, and `src/biogasflex/__init__.py` to `0.9.1`.
- Add Linux/macOS Bash and Windows PowerShell v0.9.1 reproducibility scripts and configure multi-OS Python 3.11/3.12/3.13 GitHub Actions plus separate wheel-install smoke.
- Build wheel and sdist; document actual local environment and untested hosted runners truthfully. No GitHub release, Zenodo DOI, human peer review or physical validation.

- **Hosted CI verification (2026-11-05):** 9/9 cross-platform reproducibility jobs passed (Ubuntu, Windows, macOS × Python 3.11–3.13); 1/1 installed-wheel smoke job passed. Repaired Windows timezone data dependency, locale-sensitive provenance reading, case-insensitive filesystem adversarial testing, and Windows Git CRLF conversion of frozen files. Recorded [GitHub Actions evidence](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029027186). No frozen scientific results changed.

---

# Changelog

## 0.9.0 — 2026-11-05 (pre-release scientific and reproducibility audit)

- Pinned hashes of the original v0.8 scenario registry, reference configuration and three attributed CC BY 4.0 Svenska kraftnät price snapshots.
- Introduced a standard-library strict input/scenario-identity validator independent of the optimization core; checks all 216 market case inputs, all five emergency case assumptions, fixed/optimized heat/gas/cost ledgers and study summary statistics.
- Added 21 analytical/adversarial tests and a clean isolated full recomputation across all 221 solved cases; 138 total regression tests.
- **Resolved major defect:** a claimed total gas supply interruption now rejects positive gas inflow rather than silently treating it as eligible.
- **Resolved metadata defect:** package version is 0.9.0; archived study/core JSON retains its original methodological version identifier.
- Added claims-to-evidence matrix, severity-tracked issue register, external reviewer questionnaire, citation metadata and SHA256-manifest verification.
- Updated GitHub Actions from obsolete v0.7 gates to the full v0.9 offline reproduction matrix (Python 3.11–3.13); ignore Git checkout metadata in archive integrity enumeration.
- **No new operating-price value, real plant validation, externally reviewed result, DOI, published GitHub release or verified black start is claimed.**

# BiogasFlex changelog

## 0.8.0 — Predeclared market sensitivity and hypothetical interruption service (2026-11-05)

- Preserved all v0.5–v0.7 code, tests, model and historical analysis outputs.
- Added a frozen, internally registered 216-configuration scenario matrix (three valid 2020 SE3 price windows × 72 hypothetical plant/heat/storage configurations) and its SHA-256 provenance.
- Retrieved additional Svk CC BY 4.0 SE3 April 1 and October 1, 2020 day-ahead price extracts. Preselected July 1 was **rejected for incomplete hourly sequence**, not interpolated or chosen again after looking at outcomes.
- Evaluated perfect-foresight incremental scenario contribution under price-window, heat demand, assumed backup cost, electrical efficiency, CHP rating and gas buffer changes. Saved **all 216 results**, including 120 zero-uplift cases; no a posteriori success-only filtering.
- Added five separate, synthetic gas-supply-interruption and critical-service cases with no grid input/backup heat, noncyclic precharged storage, and explicit hypothetical islanding/CHP availability gates. No observed outage or black-start claim.
- Added self-contained output ledger auditor, full-source market price matching, 36 new regressions including tamper detection and service bounds, 117 total passing tests.
- Added dated source/provenance documents, results and plots, v0.8 audit and model-boundary report, Windows/Unix repro scripts and optional emergency CLI.
- **No** plant calibration, human peer review, regional supply-security validation, probabilistic market inference, economic CAPEX/NPV, GitHub tag or Zenodo DOI is claimed.

## 0.7.0 and older

For original historical change records see the preserved v0.7 results, docs, and reports shipped unchanged in this package. Core heat-LP module retains its v0.7 version identity; v0.8 adds a separate orchestration/interpretation and emergency-service model.
