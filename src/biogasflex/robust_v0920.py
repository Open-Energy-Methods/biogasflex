"""v0.9.20: frozen-decision, held-out synthetic-price CHP robustness.

This is EXACT maximin robust optimization for a RECTANGULAR set of
electricity prices ONLY (not physical uncertainty). Every generator
terminal MWh is nonnegative. Therefore for ANY physically feasible
fixed schedule x, its worst-case price vector is the elementwise lower
envelope, without enumerating all 2^N interval price vertices.

The robust schedule is obtained by applying the UNMODIFIED inherited
v0.9.7 MILP to that lower envelope. Nominal comparator uses a
predeclared forecast; held-out prices are not generated until after
both schedules are fixed. Ex-post hindsight reoptimization is labeled
a non-operational perfect-information oracle, never operational profit.

All gas, engine, backup, penalties, uncertainty envelopes and prices
are invented. No distribution, plant failure rate, bid-time real
prices, startup transients or biogas-engine calibration is claimed.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import platform
from pathlib import Path
from time import perf_counter

from .baseline import Interval
from .benchmark_v0919 import _config, BASE_PRICES
from .experimental_v097 import optimize_commitment_milp
from .public_chp_sources_v0916 import ROOT

PROTOCOL="BIOGASFLEX_V0920_RECTANGULAR_PRICE_UNCERTAINTY_HELDOUT_REPLAY_V1"
SOURCE="SYNTHETIC_NO_REAL_BID_TIME_MARKET_OR_BIOGAS_ENGINE_OBSERVATIONS"
TRAIN=(11,37)
BANDS=("reference","wide_stress")
HOLDOUT=(101,211,307)
HORIZONS=(24,96,192)
DT=.25
START=datetime(2020,1,1,tzinfo=timezone.utc)

def require(ok:bool,why:str)->None:
    if not ok:raise ValueError("v0.9.20: "+why)

def _nominal(seed:int,n:int)->list[float]:
    require(seed in TRAIN and n in (8,*HORIZONS),"Unregistered ex-ante seed or horizon")
    return [
       float(BASE_PRICES[i%24]+((seed*7+i*13+(i//4)*5)%9-4))
       for i in range(n)
    ]

def _envelope(nominal:list[float],band:str)->tuple[list[float],list[float]]:
    # TWO frozen research envelopes, not historical confidence intervals.
    # Retain the original reference study whose robust & nominal policies
    # were identical; deliberately add a separately named more severe
    # hypothetical stress, never select outcomes by heldout performance.
    require(band in BANDS,"Unregistered deterministic price stress design")
    if band=="reference":
        high,mid,low=55.,12.,8.
    else:
        high,mid,low=115.,20.,8.
    spreads=[high if BASE_PRICES[i%24]>=100. else
             mid if BASE_PRICES[i%24]>=15. else low
             for i in range(len(nominal))]
    lower=[max(0.,round(v-spread,8)) for v,spread in zip(nominal,spreads)]
    upper=[round(v+spread,8) for v,spread in zip(nominal,spreads)]
    return lower,upper

def _holdout(seed:int,source:int,lower:list[float],upper:list[float])->list[float]:
    require(seed in TRAIN and source in HOLDOUT,"Heldout scenario/seed not frozen")
    require(len(lower)==len(upper),"Mismatched uncertain price envelope")
    return [
        round(lo+(hi-lo)*(((source*17+i*23+(i//4)*13+seed*7)%97)/96),8)
        for i,(lo,hi) in enumerate(zip(lower,upper))
    ]

def _config_for(n:int,seed:int,band:str)->dict:
    # Deliberately frozen v0.9.19 hypothetical physical service,
    # not a tuned gas/heat performance or a model trained on holdouts.
    cfg=_config(seed,96 if n==192 else n,1.5,.15,5.)
    cfg["gas_production_mw_lhv"]=[1.]*n
    cfg["case_id"]=f"v0920_RECTANGULAR_SYNTHETIC_price_seed{seed}_{n}slots_{band}"
    cfg["forecast_source_status"]=SOURCE
    return cfg

def _intervals(prices:list[float])->list[Interval]:
    return [
        Interval(START+timedelta(minutes=15*i),p,DT,"SE3")
        for i,p in enumerate(prices)
    ]

def _solve(config:dict,price:list[float])->dict:
    t=perf_counter()
    original=optimize_commitment_milp(config,_intervals(price))
    return {
      "rows":original["hourly"],
      "reported_model_objective_eur":float(original["net_contribution_eur"]),
      "reported_mip_gap":original["solver"]["mip_gap"],
      "start_count":original["start_count"],
      "stop_count":original["stop_count"],
      "solver_wall_seconds":round(perf_counter()-t,6),
      "original_engine_model":original["model_type"],
      "reported_ledger":original["optimized_dispatch"],
    }

def _schedule_sha(rows:list[dict])->str:
    # Price and replay score excluded: commitment + gas/heat decisions only.
    physical=[
       [int(x["on"]),int(x["startup"]),int(x["shutdown"]),
        round(x["gas_use_mw_lhv"],8),round(x["stock_end_mwh_lhv"],8),
        round(x["useful_heat_mw_th"],8),
        round(x["aux_heat_mw_th"],8),round(x["dump_heat_mw_th"],8)]
       for x in rows
    ]
    return hashlib.sha256(json.dumps(physical,separators=(",",":"),
                             allow_nan=False).encode("utf8")).hexdigest()

def _value(rows:list[dict],prices:list[float],cfg:dict)->float:
    require(len(rows)==len(prices),"Schedule/price rows mismatched")
    lim=cfg["experimental_v097"]
    value=math.fsum(
        .25*(row["power_mw_e"]*(price-cfg["chp_variable_cost_eur_per_mwh_e"])
            -row["aux_heat_mw_th"]*cfg["aux_heat_cost_eur_per_mwh_th"]
            -row["dump_heat_mw_th"]*cfg["heat_dump_penalty_eur_per_mwh_th"])
        -lim["startup_cost_eur"]*row["startup"]
        -lim["shutdown_cost_eur"]*row["shutdown"]
        for row,price in zip(rows,prices)
    )
    require(math.isfinite(value),"Nonfinite replay contribution")
    return value

def _case(seed:int,n:int,band:str)->dict:
    cfg=_config_for(n,seed,band)
    nominal=_nominal(seed,n)
    lower,upper=_envelope(nominal,band)
    forecast_issued=(START-timedelta(hours=1)).isoformat()
    # Hard information barrier: no holdout path exists until both
    # fixed schedules are chosen and serialized in memory.
    policies={}
    for key,prices in (("nominal_forecast",nominal),
                       ("rectangular_maximin",lower)):
        sol=_solve(cfg,prices)
        sol["decision_sha256"]= _schedule_sha(sol["rows"])
        sol["optimization_price_input"]=key
        sol["frozen_objective_on_nominal_forecast_eur"]= _value(sol["rows"],nominal,cfg)
        sol["frozen_worst_case_rectangle_eur"]= _value(sol["rows"],lower,cfg)
        if abs(_value(sol["rows"],prices,cfg)-sol["reported_model_objective_eur"])>3e-5:
            raise RuntimeError("Original MILP objective and replay arithmetic disagree")
        policies[key]=sol
    if (policies["rectangular_maximin"]["frozen_worst_case_rectangle_eur"]+1e-5 <
        policies["nominal_forecast"]["frozen_worst_case_rectangle_eur"]):
        raise RuntimeError("Rectangular maximin underperforms a physically feasible nominal schedule")
    # All held-out prices originate here, AFTER fixed schedule decisions.
    holdouts=[]
    for holdout_seed in HOLDOUT:
        observed=_holdout(seed,holdout_seed,lower,upper)
        hindsight=_solve(cfg,observed)  # expressly nonoperational
        oracle=hindsight["reported_model_objective_eur"]
        values={}
        for name,policy in policies.items():
            realized=_value(policy["rows"],observed,cfg)
            regret=oracle-realized
            if regret<-2e-5:raise RuntimeError("Perfect-information hindsight below fixed schedule")
            values[name]={
               "frozen_schedule_decision_sha256":policy["decision_sha256"],
               "realized_synthetic_contribution_eur":realized,
               "perfect_information_regret_eur":max(0.,regret),
            }
        holdouts.append({
            "source_seed":holdout_seed,
            "prices_revealed_only_after_schedule_fixed_eur_mwh":observed,
            "perfect_information_oracle_not_operational":hindsight,
            "frozen_policy_evaluations":values,
        })
    return {
       "train_seed":seed,"slots":n,"price_bound_class":band,
       "duration_hours":n*.25,
       "forecast_issued_at_utc":forecast_issued,
       "service_begins_utc":START.isoformat(),
       "synthetic_electricity_price_zone_label_not_actual_market":"SE3",
       "input_provenance":SOURCE,
       "config":cfg,
       "nominal_train_forecast_eur_mwh":nominal,
       "rectangular_lower_price_eur_mwh":lower,
       "rectangular_upper_price_eur_mwh":upper,
       "policies":policies,
       "heldout_paths":holdouts,
       "rectangle_exactness_reason":"GENERATOR_TERMINAL_EXPORT_NONNEGATIVE_AND_OTHER_COSTS_PRICE_INVARIANT_SO_MIN_PRICE_VECTOR_IS_COMPONENTWISE_LOWER_BOUND",
       "no_real_bid_time_data_or_probability":True,
    }

def run(*,smoke:bool=False)->dict:
    cells=([(11,8,band) for band in BANDS] if smoke else
           [(seed,n,band) for seed in TRAIN for n in HORIZONS
            for band in BANDS]+[(11,8,band) for band in BANDS])
    cases=[_case(seed,n,band) for seed,n,band in cells]
    totals=[]
    for c in cases:
        if c["slots"]==8:continue
        rows=c["heldout_paths"]
        nom=[row["frozen_policy_evaluations"]["nominal_forecast"][
                 "realized_synthetic_contribution_eur"] for row in rows]
        rob=[row["frozen_policy_evaluations"]["rectangular_maximin"][
                 "realized_synthetic_contribution_eur"] for row in rows]
        regret_nom=[row["frozen_policy_evaluations"]["nominal_forecast"][
                        "perfect_information_regret_eur"] for row in rows]
        regret_rob=[row["frozen_policy_evaluations"]["rectangular_maximin"][
                        "perfect_information_regret_eur"] for row in rows]
        totals.append({
            "train_seed":c["train_seed"],"slots":c["slots"],
            "price_bound_class":c["price_bound_class"],
            "nominal_min_observed_heldout_eur":min(nom),
            "robust_min_observed_heldout_eur":min(rob),
            "nominal_arithmetic_heldout_mean_eur":math.fsum(nom)/len(nom),
            "robust_arithmetic_heldout_mean_eur":math.fsum(rob)/len(rob),
            "nominal_heldout_mean_regret_eur":math.fsum(regret_nom)/len(regret_nom),
            "robust_heldout_mean_regret_eur":math.fsum(regret_rob)/len(regret_rob),
            "nominal_exact_rectangular_worst_case_eur":
                c["policies"]["nominal_forecast"]["frozen_worst_case_rectangle_eur"],
            "robust_exact_rectangular_worst_case_eur":
                c["policies"]["rectangular_maximin"]["frozen_worst_case_rectangle_eur"],
            "average_refers_only_to_3_selected_nonprobabilistic_holdout_paths":True,
        })
    return {
       "protocol":PROTOCOL,
       "release_version":"0.9.20",
       "status":"PASS_SYNTHETIC_FROZEN_POLICY_BOUNDED_PRICE_OOS_PENDING_INDEPENDENT_AUDIT",
       "train_seeds":list(TRAIN[:1] if smoke else TRAIN),
       "price_stress_classes":list(BANDS),
       "unseen_price_evaluation_seeds":list(HOLDOUT),
       "horizons_quarter_hour_intervals":[8] if smoke else list(HORIZONS)+[8],
       "uncertainty_geometry":"RECTANGULAR_INDEPENDENT_INTERVAL_PRICE_BOUNDS_NOT_STATISTICAL_CONFIDENCE_INTERVAL",
       "confidence_level_or_probabilistic_reliability":None,
       "chronology":"FORECAST_AND_DECLARED_PRICE_BOUNDS_BEFORE_POLICY_SOLVE__HOLDOUT_PATHS_GENERATED_AND_REVEALED_AFTER_FIXED_DECISIONS__HINDSIGHT_ORACLE_SEPARATE",
       "cases":cases,
       "selected_holdout_descriptive_comparisons":totals,
       "runtime":{"python":platform.python_version(),"host":platform.platform(),
                  "not_a_repeatable_hardware_SLA":True},
       "claims":{"real_biogas_engine_calibrated":False,"actual_price_forecast_verified":False,
                 "stochastic_distribution_estimated":False,
                 "outage_probability_estimated":False,
                 "hindsight_is_operational":False,
                 "price_robustness_covers_gas_or_thermal_uncertainty":False,
                 "large_MILP_independently_global_optimum_certified":False},
    }

def write_out(result:dict,path:Path)->None:
    p=Path(path).resolve()
    require(not p.is_relative_to(ROOT.resolve()),
            "Full synthetic scenario report must stay OUTSIDE git repository")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--smoke",action="store_true",
                   help="Eight-quarter robust and nominal small oracle only")
    p.add_argument("--output",type=Path,default=None)
    a=p.parse_args()
    data=run(smoke=a.smoke)
    if a.output:write_out(data,a.output)
    print(json.dumps({
       "protocol":PROTOCOL,"status":data["status"],
       "case_count":len(data["cases"]),
       "synthetic_holdout_path_count":sum(len(c["heldout_paths"]) for c in data["cases"]),
       "policy_count":sum(len(c["policies"]) for c in data["cases"]),
       "selected_heldout_comparisons":data["selected_holdout_descriptive_comparisons"],
       "full_rows":str(a.output) if a.output else None,
       "field_calibrated":False,
    },indent=2,allow_nan=False))

if __name__=="__main__":
    main()
