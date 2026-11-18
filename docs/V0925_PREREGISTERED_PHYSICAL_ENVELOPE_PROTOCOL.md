# BiogasFlex v0.9.25 — Preregistered paired-source physical uncertainty envelope

**Status:** mathematical research sensitivity; NOT a causal CHP dispatch strategy, a measured gas/heat forecast-error model, real accepted electricity awards, or an industrial safety certificate.

## Scientific question

The v0.9.24 hypothetical contract experiment established that firm 15-minute electrical awards limit CHP flexibility, and no fully executed award had identical initial/final fuel inventory. With fixed efficiency ηe = 0.4, quarter-hour duration Δt = 0.25h and external award A_t MWh_e, fuel burn is exactly u_t = A_t/(ηe Δt). For fixed on/off commitment, the gas-stock trajectory is therefore determined by gas arrivals:

    s_k = s_0 + Δt * SUM_{t=1..k}(gas_arrival_t - u_t)

The new experiment separates **ex-post realizable physics** (test the already observed entire synthetic future path, NOT an implementable forecast-time controller) from **ex-ante all-bounded-path mathematical feasibility** (valid only if the assumed gas bounds genuinely hold). Neither is a reliable future site prediction.

No gas vent, purchased fuel, arbitrary gas-disposal device, imported electricity, softened award, heat-service omission, or market imbalance payment is introduced.

## Preregistered 54-cell parameter grid

| Factor | Exact choices | Physical scope |
|---|---|---|
| Gas buffer capacity | 0.75, 1.50, 3.00 MWh_LHV | Initial gas stock stays 0.75 MWh_LHV |
| Joint gas and heat shock multiplier | 0, 1, 1.5 | Both synthetic channels stressed together, never independently reshuffled |
| Useful thermal backup capacity | 0, 0.20 MW_th | Original separately assumed heat-dump limit remains 0.40 MW_th |
| External hypothetical electrical award | 0.090, 0.100, 0.150 MWh_e per 15 minutes | Fixed pre-reveal; 0.150 intentionally violates original initial electrical ramp |

**54 cells (3 × 3 × 2 × 3)**. Each reports *all* eligible training/holdout source-day physical feasibility, cyclic stock match, violated constraint families, terminal-stock delta extrema, and training-only moving-week bootstrap percentiles.

The benchmark fixes the static 24-quarter-hour **ALL-ON CHP commitment** for every source training and heldout sample. It additionally checks how many original v0.9.24 day-specific, pre-reveal nominal commitments are the same all-on pattern. This avoids selecting binary commitments based on favorable holdout gas realizations, but it is not a reoptimized hypothetical-award bidding MILP.

## Frozen source, heldout chronology, synthetic couplings

Source: Open Power System Data 2020-10-06 original SE3 hourly series, publisher SHA-256 6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8.

All complete days before 2019-10-01 are training. All **92** complete and prior-week-price-baseline eligible October–December 2019 source days are heldout. The preexisting full v0.9.24 study and its exact historical award/profile fingerprint must independently pass their original mathematical source/energy/award audit before the sensitivity output can be accepted. No dates can be removed following results.

At each of the six original **60-minute** source hours, the published price-baseline error and regional electrical-load forecast error jointly determine the unchanged v0.9.21 **uncalibrated synthetic** gas and heat rates. The six hourly paired shocks stay together as one chronological source-day block. Four 15-minute controls per source hour are mathematical, not 15-minute observations.

For registered alpha in {0,1,1.5}:

    gas_stressed = clip(1 + alpha*(gas_original_synthetic - 1), .78, 1.22) MW_LHV
    heat_stressed = clip(.15 + alpha*(heat_original_synthetic - .15), .105, .195) MW_th

This is a synthetic intervention. It cannot establish an empirical gas/heat/price joint forecast-error distribution or the historical TSO price-forecast issue vintage.

## 54 analytic all-path interval-bound certificates

For each gas-buffer, heat-backup and external-award configuration, independently test exactly these **predeclared hypothetical** uniform gas-input intervals, at each 15-minute instant:

| Band | Gas MW_LHV lower–upper | Interpretation |
|---|---|---|
| full_synthetic_clip | 0.78–1.22 | Proxy's imposed hard clipping, not measured supply guarantee |
| narrow_assumption_not_guaranteed | 0.90–1.10 | Arbitrary narrower interval; not certified to cover holdout gas |
| deterministic_nominal_only | 1.00–1.00 | Zero gas uncertainty, deliberate control case |

For constant u = A/(ηe Δt), all possible quarter-hour arrivals within a uniform interval yield extremal stock trajectories:

    s_lower(k) = s_0 + k Δt (gas_lower - u)
    s_upper(k) = s_0 + k Δt (gas_upper - u)

The certificate requires **both extreme paths stay between zero and storage capacity** at every k=1..24, original initial ramp and generator ratings hold, and all thermal source-demand support [0.105,0.195] MW_th can be served with available backup and dump ratings.

Nondegenerate independent gas bounds imply different possible terminal gas energies; exact cyclic terminal inventory **cannot be guaranteed for all paths** at fixed electrical burn and with no valid fuel-handling actuator. A degenerate constant gas input equal to fuel burn can guarantee cyclic inventory *within the declared mathematical model*.

Every assumed gas interval separately reports how many original 92-day source-mapped synthetic paths actually lie inside it. An arbitrary narrower interval may be selectively optimistic; its coverage cannot be advertised as a statistically calibrated forecast band.

## Training-only seven-day moving-block uncertainty sensitivity

Use all source-complete training dates preceding 2019-10-01. Form every **seven-calendar-consecutive-day** block without crossing missing dates or the source split. Predeclare **200** Monte Carlo resamples per sensitivity cell, using fixed seed **20261118** plus a SHA-256-derived per-cell seed. Each resample selects complete seven-day blocks with replacement, keeps the original hourly/regional pair dependencies within each day and seven-day serial dependencies, and trims to **92 training-source days**.

Report empirical training-only 5th and 95th percentile of the simulated six-hour feasible-day fraction. These are **descriptive sensitivity quantiles, not confidence limits, calibrated future-prediction coverage, or plant reliability probabilities**. The October–December 2019 heldout days never enter the bootstrap sampling pool and never define the registered parameter grid.

Report training and holdout **regional electricity price-persistence-error versus regional electricity-load forecast-error** correlations as descriptive source facts. Never call them site biogas/heat/price correlations.

## Independent acceptance and reproducibility

A completely separate Python standard-library auditor, importing **no BiogasFlex optimizing software**, must:

1. Reaudit original publisher source, 92-day v0.9.24 chronological commitment/award/source physical ledgers, and all allowed historical dates.
2. Independently reconstruct all training and holdout gas/heat proxy source-hour paths from original regional price/load errors, training moments and predeclared shock multipliers.
3. Independently recompute the **54-cell factorial matrix**, all complete-day physical constraint failures and strict terminal-stock matches.
4. Independently derive all **54 worst-case gas/heat interval certificates**.
5. Reproduce the **training-only consecutive-calendar-week bootstrap**, SHA-locked seed, and statistical disclaimers.
6. Reject altered source or award SHA, selected dates, missing failed days, false real-site calibration, incorrect physical unit conversions, negative stock, buffer overflow, thermally unserved loads, missed ramp limits and fabricated matched-service economics.

Reproduce source, original v0.9.24 and sensitivity studies outside tracked Git repository:

    python -m biogasflex source-evidence-v0921 --csv /tmp/opsd_original_60min.csv --download --output /tmp/v0921_verified_source.json
    python -m biogasflex.award_v0924 --source /tmp/v0921_verified_source.json --output /tmp/v0924_full.json
    python -m biogasflex.sensitivity_v0925 --source /tmp/v0921_verified_source.json --baseline /tmp/v0924_full.json --output /tmp/v0925_full.json
    python scripts/audit_v0925_envelope_independent.py --source /tmp/v0921_verified_source.json --baseline /tmp/v0924_full.json --study /tmp/v0925_full.json --output /tmp/v0925_certificate.json

**A4 research software gate is conditional on passing all checks, not on producing a favorable feasibility figure.** Industrial CHP real-site calibration and actual settlement remain blocked. The future v1.0 software release still requires matched-terminal-service economics, equipment parameter provenance, package release QA and external methodological review.


## Executed source-backed results, without changing the predeclared grid

The original publisher-hash-verified October–December 2019 experiment
and separate optimizer-free mathematical audit have **passed** in
[GitHub Actions run 44373327050](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44373327050).
The full [executed 92-day report](../reports/V0925_EXECUTED_92DAY_SOURCE_PAIRED_ENVELOPE.md)
and [machine-readable aggregate](../data/evidence/v0925_executed_92day_envelope_summary.json)
retain positive and negative findings, including every source-day
cell count and explicit false field-validation flags.

The independent numerical audit reconstructed **54 physical
parameter cells × (271 training days + 92 heldout days) = 19,602
physical day-cell scenarios**, exactly **54 interval-bound
certificates** (14 conditionally valid; **only one** spanning the
synthetic model's entire gas clipping interval), **253**
calendar-consecutive seven-day training block starts and
**200** training-only bootstrap replicates per cell.
The predeclared static ALL-ON CHP commitment matched the
unmodified v0.9.24 nominal first-stage across **92/92**
heldout days.

At original paired-source shock strength and 0.20 MW_th backup,
0.75 / 1.50 / 3.00 MWh_LHV gas storage yielded ex-post
fixed-award physically feasible holdout days:

- 0.090 MWh_e per 15min: **2 / 61 / 92** (of 92).
- 0.100 MWh_e per 15min: **41 / 88 / 91** (of 92).
- 0.150 MWh_e per 15min: **0 / 0 / 0** (original generator ramp violated).

No original-paired-shock feasible day also recovered exact
initial terminal fuel stock. Enlarged storage prevents
the modeled **upper-capacity** conflict, but a
fuel **shortage** persists on one source day at the
0.100 MWh_e contract even with 3.00 MWh_LHV capacity.
The initial ramp conflict cannot be resolved by adding
storage.

The complete report distinguishes the original 271
training and 92 heldout regional **electricity** error
correlations (−0.0285889039 and +0.2079326362)
from unobserved real CHP site gas/heat forecast errors,
and labels 7-day-bootstrap percentiles as descriptive
training uncertainty rather than calibrated field
confidence limits.

**Scientific gate:** the complete source mathematical audit
passes for A4. The remaining cross-platform tests,
PR dependency merges, site-data validation, credible
contract-aware commitment and strict cyclic terminal
service are **not** thereby qualified or released.
