# BiogasFlex v0.9.24 — Independently executed 92-day hypothetical electricity-award study

**Scientific status:** Audited research-software milestone. It is **not** an actual day-ahead bid execution, a measured CHP electrical-export campaign, a complete market-contract optimization or a reliable real-plant dispatch qualification.

**Reproduction:** [GitHub Actions 44209007420](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44209007420): **8/8 jobs passed**, with 3 operating systems × 2 Python versions, complete frozen-publisher-source two-day smoke and full 92-day independent market-award/physical/negative-case audits. The inherited v0.9.21, v0.9.22 and v0.9.23 workflow suites also passed on the validated source commit.

**Data provenance:** Original Open Power System Data 2020-10-06 hourly SE3 source, publisher original SHA-256 `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`. The historical electrical-load forecast-error pairs and regional prices are genuine dataset fields, but the original price forecasting baseline is a constructed 7-day historical persistence comparator, not an authentic archived as-of-market-gate vendor forecast. Gas production and site heat trajectories are **uncalibrated synthetic functions** of those historical errors, not biogas facility measurements. No actual accepted CHP export awards or grid meter readings exist in the source.

## Preregistered experiment and contract model

The target covers all 92 UTC-complete 2019-10-01 through 2019-12-31 source days. Each day has a complete earlier calendar-week price source. The nominal and paired maximin CHP first-stage binary commitments are frozen before generating the target-day synthetic gas and heat. Their hashes remain **identical on all 92 days**. The same fixed hypothetical 24-quarter-hour export energy award is then used under (a) award-only causal control and (b) award-constrained causal control with the v0.9.23 next-hour low-gas feasibility witness.

For each quarter-hour t, a **hard physical/model equality** imposes eta_e × gas_burn_MW_LHV × 0.25h = awarded_export_MWh_e, using eta_e=0.4. The same equalities are imposed on every next-hour reserve witness. On infeasibility, **no awarded energy forgiveness, hidden electricity imports, ramp relaxation, fuel buffer overfill, generic disposal device or estimated sales proceeds** are introduced. The full contract is declared **not delivered**, even when a subset of quarter-hour physical outputs was feasible.

Three award profiles were fixed **before** seeing any held-out results:

| Ex-ante hypothetical constant export award | Total 6-hour contract MWh_e | Rationale |
|---|---:|---|
| 0.090 MWh_e per quarter-hour | 2.16 | Six-hour low-synthetic-gas budget: (0.78 MW_LHV + 0.75 MWh_LHV / 6 h) exceeds 0.9 MW_LHV consumption |
| 0.100 MWh_e per quarter-hour | 2.40 | Nominal 1 MW_LHV gas consumption |
| 0.150 MWh_e per quarter-hour | 3.60 | Deliberate first-half-quarter ramp incompatibility |

**These awards are manufactured research inputs, not market offers, bids, accepted trades or invoices.** The parent first-stage MILPs are the pre-existing unawarded commitment policies: v0.9.24 tests the ability of their already-frozen commitments to meet newly imposed exogenous awards. A genuinely jointly optimized **contract-aware first-stage commitment MILP** with full terminal service is a separate modeling extension, not demonstrated here.

## Complete 92-day results

| Hypothetical awarded MWh_e / 15 min | Award only feasible | Award + gas reserve feasible | Six-hour feasible AND cyclic-terminal-gas-matched |
|---|---:|---:|---:|
| 0.090 | **61 / 92** | **61 / 92** | **0** in either controller |
| 0.100 | **88 / 92** | **83 / 92** | **0** in either controller |
| 0.150 | **0 / 92** | **0 / 92** | **0** in either controller |

Each number is per first-stage policy; because nominal and joint binary decisions are identical for all 92 days, their results are identical. The exporter measured by software is **eta_e × fuel_use × time**, not physical net power at a real grid-metering point.

**No matched-service earnings comparison is valid:** all physically completed fixed-award paths end with gas-buffer inventory different from their starting state. The study has zero six-hour cases satisfying both exact awarded export and exact cyclic terminal gas inventory for any profile. Merely selling different amounts of terminal stored fuel would bias an economic comparison. No missing-day revenue, annual profit, contract default penalty or corrective electricity purchases have been fabricated.

This is a materially different and stricter question than v0.9.23, which obtained 92/92 modeled feasible six-hour dispatches **without** hard interval-specific export awards. With fixed 15-minute energy obligations, the CHP burn is already determined and continuous dispatch loses its freedom to reduce fuel consumption or ramp more slowly.

## Independent infeasibility taxonomy

In addition to independently verifying all exact award meters and gas/heat/ramp states, a standalone standard-library arithmetic auditor reconstructed each first failed source hour directly from the **locked award**, previous gas stock and power, current available synthetic gas and heat, and fixed binary CHP commitment. It then checked the predefined next-hour minimum-gas witness and future **nominal** forecast constraints separately. The taxonomies below count **source days** (each is independently repeated for nominal and joint policies).

| Award profile and control mode | Failed source days | Observed current-hour physical conflict | Next-hour synthetic gas reserve rejection | Future nominal forecast constraint infeasibility |
|---|---:|---:|---:|---:|
| 0.090 award-only | 31 | 4 | 0 | 27 |
| 0.090 award + reserve | 31 | 4 | 0 | 27 |
| 0.100 award-only | 4 | 4 | 0 | 0 |
| 0.100 award + reserve | 9 | 3 | 6 | 0 |
| 0.150 award-only | 92 | 92 | 0 | 0 |
| 0.150 award + reserve | 92 | 92 | 0 | 0 |

**Interpretation:**

- For the 0.090 profile, most of the failed *forecast-horizon LPs* do not prove that the newly observed operating hour itself is impossible. They reflect constraints predicted under the future **nominal source-hour gas assumptions**. The 2019 actual future gas is deliberately unavailable to the controller at the earlier forecast gate. Do not misclassify the 27 forecast-only failures as observed future plant faults.
- For the 0.100 profile, the added low-synthetic-gas reserve condition causes earlier or additional award rejection. This is an intentionally more conservative requirement. It cannot magically produce gas or maintain revenue while honoring a rigid power award.
- The 0.150 profile fails as designed: the first-quarter required 0.6 MW_e output exceeds the allowed midpoint ramp from initial 0.4 MW_e. The impossible contract is **not** counted as zero-price delivered generation.

The classifier explicitly checks that every solver-reported failed policy replay is explained by a current observed-hour conflict, a required next-hour reserve infeasibility, or a future nominal forecast constraint. If none apply, it raises an audit failure rather than inventing a reason. It passed on all **518** failed policy-replay instances across all profile/mode/commitment combinations.

## Independent audit coverage

The complete original-source audit reconstructed:

- **15,584** chronological executed quarter-hour physical export records, checking hard awarded MWh equality, bounded CHP fuel, modeled electricity meter, heat service, gas stock, and switching.
- **6,592** next-hour reserve-witness quarters, checking exactly the same previously locked contractual MWh, source-independent synthetic minimum gas floor, gas stock and generator ramp.
- All pre-reveal SHA-256 award and commitment fingerprints, 92-day historical source eligibility, false historical market-vintage claims, and explicit infeasible-service accounting.
- All 518 failed policy-replay cases independently classified, with the reason and source hour archived in the CI diagnostic artifact.

The source/physical auditors do not import BiogasFlex optimizer code. SciPy/HiGHS remains the backend of the original LP; the new failure taxonomy uses direct arithmetic and no optimizer. This is not proof of MILP global optimality beyond the original solver status, nor real equipment validation.

## v1.0 gate and remaining requirements

The v0.9.24 research gate **passes** for exact *hypothetical award equality*, explicit service failure, source chronology and independent mathematical auditing. It does **not** pass actual market contract qualification or matched-terminal-service economics.

The most important next scientific work is to specify **pre-reveal contract feasibility and terminal gas inventory accounting** in the first-stage design, including a physically evidenced upper/lower gas management envelope. An accepted export contract forces gas burn; if biogas arrives in surplus, storage can fill unless a justified actual physical outlet exists. Forecast-only infeasibilities must be distinguished from realised current-hour safety issues. No arbitrary venting, electrical import or imaginary contract penalties are acceptable repairs.

Further research-software v1.0 gates cover preregistered uncertainty/sensitivity, independently sourced equipment parameters and units, matched-service comparisons, package/wheel reproducibility, citation/license checks and external scientific review. Actual field qualification additionally requires authorized gas composition/flow/pressure, thermal delivery, net power metering, startup/ramp and market award/forecast issuance evidence.

See [the parent gate plan](../docs/V1_0_SCIENTIFIC_RELEASE_GATES.md), [pre-registered award protocol](../docs/V0924_CAUSAL_HARD_AWARD_PROTOCOL.md), and [v1.0 master issue #30](https://github.com/Open-Energy-Methods/biogasflex/issues/30).

**Release decision:** Research implementation is scientifically auditable as a *negative feasibility/market-service benchmark*. Keep v0.9.24 draft until inherited PRs #28/#29 are integrated and release qualification has been considered. Do not present 92-day hypothetical award results as real market reliability or earnings.
