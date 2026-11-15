# BiogasFlex v0.9.18 — Independently audited 15-minute optimizer week

Research-scale mathematical verification (**synthetic assumptions, not
plant telemetry**): the inherited clock-hour commitment MILP and
always-ON ramp LP now have a systematic three-scale quarter-hour
benchmark: **96, 192 and 672 intervals** (24h, 48h, 168h).

- **MILP:** zero gas buffer + periodic 0/2 MW_LHV fictional gas input
  force on/off switching; an independent algebraic witness fixes every
  gas, power, startup and shutdown decision and hence the exact
  mathematical objective.
- **LP:** paired no-storage and buffered (0.75 MWh_LHV) scenarios
  test genuinely shiftable CHP output under 15-minute midpoint ramp
  constraints, cyclic gas stock and instantaneous heat service.
- **Three negative controls:** insufficient heat backup, engine
  rating exceeded and startup minimum-on dwell crossing the horizon.
- **Independent physical audit:** source-free standard-library
  recomputation of all quarter-hour gas, electric, heat, ramp,
  commitment and economic ledgers. Buffered LP primal is verified,
  but its dual optimality is **not independently certified**.
- Full week executes only in the separate
  [v0.9.18 benchmark workflow](.github/workflows/v0918-week-benchmark.yml).
  Portable regression and original frozen scientific cases run across
  Linux, Windows and macOS. No wall-time SLA or real equipment
  ramp/availability assertion is made.

```powershell
git pull origin main
python -m pip install -e .
.\scripts\reproduce_v0918.ps1

# Full synthetic 672-interval scaling and independent scientific audit:
$full = Join-Path $env:TEMP 'biogasflex_v0918_full.json'
$proof = Join-Path $env:TEMP 'biogasflex_v0918_independent.json'
python -m biogasflex benchmark-v0918 --output $full
python scripts/audit_v0918_independent.py --input $full --output $proof
```

See the [complete predeclared research protocol](docs/V0918_QUARTER_HOUR_WEEK_VERIFICATION_PROTOCOL.md)
for assumptions, independent algebraic derivation and limitations.
This benchmark does **not** implement 672-slot hard electricity awards:
earlier 2-slot contract semantics remain unchanged and are not
represented as day-ahead market participation. No actual biogas plant
performance or scientific v1.0 calibration is claimed.

---

# BiogasFlex v0.9.17 — Measured hourly Kitakyushu gas-engine source analysis

**Actual externally published real CHP data, not calibrated biogas-engine
prediction.** The v0.9.17 source-specific analyzer reads the **original
2005 XLSX workbooks** from three independently checksum-pinned Figshare
archives: gas-engine electrical power in kW, **city-gas** engine fuel
meter volumes in source m³ and separately attributed `Gas 1/Gas 2`
heat recovery rates in GJ/h. It rejects missing/duplicate hourly
timestamps, unexpected headers or changed source binaries, verifies
one-to-one alignment over 8,760 source-local hours, reports observed
channel totals and disagreement/quality flags, and does **not** borrow
gas heating values, assume calibrated equipment or infer subhour ramps.

```powershell
git pull origin main
python -m pip install -e .
python -m unittest tests.test_v0917_kitakyushu_real -v
.\scripts\reproduce_v0917.ps1

# Explicitly retrieve and verify actual source files before analyzing:
$out=Join-Path $env:TEMP "biogasflex_kitakyushu_2005_real.json"
python -m biogasflex real-chp-analysis --fetch --report $out
```

The [executed actual 2005 results](reports/V0917_KITAKYUSHU_EXECUTED_REAL_HOURLY_RESULTS.md)
report **8,760 matched observations**, **686,380 kWh** gas-engine
source electricity, **199,510.35 source m³** engine gas input,
**4,263 positive power/positive gas hours** and **343 contradictory
power/gas source-hour states** (27 generation-without-gas and 316
gas-without-generation). These discrepancies preclude naïve efficiency
estimation; gas heating-value basis and source heat allocation are not
verified. The report is derived from the original publisher-byte
verified archives in [GitHub Actions real-source run 43711923353](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/43711923353).

Full scientific [source-matched methodology](docs/V0917_KITAKYUSHU_REAL_HOURLY_ANALYSIS.md).
The real-source job also produces three **vector SVG plots** of
observed monthly engine electricity, engine gas source volume and
power/gas disagreement hours, computed from the 12-month report
without interpolating any readings.

Independent real data execution lives in
[the online source-analysis workflow](.github/workflows/v0917-kitakyushu-real.yml);
full offline CI remains independent of the internet.
The dataset is a Japanese **CITY-GAS** reciprocating engine and distinct
fuel cells: it is neither a biogas CHP operating curve nor measured
Swedish grid sales. Gas conversion to MJ and engine thermal allocation
are intentionally unverified. **Scientific v1.0 physical validation
remains outstanding.**

---

## Matlink Farm — v0.9.16-C acquisition handoff (raw data not obtained)

The original NYSERDA Matlink Farm **145 kWe Waukesha anaerobic-digester biogas CHP** has source-described 15-minute measurements, but neither its original CSV files nor reuse permission and calibrated instrument definitions have been received. The [Matlink acquisition handoff](docs/V0916C_MATLINK_AUTHORIZED_DATA_HANDOFF.md) and [nine-condition evidence register](data/evidence/v0916c_matlink_source_access_register.json) document raw files, fuel-energy basis, meter boundaries, timezone/DST, heat-integral ambiguity, source permissions and physical-validation blockers. The institutional data-custodian inquiry was **prepared but not sent**. No operating records were invented and no engine was calibrated.

# BiogasFlex v0.9.16 — Real published CHP source acquisition

This release extends **v0.9.15 telemetry QA** to independently published,
CC BY 4.0 **real measurement sources** without declaring that a biogas
reciprocating engine is physically calibrated.

- **RISE WEDISTRICT Luleå (Sweden)** — biogas-fired **solid oxide fuel
  cells**, January–June 2023. Four source Excel workbooks measure fuel-cell
  gas use, electricity, grid metering, transferred and delivered heat.
  **Not a reciprocating gas engine.**
- **Kitakyushu campus (Japan)** — operational **city-gas** reciprocating
  engine CHP and separate fuel cell. Three publicly available source ZIP
  archives cover hourly electrical generation, gas use and recovered heat.
  **Not biogas, not sub-hour ramp/event metering.**

A **third, stronger equipment/fuel match** is identified but not
downloaded: the [NYSERDA Matlink Farm 145 kW Waukesha biogas engine](https://der.nyserda.ny.gov/facilities/567/?project=516).
Its source notes describe 15-minute monitoring and the NYSERDA site
offers hourly/daily/monthly export; however the automated export was
blocked by the site WAF, the reuse license is unverified, and some
published monthly efficiencies are implausible. No Matlink source
values have been admitted into the model. Its blocked
[candidate register](data/evidence/v0916_matlink_biogas_engine_candidate.json)
details manual authorization, checksums and calibration prerequisites.

Source DOI, CC BY 4.0 license, technology/fuel boundary, author-attributed
original file sizes and MD5 references are pinned in
[data/evidence/v0916_public_chp_source_registry.json](data/evidence/v0916_public_chp_source_registry.json).
No values from either installation enter the existing v0.9.11/14
synthetic CHP MILP or the v0.9.12 Polish landfill CHP paper case.

Offline source registry only:
```powershell
git pull origin main
python -m pip install -e .
python -m biogasflex public-chp-sources
.\scripts\reproduce_v0916.ps1
```

Optional network retrieval of **actual published original source bytes**:
```powershell
$report = Join-Path $env:TEMP 'biogasflex_v0916_public_sources.json'
python -m biogasflex public-chp-sources --source all --fetch --report $report
```

The explicit `--fetch` operation compares provider MD5/byte counts,
computes fresh SHA256 and checks archive/workbook structures with
archive traversal/bomb protections. The separate
[online GitHub Actions retrieval workflow](.github/workflows/public-chp-source-acquisition.yml)
uses ephemeral runners and stores only source-integrity reports;
numerical/offline CI **does not depend on remote network services**.

The [executed seven-file acquisition audit](reports/V0916_REAL_PUBLIC_CHP_SOURCE_ACQUISITION_AUDIT.md)
records **all seven publisher MD5 checks and independently computed
SHA256** from successful hosted retrieval run 43704165251. It also
distinguishes the blocked NYSERDA matched biogas-engine candidate.

The [full acquisition and transfer-boundary protocol](docs/V0916_PUBLIC_EXTERNAL_CHP_SOURCE_ACQUISITION.md)
includes physical limitations and a prepared **unsent** request to
acquire instrument-calibrated, high-frequency *biogas reciprocating
gas-engine CHP* measurements from an authorized operator.

**No full gas-engine biogas calibration, independent source certificate
authentication, real start/stop/ramp engineering limits, real electricity
sales or signed operator data-sharing agreement have been established.**
The next validated milestone must be restricted to the evidence actually
available. Scientific v1.0 remains outstanding.

---

# BiogasFlex v0.9.15 — CHP telemetry acquisition-readiness and data QA

**No real CHP telemetry has been acquired. No source calibration
certificates have been independently authenticated. No real-plant
predictive accuracy or operating envelope is validated.**

This milestone adds a **time-resolved field-measurement protocol**, a pinned
four-interval **synthetic-only** generator/gas/heat/grid/buffer energy fixture,
an 11-instrument metrology register, and a fail-closed CSV/metadata auditor.
The program separates generator-terminal production from signed net-grid
export, treats gas on a dry-normal cubic-metre **LHV** basis, enforces UTC
quarter-hour continuity, checks meters/clock/calibration metadata and
screens energy/gas/heat balances using an explicitly *non-GUM*
linear uncertainty allowance. It rejects plausible but modified source
bytes, false site identity, suspect records, stale calibration metadata
and contradictory flow/energy states.

```powershell
git pull origin main
python -m pip install -e .
python -m biogasflex telemetry-qa
python -m biogasflex telemetry-qa --output qa_v0915_demo.json
python scripts/audit_v0915_telemetry_qa.py
.\scripts\reproduce_v0915.ps1
```

See [v0.9.15 field acquisition and independent validation
protocol](docs/V0915_CHP_FIELD_ACQUISITION_VALIDATION_PROTOCOL.md) and
the [separate high-frequency startup/ramp event requirements](data/schemas/v0915_high_rate_event_data_contract.json).
The proposed 1-second event logging is a **provisional design target**;
it is **not implemented** or supported by the 15-minute demo fixture.

`telemetry-qa --manifest <authorized.json> --csv <private.csv>` supports
raw real-data **schema/balance screening only** when an authorized operator
can supply the data, 24-hour UTC coverage and the complete documented
instrument metadata. Both real manifests and private raw data must be stored **outside
the public repository**; the CLI enforces that boundary. A real-data QA pass is explicitly still
`PENDING_HUMAN_VERIFICATION` and **not** physical model validation.

Original price and market source-provenance constraints, 2012–2022
published Polish landfill annual summaries, the unmatched manufacturer
identities and the synthetic 81-cell bounded-sensitivity model remain
unchanged. Independent field campaigns, defensible measured dynamic
constraints, uncertainty covariance and out-of-sample testing are
required before scientific v1.0.

---

# BiogasFlex v0.9.14-B — Synthetic CHP bounded sensitivity and identifiability

**Research software, not a calibrated plant, grid-export forecast, or tradable
physical guarantee.** The opt-in `bounded-sensitivity` command evaluates the
*unchanged* fictional v0.9.11 2-hour hard-electricity-award case across
a predeclared **81-cell full factorial**, **9 one-at-a-time checks**,
and **2 conditional continuous parameter boxes**.

```powershell
git pull origin main
python -m pip install -e .
python -m biogasflex bounded-sensitivity
python -m biogasflex bounded-sensitivity --output report_v0914b.json
python scripts/audit_v0914b_sensitivity.py
.\scripts\reproduce_v0914b.ps1
```

The exact source-pinned model and analytical witness establish which of
the hypothetical parameter combinations can satisfy the awarded
`[0.2,0.6] MWh_e` schedule. **16/81** finite design cells are feasible;
this is a *design-grid fraction, not a probability of real delivery*.
The available 2012–2022 annual landfill-CHP measurements do not identify
dynamic ramps or start/stop counts. A carefully scoped monotonicity
proof certifies a narrower hypothetical continuous box **only for the
fixed 2-hour always-on interval model**; the larger box is falsified.

All original model code and data, the 29-entry manufacturer provenance
register, and the v0.9.13 historical market as-of evidence gate remain
separate and unchanged. No manufacturer catalogue maxima are installed
as operating constraints. See [full methodology](docs/V0914B_BOUNDED_SENSITIVITY_PROTOCOL.md)
and [internal research report](reports/V0914B_INTERNAL_RESEARCH_REPORT.md).
No independent human peer review, site dynamic validation or public v1.0
research release has been completed.

---

# BiogasFlex v0.9.14-A — CHP operating-parameter source and identity audit

This milestone builds **on top of** the merged v0.9.13 historical
market-provenance work, without changing its market source files,
read-only audits, contract-dispatch fail-closed guard or synthetic solver.
It adds a reproducible register for CHP parameters whose actual equipment
identity, time resolution and operating conditions are known or unknown.

**Three unmatched equipment identities:** published 440 kW electrical /
520 kW thermal Polish landfill CHP (engine make/model unknown), Caterpillar
CG132B-8 400 ekW catalogue example, and Jenbacher J312 **up to 635 kW**
catalogue example. Manufacturer examples **are not** identified as the
Polish engine or a Swedish site installation. Vendor maximum efficiency
claims are not inferred part-load performance.

A [29-row source register](data/evidence/v0914_chp_parameter_register.json) with
three attributed source pages identifies **14 unmeasured/unidentifiable
site dynamic parameters**, blocked from operational inference or automatic
MILP import. Only the Polish source site's own published electric/thermal
ratings can be used for static sanity screening of that same installation.
The source-scope audit rejects manufacturer/plant swaps and invented
ramp, minimum load, storage, fuel/heat or net-export data.

```bash
python -m pip install -e .
python -m biogasflex chp-evidence-register
python -m biogasflex chp-evidence-register --output chp_register_audit.json
python scripts/audit_v0914_chp_sources.py
bash scripts/reproduce_v0914.sh
```

Windows: `./scripts/reproduce_v0914.ps1`.

See the [complete manufacturer evidence and identifiability protocol](docs/V0914_CHP_MANUFACTURER_EVIDENCE_PROTOCOL.md).
**No time-resolved plant validation, commissioned part-load curves, actual
market trades, real revenue or independent human review are claimed.**
Scientific bounded-sensitivity/identifiability work remains open for
v0.9.14-B, and a peer-reviewed v1.0 release remains outstanding.

---

# BiogasFlex v0.9.13 — Source-pinned historical market evidence and operational validation refusal

**Research development candidate, not field-validated operations.**

New `market-provenance` audits the **original Svk
2020-04-01 SE3 prices** (24 hourly observations,
24-price mean €6.9879/MWh) and records their
**2026-04-09 source dataset publication date** and
**2026-11-05 frozen-file retrieval date**.
The data are genuine *retrospective historical prices*
but do **not** establish original 2020 D−1
auction publication/participant receipt times.
We never treat them as verified 2020 ex-ante
forecast inputs.

The new command also **reuses**, without duplication,
v0.9.12's independently published **2012–2022
annual** Polish landfill-gas CHP observations and
their documented source arithmetic issues.
Annual measured summaries from a different 0.44-MW
CHP do **not** validate the 0.8-MW synthetic
BiogasFlex hourly gas/heat/ramp/stored-energy MILP.

```bash
python -m pip install -e .
bash scripts/reproduce_v0913.sh
python scripts/audit_v0913_market_provenance.py
python -m biogasflex market-provenance
python -m biogasflex market-provenance --output market_evidence.json
# Optional strict real-operation requirement must FAIL CLOSED on this evidence:
python -m biogasflex contract-dispatch --require-operational-validation
```

On Windows: `./scripts/reproduce_v0913.ps1`.

[Complete new market chronology/evidence protocol](docs/V0913_MARKET_SOURCE_PROTOCOL.md).
[Original external annual measured CHP study](docs/V0912_EXTERNAL_CHP_EVIDENCE_PROTOCOL.md).
[Existing hard-award MILP specification](docs/V0911_HARD_CONTRACT_PROTOCOL.md).

**No actual participant bids, real market profit,
industrial CHP calibration, field validation,
human-reviewed v1.0, Release or DOI** is claimed.
The independent scientific review
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains outstanding.

---

# BiogasFlex v0.9.12 — Published CHP annual evidence audit (research)

**New:** source-verifiable 2012–2022 annual operating observations for a
**440 kW_e / 520 kW_th Polish landfill-gas CHP unit** (Ciuła et al.,
2023, [DOI 10.3390/en16052180](https://doi.org/10.3390/en16052180)).
The opt-in `annual-chp-evidence` command independently checks published
annual running hours, recovered gas, electricity/heat and nameplate bounds.
A separate solver-free audit cross-checks arithmetic and highlights the
paper's internally inconsistent post-period gas mean and growth percentages.

```bash
python -m pip install -e .
python -m biogasflex annual-chp-evidence
python -m biogasflex annual-chp-evidence --output annual_evidence_report.json
python scripts/audit_v0912_external_chp.py
bash scripts/reproduce_v0912.sh
```

Windows: `./scripts/reproduce_v0912.ps1`.

**Scientific boundary:** This is **landfill gas, not anaerobic digester gas**.
Annual CHP capacity/generation observations do **not** establish minimum
stable power, ramp limits, hourly heat load, storage capacity or gas-to-engine
mass balance. The pre-existing v0.9.11 contract-dispatch MILP remains
synthetic, completely separate, and **not validated by this source**.
See the [external evidence protocol](docs/V0912_EXTERNAL_CHP_EVIDENCE_PROTOCOL.md).
Independent human review, metered dispatch validation, true market trades,
public GitHub Release and DOI remain outstanding.

---

# BiogasFlex v0.9.11 — Hard-contracted CHP electricity delivery (experimental)

**Status:** scientifically auditable numerical software, **not** an
operational market-bidding system or validated CHP/site profit model.

The new opt-in `contract-dispatch` interface fixes a
v0.9.10 limitation: a day-ahead auction's **fictional
accepted energy volumes** are now embedded as exact
equality constraints in the gas/heat/binary CHP mixed-integer
optimizer, rather than rejected merely because the
uncontracted optimizer would prefer a different
physical schedule.

For each slot, `η_e × gas_use_MW_LHV × Δt_hours = accepted_MWh_e`
inside the MILP *and* its matching continuous relaxation.
Pre-/postauction information times and participant receipt
checks are inherited from v0.9.10. No accepted MWh may
exceed offered MWh; a true physical infeasibility fails closed
as `CONTRACT_INFEASIBLE`.

The independent synthetic **hourly** award
`[0.2,0.6]` MWh generates €20 gross cashflow
at invented prices `[100,0]` versus an
uncontracted preferable `[0.4,0.4]` MWh schedule
worth €40. Both are physically feasible, but
only the first matches the hypothetical award.
A **15-minute** contract
`[0.05,0.15,0.1,0.1]` MWh is also feasible
and yields €9 fictional gross cashflow. Exact
gas inventory, heat, ramp, dwell and LP bounds
are checked; insufficient storage, ramp or heat
resources must reject the award.

```bash
python -m pip install -e .
bash scripts/reproduce_v0911.sh
python scripts/audit_v0911_hard_contract.py
python -m biogasflex contract-dispatch
python -m biogasflex contract-dispatch --manifest examples/v0911_contract_quarterhour.json
python -m biogasflex contract-dispatch --output contracted_report.json
```

On Windows: `./scripts/reproduce_v0911.ps1`.

This is **generator-terminal modelled MWh**, not
measured electricity sold to the grid. All prices,
awards, forecasts, gas input, heat/costs and CHP
physics in v0.9.11 are **invented**. There is no
actual auction, balancing settlement, intraday
trading, grid metering, revenue, profit or price
prediction claim.

Read the [complete methodology and limitations](docs/V0911_HARD_CONTRACT_PROTOCOL.md),
[v0.9.10 market information boundary](docs/V0910_MARKET_INFORMATION_PROTOCOL.md)
and the [v0.9.9 negative historical-price study](reports/V099_INTERNAL_AUDIT.md).
The original scientific source/results remain frozen.
Human review is still required under
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3);
no public Release/DOI or scientifically reviewed v1.0 exists.

---

# BiogasFlex v0.9.10 — Explicit day-ahead information and fictional award matching

**Status:** independently tested research software, **not** a functioning
Nord Pool auction/settlement integration or an operating power plant model.

New opt-in `market-boundary` command separates two deliberately different
information sets: (1) a pre-clearing submitted *hypothetical* sell-energy
schedule based on dated invented forecasts, with no actual clearing prices
or awards accessible, and (2) post-clearing *exogenous fictional*
participant accepted energy, clearing prices and result-delivery times.

Every accepted MWh must match the unchanged v0.9.8.1 physically audited
CHP MILP delivery exactly, or the experiment fails closed with
`UNMODELLED_IMBALANCE`. We **do not** silently assume intraday sales,
balance settlement, nominations, metered export or market profits.
The post-clearing diagnostic is only a gross
`Σ(MWh_awarded × EUR/MWh_cleared)` fictional cashflow proxy.

Two independent numerical oracles: two hourly deliveries
`[0.4,0.4] MWh × [20,60] EUR/MWh = €32`; four 15-minute
deliveries `[0.1,0.1,0.1,0.1] MWh × [20,40,60,80] EUR/MWh = €20`.
The UTC gate/receipt/plan sequence, partial-award rejection, and
23-/25-hour Stockholm DST days are explicitly tested.

```bash
python -m pip install -e .
bash scripts/reproduce_v0910.sh
python scripts/audit_v0910_market_boundary.py
python -m biogasflex market-boundary
python -m biogasflex market-boundary --manifest examples/v0910_market_quarterhour.json
python -m biogasflex market-boundary --output market_report.json
```

On Windows: `./scripts/reproduce_v0910.ps1`.

Read the [complete market information and contract
boundary protocol](docs/V0910_MARKET_INFORMATION_PROTOCOL.md).
The previous observed-price sequential experiment remains available
and is still **counterfactual**; see the archived
[v0.9.9 numerical audit](reports/V099_INTERNAL_AUDIT.md).

**Scientific release gate remains open** under
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
No real auction awards, observed grid exports, true price forecast
performance, physical CHP calibration, external peer review, public
GitHub Release or DOI are claimed.

---

# BiogasFlex v0.9.9 — Observed-price chronological replay, hypothetical CHP

**Research software only.** This opt-in experiment combines **actual
2020 Svenska kraftnät SE3 market prices** with an **entirely synthetic CHP,
gas storage and heat-service model**. The sequential hourly reveal of
prices is an *imagined* information regime, **not a real day-ahead
electricity market forecast or operational trading strategy**.

The new `historical-replay` command runs **two predeclared 24-hour
held-out days (April 1 and October 1, 2020)** using January 1 as
chronologically earlier context. Three predeclared causal predictor baselines
are applied to the existing v0.9.8.1 rolling-horizon commitment MILP:

- **last_observed:** hold the latest already observed price constant
  over the remaining planning horizon;
- **trailing_three_mean:** hold the mean of the last three already
  observed prices constant over that horizon;
- **diurnal_template_bias:** use the January local-hour price shape,
  adjusted only by the price difference observed in the preceding
  completed target interval. This third baseline gives the solver a
  nonconstant, time-varying forecast shape without future leakage.

At each step, forecasts are made before the current observed price
becomes visible to the hypothetical replay. The report records
as-of information cutoffs, one-step MAE/RMSE, observed-price
realized *model* contribution, hindsight regret, gas/heat conservation,
and infeasible-fixed-comparator status. No price-model training
or tuning on the held-out days is performed.

```bash
python -m pip install -e .
bash scripts/reproduce_v099.sh
python scripts/audit_v099_historical.py
python -m biogasflex historical-replay
# Optional detailed machine-readable audit (not written by default):
python -m biogasflex historical-replay --output replay.json
```

Windows: `./scripts/reproduce_v099.ps1`.

**Observed negative result:** Both constant-price predictors produced
identical dispatch contributions on the two selected days. The
nonconstant January-hourly template did alter dispatch, but produced
**lower** contribution than those flat baselines on both dates.
This is not proof of any predictor's operational skill. See the
[full independent numerical outcome table and limitations](reports/V099_INTERNAL_AUDIT.md).

Read the [v0.9.9 complete research boundary,
source provenance and validation protocol](docs/V099_HISTORICAL_REPLAY_PROTOCOL.md).
The original observed price files are CC BY 4.0 and remain unchanged.
The **286** original pinned scientific source/result files and the
v0.9.5–v0.9.8.1 synthetic and original models remain frozen.

**Limitations:** two days are insufficient to establish meaningful
forecast skill; sequential price availability is counterfactual;
CHP and thermal costs are invented; no calibrated operational
controller, measured returns, or externally reviewed findings.
[Scientific reviewer issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains open. There is **no public GitHub Release or Zenodo DOI**.

---

# BiogasFlex v0.9.8.1 — Rolling-horizon maintenance patch

**Status:** experimental software maintenance, not equipment-validated
CHP dispatch, measured electricity forecasting or an externally
reviewed scientific release. No public GitHub Release or DOI.

This narrow patch preserves the opt-in synthetic
v0.9.8 price-only rolling-horizon commitment MILP
and fixes two state/benchmark handling defects:

- The first replan now honors the **declared initial
  power-observation age** instead of silently
  overwriting it with zero, preserving correct
  elapsed-hour ramp feasibility.
- An **infeasible fixed-operation reference** (for
  example one exceeding nameplate or auxiliary
  heat capacity) no longer aborts an otherwise
  physically feasible flexible CHP dispatch.
  The invalid reference and its uplift report
  `null`; the optimized dispatch remains subject
  to strict conservation, dwell, ramp and LP-bound audits.

Run on Unix:

```bash
python -m pip install -e .
bash scripts/reproduce_v0981.sh
python scripts/audit_v0981_maintenance.py
python -m biogasflex rolling-forecast
```

On Windows PowerShell use
`./scripts/reproduce_v0981.ps1`.
The new independent test fixtures verify €40 in a
one-hour ramp observation example and €56 in a
two-hour nameplate-constrained flexible gas-storage
example; both are **fictional** analytical oracles.

All 286 pinned historical scientific source/result
files and the v0.9.5–v0.9.7 models remain unchanged.
See the [v0.9.8.1 maintenance protocol](docs/V0981_MAINTENANCE_PROTOCOL.md)
and the original
[v0.9.8 synthetic rolling study](docs/V098_ROLLING_PROTOCOL.md).
Human independent scientific review remains open
under [issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).

---

# BiogasFlex v0.9.8 — Synthetic rolling-price CHP commitment experiment

**Status:** development candidate; no public GitHub Release,
Zenodo DOI, real plant controller, measured forecast skill or
independent human-reviewed scientific finding.

The new **opt-in rolling-horizon experiment** evaluates price
forecast revisions against synthetic realized electricity
prices. At each interval the optimizer solves a full
remaining-horizon CHP ON/OFF commitment MILP using the
current forecast, executes **only one interval**, then
carries forward exact gas stock, ON/OFF state, output
observation time and remaining minimum operating dwell.

**Scientific correctness correction:** An intermediate
replan has a different initial gas stock but must keep
the ORIGINAL final gas-stock target. The new module
enforces that target explicitly, audits the true
end-to-end energy balance, and recomputes an LP upper
bound using exactly the same terminal boundary.
An infeasible fixed comparator does **not** get
assigned an invented incremental economic gain.

```bash
python -m pip install -e .
bash scripts/reproduce_v098.sh
python -m biogasflex rolling-forecast
```

For Windows: `./scripts/reproduce_v098.ps1`.
The CLI uses fabricated example data and forecast snapshots,
prints a concise summary and **writes no output by default**;
use `--output report.json` to save full step-by-step
optimization and realization results.

In the fully synthetic three-hour test, corrected forecasts
produce €70 of modeled ex-post contribution, stale
forecasts €60, and perfect hindsight €80. This does
**not** establish a real benefit from forecasting.
A separate synthetic two-hour adversarial case reports
€20 regret, independently derived from gas conservation.

The original 286 frozen scientific file hashes,
216 historic market cases and five hypothetical
emergency cases remain immutable; all inherited
dual checks, solver-free oracles, and experimental
v0.9.5–v0.9.7 audits remain in release gates.

Read the [v0.9.8 mathematical protocol](docs/V098_ROLLING_PROTOCOL.md),
[change register](docs/V098_CHANGE_EVIDENCE.csv) and
[internal numerical audit](reports/V098_INTERNAL_AUDIT.md).

**No observed equipment startup/stop transients, real
forecast uncertainty, site profit, heat-load disturbance,
gas vessel pressure dynamics or grid islanding are modeled.**

---

# BiogasFlex v0.9.7 — Clock-hour CHP commitment and carried initial obligations

**Status:** **10/10 hosted CI gates passed twice** ([final reviewed code push](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052149427) and [matching PR workflow](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052216953)); software development candidate, not
a public GitHub Release, Zenodo DOI, measured CHP control model or
independently human-reviewed research result.

The v0.9.6 **experimental** mixed-integer CHP scheduler
used minimum up/down **numbers of intervals**. v0.9.7 adds a
**separate opt-in** scheduling model enforcing minimum
ON/OFF times in **elapsed hours**, with explicit operating
obligations carried in from *before* the modeled horizon.
This matters when a 15-minute market interval and a 60-minute
interval coexist. A prior obligation may continue beyond
the horizon, but a new startup/shutdown must satisfy its
declared full commitment **within** the horizon.

```bash
python -m pip install -e .
bash scripts/reproduce_v097.sh
python -m biogasflex hourly-commitment
```

Windows PowerShell: `./scripts/reproduce_v097.ps1`.
The new CLI uses **entirely fictional** example prices/CHP
inputs, prints a summary and writes no file unless
`--output report.json` is supplied.

Verification includes an exact **solver-free two-period
binary + gas stock** oracle: for 0.25h followed by 1h, the
invented test yields €45 with minimum on-time 1h,
€40 with minimum on-time 1.01h, and is infeasible at
1.26h. A separate 24h **mixed-resolution 36-slot**
scenario checks elapsed-time and mass/heat/ramp constraints.

The v0.9.5 always-on LP, v0.9.6 binary interval-count MILP,
original 216 market scenarios and five hypothetical
emergencies remain unchanged. All original **286 research
files are SHA-256 pinned**; inherited dual/solver-free
verification and cross-platform CI remain mandatory.

See the [hour-based scientific protocol](docs/V097_HOURLY_COMMITMENT_PROTOCOL.md),
[internal audit](reports/V097_INTERNAL_AUDIT.md) and
[verification change register](docs/V097_CHANGE_EVIDENCE.csv), and\n[observed v0.9.7 reproducibility matrix](docs/V097_REPRODUCIBILITY_MATRIX.md).

**This is not evidence of calibrated CHP startup physics,
actual electricity revenues, plant economics, or
operational islanding capability.**

---

# BiogasFlex v0.9.6 — Experimental binary CHP commitment (development candidate)

**Status:** **10/10 hosted CI jobs passed** ([v0.9.6 verified development workflow](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42046779132)).\n\n**Scope:** Software verification of an explicitly synthetic on/off
gas-buffered CHP MILP. No actual plant calibration, formal independent
scientific review, published GitHub Release or DOI is claimed.

v0.9.6 adds a new **opt-in** mathematical model with binary
**on/off, startup and shutdown**, positive minimum-on electrical
power, start/stop cost assumptions, direction-specific steady-on
midpoint ramps, and minimum up/down periods. The original v0.9.5
always-on ramp LP and the entire frozen historical research study
are **not replaced**.

The three-hour toy case has invented gas and price data; an
independent Python exhaustive enumeration checks €55/€35/€15
modeled contributions for 1/2/3 minimum-up intervals. A further\n24-hour mock case checks minimum up/down periods, gas and heat\nconservation, and steady-on ramp constraints. Switching
transients are **not** physically modeled; steady-on ramp limits
are deliberately exempted across on/off transitions.

From a clean Python 3.10+ checkout:

```bash
python -m pip install -e .
bash scripts/reproduce_v096.sh
python -m biogasflex unit-commitment
```

Windows PowerShell: `./scripts/reproduce_v096.ps1`.
The new command does **not** write output unless `--output report.json`
is provided. Historical commands retain their original behavior.

The verification gate retains the original **286 pinned scientific
files**, **216 historical market dual certificates**, **216 + five
original scenario reproductions**, the inherited **96 solver-free
synthetic comparisons** and v0.9.5 operating-envelope tests.
See [exact modeling protocol](docs/V096_COMMITMENT_PROTOCOL.md),
[change register](docs/V096_CHANGE_EVIDENCE.csv) and
[internal audit](reports/V096_INTERNAL_AUDIT.md), and\n[hosted v0.9.6 reproducibility matrix](docs/V096_REPRODUCIBILITY_MATRIX.md).

**Do not treat synthetic CHP commitment value as real revenue,
annual profit, equipment availability, guaranteed islanding,
or a validated operating procedure.**

---

# BiogasFlex v0.9.5 — Experimental ramp and synthetic forecast sensitivity

**Status:** **10/10 GitHub Actions verification jobs passed** ([v0.9.5 hosted run](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42042375641)); still a research development candidate, not a published GitHub
Release, Zenodo DOI, real CHP control design, or human-reviewed
scientific finding. This version advances directly from v0.9.3:
no v0.9.4 release is being asserted.

The new **opt-in, continuously-on** CHP optimization adds directional
electric-output ramp limits and a minimum power bound while preserving
cyclic gas conservation and instantaneous heat service. A fixed
synthetic forecast dispatch can also be scored against an explicitly
supplied realized-price trajectory, with ex-post perfect-foresight
regret. **This is not a unit-commitment MILP or validated plant model.**

```bash
python -m pip install -e .
bash scripts/reproduce_v095.sh
python -m biogasflex operating-surrogate
python -m biogasflex forecast-regret
```

For Windows PowerShell use `./scripts/reproduce_v095.ps1`.
Both new commands run **entirely fabricated toy scenarios**,
show a result summary, and write no output unless `--output` is set.
The original 286 pinned scientific files, 216 24-hour market cases,
five hypothetical emergencies and inherited independent audit
checks remain unchanged.

Read the [v0.9.5 mathematical protocol](docs/V095_EXPERIMENTAL_PROTOCOL.md),
[internal audit](reports/V095_INTERNAL_AUDIT.md), and
[change evidence](docs/V095_CHANGE_EVIDENCE.csv), and\n[hosted reproducibility results](docs/V095_REPRODUCIBILITY_MATRIX.md). These experiments do
not establish actual CHP ramp/startup performance, representative
annual revenues, plant investment/NPV, calibrated forecast losses, or
islanding/black-start capability.

---

# BiogasFlex v0.9.3 — Analytical oracle and synthetic stress (development candidate)

**Status:** hosted **10/10 CI jobs passed** ([v0.9.3 verified run](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42038354589)). Still a development candidate, not a public GitHub Release, DOI, field calibration, or human peer-reviewed result.

This increment adds a **solver-free exact two-interval oracle** and a
**96-case seeded synthetic stress suite**, checking cost/price
translations, storage monotonicity, zero-buffer behavior and
irregular interval lengths. The existing 216 original market-case
primal/dual checks and the original five hypothetical outage cases
remain unchanged.

Reproduce from a complete checkout (after installing Python 3.10+
and dependencies):

```bash
python -m pip install -e .
bash scripts/reproduce_v093.sh
```

Windows PowerShell:

```powershell
python -m pip install -e .
./scripts/reproduce_v093.ps1
```

The full gate includes original independently audited research results,
**286 frozen source hashes**, 216 dual certificates, 96 synthetic
two-interval comparisons, strict manifest coverage and CI
verification. Installing dependencies may need internet access;
the research reproduction itself is offline.

See [verification protocol](docs/V093_VERIFICATION_PROTOCOL.md),
[internal audit](reports/V093_INTERNAL_AUDIT.md),
[observed host matrix](docs/V093_REPRODUCIBILITY_MATRIX.md) and
[change register](docs/V093_CHANGE_EVIDENCE.csv).
Synthetic stress does not prove real CHP economics, general 24-hour
solver independence, representative annual results, storage vessel
feasibility or outage resilience.

---

# BiogasFlex v0.9.2 — Optimality certificates (development candidate)

**Status:** pre-release with a **10/10 green hosted cross-platform CI matrix** ([v0.9.2 Actions](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42034834791)); not field validated, independently human-reviewed or DOI-published.
v0.9.2 preserves all original frozen scientific files and the 216 market / five hypothetical
outage results, while adding an independently assembled **mathematical dual**
certificate for each saved market LP. The new certificate uses SciPy/HiGHS
(as does the original solver), so it verifies a separate formulation
rather than an independent solver or physical experiment.

**Full checked-out source reproduction (Python 3.10+, SciPy>=1.11,<2):**

```bash
python -m pip install -e .
bash scripts/reproduce_v092.sh
```

Windows PowerShell:

```powershell
python -m pip install -e .
./scripts/reproduce_v092.ps1
```

This includes inherited 155 regression tests plus the new v0.9.2 tests,
clean scratch recomputation of all 221 stored market/outage cases,
source and ledger audits, 286 inherited scientific file hashes,
216 independent primal/dual checks, strict manifest and Git coverage.
Dependencies may require network access during installation; scientific
reproduction operates on included observations thereafter.
See [optimality method and boundaries](docs/V092_OPTIMALITY_CERTIFICATION.md),
[hosted v0.9.2 reproducibility](docs/V092_REPRODUCIBILITY_MATRIX.md),
[reproducibility history](docs/V091_REPRODUCIBILITY_MATRIX.md), and
[change evidence](docs/V092_CHANGE_EVIDENCE.csv).
**Do not extrapolate scenario counts into probabilities or selected-day
incremental modeled contribution into real annual CHP profit.**

---

# BiogasFlex v0.9.1 — Release engineering and checkout reproducibility

**Status:** locally and GitHub-hosted tested development release candidate. **Scientific results are unchanged from v0.9.** This increment repairs the tracked-file/manifest contract, tests distribution installation, hardens integrity checks, and makes CI reproduction more explicit. It is **not** a published GitHub release, DOI, plant validation or independent human review.

**Hosted verification (2026-11-05):** All nine GitHub Actions research-reproduction jobs passed on Ubuntu, Windows and macOS using Python 3.11, 3.12 and 3.13; a separate Ubuntu/Python 3.13 installed-wheel smoke test passed. [Inspect the successful 10-job PR workflow](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42029027186). Windows installs include the `tzdata` package, and `.gitattributes` preserves byte-identical LF research inputs in Windows checkouts. This is **software reproduction**, not external human peer review or CHP plant validation. For the observed environment-by-environment ledger, see [the reproducibility matrix](docs/V091_REPRODUCIBILITY_MATRIX.md).

## Quick start — full research reproduction

From the **complete project archive** (not a software wheel; the wheel contains code, not datasets), after installation of Python 3.10+ and SciPy:

```bash
python -m pip install -e .
bash scripts/reproduce_v091.sh
```

Windows PowerShell after installing the package:

```powershell
python -m pip install -e .
./scripts/reproduce_v091.ps1
```

Both workflows run the **155-test inherited-and-new regression suite** (subject to any subsequent test additions), recompute 216 market and five outage cases in an isolated scratch directory, run the independent output and assumption auditors, verify the installed runtime/HiGHS and check the SHA-256 release manifest. In a Git checkout, they additionally assert that all manifest files are tracked by Git; in a ZIP extraction that specific check reports **NOT_TESTED** because there is no `.git` directory. Once dependencies are installed, the reproduction itself does not access the network. A full fresh `pip install` may require package-index access; this distinction matters.

For the standard-library-only scientific provenance audit (without SciPy):

```bash
python scripts/audit_v09_candidate.py
python scripts/verify_v09_manifest.py
python scripts/verify_v091_inherited_frozen.py
```

The older `scripts/reproduce_v09.*` files remain available as historical artifacts. **Use `reproduce_v091.*` for this release**, not the older entry points.

## What is in the package

- `docs/V091_REPRODUCIBILITY_MATRIX.md`: observed versus untested OS/Python/installation paths.
- `reports/V091_RELEASE_ENGINEERING_AUDIT.md`: results, defects, evidence and deferred CI execution.
- `docs/V091_CHANGE_EVIDENCE.csv`: tracked findings and their resolution.
- `docs/V091_INHERITED_FROZEN_HASHES.json`: SHA-256 pins for inherited research inputs, LP engine and recorded outputs.
- `.github/workflows/ci.yml`: configured 3×3 OS/Python matrix plus an installed-wheel smoke job; **configuration alone is not a successful hosted workflow run**.
- `SHA256SUMS.txt`: complete archive file-integrity manifest, not a certification of scientific correctness.

**Important boundary:** the 216-case economic scenario table is a finite nonrepresentative sensitivity grid, and the five interruption cases are hypothetical conditional service accounting. The Lövsta reference supplies annual figures only; the electricity prices are from another year. No physical field validation, real operational islanding, CAPEX/profit estimate, external peer review or probabilistic robustness claim has been established.

---

## Previous v0.9 audit and scientific documentation (preserved)

# BiogasFlex v0.9 — Pre-release Reproducibility and Scientific Audit

**Status: computational reproduction candidate, not a field-validated or human-peer-reviewed release.** v0.9 preserves the v0.8 scientific findings and adds independent-from-optimizer input-contract auditing, frozen SHA-256 source checks, malicious-data tampering tests, and clean re-execution. One total-outage input validation defect was repaired. There is **no new plant-economic or resilience result** in this audit version.

**138/138 automated tests pass** (117 inherited plus 21 new). The standard-library checker audits **216 observed-price market cases and five hypothetical emergency cases**. A separate clean temporary run regenerates all 221 solved cases without altering the packaged reference outputs. Unchanged headline: 96 positive and 120 essentially zero conditional contribution cases; maximum €15.7953 in the deliberately small, nonrepresentative sample of selected days and assumed operating parameters.

## Reproduction

Prerequisites: Python 3.10+ and `scipy>=1.11,<2` for LP recomputation. Network and credentials are not required; existing plots remain included. From the extracted project root:

```bash
python -m pip install -e .
bash scripts/reproduce_v09.sh
```

On Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/reproduce_v09.ps1` after installing SciPy. Both workflows include a read-only manifest check. For the independent-of-solver checks only, run `python scripts/audit_v09_candidate.py` (uses the Python standard library).

Start with `reports/V09_RELEASE_AUDIT.md`, `docs/V09_REVIEW_PACKET.md`, `docs/V09_ISSUE_REGISTER.csv`, `docs/V09_CLAIMS_EVIDENCE.csv`, `docs/V09_FROZEN_INPUT_HASHES.json` and `CITATION.cff`.

**Use limitations:** No measured CHP hourly operation or electricity export data; 2022 annual plant figures mixed with 2020 observed market prices; no heat telemetry, part-load, start/ramp constraints, gas pressure/storage hardware costs, actual market participation, CAPEX/NPV, black-start system or validated islanding. Study outputs are bounded theoretical counterfactuals. No probabilities or representative annual revenue inferred from 96/216 positive cases.

---

## Preserved v0.8 analysis and sources

# BiogasFlex v0.8 — Market uncertainty and bounded critical-service security

**Status: locally verified research-development candidate; not field validated, independently human peer reviewed, or published to GitHub/Zenodo.** This release extends the *unchanged v0.7 heat-aware dispatch LP* with an internally predeclared 216-case market/parameter sensitivity and a **separate**, explicitly hypothetical gas-supply-interruption critical-service LP.

**117 automated tests pass** (81 inherited + 36 new). A standard-library-only numerical checker additionally audits **all 216 market cases, all five emergency cases, all price timestamps/values and the frozen scenario registry**, without importing the optimizer. These are computational tests, **not** empirical confirmation of plant flexibility, operational black start or real Swedish resilience.

## Key findings (conditional; not real plant operations)

- **Price observations:** source-licensed SE3 day-ahead prices for the first local day of January, April and October **2020**. The preselected July 1 window failed hourly-series completeness and was rejected **before uplift evaluation**, without imputation. The three retained dates are **not a statistical or representative annual sample**.
- **Economic scenario matrix:** 216 combinations covering gas buffer 0/0.25/1 MWh_LHV, heat demand 0.75/1 × *2022 annual-average heat production*, backup heat cost €20/€80 per MWh_th, electric efficiency 38/40/42%, 499 kW nameplate versus hypothetical reduced rating with 5% headroom, and the three price windows.
- **Conditional incremental scenario contribution:** 96 positive, 120 effectively zero; highest **€15.7953 per selected day**; median effectively €0. The optimized uplift is **nonnegative by construction** because the fixed case is feasible inside the LP. It does **not** establish nonnegative storage NPV or profit. No day is extrapolated to a year.
- **Assumption reversal:** 2020-04-01, 1 MWh buffer, annual-mean heat-demand factor 1, 42% hypothetical electric efficiency and 499 kW rating: **+€0.5206** uplift with hypothetical backup heat €20/MWh_th; **€0.00** at €80/MWh_th.
- **Separate emergency service test:** during a **hypothetical three-hour total gas-inflow interruption**, with assumed electricity/heat critical loads and an exogenously precharged 0.6 MWh_LHV buffer, an **assumed island-capable, available CHP** could meet up to **0.24 MWh electricity** and **0.235 MWh_th heat** in the idealized energy-service model. Without assumed islanding equipment or available CHP, even the same buffer delivers **zero** service. This is **not** actual Lövsta islanding, black-start feasibility, grid resilience or regional self-sufficiency.

## Reproduce offline

Python **3.10+** and `scipy>=1.11,<2` required. `matplotlib>=3.6` optional for regenerating the three v0.8 figures (the package contains generated images already). The price datasets are included with Svk/CC BY 4.0 attribution.

```bash
# From the ZIP's biogasflex-v0.8/ directory:
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/run_v08_study.py --plots
python scripts/independent_v08_audit.py
python -m biogasflex emergency-service \
  --config config/v08_hypothetical_emergency.json \
  --output results/v0.8/manual_emergency_example.json
```

Or use **`bash scripts/reproduce_v08.sh`** on Linux/macOS or **`powershell -ExecutionPolicy Bypass -File scripts/reproduce_v08.ps1`** on Windows to reproduce the earlier v0.7 study and its audit as well as v0.8. The shell/PowerShell paths set `PYTHONPATH` to run from a checkout without requiring a package installation, provided SciPy is available. No live network, account credentials, or proprietary plant records are required.

## Where to look

| Path | Purpose |
|---|---|
| `scenarios/registry.json` / `registry.yaml` | Frozen 216-case inputs; transparent rejection of July market-data window; five emergency cases |
| `data/observed/` | CC BY 4.0 attributed Svk 2020 SE3 snapshots for January, April and October |
| `src/biogasflex/heat_dispatch.py` | Unchanged v0.7 cyclic gas-buffer, heat-service and electricity economic LP |
| `src/biogasflex/resilience.py` | New noncyclic inventory outage model with explicit islanding/CHP availability gate |
| `scripts/run_v08_study.py` | Rebuild all 216 market scenarios and five emergency cases from registry |
| `scripts/independent_v08_audit.py` | Recompute result ledgers and compare original CSV sources without optimizer |
| `tests/test_v08_uncertainty_resilience.py` | Data QA, empirical source checks, analytical bounds, infeasible input and tampering tests |
| `results/v0.8/predeclared_scenario_matrix_results.csv` | Every economic scenario and its full assumptions and results |
| `results/v0.8/cases/` | All 216 solver outputs, including per-hour gas, heat and price ledgers |
| `results/v0.8/hypothetical_critical_service_results.csv` | Energy service under five explicit outage-capability assumptions |
| `results/v0.8/resilience/` | Emergency LP hourly records and conservation checks |
| `reports/v0.8_sensitivity_resilience.md` | Full interpretation, scenario results and scientific limitations |
| `docs/V08_MODEL_BOUNDARY.md` | Formal claims contract, assumptions and exclusions |
| `docs/V08_DATA_PROVENANCE.md` | Source, license, selection, known gap and cross-year case attribution |

## Scientific boundaries and reuse

The 2022 source-backed Lövsta facility generator and annual production figures are only *scale references*; the model is not calibrated to observed real heat loads, operational storage or electricity exports. All price observations come from different calendar years than the plant-reference quantities. The v0.8 economic LP ignores startup, ramp rates, part-load efficiency, storage CAPEX/OPEX, grid/export constraints and market participation limits; perfect price foresight is a theoretical benchmark. All heat requirements and substitute costs are synthetic assumptions, not quotes or prices charged at the plant. Thus the output is neither actual plant profit nor full techno-economic appraisal.

The emergency model is even narrower: it assumes *precharged* gas, absence of grid power and all external heat backup, optional island-capable CHP and optional plant availability. No control hardware, blackout restart system, gas-pressure infrastructure or connection safety has been verified. Report its output only as **conditional critical-energy fractions in an assumed local interruption**, never as observed grid resilience.

Source: Svenska kraftnät historical day-ahead market data, https://data.svk.se/dataset/market_data_day_ahead_area_prices, licence **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/. Academic reference: Åberg (2024), SLU thesis describing Lövsta 2022 annual generator capacity and heat/electric output. These dataset acknowledgements and modifications are detailed under `docs/`.

## Next release

**v0.9**: independent pre-release software/scientific audit, external reviewer reconciliation if available, numerical and input/data stress testing, full v1.0 claims-evidence matrix. Do not claim a DOI, peer-reviewed result, or calibrated biogas plant until evidence exists.
