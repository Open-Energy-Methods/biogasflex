# BiogasFlex v0.9 — Pre-release Scientific and Software Audit

**Audit date:** 2026-11-05  
**Assessment:** `PASS — COMPUTATIONAL REPRODUCTION CANDIDATE`; external/human research review still open.  
**What was audited:** the v0.8 observed-price/assumed-CHP dispatch and explicitly hypothetical outage studies, retained in full, plus boundary and provenance checks added for v0.9.  
**Reviewer status:** An AI-assisted/internal engineering audit with independent *code paths* for saved-output checking and analytical reference tests. **This is not an independent human review, field validation, journal peer review or third-party certification.**

## Executive verdict

The frozen v0.8 numerical outputs remain reproducible from source. The v0.9 candidate addresses two real defects in verification coverage/input-boundary enforcement without introducing a new economic claim. No fatal scientific or software issue was found **within the limited claims contract**. There remain material gaps preventing plant-level operational or profitability claims: no observed hourly plant operation, no measured onsite heat demand, no physical gas-storage vessel model, no equipment start/ramp/part-load constraints, no actual electricity exports, no capital costs, and no proven islanding. Those are exclusions, not issues fixed by more regression tests.

The project is suitable for **independent external methodological review and pre-release replication**. A public v1.0 should not describe itself as experimentally validated or independently peer reviewed unless evidence is obtained.

## Verified scientific results and unchanged evidence

- **216 economic market/parameter cases** from a frozen factorial scenario registry; **96 positive**, **120 effectively zero** incremental modeled operating-contribution cases, **none negative** within ±1e−7 EUR. The maximum is **€15.795327799657514 per chosen day**. Median numerical floating-point residue is about 8.5e−14 EUR (scientifically zero); label as **€0.00** in prose.
- Price snapshots: 1 Jan 2020, 1 Apr 2020, 1 Oct 2020 in SE3. The predeclared 1 Jul 2020 window was excluded because its source-data hour sequence was incomplete, without interpolation or cherry-picked replacement. Three days do not represent an annual probability sample.
- Åberg's 2024 SLU master's thesis gives Lövsta 2022 **499 kW** CHP motor maximum electrical rating, **3,002.6 MWh_e annual output** and **2,939.5 MWh_th annual heat output**. An SLU environmental report for 2022 independently provides rounded 3,003 MWh electricity and 2,940 MWh heat from its biogas facility. These annual totals do not identify hourly production, consumed-on-site versus exported electricity, gas availability or storage headroom.
- The flexibility LP uses **hypothetical** flat production, LHV efficiencies, constant heat service, auxiliary-heat capacity/cost, heat-rejection capacity, CHP rating variants, storage inventory and perfect foresight. Different CHP efficiencies are intentionally varied. Therefore the reported incremental contribution is **not** real operating income or a result for Lövsta's observed daily operations.
- An independent two-interval oracle (`tests/test_v09_audit_contract.py`) derives an optimum at 0.5 MWh_LHV inventory: **€10 gross electricity uplift less €1.25 backup-heat cost and €0.50 heat-dump cost = €8.25 contribution uplift**.
- Five hypothetical three-hour emergency cases test **critical-energy-service accounting** conditional on availability of an island-capable CHP, precharged store, zero new gas supply, no grid supply and no auxiliary heat. A 0.6 MWh_LHV buffer can serve 0.24 MWh_e and approximately 0.235 MWh_th in the synthetic test. Neither black start nor real Lövsta service continuity has been observed.
- The mathematical fact that optimized contribution cannot be lower than a feasible fixed comparator is **not** evidence that gas storage is profitable. Neither investment costs nor a realistic storage pressure/recompression system is priced.

## v0.9 defects, severity and resolution

| Finding | Severity | Resolution | Evidence |
|---|---|---|---|
| V09-001: prior numerical checker trusted several scenario input fields carried by saved outputs without independently reconstructing them from the registry | **Major — closed** | New standard-library audit pins original hashes and checks full supply/heat/price/cost/CHP assumptions per interval, baseline fixed use, outage definitions and aggregate case statistics | `scripts/audit_v09_candidate.py`, 216 cases, tampering tests |
| V09-002: emergency-service API accepted nonzero gas input while labeling a case a total gas-inflow interruption | **Major — closed** | `src/biogasflex/resilience.py` explicitly rejects nonzero inflow in this model family | New negative test, unchanged five recorded zero-inflow results |
| V09-003: package-level `__version__` in v0.8 still declared 0.7.0 | **Minor — closed** | Updated public package version to 0.9.0; historical solver JSON reports its originating model version by design | `pyproject.toml`, `__init__.py` |
| V09-011: GitHub Actions workflow still only checked v0.7 and manifest would include `.git` metadata in real CI | **Minor — closed** | Run full v0.9 gates on Python 3.11–3.13, ignore `.git` checkout metadata in integrity enumeration | `.github/workflows/ci.yml`, `scripts/verify_v09_manifest.py` |
| V09-004: absent hourly plant/export/heat operating data | **Out-of-scope major** | Source-backed scale reference only; no plant validation claim | Claim register C03–C05 |
| V09-005: no verified CHP transient dynamics, plant economics, policy model or gas-storage vessel design | **Out-of-scope major** | Strict perfect-foresight marginal contribution terminology and model boundary | `docs/V08_MODEL_BOUNDARY.md`, C07–C10 |
| V09-006: no demonstrated real emergency islanding/black start | **Out-of-scope major** | Keep emergency cases purely hypothetical; do not infer national or regional resilience | `docs/V09_REVIEW_PACKET.md`, C11–C12 |
| V09-008: no external human reviewer | **Outstanding governance gate** | Prepare reviewer packet and retain explicit reviewer-status disclosure | `docs/V09_REVIEW_PACKET.md` |

## Independent computational checks

1. **Inherited regression suite:** 117 original v0.8 tests unchanged and passing.
2. **New adversarial/analytical tests:** 21 additional v0.9 tests (138 total), including source/assumption mutation rejection, uniform market-price translation invariance, monotonicity with added storage, negative prices, closed-form heat-cost oracle, and total-outage input rejection.
3. **Standard-library numerical checker:** `independent_v08_audit.py` recomputes fuel/heat/electricity/service/revenue from saved interval ledgers; `audit_v09_candidate.py` adds reconstructing the frozen scenario inputs and source hashes. It neither calls `linprog` nor imports the model package.
4. **Independent clean-scratch rerun:** `recompute_v09_against_frozen.py` creates an isolated temporary project with source/observations/configuration, re-solves **216 LP cases and five emergency cases**, then compares all fixed/optimized/economic aggregates with the shipped result records to 2e−6 in their respective units. No network required; no overwriting of the published reference files.
5. **Integrity:** file-by-file SHA-256 manifest checks source, datasets, images, simulation outputs, documentation and scripts; SHA source-pin file guards the original registry/price snapshots separately from the output manifest.
6. **Reproduction:** `scripts/reproduce_v09.sh` and PowerShell equivalent run tests, clean recomputation, standard-library audits and package manifest checks. A clean extracted ZIP is tested before delivery.

### Numerical interpretation and confidence boundary

The model is a *linear program* (LP), not a unit-commitment MILP; HiGHS is used through SciPy. Its results are constrained optima **for the specified simplifications**, not field-validated dispatch policies. The scenario-count ratio 96/216 must never be described as a probability, success rate for Swedish sites, or confidence level. Exact optimization results do not establish economic accuracy; perfect-foresight market prices create an upper-bound scheduling premise. Short observations across three days give no basis for annual cashflow extrapolation.

### Source and rights confirmation

- **Svenska kraftnät day-ahead resource:** `https://data.svk.se/dataset/market_data_day_ahead_area_prices/resource/cf392ef3-7345-4e98-970e-83088c185570`; openly published as **CC BY 4.0**, historical data in EUR/MWh. Selected 2020 observations are hourly despite more recent dataset metadata describing 15-minute resolution. Provider warns that the service has missing periods and stopped updating 1 July 2026. Modifications: filtered to SE3/day and retained four fields with explicit UTC offset. Producer: **Svenska kraftnät**, provider attribution maintained.
- **SLU Åberg (2024) master's thesis:** `https://stud.epsilon.slu.se/20493/1/aberg-a-20240904.pdf`, §5.4 and table 1. The thesis addresses plasma-based fertilizer production, not a dedicated operating audit of gas storage or CHP flexibility. Use its figures only as source-published annual plant reference information.
- **SLU environmental report 2022:** `https://internt.slu.se/globalassets/mw/stod-serv/miljo/miljoredovisning-2022` confirms rounded electricity and heat from institution's biogas facility, not operating exports.
- **Mauky et al. (2017), Anaerobe:** DOI `10.1016/j.anaerobe.2017.03.010` demonstrates intraday biological gas-production flexibility **up to ±50%** in a particular full-scale setting. It is background research, **not** a parameter for the constant-gas-supply LP.

## Release recommendation

**Accept v0.9 as an auditable pre-release/reproduction candidate; do NOT describe it as a peer-reviewed research result.** Prior to v1.0: (i) run the supplied clean ZIP reproducer on another machine/OS if possible, (ii) request external human review of physics, source provenance and claim scope, (iii) close any fatal/major *in-scope* findings, (iv) select and publish a citable versioned GitHub release and optionally an immutable Zenodo deposit when actually created, (v) recheck that downstream summaries repeat the limitations and do not suggest profitability, policy or real outage readiness.

**No DOI, third-party reviewer acceptance, live plant telemetry, peer-reviewed paper, GitHub release tag or Zenodo deposit is claimed for v0.9.**
