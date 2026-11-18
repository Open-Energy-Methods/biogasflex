# v0.9.27 — Pre-delivery fixed-award acceptance and matched service

## Scientific scope

This is a research-software acceptance gate for the existing synthetic constant-efficiency, all-ON CHP model, not real bidding or market settlement. The award vector is supplied externally and known at the gate. Positive awards determine fuel and ON state, so no MILP is needed to certify the fixed request. An all-ON certificate deliberately does not model startup, shutdown, auction clearing, alternate operation after rejection or gas mass/pressure. The original v0.9.24 and v0.9.25 experiments are unchanged.

## Exact certificate

At each 15-minute slot t, fixed awarded energy A_t determines the fuel power u_t=A_t/(eta_e*dt). For uniform independently bounded gas arrival in [g_low,g_high], the two reachable inventory extremes at prefix k are

    S_low(k)  = S0 + k*dt*g_low  - sum(A_1..A_k)/eta_e
    S_high(k) = S0 + k*dt*g_high - sum(A_1..A_k)/eta_e.

Both extrema are attainable by constant extremal arrival paths, so requiring every prefix to remain inside [0,C] is necessary and sufficient for universal stock feasibility within the declared box. All positive-award power limits and consecutive-ON ramp limits are checked. Heat feasibility is checked at both demand extremes: the feasible useful CHP heat allocation interval is [max(0,h-backup_cap,recovered-dump_cap), min(h,recovered)]. This covers every intermediate heat demand because shortage and surplus are monotone. Arithmetic tolerance is 1e-9 in native units.

Two distinct services:
- **cyclic:** end inventory must equal initial inventory within the inherited 5e-5 MWh_LHV numerical criterion, for BOTH terminal extremes at acceptance.
- **carryover:** terminal stock must remain within physical bounds; no invented terminal monetary value or equivalence to cyclic service.

With gas support 0.78–1.22 MW_LHV over six hours, terminal spread is 2.64 MWh_LHV regardless of fixed award shape. A fixed award cannot guarantee cyclic inventory (the spread exceeds twice the numerical tolerance). For constant burn u, storage bounds give 1.22-(C-.75)/6 <= u <= .78+.75/6. C=1.5 gives an empty interval; C=3 gives [.845,.905] MW_LHV before other constraints. The 2.64 MWh minimum is a storage-energy requirement under the specified support and initial state, not a pressure-vessel design.

## Preregistered benchmark

All 24 cells are locked and SHA-256 fingerprinted before target source projection: 2 buffers (1.5 and 3.0 MWh_LHV), 3 inherited fixed profiles (.09, .10, .15 MWh_e/quarter), 2 terminal services, and 2 gates.
- Nominal gate: gas 1 MW_LHV, heat .15 MW_th deterministic assumption.
- Bounded gate: gas .78–1.22 MW_LHV, heat .105–.195 MW_th, full synthetic proxy support, not measured bounds.

Both gates use identical plant equipment within each cell pair: initial stock .75 MWh_LHV, 0.4 MW_e initial output, .2–.8 MW_e all-ON power, .8 MW_e/h ramp (half-interval initially), eta_e=.4, eta_h=.2, backup .2 MW_th, dump .4 MW_th. No comparison of profits across different capacities, contracts or terminal specifications.

Historical score: all 92 original eligible Oct–Dec 2019 UTC holdout dates, 271 training days to compute the unchanged source proxy standardization. Original OPSD hourly regional electrical price/load error pairs, not measured CHP data. Prices are used only for ex-post modeled operating contribution.

## Execution and comparison

A refused award produces no simulated operation and no earnings, not an order to shut down a real CHP. For acceptance, use the fixed award and newly available current-hour gas and heat only; advance until the first infeasible interval, explicitly retaining prior completed rows. Greedy useful heat min(h,recovered) minimizes static proxy backup/dump cost because increasing useful heat simultaneously reduces both. No future real prices or gas affect earlier control; no correction imports, venting, gas sales, or penalty payments.

Report total 92-day denominators for each gate, refusal, delivery failure, terminal service failure, fulfilled service and cyclic match. Full electricity delivery is not automatically full terminal service. No final contribution for rejected/incomplete/terminal-failed paths.

Paired economic comparison requires same capacity, exact per-interval awards, heat history, commitment, initial and identical final stock, full service for both gates. Strict cyclic pairs are separate from equal-inventory carryover pairs. The latter are descriptive operating contribution only, not cyclic earnings comparisons. Empty comparison sets return null, not zero. Identical fixed awards and static allocation imply zero paired difference if both paths fulfill; this is structural, not proof of commercial advantage. Gate refusal is not a full counterfactual operating strategy.

## Independent validation

A solver-free Fraction-arithmetic checker reconstructs every prefix certificate from cumulative energy sums, all gate decisions and all 92 × 24 outcomes, original source proxy, current heat split, failure prefix, terminal state and ex-post contribution. It rederives all counts and matched comparisons. Tests include nominal success, robust rejection, high/low gas extremes, nonconstant profiles and ramps, missing terminal service, meter-independent chronology and invalid inputs.

    python -m biogasflex source-evidence-v0921 --csv /tmp/opsd.csv --download --output /tmp/source.json
    python -m biogasflex.contract_v0927 --source /tmp/source.json --output /tmp/contract.json
    python scripts/audit_v0927_contract_independent.py --source /tmp/source.json --study /tmp/contract.json --output /tmp/audit.json

A6 allows a scientifically defensible negative result: no true matched cyclic contracts under this uncertainty and fixed-burn model. The required external gas-handling/contract flexibility, field calibration and actual awards remain separate. v1.0 requires A7 packaging/release verification, A8 scope and integration; no assumption that this is an industrial controller.
