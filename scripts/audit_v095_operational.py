"""Deterministic, analytically checkable v0.9.5 operating/price stress gate.

Only made-up input assumptions are used, never observational measurements.
Read-only runner: never writes into original results or scientific sources.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from biogasflex.baseline import Interval
from biogasflex.experimental_v095 import (
    optimize_operating_surrogate, evaluate_fixed_forecast_schedule,
)
from biogasflex.heat_dispatch import load_heat_case


def _close(actual, expected, claim):
    if not math.isclose(actual, expected, rel_tol=0, abs_tol=1e-6):
        raise AssertionError(f"{claim}: got {actual!r}, expected {expected!r}")


def audit():
    cfg, actual = load_heat_case(ROOT/"examples/v095_toy_config.json",
                                 ROOT/"examples/v095_toy_realized_prices.csv")
    _, forecast = load_heat_case(ROOT/"examples/v095_toy_config.json",
                                 ROOT/"examples/v095_toy_forecast_prices.csv")
    ramps = []
    for limit in (0.0,0.05,0.1,0.2,100.0):
        c = {**cfg, "experimental_v095":{
            **cfg["experimental_v095"],
            "ramp_up_mw_e_per_hour":limit,
            "ramp_down_mw_e_per_hour":limit,
        }}
        r = optimize_operating_surrogate(c, actual)
        ramps.append(r["incremental_contribution_eur"])
    for a,b in zip(ramps, ramps[1:]):
        if b < a-1e-7:
            raise AssertionError("Relaxed ramp reduced optimum (feasible-set inclusion)")
    _close(ramps[0],0.0,"zero-ramp oracle")
    _close(ramps[2],5.0,"0.1 MW_e per h analytical oracle")
    _close(ramps[4],20.0,"unconstrained surrogate")
    minimum_floor_values = []
    for floor in (0.0,0.2,0.36):
        c = {**cfg, "experimental_v095":{
            **cfg["experimental_v095"],
            "ramp_up_mw_e_per_hour":100.0,
            "ramp_down_mw_e_per_hour":100.0,
            "minimum_power_mw_e":floor,
        }}
        value = optimize_operating_surrogate(c, actual)
        minimum_floor_values.append(value["incremental_contribution_eur"])
    for a,b in zip(minimum_floor_values, minimum_floor_values[1:]):
        if b > a+1e-7:
            raise AssertionError("Tightened always-on minimum increased optimum")
    _close(minimum_floor_values[-1],4.0,"0.36 MW_e always-on floor")
    c = {**cfg, "experimental_v095":{
        **cfg["experimental_v095"],
        "ramp_up_mw_e_per_hour":100.0,
        "ramp_down_mw_e_per_hour":100.0,
    }}
    price_error = evaluate_fixed_forecast_schedule(c,forecast,actual)
    _close(price_error["perfect_foresight_regret_eur"],40.0,
           "reversed synthetic price forecast regret")
    _close(price_error["realized_increment_over_fixed_eur"],-20.0,
           "adversarial forecast can underperform fixed generation")

    # A second, longer 24-h synthetic operating stress checks the
    # midpoint ramp rows and noncyclic internal inventory (cyclic endpoint).
    start = datetime(2020,1,1,tzinfo=timezone.utc)
    horizon = [Interval(start+timedelta(hours=t),
                        float(0 if t<12 else 100),1.0,"SE3")
               for t in range(24)]
    long = optimize_operating_surrogate({**cfg,"case_id":"v095_synthetic_24h"}, horizon)
    if long["max_ramp_violation_mw_e"]>1e-7:
        raise AssertionError("24h ramp inequality violated")
    if long["optimized_dispatch"]["max_interval_balance_residual_mwh"]>1e-8:
        raise AssertionError("24h gas inventory conservation violation")
    return {
        "version":"0.9.5",
        "status":"PASS",
        "source":"entirely synthetic examples, NOT actual CHP/market time series",
        "ramp_monotonicity_points":len(ramps),
        "ramp_increment_eur":ramps,
        "minimum_floor_monotonicity_points":len(minimum_floor_values),
        "minimum_floor_increment_eur":minimum_floor_values,
        "price_forecast_regret_eur":price_error["perfect_foresight_regret_eur"],
        "forecast_increment_over_fixed_eur":price_error["realized_increment_over_fixed_eur"],
        "long_horizon_interval_count":len(long["hourly"]),
        "long_horizon_ramp_violation_mw_e":long["max_ramp_violation_mw_e"],
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (ValueError, AssertionError, RuntimeError) as exc:
        raise SystemExit(f"V095 EXPERIMENTAL AUDIT FAILED: {exc}")
