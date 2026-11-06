# BiogasFlex v0.9.9 — Observed-price chronological replay, hypothetical CHP

**Research software only.** This opt-in experiment combines **actual
2020 Svenska kraftnät SE3 market prices** with an **entirely synthetic CHP,
gas storage and heat-service model**. The sequential hourly reveal of
prices is an *imagined* information regime, **not a real day-ahead
electricity market forecast or operational trading strategy**.

The new `historical-replay` command runs **two predeclared 24-hour
held-out days (April 1 and October 1, 2020)** using January 1 as
chronologically earlier context. Two simple causal predictor baselines
are applied to the existing v0.9.8.1 rolling-horizon commitment MILP:

- **last_observed:** hold the latest already observed price constant
  over the remaining planning horizon;
- **trailing_three_mean:** hold the mean of the last three already
  observed prices constant over that horizon.

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
