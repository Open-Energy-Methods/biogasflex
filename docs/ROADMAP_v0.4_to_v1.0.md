# BiogasFlex — Evidence-Gated Roadmap from v0.4 to v1.0

**Roadmap edition:** 1.0 (planning document; not a software release)  
**Prepared:** 2026-11-05  
**Baseline specification:** `BiogasFlex_Master_Plan_v0.4.md` (2026-11-05)  
**Programme status:** pre-code. **WP1 is not yet passed**; no plant case, electricity-price series, optimization results, experimental validation or economic findings should be inferred from the existence of this roadmap.  
**Research status:** an **independent, non-affiliated** research/portfolio demonstrator, motivated by the Linköping University / Biogas Solutions Research Center doctoral vacancy IEI-2026-00717. No BSRC/LiU involvement, review or endorsement is claimed.

## Executive decision

**Ship a defensible v1.0 that makes one narrow, reproducible claim:** for a fully specified *stylized* biogas-fuelled CHP plant, a constrained gas buffer can be evaluated for its **incremental gross electricity-market revenue**, and the robustness of that result can be examined under heat-service, uncertainty and hypothetical service-disruption assumptions. The optimizer may find positive, zero or negative incremental value after defined operating penalties; **none is a failure** if the model is correct and the result is reported honestly.

The plant is **not** presumed to be a calibrated representation of a real Swedish facility; model-vs-oracle checks are **verification**, not operational validation. A regional resilience or full-project profitability claim is **not** in scope without appropriate additional evidence. No demand-driven anaerobic digestion, biomethane upgrading/injection, physical storage vessel engineering, validated plant process model or comparative life-cycle assessment is required for v1.0. They belong to later separately reviewed extensions.

**Priority rule:** Linköping job application and legally required documentation remain separate. Do not delay submitting the application until this project is completed; do not upgrade an unfinished BiogasFlex plan to a completed CV achievement.

---

## 1. Stage-gated release map

| Release | Substantive outcome | Required WP | Evidence that advances the gate | Do not claim yet |
|---|---|---|---|---|
| **v0.4 — Specified** | Frozen physical, economic and honesty boundaries; hand-worked toy oracle; test contract | WP0–WP6 plan | Approved `Master_Plan_v0.4`, traceable sources and equations | Any measured or simulated project output beyond the toy oracle |
| **v0.5 — Baseline** | Named price window, evidence register and feasible must-run CHP case; independent revenue reproduction | WP0 + WP1 | Source/rights ledger, typed configuration, timestamp QA, reproducible fixed-dispatch results, baseline audit | Benefits of storage or net profitability |
| **v0.6 — Verified flexibility** | Linear gas-buffer dispatch; exact toy optimum; analytical conservation checks; predeclared storage sweep | WP2 + WP3 electricity screen | Tests A–G and I–J, verified solver statuses, immutable configs and positive/zero cases, independent audit | Real heat-feasible CHP optimum or operation at a real plant |
| **v0.7 — CHP service constraints** | Electricity/heat co-output feasibility; heating obligations, curtailment/deficit accounting and bounded economic screen | WP3 extension | Explicit heat-demand assumption, service-constrained cases, negative/zero findings retained, decomposed revenue/operating penalties | Generalized profitability or actual operating cost optimum |
| **v0.8 — Uncertainty & service security** | Predeclared sensitivity matrix, price-window dependence and one transparent disruption/service case | WP4 | Parameter/scenario matrix, service-security boundary, sensitivity outputs, assumption-reversal analysis | Verified regional resilience, black-start or independence from grid without evidence |
| **v0.9 — Reproduction candidate** | Freeze data rights, rerun from clean environment, independent audit and reviewer package | WP5 | Full test/audit suite, reproducibility report, corrected issues, claims-to-evidence ledger, tagged prerelease candidate | Finished academic paper or peer-reviewed proof |
| **v1.0 — Citable research release** | Frozen code, inputs that can legally be shared, reports, versioned figures, public replication path and optional archive DOI | WP5 release gate | Signed release checklist; release tag; immutable archive/research report; re-execution evidence; no unresolved critical issues | Plant validation, field deployment, policy recommendation or proven nationwide benefit |

**Release sequencing:** sequential gates for computation and claims. Literature, licensing, documentation and interview learning can progress in parallel. A release number is **earned by its gate**, not by elapsed time or code volume.

### Scope discipline

- **Core deliverable (must):** v0.5–v0.8 evidence + v0.9 audit + v1.0 archived/reproducible report.
- **Conditional deliverable:** MILP commitment/start-up binaries **only if** the plant assumptions require them. Otherwise the honest and simpler model is an LP (Pyomo with HiGHS can solve either).
- **Optional after v1.0:** WP6 branch A, biomethane upgrading/grid injection with additional market and process evidence; **or** branch B, demand-oriented biological gas production with justified kinetic data. Do not quietly add either to v1.0.
- **Not a deliverable:** numerical percentages chosen in advance. No inherited PyNEXUS performance percentages, no claimed Swedish plant measurements and no manufactured positive uplift.

---

## 2. Common technical contract (all releases)

### 2.1 System boundary and units

All gas variables use **chemical energy on one explicitly selected LHV or HHV basis**, not interchangeable normal cubic metres and MWh. Define `G[t]`, `U[t]`, `F[t]`, `L[t]` in MW_gas, `S[t]` in MWh_gas; `P[t]` in MW_e, `Q[t]` in MW_th, `price[t]` in EUR/MWh_e, `dt[t]` in h, and revenue in EUR. Net export must be distinguished from gross generator output if auxiliary electric loads are later included.

At each interval, enforce:

```text
S[t+1] = S[t] + (G[t] - U[t] - F[t] - L[t]) * dt[t]
P[t]   = eta_e * U[t]
Q[t]   = eta_th * U[t]          (potentially useful heat, not automatically delivered heat)
0 <= S[t] <= S_max
0 <= P[t] <= P_max
```

Use explicit `dt[t]` even with nominal 15-minute or hourly observations; store UTC interval starts/ends and display local Swedish time separately. Reject gaps, duplicate intervals, inconsistent price units, non-physical negative durations and accidental double-counting at daylight-saving transitions. Negative prices are allowed.

**Conservation law for comparisons:**

```text
sum(U[t]*dt[t]) = sum(G[t]*dt[t]) - sum(F[t]*dt[t])
                  - sum(L[t]*dt[t]) - (S_final - S_initial)
```

Equal gas supply **does not guarantee** equal utilized gas unless losses, flaring and inventory differences are also reconciled. At the principal clean comparator, set `F=L=0`, use equal initial/final inventory, constant documented conversion efficiencies and the same supplied gas sequence. Do not describe an avoided-flaring benefit or extra consumption as *pure timing value*.

### 2.2 Headroom and physical feasibility

For an illustrative stationary baseline, `P_baseline = eta_e * G`; require `P_max > P_baseline` for **positive upward power-shifting capability**, and prove the baseline itself is feasible with gas flow, minimum load and heat-related assumptions. If there is no headroom, a zero-value or limited-flexibility result is scientifically legitimate. **Do not alter the rating to force a gain.** Ensure proposed gas storage energy is not casually asserted to be a realizable vessel volume; translating `MWh_gas` to tank volume would require gas composition, pressure, temperature and relevant standards/design assumptions outside this release.

### 2.3 Economic boundary

The primary reported quantity is **gross day-ahead electricity-market revenue**:

`R_electricity = sum(price[t] * P_export[t] * dt[t])`.

Its difference between feasible cases is **gross timing-related opportunity**, **not** profit, LCOE, system NPV, cash flow or a Swedish market forecast. If start-up, standby, storage or heat-alternative costs are added, disclose and separate the particular **scenario-specific** net proxy. When market dispatch optimizes using full price history, label it as a **perfect-foresight upper-bound schedule**, not an executable forecast. A short-price-window result must not be extrapolated uncritically into annual revenue.

### 2.4 Evidence classification and permissible claims

Every numerical figure must be labelled **official observation**, **individual-plant documented datum**, **peer-reviewed literature input**, **stylized assumption**, **algorithmically computed result**, **independent verification result**, or **unvalidated inference**. The Swedish Energy Agency's 2025 categories (2,688 GWh production, 1,805 GWh upgraded, 85 GWh electricity) are **national annual allocation figures**, not an individual CHP operating record. A verified optimization result is **not** field validation.

### 2.5 Non-negotiable data-rights rule

No blanket assertion that publicly viewable electricity prices can be republished. For each external price dataset, retain its origin, source owner, access terms, date of terms check and explicit decision on permitted distribution. The public repo/archive must provide **(a)** fully redistributable synthetic/toy fixtures for offline testing and **(b)** retrieval/processing code for actual market observations if the original terms permit access but not redistribution. Do not push restricted raw data or secrets/API tokens to GitHub, release assets or Zenodo. If restrictions prevent a legally reproducible numerical market claim, **narrow the claim** or use an alternative properly licensed data source.

---

## 3. Release specifications and acceptance tests

### v0.5 — Baseline and provenance first

**Research objective:** Does one fixed-operation biogas-CHP archetype yield a technically possible and independently reproducible gross-revenue baseline when supplied with a known market-price period?

**Tasks**

1. Finish WP0: dated bibliography; primary official statistics; Mauky et al. (2017) cited for *study-specific biological flexibility* (not used to parametrize the storage-only model); at least one additional peer-reviewed biogas CHP/gas-storage dispatch source; claim/evidence register.
2. Define plant archetype in version-controlled configuration. Prefer a documented individual CHP rating; otherwise explicitly select a **stylized** plant with independently labeled `assumed`, `sourced` and `varied` parameters. Include electrical rating, constant gas input, heat efficiency, electrical efficiency, feasible baseline output, headroom ratio, conversion basis, and initial heat-service convention.
3. Choose one Swedish bidding zone (SE1–SE4), date range and price data path. Log underlying rights; validate price interval continuity/physical duration and conversion to EUR/MWh. Keep any read-only restricted data out of the public artifacts.
4. Implement **data parsing and fixed baseline only**. Do **not** implement flexible optimization before the baseline acceptance gate. Calculate energy/gas/heat/revenue independently using a separate simple hand check or separate reference script.
5. Generate concise baseline report: inputs table, sample price QA, gas and electricity total, potential heat output, revenue, headroom, uncertainty and limitations.

**Must-exist evidence:** `sources.csv` or equivalent; `data/README.md`; `config/baseline.yaml`; baseline code; tests for timestamps and units; one normalized results ledger; `reports/v0.5_baseline.md`; audit record.

**Release blockers:** unlicensed/publicly unreproducible market data used without a lawful path; unknown unit or LHV/HHV basis; physically impossible rating/load; no headroom explanation; failure to reproduce baseline revenue; undocumented synthetic plant parameters.

**Exit rule:** a reviewer can recompute a baseline without using the optimization model. If market data cannot be retrieved, a synthetic technical baseline can be issued **as pre-release only**, but **v0.5's source-backed market gate is not passed** until an authorized observation path exists.

### v0.6 — Gas buffer + verified LP/MILP dispatch

**Research objective:** Under consistent supply and operating limits, can the model shift generation and compute the correct optimum without creating gas or money?

**Tasks**

1. Implement LP gas-storage dispatch in Pyomo/HiGHS: bounds, fuel-to-power conversion, gas-inventory dynamics, cyclic terminal inventory and objective with explicit `dt`.
2. Keep base-case `F=L=0`. Model them only as separately documented optional experiments, with accounting identities.
3. Preserve the exact **two-period oracle** from v0.4: `G=[0.6,0.6] MW_gas`, `eta_e=0.4`, `P_max=0.4 MW_e`, `S_max=0.4 MWh_gas`, price `[50,200] EUR/MWh_e`, two one-hour steps; fixed `EUR 60`, shifted `EUR 84`, uplift `EUR 24`, storage `[0,0.4,0] MWh_gas`. Independently check the computed optimum and trajectory.
4. Test zero storage, zero headroom, flat prices, negative prices, infeasible configurations, nonzero flaring/losses, and unequal timesteps. Explicitly check a **reported infeasible** state is never converted to valid zero-value output.
5. Sweep several **predeclared** storage energy capacities (including zero) against the same inputs; show dispatch/inventory plots and separate their data from headline conclusions.
6. Record objective, solver status/termination and independently calculated maximum constraint residuals; optionally cross-check small LP cases with an independent formulation or exhaustive discretized toy check.

**Must-exist evidence:** `src/biogasflex/dispatch.py`, unit tests A–G and I–J from v0.4, deterministic frozen toy, `reports/v0.6_flexibility.md`, one fully reproducible sweep fixture, model-vs-reference comparison.

**Release blockers:** energy imbalance, numerical tolerance tuned after seeing results, unstable units, false MILP description for LP, a claimed profit/benefit ignoring changed fuel use, or a solver result with unknown status.

**Exit rule:** every published v0.6 figure is reproducible from an immutable config and price-data reference. Gross value is clearly a perfect-foresight, electricity-only screening result.

### v0.7 — CHP heat-feasibility and bounded economics

**Research objective:** How much of the electricity-timing value remains once useful heat must be delivered when needed?

**Tasks**

1. Add explicit hourly/quarter-hour **hypothetical heat demand** or a source-backed service requirement; document which it is and why. Use `Q_potential = eta_th*U` and distinguish actual useful heat delivered, dumped/curtailed heat, auxiliary heat supply and unmet demand.
2. Choose a **minimal heat-service design**: at first either (A) strict `Q_delivered >= heat_demand` each interval, or (B) auxiliary boiler/backup with explicit capacity, efficiency and cost. A thermal store is optional and requires a separately checked thermal-energy balance; do not add an undocumented free buffer.
3. Compare the electricity-only upper-bound dispatch with a heat-feasible dispatch; when heat-service constraints render cases infeasible, report that result rather than backfilling imaginary service.
4. If economically screened, add only documented or prominently assumed per-start, auxiliary heat and variable operating penalties. Keep electricity gross revenue, heat benefit/cost and total **scenario-specific margin proxy** in separate columns. Storage CAPEX/OPEX and payback may be tested as stylized sensitivities but must not become a plant profitability assertion.
5. Challenge the results on high heat demand, zero heat demand, electricity/heat co-generation ratios and flat/negative price periods. Preserve a meaningful null finding if heat obligation eliminates market flexibility.

**Must-exist evidence:** service-definition document; `config/heat_service_*.yaml`; heat-demand and delivered/curtailed/backup profile plots; separate electricity and heat ledgers; tests for heat balance and infeasible service; `reports/v0.7_chp_heat.md`.

**Release blockers:** heat production treated as heat served without demand/capacity, a violation of heat obligation hidden by the optimizer, a cost described as observed when assumed, or any conflation of gross revenue and profit.

**Exit rule:** at least one electricity-only and one heat-feasible case are compared using the same fuel, prices, rating and explicitly reconciled gas consumption.

### v0.8 — Price uncertainty, bounded policy scenarios and hypothetical resilience

**Research objective:** Under which transparent assumptions does the value estimate persist, reverse or disappear?

**Tasks**

1. Pre-register a modest scenario matrix before running it: multiple separate time windows or price regimes; small/medium/large storage; two or more CHP headroom levels; electric efficiency/heat requirement variations; at least one disrupted gas-supply or CHP-availability case. Choose an observation window with a defensible data basis. Do **not** cherry-pick only high-uplift days.
2. Include **at least two non-overlapping market-price windows with different conditions** in the minimum v1.0 evidence; prefer multiple seasonal windows if authorized data supports them. Clearly label sampling limitations instead of treating samples as an annual distribution.
3. Model market uncertainty as **scenario analysis**. Price perfect-foresight dispatch remains an upper-bound benchmark; a simple fixed or rule-based dispatch comparator can be added to assess sensitivity. A forecast-aware rolling optimizer is a stretch, not required for v1.0.
4. If policy instruments are examined, define **illustrative tariff/premium/constraint scenarios**, sourced and dated where real, rather than implying that a stylized scheme is an enacted Swedish policy. Policy analysis can remain a sensitivity branch and must not outrun available sources.
5. Define exactly one hypothetical service-security case, e.g. *electric critical load that can be served during a stated outage **if** the CHP is hypothetically configured for the requisite islanded operation*, or a specified local heat-service requirement. State grid connection, switchgear/islanding and ancillary-power assumptions; a grid-connected CHP does not inherently provide black-start, islanding or regional independence.
6. Report the scenario grid, stability of results, worst/median/best conditional cases (not probabilistic confidence intervals without defensible probability models), and at least one **assumption-reversal** case.

**Must-exist evidence:** `scenarios/registry.yaml`, frozen scenario matrix, parameter-provenance notes, revenue-vs-service plots, sensitivity report, resilience scenario schematic and boundaries, `reports/v0.8_sensitivity_resilience.md`.

**Release blockers:** resilience defined as ordinary market revenue, overclaiming Swedish policy significance, invented islanding capability, hidden failed scenarios, retrospective parameter tuning to strengthen the headline, or unsourced probability language.

**Exit rule:** an informed reader can identify which assumptions dominate the result and which ones make flexibility ineffective.

### v0.9 — Independent pre-release scientific and software audit

**Research objective:** Could a skeptical reviewer reproduce the result, find the limitations and detect implementation mistakes without the author explaining them privately?

**Tasks**

1. Freeze model/config, data ledger, dependencies and scenario index; generate and record a release-candidate commit hash.
2. Run full unit/integration/physics regression suite and type/static checks; independently recompute fuel/heat/energy/revenue outputs from results tables, not from the optimizer's declared objective value. Verify solver constraint residuals under predetermined, scale-aware tolerances.
3. Reproduce from a **clean environment** on an independent machine/container or CI image. Support **no-market-credentials offline mode** using legally redistributable synthetic/test fixtures. Provide a real-data rerun script when rights permit.
4. Compare published plots to raw result tables; ensure no unpublished manual spreadsheet transforms, silently edited figures or hidden cached inputs.
5. Conduct a structured **independent review** with explicit categories: fatal, major, minor, editorial. Findings should have evidence, resolution, owner and tests, with a second pass for any model changes.
6. Write a short paper-style report with introduction, exact hypotheses, literature, system boundary, methods, data/case identification, verification, results, parameter sensitivity, interpretation, limitations, code/data availability and AI-assistance statement.
7. Decide whether the market data license permits numerical reproduction. If not, mark a claim reproducible only by authorized re-download and ensure a wholly reproducible open-data/synthetic demo; do not claim a full public rerun if it cannot be done legally.

**Must-exist evidence:** `reports/v0.9_independent_review.md`, `reports/verification_matrix.md`, clean-run log, dependency lockfile, reproducibility script, critical issue register, draft scientific report, draft `CITATION.cff`.

**Release blockers:** critical/major scientific or accounting issue open; source without rights decision; no clean rerun; inability to link a chart to a dataset/config/commit; false validation claims; a test failure hidden or bypassed.

**Exit rule:** `v1.0-rc1` is reproducible, reviewed and has **zero open fatal or major issues**. Minor issues must be listed, owned and judged non-misleading. Any model-changing fix mandates rerunning relevant gates.

### v1.0 — Frozen, citable research release

**Research objective:** Publish a stable, transparent baseline for continued biogas-flexibility research, without claiming physical validation or broader representativeness.

**Must include**

- Public repository release with immutable tag `v1.0.0`, changelog from v0.4 onward, license for **original code** and explicit third-party data-license separation; reproducible environment/lockfile, pinned HiGHS and Pyomo versions.
- Stable CLI or `make`-style commands covering installation, offline toy/baseline, dispatch reproduction, heat cases, uncertainty cases, figures and tests. Document expected runtime/resource envelope **as measured in the final release**, not invented beforehand.
- Publicly redistributable toy/synthetic inputs and reference output checksums; market-data provenance and authorized retrieval or a legally redistributable equivalent; no credential/secrets in the release.
- Research report **with scope, scenario details and negative cases**, clear distinction between source observations, assumptions and optimized outputs, final claims-evidence table, numerical verification matrix and explicit absence of plant-level operational validation.
- Release artifacts: per-scenario machine-readable tables, unit-labelled figures, model/config snapshot, software/data availability statement, limitations, reviewer resolution table and declared AI assistance.
- Research metadata: `CITATION.cff`, authorship, repository URL, persistent ORCID **only after checking the correct ID**, keywords, methods, licenses and citation instructions.
- If using Zenodo, enable/verify GitHub release archiving, check that archive excludes restricted datasets, then issue the Zenodo record/DOI. Verify metadata and exact archived release contents before advertising the DOI; record version-specific DOI and concept DOI if available.
- Website/LinkedIn dissemination only **after** release verification. Link to source, versioned report and DOI. Avoid claims of journal publication or BSRC association.

**Success means:** an external reviewer can inspect the case assumptions, rerun a complete permitted reference path, verify conservation and computation, understand heat/economic/resilience trade-offs and cite an immutable release. **Success does not depend on positive uplift, a publication acceptance or demonstrating a real Swedish biogas plant's savings.**

---

## 4. Traceable verification matrix

| ID | Invariant / QA | First mandatory | v1.0 evidence |
|---|---|---|---|
| `BIO-T01` | Gas-inventory step balance (including flaring and losses when enabled) | v0.6 | Independent residual summary, test |
| `BIO-T02` | Zero buffer forces instant utilization when no loss/flaring | v0.6 | Test + result comparison |
| `BIO-T03` | No generation headroom produces no upward shifting | v0.5 feasibility, v0.6 test | Configuration check + test |
| `BIO-T04` | Flat price and fixed efficiency, same gas use -> equal gross revenue | v0.6 | Unit test |
| `BIO-T05` | Two-step oracle optimum and EUR 60 / 84 / 24 accounting | v0.6 | Independent calculation + test |
| `BIO-T06` | Negative price accepted; objective dimension correct | v0.5 parsing, v0.6 optimizer | Regression test |
| `BIO-T07` | UTC and 15-minute/DST handling does not invent time/energy | v0.5 | Timestamp fixture + validation report |
| `BIO-T08` | Solver infeasible/unbounded/invalid state surfaced distinctly | v0.6 | Solver-status tests |
| `BIO-T09` | Thermal potential vs useful heat vs discarded/backup heat separated | v0.7 | Heat-ledger tests |
| `BIO-T10` | Heat-demand minimum satisfied or clearly reported infeasible | v0.7 | Scenario/service test |
| `BIO-T11` | Change in gas utilized decomposed into throughput, flaring/loss and inventory terms | v0.6–v0.7 | Comparator ledger |
| `BIO-T12` | Scenario set frozen before sensitivity results reviewed | v0.8 | Pre-registered YAML/hash |
| `BIO-T13` | Hypothetical outage case uses explicit delivery/islanding assumptions | v0.8 | Boundary checklist |
| `BIO-T14` | Restricted inputs excluded from public archive; offline reproduction works | v0.9 | License scan, clean-run log |
| `BIO-T15` | Every headline result has config+input+code+figure provenance | v0.9 | Claims-to-evidence map |
| `BIO-T16` | Fatal and major independent-review findings closed before release | v1.0 | Signed issue-resolution table |

**Numerical tolerance policy:** choose scale-aware, predeclared constraint tolerances and independent recomputation. Reference thresholds in test configuration. Do not post hoc relax checks to allow a desired result; if numerical scaling is a problem, fix units/formulation or explicitly record a failed gate. Reproducibility covers **data, code, parameters, solver settings and figure scripts**.

---

## 5. Repository and research-artifact architecture

Proposed paths (create during v0.5, adjust only with an explicit decision record):

```text
biogasflex/
  README.md
  LICENSE                       # original code only
  CITATION.cff                  # add no later than v0.9
  CHANGELOG.md
  pyproject.toml
  uv.lock / requirements.lock   # one documented environment strategy
  Makefile / scripts/reproduce.sh
  docs/
    MASTER_PLAN_v0.4.md        # preserve original spec
    ROADMAP_v0.4_to_v1.0.md
    research_question.md
    assumptions.md
    data_and_reuse_rights.md
    sources.csv
    decisions.md
    limitations.md
  config/
    baseline.yaml
    dispatch.yaml
    heat_service.yaml
    scenarios.yaml
  src/biogasflex/
    inputs.py
    units.py
    baseline.py
    dispatch.py
    heat_service.py
    scenarios.py
    accounting.py
    reporting.py
  data/
    README.md
    synthetic/                  # redistribution permitted
    external/                   # local-only / gitignored unless explicitly licensed
  tests/
    test_oracles.py
    test_mass_energy_balance.py
    test_market_times.py
    test_heat_service.py
    test_solver_status.py
    test_reproducibility.py
  results/
    MANIFEST.md                 # provenance, checksums and scope
    v0.5/ ... v1.0/
  reports/
    baseline.md
    verification_matrix.md
    review_findings.md
    technical_report.md
  scripts/
    fetch_licensed_prices.py
    run_baseline.py
    run_sweep.py
    make_figures.py
    reproduce_release.py
```

**Git hygiene:** source and small permitted synthetic fixtures committed; restricted input data and credential files ignored and scanned; outputs must have manifests and checksums; no manual alterations to plots. A private data-access token must never appear in archive, CI log or published notebook. CI should run the full synthetic suite with no secrets; real-data runs can be optional access-controlled jobs when permitted.

### Version metadata and issue control

For every milestone, create:
- `CHANGELOG.md` entry listing new scientific claims and what remains unverified.
- Release tag and source commit SHA; `results/<version>/manifest.json` containing code SHA, input hashes/retrieval metadata, configuration hash, solver/version, execution timestamp, unit definitions and output hashes.
- `decisions.md` entries for deviations from v0.4, each with reason, scientific effect and affected regression tests.
- Review classification **fatal / major / minor / editorial**. Failing critical physical tests are blockers, never mere stylistic issues.
- No ‘v1.0’ label for a feature-complete but non-reproducible draft; use `-rc` until validated against the release criteria.

---

## 6. Predeclared case and scenario strategy

### Fixed comparison hierarchy

1. **Fixed must-run baseline:** gas supply consumed when produced; no storage; common conversion assumptions.
2. **Electricity-only buffered ideal upper bound:** same gas availability/consumption, storage bounds and perfect foresight. Explicitly an idealized gross revenue screen.
3. **Heat-feasible buffered operation:** same inputs, explicit heat service and auxiliary options; electricity/heat ledgers separate.
4. **Assumption sweeps:** storage capacity, heat requirement, generation headroom, efficiency, price conditions and specified market/policy sensitivity.
5. **Separate hypothetical outage:** service-security response under explicitly stated electrical or heating service boundary. Do not merge this into regular electricity market income.

### Case-selection controls

- Price windows and scenario parameters chosen **before** inspecting model uplifts; document the choice and ensure low, ordinary and high volatility are not selected purely to favor storage.
- Store separate cases for a period where storage gives *zero* uplift and for an adverse heat/service constraint. Negative results are mandatory to report **if they occur**; do not fabricate a negative finding.
- Avoid full-year statistical confidence language unless year and probability sampling support it. If a single price window is all that is accessible, v0.8 can document a constrained pilot but cannot claim broad temporal robustness for v1.0. Obtain an additional permitted window or narrow release conclusions.
- Electrical output at the generator is not automatically export revenue if own-consumption/parasitics or export caps are modelled; keep the point of measurement fixed across cases.
- Report **conditional** results: "under this stylized plant, these electricity prices, this fuel, this heat-service rule and perfect foresight ..." not "Swedish biogas plants can earn X".

---

## 7. Review and release-quality framework

### Named evidence gates

- **Gate A — Physics & units:** conservation, CHP capacity/headroom, gas-energy basis and time aggregation checked. Mandatory v0.5–v1.0.
- **Gate B — Data provenance & legal reuse:** named source, access timestamp, interval QA and redistribution status. Mandatory v0.5–v1.0.
- **Gate C — Optimization correctness:** toy oracle, infeasibility, objective reconciliation, solver logs. Mandatory v0.6–v1.0.
- **Gate D — Service & comparison integrity:** heat delivered versus generated, comparable gas input/used, honest gross/net classification. Mandatory v0.7–v1.0.
- **Gate E — Scientific sensitivity:** predeclared variations and scope-limited hypothetical resilience. Mandatory v0.8–v1.0.
- **Gate F — Independent reproduction:** clean installation, offline demo, legal market path, figures and full evidence trace. Mandatory v0.9–v1.0.
- **Gate G — Public-release integrity:** immutable archive, DOI if obtained, metadata, all major findings resolved. Mandatory v1.0.

### One release scorecard per version

```text
Release target: v0.X
Commit SHA: ...
Frozen input/config hashes: ...
New claim permitted: ...
Model/data boundary changed: yes/no, and why
Physics and units gate: pass/fail
Data and rights gate: pass/fail
New version-specific gate: pass/fail
Independent reviewer / second-pass status: ...
Open fatal: 0   Open major: 0   Open minor: ...
Build/test reproducibility: pass/fail
Release decision: GO / NO-GO / CONDITIONAL PRE-RELEASE
```

**Do not assign a version as complete solely because a reviewer says "looks good."** The gate must be backed by inspectable reproducibility artifacts and negative/error tests.

---

## 8. Citation, archival and publication plan

**Scientific integrity first:** a software DOI makes an immutable record citable; it does **not** constitute peer review or validate results. An arXiv-style manuscript or journal submission is optional and depends on genuine novelty, literature coverage and author review—not a mandatory launch requirement.

**At v0.9:** verify license compatibility, write manuscript-like report, draft `CITATION.cff`, confirm ORCID from actual user record, test GitHub–Zenodo archive on a suitable prerelease or use a direct deposit only if appropriate. Do not accidentally generate multiple ambiguous citation versions. Prepare records of authorship/contributions, funding (if any), AI assistance and code/data availability.

**At v1.0:** release signed/annotated Git tag and notes, attach the published report and permitted fixtures, audit exact archive bytes and metadata, verify a resolvable version DOI if archived, and record citation instructions. A release can be technically valid **without a DOI if archiving is temporarily unavailable**; never imply a DOI exists before confirming the record. Website and LinkedIn post should focus on the bounded result, reproducibility path and where the model is **not** validated.

### Possible v1.0 output claims (templates, not asserted findings)

> "For an explicitly stylized biogas-CHP case and selected Swedish bidding-zone day-ahead price windows, we evaluated the difference in *gross* revenue between must-run and ideal storage-buffered electricity dispatch, subject to a common gas-energy budget. We then quantified how explicit heat-service and disruption assumptions affect the result. The model is numerically verified and reproducible; it is not validated against operating data from a specific biogas plant."

Do not insert invented percentages, prices, annual values, emissions reductions or plant-specific capacities into this statement before the studies are executed.

---

## 9. Risk register, triggers, mitigation and scope cuts

| Risk | Trigger | Response | Impact on milestone |
|---|---|---|---|
| Market-price rights block redistribution | Terms exclude raw publication | Publish code, checksums/provenance, instructions and lawful synthetic example; seek permitted alternative | Blocks a claim of fully public *real-data* reproduction unless alternate licensed data found |
| No credible individual Swedish CHP site data | Rating/operation inaccessible | Stylized case with provenance and sensitivity; never call it a specific plant | Does **not** block v1.0 if hypothetical status prominent |
| Baseline at full CHP load | `H <= 1` | Accept zero-upward-flexibility or select an explicitly alternative justified archetype | Blocks claiming available upward shift in that case |
| MILP scope creep | Features added to create complexity | LP baseline; binaries only with credible operating conditions | Optional feature deferred |
| Negative prices/heat constraints make fixed case infeasible | Contradictory assumed services/loads | Report infeasibility, revise separately logged case and keep original as negative evidence | Do not hide/replace invalid cases |
| Heat obligation erases uplift | Binding demand constraint | Report as an important bounded result | **Not** a failure |
| Perfect-foresight bias | Historical prices known in optimizer | Label upper bound; optional rule-based comparator | Blocks realized-revenue claims |
| Synthetic case mistaken for plant validation | Language uses "validated" | Report "numerically verified"; conspicuous limitations and data provenance | Fatal external-claim blocker |
| Sensitivity matrix proliferates | New unplanned dimensions | Freeze minimum matrix; defer extensions | Keep v1.0 focused |
| Zenodo DOI or licensing not ready | Archive/rights blocker | Freeze release candidate with clear metadata; archive only when verified | Do not advertise unconfirmed DOI |
| Application deadline creates pressure | v1.0 not done by recruitment deadline | Submit existing documented experience; keep project separate | No project-driven application delay |

---

## 10. Decision points to close before each gate

**Before v0.5:** What exact stylized or sourced CHP rating and input are used? Which SE bidding zone and permitted price window? Which LHV/HHV basis and constant efficiencies? What heat output is recorded at baseline? Who owns/restricts the price series? No selection has yet been executed.

**Before v0.6:** Is LP physically adequate? Is zero flaring/loss credible as an idealized comparator? Which predeclared buffer sizes? What result tolerances and solver-status checks?

**Before v0.7:** How is heat service defined? Strict delivery versus backup? What exactly is the bounded economic screen and source/assumption status of each cost?

**Before v0.8:** Which price windows and policy proxies are supportable? What disruptions and services are hypothetically enabled? Which sensitivity extremes could invalidate the conclusion?

**Before v0.9:** Can an external user run the release offline without raw restricted observations? Are the data and software license distinctions honest? Who is the independent reviewer?

**Before v1.0:** Are there any critical unresolved scientific claims? Can code/config/results/plots be traced to hashes? Have negative cases and all limitations been preserved? Are archive contents and citation metadata confirmed?

---

## 11. Immediate ordered backlog (first working session)

1. Add v0.4 master plan and this roadmap to a version-controlled project; preserve v0.4 unchanged as a baseline specification.
2. Create the source and data-rights ledger (including official Swedish biogas 2025 categories and peer-reviewed process-flexibility sources).
3. Write the smallest public **synthetic reference fixture** using the v0.4 two-period oracle, with expected revenue and storage checks. This can be done as a QA artifact without violating the "no flexible solver until WP1 passes" rule.
4. Search for a documented individual Swedish biogas CHP rating; if no adequate case is accessible, explicitly pick a stylized archetype and freeze assumptions with bounded sensitivity choices.
5. Decide bidding zone and historical price window; register/retrieve permitted price observations, check UTC/15-minute coverage and owner terms.
6. Implement and independently check the **fixed** gas-to-electricity CHP baseline. Record a gate review. **Only then** start v0.6 flexibility optimization.

### Final v1.0 definition of done

**v1.0 is complete only if all are true:**

- [ ] v0.5 source-backed baseline accepted and independently recomputable.
- [ ] v0.6 storage optimizer satisfies conservation and toy/negative-case tests; output labels honest.
- [ ] v0.7 heat-service constrained evaluation reported, including infeasible or zero-value cases if found.
- [ ] v0.8 preregistered sensitivity and explicitly hypothetical service-security scenario reported.
- [ ] v0.9 clean-environment reproduction, rights audit, and independent technical review passed; no fatal or major issues open.
- [ ] Complete v1.0 technical report and machine-readable results include the full assumptions and absence of physical plant validation.
- [ ] User can reproduce **some complete public reference study without access to restricted data** and has documented instructions for the real-price study if legally accessible.
- [ ] Code/data/archive licensing and citation instructions reflect actual permissions; all release metadata verified.
- [ ] Stable `v1.0.0` code release/tag and changelog exist; archived version DOI only claimed if verified.
- [ ] CV, website and social dissemination describe only actually completed results, with no BSRC affiliation claims.

**Stop condition:** Once v1.0 checks pass, freeze the release. New scientific questions go to `v1.1+` or a separate reactor/upgrading research programme rather than retroactively changing frozen v1.0 evidence.

---

## Authoritative v0.4 source anchors (retained; do not substitute with unrelated claims)

- Swedish Energy Agency, official 2025 production and end-use allocation: <https://www.energimyndigheten.se/nyhetsarkiv/2026/okad-biogasproduktion-i-sverige-under-2025/> (last updated 2026-10-01).
- Mauky et al. (2017), full-scale demand-driven flexible feeding: <https://doi.org/10.1016/j.anaerobe.2017.03.010>.
- Biogas Solutions Research Center overview (research context, **not affiliation**): <https://liu.se/en/research/biogas-research-center>.
- ENTSO-E Transparency Platform (availability and terms must be checked per dataset): <https://transparency.entsoe.eu/>.
- Nord Pool 15-minute market implementation: <https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/2025/q4/15-minute-mtu-in-sdac-was-implemented/>.

**Document control:** This is a **forward-looking roadmap** derived from `BiogasFlex_Master_Plan_v0.4.md`. No release beyond the v0.4 specification has actually been built, tested or published by creating this document.
