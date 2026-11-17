"""BiogasFlex v0.9.21: source-paired joint uncertainty + explicitly fictional CHP recourse.

Public hourly source supplies TWO genuine joint time series: a seven-day
persistence *price baseline* error and an ENTSO-E reported regional
electricity-load forecast error. Full 6-hour day blocks preserve their
observed cross-variable and serial pairing. They are not published
site-heat or digester-gas forecast errors.

Fictional heat and gas deviations are *declared functions* of the SAME
two source-error coordinates. This creates a correlated three-channel
experiment, NOT a measured joint 3D distribution or statistically
calibrated site forecast.

Two-stage stochastic MAXIMIN MILP: one shared ahead-of-time binary
CHP commitment for all training blocks; scenario-conditioned gas,
electrical power, heat and stock are perfect-information continuous
RECOURSE. The latter is deliberately optimistic: not a credible
fully causal online or accepted-grid-award dispatch policy.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp, linprog
from scipy.sparse import lil_matrix

from .opsd_v0921 import (PROTOCOL as SOURCE_PROTOCOL,
                         SOURCE_SHA256, TRAIN_END, START)
from .public_chp_sources_v0916 import ROOT

PROTOCOL="BIOGASFLEX_V0921_SOURCE_PAIRED_SE3_2D_ERRORS_SYNTHETIC_GAS_HEAT_TWO_STAGE_V1"
METHOD="EMPIRICAL_WHOLE_DAY_BLOCKS_WITH_DETERMINISTIC_UNCALIBRATED_GAS_AND_HEAT_PROXY_COUPLINGS"
TRAIN_ORDINALS=(0,20,40,60,80,100,120,140)
HELDOUT_ORDINALS=(8,40,72)
HOUR_START=8
HOURS=6
N=24
DT=.25
RATING=.8
ETA_E=.4
ETA_H=.2
STOCK_CAP=1.5
STOCK_INITIAL=.75
INITIAL_ON=1
INITIAL_POWER=.4
MIN_ON=.2
RAMP=.8
HEAT_BACKUP_CAP=.20
HEAT_DUMP_CAP=.40
START_COST=5.
STOP_COST=1.
AUX_COST=6.
DUMP_COST=1.
VAR_COST=.75
GAS_BASE=1.
HEAT_BASE=.15
ABS_TOL=5e-5
MAX_SCENARIOS=8

def demand(ok,why):
    if not ok:raise ValueError("v0.9.21 correlated joint CHP: "+why)

def _source_validate(source:dict)->tuple[list,list]:
    demand(source["protocol"]==SOURCE_PROTOCOL,
           "Wrong source-provenance protocol")
    demand(source["status"]=="SOURCE_SHA256_VERIFIED_REPORTED_FORECAST_ERROR_SNAPSHOT_NOT_GATE_VINTAGE",
           "Source archive not provenance verified")
    src=source["source"]
    demand(src["sha256"]==SOURCE_SHA256 and
           src["geography"]=="Sweden SE3 bidding zone" and
           src["source_resolution"]=="60 minutes",
           "Wrong publisher SHA256 or SE3 hourly source")
    demand(src["last_per_observation_forecast_publication_verified"] is False
           and src["electricity_price_original_forecast_column_available"] is False
           and src["gas_production_or_heat_load_site_measurement_present"] is False,
           "Wrongly claimed historical price/heat/gas observation vintages")
    train=[d for d in source["complete_days"]
           if d["partition"]=="TRAIN_PRIOR_TO_2019_10_01"]
    test=[d for d in source["complete_days"]
          if d["partition"]=="HOLDOUT_FROM_2019_10_01"]
    demand(len(train)>max(TRAIN_ORDINALS) and len(test)>max(HELDOUT_ORDINALS),
           "Not enough source-verified UTC day blocks")
    dates=[d["date_utc"] for d in source["complete_days"]]
    demand(dates==sorted(set(dates)),"Source dates duplicated or reordered")
    for d in train:
        demand(d["date_utc"]<"2019-10-01","Training day leaks future holdout date")
    for d in test:
        demand(d["date_utc"]>="2019-10-01","Heldout day leaks training")
    for day in source["complete_days"]:
        demand(all(len(day[k])==24 for k in (
            "price_baseline_error_eur_mwh",
            "regional_load_error_relative",
            "delivery_price_eur_mwh",
            "regional_load_forecast_mw",
            "regional_load_actual_mw")),
            "Daily historical source block is not exactly 24 UTC hours")
    demand(source["quality"]["training_complete_days"]==len(train)
           and source["quality"]["heldout_complete_days"]==len(test),
           "Original complete-day counts do not match")
    return train,test

def _standardizers(source:dict)->tuple[float,float,float,float]:
    t=source["training_metrics"]
    mp=t["price_lag_7day_baseline_mean_error_eur_mwh"]
    ml=t["published_TSO_load_forecast_mean_relative_error"]
    sp=max(1e-9,math.sqrt(max(0.,t["price_lag_7day_baseline_RMSE_eur_mwh"]**2-mp**2)))
    sl=max(1e-9,math.sqrt(max(0.,t["published_TSO_load_forecast_RMSE_relative"]**2-ml**2)))
    demand(sp>1 and 0<sl<.5,"Implausible source scale")
    return mp,ml,sp,sl

def _scenario(day:dict,nominal_price_hourly:list[float],scales:tuple,*,key:str)->dict:
    # Preserve each source day as ONE 6-hour multichannel BLOCK:
    # never draw hourly or price/load dimensions separately.
    mp,ml,sp,sl=scales
    prices=[];gas=[];heat=[];real_p=[];real_load=[];latents=[]
    for hour in range(HOUR_START,HOUR_START+HOURS):
        pe=float(day["price_baseline_error_eur_mwh"][hour])
        le=float(day["regional_load_error_relative"][hour])
        zp=max(-2.5,min(2.5,(pe-mp)/sp))
        zl=max(-2.5,min(2.5,(le-ml)/sl))
        # *** Hypothetical physical couplings, NOT identified from OPSD ***
        # Distinct gas/heat trajectories depend on common source shocks.
        g=max(.78,min(1.22,GAS_BASE*(1+.08*zp-.06*zl)))
        h=max(.105,min(.195,HEAT_BASE*(1+.10*zl+.03*zp)))
        p=nominal_price_hourly[hour]+pe
        prices.extend([round(p,8)]*4)
        gas.extend([round(g,8)]*4)
        heat.extend([round(h,8)]*4)
        real_p.append(pe);real_load.append(le)
        latents.append([round(zp,8),round(zl,8)])
    demand(len(prices)==len(gas)==len(heat)==N,"Bad 60min-to-15min replay")
    return {
       "block_key":key,
       "source_day_utc":day["date_utc"],
       "source_UTC_hour_window":"08:00–14:00 (6 source hourly periods, each held constant for 4 modeled quarter-hours)",
       "observed_price_persistence_errors_eur_mwh":real_p,
       "observed_regional_electric_load_errors_relative":real_load,
       "standardized_source_pair_latents":latents,
       "price_eur_mwh":prices,
       "synthetic_gas_production_mw_lhv":gas,
       "synthetic_site_heat_demand_mw_th":heat,
       "gas_and_site_heat_are_uncalibrated_functions_of_source_errors":True,
       "probability_weight_or_forecast_confidence":None,
    }

def build_source_scenarios(source:dict,*,target_ordinal:int=8)->dict:
    train,test=_source_validate(source)
    demand(target_ordinal in HELDOUT_ORDINALS,"Predeclared heldout target required")
    target=test[target_ordinal]
    # Observed day-ahead market clearing price minus seven-day lag
    # persistence error provides the strictly historical model baseline.
    price_persistence=[p-e for p,e in zip(
        target["delivery_price_eur_mwh"],target["price_baseline_error_eur_mwh"])]
    demand(len(price_persistence)==24,"Missing ex-ante persistence price forecast")
    scales=_standardizers(source)
    samples=[_scenario(train[i],price_persistence,scales,
                       key=f"TRAIN_BLOCK_{i:03d}") for i in TRAIN_ORDINALS]
    # Deliberately DO NOT construct or return a heldout scenario yet.
    # At this point only a historical lagged-price baseline is
    # available, and the training residual blocks. The later
    # evaluator must call reveal_heldout() after both solves.
    nominal={
       "block_key":"NOMINAL_HYPOTHETICAL_GAS_HEAT_LAGGED_PRICE",
       "source_day_utc":None,
       "price_eur_mwh":[price_persistence[i] for i in range(HOUR_START,HOUR_START+HOURS)
                         for _ in range(4)],
       "synthetic_gas_production_mw_lhv":[GAS_BASE]*N,
       "synthetic_site_heat_demand_mw_th":[HEAT_BASE]*N,
       "gas_and_site_heat_are_uncalibrated_functions_of_source_errors":True,
    }
    return {
      "target_day_utc":target["date_utc"],"target_heldout_day_ordinal":target_ordinal,
      "source_release_sha256":SOURCE_SHA256,
      "train_block_ordinals":list(TRAIN_ORDINALS),
      "historical_price_baseline_method":"PREVIOUS_7DAY_SE3_DAY_AHEAD_CLEARING_PRICE_AVAILABLE_BEFORE_TARGET_DAY",
      "forecast_issue_provenance":"PERSISTENCE_BASELINE_NOT_RECORDED_PRICE_FORECAST",
      "observed_regional_electric_load_forecast_vintage_verified":False,
      "source_training_forecast_error":source["training_metrics"],
      "source_heldout_forecast_error":source["heldout_metrics"],
      "frozen_standardizers":{"price_mean_eur_mwh":scales[0],
                             "load_mean_relative":scales[1],
                             "price_std_eur_mwh":scales[2],
                             "load_std_relative":scales[3]},
      "nominal":nominal,"training_blocks":samples,
      "heldout_not_generated_at_forecast_time":True,
    }

def reveal_heldout(source:dict,*,target_ordinal:int)->dict:
    """Construct held-out actual-price/load-error block ONLY after solves.

    The caller's ordering is independently checked in run(): this function
    is absent from the ex-ante bundle and from optimizer inputs.
    """
    train,test=_source_validate(source)
    demand(target_ordinal in HELDOUT_ORDINALS,"Unlisted evaluation day")
    target=test[target_ordinal]
    base=[p-e for p,e in zip(target["delivery_price_eur_mwh"],
                            target["price_baseline_error_eur_mwh"])]
    return _scenario(target,base,_standardizers(source),
                     key=f"HELDOUT_REALIZED_TARGET_{target_ordinal:03d}")

def _milp_bundle(scenarios:list[dict],*,fixed_binary:list[int]|None=None)->dict:
    """8-block two-stage MILP with COMMON binary first-stage commitment.

    Each scenario has entirely separate physical recourse, including
    within-horizon future-known prices/gas/heat: optimistic second stage.
    Variable order: common y/z/v; scenario u/s/h/a/w; last variable
    scenario-minimum objective q (only in joint maximin).
    """
    S=len(scenarios)
    demand(1<=S<=MAX_SCENARIOS,"Too many source blocks for frozen MILP")
    for sc in scenarios:
        for k in ("price_eur_mwh","synthetic_gas_production_mw_lhv",
                  "synthetic_site_heat_demand_mw_th"):
            demand(len(sc[k])==N,"Wrong scenario length")
    with_q=(S>1)
    ys,zs,vs=0,N,2*N
    base=3*N
    total=base+S*5*N+(1 if with_q else 0)
    qix=total-1 if with_q else -1
    c=np.zeros(total);lb=np.zeros(total);ub=np.full(total,np.inf)
    integrality=np.zeros(total,dtype=int)
    for t in range(N):
        for i in (ys+t,zs+t,vs+t):
            ub[i]=1
            integrality[i]=1
        c[zs+t]=START_COST
        c[vs+t]=STOP_COST
        if fixed_binary is not None:
            demand(len(fixed_binary)==N and fixed_binary[t] in (0,1),
                   "Fixed CHP commitment is not binary")
            lb[ys+t]=ub[ys+t]=fixed_binary[t]
    if with_q:
        lb[qix]=-np.inf
        c[qix]=-1
    rows=[];lows=[];highs=[]
    def add(v:dict,lo=-np.inf,hi=np.inf):
        rows.append(v);lows.append(float(lo));highs.append(float(hi))
    for t in range(N):
        prev=INITIAL_ON if t==0 else None
        trans={zs+t:1.,vs+t:-1.,ys+t:-1.}
        if t:trans[ys+t-1]=1.
        add(trans,lo=-(prev if t==0 else 0.),hi=-(prev if t==0 else 0.))
        add({zs+t:1,ys+t:-1},hi=0)
        add({vs+t:1,ys+t:1},hi=1)
        add({zs+t:1,vs+t:1},hi=1)
        if t==0:
            add({zs:1},hi=0)
            add({vs:1},hi=1)
        else:
            add({zs+t:1,ys+t-1:1},hi=1)
            add({vs+t:1,ys+t-1:-1},hi=0)
        if t==N-1:
            add({zs+t:1},hi=0)
            add({vs+t:1},hi=0)
        else:
            # Exactly 0.5h dwell: event occurs at slot start; next
            # quarter-hour has the same mandatory binary state.
            add({zs+t:1,ys+t+1:-1},hi=0)
            add({vs+t:1,ys+t+1:1},hi=1)
    for j,sc in enumerate(scenarios):
        u,s,h,a,w=[base+(j*5+k)*N for k in range(5)]
        prices=sc["price_eur_mwh"]
        gas=sc["synthetic_gas_production_mw_lhv"]
        heat=sc["synthetic_site_heat_demand_mw_th"]
        objective={}
        for t in range(N):
            for ix,v in ((u+t,2.),(s+t,STOCK_CAP),(h+t,heat[t]),
                         (a+t,HEAT_BACKUP_CAP),(w+t,HEAT_DUMP_CAP)):
                ub[ix]=v
            # Independent scenario gas balance, end stock cyclic.
            balance={u+t:DT,s+t:1.}
            if t:balance[s+t-1]=-1.
            rhs=gas[t]*DT+(STOCK_INITIAL if t==0 else 0.)
            add(balance,lo=rhs,hi=rhs)
            add({u+t:ETA_H,h+t:-1.,w+t:-1.},lo=0,hi=0)
            add({h+t:1.,a+t:1.},lo=heat[t],hi=heat[t])
            add({u+t:ETA_E,ys+t:-RATING},hi=0)
            add({u+t:ETA_E,ys+t:-MIN_ON},lo=0)
            # Within-on midpoint ramp; off transitions deliberately
            # exempted, NOT physical startup/slip modeling.
            for sign in (1.,-1.):
                if t:
                    rr={u+t:sign*ETA_E,u+t-1:-sign*ETA_E,
                        ys+t:RATING,ys+t-1:RATING}
                    rhsr=RAMP*DT+2*RATING
                else:
                    rr={u+t:sign*ETA_E,ys+t:RATING}
                    rhsr=RAMP*(DT/2)+RATING*(2-INITIAL_ON)+sign*INITIAL_POWER
                add(rr,hi=rhsr)
            # The scenario-dependent part of modeled operating
            # contribution, no start/stop (shared in objective).
            objective[u+t]=-ETA_E*(prices[t]-VAR_COST)*DT
            objective[a+t]=AUX_COST*DT
            objective[w+t]=DUMP_COST*DT
            if not with_q:
                c[u+t]=objective[u+t]
                c[a+t]=objective[a+t]
                c[w+t]=objective[w+t]
        add({s+N-1:1.},lo=STOCK_INITIAL,hi=STOCK_INITIAL)
        if with_q:
            objective[qix]=1.
            add(objective,hi=0)
    mat=lil_matrix((len(rows),total),dtype=float)
    for k,row in enumerate(rows):
        for ix,val in row.items():
            mat[k,ix]=val
    begin=perf_counter()
    sol=milp(c,integrality=integrality,bounds=Bounds(lb,ub),
             constraints=LinearConstraint(mat.tocsr(),lows,highs),
             options={"mip_rel_gap":0.,"time_limit":90.})
    demand(sol.success and sol.status==0 and sol.x is not None,
           "Joint stochastic MILP not proven optimal: "+str(sol.message))
    x=sol.x
    states=[int(round(x[ys+t])) for t in range(N)]
    starts=[int(round(x[zs+t])) for t in range(N)]
    stops=[int(round(x[vs+t])) for t in range(N)]
    result=[]
    for j,sc in enumerate(scenarios):
        u,s,h,a,w=[base+(j*5+k)*N for k in range(5)]
        rows=[]
        for t in range(N):
            rows.append({
                "on":states[t],"start":starts[t],"stop":stops[t],
                "gas_use_mw_lhv":float(x[u+t]),
                "stock_end_mwh_lhv":float(x[s+t]),
                "useful_chp_heat_mw_th":float(x[h+t]),
                "backup_heat_mw_th":float(x[a+t]),
                "dumped_heat_mw_th":float(x[w+t]),
                "price_eur_mwh":sc["price_eur_mwh"][t],
                "gas_in_mw_lhv":sc["synthetic_gas_production_mw_lhv"][t],
                "heat_demand_mw_th":sc["synthetic_site_heat_demand_mw_th"][t],
            })
        contribution=_ledger(rows)
        result.append({"block_key":sc["block_key"],"rows":rows,
                       "contribution_excluding_switching_eur":contribution})
    switching=START_COST*sum(starts)+STOP_COST*sum(stops)
    cash=[v["contribution_excluding_switching_eur"]-switching for v in result]
    optimized=float(-sol.fun)
    if with_q:
        demand(abs(optimized-(min(cash)))<=5e-4,
               "Joint maximin objective not equal to audited scenario minimum")
        demand(abs(x[qix]-min(v["contribution_excluding_switching_eur"] for v in result))<=5e-4,
               "Worst-case scenario epigraph coefficient incorrect")
    else:
        demand(abs(optimized-cash[0])<=5e-4,
               "Single-scenario solver cashflow objective discrepancy")
    return {
        "binary_first_stage_on":states,"starts":starts,"stops":stops,
        "first_stage_sha256":_first_stage_hash(states,starts,stops),
        "scenario_second_stage_idealized_full_day_recourse":result,
        "per_scenario_cashflow_proxy_eur":cash,
        "objective_maximin_eur":optimized,
        "solver_mip_gap":float(sol.mip_gap),
        "single_stage_nominal_only":not with_q,
        "solver_wall_seconds":round(perf_counter()-begin,6),
        "second_stage_fully_observes_full_future_scenario":True,
    }

def _first_stage_hash(states,starts,stops)->str:
    return hashlib.sha256(json.dumps([states,starts,stops],
        separators=(",",":")).encode("utf8")).hexdigest()

def _ledger(rows:list[dict])->float:
    return math.fsum(
        DT*(ETA_E*r["gas_use_mw_lhv"]*(r["price_eur_mwh"]-VAR_COST)
            -AUX_COST*r["backup_heat_mw_th"]
            -DUMP_COST*r["dumped_heat_mw_th"])
        for r in rows)

def _fixed_recourse(scenario:dict,states:list[int])->dict:
    """Continuous recourse via independently vectorized LP construction.

    Binary pattern locked for all gas/heat/price scenarios, but the
    entire realized path is visible to the continuous recourse
    optimizer. Not an actual online nonanticipative plant controller.
    """
    demand(len(states)==N,"Missing first-stage binary commitments")
    cfg=scenario
    u,s,h,a,w=[j*N for j in range(5)]
    nv=5*N
    c=np.zeros(nv);lb=np.zeros(nv);ub=np.full(nv,np.inf)
    eq=[];bq=[];ineq=[];bi=[]
    for t in range(N):
        state=states[t]
        demand(state in (0,1),"Nonbinary first stage")
        lb[u+t]=.5 if state else 0.
        ub[u+t]=2. if state else 0.
        ub[s+t]=STOCK_CAP
        ub[h+t]=cfg["synthetic_site_heat_demand_mw_th"][t]
        ub[a+t]=HEAT_BACKUP_CAP;ub[w+t]=HEAT_DUMP_CAP
        c[u+t]=-ETA_E*(cfg["price_eur_mwh"][t]-VAR_COST)*DT
        c[a+t]=AUX_COST*DT;c[w+t]=DUMP_COST*DT
        def v(row):
            a=np.zeros(nv)
            for idx,value in row.items():a[idx]=value
            return a
        balance={u+t:DT,s+t:1.}
        if t:balance[s+t-1]=-1.
        eq.append(v(balance))
        bq.append(DT*cfg["synthetic_gas_production_mw_lhv"][t]
                  +(STOCK_INITIAL if t==0 else 0.))
        eq.append(v({u+t:ETA_H,h+t:-1.,w+t:-1.}));bq.append(0.)
        eq.append(v({h+t:1.,a+t:1.}));bq.append(cfg["synthetic_site_heat_demand_mw_th"][t])
        previous=INITIAL_ON if t==0 else states[t-1]
        if previous==state==1:
            dt=DT/2 if t==0 else DT
            for sign in (1.,-1.):
                ramp={u+t:sign*ETA_E}
                rhs=RAMP*dt
                if t:ramp[u+t-1]=-sign*ETA_E
                else:rhs+=sign*INITIAL_POWER
                ineq.append(v(ramp));bi.append(rhs)
    terminal=np.zeros(nv);terminal[s+N-1]=1.
    eq.append(terminal);bq.append(STOCK_INITIAL)
    sol=linprog(c,A_eq=np.asarray(eq),b_eq=bq,
                A_ub=np.asarray(ineq) if ineq else None,
                b_ub=bi if bi else None,
                bounds=list(zip(lb,ub)),method="highs")
    if not sol.success:
        return {"feasible":False,"reason":str(sol.message),
                "contribution_eur":None,"schedule_rows":None}
    x=sol.x
    rows=[{
        "on":states[t],
        "gas_use_mw_lhv":float(x[u+t]),
        "stock_end_mwh_lhv":float(x[s+t]),
        "useful_chp_heat_mw_th":float(x[h+t]),
        "backup_heat_mw_th":float(x[a+t]),
        "dumped_heat_mw_th":float(x[w+t]),
        "price_eur_mwh":cfg["price_eur_mwh"][t],
        "gas_in_mw_lhv":cfg["synthetic_gas_production_mw_lhv"][t],
        "heat_demand_mw_th":cfg["synthetic_site_heat_demand_mw_th"][t],
    } for t in range(N)]
    value=-float(sol.fun)
    demand(abs(_ledger(rows)-value)<=5e-5,
           "Numerical recourse LP and reconstructed ledger mismatch")
    return {"feasible":True,"contribution_eur":value,
            "schedule_rows":rows}

def run(source:dict,*,smoke:bool=False)->dict:
    targets=(HELDOUT_ORDINALS[:1] if smoke else HELDOUT_ORDINALS)
    cases=[]
    for ordinal in targets:
        bundle=build_source_scenarios(source,target_ordinal=ordinal)
        # Strict no-lookahead barrier: heldout source innovations do not
        # even exist as optimizer inputs or as a generated scenario until
        # BOTH first-stage policies have been solved and hashed.
        demand("heldout_post_reveal" not in bundle and
               bundle["heldout_not_generated_at_forecast_time"] is True,
               "A heldout price/load path leaked into ex-ante bundle")
        nominal=_milp_bundle([bundle["nominal"]])
        joint=_milp_bundle(bundle["training_blocks"])
        for policy in (nominal,joint):
            demand(len(policy["first_stage_sha256"])==64,
                   "Pre-reveal binary decision was not frozen")
        realized=reveal_heldout(source,target_ordinal=ordinal)
        bundle["heldout_post_reveal"]=realized
        comparisons={}
        for name,opt in (("nominal",nominal),("joint_block_maximin",joint)):
            result=_fixed_recourse(realized,opt["binary_first_stage_on"])
            starts=START_COST*sum(opt["starts"])+STOP_COST*sum(opt["stops"])
            comparisons[name]={
              "first_stage_sha256_before_realization":opt["first_stage_sha256"],
              "holdout_recourse":result,
              "realized_idealized_contribution_eur":
                    result["contribution_eur"]-starts if result["feasible"] else None,
              "binary_switching_cost_eur":starts,
              "first_stage_remained_frozen":True,
            }
        cases.append({"source_bundle":bundle,"nominal_first_stage":nominal,
                      "joint_block_maximin_first_stage":joint,
                      "holdout_comparison":comparisons})
    return {
      "protocol":PROTOCOL,
      "status":"PASS_MATHEMATICAL_TWO_STAGE_JOINT_BLOCK_STRESS_PENDING_INDEPENDENT_AUDIT",
      "source_checksum_verified_expected":SOURCE_SHA256,
      "source_empirical_dimensions":[
          "real_SE3_day_ahead_auction_price_minus_7day_persistence_baseline",
          "real_SE3_published_TSO_load_forecast_error_from_snapshot_NOT_vintage_attested"],
      "synthetic_uncalibrated_dimensions":[
          "site_biogas_production_from_2D_shared_latent",
          "site_heat_demand_from_2D_shared_latent"],
      "joint_scenario_training_method":METHOD,
      "historical_day_block_preservation_hours":HOURS,
      "forecast_issue_gate_claim":False,
      "site_gas_heat_empirically_calibrated":False,
      "two_stage_first_stage":"SAME_BINARY_COMMITMENT_FOR_ALL_TRAINING_BLOCKS",
      "second_stage":"FULL_SCENARIO_PATH_CONTINUOUS_PERFECT_INFORMATION_RECOURSE_OPTIMISTIC_BOUND",
      "probabilistic_reliability_estimate":False,
      "unseen_target_heldout_ordinals":list(targets),
      "cases":cases,
      "provenance_limits":{
         "price_is_original_vendor_forecast":False,
         "published_load_forecast_revision_as_of_gate_proven":False,
         "region_load_equals_CHp_site_heat":False,
         "gas_pressure_transients_or_engine_efficiency_calibrated":False,
         "real_energy_delivery_contract_or_market_earnings":False,
      },
    }

def write_out(result,path:Path)->None:
    p=Path(path).resolve()
    demand(not p.is_relative_to(ROOT.resolve()),"Report must be outside git checkout")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--smoke",action="store_true")
    opt=p.parse_args()
    source=json.loads(opt.source.read_text(encoding="utf8"))
    result=run(source,smoke=opt.smoke)
    write_out(result,opt.output)
    print(json.dumps({
      "status":result["status"],
      "source_sha256":SOURCE_SHA256,
      "heldout_study_targets":len(result["cases"]),
      "training_empirical_day_blocks_per_target":len(TRAIN_ORDINALS),
      "main_joint_first_stage_objectives_eur":[
          c["joint_block_maximin_first_stage"]["objective_maximin_eur"]
          for c in result["cases"]],
      "holdout_idealized_recourse_comparisons":[{
          "date":c["source_bundle"]["target_day_utc"],
          "nominal":c["holdout_comparison"]["nominal"]["realized_idealized_contribution_eur"],
          "joint":c["holdout_comparison"]["joint_block_maximin"]["realized_idealized_contribution_eur"]
      } for c in result["cases"]],
      "real_gas_heat_joint_measurements":False,
      "real_se3_price_forecast_vintage_proven":False,
    },indent=2,allow_nan=False))

if __name__=="__main__":
    main()
