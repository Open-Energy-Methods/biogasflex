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
