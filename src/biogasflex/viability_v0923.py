"""v0.9.23: explicitly hypothetical precommitted gas-reserve viability study.

Compares the v0.9.22 *same frozen first-stage CHP commitments* under two
hour-causal controllers: original soft terminal-stock planning vs a new LP
that requires the just-planned current hour to admit a feasible NEXT source
hour at the declared minimum synthetic gas supply. The witness has distinct
future dispatch but shares current-hour controls, stock and power.

IMPORTANT: a single minimum-gas one-hour witness is NOT a robust viability
certificate for all future realization paths, gas overproduction, pressure
physics, true historical forecast vintages or grid awards. The model lower
bound is a KNOWN ARTIFICIAL clip in v0.9.21, not a gas-supply contract.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
import math
from pathlib import Path

from . import causal_v0922 as c22
from . import joint_v0921 as j

PROTOCOL="BIOGASFLEX_V0923_NEXT_HOUR_MIN_SYNTHETIC_GAS_NONANTICIPATIVE_RESERVE_V1"
DEFAULT_SYNTHETIC_FLOOR_MW_LHV=.78


def require(ok, message):
    if not ok:
        raise ValueError("v0.9.23 protected stock replay: "+message)


def _build_compatible_view(source: dict, entries: list[dict],
                           *, mode: str, eligible_count: int,
                           excluded: list[dict]) -> dict:
    """Return a complete v0.9.22 ledger-auditable structure, one per mode.

    The independent historical/physical auditor expects v0.9.22's frozen
    source and full per-interval ledger shape; we do not alter that auditor.
    """
    cases=[]
    for entry in entries:
        comparisons={}
        for name in ("nominal","joint"):
            policy=entry["policies"][name]
            rollout=policy[mode]
            comparisons[name]={
                "first_stage_sha256_pre_reveal":policy["first_stage_sha256_pre_reveal"],
                "first_stage_on":policy["first_stage_on"],
                "first_stage_starts":policy["first_stage_starts"],
                "first_stage_stops":policy["first_stage_stops"],
                "causal_hourly_observation_replay":rollout,
                "same_binary_full_future_recourse_upper_bound_eur":
                    policy["hindsight_upper_bound_eur"],
                "same_binary_hindsight_feasible":policy["hindsight_feasible"],
            }
        cases.append({
            "heldout_day_utc":entry["day_utc"],
            "heldout_ordinal":entry["heldout_ordinal"],
            "nominal_and_joint_solved_before_heldout_reveal":True,
            "pre_reveal_policy_hashes":{
                name:entry["policies"][name]["first_stage_sha256_pre_reveal"]
                for name in ("nominal","joint")},
            "comparisons":comparisons,
        })
    paired=[]
    fail=0
    unmatched=0
    for case in cases:
        flows={key:case["comparisons"][key]["causal_hourly_observation_replay"]
               for key in ("nominal","joint")}
        if not all(x["feasible"] for x in flows.values()):
            fail+=1
        if any(x["feasible"] and not
               x["terminal_inventory_matches_initial_for_comparison"]
               for x in flows.values()):
            unmatched+=1
        if all(x["feasible"] and
               x["terminal_inventory_matches_initial_for_comparison"]
               for x in flows.values()):
            paired.append(flows["joint"]["economic_contribution_eur"]
                          -flows["nominal"]["economic_contribution_eur"])
    return {
        "protocol":"BIOGASFLEX_V0922_HOURLY_CAUSAL_OBSERVATION_15MIN_CHp_REPLAY_RESEARCH_V1",
        "source_sha256":j.SOURCE_SHA256,
        "gas_and_heat_couplings_empirically_calibrated":False,
        "original_price_forecast_vintages_verified":False,
        "real_traded_awards_enforced":False,
        "available_complete_heldout_days":
            source["quality"]["heldout_complete_days"],
        "eligible_days_with_exact_complete_7day_lag":eligible_count,
        "excluded_due_to_missing_prior_complete_day":excluded,
        "days_evaluated":len(cases),
        "all_eligible_days_evaluated":len(cases)==eligible_count,
        "one_or_more_causal_replays_infeasible_count":fail,
        "one_or_more_replays_terminal_inventory_unmatched_count":unmatched,
        "both_policies_feasible_and_terminal_matched_count":len(paired),
        "joint_minus_nominal_causal_contribution_eur_paired":paired,
        "paired_average_difference_eur_descriptive_not_confidence_interval":
            math.fsum(paired)/len(paired) if paired else None,
        "rows":cases,
    }


def _metrics(entries, policy_name):
    records=[case["policies"][policy_name] for case in entries]
    output={}
    for mode in ("unprotected","protected"):
        outcomes=[r[mode] for r in records]
        fail=sum(not x["feasible"] for x in outcomes)
        unmatched=sum(x["feasible"] and not
                      x["terminal_inventory_matches_initial_for_comparison"]
                      for x in outcomes)
        output[mode]={
            "days":len(records),
            "causal_full_horizon_feasible_days":len(records)-fail,
            "causal_full_horizon_infeasible_days":fail,
            "terminal_stock_unmatched_despite_feasible":unmatched,
            "complete_and_terminal_matched_days":len(records)-fail-unmatched,
        }
    rescued=sum((not case["unprotected"]["feasible"]) and
               case["protected"]["feasible"] for case in records)
    regressed=sum(case["unprotected"]["feasible"] and
                  (not case["protected"]["feasible"]) for case in records)
    common=[]
    for r in records:
        x,y=r["unprotected"],r["protected"]
        if (x["feasible"] and y["feasible"] and
            x["terminal_inventory_matches_initial_for_comparison"] and
            y["terminal_inventory_matches_initial_for_comparison"]):
            common.append(y["economic_contribution_eur"]-x["economic_contribution_eur"])
    return {
        "unprotected":output["unprotected"],
        "protected":output["protected"],
        "rescued_infeasible_replay_days_feasible_under_protection":rescued,
        "new_infeasibility_under_protection_days":regressed,
        "strict_matched_service_days_with_both_controllers_and_same_binary":len(common),
        "protected_minus_unprotected_contribution_eur_matched_only":common,
        "average_matched_economic_change_eur_not_population_mean":
            math.fsum(common)/len(common) if common else None,
    }


def run(source:dict, *, max_days:int|None=None,
        synthetic_gas_floor_mw_lhv:float=DEFAULT_SYNTHETIC_FLOOR_MW_LHV)->dict:
    require(max_days is None or max_days>0,"max_days must be positive")
    require(math.isfinite(synthetic_gas_floor_mw_lhv) and
            0<=synthetic_gas_floor_mw_lhv<=j.GAS_BASE,
            "Out-of-range research gas arrival floor")
    # Enforce absolute model support for the source-derived synthetic input.
    # A higher 'floor' would be more optimistic, not a conservative bound.
    require(synthetic_gas_floor_mw_lhv<=.78+1e-12,
            "Requested floor exceeds the predeclared model-global synthetic lower bound .78")
    train, heldout = j._source_validate(source)
    scales=j._standardizers(source)
    by_day={d["date_utc"]:d for d in source["complete_days"]}
    entries=[]
    excluded=[]
    eligible=[]
    for ordinal,day in enumerate(heldout):
        lag=c22._historical_baseline(day,by_day)
        if lag is None:
            excluded.append({"date_utc":day["date_utc"],
                             "reason":"Exact complete UTC prior-7-day source block absent"})
        else:
            eligible.append((ordinal,day,lag))
    require(eligible,"No prior-week-complete heldout days")
    subset=eligible if max_days is None else eligible[:max_days]
    for ordinal,day,lag in subset:
        nominal={
            "block_key":"PERSISTENCE_PRICE_UNCALIBRATED_NOMINAL",
            "price_eur_mwh":[float(lag[h]) for h in range(j.HOUR_START,j.HOUR_START+j.HOURS)
                              for _ in range(4)],
            "synthetic_gas_production_mw_lhv":[j.GAS_BASE]*j.N,
            "synthetic_site_heat_demand_mw_th":[j.HEAT_BASE]*j.N,
        }
        # Exactly same ex-ante input and commitment methods as v0.9.22;
        # preserve policies unchanged when comparing controllers.
        blocks=[j._scenario(train[i],lag,scales,
                             key=f"TRAIN_BLOCK_{i:03d}") for i in j.TRAIN_ORDINALS]
        policies={
            "nominal":j._milp_bundle([nominal]),
            "joint":j._milp_bundle(blocks),
        }
        hashes={name:policies[name]["first_stage_sha256"] for name in policies}
        actual=j._scenario(day,lag,scales,key="POST_LOCK_HELDOUT")
        for name,policy in policies.items():
            states=policy["binary_first_stage_on"]
            options=dict(starts=policy["starts"],stops=policy["stops"])
            raw=c22.replay_causal(nominal,actual,states,**options)
            protected=c22.replay_causal(
                nominal,actual,states,**options,
                next_hour_gas_floor=synthetic_gas_floor_mw_lhv)
            hindsight=j._fixed_recourse(actual,states)
            switching=j.START_COST*sum(policy["starts"])+j.STOP_COST*sum(policy["stops"])
            policy.clear()
            policy.update({
                "first_stage_sha256_pre_reveal":hashes[name],
                "first_stage_on":states,
                "first_stage_starts":options["starts"],
                "first_stage_stops":options["stops"],
                "hindsight_feasible":hindsight["feasible"],
                "hindsight_upper_bound_eur":
                   hindsight["contribution_eur"]-switching
                   if hindsight["feasible"] else None,
                "unprotected":raw,
                "protected":protected,
            })
        entries.append({
            "day_utc":day["date_utc"],
            "heldout_ordinal":ordinal,
            "source_actual_synthetic_gas_min_mw_lhv":
                min(actual["synthetic_gas_production_mw_lhv"]),
            "gas_arrival_floor_condition_met_on_realized_synthetic_hours":
                all(x>=synthetic_gas_floor_mw_lhv-1e-9
                    for x in actual["synthetic_gas_production_mw_lhv"]),
            "first_stage_sha256_identical_nominal_and_joint":
                hashes["nominal"]==hashes["joint"],
            "policies":policies,
        })
    views={
        mode:_build_compatible_view(source,entries,mode=mode,
                                  eligible_count=len(eligible),excluded=excluded)
        for mode in ("unprotected","protected")
    }
    return {
        "protocol":PROTOCOL,
        "status":"MATHEMATICAL_SYNTHETIC_GAS_FLOOR_ONE_HOUR_WITNESS_NOT_FULL_ROBUST_VIABILITY",
        "source_sha256":j.SOURCE_SHA256,
        "synthetic_gas_lower_clip_mw_lhv":.78,
        "predeclared_guard_synthetic_floor_mw_lhv":synthetic_gas_floor_mw_lhv,
        "training_only_estimated_gas_bound":False,
        "plant_gas_arrival_physically_validated":False,
        "reserve_witness_scope":"ONE_NEXT_SOURCE_HOUR_CONSTANT_GAS_LOWER_BOUND_EXISTS",
        "future_source_hour_realized_gas_in_controller":False,
        "source_hourly_not_independent_quarter_hourly":True,
        "original_price_forecast_vintage_verified":False,
        "market_accepted_electric_award_enforced":False,
        "terminal_inventory_not_hard_enforced":True,
        "entire_heldout_selected_ex_ante":max_days is None,
        "days_evaluated":len(entries),
        "complete_holdout_days":len(heldout),
        "eligible_full_holdout_days":len(eligible),
        "first_stages_identical_nominal_joint_days":
            sum(x["first_stage_sha256_identical_nominal_and_joint"] for x in entries),
        "nominal_policy":_metrics(entries,"nominal"),
        "joint_policy":_metrics(entries,"joint"),
        "views_for_independent_v0922_ledger_audit":views,
        "cases":entries,
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True,
                   help="Verified v0.9.21 source JSON outside repository")
    p.add_argument("--output",type=Path,required=True,
                   help="Study JSON outside repository")
    p.add_argument("--max-days",type=int,default=None,
                   help="Subset smoke only; full holdout is default")
    p.add_argument("--synthetic-gas-floor",type=float,
                   default=DEFAULT_SYNTHETIC_FLOOR_MW_LHV)
    args=p.parse_args()
    source=json.loads(args.source.read_text(encoding="utf8"))
    result=run(source,max_days=args.max_days,
               synthetic_gas_floor_mw_lhv=args.synthetic_gas_floor)
    j.write_out(result,args.output)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("cases","views_for_independent_v0922_ledger_audit")},
                     indent=2,allow_nan=False))


if __name__=="__main__":
    main()
