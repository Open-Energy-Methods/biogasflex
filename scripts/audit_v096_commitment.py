"""Offline read-only v0.9.6 mixed-integer CHP verification on mock inputs."""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
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
    return {"version":"0.9.6","status":"PASS",
            "scope":"explicitly synthetic; no observed CHP start/stop data",
            "minimum_up_oracles":observed,
            "max_ramp_violation_mw_e":x["max_steady_on_ramp_violation_mw_e"],
            "unconstrained_LP_upper_bound_eur":x["unconstrained_LP_upper_bound_eur"],
            "reference_feasible":x["fixed_reference_feasible"],
            "independent_oracle":"exhaustive 0.5-MW_LHV grid on this special 3-interval instance"}


if __name__=="__main__":
    try:
        print(json.dumps(run(),indent=2,allow_nan=False))
    except (AssertionError,ValueError,RuntimeError) as error:
        raise SystemExit(f"v0.9.6 AUDIT FAILED: {error}")
