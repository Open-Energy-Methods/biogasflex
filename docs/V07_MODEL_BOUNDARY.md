# V07 technical model boundary and acceptance contract

## System definition

One CHP with constant or exogenously varied gas supply, energy-based gas storage, electricity output, and simultaneous recoverable heat. One price per explicitly bounded UTC interval; one exogenous **heat service requirement** per interval. All heat is assumed to be immediately interchangeable at a compatible temperature, an idealization with no proof from individual plant operating records. No thermal storage.

Unit definitions: `G, U, F, L` MW_LHV, `S` MWh_LHV, `P` MW_e, `Q` MW_th, `D` MW_th, `B` MW_th auxiliary, `J` MW_th dumped/rejected, `dt` hours. `price` EUR/MWh_e; `c_aux`, `c_dump` EUR/MWh_th; `c_chp` EUR/MWh_e.

### Constraints

For each interval `t`:

```text
S[t+1] = S[t] + (G[t] - U[t] - F[t] - L[t]) * dt[t]
S[0] = S[N] = S_initial; 0 <= S[t] <= S_max
0 <= eta_e*U[t] <= P_e_max
Q_available[t] = eta_th * U[t]
Q_useful[t] + Q_dump[t] = Q_available[t]
Q_useful[t] + Q_aux[t] = D[t]
0 <= Q_useful[t] <= D[t]
0 <= Q_aux[t] <= Q_aux_max[t]
0 <= Q_dump[t] <= Q_dump_max[t]
```

The heat allocation always maximizes immediate direct useful CHP heat before backup and heat dumping, breaking any otherwise non-physical degeneracy at zero backup/dump marginal cost. This is done after optimization and can only decrease auxiliary/dumped energy, preserving or increasing the economic objective. Equal `G/F/L`, fuel efficiency, time base and cyclic terminal stock make total utilized gas identical for fixed and optimized schedules. If the **fixed comparator is infeasible** under electric or thermal service/sink limits, no comparative result is published.

### Objective

```text
max sum_t dt[t] * (
    price[t] * (eta_e*U[t])
    - c_chp[t] * (eta_e*U[t])
    - c_aux[t] * Q_aux[t]
    - c_dump[t] * Q_dump[t]
)
```

This is called **scenario economic contribution**. It is not net operating margin/profit: there is no fuel purchase price, CAPEX, annual maintenance, equipment depreciation, grid charges, plant specific generation/export tariff, heat sales, backup asset CAPEX, storage construction cost, personnel, contingency or verified plant efficiency. A day-ahead price multiplied by **gross electricity generation** gives *spot-equivalent value*, not actual cash revenue. Price foresight is perfect and may overestimate feasible dispatch value.

### Consequences of the assumptions

- With **zero service demand** and sufficient dumping capacity, and zero dump/CHP cost, the model reduces to the v0.6 electricity-only LP.
- If heat demand equals the fixed CHP thermal output and backup and dump both unavailable, the only feasible dispatch can be fixed generation (even when gas buffer exists).
- Auxiliary-heat penalties lower scenario value only when the dispatch increases auxiliary requirement relative to its comparator; when demand is already above fixed CHP heat output, gas shifting can produce electricity arbitrage **without** increasing total backup use if no additional heat is dumped.
- Physically, a CHP unit may require thermal protection during heat rejection and minimum loads. Neither is modelled. LP convexity and solver optimality do not establish field operability.
- Heat recovery is proportional to gas utilization at a **constant hypothetical efficiency** across load. High-grade/low-grade heat matching, heat network temperature, storage and pumping constraints are absent.
- Modulation and dispatch can be highly unrealistic for an actual engine without min on/off, starts, ramp, wear and efficiency-map evidence. This version deliberately does *not* introduce binary MILP claims.

## V07 acceptance gates

1. Keep old v0.6 analytical oracle EUR 60 → EUR 84 with the unchanged data and 40 legacy tests.
2. Two-period heat-constrained oracle at c_aux=80: gross EUR 84, backup EUR 14.4, contribution EUR 69.6, increment EUR 9.6; exact independent analytical derivation.
3. Both gas and heat balances verified per interval and in total. No simultaneous auxiliary and dumping under direct-use priority.
4. Infeasible fixed comparators/invalid inputs **raise**, not incorrectly reported as zero additional contribution.
5. Equal total gas supply/use and heat **demand** across optimized and fixed comparisons; heat *split* may differ.
6. Source-mixed Lövsta 24-h case uses an explicit demand *proxy*; costs and capacities are unobserved assumptions.
7. A predeclared scenario matrix includes null outcomes, JSON/CSV and optional plot regeneration.
8. Separate independent-code checker verifies archived trajectories and detects corrupted outputs; documented limits on independent human review.
9. No claim of full CHP profitability or validated heat dispatch.
