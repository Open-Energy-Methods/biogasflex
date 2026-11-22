"""Independent source-backed v0.9.23 one-hour reserve-witness certificate.

Uses Python standard library + the unmodified v0.9.22 independent auditor
WITHOUT importing biogasflex. Verifies actual executed reserve witness
variables and constraints, commitment hashes, source provenance, physical
ledgers and equal-terminal-stock paired economic differences.

It certifies ONLY one-hour lower-gas existential feasibility, not robust
control under every possible future path, real gas procurement or site physics.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path

HERE=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location(
    "v0922_independent_physical_ledger",
    HERE/"audit_v0922_causal_independent.py")
AUDIT=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)

EXPECTED="BIOGASFLEX_V0923_NEXT_HOUR_MIN_SYNTHETIC_GAS_NONANTICIPATIVE_RESERVE_V1"
DT=.25
ET=.4
RAMP=.8
CAP=1.5
TOL=7e-5


def require(ok,why):
    if not ok:
        raise AssertionError("Independent v0.9.23 reserve audit: "+why)


def close(a,b,label):
    require(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=TOL,
            label+f": {a!r} != {b!r}")


def check_next_hour_witness(states,completed_rows,observation,hour,floor):
    """Current-end commitment/power/stock shared with distinct next-hour witness."""
    require(hour in range(5),"No next source hour")
    require(observation["next_hour_gas_floor_viability_witness_active"] is True,
            "Expected nonanticipative next-hour witness")
    close(observation["predeclared_next_hour_synthetic_gas_floor_mw_lhv"],
          floor,"Bound changed after source reveal")
    f=observation["feasibility_witness_gas_use_mw_lhv"]
    s=observation["feasibility_witness_stock_end_mwh_lhv"]
    require(isinstance(f,list) and len(f)==4 and
            isinstance(s,list) and len(s)==4,
            "Missing four-step gas/stock witness")
    prior=completed_rows[4*hour+3]
    stock=prior["stock_end_mwh_lhv"]
    last_power=ET*prior["gas_use_mw_lhv"]
    prior_on=states[4*hour+3]
    for q in range(4):
        next_on=states[4*(hour+1)+q]
        u=f[q]
        require(-TOL<=stock<=CAP+TOL,"Initial witness stock outside bounds")
        require((.5-TOL<=u<=2.+TOL) if next_on else
                (-TOL<=u<=TOL),"Witness does not respect frozen CHP on/off")
        next_stock=stock+DT*(floor-u)
        close(next_stock,s[q],"Next-hour worst-gas mass balance")
        require(-TOL<=next_stock<=CAP+TOL,
                "Next-hour witness leaves gas buffer bounds")
        power=ET*u
        if prior_on==next_on==1:
            require(abs(power-last_power)<=RAMP*DT+TOL,
                    "Witness violates original electric ON/ON ramp")
        prior_on=next_on
        last_power=power
        stock=next_stock
    return True


def metrics(cases,name):
    x=[case["policies"][name] for case in cases]
    out={}
    for mode in ("unprotected","protected"):
        data=[v[mode] for v in x]
        out[mode]={
            "days":len(data),
            "causal_full_horizon_feasible_days":sum(z["feasible"] for z in data),
            "causal_full_horizon_infeasible_days":sum(not z["feasible"] for z in data),
            "terminal_stock_unmatched_despite_feasible":
                sum(z["feasible"] and not
                    z["terminal_inventory_matches_initial_for_comparison"] for z in data),
            "complete_and_terminal_matched_days":
                sum(z["feasible"] and
                    z["terminal_inventory_matches_initial_for_comparison"] for z in data),
        }
    days=[]
    for row in x:
        a,b=row["unprotected"],row["protected"]
        if (a["feasible"] and b["feasible"] and
            a["terminal_inventory_matches_initial_for_comparison"] and
            b["terminal_inventory_matches_initial_for_comparison"]):
            days.append(b["economic_contribution_eur"]-a["economic_contribution_eur"])
    return {
        "unprotected":out["unprotected"],
        "protected":out["protected"],
        "rescued_infeasible_replay_days_feasible_under_protection":
            sum(not v["unprotected"]["feasible"] and
                v["protected"]["feasible"] for v in x),
        "new_infeasibility_under_protection_days":
            sum(v["unprotected"]["feasible"] and
                not v["protected"]["feasible"] for v in x),
        "strict_matched_service_days_with_both_controllers_and_same_binary":
            len(days),
        "protected_minus_unprotected_contribution_eur_matched_only":days,
        "average_matched_economic_change_eur_not_population_mean":
            math.fsum(days)/len(days) if days else None,
    }


def audit(source,report):
    require(report["protocol"]==EXPECTED,"Wrong study protocol")
    require(report["source_sha256"]==AUDIT.SRC_SHA==
            source["source"]["sha256"],"Source hash changed")
    require(report["plant_gas_arrival_physically_validated"] is False,
            "Fictional gas supply presented as measured")
    require(report["market_accepted_electric_award_enforced"] is False,
            "No actual accepted award evidence")
    require(report["original_price_forecast_vintage_verified"] is False,
            "Price vintage falsely attested")
    require(report["training_only_estimated_gas_bound"] is False,
            "Synthetic hardclip falsely called statistical training")
    floor=report["predeclared_guard_synthetic_floor_mw_lhv"]
    require(0<=floor<=.78+1e-12,
            "Chosen lower bound exceeds known synthetic model global support")
    require(report["synthetic_gas_lower_clip_mw_lhv"]==.78,
            "Original synthetic gas minimum changed")
    require(report["days_evaluated"]==len(report["cases"]),"Study size mismatch")
    require(report["eligible_full_holdout_days"]>=len(report["cases"]),
            "Subset count exceeds population")
    require(report["entire_heldout_selected_ex_ante"]==
            (report["days_evaluated"]==report["eligible_full_holdout_days"]),
            "Full study / subset flag invalid")
    views=report["views_for_independent_v0922_ledger_audit"]
    source_audits={}
    for mode in ("unprotected","protected"):
        # Independent full physical/financial/chronological reconstruction,
        # with no import of project optimization model code.
        source_audits[mode]=AUDIT.audit(source,views[mode])
    witness_count=0
    unprotected_and_protected_common=0
    for case in report["cases"]:
        require(case["gas_arrival_floor_condition_met_on_realized_synthetic_hours"],
                "Claimed global lower bound violated by realized synthetic source path")
        require(case["first_stage_sha256_identical_nominal_and_joint"]==
                (case["policies"]["nominal"]["first_stage_sha256_pre_reveal"]==
                 case["policies"]["joint"]["first_stage_sha256_pre_reveal"]),
                "First-stage identity indication forged")
        for name in ("nominal","joint"):
            state=case["policies"][name]
            guarded=state["protected"]
            raw=state["unprotected"]
            require(raw["next_hour_gas_reserve_viability_guard_enabled"] is False,
                    "Original unprotected controller unexpectedly modified")
            require(guarded["next_hour_gas_reserve_viability_guard_enabled"] is True,
                    "Protected strategy omits its safety guard")
            obs=guarded["hourly_observation_log"]
            rows=guarded["completed_15min_rows"]
            require(len(rows)%4==0,"Only complete source-hours executable")
            for hour in range(len(rows)//4):
                if hour<5:
                    check_next_hour_witness(
                        state["first_stage_on"],rows,obs[hour],hour,floor)
                    witness_count+=1
                else:
                    require(obs[hour]["next_hour_gas_floor_viability_witness_active"] is False,
                            "Fake next hour after six-hour horizon")
            # Both controllers must have exactly identical frozen binary
            # commitments; this comparison isolates continuous safety control.
            if raw["feasible"] and guarded["feasible"]:
                require(len(raw["completed_15min_rows"])==
                        len(guarded["completed_15min_rows"])==24,
                        "Incorrect full-service day flag")
            if raw["feasible"] and guarded["feasible"] and (
                raw["terminal_inventory_matches_initial_for_comparison"] and
                guarded["terminal_inventory_matches_initial_for_comparison"]):
                unprotected_and_protected_common+=1
    for name in ("nominal","joint"):
        got=metrics(report["cases"],name)
        stated=report[name+"_policy"]
        for key in ("unprotected","protected"):
            require(got[key]==stated[key],
                    "Per-policy "+key+" feasibility metrics changed")
        for key in ("rescued_infeasible_replay_days_feasible_under_protection",
                    "new_infeasibility_under_protection_days",
                    "strict_matched_service_days_with_both_controllers_and_same_binary"):
            require(got[key]==stated[key], "Viability comparison count forged: "+key)
        got_dif=got["protected_minus_unprotected_contribution_eur_matched_only"]
        report_dif=stated["protected_minus_unprotected_contribution_eur_matched_only"]
        require(len(got_dif)==len(report_dif),"Model contribution pair-count mismatch")
        for a,b in zip(got_dif,report_dif):
            close(a,b,"Matched 6-hour contribution")
        if got_dif:
            close(got["average_matched_economic_change_eur_not_population_mean"],
                  stated["average_matched_economic_change_eur_not_population_mean"],
                  "Mean over strictly matched service")
        else:
            require(stated["average_matched_economic_change_eur_not_population_mean"]
                    is None,"Invented comparison with no matches")
    identity=sum(x["first_stage_sha256_identical_nominal_and_joint"]
                 for x in report["cases"])
    require(identity==report["first_stages_identical_nominal_joint_days"],
            "Policy identity count changed")
    return {
        "status":"PASS_INDEPENDENT_V0923_CAUSAL_LOWER_GAS_WITNESS_AND_PHYSICAL_LEDGER",
        "source_original_publisher_sha256":AUDIT.SRC_SHA,
        "eligible_holdout_days":report["eligible_full_holdout_days"],
        "days_evaluated":len(report["cases"]),
        "current_to_next_hour_witnesses_verified":witness_count,
        "first_stages_nominal_equals_joint_days":identity,
        "nominal_unprotected_full_horizon_feasible":
            report["nominal_policy"]["unprotected"]["causal_full_horizon_feasible_days"],
        "nominal_protected_full_horizon_feasible":
            report["nominal_policy"]["protected"]["causal_full_horizon_feasible_days"],
        "nominal_rescued_days":report["nominal_policy"]
            ["rescued_infeasible_replay_days_feasible_under_protection"],
        "joint_rescued_days":report["joint_policy"]
            ["rescued_infeasible_replay_days_feasible_under_protection"],
        "source_independent_v0922_reaudits":source_audits,
        "heldout_gas_and_heat_are_synthetic":True,
        "historical_forecast_gate_vintage_authenticated":False,
        "robust_all_future_realizations_guarantee":False,
        "physical_plant_reliability_proven":False,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--study",type=Path,required=True)
    p.add_argument("--output",type=Path,required=False)
    args=p.parse_args()
    result=audit(json.loads(args.source.read_text(encoding="utf8")),
                 json.loads(args.study.read_text(encoding="utf8")))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",
                               encoding="utf8")
    print(json.dumps(result,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
