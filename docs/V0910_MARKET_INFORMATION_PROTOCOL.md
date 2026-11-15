# BiogasFlex v0.9.10 — Explicit day-ahead information and no-imbalance contract boundary

**Status:** Opt-in, offline, strictly hypothetical market-interface **software
validation**. NOT a real Nord Pool auction, submitted order, accepted bid,
market clearing, plant export, intraday trade, imbalance price, settlement,
profitability estimate, or operational CHP-control validation.

## Motivation and explicit limits

v0.9.9 accurately replayed source-attributed real 2020 SE3 price observations
against an *invented* CHP, but revealed price observations sequentially.
That synthetic information regime is not the Nordic day-ahead auction. In
actual day-ahead trading, participants submit bids by the gate (normally
12:00 CET on the day before delivery), then clearing results are published,
and the participant receives its own results. Results may be delayed.

**Authoritative market-reference URLs**, checked 15 November 2026:

- [Nord Pool — Day-ahead market daily process](https://www.nordpoolgroup.com/en/the-power-market/Day-ahead-market/)
  — D−1 gate, clearing, participant reports, physical obligations
- [Nord Pool — Nordic/Baltic product specifications effective 28 May 2026](https://www.nordpoolgroup.com/49bf28/globalassets/download-center/rules-and-regulations/b.3.1-product-specifications-nordic-and-baltic-valid-from-28.05.2026.pdf)
  — 15-minute delivery periods, 12:00 CET D−1 published gate
- [Nord Pool — Market regulations effective 16 February 2026](https://www.nordpoolgroup.com/491c3f/globalassets/download-center/rules-and-regulations/b.2.1a-day-ahead-market-regulations-nordic-baltic-and-wce.pdf)
  — results, participant reports and delays

**We do not convert the usual wall-clock market deadline to a guessed
UTC instant.** Each synthetic study supplies the exact recorded
`auction_gate_close_utc` and `prices_published_utc`; an
exceptionally delayed result remains possible. Every timestamp must be
explicit UTC, and Stockholm civil-date consistency is independently
checked. No inferences about what was actually known or awarded are
made from generic published historical price rows.

## Phase A — pre-clearing offer boundary

`validate_preclearing_offer(market, delivery_slots, offer, rating_mw_e)`

Accepted information: predeclared future delivery UTC grid, explicit
forecast information issuance time, decision/submission times, a
synthetic vector of forecast prices and EXOGENOUS hypothetical
single-period *sell* offered energy quantities (MWh).
**No realized clearing price, accepted quantity or award field is
accepted in this API.** An accidental clearing-price key fails the
exact-input contract.

Timeline: `forecast_issued <= bid_decided <= bid_submitted < gate`.

The receipt says **NOT_AWARDED_YET**, clearing prices unavailable,
cashflow and accepted volumes null, and records the exact input
fingerprint (SHA-256 integrity digest, **not a cryptographic proof
of historical availability**). `forecast_provenance` is limited
to `SYNTHETIC_PREAUCTION_ASSUMPTIONS`: metadata assertions alone
cannot substantiate genuine market-as-of forecast skill.

Each offered MWh must be finite, nonnegative and no greater than the
hypothetical nameplate MW × hours. Not a Nord Pool product-order API:
block orders, coupled auction constraints, lot sizes, price curves,
order acceptance and exchange transaction requirements are **not
implemented**.

## Phase B — post-clearing exogenous award / physical match

`audit_postclearing_delivery(market, slots, pre_receipt, award, chp_config)`

Exogenous inputs include participant-specific *fictional* accepted
MWh and fictional clearing EUR/MWh, publication/receipt/dispatch
timestamps, with exact receipt/market/slot crosschecks.

Mandatory timeline: `gate < published <= participant_receipt
<= dispatch_plan_created < first_delivery_start`. A delayed or
missing result cannot be silently replaced by the nominal 12:45
clearing time.

Accepted MWh cannot exceed previously offered MWh. The physical
v0.9.8.1 `receding_horizon_commitment_milp_v098` model is solved
using the known post-clearing prices to assess feasibility under its
declared gas, thermal, ramp, dwell, on/off and inventory assumptions.
The previously verified physical solver/ledger is **untouched**.
Every chosen electric MW × delivery hours must **equal** accepted
MWh (absolute tolerance 1e−7 MWh). If not, return
`UNMODELLED_IMBALANCE` and **refuse to invent an intraday trade,
balancing energy or imbalance settlement price**.

A matched result calculates strictly:
`gross_contract_cashflow_proxy_eur = Σ(accepted_MWh_i × cleared_EUR_per_MWh_i)`.

It is a **gross, fictional matched-contract numerical proxy**.
It does not include imbalance, transaction fees, grid tariffs,
export metering, ancillary services, price-area forecasting skill,
accepted volume optimization, exchange clearing, OPEX or NPV.
Do not combine it with the solver's `net_contribution_eur` as
though they were separate, additive revenues. It reports both
quantities as separate, explicitly scoped diagnostics.

**Important modelling constraint:** The optimizer currently
selects its own postclear preferred feasible dispatch. This phase
does NOT impose contracted awards as hard equalities inside the
MILP. It therefore supports *only* exogenous awards already
matched exactly by that optimum; otherwise it rejects them.
Feasible nonoptimal contractual schedules, operational redispatch
after award and imbalance management are future versions.

## Synthetic independent oracles

All dates, awards, CHP inputs and prices below are invented;
2020 observed datasets are never used to imply real outcomes.

- **Two hourly slots:** constant 1 MW_LHV input, η_e=0.4,
  no storage, initial/terminal stock 0, 0.4 MW_e each hour.
  Submitted and accepted energy [0.4, 0.4] MWh,
  fictional prices [20, 60] EUR/MWh.
  Independent gross proxy: **€32**, accepted electricity **0.8 MWh**.
- **Four 15-minute slots:** same constant 0.4 MW_e,
  [0.1,0.1,0.1,0.1] MWh each, fictional prices
  [20,40,60,80] EUR/MWh, gross proxy **€20**,
  accepted electricity **0.4 MWh**.
- **Negative test:** accepted [0.4,0.1] MWh against
  physically forced [0.4,0.4] MWh must raise
  `UNMODELLED_IMBALANCE`, not sell 0.3 MWh implicitly.

The predeclared hour and quarter-hour scenarios deliberately cover
only the first slots of a fictional delivery day, not a full
trading-day or clearing-price reconstruction.

## UTC/DST, provenance, adversarial tests

- UTC timestamps only: reject naive or local-offset timestamps,
  duplicate/gapped/out-of-order physical slots and wrong bidding zones
- Check all slot starts belong to the declared Stockholm delivery
  date; auction gate belongs to **previous Stockholm civil date**
- 2026 spring/autumn DST full local-day interval-grid tests:
  respectively **23 and 25 hourly slots**, without fabricating
  repeated or missing UTC hours
- Explicit 0.25- and 1-hour durations; negative finite prices
  permitted; NaN/infinite/boolean quantities disallowed
- Reject bid at gate, post-gate forecast, publication before
  gate, participant notification before publication, and planning
  after first delivery
- Reject acceptance greater than offer, altered pre-clearing
  receipt and model-delivered energy mismatches
- No output file by default; opt-in detailed ledger only

## Reproduce

```bash
python -m pip install -e .
bash scripts/reproduce_v0910.sh
python scripts/audit_v0910_market_boundary.py
python -m biogasflex market-boundary
python -m biogasflex market-boundary --manifest examples/v0910_market_quarterhour.json
python -m biogasflex market-boundary --output market_report.json
```

Windows: `./scripts/reproduce_v0910.ps1`.

Reproduces all historical scientific audits and validates the original
**286 frozen scientific source/results files** byte-for-byte, with
full SHA-256 distribution and Git tracking manifest. The original
2019/2020 SE3 observations, original 216 historical sensitivity
cases, five hypothetical resilience cases, 216 primal-dual certificates,
96 solver-free oracles and v0.9.5–v0.9.9 experimental models are
**unmodified**.

## What remains for stronger claims

Genuine participant-specific dated auction awards and bid
records (when permissible), verified as-of forecasts with
publication metadata, delivery nominations and grid export
meters, balancing/imbalance rules, plant-specific flexible
dispatch with contractual hard volume constraints, calibrated
gas/heat/CHP performance and independent human
methodological review. [Review issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3)
remains open. No scientific v1.0, GitHub Release or DOI is
established by this software gate.
