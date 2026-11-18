# BiogasFlex v0.9.25 — Executed source-paired physical uncertainty envelope

**Research status:** source-hash-verified 92-day synthetic CHP physical-sensitivity experiment, with **independently verified** all-source-day mathematical outcomes. These are **not** observed biogas plant forecasts, physical equipment certification, 15-minute measured gas/heat records, market-accepted bids, or actual dispatch economic performance.

**Evidence:** [GitHub Actions run 44373327050](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44373327050), complete machine-readable [92-day/54-cell output plus independent audit certificate](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44373327050/artifacts/14460770850). The full original-publisher source independently audited job **PASSED** and reconstructed every preregistered result. Cross-platform suite completion is a separate release-integration gate; consult live Actions before claiming all jobs passed.

Original Open Power System Data 2020-10-06 publisher original SHA-256: `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`. The same original real SE3 historical regional electricity price/load forecast errors are preserved as hourly paired source sequences; gas supply and site heat are **uncalibrated synthetic functions** of those errors and NOT source-measured gas or heat. All 92 eligible 2019-10-01–2019-12-31 held-out dates and 271 pre-October source-training dates are retained.

## Exact fixed-award physical feasibility results

Source-mapped original gas/heat shock multiplier **1.0**, heat-backup rating **0.20 MW_th**, static all-ON CHP and exactly the predeclared six-hour hypothetical awarded MWh_e/15-min:

| Buffer MWh_LHV | 0.090 MWh_e/15 min | 0.100 MWh_e/15 min | 0.150 MWh_e/15 min |
|---|---:|---:|---:|
| **0.75** | **2/92** | **41/92** | **0/92** |
| **1.50** | **61/92** | **88/92** | **0/92** |
| **3.00** | **92/92** | **91/92** | **0/92** |

All table entries are **retrospective feasibility under already specified synthetic gas-arrival paths**. They do NOT indicate success rates of the forecast-time controller: the entire future path was used only for independent scoring, not for making a causal dispatch decision.

The static all-ON commitment matches the independently audited **v0.9.24 pre-reveal nominal commitment on 92/92** test days. At the original 1.5 MWh storage/0.20 MW_th backup model configuration, the new independent closed-form physical check recovers the same full-service feasible denominators (61/92, 88/92 and 0/92) as the original v0.9.24 award-only LP, with **zero** old audited accepted service contradictions.

### Why each failure occurs in the frozen physical model

- **0.090 MWh award (fuel burn 0.90 MW_LHV):** at 0.75 MWh_LHV storage, **90** of 92 original-shock days breach the gas-buffer ceiling; at 1.50 MWh_LHV, **31** overflow; 3.00 MWh_LHV prevents overflow on all 92 historical synthetic source paths. Bigger physical storage prevents a modelled gas *surplus* violation, not a shortage or guaranteed market earnings.
- **0.100 MWh award (fuel burn 1.00 MW_LHV):** 0.75 MWh_LHV storage results in **50** upper-stock breaches and **1** lower-stock shortage (constraint families are not exclusive); at 1.50 MWh_LHV, **3** upper and **1** lower violation; at 3.00 MWh_LHV, **one** lower-fuel-stock deficit remains. The system cannot fix unavailable fuel solely by increasing the container's upper capacity.
- **0.150 MWh award (fuel burn 1.50 MW_LHV):** **all 92** source-day cases violate the declared generator's **first half-interval electrical ramp**; increasing storage cannot change the electromechanical ramp boundary. All also eventually violate lower fuel inventory at the declared six-hour inputs. None is a valid completed contract.
- **Cyclic terminal inventory:** among the above fully feasible original-shock cases, **0** also end at the initial 0.75 MWh_LHV gas inventory. A zero ending difference is not a mathematically likely or universal requirement if fixed fuel burn and time-varying gas inflow are independent of the contract award. There is no modeled biogas injection, gas vent, genuine alternative fuel sink or import/award slack to force equality.

The complete 54-cell matrix also tests **zero thermal backup**, **zero paired-source deviations**, and **1.5× paired synthetic gas-and-heat deviations**; these are explicitly modeled sensitivity interventions, not additional real gas/heat measurements. The full matrix and per-constraint count is preserved as a machine-readable CI artifact rather than selecting favorable grid points.

## Source-paired forecast uncertainty: keep quantities distinct

The source-backed regional **electricity** price-persistence-error versus regional electric-load forecast-error correlation for the six-hour 08:00–14:00 UTC window was:

| Source partition | Complete UTC source days | Empirical regional electricity-error correlation |
|---|---:|---:|
| Before 2019-10-01 (training) | **271** | **−0.0285889039** |
| Oct–Dec 2019 (heldout, descriptive only) | **92** | **+0.2079326362** |

These are neither biogas production–heat demand correlations nor calibrated coefficients for CHP site gas/heat forecasts. Their difference is a reason to avoid assuming identical unconditional multi-variable uncertainty across periods; it is not a distribution-free statistical claim.

The **training-only seven-calendar-day moving-block bootstrap** had **253 eligible starting weeks**, **200** repetitions per physical grid cell, and **92 source-training days per replicate**. It preserves within-source-day time order and seven-day serial source dependencies and reports only *descriptive* p05/p95 training feasibility fractions. For the unscaled paired synthetic shock and 0.20 MW_th thermal backup:

| Buffer / award | Training days feasible | Descriptive training bootstrap p05–p95 |
|---|---:|---:|
| 1.50 MWh_LHV / 0.090 MWh_e | 157/271 | 0.4674–0.6848 |
| 1.50 MWh_LHV / 0.100 MWh_e | 235/271 | 0.7935–0.9348 |
| 3.00 MWh_LHV / 0.090 MWh_e | 271/271 | 1.0000–1.0000 |
| 3.00 MWh_LHV / 0.100 MWh_e | 255/271 | 0.8913–0.9891 |

**These are not confidence intervals for field reliability**, and the observed heldout rates must not be used to recalibrate or change the registered grid after the fact. The bootstrap resamples whole source-day blocks rather than independent regional-error hours or separately sampled channels.

## Exact conditional gas-support certificate findings

The separate **54** hypothetical interval cases encompass 3 buffer capacities × 2 heat-backup ratings × 3 awards × 3 gas-support bands. The independent arithmetic auditor verified **14/54** instances in which *every* arrival path bounded by the declared interval can satisfy the **fixed** all-ON award, generator rating, first ramp, backup heat and buffer limits.

**Only one** of the 54 cases certifies feasibility under the entire **synthetic proxy clipping** gas range **[0.78, 1.22] MW_LHV** without shortening the interval: **3.00 MWh_LHV buffer**, **0.20 MW_th backup**, **0.090 MWh_e per 15-minute award**. This is a *conditional property of the synthetic model* if gas stays inside the assumed range. It does not guarantee exact cyclic end fuel inventory, gas holder pressure safety, ramp physics of a specific engine, real site heat or the existence of an accepted market bid.

Several other certificates pass only with arbitrarily **narrower** gas ranges (0.90–1.10 MW_LHV) or **degenerate nominal gas** (1.00 MW_LHV). These are *assumptions to test*, not learned forecast bounds. With gas uncertainty spanning nonzero width and no real fuel-balancing actuator, all-path exact terminal-stock equality cannot be achieved under a single fixed fuel-burn contract. A constant nominal 1.0 MW_LHV gas case with 0.100 MWh_e/quarter achieves exact terminal equality, but **removing uncertainty by assumption is not uncertainty mitigation**.

## What the independent audit establishes

[Complete source and independent audit run](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44373327050) verified:

- **54 preregistered** full training/holdout factorial cells, including **19,602** separate source-day/cell physical path evaluations.
- **54 analytic** exact worst-upper/worst-lower stock, startup ramp and bounded heat-service certificates; **14** conditionally pass.
- **271** source-training days and all **92** eligible historic heldout days; source training normalizers and date split unchanged.
- All trained **253** complete moving-week starting points, **200** reproducible training-only seven-day bootstrap replicates per cell; independent re-creation of the p05/p95 values.
- Original unchanged v0.9.24 full contract award/service/source SHA, gas/ramp/thermal and failure accounting.
- Explicit failure when field calibration or market settlement provenance is falsely asserted.

This provides independently auditable *negative and positive finite synthetic research findings*. It does **not** certify predictive accuracy on a real biogas CHP plant, price-forecast vintages, actual firm grid export, market settlement, or independently optimal CHP contract bidding.

## v1.0 scientific release implications

**A4 mathematical research protocol/results: PASS (complete historical independent audit).** The software merge and all OS/Python CI checks are separate release gates until verified. Industrial field qualification is still blocked.

Most important remaining research dependency is **physically grounded terminal stock service and feasible contract-aware first-stage bidding under bounded gas arrivals**, rather than increasing storage until the studied synthetic trajectory happens to fit. Further A5–A8 work includes equipment-unit traceability, matched-service economic comparisons, cross-platform package wheel release audit, external scientific review and unambiguous source/field disclaimers.

Canonical methods: [v0.9.25 preregistered protocol](../docs/V0925_PREREGISTERED_PHYSICAL_ENVELOPE_PROTOCOL.md), [v1.0 scientific release gates](../docs/V1_0_SCIENTIFIC_RELEASE_GATES.md), [master v1.0 tracker #30](https://github.com/Open-Energy-Methods/biogasflex/issues/30).
