"""Independent v0.9.18 physical/optimization witness from JSON ONLY.

Deliberately imports NO biogasflex source, NumPy, SciPy or solver routines.
For zero-buffer MILP, fixed gas inflow uniquely determines every CHP
operating state and objective. For buffered LP, check primal and published
unconstrained LP upper bound without claiming independent dual optimality.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timedelta,timezone
import json
import math
from pathlib import Path

PROTOCOL="BIOGASFLEX_V0918_15MIN_WEEK_INDEPENDENT_RESEARCH_BENCHMARK_V1"
TOL=3e-6
START=datetime(2020,1,1,tzinfo=timezone.utc)
KIND={"forced_commitment_milp","zero_storage_ramp_lp","storage_ramp_lp"}

def demand(ok,why):
    if not ok:raise AssertionError("v0.9.18 independent witness: "+why)

def close(a,b,which,tol=TOL):
    demand(math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,
           f"{which}: {a} != {b}")

def witness_case(item):
    kind=item["kind"]
    n=item["interval_count"]
    demand(kind in KIND and n>=4 and n%4==0,"Unexpected model kind or scale")
    demand(item["declared_duration_hours"]==n/4,"Wrong quarter-hour duration")
    cfg=item["problem_input"]
    demand(cfg["input_provenance"]==
          "PURELY_INVENTED_NO_BIOGAS_EQUIPMENT_CALIBRATION_OR_OBSERVED_MARKET_PRICES",
          "Source incorrectly labelled real")
    gas=cfg["gas_production_mw_lhv"]
    prices=item["price_eur_mwh"]
    rows=item["rows"]
    demand(len(rows)==len(prices)==len(gas)==n,"Truncated time series")
    demand(item["solver_nominal_success"] and item["status"].startswith("SOLVED_"),
           "Reported solver did not succeed")
    limit=cfg.get("experimental_v097") or cfg.get("experimental_v095")
    demand(cfg["electric_efficiency_lhv"]==.4 and cfg["thermal_efficiency_lhv"]==.2,
           "Unexpected efficiency convention")
    demand(cfg["fixed_flaring_mw_lhv"]==0 and cfg["fixed_losses_mw_lhv"]==0,
           "Independent witness does not support flaring/loss terms")
    demand(cfg["price_zone"]=="SE3" and cfg["gas_storage_capacity_mwh_lhv"]>=0,
           "Invalid zone/storage")
    capacity=cfg["gas_storage_capacity_mwh_lhv"]
    # Reconstruct the entire fictional input *without* importing the
    # optimizer or trusting reported scenario arrays. This is essential:
    # a false input price/gas profile cannot pass by changing the JSON.
    if kind=="forced_commitment_milp":
        demand(capacity==0.0 and cfg["initial_gas_inventory_mwh_lhv"]==0.0,
               "Forced commitment source contract was changed")
        demand(cfg["electric_rating_mw"]==.8
               and cfg["heat_demand_mw_th"]==.15
               and cfg["aux_heat_capacity_mw_th"]==.2
               and cfg["heat_dump_capacity_mw_th"]==.3
               and cfg["aux_heat_cost_eur_per_mwh_th"]==3.
               and cfg["heat_dump_penalty_eur_per_mwh_th"]==1.
               and cfg["chp_variable_cost_eur_per_mwh_e"]==1.,
               "Forced commitment base assumptions changed")
        demand(limit["minimum_on_power_mw_e"]==.2
               and limit["minimum_up_hours"]==.5
               and limit["minimum_down_hours"]==.5
               and limit["initial_on"] is False
               and limit["initial_power_mw_e"]==0.
               and limit["startup_cost_eur"]==5.
               and limit["shutdown_cost_eur"]==2.,
               "Forced commitment startup/shutdown/dwell assumptions changed")
        period=min(96,n)
        expected_gas=[0. if i%period < period//2 else 2. for i in range(n)]
    else:
        demand(cfg["electric_rating_mw"]==.8
               and cfg["heat_demand_mw_th"]==.2
               and cfg["aux_heat_capacity_mw_th"]==.25
               and cfg["heat_dump_capacity_mw_th"]==.5
               and cfg["aux_heat_cost_eur_per_mwh_th"]==4.
               and cfg["heat_dump_penalty_eur_per_mwh_th"]==1.
               and cfg["chp_variable_cost_eur_per_mwh_e"]==.5,
               "Buffered LP base assumptions changed")
        demand(limit["minimum_power_mw_e"]==.1
               and limit["ramp_up_mw_e_per_hour"]==.4
               and limit["ramp_down_mw_e_per_hour"]==.4
               and limit["initial_power_mw_e"]==.4,
               "Buffered LP ramp/minimum output assumptions changed")
        if kind=="storage_ramp_lp":
            demand(capacity==.75
                   and cfg["initial_gas_inventory_mwh_lhv"]==.375,
                   "Buffered scenario store assumptions changed")
        else:
            demand(capacity==0.
                   and cfg["initial_gas_inventory_mwh_lhv"]==0.,
                   "No-storage LP assumptions changed")
        expected_gas=[1.]*n
    demand(len(gas)==len(expected_gas)
           and all(abs(actual-expected)<1e-12
                   for actual,expected in zip(gas,expected_gas)),
           "Synthetic gas-source pattern altered")
    expected_prices=(20.,95.,35.,110.,25.,85.)
    demand(all(abs(p-expected_prices[(i//16)%6])<1e-12
               for i,p in enumerate(prices)),
           "Synthetic price scenario altered")
    previous_stock=cfg["initial_gas_inventory_mwh_lhv"]
    first_stock=previous_stock
    prior_on=int(limit["initial_on"]) if kind=="forced_commitment_milp" else 1
    previous_power=limit["initial_power_mw_e"]
    starts=stops=0
    total_electric=total_gas=total_heat=total_aux=total_dump=0.0
    gross=variable_cost=aux_cost=dump_cost=0.0
    max_gas=max_heat=max_ramp=max_bound=0.0
    distinct_output=[]
    for i,row in enumerate(rows):
        expected_timestamp=(START+timedelta(minutes=15*i)).isoformat()
        demand(row["start_utc"]==expected_timestamp,f"{kind}/{n}/row {i} time gap/offset")
        close(row["dt_h"],.25,"hour fraction")
        price=prices[i]
        demand(math.isfinite(price),"Nonfinite invented price")
        published_row_price=row["price_eur_mwh"] if kind=="forced_commitment_milp" else row["market_price_eur_mwh"]
        close(published_row_price,price,"Original solver row price and source scenario",1e-10)
        p=float(row["power_mw_e"] if kind=="forced_commitment_milp"
                else row["electric_power_mw_e"])
        u=float(row["gas_use_mw_lhv"])
        stock=float(row["stock_end_mwh_lhv"])
        heat=float(row["useful_heat_mw_th"] if kind=="forced_commitment_milp"
                    else row["heat_served_chp_mw_th"])
        aux=float(row["aux_heat_mw_th"] if kind=="forced_commitment_milp"
                   else row["heat_served_auxiliary_mw_th"])
        dump=float(row["dump_heat_mw_th"] if kind=="forced_commitment_milp"
                    else row["heat_rejected_mw_th"])
        demand(min(u,p,stock,heat,aux,dump)>=-TOL,"Nonphysical negative energy/stock")
        max_bound=max(max_bound,p-cfg["electric_rating_mw"],
                      stock-capacity,aux-cfg["aux_heat_capacity_mw_th"],
                      dump-cfg["heat_dump_capacity_mw_th"])
        close(p,.4*u,"independent electric conversion")
        close(.2*u,heat+dump,"independent CHP heat generation balance")
        close(cfg["heat_demand_mw_th"],heat+aux,"independent heat service balance")
        residual=stock-previous_stock-(gas[i]-u)*.25
        max_gas=max(max_gas,abs(residual))
        max_heat=max(max_heat,abs((heat+dump-.2*u)*.25),
                     abs((heat+aux-cfg["heat_demand_mw_th"])*.25))
        if kind=="forced_commitment_milp":
            # Zero storage and zero flaring force EACH interval's gas use.
            # Since gas is exactly 0 or 2, binary ON/OFF is uniquely fixed.
            demand(capacity==0. and first_stock==0.,"Unique oracle needs zero storage")
            demand(gas[i] in (0.,2.),"Unexpected gas pulse")
            close(u,gas[i],f"{i}: zero-buffer fixed gas use")
            on=int(row["on"])
            start=int(row["startup"])
            stop=int(row["shutdown"])
            demand(on==int(gas[i]>0),f"binary state not uniquely fixed at {i}")
            demand(start==int(prior_on==0 and on==1),f"start transition at {i}")
            demand(stop==int(prior_on==1 and on==0),f"stop transition at {i}")
            demand(p>=limit["minimum_on_power_mw_e"]-TOL if on else abs(p)<=TOL,
                   "Minimum/on nameplate")
            if prior_on==on==1:
                step=.25 if i else .125
                max_ramp=max(max_ramp,p-previous_power-limit["ramp_up_mw_e_per_hour"]*step,
                             previous_power-p-limit["ramp_down_mw_e_per_hour"]*step)
            prior_on=on
            starts+=start;stops+=stop
            distinct_output.append(on)
        else:
            demand(p>=limit["minimum_power_mw_e"]-TOL,"Always-ON minimum power")
            step=.125 if i==0 else .25
            max_ramp=max(max_ramp,p-previous_power-limit["ramp_up_mw_e_per_hour"]*step,
                         previous_power-p-limit["ramp_down_mw_e_per_hour"]*step)
        gross+=p*price*.25
        variable_cost+=p*cfg["chp_variable_cost_eur_per_mwh_e"]*.25
        aux_cost+=aux*cfg["aux_heat_cost_eur_per_mwh_th"]*.25
        dump_cost+=dump*cfg["heat_dump_penalty_eur_per_mwh_th"]*.25
        total_electric+=p*.25;total_gas+=u*.25
        total_heat+=heat*.25;total_aux+=aux*.25;total_dump+=dump*.25
        previous_stock=stock;previous_power=p
    demand(max_gas<1e-7 and max_heat<1e-7 and max_bound<1e-7,
           f"Primal constraints fail: gas={max_gas} heat={max_heat} bound={max_bound}")
    demand(max_ramp<1e-7,"Midpoint ramp violation")
    close(previous_stock,first_stock,"Cyclic inventory",1e-7)
    close(total_gas,sum(gas)*.25,"Full horizon gas conservation",1e-7)
    close(total_electric,.4*total_gas,"Full electric first-law model",1e-7)
    close(total_heat+total_dump,.2*total_gas,"Full modeled heat conversion",1e-7)
    close(total_heat+total_aux,cfg["heat_demand_mw_th"]*n*.25,
          "Full heat service",1e-7)
    ledger=item["reported_ledger"]
    for k,independent in (
       ("gas_utilized_mwh_lhv",total_gas),
       ("electricity_generated_mwh",total_electric),
       ("useful_chp_heat_delivered_mwh_th",total_heat),
       ("auxiliary_heat_delivered_mwh_th",total_aux),
       ("heat_dumped_mwh_th",total_dump),
       ("gross_electricity_revenue_eur",gross),
       ("chp_variable_cost_eur",variable_cost),
       ("auxiliary_heat_cost_eur",aux_cost),
       ("heat_dump_penalty_eur",dump_cost),
    ):close(float(ledger[k]),independent,"Ledger "+k,1e-6)
    objective=gross-variable_cost-aux_cost-dump_cost
    if kind=="forced_commitment_milp":
        objective-=starts*limit["startup_cost_eur"]+stops*limit["shutdown_cost_eur"]
        close(item["reported_start_count"],starts,"start count")
        close(item["reported_stop_count"],stops,"stop count")
        close(item["solver_mip_gap"],0.,"MIP gap",1e-7)
        demand(item["fixed_reference_feasible"],"Unique fixed comparator incorrectly infeasible")
        # Dwell: constructed 12h OFF / 12h ON blocks; repeated every day.
        # For 4/8 source series, verify integer elapsed periods explicitly.
        for i,on in enumerate(distinct_output):
            if (i==0 or distinct_output[i-1]!=on):
                if i and on:
                    required=int(round(limit["minimum_up_hours"]/.25))
                    demand(all(x==1 for x in distinct_output[i:i+required])
                           and len(distinct_output[i:i+required])==required,"Startup dwell failed")
                elif i:
                    required=int(round(limit["minimum_down_hours"]/.25))
                    demand(all(x==0 for x in distinct_output[i:i+required])
                           and len(distinct_output[i:i+required])==required,"Shutdown dwell failed")
        # This is a genuine independent optimum certificate for THIS
        # specific synthetic case: gas inventory C=0 forces u_t=gas_t,
        # and p_t=.4u_t forces every binary and start/stop variable.
        # Therefore the independently calculated objective is not merely
        # a feasible primal value: it is the unique model optimum.
        optimum_scope="EXACT_ALGEBRAIC_UNIQUE_SOLUTION_FOR_FIXED_ZERO_BUFFER_PULSE_CASE"
    else:
        demand(item["reported_start_count"] is None,"LP cannot claim binary starts")
        demand(item["reported_lp_relaxation_upper_bound_eur"]+TOL>=objective,
               "LP published theoretical upper bound below primal")
        if kind=="zero_storage_ramp_lp":
            demand(capacity==0,"No-buffer reference unexpectedly has buffer")
            close(total_gas,n*.25,"Fixed always-on gas use")
            demand(all(abs(r["gas_use_mw_lhv"]-1)<1e-6 for r in rows),
                   "No-storage flexible LP invented gas shifting")
        optimum_scope=(
            "EXACT_ALGEBRAIC_ZERO_BUFFER_LP_SOLUTION_FROM_GAS_CONSERVATION"
            if kind=="zero_storage_ramp_lp" else
            "PRIMAL_CONSERVATION_AND_SOLVER_REPORTED_LOOSE_LP_BOUND_NOT_INDEPENDENT_DUAL_PROOF"
        )
    close(item["reported_net_contribution_eur"],objective,"independent monetary objective",1e-5)
    return {
      "case":item["case"],"kind":kind,"intervals":n,
      "independently_recomputed_electricity_mwh":round(total_electric,7),
      "independently_recomputed_gas_use_mwh_lhv":round(total_gas,7),
      "independently_recomputed_heat_service_mwh_th":round(total_heat+total_aux,7),
      "independently_recomputed_objective_eur":round(objective,7),
      "independently_verified_start_count":starts if kind=="forced_commitment_milp" else None,
      "independently_verified_stop_count":stops if kind=="forced_commitment_milp" else None,
      "independent_optimality_claim":optimum_scope,
      "max_gas_balance_residual_mwh":max_gas,
      "max_heat_balance_residual_mwh":max_heat,
      "max_ramp_over_limit_mw":max(0,max_ramp),
      "max_capacity_over_limit":max(0,max_bound),
      "status":"PASS_INDEPENDENT_NUMERICAL_PRIMAL_CHECK_AND_CASE_SCOPED_WITNESS",
    }

def audit(payload:dict)->dict:
    demand(payload["protocol"]==PROTOCOL and payload["version"]=="0.9.18",
           "Wrong benchmark protocol")
    demand(payload["status"].startswith("PASS_EXECUTED_"),"Incomplete reported execution")
    demand(payload["claims"]["real_plant_telemetry_used"] is False
           and payload["claims"]["biogas_engine_calibration_established"] is False
           and payload["claims"]["real_market_forecast_or_contracts_used"] is False
           and payload["claims"]["LP_global_optimality_independently_proven"] is False,
           "Research exclusions removed")
    results=[witness_case(c) for c in payload["cases"]]
    unique={(c["intervals"],c["kind"]):c for c in results}
    demand(len(unique)==len(results)==3*len(payload["scales"]),
           "Missing/duplicate experimental scale cases")
    for n in payload["scales"]:
        demand(all((n,k) in unique for k in KIND),"Incomplete scale/method combination")
        buffered=unique[n,"storage_ramp_lp"]["independently_recomputed_objective_eur"]
        empty=unique[n,"zero_storage_ramp_lp"]["independently_recomputed_objective_eur"]
        demand(buffered>=empty-1e-5,"Extra storage made chosen feasible objective worse")
    if max(payload["scales"])>=96:
        controls=payload["infeasible_synthetic_controls"]
        demand(len(controls)==3 and all(c["optimizer_rejected"] is True for c in controls),
               "At least one analytical infeasible control failed")
        demand({c["kind"] for c in controls}=={
             "DECLARED_SYNTHETIC_INFEASIBLE_insufficient_aux_heat",
             "DECLARED_SYNTHETIC_INFEASIBLE_rating_too_small_for_forced_gas",
             "DECLARED_SYNTHETIC_INFEASIBLE_mandatory_up_dwell_exceeds_remaining_horizon",
        },"Incorrect synthetically infeasible controls")
    return {
      "protocol":"BIOGASFLEX_V0918_INDEPENDENT_STDLIB_PRIMAL_AND_UNIQUE_OPTIMUM_AUDIT_V1",
      "status":"PASS_INDEPENDENT_SYNTHETIC_MULTISCALE_RESEARCH_MODEL_WITNESSES",
      "case_count":len(results),
      "input_scales":payload["scales"],
      "total_independently_rechecked_quarter_hour_rows":sum(x["intervals"] for x in results),
      "forced_zero_buffer_models_uniquely_optimal":sum(x["kind"]=="forced_commitment_milp" for x in results),
      "buffered_LP_models_primal_checked_not_dual_certified":sum(x["kind"]=="storage_ramp_lp" for x in results),
      "infeasible_synthetic_controls_rejected":len(payload["infeasible_synthetic_controls"]),
      "cases":results,
      "plant_calibrated":False,"real_forecast_or_market_profit_validated":False,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output",type=Path,required=False)
    a=p.parse_args()
    result=audit(json.loads(a.input.read_text(encoding="utf8")))
    if a.output is not None:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2,allow_nan=False))
