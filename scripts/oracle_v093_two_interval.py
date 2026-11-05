"""Solver-free two-interval oracle for heat-aware biogas CHP gas-buffer dispatch.

Uses conservation to eliminate both fuel-use variables in favor of one
intermediate inventory. The remaining objective is piecewise affine:
an optimum must occur at a feasible stock endpoint or a heat-service kink.
No SciPy, NumPy, or original BiogasFlex solver imports are used here.

This establishes independent *small-horizon mathematical verification*,
not validation of real CHP operation, the 216-case historical results, or
an independent general-purpose LP solver.
"""
from __future__ import annotations

import math

TOL = 1e-9


class OracleFailure(ValueError):
    """The requested scenario has invalid inputs or no feasible fixed baseline."""


def _finite(value, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise OracleFailure(f"{label} must be numeric, not a boolean/string")
    result = float(value)
    if not math.isfinite(result):
        raise OracleFailure(f"{label} must be finite")
    return result


def _series(config: dict, key: str, *, default=None, required=False):
    if required and key not in config:
        raise OracleFailure(f"Missing required field: {key}")
    raw = config.get(key, default)
    if isinstance(raw, (tuple, list)):
        if len(raw) != 2:
            raise OracleFailure(f"{key}: expected two intervals")
        result = tuple(_finite(item, key) for item in raw)
    else:
        result = (_finite(raw, key),) * 2
    if any(item < 0 for item in result):
        raise OracleFailure(f"{key}: values must be nonnegative")
    return result


def _heat_cost(use: float, demand: float, eta_h: float,
               backup_price: float, dump_price: float) -> float:
    heat = eta_h * use
    auxiliary = max(0.0, demand - heat)
    dumped = max(0.0, heat - demand)
    return auxiliary * backup_price + dumped * dump_price


def verify_two_interval(config: dict, intervals) -> dict:
    """Exact piecewise-linear search for any valid two-interval scenario.

    intervals: two (EUR/MWh_e spot price, duration_h) numeric pairs.
    Returns the optimized economic contribution and incremental modeled
    contribution versus the constant-stock fixed-use comparator.
    """
    if config.get("heat_service_model") != "instantaneous_heat_service_no_thermal_store_v07":
        raise OracleFailure("Unsupported heat-service assumption")
    if not isinstance(intervals, (tuple, list)) or len(intervals) != 2:
        raise OracleFailure("Exactly two intervals are required")
    prices = []
    durations = []
    for interval in intervals:
        if not isinstance(interval, (tuple, list)) or len(interval) != 2:
            raise OracleFailure("Each interval must have (price, duration)")
        price, dt = [_finite(value, "price/duration") for value in interval]
        if dt <= 0:
            raise OracleFailure("Interval duration must be positive")
        prices.append(price)
        durations.append(dt)
    eta_e = _finite(config.get("electric_efficiency_lhv"), "electric efficiency")
    eta_h = _finite(config.get("thermal_efficiency_lhv"), "thermal efficiency")
    rating = _finite(config.get("electric_rating_mw"), "CHP rating")
    capacity = _finite(config.get("gas_storage_capacity_mwh_lhv"), "buffer capacity")
    initial = _finite(config.get("initial_gas_inventory_mwh_lhv", 0),
                      "initial inventory")
    if not (0 < eta_e <= 1 and 0 <= eta_h <= 1 and eta_e+eta_h <= 1+1e-12
            and rating > 0 and capacity >= 0 and 0 <= initial <= capacity):
        raise OracleFailure("Unphysical efficiency, nameplate or gas inventory")
    source = _series(config, "gas_production_mw_lhv",
                     default=config.get("gas_input_mw_lhv"), required=False)
    flaring = _series(config, "fixed_flaring_mw_lhv", default=0)
    losses = _series(config, "fixed_losses_mw_lhv", default=0)
    demand = _series(config, "heat_demand_mw_th", required=True)
    backup_cap = _series(config, "aux_heat_capacity_mw_th", required=True)
    dump_cap = _series(config, "heat_dump_capacity_mw_th", required=True)
    backup_price = _series(config, "aux_heat_cost_eur_per_mwh_th", required=True)
    dump_price = _series(config, "heat_dump_penalty_eur_per_mwh_th", default=0)
    chp_cost = _series(config, "chp_variable_cost_eur_per_mwh_e", default=0)
    supplied = tuple(source[t]-flaring[t]-losses[t] for t in range(2))
    if any(u < -TOL for u in supplied):
        raise OracleFailure("Fixed flaring and losses exceed gas production")
    bounds = []
    for t in range(2):
        low, high = 0.0, rating/eta_e
        if eta_h > 0:
            low = max(low, (demand[t]-backup_cap[t])/eta_h)
            high = min(high, (demand[t]+dump_cap[t])/eta_h)
        elif demand[t] > backup_cap[t]+TOL:
            raise OracleFailure("Heat demand cannot be met without CHP heat")
        if low > high+TOL:
            raise OracleFailure("No feasible CHP use within heat capacity")
        if not (low-TOL <= supplied[t] <= high+TOL):
            raise OracleFailure("Fixed gas-use comparator violates CHP/heat bounds")
        bounds.append((max(0.0,low),high))
    # Stock at end of first interval is the sole degree of freedom.
    # u0 = supply0 + (initial-s)/dt0
    # u1 = supply1 + (s-initial)/dt1.
    s_min = max(
        0.0,
        initial+(supplied[0]-bounds[0][1])*durations[0],
        initial+(bounds[1][0]-supplied[1])*durations[1],
    )
    s_max = min(
        capacity,
        initial+(supplied[0]-bounds[0][0])*durations[0],
        initial+(bounds[1][1]-supplied[1])*durations[1],
    )
    if s_min > s_max + TOL or not (s_min-TOL <= initial <= s_max+TOL):
        raise OracleFailure("No feasible inventory trajectory or baseline")
    if s_min > s_max:
        s_min = s_max = initial

    def fuel(stock: float):
        return (
            supplied[0]+(initial-stock)/durations[0],
            supplied[1]+(stock-initial)/durations[1],
        )

    def contribution(stock: float) -> float:
        use = fuel(stock)
        return math.fsum(
            (eta_e*use[t]*(prices[t]-chp_cost[t])
             - _heat_cost(use[t],demand[t],eta_h,
                          backup_price[t],dump_price[t])) * durations[t]
            for t in range(2)
        )

    candidates = [s_min, s_max]
    if eta_h > 0:
        # Piecewise-linear heat-service cost changes slope at eta_h*u=demand.
        candidates += [
            initial+(supplied[0]-demand[0]/eta_h)*durations[0],
            initial+(demand[1]/eta_h-supplied[1])*durations[1],
        ]
    feasible_candidates = sorted(set(
        min(s_max,max(s_min,s)) for s in candidates
        if s_min-TOL <= s <= s_max+TOL
    ))
    if not feasible_candidates:
        raise OracleFailure("No candidate dispatch")
    optimal_stock = min(feasible_candidates,
                        key=lambda s: (-contribution(s), s))
    optimized = contribution(optimal_stock)
    fixed = contribution(initial)
    if optimized < fixed-1e-7:
        raise OracleFailure("Analytical optimum below feasible fixed comparator")
    return {
        "status": "PASS",
        "optimal_stock_after_first_mwh_lhv": optimal_stock,
        "optimal_gas_use_mw_lhv": list(fuel(optimal_stock)),
        "optimized_contribution_eur": optimized,
        "fixed_contribution_eur": fixed,
        "incremental_contribution_eur": optimized-fixed,
        "candidate_count": len(feasible_candidates),
        "stock_feasible_min_mwh_lhv": s_min,
        "stock_feasible_max_mwh_lhv": s_max,
        "derivation": "one-dimensional exact breakpoint enumeration; no optimization library",
    }
