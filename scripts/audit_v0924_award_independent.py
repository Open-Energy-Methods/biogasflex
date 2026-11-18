"""Independent v0.9.24 award/meter, first-stage and physical-service audit.

Imports NO BiogasFlex optimization source. It calls the independently
implemented v0.9.22 hourly source/energy/cost auditor and the
independently written v0.9.23 next-hour gas witness auditor.

The modeled generation meter is defined as positive CHP production;
actual grid metering, import, curtailment, export losses, sales, penalties
and accepted bids are NOT independently observed in the source.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

AUDIT=module("independent_v0922", "audit_v0922_causal_independent.py")
WITNESS=module("independent_v0923", "audit_v0923_reserve_independent.py")
PROTOCOL="BIOGASFLEX_V0924_CAUSAL_HARD_15MIN_HYPOTHETICAL_ELECTRIC_AWARD_V1"
PROFILES={
    "floor_budget_0p090":.09,
    "nominal_gas_0p100":.10,
    "initial_ramp_stress_0p150":.15,
}
ETA=.4
DT=.25
GAS_FLOOR=.78
TOL=7e-5


def check(condition,reason):
    if not condition:
        raise AssertionError("INDEPENDENT_V0924_AWARD: "+reason)


def close(actual,want,reason,tol=TOL):
    check(math.isfinite(actual) and math.isfinite(want) and
          abs(actual-want)<=tol,
          f"{reason}: actual={actual!r}, expected={want!r}")


def schedule_hash(values):
    return sha256(json.dumps(values,separators=(",",":"),
                             allow_nan=False).encode("utf8")).hexdigest()


def independent_award_replay_check(states,profile,rollout,mode):
    """Check EVERY executed interval, including partial failed prefixes."""
    approved=profile["quarter_hour_export_mwh"]
    check(len(approved)==24,"Expected 24 15-minute export awards")
    check(profile["pre_reveal_award_sha256"]==schedule_hash(approved),
          "Award SHA was modified")
    check(rollout["contracted_export_mwh_total_for_entire_horizon"] is not None,
          "Full-horizon award is not declared")
    close(rollout["contracted_export_mwh_total_for_entire_horizon"],
          math.fsum(approved),"Horizon awarded MWh")
    log=rollout["hourly_observation_log"]
    rows=rollout["completed_15min_rows"]
    check(len(rows)<=24 and len(rows)%4==0,"Partial execution must end at source-hour boundary")
    check(len(log)==len(rows)//4+(0 if rollout["feasible"] else 1),
          "Infeasibility may only stop at a newly revealed hour")
    for hour,observation in enumerate(log):
        check(observation["hard_awarded_export_equalities_enforced"] is True,
              "Award equality not active during source hour")
    for t,row in enumerate(rows):
        expected=approved[t]
        check(row["quarter_index"]==t,"Execution rows out of chronological order")
        check("contract_awarded_export_mwh" in row and
              "physical_chp_export_meter_mwh" in row,
              "Accepted award or physical meter missing")
        close(row["contract_awarded_export_mwh"],expected,"Pre-reveal contract unchanged")
        physical=ETA*DT*row["gas_use_mw_lhv"]
        close(row["physical_chp_export_meter_mwh"],physical,
              "Model export meter must equal CHP generated energy")
        close(row["physical_chp_export_meter_mwh"],expected,
              "Hard awarded MWh must exactly equal generated export")
        check(row["on"]==states[t],"CHP frozen on/off decision changed")
    if rollout["feasible"]:
        check(len(rows)==24,"False complete contract service success")
        check(rollout["hard_award_service_feasible"] is True,
              "Complete service not acknowledged")
        close(rollout["executed_physical_chp_meter_export_mwh_total"],
              math.fsum(approved),"Aggregate contracted export MWh")
        close(rollout["contract_export_shortfall_mwh"],0.,
              "Completed service contains a hidden imbalance")
        check(rollout["contract_import_or_forgiveness_modeled"] is False,
              "Imaginary electric import or awarded-service forgiveness")
        check(rollout["contracted_award_is_hypothetical_not_market_settlement"] is True,
              "False claim of market-settled trade")
    else:
        check(rollout["hard_award_service_feasible"] is False,
              "Infeasible contract not declared")
        check(rollout["contracted_export_service_failure_is_explicit"] is True,
              "Infeasible award not reported")
        check(rollout["economic_contribution_eur"] is None,
              "Incomplete award falsely counted as paid earnings")
        check("executed_physical_chp_meter_export_mwh_total" not in rollout,
              "Incomplete sale incorrectly reported as full-horizon delivery")
    if mode=="award_and_reserve":
        check(rollout["next_hour_gas_reserve_viability_guard_enabled"] is True,
              "Reserve-aware policy disabled its protection")
        for h in range(len(rows)//4):
            if h>=5:
                check(log[h]["next_hour_gas_floor_viability_witness_active"] is False,
                      "Fictitious next hour after target horizon")
                continue
            WITNESS.check_next_hour_witness(states,rows,log[h],h,GAS_FLOOR)
            burned=log[h]["feasibility_witness_gas_use_mw_lhv"]
            check(len(burned)==4,"Incomplete next-hour witness award array")
            for q in range(4):
                close(ETA*DT*burned[q],approved[4*(h+1)+q],
                      "Reserve witness illegally drops contracted output")
    else:
        check(rollout["next_hour_gas_reserve_viability_guard_enabled"] is False,
              "Award-only comparator unexpectedly constrained with reserve")
    return len(rows)


def audit(source,report):
    check(report["protocol"]==PROTOCOL,"Study protocol changed")
    check(report["source_sha256"]==AUDIT.SRC_SHA==
          source["source"]["sha256"],"Publisher source SHA mismatch")
    check(report["gas_heat_proxy_empirically_calibrated"] is False,
          "Fictional site gas/heat falsely called calibrated")
    check(report["real_market_bid_or_award_verified"] is False,
          "Historical accepted bid falsely attested")
    check(report["forecast_issue_vintages_verified"] is False,
          "Historical market forecast issue-time falsely attested")
    check(report["real_electricity_meter_readings_present"] is False,
          "Model generator energy falsely called actual grid meter")
    check(report["modeled_electric_import_and_award_shortfall_slack_enabled"] is False,
          "Imaginary balancing mechanism introduced")
    check(report["published_source_is_hourly_with_four_mathematical_quarters"] is True,
          "Historical 15-minute data invented from hourly OPSD")
    check(report["gas_floor_mw_lhv"]==GAS_FLOOR,
          "Predeclared gas floor changed")
    check(set(report["award_profiles_predeclared"])==set(PROFILES),
          "Wrong preregistered synthetic award profiles")
    for key,val in PROFILES.items():
        declared=report["award_profiles_predeclared"][key]
        expectation=[val]*24
        check(declared["profile_id"]==key,"Award profile ID changed")
        check(declared["quarter_hour_export_mwh"]==expectation,
              "Ex-ante constant synthetic award secretly changed")
        close(declared["total_six_hour_export_mwh"],math.fsum(expectation),
              "Contracted six-hour MWh changed")
        check(declared["pre_reveal_award_sha256"]==schedule_hash(expectation),
              "Ex-ante award hash changed")
        check(declared["bid_is_synthetic_not_an_actual_market_award"] is True,
              "False actual market award claim")
    days=report["cases"]
    check(len(days)==report["days_evaluated"],"Study row count mismatch")
    check(report["days_evaluated"]<=report["eligible_heldout_complete_days"],
          "Too many eligible days")
    check(report["study_is_subset_smoke"]==
          (len(days)!=report["eligible_heldout_complete_days"]),
          "Completeness/smoke status incorrect")
    view=report["complete_replays_for_independent_v0922_audit"]
    # Reconstruct full source chronology, gas and heat from
    # independently frozen original evidence; also independently
    # check all emitted CHP physical balances, failed-mode termination,
    # unit switching, objective costs and terminal inventory.
    v22_certificates={}
    for key in PROFILES:
        v22_certificates[key]={}
        for mode in ("award_only","award_and_reserve"):
            v22_certificates[key][mode]=AUDIT.audit(source,view[key][mode])
    expected_names=("nominal","joint")
    lock_same=0
    executed_periods=0
    reserve_witnesses=0
    failed_policy_replays=0
    counts={key:{mode:{name:{"success":0,"terminal_matched":0}
                       for name in expected_names}
                 for mode in ("award_only","award_and_reserve")}
            for key in PROFILES}
    for case in days:
        check(case["all_award_profiles_created_before_heldout_reveal"] is True,
              "Pre-reveal award declaration absent")
        check(case["realized_gas_and_heat_are_synthetic"] is True,
              "False site telemetry claim")
        check(set(case["award_profiles"])==set(PROFILES),
              "Predefined award profiles not evaluated for this day")
        hashes=case["first_stage_policy_hashes_pre_reveal"]
        check(set(hashes)==set(expected_names),"Missing commitment policy")
        identical=hashes["nominal"]==hashes["joint"]
        check(case["first_stages_nominal_equal_joint"]==identical,
              "Commitment SHA identity flag invalid")
        lock_same+=identical
        for key in PROFILES:
            award=case["award_profiles"][key]
            declared=report["award_profiles_predeclared"][key]
            check(award["quarter_hour_export_mwh"]==
                  declared["quarter_hour_export_mwh"],
                  "Award changed after heldout day reveal")
            check(award["pre_reveal_award_sha256"]==
                  declared["pre_reveal_award_sha256"],
                  "Award hash changed at selected target date")
            check(set(award["strategies"])==set(expected_names),
                  "Missing nominal/joint contract policy")
            for name in expected_names:
                policy=award["strategies"][name]
                check(policy["first_stage_sha256_pre_reveal"]==hashes[name],
                      "Frozen first-stage hash changed between award profiles")
                states=policy["first_stage_on"]
                check(len(states)==24,"Incorrect CHP binary plan horizon")
                for mode,rollout in policy["replays"].items():
                    check(mode in ("award_only","award_and_reserve"),
                          "Unexpected contract realization mode")
                    completed=independent_award_replay_check(
                        states,award,rollout,mode)
                    executed_periods+=completed
                    if mode=="award_and_reserve":
                        reserve_witnesses+=4*min(completed//4,5)
                    if rollout["feasible"]:
                        counts[key][mode][name]["success"]+=1
                        if rollout["terminal_inventory_matches_initial_for_comparison"]:
                            counts[key][mode][name]["terminal_matched"]+=1
                    else:
                        failed_policy_replays+=1
    check(lock_same==
          report["nominal_and_joint_first_stages_identical_count"],
          "Nominal vs joint commitment identity count wrong")
    for key in PROFILES:
        for mode in counts[key]:
            for name,result in counts[key][mode].items():
                declared=report["summary_by_award_profile_and_control_mode"][key][mode][name]
                check(declared["attempted_source_days"]==len(days),
                      "Some historical dates were omitted from benchmark")
                check(result["success"]==
                      declared["complete_awarded_export_feasible_days"],
                      "Reported accepted-contract delivery count altered")
                check(len(days)-result["success"]==
                      declared["infeasible_contract_service_days"],
                      "Failed contract delivery denominator altered")
                check(result["terminal_matched"]==
                      declared["complete_contract_service_and_matched_terminal_stock_days"],
                      "Incorrect terminal-stock-matched contract count")
                check(result["success"]-result["terminal_matched"]==
                      declared["feasible_but_unmatched_terminal_stock_days"],
                      "Terminal-equivalence exclusions miscounted")
    return {
        "status":"PASS_INDEPENDENT_V0924_PRE_REVEAL_AWARDS_PHYSICAL_METER_AND_RESERVE",
        "original_publisher_source_sha256":AUDIT.SRC_SHA,
        "chronologically_eligible_days_audited":len(days),
        "modeled_15min_delivered_prefix_periods_verified":executed_periods,
        "next_hour_award_locked_witness_quarters_verified":reserve_witnesses,
        "infeasible_hypothetical_contract_policy_replays_not_monetized":
            failed_policy_replays,
        "identical_nominal_and_maximin_commitment_days":lock_same,
        "all_award_profiles_reaudited_by_independent_v0922_ledger":v22_certificates,
        "actual_market_acceptances_verified":False,
        "real_site_grid_meter_present":False,
        "actual_contract_settlement_proven":False,
        "future_realized_price_used_in_control":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--study",type=Path,required=True)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=audit(json.loads(args.source.read_text(encoding="utf8")),
                 json.loads(args.study.read_text(encoding="utf8")))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
