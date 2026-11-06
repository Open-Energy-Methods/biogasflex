"""Independent synthetic v0.9.8.1 corrective maintenance regression audit.

Exact hand-derived conservation checks; no historical research data changed.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
sys.path.insert(0,str(ROOT/"tests"))
from biogasflex.experimental_v098 import optimize_commitment_milp, evaluate_rolling_prices
from test_v098_rolling import config, times, snapshots


def approx(x,expected,label):
    if not math.isfinite(x) or abs(x-expected)>1e-7:
        raise AssertionError(f"{label}: expected {expected}, found {x}")


def audit():
    # Analytical first-hour power ramp: initial output .2 MW_e, expected
    # .4 MW_e from 1MW_LHV fixed fuel, true observation age 2h, ramp
    # .1MW_e/h. Available change .25MW_e > .2MW_e.
    c=config(n=1,gas_storage_capacity_mwh_lhv=0.0)
    c["experimental_v098"]={**c["experimental_v098"],
        "initial_power_mw_e":0.2,
        "initial_power_observation_age_hours":2.0,
        "ramp_up_mw_e_per_hour":0.1,
        "ramp_down_mw_e_per_hour":0.1}
    realized=times([100])
    first=evaluate_rolling_prices(c,realized,snapshots(realized,[[100]]))
    approx(first["rolling_realized_contribution_eur"],40,"Initial-age carried contribution")
    approx(first["perfect_foresight_regret_eur"],0,"Initial-age one-slot regret")

    # Analytical two-slot gas balance: production 3/1 MW_LHV; rating
    # .8 MW_e and eta_e=.4. Fixed first slot would require 1.2 MW_e
    # (unrated). Flexible operation stores 1 MWh_LHV (u0=2) and
    # consumes stock next slot (u1=2) with 0 stock at global end.
    c2=config(n=2,gas_production_mw_lhv=[3.0,1.0],
              gas_storage_capacity_mwh_lhv=1.0)
    a2=times([20,50])
    revised=evaluate_rolling_prices(c2,a2,snapshots(a2,[[20,50],[50]]))
    approx(revised["rolling_realized_contribution_eur"],56,"Flexible two-slot EUR")
    approx(revised["perfect_foresight_regret_eur"],0,"Flexible two-slot regret")
    if revised["rolling_fixed_reference_feasible"]:
        raise AssertionError("Infeasible nameplate fixed reference mislabelled feasible")
    if (revised["realized_original_fixed_reference_net_eur"] is not None or
        revised["rolling_gain_over_feasible_fixed_eur"] is not None):
        raise AssertionError("Nonexistent fixed reference must be null, not invented")
    r2=optimize_commitment_milp(c2,a2)
    if r2["fixed_reference_status"]!="PHYSICALLY_INFEASIBLE":
        raise AssertionError("Invalid fixed-reference status")
    if abs(revised["realized_physical_and_contribution_ledger"]["full_horizon_gas_residual_mwh"])>1e-7:
        raise AssertionError("Flexible gas conservation failed")
    return {
        "status":"PASS","package_release":"0.9.8.1",
        "scope":"Entirely synthetic solver/rolling state maintenance, not CHP hardware validation",
        "declared_initial_power_age_hours":2.0,
        "initial_age_carried_one_slot_eur":first["rolling_realized_contribution_eur"],
        "fixed_nameplate_excess_mw_e":0.4,
        "flexible_two_slot_contribution_eur":revised["rolling_realized_contribution_eur"],
        "two_slot_fixed_reference_status":r2["fixed_reference_status"],
        "gas_balance_residual_mwh":
            revised["realized_physical_and_contribution_ledger"]["full_horizon_gas_residual_mwh"],
        "original_frozen_inputs_and_results_modified":False,
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (AssertionError,ValueError,RuntimeError) as error:
        raise SystemExit(f"V0981 MAINTENANCE AUDIT FAIL: {error}")
