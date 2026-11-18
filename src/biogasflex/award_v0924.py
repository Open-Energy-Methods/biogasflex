"""v0.9.24: pre-reveal hypothetical export awards + causal CHP gas-reserve replay.

Each accepted energy award is specified IN MWh FOR EACH 15-MINUTE
INTERVAL. This is a HYPOTHETICAL stress of model/contract feasibility,
NOT evidence of real accepted bids, observed site-grid exports,
price-forecast vintages, penalties or European settlement practices.

The 0.09 / 0.10 / 0.15 MWh synthetic award profiles are predeclared
for all 92 holdout days. The .09 MWh/slot case is a rounded-down
six-hour *minimum-synthetic-gas* energy-budget illustration:
  g_min=.78 MW_LHV, initial stock=.75 MWh_LHV, H=6h:
  u_average <= .78+.75/6 = .905 MW_LHV; chosen .90.
It is NOT a worst-case upper-buffer feasibility guarantee.
.10 MWh/slot is 1 MW_LHV nominal; .15 MWh/slot is a deliberate
ramp-incompatible award from the stated initial 0.4 MW_e / half-slot
ramp convention. No case is tuned to heldout outcomes.

No actual electric import/export slack, fuel dumping, spare gas purchases,
awarded-energy forgiveness or market imbalance penalty is invented.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path

from . import causal_v0922 as c22
from . import joint_v0921 as j

PROTOCOL="BIOGASFLEX_V0924_CAUSAL_HARD_15MIN_HYPOTHETICAL_ELECTRIC_AWARD_V1"
AWARD_PROFILES_MWH_PER_QUARTER={
    "floor_budget_0p090":.09,
    "nominal_gas_0p100":.10,
    "initial_ramp_stress_0p150":.15,
}
GAS_FLOOR=.78


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError("v0.9.24 hard-export contract: "+message)


def award_hash(energy: list[float]) -> str:
    """Explicit locking of forecast-time per-quarter accepted export award."""
    return sha256(json.dumps(energy,separators=(",",":"),
                             allow_nan=False).encode("utf8")).hexdigest()


def predeclare_award_profiles() -> dict:
    """No historical target, price or site measurement may enter this function."""
    return {
        key:{
            "profile_id":key,
            "quarter_hour_export_mwh":[v]*j.N,
            "total_six_hour_export_mwh":v*j.N,
            "pre_reveal_award_sha256":award_hash([v]*j.N),
            "bid_is_synthetic_not_an_actual_market_award":True,
        }
        for key,v in AWARD_PROFILES_MWH_PER_QUARTER.items()
    }


def make_nominal(lagged_prices: list[float]) -> dict:
    return {
        "block_key":"SE3_HISTORICAL_7DAY_PRICE_BASELINE_SYNTHETIC_GAS_AND_HEAT",
        "price_eur_mwh":[float(lagged_prices[h])
                         for h in range(j.HOUR_START,j.HOUR_START+j.HOURS)
                         for _ in range(4)],
        "synthetic_gas_production_mw_lhv":[j.GAS_BASE]*j.N,
        "synthetic_site_heat_demand_mw_th":[j.HEAT_BASE]*j.N,
    }


def to_v0922_audit_view(source:dict, cases:list[dict], *,
                        profile_id:str, mode:str,
                        eligible_count:int, excluded:list[dict]) -> dict:
    """Construct fully source-verifiable v0.9.22 legacy audit data shape."""
    rows=[]
    paired=[]
    fail=0
    unmatched=0
    for day in cases:
        profile=day["award_profiles"][profile_id]
        cmp={}
        for name in ("nominal","joint"):
            p=profile["strategies"][name]
            cmp[name]={
                "first_stage_sha256_pre_reveal":
                    p["first_stage_sha256_pre_reveal"],
                "first_stage_on":p["first_stage_on"],
                "first_stage_starts":p["first_stage_starts"],
                "first_stage_stops":p["first_stage_stops"],
                "causal_hourly_observation_replay":p["replays"][mode],
                # The fixed-binary oracle without awards is a feasible
                # superset only when the same terminal stock is achieved.
                "same_binary_full_future_recourse_upper_bound_eur":
                    p["unconstrained_export_hindsight_upper_bound_eur"],
                "same_binary_hindsight_feasible":p["hindsight_feasible"],
            }
        result={
            "heldout_day_utc":day["day_utc"],
            "heldout_ordinal":day["heldout_ordinal"],
            "nominal_and_joint_solved_before_heldout_reveal":True,
            "pre_reveal_policy_hashes":day["first_stage_policy_hashes_pre_reveal"],
            "comparisons":cmp,
        }
        rows.append(result)
        runs={p:cmp[p]["causal_hourly_observation_replay"]
              for p in ("nominal","joint")}
        if any(not r["feasible"] for r in runs.values()):
            fail+=1
        if any(r["feasible"] and not
               r["terminal_inventory_matches_initial_for_comparison"]
               for r in runs.values()):
            unmatched+=1
        if all(r["feasible"] and
               r["terminal_inventory_matches_initial_for_comparison"]
               for r in runs.values()):
            paired.append(runs["joint"]["economic_contribution_eur"]-
                          runs["nominal"]["economic_contribution_eur"])
    return {
        "protocol":"BIOGASFLEX_V0922_HOURLY_CAUSAL_OBSERVATION_15MIN_CHp_REPLAY_RESEARCH_V1",
        "source_sha256":j.SOURCE_SHA256,
        "gas_and_heat_couplings_empirically_calibrated":False,
        "original_price_forecast_vintages_verified":False,
        "real_traded_awards_enforced":False,
        "available_complete_heldout_days":source["quality"]["heldout_complete_days"],
        "eligible_days_with_exact_complete_7day_lag":eligible_count,
        "excluded_due_to_missing_prior_complete_day":excluded,
        "days_evaluated":len(rows),
        "all_eligible_days_evaluated":len(rows)==eligible_count,
        "one_or_more_causal_replays_infeasible_count":fail,
        "one_or_more_replays_terminal_inventory_unmatched_count":unmatched,
        "both_policies_feasible_and_terminal_matched_count":len(paired),
        "joint_minus_nominal_causal_contribution_eur_paired":paired,
        "paired_average_difference_eur_descriptive_not_confidence_interval":
            math.fsum(paired)/len(paired) if paired else None,
        "rows":rows,
    }


def profile_metrics(cases:list[dict], profile_id:str, name:str, mode:str) -> dict:
    runs=[d["award_profiles"][profile_id]["strategies"][name]
           ["replays"][mode] for d in cases]
    feasible=sum(r["feasible"] for r in runs)
    matched=sum(r["feasible"] and
                r["terminal_inventory_matches_initial_for_comparison"] for r in runs)
    return {
        "attempted_source_days":len(cases),
        "complete_awarded_export_feasible_days":feasible,
        "infeasible_contract_service_days":len(cases)-feasible,
        "feasible_but_unmatched_terminal_stock_days":feasible-matched,
        "complete_contract_service_and_matched_terminal_stock_days":matched,
        "failed_awards_are_not_counted_as_delivered_energy":True,
    }


def run(source:dict, *, max_days:int|None=None)->dict:
    require(max_days is None or max_days>0,"max_days must be positive")
    train,holdout=j._source_validate(source)
    scales=j._standardizers(source)
    by_day={day["date_utc"]:day for day in source["complete_days"]}
    eligible=[]
    excluded=[]
    for ordinal,day in enumerate(holdout):
        lag=c22._historical_baseline(day,by_day)
        if lag is None:
            excluded.append({"date_utc":day["date_utc"],
                             "reason":"Exact complete UTC source day seven calendar days earlier absent"})
        else:
            eligible.append((ordinal,day,lag))
    require(eligible,"No prior-week-complete heldout days")
    selected=eligible if max_days is None else eligible[:max_days]
    declared=predeclare_award_profiles()
    cases=[]
    for ordinal,day,lag in selected:
        nominal=make_nominal(lag)
        training=[j._scenario(train[k],lag,scales,
                             key=f"TRAIN_BLOCK_{k:03d}") for k in j.TRAIN_ORDINALS]
        # First stage and awards locked prior to revealing actual heldout
        # price, paired regional load error, or synthetic plant variables.
        fixed={
            "nominal":j._milp_bundle([nominal]),
            "joint":j._milp_bundle(training),
        }
        locks={name:fixed[name]["first_stage_sha256"] for name in fixed}
        # Reveal ONLY after ex-ante award hashes, source-baseline, commitment
        # models and data-independent award profiles have been fully fixed.
        actual=j._scenario(day,lag,scales,key="POST_COMMITMENT_HELDOUT_REVEAL")
        profiles={}
        for key,profile in declared.items():
            strategies={}
            for name,policy in fixed.items():
                states=policy["binary_first_stage_on"]
                starts,stops=policy["starts"],policy["stops"]
                award=profile["quarter_hour_export_mwh"]
                no_guard=c22.replay_causal(
                    nominal,actual,states,starts=starts,stops=stops,
                    awarded_export_mwh=award)
                with_guard=c22.replay_causal(
                    nominal,actual,states,starts=starts,stops=stops,
                    next_hour_gas_floor=GAS_FLOOR,
                    awarded_export_mwh=award)
                hindsight=j._fixed_recourse(actual,states)
                switching=j.START_COST*sum(starts)+j.STOP_COST*sum(stops)
                strategies[name]={
                    "first_stage_sha256_pre_reveal":locks[name],
                    "first_stage_on":states,
                    "first_stage_starts":starts,
                    "first_stage_stops":stops,
                    "hindsight_feasible":hindsight["feasible"],
                    "unconstrained_export_hindsight_upper_bound_eur":
                        hindsight["contribution_eur"]-switching
                        if hindsight["feasible"] else None,
                    "replays":{
                        "award_only":no_guard,
                        "award_and_reserve":with_guard,
                    }
                }
            profiles[key]={**profile,"strategies":strategies}
        cases.append({
            "day_utc":day["date_utc"],
            "heldout_ordinal":ordinal,
            "first_stage_policy_hashes_pre_reveal":locks,
            "first_stages_nominal_equal_joint":
                locks["nominal"]==locks["joint"],
            "all_award_profiles_created_before_heldout_reveal":True,
            "realized_gas_and_heat_are_synthetic":True,
            "award_profiles":profiles,
        })
    audit_views={
        key:{
            mode:to_v0922_audit_view(
                source,cases,profile_id=key,mode=mode,
                eligible_count=len(eligible),excluded=excluded)
            for mode in ("award_only","award_and_reserve")
        } for key in declared
    }
    summary={
        key:{
            mode:{
                name:profile_metrics(cases,key,name,mode)
                for name in ("nominal","joint")
            } for mode in ("award_only","award_and_reserve")
        } for key in declared
    }
    return {
        "protocol":PROTOCOL,
        "status":"SYNTHETIC_AWARD_MODEL_NOT_ACTUAL_ACCEPTED_BID_OR_SETTLEMENT",
        "source_sha256":j.SOURCE_SHA256,
        "source_date_range_utc":("2019-10-01","2019-12-31"),
        "available_source_heldout_complete_days":len(holdout),
        "eligible_heldout_complete_days":len(eligible),
        "days_evaluated":len(cases),
        "study_is_subset_smoke":len(cases)!=len(eligible),
        "gas_floor_mw_lhv":GAS_FLOOR,
        "gas_heat_proxy_empirically_calibrated":False,
        "real_market_bid_or_award_verified":False,
        "forecast_issue_vintages_verified":False,
        "real_electricity_meter_readings_present":False,
        "modeled_electric_import_and_award_shortfall_slack_enabled":False,
        "award_15min_source_resolution_observed":False,
        "published_source_is_hourly_with_four_mathematical_quarters":True,
        "award_profiles_predeclared":declared,
        "nominal_and_joint_first_stages_identical_count":
            sum(d["first_stages_nominal_equal_joint"] for d in cases),
        "summary_by_award_profile_and_control_mode":summary,
        "complete_replays_for_independent_v0922_audit":audit_views,
        "cases":cases,
    }


def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True,
                   help="Publisher-verified v0.9.21 full hourly SE3 evidence JSON")
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--max-days",type=int,default=None,
                   help="Smoke subset ONLY; omitted means full historical holdout")
    args=p.parse_args()
    result=run(json.loads(args.source.read_text(encoding="utf8")),
               max_days=args.max_days)
    j.write_out(result,args.output)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("cases","complete_replays_for_independent_v0922_audit")},
                     indent=2,allow_nan=False))


if __name__=="__main__":
    main()
