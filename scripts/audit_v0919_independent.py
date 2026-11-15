"""Independent v0.9.19 optimum/feasibility audit with explicit dual KKT checks.

This file deliberately imports no biogasflex package. It reconstructs
a continuous linear-program model directly from primitive hypothetical
inputs. SciPy/HiGHS is still used as a numerical backend; independence
here means independent formulation plus checked primal+dual residuals,
NOT an independent optimization solver.

The original on/off MILP is checked with a second LP formulation for its
chosen binary pattern, and 8-slot cases are globally checked via exhaustive
2^8 binary pattern enumeration and LP solves.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
from itertools import product
import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

PROTOCOL="BIOGASFLEX_V0919_ENDOGENOUS_COMMITMENT_FINITE_DESIGN_AND_DUAL_V1"
PROVENANCE="FULLY_SYNTHETIC_DETERMINISTIC_NONPROBABILISTIC_2026_RESEARCH_DESIGN"
SEEDS=(11,37,59)
CAPS=(0.,.5,1.5)
BACKUP=(0.,.15)
STARTS=(5.,15.)
PRICES=(5.,5.,5.,5.,120.,120.,120.,120.,120.,120.,15.,15.,
        15.,15.,15.,15.,110.,110.,110.,110.,110.,110.,110.,110.)
TOL=3e-5

def demand(ok,msg):
    if not ok:raise AssertionError("v0.9.19 external independent audit: "+msg)

def near(a,b,label,tol=TOL):
    demand(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,
           f"{label}: {a} versus {b}")

def _predeclare(case):
    seed=case["seed"];n=case["slots"];cap=case["capacity_mwh_lhv"]
    backup=case["auxiliary_capacity_mw_th"];cost=case["startup_cost_eur"]
    model=case["model"];cfg=case["config"]
    demand(seed in SEEDS and n in (8,24,96),"Unexpected predeclared seed/horizon")
    demand(cap in CAPS and backup in BACKUP and cost in STARTS,
           "Unexpected finite design value")
    demand(model in ("ALWAYS_ON_RAMP_LP","ENDOGENOUS_ON_OFF_MILP"),
           "Unexpected model type")
    demand(cfg["input_provenance"]==PROVENANCE
           and cfg["design_seed_not_a_probability_draw"]==seed,
           "Invented input provenance removed")
    demand(cfg["gas_production_mw_lhv"]==[1.]*n
           and cfg["gas_input_mw_lhv"]==1.
           and cfg["electric_rating_mw"]==.8
           and cfg["electric_efficiency_lhv"]==.4
           and cfg["thermal_efficiency_lhv"]==.2,
           "Changed predeclared gas source/electric/thermal conversion")
    demand(cfg["gas_storage_capacity_mwh_lhv"]==cap
           and cfg["initial_gas_inventory_mwh_lhv"]==cap/2
           and cfg["fixed_flaring_mw_lhv"]==0.
           and cfg["fixed_losses_mw_lhv"]==0.
           and cfg["heat_service_model"]=="instantaneous_heat_service_no_thermal_store_v07"
           and cfg["heat_demand_mw_th"]==.15
           and cfg["aux_heat_capacity_mw_th"]==backup
           and cfg["heat_dump_capacity_mw_th"]==.35
           and cfg["aux_heat_cost_eur_per_mwh_th"]==6.
           and cfg["heat_dump_penalty_eur_per_mwh_th"]==1.
           and cfg["chp_variable_cost_eur_per_mwh_e"]==.75,
           "Changed predeclared heat/gas/storage/expense assumptions")
    intervals=case["timestamps_utc"]
    source_prices=case["prices_eur_mwh"]
    demand(len(intervals)==len(source_prices)==len(case["rows"])==n,
           "Length mismatch in source rows")
    for i,(stamp,price) in enumerate(zip(intervals,source_prices)):
        expected=(datetime(2020,1,1,tzinfo=timezone.utc)
                  +timedelta(minutes=15*i)).isoformat()
        demand(stamp==expected,"Interval timestamp not as predeclared")
        near(price,PRICES[i%24]+((seed*7+i*13+(i//4)*5)%9-4),
             "Invented price source mismatch",1e-10)
    if model=="ENDOGENOUS_ON_OFF_MILP":
        lim=cfg["experimental_v097"]
        demand(set(lim)=={"model","ramp_up_mw_e_per_hour","ramp_down_mw_e_per_hour",
          "minimum_on_power_mw_e","initial_on","initial_power_mw_e",
          "startup_cost_eur","shutdown_cost_eur","minimum_up_hours",
          "minimum_down_hours","initial_remaining_dwell_hours"},"MILP limits keys changed")
        demand(lim["model"]=="clock_hour_on_off_milp_v097"
           and lim["minimum_on_power_mw_e"]==.2
           and lim["initial_on"] is True and lim["initial_power_mw_e"]==.4
           and lim["startup_cost_eur"]==cost and lim["shutdown_cost_eur"]==1.
           and lim["ramp_up_mw_e_per_hour"]==.8
           and lim["ramp_down_mw_e_per_hour"]==.8
           and lim["minimum_up_hours"]==.5 and lim["minimum_down_hours"]==.5
           and lim["initial_remaining_dwell_hours"]==0.,
           "Altered invented MILP commitment/ramp assumptions")
    else:
        lim=cfg["experimental_v095"]
        demand(set(lim)=={"model","ramp_up_mw_e_per_hour",
                         "ramp_down_mw_e_per_hour",
                         "minimum_power_mw_e","initial_power_mw_e"},
               "Changed LP limits")
        demand(lim["model"]=="continuous_always_on_ramp_surrogate_v095"
           and lim["ramp_up_mw_e_per_hour"]==.8
           and lim["ramp_down_mw_e_per_hour"]==.8
           and lim["minimum_power_mw_e"]==.2
           and lim["initial_power_mw_e"]==.4,
           "Altered invented LP ramp assumptions")
    return cfg,lim,np.array(source_prices,dtype=float)

def _events(states,lim):
    prev=int(lim["initial_on"])
    starts=[];stops=[]
    for current in states:
        demand(current in (0,1),"Nonbinary fixed pattern")
        starts.append(int(prev==0 and current==1))
        stops.append(int(prev==1 and current==0))
        prev=current
    # Exact elapsed dwell: every start/stop locks the current + next 15-minute slot.
    for i,(a,b) in enumerate(zip(starts,stops)):
        if a or b:
            demand(i+2<=len(states),"Commitment dwell past the horizon")
            demand(states[i]==states[i+1],
                   "Start/stop not held for 0.5h minimum dwell")
    return starts,stops

def formulate(cfg,lim,prices,fixed_states=None):
    """Completely independent 5N LP formulation for fixed on/off pattern."""
    n=len(prices);dt=.25
    is_milp=fixed_states is not None
    if is_milp:demand(len(fixed_states)==n,"Wrong pattern size")
    u,s,h,a,w=(j*n for j in range(5))
    dims=5*n
    c=np.zeros(dims);lb=np.zeros(dims);ub=np.full(dims,np.inf)
    eta=.4;eth=.2;rating=.8
    for t in range(n):
        c[u+t]=-eta*(prices[t]-.75)*dt
        c[a+t]=6.*dt;c[w+t]=1.*dt
        if is_milp:
            lb[u+t]=(.2/eta) if fixed_states[t] else 0.
            ub[u+t]=(rating/eta) if fixed_states[t] else 0.
        else:
            lb[u+t]=.2/eta;ub[u+t]=rating/eta
        ub[s+t]=cfg["gas_storage_capacity_mwh_lhv"]
        ub[h+t]=.15;ub[a+t]=cfg["aux_heat_capacity_mw_th"]
        ub[w+t]=.35
    Aeq=np.zeros((3*n+1,dims));beq=np.zeros(3*n+1)
    initial=cfg["initial_gas_inventory_mwh_lhv"]
    for t in range(n):
        Aeq[t,u+t]=dt;Aeq[t,s+t]=1.
        if t:Aeq[t,s+t-1]=-1.
        beq[t]=dt+(initial if t==0 else 0.)
        Aeq[n+t,u+t]=eth
        Aeq[n+t,h+t]=-1.;Aeq[n+t,w+t]=-1.
        Aeq[2*n+t,h+t]=1.;Aeq[2*n+t,a+t]=1.
        beq[2*n+t]=.15
    Aeq[3*n,s+n-1]=1.
    beq[3*n]=initial
    ramp=[]
    prior_on=int(lim["initial_on"]) if is_milp else 1
    prev_p=lim["initial_power_mw_e"]
    for t in range(n):
        active=(not is_milp or prior_on==fixed_states[t]==1)
        if active:
            step=.125 if t==0 else .25
            for sign,r in ((1.,lim["ramp_up_mw_e_per_hour"]),
                           (-1.,lim["ramp_down_mw_e_per_hour"])):
                row=np.zeros(dims)
                row[u+t]=sign*eta
                if t:
                    row[u+t-1]=-sign*eta
                    rhs=r*step
                else:
                    rhs=r*step+sign*prev_p
                ramp.append((row,rhs))
        if is_milp:prior_on=fixed_states[t]
    Aub=np.stack([row for row,_ in ramp]) if ramp else np.zeros((0,dims))
    bub=np.array([b for _,b in ramp],dtype=float)
    return {"c":c,"lb":lb,"ub":ub,"Aeq":Aeq,"beq":beq,"Aub":Aub,"bub":bub}

def _kkt_check(prob,sol):
    """Direct primal/dual arithmetic, not a claim of a second optimizer."""
    x=np.asarray(sol.x)
    demand(sol.success and np.all(np.isfinite(x)),"Independent HiGHS LP did not solve")
    eq=prob["Aeq"];beq=prob["beq"];au=prob["Aub"];bu=prob["bub"]
    lo=prob["lb"];up=prob["ub"];c=prob["c"]
    eqr=np.max(np.abs(eq@x-beq))
    ineqr=max(0.,float(np.max(au@x-bu))) if len(bu) else 0.
    lo_res=max(0.,float(np.max(lo-x)))
    finite=np.isfinite(up)
    up_res=max(0.,float(np.max(x[finite]-up[finite]))) if finite.any() else 0.
    em=np.asarray(sol.eqlin.marginals)
    im=np.asarray(sol.ineqlin.marginals)
    lm=np.asarray(sol.lower.marginals)
    um=np.asarray(sol.upper.marginals)
    station=c-eq.T@em-au.T@im-lm-um
    stat=float(np.max(np.abs(station)))
    dual=float(beq@em+bu@im+lo@lm+up[finite]@um[finite])
    value=float(c@x)
    gap=abs(value-dual)
    comp_ineq=abs(float((bu-au@x)@im)) if len(im) else 0.
    comp_low=abs(float((x-lo)@lm))
    comp_up=abs(float((up[finite]-x[finite])@um[finite]))
    demand(float(np.max(im))<=1e-7 if len(im) else True,
           "Inequality dual multipliers positive (min-problem sign)")
    demand(float(np.min(lm))>=-1e-7,
           "Lower bound dual multipliers negative")
    demand(float(np.max(um))<=1e-7,"Upper bound dual multipliers positive")
    residuals={
      "max_primal_equality_residual":float(eqr),
      "max_primal_inequality_excess":float(ineqr),
      "max_primal_lower_bound_excess":float(lo_res),
      "max_primal_upper_bound_excess":float(up_res),
      "max_dual_stationarity_residual":stat,
      "max_complementarity":max(comp_ineq,comp_low,comp_up),
      "absolute_primal_dual_objective_gap_eur":gap,
    }
    demand(all(math.isfinite(v) and v<=TOL for v in residuals.values()),
           "Independent LP primal/dual KKT witness failed: "+str(residuals))
    return {"independent_lp_primal_eur":value,"independent_lp_dual_eur":dual,
            "residuals":residuals}

def _solve(prob):
    return linprog(prob["c"],A_ub=prob["Aub"],b_ub=prob["bub"],
                   A_eq=prob["Aeq"],b_eq=prob["beq"],
                   bounds=list(zip(prob["lb"],prob["ub"])),method="highs")

def _row_checks(case,cfg,lim,prices):
    n=case["slots"];start_stock=cfg["initial_gas_inventory_mwh_lhv"];stock=start_stock
    prev_p=lim["initial_power_mw_e"]
    prev_on=int(lim["initial_on"]) if case["model"]=="ENDOGENOUS_ON_OFF_MILP" else 1
    gross=chp_cost=aux_cost=dump_cost=elec=gas_used=useful=aux_total=dumped=0.
    states=[];starts=[];stops=[]
    for t,row in enumerate(case["rows"]):
        demand(row["start_utc"]==case["timestamps_utc"][t]
               and abs(row["dt_h"]-.25)<1e-10,
               "Reported hourly timestamps have missing/shifted quarter")
        on=int(row["on"]) if case["model"]=="ENDOGENOUS_ON_OFF_MILP" else 1
        y=int(row["startup"]) if case["model"]=="ENDOGENOUS_ON_OFF_MILP" else 0
        v=int(row["shutdown"]) if case["model"]=="ENDOGENOUS_ON_OFF_MILP" else 0
        demand(on in (0,1) and y in (0,1) and v in (0,1),"Nonbinary original flags")
        demand(y==int(prev_on==0 and on==1) and v==int(prev_on==1 and on==0),
               "Reported original transition inconsistency")
        if case["model"]=="ENDOGENOUS_ON_OFF_MILP":
            near(row["price_eur_mwh"],prices[t],"Original MILP row price")
            u=row["gas_use_mw_lhv"];p=row["power_mw_e"];s=row["stock_end_mwh_lhv"]
            h=row["useful_heat_mw_th"];a=row["aux_heat_mw_th"];w=row["dump_heat_mw_th"]
        else:
            near(row["market_price_eur_mwh"],prices[t],"Original LP row price")
            u=row["gas_use_mw_lhv"];p=row["electric_power_mw_e"];s=row["stock_end_mwh_lhv"]
            h=row["heat_served_chp_mw_th"];a=row["heat_served_auxiliary_mw_th"]
            w=row["heat_rejected_mw_th"]
        demand(all(math.isfinite(x) for x in (u,p,s,h,a,w)),
               "Nonfinite source row")
        near(p,.4*u,"Generator-terminal source power")
        near(s-stock,(1.-u)*.25,"15-minute gas inventory")
        near(.2*u,h+w,"CHP heat conversion")
        near(h+a,.15,"Heat service")
        near(h,min(.15,.2*u),"Cost-minimal heat allocation")
        demand(-TOL<=s<=cfg["gas_storage_capacity_mwh_lhv"]+TOL and
               -TOL<=a<=cfg["aux_heat_capacity_mw_th"]+TOL and
               -TOL<=w<=.35+TOL and -TOL<=h<=.15+TOL,
               "Physical source bounds")
        demand(-TOL<=p<=.8+TOL and (on or abs(p)<TOL),
               "Generator on/off rating")
        if on:demand(p>=.2-TOL,"Minimum generator ON power")
        if prev_on and on:
            step=.125 if t==0 else .25
            demand(p-prev_p<=.8*step+TOL and prev_p-p<=.8*step+TOL,
                   "Continuous ON midpoint ramp")
        stock=s;prev_p=p;prev_on=on
        states.append(on);starts.append(y);stops.append(v)
        elec+=p*.25;gas_used+=u*.25;useful+=h*.25;aux_total+=a*.25;dumped+=w*.25
        gross+=prices[t]*p*.25;chp_cost+=p*.75*.25
        aux_cost+=a*6*.25;dump_cost+=w*.25
    near(stock,start_stock,"Cyclic end gas stock")
    near(gas_used,n*.25,"Net gas full-horizon conservation")
    near(elec,.4*gas_used,"Full electricity accounting")
    near(useful+aux_total,.15*n*.25,"Full heat service")
    if case["model"]=="ENDOGENOUS_ON_OFF_MILP":
        es,vs=_events(states,lim)
        demand(starts==es and stops==vs,"Dwell/transition independently fails")
        near(case["start_count"],sum(es),"Number of startups")
        near(case["stop_count"],sum(vs),"Number of shutdowns")
        value=gross-chp_cost-aux_cost-dump_cost
        value-=lim["startup_cost_eur"]*sum(es)+lim["shutdown_cost_eur"]*sum(vs)
        near(case["reported_mip_gap"],0.,"Original MILP mip_gap")
    else:
        value=gross-chp_cost-aux_cost-dump_cost
        demand(case["start_count"] is None and case["stop_count"] is None,
               "Original LP claiming binary switches")
    near(case["reported_net_objective_eur"],value,
         "Independent objective recomputation")
    near(case["auxiliary_heat_fraction_of_demand"],
         aux_total/(.15*n*.25),"Auxiliary heat fraction")
    near(case["chp_heat_fraction_of_demand"],
         useful/(.15*n*.25),"CHP heat coverage")
    return value,states

def audit_case(case,*,exhaustive=False):
    cfg,lim,prices=_predeclare(case)
    objective,states=_row_checks(case,cfg,lim,prices)
    fixed=states if case["model"]=="ENDOGENOUS_ON_OFF_MILP" else None
    prob=formulate(cfg,lim,prices,fixed)
    independent=_solve(prob)
    demand(independent.success,"Independent reconstructed LP for observed ON pattern is infeasible")
    cert=_kkt_check(prob,independent)
    starts=stops=0
    if fixed is not None:
        es,vs=_events(states,lim)
        starts=sum(es);stops=sum(vs)
    independent_obj=-cert["independent_lp_primal_eur"]
    if fixed is not None:independent_obj-=starts*lim["startup_cost_eur"]+stops*lim["shutdown_cost_eur"]
    near(independent_obj,objective,"Independent fixed-pattern LP vs inherited solver optimum",2e-4)
    exhaustive_report=None
    if exhaustive:
        demand(fixed is not None and case["slots"]==8,
               "Exhaustive binary MILP oracle is limited to 8 slots")
        best=-math.inf
        feasible=0
        for sequence in product((0,1),repeat=8):
            try:
                starts2,stops2=_events(sequence,lim)
            except AssertionError:continue
            other=formulate(cfg,lim,prices,sequence)
            res=_solve(other)
            if not res.success:continue
            feasible+=1
            net=-float(res.fun)-sum(starts2)*lim["startup_cost_eur"]-sum(stops2)*lim["shutdown_cost_eur"]
            best=max(best,net)
        demand(feasible>1,"8-slot oracle did not have genuinely competing feasible schedules")
        near(objective,best,"Exhaustive 2^8 independently rebuilt MILP global optimum",2e-4)
        exhaustive_report={"binary_patterns_enumerated":256,
                           "feasible_patterns_with_lp_solution":feasible,
                           "certified_global_optimum_eur":best}
    return {
        "seed":case["seed"],"slots":case["slots"],
        "model":case["model"],"capacity_mwh_lhv":case["capacity_mwh_lhv"],
        "auxiliary_capacity_mw_th":case["auxiliary_capacity_mw_th"],
        "startup_cost_eur":case["startup_cost_eur"],
        "independently_recomputed_objective_eur":objective,
        "alternative_lp_primal_and_dual_certificate":cert,
        "exhaustive_8slot_binary_global_optimum":exhaustive_report,
        "status":"PASS_INDEPENDENT_SOURCE_RECONSTRUCTION_PRIMAL_DUAL_AND_COMMITMENT_GATE",
    }

def audit(payload):
    demand(payload["protocol"]==PROTOCOL and payload["version"]=="0.9.19",
           "Wrong benchmark source identity")
    demand(payload["status"].startswith("SOLVED_FINITE_SYNTHETIC_"),
           "Results do not identify synthetic solved benchmark")
    claims=payload["claims"]
    demand(not any(claims.values()),"Unfounded physics/market proof claim")
    results=[audit_case(case,exhaustive=(
       case["model"]=="ENDOGENOUS_ON_OFF_MILP" and case["slots"]==8
       and case["capacity_mwh_lhv"]==.5
    )) for case in payload["cases"]]
    if len(payload["cases"])>3:
        demand(len(results)==46,
               "Missing factorial 3 × 3 × 2 × 2 + 9 LP + one 8-slot oracle")
        demand(sum(r["model"]=="ENDOGENOUS_ON_OFF_MILP" for r in results)==37,
               "Missing binary model")
        demand(sum(r["model"]=="ALWAYS_ON_RAMP_LP" for r in results)==9,
               "Missing LP design")
    for frontier in payload["frontiers"]:
        candidates=[c for c in payload["cases"]
                    if c["seed"]==frontier["seed"] and c["slots"]==24
                    and c["model"]=="ENDOGENOUS_ON_OFF_MILP"
                    and c["startup_cost_eur"]==5.]
        found=[]
        for c in candidates:
            dominated=any(
                other is not c and
                other["reported_net_objective_eur"]>=c["reported_net_objective_eur"]-1e-7 and
                other["auxiliary_heat_fraction_of_demand"]<=c["auxiliary_heat_fraction_of_demand"]+1e-7 and
                other["start_count"]<=c["start_count"] and
                (other["reported_net_objective_eur"]>c["reported_net_objective_eur"]+1e-7 or
                 other["auxiliary_heat_fraction_of_demand"]<c["auxiliary_heat_fraction_of_demand"]-1e-7 or
                 other["start_count"]<c["start_count"])
                for other in candidates)
            if not dominated: found.append(c)
        demand(frontier["candidates"]==len(candidates),
               "Comparative frontier design cells missing")
        declared={(x["capacity_mwh_lhv"],x["auxiliary_capacity_mw_th"])
                  for x in frontier["nondominated_candidates"]}
        expected={(x["capacity_mwh_lhv"],x["auxiliary_capacity_mw_th"]) for x in found}
        demand(declared==expected,"Nondominated frontier does not match independent screening")
    return {
        "protocol":"BIOGASFLEX_V0919_INDEPENDENT_KKT_AND_EXHAUSTIVE_BINARY_ORACLE_V1",
        "status":"PASS_SYNTHETIC_ENDOGENOUS_RESEARCH_FRONTIERS_AND_PRIMAL_DUAL_KKT",
        "cases_verified":len(results),
        "total_independently_checked_quarter_hour_rows":sum(x["slots"] for x in results),
        "lp_primal_dual_witnesses":len(results),
        "exhaustive_8slot_binary_oracles":sum(x["exhaustive_8slot_binary_global_optimum"] is not None
                                         for x in results),
        "finite_design_frontiers_rechecked":len(payload["frontiers"]),
        "calibrated_real_plant_or_reliability_probability":False,
        "case_witnesses":results,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=False,type=Path)
    args=p.parse_args()
    result=audit(json.loads(args.input.read_text(encoding="utf8")))
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps({
      "status":result["status"],
      "cases_verified":result["cases_verified"],
      "quarter_hour_rows":result["total_independently_checked_quarter_hour_rows"],
      "lp_primal_dual_witnesses":result["lp_primal_dual_witnesses"],
      "exhaustive_binary_oracles":result["exhaustive_8slot_binary_oracles"],
      "rechecked_frontiers":result["finite_design_frontiers_rechecked"],
      "true_physical_reliability_calibrated":False,
    },indent=2))
