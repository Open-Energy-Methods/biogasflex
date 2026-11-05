"""Offline read-only v0.9.6 mixed-integer CHP verification on mock inputs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from biogasflex.baseline import Interval
from biogasflex.heat_dispatch import load_heat_case
from biogasflex.experimental_v096 import optimize_commitment_milp
from test_v096_commitment import half_grid_oracle


def close(got,want,label):
    if not math.isfinite(got) or abs(got-want)>1e-6:
        raise AssertionError(f"{label}: {got} != {want}")


def run():
    cfg,intervals=load_heat_case(ROOT/"examples/v096_commitment_toy.json",
                                ROOT/"examples/v096_commitment_toy_prices.csv")
    observed=[]
    for up in (1,2,3):
        p=dict(cfg,experimental_v096=dict(cfg["experimental_v096"],
                                       minimum_up_intervals=up))
        result=optimize_commitment_milp(p,intervals)
        oracle,_=half_grid_oracle(minimum_up=up)
        close(result["net_contribution_eur"],oracle,"independent grid oracle")
        observed.append({"minimum_up_intervals":up,
                         "net_contribution_eur":result["net_contribution_eur"],
                         "on":result["on"],"starts":result["start_count"],
                         "stops":result["stop_count"]})
    if [round(x["net_contribution_eur"],6) for x in observed]!=[55,35,15]:
        raise AssertionError("Minimum-up-time oracle mismatch")
    x=optimize_commitment_milp(cfg,intervals)
    close(x["unconstrained_LP_upper_bound_eur"],60,"relaxed LP bound")
    close(x["increment_over_feasible_fixed_eur"],40,"feasible reference uplift")
    if x["max_steady_on_ramp_violation_mw_e"]>1e-7:
        raise AssertionError("Steady-on ramp constraint broken")
    if (x["optimized_dispatch"]["max_interval_balance_residual_mwh"]>1e-8
            or x["optimized_dispatch"]["max_heat_service_residual_mwh"]>1e-8):
        raise AssertionError("Gas or heat ledger invalid")
    # Longer-horizon, intentionally synthetic MILP exercise. This does
    # not establish 24-hour solver independence or field validation.
    start=datetime(2020,1,1,tzinfo=timezone.utc)
    longer=[Interval(start+timedelta(hours=t),
                     float(0 if t<12 else 100),1.0,"SE3")
            for t in range(24)]
    p24=dict(cfg,case_id="v096_synthetic_24h_not_observed",
             experimental_v096=dict(cfg["experimental_v096"],
                                    minimum_up_intervals=2,
                                    minimum_down_intervals=2,
                                    ramp_up_mw_e_per_hour=0.2,
                                    ramp_down_mw_e_per_hour=0.2))
    long=optimize_commitment_milp(p24,longer)
    if len(long["hourly"])!=24 or long["max_steady_on_ramp_violation_mw_e"]>1e-7:
        raise AssertionError("24h commitment ramp or record count invalid")
    if long["optimized_dispatch"]["max_interval_balance_residual_mwh"]>1e-8:
        raise AssertionError("24h CHP gas conservation invalid")
    if long["optimized_dispatch"]["max_heat_service_residual_mwh"]>1e-8:
        raise AssertionError("24h CHP thermal service invalid")
    close(long["hourly"][-1]["stock_end_mwh_lhv"],0,"24h cyclic gas stock")
    return {"version":"0.9.6","status":"PASS",
            "scope":"explicitly synthetic; no observed CHP start/stop data",
            "minimum_up_oracles":observed,
            "max_ramp_violation_mw_e":x["max_steady_on_ramp_violation_mw_e"],
            "unconstrained_LP_upper_bound_eur":x["unconstrained_LP_upper_bound_eur"],
            "reference_feasible":x["fixed_reference_feasible"],
            "synthetic_24h_intervals":len(long["hourly"]),
            "synthetic_24h_minimum_up_intervals":2,
            "synthetic_24h_minimum_down_intervals":2,
            "synthetic_24h_steady_ramp_violation_mw_e":long["max_steady_on_ramp_violation_mw_e"],
            "synthetic_24h_gas_balance_residual_mwh":long["optimized_dispatch"]["max_interval_balance_residual_mwh"],
            "independent_oracle":"exhaustive 0.5-MW_LHV grid on this special 3-interval instance"}


if __name__=="__main__":
    try:
        print(json.dumps(run(),indent=2,allow_nan=False))
    except (AssertionError,ValueError,RuntimeError) as error:
        raise SystemExit(f"v0.9.6 AUDIT FAILED: {error}")
