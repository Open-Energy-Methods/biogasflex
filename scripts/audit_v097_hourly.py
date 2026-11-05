"""v0.9.7 offline solver-independent fractional-hour stress, research files read-only."""
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
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v097 import optimize_commitment_milp
from biogasflex.heat_dispatch import load_heat_case
from test_v097_hourly import oracle_two_slot


def almost(got, expected, msg):
    if not math.isfinite(got) or abs(got-expected)>2e-6:
        raise AssertionError(f"{msg}: {got} != {expected}")


def audit():
    cfg,intervals=load_heat_case(
        ROOT/"examples/v097_fractional_hour_config.json",
        ROOT/"examples/v097_fractional_hour_prices.csv"
    )
    results=[]
    for dwell,expected in ((0.25,45.0),(1.0,45.0),(1.01,40.0)):
        c={**cfg,"experimental_v097":{
            **cfg["experimental_v097"],"minimum_up_hours":dwell}}
        solved=optimize_commitment_milp(c,intervals)
        target,_=oracle_two_slot(minimum_up=dwell)
        almost(target,expected,"independent binary and storage oracle")
        almost(solved["net_contribution_eur"],target,"HiGHS MILP vs independent oracle")
        results.append({"minimum_up_hours":dwell,
                        "net_contribution_eur":solved["net_contribution_eur"],
                        "on":solved["on"]})
    forbidden={**cfg,"experimental_v097":{
        **cfg["experimental_v097"],"minimum_up_hours":1.26}}
    try:
        optimize_commitment_milp(forbidden,intervals)
    except DispatchError:
        pass
    else:
        raise AssertionError("Invalid over-horizon startup was accepted")

    carried={**cfg,"experimental_v097":{
        **cfg["experimental_v097"],"initial_remaining_dwell_hours":0.25}}
    carried_plan=optimize_commitment_milp(carried,intervals)
    if carried_plan["on"]!=[0,1]:
        raise AssertionError("Carry-in OFF obligation leaked across first quarter-hour")

    # Mixed-resolution synthetic 24-hour stress, not an observed market day:
    # 16 quarter-hour slots plus 20 hourly slots = 24h / 36 decisions.
    dt=[0.25]*16+[1.0]*20
    cur=datetime(2020,1,1,tzinfo=timezone.utc)
    day=[]
    for i,d in enumerate(dt):
        day.append(Interval(cur,float(0 if i<20 else 100),d,"SE3"))
        cur+=timedelta(hours=d)
    params={**cfg,"case_id":"v097_synthetic_24h_36_slot_mixed",
            "gas_storage_capacity_mwh_lhv":0.5,
            "experimental_v097":{
                **cfg["experimental_v097"],
                "minimum_up_hours":1.25,
                "minimum_down_hours":0.75,
                "ramp_up_mw_e_per_hour":0.2,
                "ramp_down_mw_e_per_hour":0.2,
            }}
    long=optimize_commitment_milp(params,day)
    almost(long["clock_hours_from_horizon_start"][-1],24.0,
           "mixed-resolution total hours")
    almost(long["optimized_dispatch"]["full_horizon_gas_residual_mwh"],0.0,
           "24h independent ledger gas conservation")
    if (long["max_steady_on_ramp_violation_mw_e"]>1e-7 or
        long["optimized_dispatch"]["max_interval_balance_residual_mwh"]>1e-8 or
        long["optimized_dispatch"]["max_heat_service_residual_mwh"]>1e-8):
        raise AssertionError("Mixed-resolution gas, heat or steady ramp validation failed")
    if len(long["on"])!=36 or len(long["clock_hours_from_horizon_start"])!=37:
        raise AssertionError("Unexpected mixed-resolution time geometry")

    return {"status":"PASS","version":"0.9.7",
            "scope":"synthetic exact two-slot binary stock oracle, plus mixed-resolution 24h stress",
            "two_slot_analytical_eur":results,
            "initial_off_residual_on_flags":carried_plan["on"],
            "late_start_feasibility":"REJECTED",
            "synthetic_day_hours":24.0,
            "synthetic_day_intervals":36,
            "synthetic_day_max_gas_balance_mwh":long["optimized_dispatch"]["max_interval_balance_residual_mwh"],
            "synthetic_day_max_steady_ramp_mw_e":long["max_steady_on_ramp_violation_mw_e"],
            "original_scientific_data_modified":False}


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (ValueError,RuntimeError,AssertionError) as exc:
        raise SystemExit(f"V097 TIME-BASED COMMITMENT AUDIT FAILED: {exc}")
