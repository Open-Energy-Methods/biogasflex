"""Independent v0.9.20 rectangular maximin and strictly held-out price audit.

Imports NO biogasflex optimizer/model package. Reuses the separately
coded v0.9.19 gas/heat fixed-binary LP formulation and explicit primal
dual KKT arithmetic (SciPy HiGHS remains the shared LP backend).

For the small 8-quarter case, explicitly enumerates all 2^8 binary
commitment patterns for BOTH nominal and robust schedules. The exact
robustness proof relies on nonnegative generator terminal electricity:
min_{lower<=price<=upper} E·price - cost = E·lower-cost.

No physical calibration or statistical uncertainty claims.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
from itertools import product
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
# Load the *independent* prior LP/KKT mathematical formulation by path,
# including when this file is imported through unittest spec_from_file_location.
_SOURCE=Path(__file__).resolve().with_name("audit_v0919_independent.py")
_SPEC=importlib.util.spec_from_file_location("v0919_independent_math",_SOURCE)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError("Independent source-level LP/KKT audit unavailable")
m19=importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(m19)

PROTOCOL="BIOGASFLEX_V0920_RECTANGULAR_PRICE_UNCERTAINTY_HELDOUT_REPLAY_V1"
SOURCE="SYNTHETIC_NO_REAL_BID_TIME_MARKET_OR_BIOGAS_ENGINE_OBSERVATIONS"
TRAIN=(11,37)
BANDS=("reference","wide_stress")
HOLDOUT=(101,211,307)
HORIZONS=(24,96,192)
PRICES=(5.,5.,5.,5.,120.,120.,120.,120.,120.,120.,15.,15.,
        15.,15.,15.,15.,110.,110.,110.,110.,110.,110.,110.,110.)
TOL=3e-5
START=datetime(2020,1,1,tzinfo=timezone.utc)
NOW_BEFORE=(START-timedelta(hours=1)).isoformat()

def demand(ok,why):
    if not ok:raise AssertionError("v0.9.20 independent audit: "+why)

def close(a,b,label,tol=TOL):
    demand(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,
           f"{label}: {a} vs {b}")

def price_design(seed,n,band):
    demand(seed in TRAIN and n in (8,*HORIZONS) and band in BANDS,
           "Nonpredeclared training seed/horizon/stress band")
    forecast=[float(PRICES[i%24]+((seed*7+i*13+(i//4)*5)%9-4))
              for i in range(n)]
    if band=="reference":
        high,mid,low=55.,12.,8.
    else:
        high,mid,low=115.,20.,8.
    spread=[high if PRICES[i%24]>=100. else mid if PRICES[i%24]>=15. else low
            for i in range(n)]
    lo=[max(0.,round(p-d,8)) for p,d in zip(forecast,spread)]
    hi=[round(p+d,8) for p,d in zip(forecast,spread)]
    return forecast,lo,hi

def heldout(seed,hold_seed,lo,hi):
    demand(hold_seed in HOLDOUT,"Nonpredeclared heldout path")
    return [
       round(a+(b-a)*(((hold_seed*17+i*23+(i//4)*13+seed*7)%97)/96),8)
       for i,(a,b) in enumerate(zip(lo,hi))
    ]

def _design_check(case):
    seed,n=case["train_seed"],case["slots"]
    band=case["price_bound_class"]
    forecast,lo,hi=price_design(seed,n,band)
    demand(case["duration_hours"]==n*.25,"Wrong time resolution")
    demand(case["forecast_issued_at_utc"]==NOW_BEFORE
           and case["service_begins_utc"]==START.isoformat(),
           "Price information timeline not frozen before execution")
    demand(case["input_provenance"]==SOURCE
           and case["no_real_bid_time_data_or_probability"] is True,
           "Fabricated physical/probability evidence")
    demand(case["nominal_train_forecast_eur_mwh"]==forecast
           and case["rectangular_lower_price_eur_mwh"]==lo
           and case["rectangular_upper_price_eur_mwh"]==hi,
           "Price confidence envelope/profile was modified")
    demand(all(0<=a<=b for a,b in zip(lo,hi)),
           "Invalid rectangular lower/upper price envelope")
    demand(set(case["policies"])=={"nominal_forecast","rectangular_maximin"},
           "Missing or substitute ex-ante optimization policy")
    demand(case["rectangle_exactness_reason"].startswith("GENERATOR_TERMINAL_EXPORT_NONNEGATIVE"),
           "Rectangular min-price proof's nonnegative-flow premise missing")
    cfg=case["config"];lim=cfg["experimental_v097"]
    demand(cfg["case_id"]==f"v0920_RECTANGULAR_SYNTHETIC_price_seed{seed}_{n}slots_{band}",
           "Unexpected synthetic case identity")
    demand(cfg["forecast_source_status"]==SOURCE
           and cfg["input_provenance"]==m19.PROVENANCE,
           "Change of immutable physical assumption source")
    demand(cfg["gas_production_mw_lhv"]==[1.]*n
           and cfg["electric_efficiency_lhv"]==.4
           and cfg["thermal_efficiency_lhv"]==.2
           and cfg["electric_rating_mw"]==.8
           and cfg["gas_storage_capacity_mwh_lhv"]==1.5
           and cfg["initial_gas_inventory_mwh_lhv"]==.75
           and cfg["aux_heat_capacity_mw_th"]==.15
           and cfg["heat_demand_mw_th"]==.15
           and cfg["heat_dump_capacity_mw_th"]==.35
           and cfg["aux_heat_cost_eur_per_mwh_th"]==6.
           and cfg["chp_variable_cost_eur_per_mwh_e"]==.75
           and cfg["heat_dump_penalty_eur_per_mwh_th"]==1.
           and cfg["fixed_flaring_mw_lhv"]==0.
           and cfg["fixed_losses_mw_lhv"]==0.
           and cfg["gas_input_mw_lhv"]==1.,
           "Hypothetical engine, heat or buffer inputs modified")
    demand(lim["model"]=="clock_hour_on_off_milp_v097"
           and lim["initial_on"] is True and lim["initial_power_mw_e"]==.4
           and lim["minimum_on_power_mw_e"]==.2
           and lim["ramp_up_mw_e_per_hour"]==.8
           and lim["ramp_down_mw_e_per_hour"]==.8
           and lim["minimum_up_hours"]==.5
           and lim["minimum_down_hours"]==.5
           and lim["initial_remaining_dwell_hours"]==0.
           and lim["startup_cost_eur"]==5.
           and lim["shutdown_cost_eur"]==1.,
           "Commitment/dwell/cost assumptions modified")
    return cfg,lim,forecast,lo,hi

def _fingerprint(rows):
    decisions=[
       [int(x["on"]),int(x["startup"]),int(x["shutdown"]),
        round(x["gas_use_mw_lhv"],8),round(x["stock_end_mwh_lhv"],8),
        round(x["useful_heat_mw_th"],8),
        round(x["aux_heat_mw_th"],8),round(x["dump_heat_mw_th"],8)]
       for x in rows
    ]
    return hashlib.sha256(json.dumps(decisions,separators=(",",":"),
                            allow_nan=False).encode("utf8")).hexdigest()

def _physical_cost(rows,prices,cfg,*,enforce_own_row_price=True):
    n=len(prices);demand(len(rows)==n,"Schedule/timestamps truncated")
    lim=cfg["experimental_v097"];old=.75;prior=int(lim["initial_on"])
    previous_p=lim["initial_power_mw_e"]
    starts=[];stops=[];states=[]
    revenues=[];use_mwh=[];chp_cost=[];heatback=[];dumped=[]
    stock=cfg["initial_gas_inventory_mwh_lhv"]
    for i,(row,price) in enumerate(zip(rows,prices)):
        expected=(START+timedelta(minutes=15*i)).isoformat()
        demand(row["start_utc"]==expected and row["dt_h"]==.25,
               "Source quarter-hour timestamp/date/clock changed")
        if enforce_own_row_price:close(row["price_eur_mwh"],price,"Optimizer price input")
        state=row["on"];start=row["startup"];stop=row["shutdown"]
        demand(state in (0,1) and start in (0,1) and stop in (0,1),
               "Nonbinary original commitment result")
        demand(start==int(prior==0 and state==1)
               and stop==int(prior==1 and state==0),
               "Incorrect commitment transition")
        u,p,s=row["gas_use_mw_lhv"],row["power_mw_e"],row["stock_end_mwh_lhv"]
        h,a,w=row["useful_heat_mw_th"],row["aux_heat_mw_th"],row["dump_heat_mw_th"]
        demand(all(math.isfinite(x) for x in (u,p,s,h,a,w,price)),
               "Nonfinite source price/schedule")
        close(p,.4*u,"Independent electric energy conversion")
        close(s-stock,(1.-u)*.25,"Independent gas inventory")
        close(.2*u,h+w,"Independent CHP heat conservation")
        close(h+a,.15,"Independent heat service")
        close(h,min(.15,.2*u),"Cost-minimal useful heat distribution")
        demand(-TOL<=s<=1.5+TOL and -TOL<=a<=.15+TOL
               and -TOL<=w<=.35+TOL and -TOL<=h<=.15+TOL,
               "Buffer/heat physical bounds")
        demand(-TOL<=p<=.8+TOL and (p>=.2-TOL if state else abs(p)<=TOL),
               "Engine nameplate/min-on/zero-OFF power")
        if state and prior:
            dt=.125 if i==0 else .25
            demand(abs(p-previous_p)<=.8*dt+TOL,
                   "Midpoint ON-ON ramp exceeded")
        revenues.append(p*price*.25)
        use_mwh.append(u*.25)
        chp_cost.append(p*.75*.25)
        heatback.append(a*6.*.25)
        dumped.append(w*.25)
        stock=s;prior=state;previous_p=p
        states.append(state);starts.append(start);stops.append(stop)
    near_total=sum(use_mwh)
    close(near_total,n*.25,"Full production/fuel energy conservation")
    close(stock,.75,"Full cyclic end gas inventory")
    es,vs=m19._events(states,lim)
    demand(starts==es and stops==vs,"Elapsed-dwell or binary pattern invalid")
    obj=(math.fsum(revenues)-math.fsum(chp_cost)
         -math.fsum(heatback)-math.fsum(dumped)
         -5*sum(starts)-1*sum(stops))
    return obj,states,es,vs

def _certify_fixed_binary(cfg,lim,prices,states,original_objective):
    prob=m19.formulate(cfg,lim,np.array(prices),states)
    sol=m19._solve(prob)
    demand(sol.success,"Independent fixed-state alternative LP infeasible")
    kkt=m19._kkt_check(prob,sol)
    starts,stops=m19._events(states,lim)
    value=-kkt["independent_lp_primal_eur"]-5*sum(starts)-sum(stops)
    close(value,original_objective,"Independent fixed-binary optimum",2e-4)
    return kkt

def _enumerate_eight(cfg,lim,prices):
    """Strict exhaustive global 8-slot binary optimum, not solver-only."""
    best=-math.inf;feasible=0
    for states in product((0,1),repeat=8):
        try:
            starts,stops=m19._events(states,lim)
        except AssertionError:
            continue
        prob=m19.formulate(cfg,lim,np.array(prices),states)
        sol=m19._solve(prob)
        if not sol.success:continue
        feasible+=1
        value=-float(sol.fun)-5*sum(starts)-sum(stops)
        best=max(best,value)
    demand(feasible>1,"Not a competitive endogenous 8-slot binary case")
    return {"enumerated_binary_sequences":256,
            "feasible_binary_sequences":feasible,
            "independently_global_model_objective_eur":best}

def audit_case(case):
    cfg,lim,forecast,lower,upper=_design_check(case)
    policy_certificates={}
    for name,price in (("nominal_forecast",forecast),
                       ("rectangular_maximin",lower)):
        sol=case["policies"][name]
        demand(sol["optimization_price_input"]==name
               and sol["original_engine_model"]=="clock_hour_on_off_milp_v097",
               "Policy optimized using incorrect information source")
        demand(sol["decision_sha256"]==_fingerprint(sol["rows"]),
               "Pre-replay schedule changed")
        objective,states,starts,stops=_physical_cost(sol["rows"],price,cfg)
        close(objective,sol["reported_model_objective_eur"],
              "Nominal or lower-bound solver objective")
        close(sol["reported_mip_gap"],0,"Original MILP reported MIP gap")
        demand(sum(starts)==sol["start_count"] and
               sum(stops)==sol["stop_count"],"Switch count inconsistent")
        value_nominal=_physical_cost(sol["rows"],forecast,cfg,
                                     enforce_own_row_price=False)[0]
        value_lower=_physical_cost(sol["rows"],lower,cfg,
                                   enforce_own_row_price=False)[0]
        close(value_nominal,sol["frozen_objective_on_nominal_forecast_eur"],
              "Frozen nominal replay objective")
        close(value_lower,sol["frozen_worst_case_rectangle_eur"],
              "Exact rectangular worst-case lower-envelope objective")
        policy_certificates[name]={
           "frozen_decision_hash":sol["decision_sha256"],
           "recomputed_rectangle_worst_case_eur":value_lower,
           "recomputed_nominal_eur":value_nominal,
           "independent_fixed_binary_kkt":_certify_fixed_binary(
                cfg,lim,price,states,objective),
        }
        if case["slots"]==8:
            enumeration=_enumerate_eight(cfg,lim,price)
            close(objective,enumeration["independently_global_model_objective_eur"],
                  "Exhaustive 8-slot global MILP optimum",2e-4)
            policy_certificates[name]["exhaustive_small_MILP"]=enumeration
    demand(policy_certificates["rectangular_maximin"][
               "recomputed_rectangle_worst_case_eur"]+TOL>=
           policy_certificates["nominal_forecast"][
               "recomputed_rectangle_worst_case_eur"],
           "Robust strategy fails certified rectangular maximin comparison")
    # The lower-envelope is the algebraically proven minimizing vertex
    # of a rectangular band for p_i >= 0. No confidence/probability claim.
    holdouts=case["heldout_paths"]
    demand(len(holdouts)==len(HOLDOUT),"Missing heldout replay")
    hindsight_certificates=[]
    for row,seed in zip(holdouts,HOLDOUT):
        demand(row["source_seed"]==seed,"Heldout path reordered")
        p=row["prices_revealed_only_after_schedule_fixed_eur_mwh"]
        expected=heldout(case["train_seed"],seed,lower,upper)
        demand(p==expected,"Heldout prices manipulated or lookahead leakage")
        demand(all(a-TOL<=v<=b+TOL for a,b,v in zip(lower,upper,p)),
               "Heldout outside a claimed uncertainty bound")
        hindsight=row["perfect_information_oracle_not_operational"]
        hindsight_obj,states,_,_=_physical_cost(hindsight["rows"],p,cfg)
        close(hindsight["reported_model_objective_eur"],hindsight_obj,
              "Hindsight oracle objective")
        hindsight_certificates.append({
            "seed":seed,"hindsight_fixed_pattern_kkt":_certify_fixed_binary(
                cfg,lim,p,states,hindsight_obj),
        })
        demand(set(row["frozen_policy_evaluations"])==set(policy_certificates),
               "Missing frozen OOS policy evaluation")
        for name in policy_certificates:
            frozen=case["policies"][name]
            evaluation=row["frozen_policy_evaluations"][name]
            demand(evaluation["frozen_schedule_decision_sha256"]==frozen["decision_sha256"],
                   "OOS policy was retroactively changed after price reveal")
            value=_physical_cost(frozen["rows"],p,cfg,
                                 enforce_own_row_price=False)[0]
            close(value,evaluation["realized_synthetic_contribution_eur"],
                  "Independently recomputed heldout frozen schedule contribution")
            regret=hindsight_obj-value
            demand(regret>=-TOL,"Nonoperational hindsight below frozen policy")
            close(max(0,regret),evaluation["perfect_information_regret_eur"],
                  "Independent hindsight-referenced forecast regret")
            # Exact rectangular regret guarantee for THIS physical
            # policy: all holdout prices are >= each lower bound,
            # generator-terminal electricity is nonnegative.
            demand(value+TOL>=policy_certificates[name][
                       "recomputed_rectangle_worst_case_eur"],
                   "Out-of-sample realized below analytic bound")
    return {
        "train_seed":case["train_seed"],"slots":case["slots"],
        "price_bound_class":case["price_bound_class"],
        "policy_count":len(policy_certificates),
        "holdout_paths":len(holdouts),
        "physical_rows_audited":case["slots"]*(2+len(holdouts)),
        "independently_certified_fixed_binary_LP_KKT":len(policy_certificates)+len(holdouts),
        "independent_global_8slot_patterns_verified":(
            2 if case["slots"]==8 else 0),
        "policy_certificates":policy_certificates,
        "hindsight_certificates":hindsight_certificates,
        "status":"PASS_SEPARATE_OPTIMALITY_AND_OUT_OF_SAMPLE_PHYSICAL_WITNESS",
    }

def audit(payload):
    demand(payload["protocol"]==PROTOCOL and payload["release_version"]=="0.9.20",
           "Wrong frozen source/release version")
    demand(payload["status"].startswith("PASS_SYNTHETIC_FROZEN_POLICY_"),
           "Unexecuted study or source uncertainty classification")
    demand(payload["uncertainty_geometry"].startswith("RECTANGULAR_")
           and payload["confidence_level_or_probabilistic_reliability"] is None
           and payload["chronology"].startswith("FORECAST_AND_DECLARED_PRICE_BOUNDS_BEFORE"),
           "Unsupported stochastic confidence or forecast chronology")
    demand(not any(payload["claims"].values()),
           "Unfounded physical/forecast certification")
    cases=payload["cases"]
    declared=[(11,8,band) for band in BANDS] if (
        payload["horizons_quarter_hour_intervals"]==[8]) else (
        [(seed,n,band) for seed in TRAIN for n in HORIZONS
         for band in BANDS]+[(11,8,band) for band in BANDS])
    demand([(c["train_seed"],c["slots"],c["price_bound_class"])
             for c in cases]==declared,
           "Source train/horizon case list incomplete, substituted or reordered")
    demand(payload["price_stress_classes"]==list(BANDS),
           "Missing wide envelope or reference negative-result control")
    demand(payload["unseen_price_evaluation_seeds"]==list(HOLDOUT),
           "Holdout selection manipulated")
    certificates=[audit_case(case) for case in cases]
    seen_summaries=set()
    for reported in payload["selected_holdout_descriptive_comparisons"]:
        index=(reported["train_seed"],reported["slots"],reported["price_bound_class"])
        demand(index not in seen_summaries,"Duplicate selected heldout scenario summary")
        seen_summaries.add(index)
        c=next((x for x in cases
                if x["train_seed"]==reported["train_seed"]
                and x["slots"]==reported["slots"]
                and x["price_bound_class"]==reported["price_bound_class"]),None)
        demand(c is not None and c["slots"]!=8,"Summarized unknown horizon")
        for name,key in (("nominal_forecast","nominal"),
                         ("rectangular_maximin","robust")):
            values=[row["frozen_policy_evaluations"][name][
                        "realized_synthetic_contribution_eur"]
                    for row in c["heldout_paths"]]
            regrets=[row["frozen_policy_evaluations"][name][
                        "perfect_information_regret_eur"]
                     for row in c["heldout_paths"]]
            close(min(values),reported[key+"_min_observed_heldout_eur"],
                  "Selected holdout minimum must be independently recomputed")
            close(math.fsum(values)/len(values),
                  reported[key+"_arithmetic_heldout_mean_eur"],"Heldout nonprobabilistic arithmetic mean")
            close(math.fsum(regrets)/len(regrets),
                  reported[key+"_heldout_mean_regret_eur"],"Independent heldout regret mean")
            close(c["policies"][name]["frozen_worst_case_rectangle_eur"],
                  reported[key+"_exact_rectangular_worst_case_eur"],
                  "Independently verified rectangular envelope bound")
        demand(reported[
            "average_refers_only_to_3_selected_nonprobabilistic_holdout_paths"] is True,
            "False uncertainty distribution inference")
    expected_summaries={(c["train_seed"],c["slots"],c["price_bound_class"])
                        for c in cases if c["slots"]!=8}
    demand(seen_summaries==expected_summaries,
           "Incomplete/replaced price stress or horizon summary")
    return {
      "protocol":"BIOGASFLEX_V0920_INDEPENDENT_RECTANGULAR_PROOF_AND_HELDOUT_KKT_V1",
      "status":"PASS_BOUNDED_PRICE_ROBUST_CHRONOLOGY_AND_INDEPENDENT_REPLAY_CERTIFICATES",
      "research_cases":len(certificates),
      "immutable_ex_ante_policies_audited":sum(c["policy_count"] for c in certificates),
      "selected_heldout_paths_replayed":sum(c["holdout_paths"] for c in certificates),
      "physical_source_quarter_hours_audited":sum(c["physical_rows_audited"] for c in certificates),
      "independent_fixed_pattern_LP_KKT_witnesses":sum(
          c["independently_certified_fixed_binary_LP_KKT"] for c in certificates),
      "exhaustively_certified_eight_slot_MILP_policies":sum(
          c["independent_global_8slot_patterns_verified"] for c in certificates),
      "real_bid_time_forecast_or_plant_calibration":False,
      "case_certificates":certificates,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",type=Path)
    x=p.parse_args()
    result=audit(json.loads(x.input.read_text(encoding="utf8")))
    if x.output:
        x.output.parent.mkdir(parents=True,exist_ok=True)
        x.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in result.items()
                      if k!="case_certificates"},indent=2))
