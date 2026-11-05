# BiogasFlex v0.8 — Model boundary and scientific claims

## Release identity

- Local research-development candidate, **v0.8.0**; retains the v0.7 heat-aware economic LP unchanged.
- 216 scenario comparisons spanning **three independently selected, complete, historical day-ahead price windows** and five separate, entirely hypothetical service-security tests.
- Scenario grid internally declared in `scenarios/registry.json` and mirrored for reading in `scenarios/registry.yaml`, before executing the v0.8 optimization runs. **Not externally preregistered.** `registry.json` is the machine-readable execution authority; JSON file SHA-256 accompanies the results.

## Primary market-price evidence

Svenska kraftnät public historical SE3 day-ahead prices: the **first Swedish civil day** of January, April, July, October 2020 was specified, without inspecting optimization uplifts. The July 1 extract did not pass completeness checks (24 returned records span 25 hours, with a missing observation), and was **rejected without interpolation or replacement**. January 1, April 1 and October 1 have complete 24-record sequences with one-hour UTC spacing.

Sources: Svenska kraftnät open-data portal, resource ID `cf392ef3-7345-4e98-970e-83088c185570`; https://data.svk.se/dataset/market_data_day_ahead_area_prices ; data under CC BY 4.0. Columns are provider timestamp converted to explicit UTC offset, zone, recorded prices and EUR/MWh units. No price smoothing or editing. Market-data export does not establish any realized merchant sales.

**No probabilistic interpretation:** Three dates cannot support claims about an annual price distribution, confidence intervals, future prices, Swedish market-wide value, or temporal stability over years. Scenarios are conditional sensitivity, not a sample of real plant operation.

## Plant reference and parameter inheritance

- Source-backed annual reference from SLU master's thesis (Åberg, 2024), reporting Lövsta 2022 generator rating **499 kW_e**, annual electricity **3,002.6 MWh_e**, annual heat production **2,939.5 MWh_th**. These are not an hour-by-hour operational trace.
- The model's gas input **0.8569063926940638 MW_LHV** was *inferred*, not measured, using the documented annual electricity and a hypothetical electric efficiency of 40%.
- The model's thermal efficiency **0.3915939519083461** was likewise fitted to the annual heat/electric output ratio; it is not a plant-calibrated heat-transfer efficiency or measured usable heat.
- Constant gas supply and heat demand, 2020 price conditions applied to 2022 mean production, CHP modulating with perfect foresight, the gas-buffer stock, ability to reject heat, backup heat capacity and marginal backup heat cost are **counterfactual assumptions**.
- At each market scenario: gas energy supplied and heat service demand are identical in fixed and optimized schedules; gas end inventory equals initial. The comparison therefore does **not** produce fuel out of stored inventory.

## Scenario grid

Across each of three observed windows, 72 hypothetical configurations vary:

| Parameter | Predeclared values | Interpretation |
|---|---|---|
| Gas storage | 0, 0.25, 1.0 MWh_LHV | Physical vessel not sized |
| Hourly heat demand | 0.75 or 1.00 × annual-average *heat production* | Not observed demand |
| Marginal backup heat cost | €20 or €80/MWh_th | Stylized price, not invoice |
| Electric efficiency | 0.38, 0.40 or 0.42 LHV | Assumed; gas energy supply kept fixed |
| Electric CHP rating | 499 kW reference or 1.05 × assumed mean electric output | Second is hypothetical reduced CHP rating, **not observed Lövsta hardware** |

The dependent quantity for economics is **incremental scenario contribution**, defined as gross spot-equivalent electricity value minus assumed marginal backup heat cost, heat-rejection penalty and CHP electric-variable cost, all compared to the fixed schedule. It is **not** project cash flow, NPV, energy system self-sufficiency, market forecast or a plant profit estimate. There are no modeled capital costs, CHP start/ramp/part-load curves, gas vessel engineering, control dynamics, or export limits.

**Critical interpretive point:** The optimized economic contribution cannot be materially below the feasible fixed schedule when the fixed schedule belongs to the LP feasible set. Thus nonnegative uplift across all solved cases is a structural mathematical result, **not** evidence that storage never has a negative overall value. Zero cases must be retained rather than omitted.

## Separate critical-service-disruption LP

The emergency LP does **not** inherit cyclic gas inventory from market operation. It uses an explicitly **precharged gas store**, no gas inflow for three hours, no grid import, no external backup heat, critical electric load **0.12 MW_e** and critical heat load **0.10 MW_th**, with a 499 kW_e assumed available CHP and an assumed 40% electric and 39.1594% thermal conversion efficiency. It minimizes the sum of hypothetical hourly electricity and heat deficits using arbitrarily declared weight ratio **10:1** (electricity:heat) while accounting for simultaneous co-produced electricity and heat.

Five predeclared conditions: zero buffer, precharged 0.3 MWh_LHV, precharged 0.6 MWh_LHV, same 0.6 without hypothetical island-capable controls, and same 0.6 when CHP is unavailable. Electricity may only serve critical islanded load when **both** CHP availability and island-capable operation are assumed. These assumptions are not observed, and no black-start, synchronization, protection, grid-forming control, islanding switchgear or operating permit is demonstrated. No auxiliary generator, heat pump or battery is included.

An emergency service fraction is **not a measurement of regional resilience**. The baseline and storage cases differ in initial gas inventory, so they are not equal-inventory economic dispatch comparisons. Initial inventory is supplied externally and the cost of filling that inventory is excluded. No recovery/startup transients or recovery time is modeled. Sum of service energy is the metric; continuity of service in each hour is not guaranteed, and the LP's hourly schedule need not be unique.

## Verification, reproducibility and independence

- `python -m unittest discover -s tests -v` retains v0.5–v0.7 regressions and adds v0.8 evidence, scenario, emergency, and falsification tests.
- `python scripts/run_v08_study.py --plots`: regenerates 216 market case JSONs, the full scenario CSV, five emergency case JSONs, summary, and figures entirely offline.
- `python scripts/independent_v08_audit.py`: standard-library-only numerical checker reads the saved results, source CSV and registry without importing the LP solver. It detects altered service, inventories, economic arithmetic, solver status, and source registry checksums.
- This is an internal/AI-assisted numerical audit, **not independent human peer review**. No real plant-level operational validation is claimed.

## Excluded claims

No Swedish policy incentive is simulated or claimed to be enacted. No biogas-process/digester feeding control, life-cycle analysis, biomethane upgrading, physical gas inventory conversion to Nm³, region-level supply independence, regional criticality ranking, epidemiological or other statistical probability statements, real-world outage response, black-start capability, or integrated economic profitability is established.
