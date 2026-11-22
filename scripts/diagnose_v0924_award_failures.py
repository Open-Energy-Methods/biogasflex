"""Independent deterministic diagnosis of v0.9.24 contract replay failures.

A hard awarded-export equality fixes CHP burn exactly: u=A/(eta_e*dt).
Thus the 4-slot current-hour physical feasibility and the contract-coupled
next-hour low-gas witness can be independently recomputed with arithmetic,
without any SciPy optimizer or imports from the BiogasFlex package.
This diagnosis identifies MODEL constraint groups, not field plant causes.

Classification precedence:
  (1) currently observed hour physically infeasible;
  (2) current feasible but predeclared next-hour lower-gas witness infeasible;
  (3) current & witness feasible, but remaining NOMINAL forecast path infeasible.
If the reported LP is infeasible and all three are feasible, reject the
study as unexplained rather than invent a root cause.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from math import isfinite
from pathlib import Path

ETA_E=.4
ETA_H=.2
DT=.25
CAP=1.5
ON_MIN_BURN=.5
ON_MAX_BURN=2.
RAMP=.8
BACKUP=.20
DUMP=.40
INITIAL_STOCK=.75
INITIAL_POWER=.4
INITIAL_ON=1
FLOOR=.78
TOL=7e-5
PROTOCOL="BIOGASFLEX_V0924_CAUSAL_HARD_15MIN_HYPOTHETICAL_ELECTRIC_AWARD_V1"


def demand(ok,reason):
    if not ok:
        raise AssertionError("INDEPENDENT_V0924_FAILURE_DIAGNOSIS: "+reason)


def quarter_hour_path(*, first_slot:int, starting_stock:float,
                      starting_power:float, previous_on:int,
                      on:list[int], awards:list[float], gas_rate:float,
                      heat_rate:float)->dict:
    """Reconstruct precisely one fixed-award source hour, no optimizer.

    Negative inventory and overfull storage are NOT permitted;
    for diagnostic purposes, the full provisional numeric sequence is
    computed and each independent violation category is recorded.
    """
    demand(0<=first_slot<=20 and first_slot%4==0,
           "Wrong chronological source hour")
    demand(len(on)==len(awards)==4 and previous_on in (0,1)
           and all(x in (0,1) for x in on),
           "Bad frozen binary first-stage/on pattern")
    demand(all(isfinite(v) for v in [starting_stock,starting_power,gas_rate,heat_rate]
               +awards),"Nonfinite model input")
    violations=set()
    stock=float(starting_stock)
    power=float(starting_power)
    old_on=previous_on
    rows=[]
    for q in range(4):
        global_t=first_slot+q
        u=awards[q]/(ETA_E*DT)
        new_power=ETA_E*u
        if (on[q] and not (ON_MIN_BURN-TOL<=u<=ON_MAX_BURN+TOL)) or (
             not on[q] and not (-TOL<=u<=TOL)):
            violations.add("frozen_binary_or_fuel_rating")
        if old_on==on[q]==1:
            allowed=RAMP*(DT/2 if global_t==0 else DT)
            if abs(new_power-power)>allowed+TOL:
                violations.add("consecutive_ON_electrical_ramp")
        stock+=DT*(gas_rate-u)
        if stock < -TOL:
            violations.add("negative_gas_buffer_inventory")
        if stock > CAP+TOL:
            violations.add("gas_buffer_upper_capacity")
        # Existence of 0<=useful<=min(thermal_output, demand)
        # such that backup=demand-useful<=.20 and dump=output-useful<=.40.
        chp_heat=ETA_H*u
        lo=max(0.,heat_rate-BACKUP,chp_heat-DUMP)
        hi=min(heat_rate,chp_heat)
        if lo>hi+TOL:
            violations.add("heat_backup_or_dump_capacity")
        rows.append({"quarter_global_index":global_t,"fuel_burn_mw_lhv":u,
                     "end_gas_inventory_mwh_lhv":stock,
                     "meter_export_mwh":new_power*DT})
        power=new_power
        old_on=on[q]
    return {
        "feasible":not violations,
        "violations":sorted(violations),
        "end_stock_mwh_lhv":stock,
        "end_power_mw_e":power,
        "end_on":old_on,
        "rows":rows,
    }


def evaluate_failure(report, row, profile, policy, mode):
    """Reproduce one reported LP failure with the record's available information."""
    replay=policy["replays"][mode]
    demand(not replay["feasible"],"Only failures may be classified")
    h=replay["failed_hour"]
    demand(0<=h<6,"Impossible first failed source hour")
    observed=replay["hourly_observation_log"]
    past=replay["completed_15min_rows"]
    demand(len(past)==4*h and len(observed)==h+1,
           "Failed replay observations and completed prefix inconsistent")
    source=observed[-1]
    demand(source["hour_index"]==h,"Newly revealed source hour not logged")
    states=policy["first_stage_on"]
    awards=profile["quarter_hour_export_mwh"]
    demand(len(states)==len(awards)==24,"Invalid known award/commitment horizon")
    begin=h*4
    stock=past[-1]["stock_end_mwh_lhv"] if past else INITIAL_STOCK
    power=ETA_E*past[-1]["gas_use_mw_lhv"] if past else INITIAL_POWER
    previous_on=past[-1]["on"] if past else INITIAL_ON

    current=quarter_hour_path(
        first_slot=begin,starting_stock=stock,
        starting_power=power,previous_on=previous_on,
        on=states[begin:begin+4],awards=awards[begin:begin+4],
        gas_rate=source["synthetic_gas_rate_observed_at_hour_start_mw_lhv"],
        heat_rate=source["synthetic_heat_load_observed_at_hour_start_mw_th"])
    next_guard=None
    forecast=[]
    if current["feasible"]:
        if mode=="award_and_reserve" and h<5:
            next_guard=quarter_hour_path(
                first_slot=begin+4,
                starting_stock=current["end_stock_mwh_lhv"],
                starting_power=current["end_power_mw_e"],
                previous_on=current["end_on"],
                on=states[begin+4:begin+8],
                awards=awards[begin+4:begin+8],
                gas_rate=FLOOR,
                heat_rate=.195)
        stock_f=current["end_stock_mwh_lhv"]
        power_f=current["end_power_mw_e"]
        prev_on_f=current["end_on"]
        for k in range(h+1,6):
            t=k*4
            part=quarter_hour_path(
                first_slot=t,starting_stock=stock_f,
                starting_power=power_f,previous_on=prev_on_f,
                on=states[t:t+4],awards=awards[t:t+4],
                gas_rate=1.0,heat_rate=.15)
            forecast.append({"future_hour_index":k,
                             "nominal_forecast_feasible":part["feasible"],
                             "violations":part["violations"]})
            if not part["feasible"]:
                break
            stock_f=part["end_stock_mwh_lhv"]
            power_f=part["end_power_mw_e"]
            prev_on_f=part["end_on"]
    if not current["feasible"]:
        category="observed_current_hour_physical_infeasibility"
        groups=current["violations"]
    elif next_guard is not None and not next_guard["feasible"]:
        category="next_hour_min_gas_guard_rejects_fixed_award"
        groups=next_guard["violations"]
    elif any(not x["nominal_forecast_feasible"] for x in forecast):
        category="future_unobserved_nominal_forecast_constraints_infeasible"
        groups=next(x["violations"] for x in forecast
                    if not x["nominal_forecast_feasible"])
    else:
        raise AssertionError("INDEPENDENT_V0924_FAILURE_DIAGNOSIS: "
                             "Optimizer claims infeasibility but observed current-hour, "
                             "predeclared reserve and nominal future are all feasible")
    return {"day_utc":row["day_utc"],
            "award_profile":profile["profile_id"],
            "policy":policy["name"],
            "mode":mode,
            "failed_hour":h,
            "classification":category,
            "first_detected_constraint_groups":groups,
            "current_hour_violations":current["violations"],
            "next_hour_gas_floor_witness_violations":
                next_guard["violations"] if next_guard is not None else None,
            "future_nominal_forecast_check":forecast}


def diagnose(report):
    demand(report["protocol"]==PROTOCOL,"Wrong v0.9.24 study")
    demand(report["days_evaluated"]==len(report["cases"]),"Missing study dates")
    counts=Counter()
    by_profile={}
    failures=[]
    for day in report["cases"]:
        for key,profile in day["award_profiles"].items():
            for name,policy in profile["strategies"].items():
                for mode,replay in policy["replays"].items():
                    if replay["feasible"]:
                        continue
                    description=evaluate_failure(
                        report,day,profile,{**policy,"name":name},mode)
                    failures.append(description)
                    countkey=(key,mode,name)
                    counts[countkey]+=1
                    by_profile.setdefault(key,{}).setdefault(mode,Counter())[
                        description["classification"]]+=1
    for key,profiles in report["summary_by_award_profile_and_control_mode"].items():
        for mode,policies in profiles.items():
            for name,p in policies.items():
                demand(counts[(key,mode,name)]==
                       p["infeasible_contract_service_days"],
                       "Failure classification does not match complete denominator")
    return {
        "status":"PASS_INDEPENDENT_V0924_REPORTED_FAILURES_DETERMINISTICALLY_RECONSTRUCTED",
        "source_year":2019,
        "source_heldout_days_audited":len(report["cases"]),
        "failed_policy_replays_classified":len(failures),
        "categories_by_award_profile_mode":{
            profile:{mode:dict(tally) for mode,tally in modes.items()}
            for profile,modes in by_profile.items()},
        "all_failed_ledger_paths_explicitly_classified":True,
        "actual_site_gas_or_heat_measurements_present":False,
        "actual_market_settlement_proven":False,
        "forecast_future_violations_are_predictions_not_measured_future":True,
        "per_failure_records":failures,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--study",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=diagnose(json.loads(args.study.read_text(encoding="utf8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps({key:value for key,value in result.items()
                      if key!="per_failure_records"},indent=2))


if __name__=="__main__":
    main()
