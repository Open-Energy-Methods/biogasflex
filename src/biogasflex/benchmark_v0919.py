"""v0.9.19 predeclared synthetic CHP flexibility / heat-autonomy experiments.

Original inherited v0.9.7 MILP and v0.9.5 ramp LP are NOT changed.
The multi-factor design introduces endogenous on/off, gas buffer and heat
backup alternatives; prices and plant limits are explicitly invented.
Do not interpret equal-weight design cells as a probability distribution.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import platform
from pathlib import Path
from time import perf_counter

from .baseline import Interval
from .experimental_v095 import optimize_operating_surrogate
from .experimental_v097 import optimize_commitment_milp
from .public_chp_sources_v0916 import ROOT

PROTOCOL="BIOGASFLEX_V0919_ENDOGENOUS_COMMITMENT_FINITE_DESIGN_AND_DUAL_V1"
PROVENANCE="FULLY_SYNTHETIC_DETERMINISTIC_NONPROBABILISTIC_2026_RESEARCH_DESIGN"
SEEDS=(11,37,83)
STORAGE=(0.0,0.5,1.5)
BACKUP=(0.0,0.15)
START_COST=(5.0,15.0)
N=24
START=datetime(2020,1,1,tzinfo=timezone.utc)
BASE_PRICES=(5.,5.,5.,5.,120.,120.,120.,120.,120.,120.,
             15.,15.,15.,15.,15.,15.,110.,110.,110.,110.,
             110.,110.,110.,110.)

def require(ok:bool,what:str)->None:
    if not ok:raise ValueError("v0.9.19: "+what)

def _intervals(seed:int,n:int)->list[Interval]:
    require(seed in SEEDS and n in (8,24,96),"Unlisted seed or interval horizon")
    # Finite chosen design, not random samples from a physical distribution.
    prices=[
        BASE_PRICES[i%24]+float((seed*7+i*13+((i//4)*5))%9-4)
        for i in range(n)
    ]
    return [Interval(START+timedelta(minutes=15*i),prices[i],.25,"SE3")
            for i in range(n)]

def _config(seed:int,n:int,capacity:float,backup:float,starts:float,*,lp:bool=False)->dict:
    require(capacity in STORAGE and backup in BACKUP and starts in START_COST,
            "Unregistered design parameters")
    cfg={
        "case_id":f"v0919_SYNTHETIC_seed{seed}_slots{n}_capacity{capacity}_backup{backup}_start{starts}_"+("lp" if lp else "milp"),
        "price_zone":"SE3",
        "gas_input_mw_lhv":1.,
        "gas_production_mw_lhv":[1.]*n,
        "electric_rating_mw":.8,
        "electric_efficiency_lhv":.4,
        "thermal_efficiency_lhv":.2,
        "gas_storage_capacity_mwh_lhv":capacity,
        "initial_gas_inventory_mwh_lhv":capacity/2,
        "fixed_flaring_mw_lhv":0.,
        "fixed_losses_mw_lhv":0.,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":.15,
        "aux_heat_capacity_mw_th":backup,
        "heat_dump_capacity_mw_th":.35,
        "aux_heat_cost_eur_per_mwh_th":6.,
        "heat_dump_penalty_eur_per_mwh_th":1.,
        "chp_variable_cost_eur_per_mwh_e":.75,
        "input_provenance":PROVENANCE,
        "design_seed_not_a_probability_draw":seed,
    }
    if lp:
        cfg["experimental_v095"]={
          "model":"continuous_always_on_ramp_surrogate_v095",
          "ramp_up_mw_e_per_hour":.8,"ramp_down_mw_e_per_hour":.8,
          "minimum_power_mw_e":.2,"initial_power_mw_e":.4,
        }
    else:
        cfg["experimental_v097"]={
          "model":"clock_hour_on_off_milp_v097",
          "ramp_up_mw_e_per_hour":.8,"ramp_down_mw_e_per_hour":.8,
          "minimum_on_power_mw_e":.2,
          "initial_on":True,"initial_power_mw_e":.4,
          "startup_cost_eur":starts,"shutdown_cost_eur":1.,
          "minimum_up_hours":.5,"minimum_down_hours":.5,
          "initial_remaining_dwell_hours":0.,
        }
    return cfg

def _solve(seed:int,n:int,capacity:float,backup:float,starts:float,*,lp:bool=False)->dict:
    config=_config(seed,n,capacity,backup,starts,lp=lp)
    intervals=_intervals(seed,n)
    begin=perf_counter()
    result=(optimize_operating_surrogate if lp else optimize_commitment_milp)(config,intervals)
    seconds=perf_counter()-begin
    ledger=result["optimized_dispatch"]
    net=(ledger["economic_contribution_proxy_eur"] if lp else result["net_contribution_eur"])
    rows=result["hourly"]
    aux_fraction=ledger["auxiliary_heat_delivered_mwh_th"]/ledger["heat_demand_mwh_th"]
    return {
        "seed":seed,"slots":n,"capacity_mwh_lhv":capacity,
        "auxiliary_capacity_mw_th":backup,"startup_cost_eur":starts,
        "model":"ALWAYS_ON_RAMP_LP" if lp else "ENDOGENOUS_ON_OFF_MILP",
        "config":config,
        "timestamps_utc":[i.start_utc.isoformat() for i in intervals],
        "prices_eur_mwh":[i.price_eur_per_mwh for i in intervals],
        "rows":rows,
        "ledger":ledger,
        "reported_net_objective_eur":float(net),
        "reported_lp_upper_bound_eur":float(
            result["unconstrained_optimal_contribution_upper_bound_eur"]
            if lp else result["unconstrained_LP_upper_bound_eur"]),
        "reported_mip_gap":result["solver"].get("mip_gap"),
        "start_count":result.get("start_count"),
        "stop_count":result.get("stop_count"),
        "fixed_reference_feasible":result.get("fixed_reference_feasible",True),
        "auxiliary_heat_fraction_of_demand":aux_fraction,
        "chp_heat_fraction_of_demand":ledger["useful_chp_heat_delivered_mwh_th"]/ledger["heat_demand_mwh_th"],
        "heat_service_achieved_fraction_in_model":1.0,
        "solver_wall_seconds":round(seconds,6),
    }

def _dominates(a:dict,b:dict)->bool:
    """Fixed seed + fixed startup cost only; three design metrics, no capex."""
    x=(a["reported_net_objective_eur"],-a["auxiliary_heat_fraction_of_demand"],-a["start_count"])
    y=(b["reported_net_objective_eur"],-b["auxiliary_heat_fraction_of_demand"],-b["start_count"])
    return all(i>=j-1e-7 for i,j in zip(x,y)) and any(i>j+1e-7 for i,j in zip(x,y))

def run(*,smoke:bool=False)->dict:
    # Even the smoke executes a genuinely endogenous 8-slot MILP:
    # the unique force-on result from v0.9.18 is not being recycled.
    if smoke:
        cases=[_solve(11,8,.5,.15,5.),_solve(11,8,0.,.15,5.),
               _solve(11,8,.5,.15,5.,lp=True)]
    else:
        cases=[_solve(seed,N,cap,backup,cost)
               for seed in SEEDS for cap in STORAGE
               for backup in BACKUP for cost in START_COST]
        cases.extend(_solve(seed,96,cap,.15,5.,lp=True)
                     for seed in SEEDS for cap in (0.,.5,1.5))
        cases.extend(_solve(11,8,.5,.15,5.),)
    frontiers=[]
    for seed in (SEEDS[:1] if smoke else SEEDS):
        subset=[r for r in cases if r["model"]=="ENDOGENOUS_ON_OFF_MILP"
                and r["seed"]==seed and r["slots"]==N
                and r["startup_cost_eur"]==5.]
        if subset:
            pareto=[r for r in subset if not any(_dominates(other,r)
                          for other in subset if other is not r)]
            frontiers.append({
               "seed":seed,
               "comparison_scope":"SAME_HORIZON_SEED_START_COST_FUEL_PRICE_AND_HEAT_COSTS",
               "candidates":len(subset),
               "nondominated_candidates":[{
                 "capacity_mwh_lhv":r["capacity_mwh_lhv"],
                 "auxiliary_capacity_mw_th":r["auxiliary_capacity_mw_th"],
                 "net_synthetic_objective_eur":r["reported_net_objective_eur"],
                 "backup_heat_fraction":r["auxiliary_heat_fraction_of_demand"],
                 "start_count":r["start_count"]
               } for r in pareto],
               "not_a_physical_reliability_probability":True,
            })
    return {
      "protocol":PROTOCOL,
      "version":"0.9.19",
      "status":"SOLVED_FINITE_SYNTHETIC_COMMITMENT_FRONTIERS_PENDING_INDEPENDENT_CERTIFICATION",
      "design":{
        "seeds":list(SEEDS[:1] if smoke else SEEDS),
        "capacities_mwh_lhv":list(STORAGE),
        "auxiliary_capacity_mw_th":list(BACKUP),
        "startup_cost_eur":list(START_COST),
        "main_horizon_quarter_hours":N,
        "lp_dual_certificate_horizon_quarter_hours":96,
        "small_milp_exhaustive_enumeration_quarter_hours":8,
        "seed_selection":"PRESELECTED_DETERMINISTIC_DISTINCT_PRICE_PERTURBATIONS_NOT_RANDOM_SAMPLES",
        "probability_distributions_assumed":False,
        "real_energy_price_forecast":False,
        "physical_biogas_engine_parameters_measured":False,
        "modelled_heat_served":True,
        "real_plant_reliability_probability_estimated":False,
      },
      "runtime_context":{
          "python":platform.python_version(),"machine":platform.platform(),
          "warning":"Single solve including HiGHS and original LP comparison; not a hardware-independent performance SLA",
      },
      "cases":cases,
      "frontiers":frontiers,
      "claims":{
        "real_plant_measurements_used":False,
        "physical_reliability_calibrated":False,
        "dynamic_chp_transients_validated":False,
        "emissions_or_profit_validated":False,
        "LP_dual_certificate_provided_by_this_file":False,
        "MILP_full_frontier_global_optimality_independently_proven":False,
      },
    }

def write_out(out:dict,path:Path)->None:
    target=Path(path).resolve()
    require(not target.is_relative_to(ROOT.resolve()),"Write full reports outside checked-out repository")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--smoke",action="store_true")
    p.add_argument("--output",type=Path,default=None)
    a=p.parse_args()
    result=run(smoke=a.smoke)
    if a.output is not None:write_out(result,a.output)
    print(json.dumps({
        "protocol":result["protocol"],"status":result["status"],
        "solved_cases":len(result["cases"]),
        "endogenous_MILP_cases":sum(x["model"]=="ENDOGENOUS_ON_OFF_MILP" for x in result["cases"]),
        "LP_cases":sum(x["model"]=="ALWAYS_ON_RAMP_LP" for x in result["cases"]),
        "finite_design_frontiers":len(result["frontiers"]),
        "first_six_case_summaries":[{
            "seed":x["seed"],"slots":x["slots"],"storage":x["capacity_mwh_lhv"],
            "backup_capacity":x["auxiliary_capacity_mw_th"],
            "objective_eur":x["reported_net_objective_eur"],
            "starts":x["start_count"],"backup_fraction":x["auxiliary_heat_fraction_of_demand"],
        } for x in result["cases"][:6]],
        "full_report":str(a.output) if a.output is not None else None,
    },indent=2,allow_nan=False))

if __name__=="__main__":
    main()
