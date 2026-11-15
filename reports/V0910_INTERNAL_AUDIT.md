# BiogasFlex v0.9.10 — Internal market-information verification audit

**Date:** 2026-11-15
**Status:** Experimental research-software numerical verification.
**No real market awards, bid submission, grid export, accepted bids,
forecast skill, balancing settlement, electrical metering, plant
profit, external methodological review, GitHub release or DOI.**

## The actual change

The new opt-in `market_v0910.py` module creates a **one-way information
boundary** between a *hypothetical pre-clearing energy offer* and a
*post-clearing exogenous fictional award*:

- Before the auction gate: accept only an explicit UTC delivery grid,
  dated synthetic as-of forecasts, exogenous offers and gate metadata;
  **no** price from the clearing result or accepted-volume input can
  enter this API.
- After clearing and after participant-specific confirmation: read
  a separately supplied fictional awarded-energy vector and clearing
  prices; check that all market events precede delivery and no offer
  was over-accepted.
- Assess delivery with the **unchanged, previously audited**
  v0.9.8.1 gas/heat/ramp/dwell/terminal-stock CHP mixed-integer
  optimization. Require the actual modeled electricity
  `power_MW × interval_duration_hours` to equal the exogenous
  accepted MWh **for every slot**, tolerance 1e-7 MWh.
- Any mismatch is explicitly **UNMODELLED_IMBALANCE** and is
  rejected rather than valuing an unmodelled intraday sale,
  imbalance settlement or electricity export.
- The sole cashflow check is
  `sum(accepted_MWh_i × fictional_clearing_price_EUR_per_MWh_i)`.
  The physical solver's contribution proxy is separate and
  must not be added a second time as electricity revenue.

## Independent exact synthetic oracles

| Case | Resolution | Hypothetical sell/accepted MWh | Hypothetical EUR/MWh | Independently calculated gross proxy |
| --- | --- | --- | --- | ---: |
| H | Two × 1 h | [0.4,0.4] | [20,60] | **€32.00** |
| Q | Four × 15 min | [0.1,0.1,0.1,0.1] | [20,40,60,80] | **€20.00** |

Each case assumes 1 MW_LHV fixed gas supply, 40% electric
conversion, 0 gas storage, zero initial and terminal
inventory and 0.4 MW_e constant CHP output. The
instantaneous heat requirement and its physical ledger
are also audited; these are **invented reference
parameters**, not real field measurements.

For both cases, independently checked:
`max_contract_delivery_residual_mwh=0`,
`max_gas_balance_residual_mwh=0`,
`max_heat_service_residual_mwh=0`.
A partially accepted `[0.4,0.1]` MWh two-hour
contract is rejected for an unmodelled excess of
synthetic electricity output, rather than recording
fictitious balancing transactions.

## Adversarial and inherited verification

New regression tests cover pre-clear and post-clear field separation,
immutable pre receipt, bids at/after gate, invalid forecast as-of
times, result publication/participant receipt/dispatch-plan order,
auction delay past delivery, accepted > offered, omitted/negative/
nonfinite quantities, negative prices, grid gaps/overlaps,
UTC-naive or non-UTC timestamps, 15-/60-minute energy accounting,
single-zone consistency, false postauction source claims,
incorrect CHP rating, unconstrained awards, and exact gross
cashflow calculations.

**DST preservation:** independent tests build complete 2026
Stockholm spring/autumn delivery days from UTC
observations—respectively **23 and 25 hourly slots**—
without inventing missing or repeating UTC times.
An explicit UTC market gate instant is always supplied;
the software never converts a generic 12:00 CET label
into a possibly incorrect DST-specific timestamp.

The inherited science and validation infrastructure remains intact:
286 original frozen science source/results, 216 historical
dual certificates, 96 solver-free two-period comparisons,
216 original market sensitivity cases, 5 hypothetical
interruption cases, and v0.9.5–v0.9.9 experimental oracles.
The v0.9.9 counterfactual sequential-price study is
retained and clearly distinguished from this new protocol.

Reproduction:
```bash
python -m pip install -e .
bash scripts/reproduce_v0910.sh
python scripts/audit_v0910_market_boundary.py
python -m biogasflex market-boundary
python -m biogasflex market-boundary --manifest examples/v0910_market_quarterhour.json
```

Windows: `./scripts/reproduce_v0910.ps1`.
The full cross-platform and strict checksum evidence is in
[GitHub Actions](https://github.com/Open-Energy-Methods/biogasflex/actions)
for the exact merged source commit when published.

## Scientific interpretation and limitations

This is **market-state validation**, not market-behaviour validation.
The current software does **not**:

1. Generate compliant Nord Pool curve/block orders, satisfy actual
   trading lot restrictions or submit bids.
2. Forecast actual pre-clearing prices with independently proved
   historical publication timestamps.
3. Infer accepted orders from zonal auction clearing prices.
4. Constrain the post-clearing MILP to reproduce an arbitrary
   *accepted* delivery schedule. The current stage rejects any
   awarded vector not already matched by the optimizer's
   **preferred feasible schedule**, even when another feasible
   but nonoptimal commitment schedule could physically meet it.
5. Model meter-level electrical export, parasitic consumption,
   network restrictions, fees, nomination, intraday hedging,
   balancing energy or imbalance charges.
6. Validate CHP start-up fuel, heat, nameplate, dwell, ramp,
   gas production or market decisions against site measurements.

These are intentionally omitted—not claims of completeness.
The next scientifically useful development is a separately
audited **hard-contracted-delivery MILP feasibility model** with
optional redispatch costs, before any bidding-profitability study.

Real market source context:
[Nord Pool day-ahead process](https://www.nordpoolgroup.com/en/the-power-market/Day-ahead-market/),
[Nordic/Baltic specifications effective 2026-05-28](https://www.nordpoolgroup.com/49bf28/globalassets/download-center/rules-and-regulations/b.3.1-product-specifications-nordic-and-baltic-valid-from-28.05.2026.pdf),
[market regulation effective 2026-02-16](https://www.nordpoolgroup.com/491c3f/globalassets/download-center/rules-and-regulations/b.2.1a-day-ahead-market-regulations-nordic-baltic-and-wce.pdf).

Independent human scientific review remains required under
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
