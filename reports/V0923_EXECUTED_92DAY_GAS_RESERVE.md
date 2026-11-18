# BiogasFlex v0.9.23 — Executed 92-day lower-gas reserve experiment

**Research status:** Independently audited mathematical improvement under an uncalibrated **synthetic** CHP gas/heat model. The implementation is in stacked draft PR #29; neither this experiment nor the software constitutes real CHP field qualification, actual electricity-market earnings or a completed v1.0 industrial release.

**Source-verified full reproduction:** [GitHub Actions run 44203856872](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44203856872). All 8 jobs PASS: 3 operating systems × 2 Python versions, a two-day historical-source smoke audit, and the full 92-day independent physical, witness and economic audit.

**Frozen data source:** Open Power System Data 2020-10-06 60-minute original, Swedish SE3 historical 2019 data. Original publisher SHA-256: 6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8. The seven-day-lagged price is a constructed persistence forecast baseline, not an original as-of-market-gate provider forecast; archived regional electric-load forecast revisions do not have proven issue-time vintages. Biogas inflow and heat load are **not observed**; their temporal deviations derive from unchanged uncalibrated synthetic formulas.

## Predeclared protected-controller difference

Both policies use exactly the same nominal or eight-training-day robust commitment MILP and identical pre-reveal frozen CHP on/start/stop decisions as v0.9.22. The reserve-aware version adds an opt-in linear feasibility branch sharing current-hour terminal gas inventory and generator power. It must be possible to operate the **next** source hour under a constant minimum hypothetical gas arrival of **0.78 MW_LHV**, subject to the same fuel-stock conservation, 0–1.5 MWh_LHV capacity, ON/OFF limits, and inherited 0.8 MW_e/hour consecutive-ON ramp.

The lower bound 0.78 MW_LHV comes from the clipping floor of the **synthetic** gas proxy, not site field measurements or a vendor supply contract. A one-hour existential low-gas witness is not a robust invariant set for arbitrary future inputs, high-gas buffer overflow, actual plant pressure/engine dynamics or unknown real-time sensor readings. No future realized price/gas/heat is supplied to the current-hour optimizer.

## Full source-backed benchmark

| Predeclared metric | Original causal controller | Reserve-aware controller |
|---|---:|---:|
| Chronologically eligible and evaluated source days | 92 | 92 |
| Six-hour modeled dispatch feasible | **63** | **92** |
| Six-hour modeled dispatch infeasible | **29** | **0** |
| Feasible with unmatched end fuel inventory | **5** | **6** |
| Feasible AND matched starting/ending fuel inventory | **58** | **86** |

**29 previously infeasible source days were rescued**, with zero newly infeasible days in the finite synthetic study. The nominal and robust binary commitments remain identical for **92/92** days. These numbers therefore quantify the added **continuous reserve guard**, not a new advantage of source-paired first-stage maximin optimization.

The independently implemented source/physical-audit stack passed on the complete 92-day test twice, once for each controller. Separately it reconstructed **920** current-to-next-hour bound-witness sequences (92 days × 2 otherwise identical binary policies × 5 next-hour checks), checking shared current-hour stock/power, forward gas balances, buffer bounds, frozen CHP commitment and electric ramps.

## Economics: no assignment of earnings to infeasible service

Only **57 held-out days** meet *both* original and protected six-hour service obligations with cyclic gas inventories matched to the initial stock. For only those 57 strict comparisons, protected-minus-original modeled operating contribution averages:

**−EUR 0.009963723024618662 per hypothetical six-hour period.**

This is a small negative modeled difference, not actual market settlement, a confidence interval, annual savings or proof of free safety. The 29 original failures have no legitimate comparable earnings, and all six protected terminal-inventory mismatches remain explicitly excluded from matched-service economics. The simultaneous identity of nominal and robust first stages remains a negative strategy-discrimination result.

## Scientific interpretation and release boundary

This is evidence that a one-hour **information-causal synthetic lower-gas viability witness** resolves the previous stock-depletion/ramp feasibility failure for the source-selected benchmark, without changing engine ramp, fuel conservation, heat delivery or gas inventory physics. It is NOT evidence of reliable operation on a real engine, nor universal robust feasibility for high- and low-gas mixed futures; it also does not resolve all exact terminal-stock end conditions.

Field qualification still lacks independently measured biogas composition/LHV, pressure-buffer calibration, startup and partial-load generator maps, heat delivery and real export-award data, issue-time forecasts and separate site-forecast holdouts.

**Next software milestone:** v0.9.24 — actual service-boundary modelling for declared **hypothetical** accepted electricity awards, with exact export MWh accounting and explicit infeasible award cases. Then implement preregistered scenario sensitivity, independent physics/units verification and reproducible v1.0 packaging according to [the scientific v1.0 release gates](../docs/V1_0_SCIENTIFIC_RELEASE_GATES.md). Industrial field-qualified v1.0 remains blocked pending genuine equipment data.
