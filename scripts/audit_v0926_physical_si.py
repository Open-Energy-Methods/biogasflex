"""Independent SI-energy assurance for the frozen CHP benchmark.

No optimizer or BiogasFlex imports. Independently checks every executed
quarter-hour prefix, including failures, in the v0.9.23 and v0.9.24 studies.
A chemical energy ledger is NOT a gas mass or pressure model. The unrecovered
fraction is an algebraic LHV remainder, NOT measured exhaust heat.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import math
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
J_PER_MWH=3_600_000_000.
W_PER_MW=1_000_000.
SECONDS=900.
# Dimensions explicit: independent residual allowances inherited from
# the published native tolerance 5e-5, not physical uncertainty budgets.
ENERGY_TOL_J=5e-5*J_PER_MWH
POWER_TOL_W=5e-5*W_PER_MW
AWARD_TOL_J=5e-7*J_PER_MWH
INITIAL_J=.75*J_PER_MWH
CAP_J=1.5*J_PER_MWH
ETA_E=.4
ETA_H=.2
RAMP_W_PER_S=.8*W_PER_MW/3600.
SOURCE_SHA="6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"

# Separate reference values, including units; don't import solver constants.
EXPECTED={
 "DT":(.25,"h"),"N":(24,"1"),"HOURS":(6,"h"),"HOUR_START":(8,"h_UTC"),
 "RATING":(.8,"MW_e"),"ETA_E":(.4,"MWh_e/MWh_LHV"),
 "ETA_H":(.2,"MWh_th/MWh_LHV"),"STOCK_CAP":(1.5,"MWh_LHV"),
 "STOCK_INITIAL":(.75,"MWh_LHV"),"INITIAL_ON":(1,"1"),
 "INITIAL_POWER":(.4,"MW_e"),"MIN_ON":(.2,"MW_e"),
 "RAMP":(.8,"MW_e/h"),"HEAT_BACKUP_CAP":(.2,"MW_th"),
 "HEAT_DUMP_CAP":(.4,"MW_th"),"GAS_BASE":(1,"MW_LHV"),
 "HEAT_BASE":(.15,"MW_th"),"START_COST":(5,"EUR/start"),
 "STOP_COST":(1,"EUR/stop"),"AUX_COST":(6,"EUR/MWh_th"),
 "DUMP_COST":(1,"EUR/MWh_th"),"VAR_COST":(.75,"EUR/MWh_e"),
 "ABS_TOL":(.00005,"numeric_model_native_units"),
}
REQUIRED_GAPS={
 "gas_composition_and_lhv_reference_conditions",
 "traceable_gas_mass_or_standard_volume_flow",
 "gas_holder_pressure_volume_temperature_and_control",
 "generator_gross_to_net_auxiliary_power_and_grid_meter",
 "load_dependent_electrical_and_heat_efficiency_maps",
 "startup_shutdown_fuel_energy_and_emissions",
 "ramp_measurements_and_minimum_up_down_time",
 "backup_heat_fuel_and_efficiency",
 "heat_supply_return_temperatures_and_flow",
 "meter_calibration_uncertainty_and_synchronized_timestamps",
 "actual_accepted_awards_and_forecast_issue_vintages",
}

def require(ok,message):
    if not ok:
        raise AssertionError("INDEPENDENT_V0926_SI: "+message)

def number(x):
    require(type(x) in (float,int) and math.isfinite(x),"Nonfinite/non-numeric physical quantity")
    return float(x)

def residual(x,y,tol,label):
    value=abs(number(x)-number(y))
    require(value<=tol,f"{label}: residual={value:.10g}, tolerance={tol:.10g}")
    return value

def load_script(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/(name+".py"))
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

def check_register(register,implementation,external):
    require(register["schema"]=="biogasflex.v0926.parameter_register.v1","Wrong register schema")
    require(register["all_equipment_field_calibrated"] is False,"False target calibration")
    require(register["source_sha256"]==SOURCE_SHA,"Wrong publisher digest")
    rows=register["parameters"]
    require(len(rows)==len(EXPECTED) and {p["symbol"] for p in rows}==set(EXPECTED),
            "Missing/duplicated parameter")
    # Read literal constants from source using AST, WITHOUT executing it.
    literals={}
    for node in ast.parse(implementation).body:
        if isinstance(node,ast.Assign):
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id in EXPECTED:
                    require(target.id not in literals,"Duplicate solver constant assignment")
                    literals[target.id]=ast.literal_eval(node.value)
    require(set(literals)==set(EXPECTED),"Missing checked solver constant")
    for entry in rows:
        symbol=entry["symbol"]
        val,unit=EXPECTED[symbol]
        require(entry["value"]==val==literals[symbol],f"Changed {symbol}")
        require(entry["unit"]==unit,f"Wrong units for {symbol}")
        require(entry["classification"] in {
            "numerical_discretization","numerical_tolerance",
            "synthetic_equipment_assumption","synthetic_initial_condition",
            "synthetic_proxy_assumption","synthetic_economic_assumption"},
            f"Improper provenance for {symbol}")
        require(entry["measured_on_target_equipment"] is False and
                bool(entry["provenance"]) and bool(entry["meaning"]),
                "Fabricated calibration or missing provenance")
    require(set(register["field_gaps"])==REQUIRED_GAPS,"Missing field qualification gap")
    derived=register["derived"]
    for key,val in {"fuel_min_mw_lhv":.5,"fuel_max_mw_lhv":2.,
                    "conversion_unrecovered_lhv_fraction":.4,
                    "dt_seconds":900,"mwh_to_joule":3_600_000_000}.items():
        residual(derived[key],val,1e-10,"Derived parameter "+key)
    sources={s["id"]:s for s in external["sources"]}
    refs=register["external_evidence"]
    require(len(refs)==2 and {x["id"] for x in refs}==set(sources),"External source registry differs")
    for src in refs:
        require(src["doi"]==sources[src["id"]]["doi"] and
                src["status"] in {"different_technology_not_target_calibration",
                                  "different_fuel_and_site_not_target_calibration"},
                "External study wrongly presented as target calibration")
    require(register["proxy_support"]["gas_mw_lhv"]==[.78,1.22] and
            register["proxy_support"]["heat_mw_th"]==[.105,.195],
            "Wrong declared synthetic proxy domains")
    return len(rows)

def audit_replay(replay,states,starts,stops,award=None):
    require(len(states)==len(starts)==len(stops)==24,"Wrong commitment shape")
    rows=replay["completed_15min_rows"]
    require(len(rows)<=24 and len(rows)%4==0,"Truncated physical hour")
    complete=replay["feasible"]
    require(type(complete) is bool,"Invalid feasibility flag")
    require((len(rows)==24)==complete,"Full service flag inconsistent")
    if not complete:
        require(replay["economic_contribution_eur"] is None,"Failed service assigned earnings")
    else:
        require(len(rows)==24,"Missing completed physical intervals")
    if award is not None:
        require(len(award)==24,"Wrong award vector length")
    stock=INITIAL_J
    power=.4*W_PER_MW
    prev_on=1
    e_sum=Counter()
    maxima=Counter()
    switch_count=0
    for t,row in enumerate(rows):
        require(row["quarter_index"]==t and row["hour_index"]==t//4,
                "Chronology failure")
        on,start,stop=states[t],starts[t],stops[t]
        require(on in (0,1) and start==int(on>prev_on) and stop==int(on<prev_on),
                "Inconsistent on/start/stop")
        require((row["on"],row["start"],row["stop"])==(on,start,stop),
                "Executed commitment differs")
        g=number(row["gas_in_mw_lhv"])*W_PER_MW
        fuel=number(row["gas_use_mw_lhv"])*W_PER_MW
        heat=number(row["heat_demand_mw_th"])*W_PER_MW
        useful=number(row["useful_chp_heat_mw_th"])*W_PER_MW
        backup=number(row["backup_heat_mw_th"])*W_PER_MW
        dump=number(row["dumped_heat_mw_th"])*W_PER_MW
        require(min(g,fuel,heat,useful,backup,dump)>=-POWER_TOL_W,
                "Negative energy flow")
        require(.78*W_PER_MW-POWER_TOL_W<=g<=1.22*W_PER_MW+POWER_TOL_W,
                "Gas proxy outside frozen support")
        require(.105*W_PER_MW-POWER_TOL_W<=heat<=.195*W_PER_MW+POWER_TOL_W,
                "Heat proxy outside frozen support")
        electric=ETA_E*fuel
        recovery=ETA_H*fuel
        remainder=fuel-electric-recovery
        require(remainder>=-POWER_TOL_W,"Negative unrecovered LHV energy")
        require((.2*W_PER_MW-POWER_TOL_W<=electric<=.8*W_PER_MW+POWER_TOL_W)
                if on else abs(electric)<=POWER_TOL_W,"CHP electric rating/on limit")
        require(backup<=.2*W_PER_MW+POWER_TOL_W and dump<=.4*W_PER_MW+POWER_TOL_W,
                "Backup/dump exceeds rating")
        if prev_on==on==1:
            allowed=RAMP_W_PER_S*(SECONDS/2 if t==0 else SECONDS)
            require(abs(electric-power)<=allowed+POWER_TOL_W,"Electrical consecutive-ON ramp")
        else:
            switch_count+=int(prev_on!=on)
        end=number(row["stock_end_mwh_lhv"])*J_PER_MWH
        maxima["stock_step_j"]=max(maxima["stock_step_j"],
            residual(end-stock,(g-fuel)*SECONDS,ENERGY_TOL_J,"Storage balance"))
        require(-ENERGY_TOL_J<=end<=CAP_J+ENERGY_TOL_J,"Storage bound")
        maxima["heat_delivery_j"]=max(maxima["heat_delivery_j"],
            residual((useful+backup)*SECONDS,heat*SECONDS,ENERGY_TOL_J,"Useful heat"))
        maxima["recovered_heat_allocation_j"]=max(maxima["recovered_heat_allocation_j"],
            residual((useful+dump)*SECONDS,recovery*SECONDS,ENERGY_TOL_J,"Recovered heat allocation"))
        # Whole modeled boundary: gas input plus external useful backup heat
        # = inventory increase + gross electric + demanded heat + dump + LHV remainder.
        # Backup fuel input and parasitic energy are OUTSIDE this boundary.
        maxima["whole_boundary_step_j"]=max(maxima["whole_boundary_step_j"],
            residual((g+backup)*SECONDS,
                     end-stock+(electric+heat+dump+remainder)*SECONDS,
                     3*ENERGY_TOL_J,"Whole boundary"))
        if award is not None:
            a=number(award[t])*J_PER_MWH
            m=number(row["physical_chp_export_meter_mwh"])*J_PER_MWH
            stated=number(row["contract_awarded_export_mwh"])*J_PER_MWH
            residual(stated,a,AWARD_TOL_J,"Locked award")
            residual(m,electric*SECONDS,AWARD_TOL_J,"Gross proxy meter")
            maxima["award_j"]=max(maxima["award_j"],
                residual(m,a,AWARD_TOL_J,"Award equality"))
        for key,val in {"gas_in_j":g,"fuel_burn_j":fuel,"electric_j":electric,
                        "recovered_heat_j":recovery,"delivered_heat_j":heat,
                        "useful_chp_heat_j":useful,"backup_delivered_heat_j":backup,
                        "dump_heat_j":dump,"unrecovered_lhv_j":remainder}.items():
            e_sum[key]+=val*SECONDS
        stock=end
        power=electric
        prev_on=on
    delta=stock-INITIAL_J
    totals=dict(e_sum)
    get=lambda key:totals.get(key,0.)
    maxima["horizon_stock_j"]=residual(delta,get("gas_in_j")-get("fuel_burn_j"),
                                      max(1,len(rows))*ENERGY_TOL_J,"Horizon storage")
    maxima["horizon_boundary_j"]=residual(get("gas_in_j")+get("backup_delivered_heat_j"),
        delta+get("electric_j")+get("delivered_heat_j")+get("dump_heat_j")+get("unrecovered_lhv_j"),
        3*max(1,len(rows))*ENERGY_TOL_J,"Horizon energy boundary")
    if complete:
        residual(number(replay["terminal_stock_mwh_lhv"])*J_PER_MWH,stock,ENERGY_TOL_J,
                 "Reported terminal inventory")
        # Exact legacy model criterion; use native inventory to avoid conversion roundoff
        matched=abs(number(rows[-1]["stock_end_mwh_lhv"])-.75)<=5e-5
        require(replay["terminal_inventory_matches_initial_for_comparison"]==matched,
                "Fabricated terminal equivalence")
    return {"intervals":len(rows),"complete":complete,
            "terminal_matched":complete and matched,
            "max_abs_residual_j":dict(maxima),
            "inventory_delta_j":delta,"energy_totals_j":totals,
            "switch_transitions_with_unmodeled_transients":switch_count}

def audit(source,reserve,award,register,implementation,external):
    count=check_register(register,implementation,external)
    a23=load_script("audit_v0923_reserve_independent")
    a24=load_script("audit_v0924_award_independent")
    require(a23.audit(source,reserve)["status"].startswith("PASS_INDEPENDENT"),"Parent reserve audit failed")
    require(a24.audit(source,award)["status"].startswith("PASS_INDEPENDENT"),"Parent award audit failed")
    require(len(reserve["cases"])==len(award["cases"])==92,"Not full heldout")
    require([d["day_utc"] for d in reserve["cases"]]==[d["day_utc"] for d in award["cases"]],
            "Holdout sequence mismatch")
    groups={}
    def collect(key,result):
        group=groups.setdefault(key,{"replays":0,"executed_intervals":0,"complete":0,
                        "failed":0,"terminal_matched":0,"max_abs_residual_j":{},
                        "switch_transitions_with_unmodeled_transients":0})
        group["replays"]+=1
        group["executed_intervals"]+=result["intervals"]
        group["complete"]+=int(result["complete"])
        group["failed"]+=int(not result["complete"])
        group["terminal_matched"]+=int(result["terminal_matched"])
        group["switch_transitions_with_unmodeled_transients"]+=result["switch_transitions_with_unmodeled_transients"]
        for label,val in result["max_abs_residual_j"].items():
            group["max_abs_residual_j"][label]=max(
                group["max_abs_residual_j"].get(label,0),val)
    for case in reserve["cases"]:
        for policy in case["policies"].values():
            for mode in ("unprotected","protected"):
                collect("v0923_"+mode,audit_replay(policy[mode],policy["first_stage_on"],
                        policy["first_stage_starts"],policy["first_stage_stops"]))
    for case in award["cases"]:
        for name,profile in case["award_profiles"].items():
            for policy in profile["strategies"].values():
                for mode,replay in policy["replays"].items():
                    collect("v0924_"+name+"_"+mode,
                            audit_replay(replay,policy["first_stage_on"],policy["first_stage_starts"],
                                     policy["first_stage_stops"],profile["quarter_hour_export_mwh"]))
    return {
        "status":"PASS_INDEPENDENT_V0926_PHYSICAL_SI_ENERGY_AND_PARAMETER_REGISTER",
        "source_sha256":SOURCE_SHA,"parameters_checked_against_literal_model":count,
        "heldout_days":92,
        "policy_replays_checked":sum(g["replays"] for g in groups.values()),
        "quarter_hour_prefix_rows_checked":sum(g["executed_intervals"] for g in groups.values()),
        "complete_replays":sum(g["complete"] for g in groups.values()),
        "failed_replays":sum(g["failed"] for g in groups.values()),
        "energy_residual_tolerance_j":ENERGY_TOL_J,"power_tolerance_w":POWER_TOL_W,
        "award_residual_tolerance_j":AWARD_TOL_J,
        "groups":groups,
        "external_reference_datasets_not_used_to_calibrate_target":True,
        "energy_balance_verified_not_gas_mass_or_pressure":True,
        "unrecovered_lhv_is_computed_not_measured":True,
        "backup_fuel_and_net_grid_meter_not_modeled":True,
        "field_qualification":False,
        "unresolved_field_evidence":sorted(REQUIRED_GAPS),
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ("source","reserve","award","output"):
        p.add_argument("--"+arg,type=Path,required=True)
    args=p.parse_args()
    def read(path):return json.loads(path.read_text(encoding="utf8"))
    result=audit(read(args.source),read(args.reserve),read(args.award),
        read(ROOT/"data/evidence/v0926_physical_parameter_register.json"),
        (ROOT/"src/biogasflex/joint_v0921.py").read_text(encoding="utf8"),
        read(ROOT/"data/evidence/v0916_public_chp_source_registry.json"))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2,allow_nan=False))
if __name__=="__main__":
    main()
