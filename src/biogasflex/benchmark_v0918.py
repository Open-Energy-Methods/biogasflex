"""v0.9.18 reproducible synthetic 15-minute CHP solver scaling benchmark.

Two distinct experiments, both built on UNCHANGED inherited algorithms:
1. forced-commitment MILP: zero storage and alternating synthetic gas
   production uniquely determine engine on/off states and gas/electric use.
   A separate algebraic optimum witness is available (no solver needed).
2. nontrivial always-ON LP with storage, heat service and midpoint ramps,
   compared to the exact same assumed inputs at zero storage.
   An independent primal auditor recomputes conservation, heat and costs.

No real CHP measurements, authenticated hardware limits, electricity
orders, renewable energy certificates or actual market price forecasts.
Results are *simulation performance*, not physical validation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import platform
from pathlib import Path
import sys
from time import perf_counter
from typing import Sequence

from .baseline import Interval
from .dispatch import DispatchError
from .experimental_v095 import optimize_operating_surrogate
from .experimental_v097 import optimize_commitment_milp
from .public_chp_sources_v0916 import ROOT

PROTOCOL="BIOGASFLEX_V0918_15MIN_WEEK_INDEPENDENT_RESEARCH_BENCHMARK_V1"
SCALES=(96,192,672)
TIME_H=0.25
START=datetime(2020,1,1,tzinfo=timezone.utc)
PROFILE_CLASS="PURELY_INVENTED_NO_BIOGAS_EQUIPMENT_CALIBRATION_OR_OBSERVED_MARKET_PRICES"

def _require(condition:bool, message:str)->None:
    if not condition: raise RuntimeError("v0.9.18 benchmark failure: "+message)

def _quarter_intervals(n:int,kind:str)->list[Interval]:
    if type(n) is not int or n<4 or n%4:
        raise ValueError("Benchmark horizon must be >= 4 and a multiple of four quarter-hours")
    def price(i:int)->float:
        # Explicitly fictional 4-hour price blocks, repeated every 24 hours.
        values=(20.,95.,35.,110.,25.,85.)
        return values[(i//16)%6]
    return [
       Interval(START+timedelta(minutes=15*i),price(i),TIME_H,"SE3")
       for i in range(n)
    ]

def _forced_config(n:int,*,bad_aux:bool=False,up_hours:float=.5)->dict:
    # For real benchmark scales: 12 hours OFF, 12 hours ON, repeated.
    # For 4/8-slot independent witnesses: half-period OFF then ON.
    period=min(96,n)
    half=period//2
    gas=[0. if i%period<half else 2. for i in range(n)]
    return {
        "case_id":f"v0918_forced_synthetic_quarter_hour_{n}",
        "price_zone":"SE3",
        "gas_production_mw_lhv":gas,
        "gas_input_mw_lhv":1.,
        "electric_rating_mw":.8,
        "electric_efficiency_lhv":.4,
        "thermal_efficiency_lhv":.2,
        "gas_storage_capacity_mwh_lhv":0.,
        "initial_gas_inventory_mwh_lhv":0.,
        "fixed_flaring_mw_lhv":0.,
        "fixed_losses_mw_lhv":0.,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":.15,
        "aux_heat_capacity_mw_th":.1 if bad_aux else .2,
        "heat_dump_capacity_mw_th":.3,
        "aux_heat_cost_eur_per_mwh_th":3.,
        "heat_dump_penalty_eur_per_mwh_th":1.,
        "chp_variable_cost_eur_per_mwh_e":1.,
        "experimental_v097":{
            "model":"clock_hour_on_off_milp_v097",
            "ramp_up_mw_e_per_hour":.4,
            "ramp_down_mw_e_per_hour":.4,
            "minimum_on_power_mw_e":.2,
            "initial_on":False,
            "initial_power_mw_e":0.,
            "startup_cost_eur":5.,
            "shutdown_cost_eur":2.,
            "minimum_up_hours":up_hours,
            "minimum_down_hours":.5,
            "initial_remaining_dwell_hours":0.,
        },
        "input_provenance":PROFILE_CLASS,
    }

def _flexible_config(n:int, storage:bool)->dict:
    return {
       "case_id":f"v0918_synthetic_always_on_{n}_"+("buffer" if storage else "no_buffer"),
       "price_zone":"SE3",
       "gas_production_mw_lhv":[1.]*n,
       "gas_input_mw_lhv":1.,
       "electric_rating_mw":.8,
       "electric_efficiency_lhv":.4,
       "thermal_efficiency_lhv":.2,
       "gas_storage_capacity_mwh_lhv":.75 if storage else 0.,
       "initial_gas_inventory_mwh_lhv":.375 if storage else 0.,
       "fixed_flaring_mw_lhv":0.,
       "fixed_losses_mw_lhv":0.,
       "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
       "heat_demand_mw_th":.2,
       "aux_heat_capacity_mw_th":.25,
       "heat_dump_capacity_mw_th":.5,
       "aux_heat_cost_eur_per_mwh_th":4.,
       "heat_dump_penalty_eur_per_mwh_th":1.,
       "chp_variable_cost_eur_per_mwh_e":.5,
       "experimental_v095":{
           "model":"continuous_always_on_ramp_surrogate_v095",
           "ramp_up_mw_e_per_hour":.4,
           "ramp_down_mw_e_per_hour":.4,
           "minimum_power_mw_e":.1,
           "initial_power_mw_e":.4,
       },
       "input_provenance":PROFILE_CLASS,
    }

def _case(n:int,kind:str)->dict:
    intervals=_quarter_intervals(n,kind)
    if kind=="forced_commitment_milp":
        config=_forced_config(n)
        solver=optimize_commitment_milp
    elif kind in ("storage_ramp_lp","zero_storage_ramp_lp"):
        config=_flexible_config(n,kind=="storage_ramp_lp")
        solver=optimize_operating_surrogate
    else:raise ValueError(f"Unknown v0.9.18 benchmark: {kind}")
    t0=perf_counter()
    result=solver(config,intervals)
    seconds=perf_counter()-t0
    _require(len(result["hourly"])==n,"Unexpected number of source-quarters")
    _require(result["solver"]["success"] is True,"Solver did not report successful optimization")
    return {
        "case":config["case_id"],
        "kind":kind,
        "interval_count":n,
        "declared_duration_hours":n*TIME_H,
        "problem_input":config,
        "price_eur_mwh":[i.price_eur_per_mwh for i in intervals],
        "solve_seconds_total_python_scipy_highs":round(seconds,6),
        "solver_mip_gap":result["solver"].get("mip_gap"),
        "solver_nominal_success":True,
        "reported_net_contribution_eur":result.get(
            "net_contribution_eur",
            result["optimized_dispatch"]["economic_contribution_proxy_eur"]),
        "reported_start_count":result.get("start_count"),
        "reported_stop_count":result.get("stop_count"),
        "reported_lp_relaxation_upper_bound_eur":result.get(
            "unconstrained_LP_upper_bound_eur",
            result.get("unconstrained_optimal_contribution_upper_bound_eur")),
        "reported_ramp_violation_mw_e":result.get(
            "max_steady_on_ramp_violation_mw_e",
            result.get("max_ramp_violation_mw_e")),
        "fixed_reference_feasible":result.get("fixed_reference_feasible",True),
        "rows":result["hourly"],
        "reported_ledger":result["optimized_dispatch"],
        "status":"SOLVED_PHYSICALLY_IN_A_DECLARED_SYNTHETIC_MATHEMATICAL_MODEL",
    }

def _negative(n:int,which:str)->dict:
    config=_forced_config(n)
    if which=="insufficient_aux_heat":
        config["aux_heat_capacity_mw_th"]=.10
        expected="First forced-OFF interval has 0 CHP heat and .15 MWth demand but only .10 backup"
    elif which=="mandatory_up_dwell_exceeds_remaining_horizon":
        config["experimental_v097"]["minimum_up_hours"]=n/8+.25
        expected="Forced ON begins half-way; minimum-up dwell exceeds full remaining time"
    elif which=="rating_too_small_for_forced_gas":
        config["electric_rating_mw"]=.6
        expected="Cyclic zero-buffer gas input of 2 MW_LHV needs .8 MWe, above .6 rating"
    else:raise ValueError(which)
    intervals=_quarter_intervals(n,"forced_commitment_milp")
    try:
        optimize_commitment_milp(config,intervals)
    except (DispatchError,ValueError) as exc:
        return {
            "kind":"DECLARED_SYNTHETIC_INFEASIBLE_"+which,
            "interval_count":n,
            "reason":expected,
            "optimizer_rejected":True,
            "optimizer_message":str(exc)[:250],
            "not_physical_plant_failure":True,
        }
    raise RuntimeError(f"Synthetic infeasibility was not detected: {which}")

def run(scales:Sequence[int]=SCALES,*,include_infeasible:bool=True)->dict:
    if not scales or any(type(n) is not int or n<4 or n%4 for n in scales):
        raise ValueError("Strict positive 15-minute durations required")
    if len(set(scales))!=len(scales) or tuple(scales)!=tuple(sorted(scales)):
        raise ValueError("Benchmark horizon scale order must be strict ascending")
    results=[]
    for n in scales:
        for kind in ("forced_commitment_milp","zero_storage_ramp_lp","storage_ramp_lp"):
            results.append(_case(n,kind))
    infeasible = (
        [_negative(96,"insufficient_aux_heat"),
         _negative(96,"rating_too_small_for_forced_gas"),
         _negative(96,"mandatory_up_dwell_exceeds_remaining_horizon")]
        if include_infeasible and max(scales)>=96 else []
    )
    return {
       "protocol":PROTOCOL,
       "version":"0.9.18",
       "status":"PASS_EXECUTED_FULL_QUARTER_HOUR_RESEARCH_BENCHMARK_PENDING_INDEPENDENT_AUDIT",
       "scenario_family":PROFILE_CLASS,
       "scales":list(scales),
       "scipy_runtime_context":{
         "python":platform.python_version(),
         "platform":platform.platform(),
         "note":"Wall clock includes model building, MILP/LP, and inherited LP comparison; indicative only, no stable SLA or optimization performance guarantee",
       },
       "cases":results,
       "infeasible_synthetic_controls":infeasible,
       "claims":{
          "real_plant_telemetry_used":False,
          "biogas_engine_calibration_established":False,
          "real_market_forecast_or_contracts_used":False,
          "physical_ramp_up_down_calibrated":False,
          "gas_storage_pressure_dynamics_modeled":False,
          "terminal_inventory_enforced":True,
          "instantaneous_heat_service_no_thermal_storage":True,
          "binary_transition_exempt_from_ramp":True,
          "small_forced_case_unique_optimum_algebraic_witness":True,
          "LP_global_optimality_independently_proven":False,
       },
    }

def write_out(result:dict,path:Path)->None:
    p=Path(path).resolve()
    _require(not p.is_relative_to(ROOT.resolve()),"Benchmark output must be written OUTSIDE repo")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")

def main()->None:
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--smoke",action="store_true",help="Tiny 4/8-slot synthetic oracle regression, not a scalability claim")
    p.add_argument("--output",type=Path,default=None,
                   help="Write ALL case rows outside git checkout for independently recomputed audit")
    a=p.parse_args()
    result=run((4,8) if a.smoke else SCALES)
    if a.output is not None:write_out(result,a.output)
    print(json.dumps({
      "protocol":PROTOCOL,"status":result["status"],
      "scales":result["scales"],
      "case_summary":[{
         "kind":x["kind"],"intervals":x["interval_count"],
         "objective_eur":x["reported_net_contribution_eur"],
         "wall_time_seconds":x["solve_seconds_total_python_scipy_highs"],
         "start_count":x["reported_start_count"],
         "stop_count":x["reported_stop_count"],
         "mip_gap":x["solver_mip_gap"],
      } for x in result["cases"]],
      "synthetic_infeasible_controls":len(result["infeasible_synthetic_controls"]),
      "full_row_report_path":str(a.output) if a.output is not None else None,
      "real_plant_validated":False,
    },indent=2,allow_nan=False))

if __name__=="__main__":
    main()
