"""BiogasFlex v0.9.5: opt-in, always-on CHP operational *surrogate*.

Experimental LP adds power-rate ramps and a positive lower output while
retaining gas inventory and instantaneous heat service. It is deliberately
separate from the frozen v0.7 scientific dispatch implementation.

A continuous minimum-output floor applies in EVERY interval. It is NOT
a unit-commitment min-load/off/on MILP; start-up, shutdown, switching,
equipment dynamics and true operating feasibility remain unmodelled.
"""
from __future__ import annotations

from datetime import timedelta
import math
from typing import Any, Sequence

from scipy.optimize import linprog
from scipy.sparse import lil_matrix

from .baseline import Interval
from .dispatch import DispatchError, CONSERVATION_ABS_TOL_MWH
from .heat_dispatch import (
    _audit_ledger, _fixed_scenario, _ledger, prepare_heat_inputs,
    optimize_heat_dispatch,
)

TOL = 1e-7
COST_TOL = 1e-6
EXPERIMENT = "continuous_always_on_ramp_surrogate_v095"
REQUIRED = {"model", "ramp_up_mw_e_per_hour", "ramp_down_mw_e_per_hour",
            "minimum_power_mw_e", "initial_power_mw_e"}


def _number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite nonnegative numeric value")
    x = float(value)
    if not math.isfinite(x) or x < 0:
        raise ValueError(f"{label} must be a finite nonnegative numeric value")
    return x


def _operating(config: dict, rating: float) -> dict[str, float | str]:
    raw = config.get("experimental_v095")
    if not isinstance(raw, dict) or set(raw) != REQUIRED or raw.get("model") != EXPERIMENT:
        raise ValueError("Explicit, complete experimental_v095 always-on ramp configuration required")
    s = {"model": EXPERIMENT}
    for k in REQUIRED - {"model"}:
        s[k] = _number(raw[k], k)
    if s["minimum_power_mw_e"] > rating + TOL:
        raise ValueError("Minimum always-on power exceeds nameplate rating")
    if not s["minimum_power_mw_e"] - TOL <= s["initial_power_mw_e"] <= rating + TOL:
        raise ValueError("Initial power outside continuously-on operating range")
    return s


def _check_ramps(power: Sequence[float], durations: Sequence[float], limits: dict) -> float:
    prev = limits["initial_power_mw_e"]
    max_over = 0.0
    for t, p in enumerate(power):
        # Initially power is observed at start of the first slot.
        # Subsequent decisions are interpreted as slot-midpoint powers.
        elapsed = 0.5 * (durations[t] if t == 0 else durations[t-1] + durations[t])
        delta = p - prev
        max_over = max(max_over,
                       delta - limits["ramp_up_mw_e_per_hour"] * elapsed,
                       -delta - limits["ramp_down_mw_e_per_hour"] * elapsed, 0)
        prev = p
    return max_over


def optimize_operating_surrogate(config: dict, intervals: Sequence[Interval]) -> dict[str, Any]:
    """Perfect-foresight experimental dispatch: same heat/gas conservation,
    plus a continuous always-on electrical output floor and midpoint ramps.

    A fixed-output, constant-stock comparator must itself satisfy all
    experimental constraints or the comparison fails (no false uplift).
    """
    inp = prepare_heat_inputs(config, intervals)
    gas = inp.gas
    limits = _operating(config, gas.rating_mw_e)
    n = len(gas.price_intervals)
    dt = [interval.hours for interval in gas.price_intervals]
    min_u = limits["minimum_power_mw_e"] / gas.eta_e
    max_u = gas.rating_mw_e / gas.eta_e
    fixed_ledger, fixed = _fixed_scenario(inp)
    fixed_power = [gas.eta_e * value for value in fixed["gas_use"]]
    if (min(fixed_power) < limits["minimum_power_mw_e"]-TOL
            or _check_ramps(fixed_power, dt, limits) > TOL):
        raise DispatchError("Fixed comparator violates experimental power minimum or ramp limits")

    # LP 5 variable blocks per period:
    # gas use u, end inventory s, useful CHP heat q, auxiliary heat a,
    # physically rejected heat w.
    u0, s0, h0, a0, w0 = (k*n for k in range(5))
    objective = [0.0] * (5*n)
    bounds = [(0.0, None)] * (5*n)
    aeq = lil_matrix((3*n+1, 5*n), dtype=float)
    beq = [0.0] * (3*n+1)
    aub = lil_matrix((2*n, 5*n), dtype=float)
    bub = [0.0] * (2*n)

    for t, row in enumerate(gas.price_intervals):
        objective[u0+t] = -gas.eta_e * (
            row.price_eur_per_mwh - inp.variable_chp_cost_eur_mwh_e[t]) * dt[t]
        objective[a0+t] = inp.backup_cost_eur_mwh_th[t]*dt[t]
        objective[w0+t] = inp.dump_penalty_eur_mwh_th[t]*dt[t]
        bounds[u0+t] = (min_u, max_u)
        bounds[s0+t] = (0, gas.storage_capacity_mwh_lhv)
        bounds[h0+t] = (0, inp.demand_mw_th[t])
        bounds[a0+t] = (0, inp.backup_cap_mw_th[t])
        bounds[w0+t] = (0, inp.dump_cap_mw_th[t])
        # Gas conservation and initial gas inventory.
        aeq[t, u0+t] = dt[t]
        aeq[t, s0+t] = 1
        if t:
            aeq[t, s0+t-1] = -1
        beq[t] = (gas.production_mw_lhv[t] - gas.fixed_flaring_mw_lhv[t]
                  - gas.fixed_losses_mw_lhv[t])*dt[t]
        if t == 0:
            beq[t] += gas.initial_storage_mwh_lhv
        # Thermal conversion and instantaneous thermal service.
        aeq[n+t, u0+t] = gas.eta_th
        aeq[n+t, h0+t] = -1
        aeq[n+t, w0+t] = -1
        aeq[2*n+t, h0+t] = 1
        aeq[2*n+t, a0+t] = 1
        beq[2*n+t] = inp.demand_mw_th[t]
        # Power change constraints between adjacent operating midpoints.
        elapsed = 0.5 * (dt[t] if t == 0 else dt[t-1] + dt[t])
        aub[2*t, u0+t] = gas.eta_e
        aub[2*t+1, u0+t] = -gas.eta_e
        if t == 0:
            bub[2*t] = limits["initial_power_mw_e"] + limits["ramp_up_mw_e_per_hour"]*elapsed
            bub[2*t+1] = -limits["initial_power_mw_e"] + limits["ramp_down_mw_e_per_hour"]*elapsed
        else:
            aub[2*t, u0+t-1] = -gas.eta_e
            aub[2*t+1, u0+t-1] = gas.eta_e
            bub[2*t] = limits["ramp_up_mw_e_per_hour"]*elapsed
            bub[2*t+1] = limits["ramp_down_mw_e_per_hour"]*elapsed
    aeq[3*n, s0+n-1] = 1
    beq[3*n] = gas.initial_storage_mwh_lhv
    result = linprog(objective, A_eq=aeq.tocsr(), b_eq=beq,
                     A_ub=aub.tocsr(), b_ub=bub, bounds=bounds, method="highs")
    if not result.success or result.x is None or result.fun is None:
        raise DispatchError(f"Experimental CHP LP infeasible / nonoptimal: {result.status}: {result.message}")

    use = [float(x) for x in result.x[u0:u0+n]]
    stock = [gas.initial_storage_mwh_lhv] + [float(x) for x in result.x[s0:s0+n]]
    # Choose physically direct CHP heat before backup/dump in a degenerate
    # zero-cost optimum, as in the frozen heat dispatch.
    useful = [min(max(0.0, gas.eta_th*use[t]), inp.demand_mw_th[t]) for t in range(n)]
    auxiliary = [inp.demand_mw_th[t]-useful[t] for t in range(n)]
    rejected = [gas.eta_th*use[t]-useful[t] for t in range(n)]
    ledger = _ledger(inp, use, stock, useful, auxiliary, rejected)
    _audit_ledger(inp, ledger)
    if abs(-float(result.fun)-ledger["economic_contribution_proxy_eur"]) > COST_TOL:
        raise DispatchError("Experimental CHP solver objective/ledger mismatch")
    power = [gas.eta_e*x for x in use]
    max_ramp = _check_ramps(power, dt, limits)
    if max_ramp > TOL or min(power) < limits["minimum_power_mw_e"]-TOL:
        raise DispatchError("Experimental CHP ramp or always-on power minimum violated")
    if abs(ledger["gas_utilized_mwh_lhv"]-fixed_ledger["gas_utilized_mwh_lhv"]) > CONSERVATION_ABS_TOL_MWH:
        raise DispatchError("Unfair comparison: different gas energy use")
    contribution = ledger["economic_contribution_proxy_eur"]
    increment = contribution-fixed_ledger["economic_contribution_proxy_eur"]
    if increment < -COST_TOL:
        raise DispatchError("Feasible fixed CHP comparator exceeds experimental optimum")
    # Because this experimental model adds constraints and does not change
    # the original objective, the original LP is a mathematical upper bound.
    free = optimize_heat_dispatch(config, intervals)
    unconstrained = free["optimized_dispatch"]["economic_contribution_proxy_eur"]
    if contribution > unconstrained+COST_TOL:
        raise DispatchError("Constrained optimum exceeds unconstrained upper bound")
    return {
        "version": "0.9.5", "model_type": EXPERIMENT, "case_id": gas.case_id,
        "boundary": ("Experimental continuous always-on thermal-service CHP LP. "
                     "Assumed ramp envelopes and minimum electrical output are NOT "
                     "validated equipment performance or real unit commitment."),
        "limits": limits, "solver": {"backend": "SciPy/HiGHS", "success": True},
        "fixed_dispatch": fixed_ledger, "optimized_dispatch": ledger,
        "incremental_contribution_eur": increment,
        "unconstrained_optimal_contribution_upper_bound_eur": unconstrained,
        "max_ramp_violation_mw_e": max_ramp,
        "min_power_observed_mw_e": min(power),
        "hourly": [
            {"start_utc": row.start_utc.isoformat(),
             "dt_h": row.hours, "market_price_eur_mwh": row.price_eur_per_mwh,
             "gas_use_mw_lhv": use[t], "stock_start_mwh_lhv": stock[t],
             "stock_end_mwh_lhv": stock[t+1], "electric_power_mw_e": power[t],
             "heat_served_chp_mw_th": useful[t],
             "heat_served_auxiliary_mw_th": auxiliary[t],
             "heat_rejected_mw_th": rejected[t]}
            for t, row in enumerate(gas.price_intervals)
        ],
    }


def evaluate_fixed_forecast_schedule(
    config: dict,
    forecast_intervals: Sequence[Interval],
    realized_intervals: Sequence[Interval],
) -> dict[str, Any]:
    """Commit the forecast dispatch, evaluate it ex post against actual prices.

    No replanning, probabilistic forecasting, price forecasting algorithm, or
    heat-demand errors are modelled. All non-price inputs stay identical.
    """
    if len(forecast_intervals) != len(realized_intervals) or not forecast_intervals:
        raise ValueError("Forecast and realized market windows must match")
    for forecast, actual in zip(forecast_intervals, realized_intervals):
        if (forecast.start_utc != actual.start_utc or forecast.hours != actual.hours
                or forecast.zone != actual.zone or
                not math.isfinite(actual.price_eur_per_mwh)):
            raise ValueError("Forecast and realization intervals/zone/duration must match")
    plan = optimize_operating_surrogate(config, forecast_intervals)
    hindsight = optimize_operating_surrogate(config, realized_intervals)
    eta_e = float(config["electric_efficiency_lhv"])
    actual_shift = math.fsum(
        eta_e * hour["gas_use_mw_lhv"] * forecast.hours *
        (realized.price_eur_per_mwh-forecast.price_eur_per_mwh)
        for hour,forecast,realized in zip(plan["hourly"],forecast_intervals,realized_intervals)
    )
    realized_value = plan["optimized_dispatch"]["economic_contribution_proxy_eur"]+actual_shift
    benchmark = hindsight["optimized_dispatch"]["economic_contribution_proxy_eur"]
    regret = benchmark-realized_value
    if regret < -COST_TOL:
        raise DispatchError("Fixed forecast schedule beats feasible perfect foresight")
    fixed = hindsight["fixed_dispatch"]["economic_contribution_proxy_eur"]
    return {
        "version":"0.9.5", "model_type":EXPERIMENT,
        "boundary":("Synthetic forecast-vs-realization *price error* comparison, "
                    "without recourse, load/weather forecast error, plant dynamics or "
                    "out-of-sample profitability evidence."),
        "forecast_planned_contribution_eur":plan["optimized_dispatch"]["economic_contribution_proxy_eur"],
        "committed_schedule_realized_contribution_eur":realized_value,
        "realized_fixed_comparator_contribution_eur":fixed,
        "realized_perfect_foresight_upper_bound_eur":benchmark,
        "perfect_foresight_regret_eur":max(0.0,regret),
        "realized_increment_over_fixed_eur":realized_value-fixed,
        "hourly_committed":plan["hourly"],
    }
