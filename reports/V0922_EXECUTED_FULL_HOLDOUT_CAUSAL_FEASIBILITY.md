# BiogasFlex v0.9.22 — Executed 92-day causal feasibility audit

**Status:** Executed source-backed mathematical benchmark and independent current-hour feasibility diagnosis. This is a research candidate, not a released operational CHP controller, a biogas-engine calibration, or evidence of actual market trading.

**Execution:** 2026-11-17. [Original frozen OPSD full holdout and independent audit, GitHub Actions 44186505921](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44186505921).

**Source:** Open Power System Data frozen 2020-10-06 release, SE3 2019 hourly series; original publisher-verified SHA-256: 6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8. Regional electrical-load forecast revisions are not individually publication-vintage authenticated. Seven-day price persistence is a constructed historical baseline, not an archived vendor price forecast.

**Reproduction:** causal controller in src/biogasflex/causal_v0922.py; independent main mathematical auditor in scripts/audit_v0922_causal_independent.py; separate current-hour independent feasibility LP in scripts/diagnose_v0922_feasibility.py; methods in docs/V0922_CAUSAL_HOURLY_REPLAY_PROTOCOL.md.

## 1. Frozen experiment

All **92 complete source days, 2019-10-01 through 2019-12-31**, had an eligible matching complete seven-day-prior historical source day. All were processed in chronological order: no post-outcome exclusions.

The nominal one-scenario and paired eight-training-day maximin MILPs locked their 24-quarter-hour binary on/start/stop commitments before the target residuals were revealed. Hourly synthetic gas inflow and site heating demand were constructed using the unchanged v0.9.21 uncalibrated gas/heat proxy formulas. A hypothetical controller receives each current source-hour's entire synthetic gas and heat rate at that hour's start; all future hours use frozen nominal gas/heat forecasts. The realized contemporaneous electricity price is only used to compute ex-post model contribution.

The source is hourly; four 15-minute mathematical controls per source hour are NOT independent 15-minute observations. No actual gas/heat telemetry, calibrated engine starts or ramps, real electricity-export award, or genuine historical as-of-gate price forecasts are available.

## 2. Full-period audited outcomes

| Quantity | Result |
|---|---:|
| Source-complete held-out days eligible and evaluated | **92 / 92** |
| Identical nominal and maximin first-stage SHA256 fingerprints | **92 / 92** |
| Both strategies feasible AND cyclic gas inventory matched | **58 days** |
| At least one infeasible causal replay | **29 days** |
| At least one feasible terminal-inventory mismatch | **5 days** |
| Mean maximin minus nominal modeled contribution on 58 valid matched comparisons | **EUR 0.00 per six hours** |
| Source, chronology, all interval conservation and economic ledger audit | **PASS** |
| Independently formulated failed-hour feasibility audit | **PASS** |
| Cross-platform no-lookahead/physical regression and strict SHA tests | **6 / 6 jobs PASS** |

These are **model-sample counts, not a plant reliability fraction**. Failures and unmatched-terminal days are reported separately, never imputed as zero earnings. The zero mean is a structural negative result: both policies chose exactly the SAME first-stage commitment for all 92 days, and the continuous causal controller then had the same inputs. The study therefore has **no experimental discrimination** between the two policies under the frozen assumption set; it proves neither economic superiority nor generalized ineffectiveness of robust methods.

## 3. Independent observed-hour failure diagnosis

A separate standalone four-interval LP reconstructed each **currently observed failed hour**, using the reported carried gas inventory, previous electrical power, frozen binary commitment and current hypothetical gas and heat flows. It retained stock conservation and 0–1.5 MWh_LHV capacity, generator minimum/maximum burn, consecutive-ON ramp and heat-service constraints, but imposed **no future-hour forecast constraints**.

| Result among 58 failed policy replays (two policies per affected day) | Count |
|---|---:|
| First failure at hour index 1 (09:00–10:00 UTC) | **50** |
| First failure at hour index 2 (10:00–11:00 UTC) | **8** |
| Current observed hour independently infeasible | **58** |
| Current hour feasible but remaining forecast horizon infeasible | **0** |
| One-at-a-time gas-stock floor relaxation restores current-hour LP feasibility | **58** |
| One-at-a-time consecutive-ON ramp relaxation restores current-hour LP feasibility | **58** |
| Individual stock-ceiling, binary-commitment or heat-capacity relaxations restore feasibility | **0 each** |

The two diagnostic single-family relaxations are *alternative counterfactuals*, not a proof of a unique cause and not permissible operational repairs. They identify the interaction of depleted stock and the modeled ramp limit under the frozen all-ON commitment. Allowing negative energy inventory or ignoring an engine ramp constraint would change the physics.

An example is **2019-10-01**, when both policies begin the failed second source hour at about **0 MWh_LHV**, with an assumed current gas inflow of **0.81635568 MW_LHV** and the frozen four-quarter-hour ON pattern. Reconstructed model feasibility fails even if all later-hour forecast requirements are removed.

**Narrow conclusion:** these 29 affected days contain genuine infeasibilities *under the current fictional model*, rather than failures caused only by overly strict future-hour nominal forecasts. The controller can consume available inventory down to the stock floor without maintaining an adequate ex-ante reserve against later lower gas arrivals and the modeled CHP ramp constraints. Real plant startup dynamics, fuel gas composition, buffer pressure and metrology are not validated.

## 4. Verification scope

The primary independent auditor uses publisher-source JSON and executed study JSON, imports no BiogasFlex model modules, and separately checks chronological prior-seven-day prices, pre-reveal first-stage fingerprints, conservation, capacity, ramp and monetary ledgers. The separate diagnostic also imports no BiogasFlex code and builds its own four-slot LP. Both alternative continuous LP formulations rely on SciPy/HiGHS; they are not independent global first-stage MILP optimality certificates.

Numerical carried-in fuel-stock roundoff at the physical boundary is normalized only within the existing independently verified 6e-5 MWh_LHV ledger tolerance. Adversarial regression tests include negative control cases for stock shortage, buffer overflow, ramp conflict, invalid binary values and numerical boundary roundoff.

## 5. Next stage, without favorable-outcome tuning

**A. Ex-ante inventory reserve viability.** Derive a gas-stock reserve requirement from declared bounded gas arrivals, minimum fuel and ramp constraints, then test whether a policy with this reserve is causally feasible and how much operating contribution it sacrifices. Do not relax energy conservation, force hindsight awareness or allow negative inventory.

**B. Strategy discriminability.** Pre-register a finite parameter/design sensitivity grid to identify when nominal and maximin first-stage decisions genuinely diverge. Report regions with identical commitment and negative results; never select only profitable dates.

**C. Physical data gate.** Obtain authorized plant biogas fuel-energy and pressure/flow records, useful-heat demand/delivery, measured starts/ramps and archived forecasts with as-of issuance times. The present SE3 regional electrical-load error is NOT measured CHP site heat forecast error, and gas/heat couplings are NOT empirical.

**Release decision:** Keep PR #28 in draft. A completed 92-day mathematical audit establishes a clear negative policy comparison and a reproducible infeasibility mechanism, not industrial CHP operational reliability or scientific v1.0 physical validation.
