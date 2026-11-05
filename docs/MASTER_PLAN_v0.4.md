# BiogasFlex — Master Plan v0.4

**Date:** 2026-11-05  
**Status:** pre-code research and modelling specification; **WP1 not yet passed**.  
**Research context:** Independent portfolio study motivated by Linköping University / Biogas Solutions Research Center PhD vacancy IEI-2026-00717; **not affiliated with, commissioned by, reviewed by, or endorsed by BSRC or Linköping University**.

**v0.4 decision:** RETAIN the v0.3 research question and WP0–WP6 sequence. Correct the gas accounting and comparison logic, distinguish observed sector statistics from hypothetical individual-plant parameters, correct cross-references, and pin directly verified primary sources. Do **not** add biological production modelling to the initial computational scope. Do **not** start writing the flexible dispatch solver until the baseline feasibility and reproducibility gates have passed.

**Why this exists:** The candidate's established energy-systems/dispatch-modelling portfolio fits LiU's mathematical modelling, scenario-analysis and techno-economic methods; the main domain gap is biogas-specific knowledge. BiogasFlex applies an already practised Pyomo/HiGHS dispatch pattern to the storage, utilization and constrained value of a different energy carrier. It is a demonstration of methodology, **not** established biogas engineering expertise, a plant-validated study or a claim that a doctoral research question has been solved.

---

## 1. Evidence foundation: what is verified and what remains an assumption

### 1.1 Two distinct flexibility mechanisms

- **Storage-buffered utilization flexibility (modelled in WP1–WP4):** biogas is produced at a specified rate, buffered in gas storage, and consumed by a dispatchable utilization device—initially a biogas-fuelled CHP unit—when it is useful or valuable. This is a narrower research question than full biological production flexibility.
- **Demand-oriented biological production flexibility (literature anchor, not in baseline model):** reactor feeding and process dynamics can alter the timing of gas production. Mauky et al. (2017), *Anaerobe* 46, 86–95, DOI [10.1016/j.anaerobe.2017.03.010](https://doi.org/10.1016/j.anaerobe.2017.03.010), document full-scale intraday production dynamics **up to approximately ±50% relative to the studied average** and potential reductions in required gas storage. These are **study-specific observations**, not a universal response guarantee for digesters with other feedstocks, reactor designs or operating regimes. The earlier v0.1 assertion that digestion cannot respond within hours was incorrect.
- **Pragmatic modelling boundary:** a credible biological-response model would need kinetic/feeding, gas-composition and operating data not currently available. Thus WP1–WP4 use fixed or exogenously specified production—not because process flexibility is physically impossible, but because this first study can make a more controlled, auditable comparison without inventing reactor dynamics.

### 1.2 Official Swedish sector statistics (primary source verified)

The Swedish Energy Agency, in its official report/article **“Ökad biogasproduktion i Sverige under 2025”**, last updated **2026-10-01**, reports Swedish-produced biogas of **2,688 GWh during 2025**. Its end-use/allocation table states: **1,805 GWh** upgraded to biomethane (67%); **397 GWh** in its heat category (15%); **85 GWh** in its produced-electricity category (3%); **95 GWh** direct industrial use (4%); **265 GWh** flaring losses (10%); **2 GWh** other uses; **39 GWh** missing data/heat losses (totals 2,688 GWh). The source notes that the heat category can include internal consumption and heat losses depending on facility type.

**Interpretation boundary:** These are national annual categories, **not** measurements of one CHP plant, an installed electrical capacity, a headroom factor, a gas-storage volume, an hourly gas-input profile, or CHP electrical and thermal efficiencies. In particular, do not infer a plant's fuel input or heat-to-power ratio simply from the 85 GWh electricity line. The first case intentionally concerns a comparatively small Swedish biogas-utilization pathway rather than the sector's dominant biomethane upgrading pathway. Do not silently treat the 2025 electricity, heat and gas-allocation categories as interchangeable physical quantities.

**Primary citation:** [Energimyndigheten, 2026-10-01](https://www.energimyndigheten.se/nyhetsarkiv/2026/okad-biogasproduktion-i-sverige-under-2025/). Supporting dataset portals: [SCB EN0124](https://www.scb.se/en0124-en) and [Energigas Sverige](https://www.energigas.se/). Record exact table edition, URL, access date, units and definitions in the source ledger when WP1 starts.

### 1.3 Electricity prices and reuse restrictions

- **Preferred acquisition path:** [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/) for a named Swedish bidding zone (SE1, SE2, SE3 or SE4), defined historical window and recorded retrieval timestamp. Registration may be needed for API/download access.
- **Data rights:** ENTSO-E's platform access does **not** imply that all underlying primary-owner price series may be publicly redistributed. Before committing raw prices or a derived full-resolution mirror to GitHub/Zenodo, check the applicable **primary-owner reuse status** and current ENTSO-E terms. Otherwise publish retrieval instructions, provenance, code and any demonstrably permitted small examples; keep restricted raw data outside the public archive.
- **Time resolution:** The European day-ahead market implemented 15-minute market time units for delivery beginning **2025-10-01**. For a later window, retain the 15-minute series or document energy-consistent aggregation to hourly resolution; specify time-zone conventions (UTC internally, Europe/Stockholm for display), handle DST 23/25-hour days, missing/duplicate periods, negative prices, currency and €/MWh versus SEK/MWh. Never silently assume every local day has 24 observations.
- **Objective:** model *gross day-ahead electricity-market revenue* first—not retail bill savings, balancing-service value, ancillary-service revenue, grid support, full plant profit or a policy evaluation. Additional revenues and costs require separate, explicitly bounded cases.

Sources: [Nord Pool 15-minute MTU implementation notice](https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/2025/q4/15-minute-mtu-in-sdac-was-implemented/); [ENTSO-E Transparency terms](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fterms+and+conditions%2F230309_ENTSOE_Transparency_Terms_Conditions_MC_APPROVED.pdf).

---

## 2. Study question, boundary and case selection

### 2.1 Primary research question

**For an explicitly specified biogas-fuelled CHP archetype with a given gas supply, what incremental gross day-ahead electricity-market revenue can an idealized, capacity-constrained gas buffer unlock relative to a must-run operating pattern, and how does that answer change when heat obligations, losses and disruption scenarios are introduced?**

This is an **illustrative value-of-flexibility** question, not a general estimate for Swedish biogas or a claim of optimal Swedish energy policy.

### 2.2 Plant archetype: evidence-backed versus hypothetical

**Preferred:** Identify a published **individual Swedish biogas-to-CHP** example with a citable electrical rating, operating context and (ideally) gas production and heat use. If plant-level utilization and storage parameters are not public, do not fill gaps by calling national aggregates “representative plant measurements.” Instead use a **transparent stylized Swedish CHP archetype** with each parameter tagged **observed / literature-sourced / assumed / sensitivity range**. A plant example can contextualize size without implying the exact model is a digital twin of that plant.

**Mandatory headroom gate:** The rated CHP output must exceed its hypothetical fixed-gas baseline output if the objective is to demonstrate *upward* time shifting. For constant input and efficiency, calculate

\[
\bar P_{\mathrm{baseline}}=\eta_{e}\,\bar G_{\mathrm{gas}},\qquad
H=\frac{P_{\mathrm{CHP,max}}}{\bar P_{\mathrm{baseline}}}>1.
\]

Here \(G_{\mathrm{gas}}\) is gas **energy-input rate** (MW on a consistent LHV or HHV basis), and \(\eta_e\) is the matching electrical efficiency. A hypothetical utilization of **60% of rated electrical capacity** is allowable as an **assumption**, not an observed Swedish national mean. If no feasible headroom can be supported, the correct outcome may be zero upward flexibility; do not resize solely to manufacture an attractive revenue result. Record why the chosen case is a meaningful but bounded illustration.

**Services:** CHP produces **electricity and heat**. The initial electricity-only valuation is a consciously limited screening case. It must not be called a validated full CHP operation or economic optimum. Heat obligations/curtailment and their value are examined explicitly in WP3, not ignored in final interpretation.

### 2.3 Definitions and units frozen before implementation

| Symbol | Meaning | Unit / rule |
|---|---|---|
| \(G_t\) | biogas delivered into the modelled storage/CHP boundary | MW\(_{gas}\), chosen LHV/HHV basis |
| \(U_t\) | biogas energy withdrawn for CHP utilization | MW\(_{gas}\) |
| \(F_t\) | deliberately flared/vented energy-equivalent biogas stream, if allowed | MW\(_{gas}\), separate from other losses |
| \(L_t\) | modelled gas loss/leakage or storage loss, if applicable | MW\(_{gas}\); never double-count \(F_t\) |
| \(S_t\) | gas inventory at beginning of interval | MWh\(_{gas}\) |
| \(P_t\) | net electrical output | MW\(_e\) |
| \(Q_t\) | potentially useful CHP heat output | MW\(_{th}\) |
| \(\pi_t\) | day-ahead electricity price | EUR/MWh\(_e\), unless explicitly converted |
| \(\Delta t_t\) | length of interval | hours; 0.25 or 1 for regular data |

Use interval timestamps and explicit durations so \(\pi_t P_t\Delta t_t\) produces **EUR**; don't sum prices or powers as if they were energies. Keep gross gas chemical energy, electric output and heat output on distinct unit labels. Fix any efficiency or gas calorific-value basis explicitly; label all operational values illustrative until independently sourced.

---

## 3. Work packages and non-negotiable acceptance gates

### WP0 — Literature anchor, source register and question freeze

Read (i) LiU/BSRC's publicly described research programme; (ii) the FLEXIGAS proposal as historical conceptual context, **not proof of a modern plant capability**; (iii) Mauky et al. (2017) for measured process-level flexibility; (iv) at least one peer-reviewed gas-storage/CHP dispatch or integrated biogas energy-systems study. Establish a dated bibliography and a claim-by-claim source ledger distinguishing **observation**, **mechanistic inference**, **assumption** and **unverified proposal**. Include known reactor- and facility-specific caveats. Draft the two-sentence research question above without implying BSRC involvement.

**Gate WP0:** all externally asserted quantities have a retrievable citation; flexible production and flexible utilization are distinctly defined.

### WP1 — Fixed-operation baseline: feasibility and data gate

1. Choose an individual-plant reference if adequately documented; otherwise freeze a **stylized** gas/CHP archetype with explicit parameter provenance. State the electrical rating, gas rate, chosen calorific-value basis, \(\eta_e\), \(\eta_{th}\) (if relevant), minimum operating load, nominal availability and credible headroom \(H\).
2. Fix one Swedish bidding zone, documented historical price window, market settlement resolution and time-zone handling. Validate the number, ordering, units and completeness of intervals; record download permissions.
3. Establish feasible **must-run** operation from the same gas supply and efficiency assumptions later used in WP2. If fuel would exceed rated output or if a minimum-load assumption contradicts baseline power, the configuration is invalid. Include nonnegative prices and negative prices without assuming the latter cannot occur.
4. Independently reproduce the baseline \(P_t=\eta_e U_t\), \(Q_t=\eta_{th}U_t\), gas consumption \(\sum U_t\Delta t_t\), electricity exported \(\sum P_t\Delta t_t\), and gross market revenue \(R_{0}=\sum_t \pi_tP_t\Delta t_t\) for the baseline.
5. Freeze the numerical and economic boundary before comparing cases. The baseline is **not** “net profit” if heat service, gas acquisition, start-up and storage cost are excluded.

**Gate WP1 — all must pass:** a citable input provenance table; valid operating headroom and thermodynamic units; date-time resolution checks; rights decision; a baseline figure independently recomputable from the frozen inputs; no flexibility solver code needed yet. If a real plant rating is unavailable, use an openly hypothetical archetype rather than inventing site performance.

### WP2 — Bounded gas-storage dispatch (LP or MILP, according to the implemented constraints)

Use Pyomo/HiGHS, reusing the solver-workflow and test discipline from PyNEXUS/district-heating work, not importing an unexamined model. For each interval enforce:

\[
S_{t+1}=S_t+\left(G_t-U_t-F_t-L_t\right)\Delta t_t,\qquad
0\le S_t\le S_{\max},
\]

\[
P_t=\eta_e U_t,\qquad 0\le P_t\le P_{\max},
\]

with any minimum stable load, ramp, unit commitment, downtime or gas-delivery constraints explicitly represented if used. Choose the correct formulation: an entirely linear continuous dispatch problem is **LP**; only use **MILP** terminology if discrete start/stop, minimum-load or other binary decisions genuinely exist. Do not add unsupported process dynamics merely to make the optimization look sophisticated.

**Primary clean comparison:** \(F_t=L_t=0\) for both cases, common \(G_t\), constant documented \(\eta_e\), and a **cyclic inventory constraint** \(S_T=S_0\). A nonzero minimum or terminal gas inventory may be selected but must be identical across cases. With these conditions, conservation implies identical total gas use. Without them, identical supplied gas does **not** imply identical gas use.

**Optional realism branches:** allow separately accounted flaring/loss, heat delivery requirements, standby load, or start/stop penalties. Such branches must not silently change the principal fuel-equivalence comparator. If a branch materially changes efficiency, output/energy may not remain equal even with equal gas use; report that explicitly.

**Gate WP2:** zero-residual gas balance within a declared numerical tolerance; bounded inventory and generation; identical end inventory; no model-created energy; solver status and termination captured; a transparent two-period hand calculation or exhaustive toy reference showing the optimizer's decision is correct. Never present an infeasible model as a valid zero-value result.

### WP3 — Value-of-flexibility, fair comparison and the CHP heat side

Compute gross electricity-market revenue difference \(\Delta R=R_{\mathrm{flex}}-R_{\mathrm{fixed}}\) for the same period and site archetype, across a **predeclared storage-capacity sweep** including \(S_{\max}=0\). Require the **same total gas production** and the **same start/end inventory**; when flaring or leakage is permitted, use the identity

\[
\sum_t U_t\Delta t_t = \sum_t G_t\Delta t_t - \sum_t F_t\Delta t_t - \sum_t L_t\Delta t_t -(S_T-S_0)
\]

and either enforce equal actual total utilization as a comparison condition or explicitly decompose the difference into **(a) dispatch/timing value** and **(b) changed flaring/loss/throughput value**. A revenue increase obtained by consuming additional fuel or avoiding flaring is not purely a storage-timing premium. Confirm common efficiency assumptions or state how they differ.

Report separately:

- Gross electricity revenue (EUR/window), difference (EUR/window), and normalized quantities where appropriate; no leap to annualized profitability from a short price window.
- Gas inventory trajectory, utilization, number of start/stop events (if modelled), storage size and CHP load factor. A zero-buffer flexible case should reproduce a feasible fixed-baseline dispatch (under the same fixed production, zero flaring and cyclic inventory assumptions).
- Useful CHP heat profile \(Q_t=\eta_{th}U_t\), and whether it meets a documented or explicitly assumed heat demand. If heat cannot be served, record deficits or curtailment; **do not call an electricity-revenue-maximizing schedule a feasible CHP optimum** while ignoring a binding heat obligation.
- Only a **separate, bounded economic screen** may include start-up/fuel/heat/storage CAPEX-OPEX assumptions. Without them, results are a *gross market-revenue opportunity*, not a complete cost-benefit finding.

**Gate WP3:** independently checked conservation and fuel/service comparability; zero-storage and constant-price sanity checks; gross-versus-net language clean; no claim of operational validation or total economic optimality.

### WP4 — Uncertainty and resilience (not synonymous with electricity-revenue gain)

Run a small, predeclared sensitivity matrix: price-window/volatility, storage capacity, CHP headroom, electrical efficiency, and at least one reduced-gas-supply or CHP-unavailability event. Define **one explicit service-security metric** for the disruption case, such as critical electrical demand served (MWh), unmet critical load (MWh) or hours supported, with an *explicitly hypothetical* demand and islanding/grid availability boundary. A biogas CHP selling into the wholesale market does not automatically improve local self-sufficiency or emergency supply without the relevant electrical connections and operating arrangements.

Keep two distinct outcomes: **revenue response** in normal market operation and **bounded modeled resilience/service response** under a specified disruption. Report where the results are driven by assumptions and where conclusions reverse under parameter variation.

**Gate WP4:** scenario table and sensitivity results reproducible; no extrapolation from a stylized one-plant case to “regional resilience” in actual Sweden.

### WP5 — Limitations, scientific interpretation and release gate

Write a concise technical report that distinguishes: (i) observed sector statistics; (ii) assumed plant and energy-conversion parameters; (iii) optimization outputs; (iv) analytical/numerical verification; (v) **absence of real plant operational validation**; and (vi) process-level biological flexibility documented in the literature but not modelled here. Include at least one negative/zero result if encountered, with no selective deletion. Separate gross-market opportunity, potential net economics and resilience claims. Disclose AI-assisted implementation once; retain code provenance and independent checks.

A reproducibility package should contain a README, versioned model/config files, dependency lock, tests, unit dictionary, source register, unambiguous data rights and retrieval instructions, scenario assumptions, results ledger and explicit limitations. Release to Zenodo/DOI only when rights and baseline audit pass; publish no restricted price data without permission.

### WP6 — Second pathway: optional, exactly one

Only after WP1–WP4 have passed, optionally choose **either** (a) grid-injection/biomethane upgrading as a separately priced and constrained utilization pathway, **or** (b) a literature-grounded process/feeding-response experiment with an appropriate reactor-specific model and identifiable kinetic assumptions. Neither is part of the promised MVP, and there is no obligation to implement either to support the application.

---

## 4. Analytical invariants and test matrix (implementation contract)

**Frozen two-interval toy oracle (illustrative, not a Swedish plant result):** Take two one-hour intervals with gas supply \(G=[0.6,0.6]\) MW\(_{gas}\), constant electrical efficiency \(\eta_e=0.4\), CHP electrical rating \(P_{\max}=0.4\) MW\(_e\), gas-buffer capacity \(S_{\max}=0.4\) MWh\(_{gas}\), initial/final inventory zero, no losses/flaring, and prices \(\pi=[50,200]\) EUR/MWh\(_e\). With no heat constraint or operating penalties, fixed utilization \(U=[0.6,0.6]\) MW\(_{gas}\) yields \(P=[0.24,0.24]\) MW\(_e\) and **EUR 60** gross revenue; feasible shifted utilization \(U=[0.2,1.0]\) MW\(_{gas}\) yields \(P=[0.08,0.4]\) MW\(_e\), storage sequence \(S=[0,0.4,0]\) MWh\(_{gas}\), and **EUR 84** gross revenue—a **EUR 24** timing uplift. A hand/exhaustive small-case check should confirm optimality under these toy assumptions. The example must never be presented as a forecast, field result, or net CHP value.

| Test | Setup | Required result / interpretation |
|---|---|---|
| A. Fuel-balance identity | Fixed \(G_t\); no loss/flaring; cyclic \(S_T=S_0\) | \(\sum U_t\Delta t_t=\sum G_t\Delta t_t\) within tolerance |
| B. Loss/flaring identity | Allow nonzero \(F_t,L_t\) | Difference in actual gas use exactly reconciles with flaring/loss and terminal inventory |
| C. Zero storage | \(S_{\max}=0\), \(F=L=0\) | Utilization follows input interval by interval; no fictitious shifting |
| D. No generation headroom | \(\eta_e\bar G=P_{\max}\) at all times; equal gas use | No upward shifting available without violating constraints |
| E. Flat prices, equal gas and fixed efficiency | \(\pi_t=\pi\) | Gross energy-sale revenue unchanged by pure shifting; if operating costs exist net may differ |
| F. Two-period exact reference | Two different prices, feasible buffer and headroom | Solver agrees with hand-calculated optimum and obeys every constraint |
| G. Time-series hygiene | 2026 15-min prices incl. DST transitions | Exactly one UTC timestamp per interval; total covered physical time and revenues consistent |
| H. Heat-feasibility branch | Define an hourly heat service requirement | Electricity-only optimum cannot silently violate heat-delivery requirement |
| I. Infeasible configuration | Too little gas, impossible service minimum or contradictory limits | Solver reports infeasible; results not presented as valid economic results |
| J. Accounting labels | Cost and revenues in EUR, energy in MWh and power in MW | Every plotted/table quantity carries unit and electricity/gas/heat basis |

**Tolerance policy:** Predeclare absolute/relative tolerances scaled to flow and horizon size, check solver feasibility independently, and report maximal absolute and normalized constraint residuals. Never set numerical tolerances after seeing a favorable result. Where efficiencies are constant, explicitly distinguish **gas-utilization equality** from **electrical-output equality**; if efficiency varies, use the appropriate output comparison.

---

## 5. Honesty and application boundaries

- No BSRC/LiU affiliation, endorsement, supervision or contribution claimed.
- No actual Swedish individual-plant operation claimed unless a specific public dataset supports it; otherwise the case is **stylized, source-informed and parameter-assumed**.
- No hourly digester response inferred from annual Swedish production data. No claim that biology cannot respond quickly; Mauky et al. is a **plant-specific counterexample**, not universal digester performance.
- Never say annual Swedish electricity/heat categories establish electrical CHP capacity, headroom, efficiency, hourly production or local resilience.
- Never claim that normal market-price arbitrage establishes **net profitability, carbon reductions or local resilience**. Each requires its own boundary and evidence.
- Never treat model-vs-hand-calculation or cross-solver checks as physical **validation**. Refer to them as verification/consistency checks.
- Do not call an LP a MILP unless actual integer decisions exist.
- Distinguish model-derived simulation outputs from observations and link every headline number to a frozen configuration, data version and script or test.
- AI-assisted coding disclosed once in each major final artifact, including the research report, without hiding original scientific responsibility.
- **Linköping CV/cover letter remain separate**: do not describe BiogasFlex as completed or add quantitative portfolio results before WP1–WP3 actually produce tested results. This project is not a precondition for submitting the PhD application by 2026-12-08.

---

## 6. Version history, resolved review issues, and unresolved decisions

| Version | Change | Status |
|---|---|---|
| v0.1 | Initial storage-utilization concept; incorrectly dismissed intraday digestion flexibility | Superseded |
| v0.2 | Acknowledged demand-oriented biological flexibility; selected storage-buffered dispatch for practical data/toolkit reasons; introduced uncertainty/resilience pathway | Retained |
| v0.3 | Added CHP output headroom; recorded 2025 Swedish aggregate statistics | Retained with corrections |
| **v0.4** | Corrected gas-utilization equality claim with loss/flaring/terminal inventory accounting; fixed WP5/WP6 references; clarified hypothetical plant and sector statistics; obtained official 2025 source and journal abstract; added testable gates, heat-service and value boundaries | **Current pre-code plan** |

**Resolved in v0.4:**

1. The official 2025 national values are directly retrievable from Energimyndigheten; secondary news verification is no longer needed as the primary anchor.
2. The published Mauky et al. abstract says **up to ±50%** for intraday production relative to the full-scale study's average. Retire v0.3's unqualified “more than 50% above/below” as the general headline; keep any distinct dissertation quotation only if exact context and operating case are documented separately.
3. Earlier v0.3 cross-references incorrectly called WP5 the optional biological pathway and WP4 the write-up. **WP5 is the write-up; WP6 is the optional pathway.**
4. Equal gas supplied plus cyclic inventory alone guarantees equal gas **used only if total flaring/loss is also equivalent**. WP2/WP3 now make this explicit.
5. National aggregate data alone cannot establish a named plant's electrical rating or actual headroom; a properly labelled stylized archetype is acceptable if such data cannot be secured.

**Open before implementation:**

- Select the reference plant or transparently stylized archetype and source/sensitivity ranges. The default is **not yet selected**.
- Select the market bidding zone and exact price window; confirm underlying price data reuse rights and release method. **No specific price dataset has yet been downloaded or licensed for this project.**
- Decide the MVP's heat-side treatment: electricity-only screening with an explicit limitation or a minimum heat-service constraint. Never leave it implicit.
- Decide whether binary on/off or minimum-load constraints are genuinely necessary before calling the solver MILP.
- Verify any new numerical values against source definitions and the exact data/solver configuration rather than carrying them forward from other repositories or earlier drafts.

---

## 7. WP1 start card — next operational action

**No coding of flexible dispatch until this card passes:**

1. Write a `sources.csv`/source ledger identifying the official Swedish 2025 biogas source, definition of each relevant energy category, Mauky et al., selected plant archetype parameters, day-ahead price source, and licensing decision.
2. Obtain a citable plant size/rating if possible; if not, choose and prominently label a stylized CHP capacity, fixed gas rate and minimum heat service, with provenance/sensitivity bounds. **Prove headroom mathematically** and confirm the baseline is feasible.
3. Select a single ENTSO-E time window/bidding zone, verify all timestamps, intervals, units and market data rights; record retrieval method and ensure a public reproduction path without unauthorized redistribution.
4. Reproduce **one independently checked baseline gross-revenue figure** from fixed gas, efficiency, CHP rating and selected prices; report gas input, electricity, useful heat treatment and reconciliation residuals.
5. Obtain a skeptical pass on that first WP1 baseline, then proceed to bounded storage optimization.

**Project freeze rule:** Once this v0.4 planning specification is accepted, do not keep rewriting the master plan for minor stylistic issues. New material findings should be logged in a dated issues/decision register and changed only through versioned requirements or tests. The immediate deliverable is a **working, auditable WP1 baseline**, not another polished plan.

---

## References (verified or explicitly scoped)

1. Energimyndigheten (2026-10-01), *Ökad biogasproduktion i Sverige under 2025*: <https://www.energimyndigheten.se/nyhetsarkiv/2026/okad-biogasproduktion-i-sverige-under-2025/>. **Primary official annual figures; not plant-level hourly evidence.**
2. Mauky, E. et al. (2017), “Demand-driven biogas production by flexible feeding in full-scale – Process stability and flexibility potentials,” *Anaerobe*, 46, 86–95. <https://doi.org/10.1016/j.anaerobe.2017.03.010>. **Full-scale experimental evidence under studied conditions, not a universal digester bound.**
3. BSRC, public research overview: <https://liu.se/en/research/biogas-research-center>. **Context, not endorsement.**
4. FLEXIGAS (Hanze University of Applied Sciences, 2012), historical proposal: <https://research.hanze.nl/en/publications/flexigas-theme-a-wpa2-phd-research-proposal-researching-and-model/>. **Conceptual reference, not experimental validation.**
5. SCB EN0124, production of biogas and digestate: <https://www.scb.se/en0124-en>. **Sector statistical context; definitions require checking for reuse.**
6. Nord Pool (2025-10-01), “15 Minute MTU Implemented in SDAC”: <https://www.nordpoolgroup.com/en/message-center-container/newsroom/exchange-message-list/2025/q4/15-minute-mtu-in-sdac-was-implemented/>.
7. ENTSO-E Transparency Platform: <https://transparency.entsoe.eu/> and [terms and conditions](https://transparency.entsoe.eu/content/static_content/download?path=%2FStatic+content%2Fterms+and+conditions%2F230309_ENTSOE_Transparency_Terms_Conditions_MC_APPROVED.pdf). **Check primary-owner reuse restrictions, not just platform access.**
