"""Independent source-paired CHP two-stage numerical scientific audit.

NO imports of biogasflex. It reconstructs all upstream experimental
price/load error pairs from the verified source report, the declared
synthetic heat/gas coupling, common first-stage binary states, and
an ALTERNATIVE fixed-binary LP. That LP is separately assembled but
still numerically solved by SciPy/HiGHS. Global 24-slot MILP binary
optimality is *solver reported only*, not proven by this audit.

Source real regional price/load pairs; plant gas/heat always synthetic.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

SOURCE_SHA="6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"
SRC_PROTOCOL="BIOGASFLEX_V0921_OPSD_SE3_REPORTED_LOAD_VS_ACTUAL_PRICE_PERSISTENCE_V1"
PROTOCOL="BIOGASFLEX_V0921_SOURCE_PAIRED_SE3_2D_ERRORS_SYNTHETIC_GAS_HEAT_TWO_STAGE_V1"
EXPECTED_ORDINALS=(8,40,72)
TRAIN_ORDINALS=(0,20,40,60,80,100,120,140)
DT=.25;N=24;START_HOUR=8
TOL=8e-5

def demand(ok,why):
    if not ok:raise AssertionError("v0.9.21 independent joint source and KKT audit: "+why)

def close(a,b,label,tol=TOL):
    demand(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,
           f"{label}: {a} versus {b}")

def _fhash(states,starts,stops):
    return hashlib.sha256(json.dumps([states,starts,stops],
        separators=(",",":")).encode("utf8")).hexdigest()

def _price_baseline(day):
    return [p-e for p,e in zip(day["delivery_price_eur_mwh"],
                               day["price_baseline_error_eur_mwh"])]

def _scales(source):
    x=source["training_metrics"]
    mp=x["price_lag_7day_baseline_mean_error_eur_mwh"]
    ml=x["published_TSO_load_forecast_mean_relative_error"]
    sp=math.sqrt(x["price_lag_7day_baseline_RMSE_eur_mwh"]**2-mp*mp)
    sl=math.sqrt(x["published_TSO_load_forecast_RMSE_relative"]**2-ml*ml)
    demand(sp>1 and 0<sl<.5,"Published empirical scales invalid")
    return mp,ml,sp,sl

def _rebuild(day,price_baseline,scales):
    mp,ml,sp,sl=scales
    p=[];g=[];h=[]
    for t in range(START_HOUR,START_HOUR+6):
        pe=day["price_baseline_error_eur_mwh"][t]
        le=day["regional_load_error_relative"][t]
        zp=max(-2.5,min(2.5,(pe-mp)/sp))
        zl=max(-2.5,min(2.5,(le-ml)/sl))
        gas=max(.78,min(1.22,1+.08*zp-.06*zl))
        heat=max(.105,min(.195,.15*(1+.10*zl+.03*zp)))
        p.extend([round(price_baseline[t]+pe,8)]*4)
        g.extend([round(gas,8)]*4)
        h.extend([round(heat,8)]*4)
    return p,g,h

def _check_scenario(sc,p,g,h,label):
    demand(len(p)==len(g)==len(h)==24,label+" wrong quarter horizon")
    for name,values in (("price_eur_mwh",p),
                        ("synthetic_gas_production_mw_lhv",g),
                        ("synthetic_site_heat_demand_mw_th",h)):
        declared=sc[name]
        demand(len(declared)==24,label+" incomplete scenario")
        for a,b in zip(declared,values):
            close(a,b,label+" "+name,2e-7)
    demand(sc["gas_and_site_heat_are_uncalibrated_functions_of_source_errors"] is True,
           "Attempted false claim of measured site gas/heat")

def _binary(solver):
    y=solver["binary_first_stage_on"];z=solver["starts"];v=solver["stops"]
    demand(len(y)==len(z)==len(v)==24,"Wrong binary schedule length")
    prior=1
    for i,(state,start,stop) in enumerate(zip(y,z,v)):
        demand(state in (0,1) and start in (0,1) and stop in (0,1),
               "Nonbinary or fractional first-stage generator")
        demand(start==int(prior==0 and state==1) and
               stop==int(prior==1 and state==0),
               "First-stage transition events not exact")
        if start or stop:
            demand(i+1<24 and y[i+1]==state,
                   "Minimum 0.5h ON/OFF dwell violated")
        prior=state
    demand(_fhash(y,z,v)==solver["first_stage_sha256"],
           "First-stage decision fingerprint forged or altered")
    close(solver["solver_mip_gap"],0.,"Original mixed-integer reported gap")
    demand(solver["second_stage_fully_observes_full_future_scenario"] is True,
           "Optimistic complete-path continuous recourse not disclosed")
    return y,z,v

def _physics(rows,sc,y,z=None,v=None):
    demand(len(rows)==24,"Source quarter-hour physical rows incomplete")
    gas=sc["synthetic_gas_production_mw_lhv"]
    heat=sc["synthetic_site_heat_demand_mw_th"]
    prices=sc["price_eur_mwh"]
    stock=.75
    prev_p=.4;previous_on=1
    cost_terms=[]
    for t,(row,source_g,source_h,price,state) in enumerate(zip(
            rows,gas,heat,prices,y)):
        demand(row["on"]==state,"Scenario violating first-stage locked commitment")
        if z is not None:
            demand(row["start"]==z[t] and row["stop"]==v[t],
                   "Scenario-dependent first-stage switching flags")
        u=row["gas_use_mw_lhv"];s=row["stock_end_mwh_lhv"]
        h=row["useful_chp_heat_mw_th"];a=row["backup_heat_mw_th"]
        w=row["dumped_heat_mw_th"]
        demand(all(math.isfinite(q) for q in (u,s,h,a,w,source_g,source_h,price)),
               "NaN or inf in gas/heat or price")
        close(s-stock,(source_g-u)*DT,"Scenario gas inventory conservation")
        close(.2*u,h+w,"Scenario thermal conversion")
        close(h+a,source_h,"Scenario thermal service")
        demand(-TOL<=s<=1.5+TOL and -TOL<=h<=source_h+TOL
               and -TOL<=a<=.2+TOL and -TOL<=w<=.4+TOL,
               "Invented finite gas/heat capacities exceeded")
        if not state:
            close(u,0,"Electric generator OFF must have zero fuel")
        else:
            demand(.5-TOL<=u<=2.+TOL,
                   "CHP minimum ON power or maximum nameplate exceeded")
        p=.4*u
        if state and previous_on:
            dt=.125 if t==0 else .25
            demand(abs(p-prev_p)<=.8*dt+TOL,
                   "Midpoint ON-to-ON ramp constraint violated")
        for field,expected in (
            ("price_eur_mwh",price),("gas_in_mw_lhv",source_g),
            ("heat_demand_mw_th",source_h)):
            close(row[field],expected,"Independent scenario input column")
        stock=s;prev_p=p;previous_on=state
        cost_terms.append(DT*(p*(price-.75)-6*a-w))
    close(stock,.75,"Source scenario cyclic terminal gas")
    return math.fsum(cost_terms)

def _independent_fixed_LP(sc,states):
    """Independent dense 5x24-variable LP and explicit primal–dual KKT."""
    n=24;u,s,h,a,w=[j*n for j in range(5)]
    nv=5*n
    c=np.zeros(nv);lower=np.zeros(nv);upper=np.full(nv,np.inf)
    eq=[];rhs=[];ineq=[];bub=[]
    def make(row):
        out=np.zeros(nv)
        for k,v in row.items():out[k]=v
        return out
    for t in range(n):
        demand(states[t] in (0,1),"Nonbinary original commitment")
        lower[u+t]=.5 if states[t] else 0.
        upper[u+t]=2. if states[t] else 0.
        upper[s+t]=1.5
        upper[h+t]=sc["synthetic_site_heat_demand_mw_th"][t]
        upper[a+t]=.2;upper[w+t]=.4
        c[u+t]=-(sc["price_eur_mwh"][t]-.75)*.4*.25
        c[a+t]=6.*.25;c[w+t]=.25
        balance={u+t:.25,s+t:1.}
        if t:balance[s+t-1]=-1.
        eq.append(make(balance))
        rhs.append(.25*sc["synthetic_gas_production_mw_lhv"][t]
                   +(.75 if t==0 else 0.))
        eq.append(make({u+t:.2,h+t:-1.,w+t:-1.}));rhs.append(0.)
        eq.append(make({h+t:1.,a+t:1.}))
        rhs.append(sc["synthetic_site_heat_demand_mw_th"][t])
        prior=1 if t==0 else states[t-1]
        if prior==states[t]==1:
            for sign in (1.,-1.):
                row={u+t:sign*.4}
                r=.8*(.125 if t==0 else .25)
                if t:row[u+t-1]=-sign*.4
                else:r+=sign*.4
                ineq.append(make(row));bub.append(r)
    row=np.zeros(nv);row[s+n-1]=1.
    eq.append(row);rhs.append(.75)
    eq=np.asarray(eq);rhs=np.asarray(rhs)
    au=np.asarray(ineq) if ineq else np.zeros((0,nv))
    bu=np.asarray(bub)
    sol=linprog(c,A_eq=eq,b_eq=rhs,
                A_ub=au if len(au) else None,
                b_ub=bu if len(bu) else None,
                bounds=list(zip(lower,upper)),method="highs")
    if not sol.success:
        return {"feasible":False,"objective_eur":None,
                "LP_optimum_KKT_verified":False}
    x=sol.x
    eqm=np.asarray(sol.eqlin.marginals)
    im=np.asarray(sol.ineqlin.marginals)
    lm=np.asarray(sol.lower.marginals)
    um=np.asarray(sol.upper.marginals)
    finite=np.isfinite(upper)
    residual={
      "equality":float(np.max(np.abs(eq@x-rhs))),
      "upper_inequality_excess":max(0.,float(np.max(au@x-bu))) if len(bu) else 0.,
      "lower_bound_excess":max(0.,float(np.max(lower-x))),
      "upper_bound_excess":max(0.,float(np.max(x[finite]-upper[finite]))),
      "stationarity":float(np.max(np.abs(c-eq.T@eqm-au.T@im-lm-um))),
      "duality_gap":abs(float(c@x)-float(rhs@eqm+bu@im+lower@lm+upper[finite]@um[finite])),
      "complementarity":max(
          abs(float((bu-au@x)@im)) if len(bu) else 0.,
          abs(float((x-lower)@lm)),
          abs(float((upper[finite]-x[finite])@um[finite]))),
    }
    demand(all(math.isfinite(v) and v<=TOL for v in residual.values()),
           "Independent LP KKT/duality residual violation: "+str(residual))
    demand((float(np.max(im))<=TOL if len(im) else True)
           and float(np.min(lm))>=-TOL and float(np.max(um))<=TOL,
           "Independent LP dual sign violation")
    return {"feasible":True,"objective_eur":-float(sol.fun),
            "LP_optimum_KKT_verified":True,"residuals":residual}

def _case_check(case,source,train,test):
    bundle=case["source_bundle"]
    ordinal=bundle["target_heldout_day_ordinal"]
    demand(ordinal in EXPECTED_ORDINALS and bundle["target_day_utc"]==test[ordinal]["date_utc"],
           "Unregistered/cherry-picked heldout date")
    demand(bundle["source_release_sha256"]==SOURCE_SHA,
           "Unrecognized original OPSD source integrity")
    demand(bundle["train_block_ordinals"]==list(TRAIN_ORDINALS),
           "Historical error block sampling changed")
    demand(bundle["forecast_issue_provenance"]=="PERSISTENCE_BASELINE_NOT_RECORDED_PRICE_FORECAST"
           and bundle["observed_regional_electric_load_forecast_vintage_verified"] is False,
           "False original forecast revision vintage")
    target=test[ordinal]
    pricebase=_price_baseline(target)
    nominal=bundle["nominal"]
    for i,p in enumerate(pricebase[8:14]):
        for j in range(4):
            close(nominal["price_eur_mwh"][4*i+j],p,
                  "Nominal price derived only from previous-week actual")
    demand(nominal["synthetic_gas_production_mw_lhv"]==[1.]*24
           and nominal["synthetic_site_heat_demand_mw_th"]==[.15]*24,
           "Invented deterministic nominal gas/heat coefficients changed")
    scales=_scales(source)
    samples=bundle["training_blocks"]
    demand(len(samples)==len(TRAIN_ORDINALS),"Missing training scenario")
    for ordinal_train,sc in zip(TRAIN_ORDINALS,samples):
        origin=train[ordinal_train]
        demand(sc["source_day_utc"]==origin["date_utc"]
               and sc["block_key"]==f"TRAIN_BLOCK_{ordinal_train:03d}",
               "Training source day was changed")
        price,gas,heat=_rebuild(origin,pricebase,scales)
        _check_scenario(sc,price,gas,heat,"Training historical day block")
        close_err_p=[v for v in origin["price_baseline_error_eur_mwh"][8:14]]
        close_err_l=[v for v in origin["regional_load_error_relative"][8:14]]
        for a,b in zip(sc["observed_price_persistence_errors_eur_mwh"],close_err_p):
            close(a,b,"Source-matched electricity price innovations",1e-10)
        for a,b in zip(sc["observed_regional_electric_load_errors_relative"],close_err_l):
            close(a,b,"Source-matched regional electricity load forecast errors",1e-10)
    hold=bundle["heldout_post_reveal"]
    demand(hold["source_day_utc"]==target["date_utc"],
           "Heldout source day mismatched")
    _check_scenario(hold,*_rebuild(target,pricebase,scales),"Heldout source price/load")
    reports=[]
    for name,key,scenario_collection in (
            ("nominal","nominal_first_stage",[nominal]),
            ("joint_block_maximin","joint_block_maximin_first_stage",samples)):
        result=case[key]
        y,z,v=_binary(result)
        original=result["scenario_second_stage_idealized_full_day_recourse"]
        demand(len(original)==len(scenario_collection),
               "Original model scenario count tampered")
        switch_cost=5*sum(z)+sum(v)
        reported=[]
        independent=[]
        for row,scenario in zip(original,scenario_collection):
            demand(row["block_key"]==scenario["block_key"],
                   "Scenario label/order swapped")
            val=_physics(row["rows"],scenario,y,z,v)
            close(val,row["contribution_excluding_switching_eur"],
                  "Original independently recomputed each-scenario cash")
            reported.append(val-switch_cost)
            cert=_independent_fixed_LP(scenario,y)
            demand(cert["feasible"],"Original optimized first-stage recourse infeasible")
            demand(cert["objective_eur"]+TOL>=val,
                   "Original recourse exceeded independent scenario LP optimum")
            independent.append(cert["objective_eur"]-switch_cost)
        close(min(reported),result["objective_maximin_eur"],
              "Original reported joint maximin objective")
        close(min(independent),result["objective_maximin_eur"],
              "Independent fixed first-stage min over optimal continuous recourse")
        holdcmp=case["holdout_comparison"][name]
        demand(holdcmp["first_stage_sha256_before_realization"]==result["first_stage_sha256"]
               and holdcmp["first_stage_remained_frozen"] is True,
               "Heldout realization changed first-stage binary commitment")
        hv=holdcmp["holdout_recourse"]
        separate=_independent_fixed_LP(hold,y)
        demand(hv["feasible"]==separate["feasible"],
               "Source-heldout physical recourse feasibility mismatch")
        if hv["feasible"]:
            realized=_physics(hv["schedule_rows"],hold,y)
            close(realized,hv["contribution_eur"],
                  "Reported heldout idealized LP recourse value")
            close(realized,separate["objective_eur"],
                  "Independent heldout LP recourse optimum")
            close(realized-switch_cost,
                  holdcmp["realized_idealized_contribution_eur"],
                  "Source-heldout synthetic cash proxy")
        else:
            demand(hv["schedule_rows"] is None and
                   holdcmp["realized_idealized_contribution_eur"] is None,
                   "Infeasible scenario was presented as feasible profit")
        reports.append({
            "policy":name,
            "frozen_binary_sha":result["first_stage_sha256"],
            "source_training_scenario_count":len(scenario_collection),
            "fixed_first_stage_conditional_optimality_certificates":len(independent),
            "heldout_idealized_recourse_KKT_verified":separate["LP_optimum_KKT_verified"],
            "heldout_feasible":separate["feasible"],
            "heldout_synthetic_contribution_eur":
                holdcmp["realized_idealized_contribution_eur"],
            "global_first_stage_binary_optimum_proven_independently":False,
        })
    return {"heldout_day_utc":target["date_utc"],
            "status":"PASS_SOURCE_PAIRED_NO_LOOKAHEAD_FIRST_STAGE_AND_KKT_RECOURSE",
            "conditional_policy_witnesses":reports}

def audit(source,study):
    demand(source["protocol"]==SRC_PROTOCOL
           and source["source"]["sha256"]==SOURCE_SHA
           and source["status"].startswith("SOURCE_SHA256_VERIFIED_"),
           "Missing publisher-pinned original SE3 source")
    demand(study["protocol"]==PROTOCOL
           and study["source_checksum_verified_expected"]==SOURCE_SHA
           and study["status"].startswith("PASS_MATHEMATICAL_TWO_STAGE_"),
           "Bad joint CHP scientific experiment identity")
    demand(study["joint_scenario_training_method"].startswith("EMPIRICAL_WHOLE_DAY_")
           and study["forecast_issue_gate_claim"] is False
           and study["site_gas_heat_empirically_calibrated"] is False
           and study["probabilistic_reliability_estimate"] is False,
           "Falsely identified real joint gas/heat or statistical model")
    demand(not any(study["provenance_limits"].values()),
           "Unfounded physical measurement or full market calibration")
    train=[x for x in source["complete_days"]
           if x["partition"]=="TRAIN_PRIOR_TO_2019_10_01"]
    test=[x for x in source["complete_days"]
          if x["partition"]=="HOLDOUT_FROM_2019_10_01"]
    ordinals=study["unseen_target_heldout_ordinals"]
    demand(ordinals in ([8],[8,40,72]),"Unregistered source holdout selection")
    demand(len(study["cases"])==len(ordinals),"Missing target report")
    results=[_case_check(case,source,train,test) for case in study["cases"]]
    demand([row["heldout_day_utc"] for row in results]==
           [test[k]["date_utc"] for k in ordinals],
           "Target reporting not in predeclared chronological order")
    return {
       "protocol":"BIOGASFLEX_V0921_INDEPENDENT_SOURCE_PAIRED_TWO_STAGE_KKT_AUDIT_V1",
       "status":"PASS_INDEPENDENT_SOURCE_PAIRED_CORRELATED_STRESS_AND_IDEALIZED_RECOURSE",
       "source_verified_original_raw_SHA256":SOURCE_SHA,
       "source_training_real_price_and_electric_load_error_days":len(train),
       "source_heldout_real_price_and_electric_load_error_days":len(test),
       "source_real_joint_observed_dimensions":2,
       "site_heat_gas_real_joint_observed_dimensions":0,
       "number_of_synthetic_CHP_heldout_targets":len(results),
       "first_stage_policy_count":2*len(results),
       "conditional_KKT_and_heldout_checks":sum(
           z["fixed_first_stage_conditional_optimality_certificates"]+1
           for r in results for z in r["conditional_policy_witnesses"]),
       "global_MILP_optimality_independently_certified":False,
       "probabilistic_reliability_inferred":False,
       "target_witnesses":results,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--study",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    options=p.parse_args()
    result=audit(json.loads(options.source.read_text(encoding="utf8")),
                 json.loads(options.study.read_text(encoding="utf8")))
    out=options.output.resolve()
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({k:v for k,v in result.items()
                      if k!="target_witnesses"},indent=2))
