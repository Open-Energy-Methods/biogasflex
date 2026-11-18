"""Independent stdlib audit of v0.9.25 source-paired parameter envelope.

No imports of any biogasflex code, optimizer, or new v0.9.25
implementation. Independently reconstructs all 54 cells x source days,
the seven-calendar-day TRAIN-ONLY block bootstrap and 54 worst-case
gas-inventory intervals. Calls the previous independent v0.9.24 ledger
auditor for the unchanged baseline's source, first-stage, and metering.
A valid model certificate cannot be described as a field safety result.
"""
from __future__ import annotations

from datetime import date,timedelta
from hashlib import sha256
import argparse
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parent
def separate(module_name,path):
    s=importlib.util.spec_from_file_location(module_name,ROOT/path)
    m=importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m
PREV=separate("independent_v0924_for_v0925","audit_v0924_award_independent.py")
SOURCE=separate("independent_v0922_source_for_v0925","audit_v0922_causal_independent.py")
PROTOCOL="BIOGASFLEX_V0925_PREDECLARED_PAIRED_SOURCE_EXPOST_PHYSICAL_AND_INTERVAL_ENVELOPE_V1"
CAPS=[.75,1.5,3.]
ALPHAS=[0.,1.,1.5]
BACKUPS=[0.,.2]
AWARDS=[.09,.10,.15]
BANDS={
 "full_synthetic_clip":[.78,1.22],
 "narrow_assumption_not_guaranteed":[.9,1.1],
 "deterministic_nominal_only":[1.,1.],
}
EPS=5e-5
D=.25
ETAE=.4
ETAH=.2
S0=.75
P0=.4
RC=.8
DUMP=.4
BOOT_DAYS=7
BOOT_REPS=200
BOOT_TARGET=92
BOOT_SEED=20261118


def demand(ok,reason):
    if not ok:
        raise AssertionError("INDEPENDENT_V0925_ENVELOPE: "+reason)


def near(a,b,reason,tol=2e-7):
    demand(isinstance(a,(int,float)) and isinstance(b,(int,float))
           and math.isfinite(a) and math.isfinite(b) and abs(a-b)<=tol,
           f"{reason}: got {a}, wanted {b}")


def change_source(source,day,alpha):
    out_g=[]
    out_h=[]
    for h in range(8,14):
        gas,heat=SOURCE.projected_hour(source,day,h)
        g=max(.78,min(1.22,1+alpha*(gas-1)))
        ht=max(.105,min(.195,.15+alpha*(heat-.15)))
        out_g.append(round(g,8))
        out_h.append(round(ht,8))
    return out_g,out_h


def direct_path(gas,heat,award,cap,backup,states=None):
    if states is None:states=[1]*24
    demand(len(gas)==len(heat)==6 and len(states)==24,
           "Daily gas/heat/commitment length incorrect")
    consumption=award/(ETAE*D)
    stock=S0
    mx=mn=S0
    last_power=P0
    prev_on=1
    problems=set()
    total_gas=0.
    for t in range(24):
        state=states[t]
        demand(state in (0,1),"Bad original frozen commitment")
        if state==1:
            if not (.5-EPS<=consumption<=2.+EPS):
                problems.add("binary_or_fuel_rating")
        elif abs(consumption)>EPS:
            problems.add("binary_or_fuel_rating")
        power=ETAE*consumption
        if prev_on==state==1:
            limit=RC*(D/2 if t==0 else D)
            if abs(power-last_power)>limit+EPS:
                problems.add("on_to_on_electric_ramp")
        h=heat[t//4]
        produced=ETAH*consumption
        lo=max(0.,h-backup,produced-DUMP)
        hi=min(h,produced)
        if lo>hi+EPS:problems.add("heat_backup_or_dump_capacity")
        stock+=D*(gas[t//4]-consumption)
        total_gas+=D*gas[t//4]
        mn=min(mn,stock)
        mx=max(mx,stock)
        if stock< -EPS: problems.add("gas_stock_lower_bound")
        if stock>cap+EPS: problems.add("gas_stock_upper_bound")
        prev_on=state
        last_power=power
    return {
      "ok":not problems,
      "cyclic":abs(stock-S0)<=EPS,
      "violations":sorted(problems),
      "delta":round(stock-S0,10),
      "min":round(mn,10),
      "max":round(mx,10),
      "source_gas_energy":round(total_gas,10),
    }


def intervals(award,cap,backup,low,high):
    burn=award/(ETAE*D)
    lower=S0+24*D*(low-burn)
    upper=S0+24*D*(high-burn)
    lo=min(S0,lower)
    hi=max(S0,upper)
    rated=.5-EPS<=burn<=2.+EPS
    ramp=abs(ETAE*burn-P0)<=RC*D/2+EPS
    thermal=True
    for demand_heat in (.105,.195):
        loh=max(0.,demand_heat-backup,ETAH*burn-DUMP)
        hih=min(demand_heat,ETAH*burn)
        thermal=thermal and loh<=hih+EPS
    feasible=rated and ramp and thermal and lo>=-EPS and hi<=cap+EPS
    cyc=feasible and abs(high-low)<=EPS and abs(low-burn)<=EPS
    return {
     "all_independent_bounded_gas_paths_feasible":bool(feasible),
     "all_bounded_paths_terminal_stock_matched":bool(cyc),
     "worst_lower_stock_mwh_lhv":round(lo,10),
     "worst_upper_stock_mwh_lhv":round(hi,10),
     "lower_gas_terminal_stock_mwh_lhv":round(lower,10),
     "upper_gas_terminal_stock_mwh_lhv":round(upper,10),
     "generator_rating_ok":bool(rated),
     "initial_half_interval_ramp_ok":bool(ramp),
     "all_supported_heat_demands_serviceable":bool(thermal),
     "all_future_gas_arrival_paths_within_assumed_bounds_only":True
    }


def seven_day_starts(training):
    dates=[date.fromisoformat(x["date_utc"]) for x in training]
    return [i for i in range(len(training)-6)
            if all(dates[i+k]==dates[i]+timedelta(days=k)
                   for k in range(7))]


def source_pearson(rows):
    pairs=[(float(d["price_baseline_error_eur_mwh"][h]),
            float(d["regional_load_error_relative"][h]))
           for d in rows for h in range(8,14)]
    a=[p[0] for p in pairs];b=[p[1] for p in pairs]
    am=math.fsum(a)/len(a); bm=math.fsum(b)/len(b)
    num=math.fsum((x-am)*(y-bm) for x,y in pairs)
    den=math.sqrt(math.fsum((x-am)**2 for x in a)*
                  math.fsum((y-bm)**2 for y in b))
    return round(num/den,10) if den>0 else None


def training_bootstrap(binary,starts,cell):
    seed=int(sha256((str(BOOT_SEED)+"|"+cell).encode("utf8")).hexdigest()[:16],16)
    rng=random.Random(seed)
    samples=[]
    for _ in range(BOOT_REPS):
        chosen=[]
        for _ in range((BOOT_TARGET+BOOT_DAYS-1)//BOOT_DAYS):
            pos=starts[rng.randrange(len(starts))]
            chosen.extend(range(pos,pos+BOOT_DAYS))
        samples.append(math.fsum(float(binary[i])
                                for i in chosen[:BOOT_TARGET])/BOOT_TARGET)
    ss=sorted(samples)
    return round(ss[int(.05*(BOOT_REPS-1))],8),round(ss[int(.95*(BOOT_REPS-1))],8)


def inspect(source,baseline,report):
    demand(report["protocol"]==PROTOCOL,"Protocol modified")
    demand(source["source"]["sha256"]==report["source_sha256"]==
           SOURCE.SRC_SHA,"Original frozen publisher source digest mismatch")
    demand(report["holdout_data_used_to_choose_grid_or_awards"] is False,
           "Post-outcome tuning claimed")
    for k in ("gas_and_heat_couplings_empirically_calibrated",
              "true_site_gas_heat_measurements_present",
              "original_bid_time_price_forecast_vintages_verified",
              "market_contract_awards_real"):
        demand(report[k] is False,"Falsely claimed field/source validity "+k)
    demand(report["expost_physical_feasibility_not_a_causal_dispatch_policy"]
           is True,"Ex-post hindsight falsely called causal control")
    demand(report["robust_interval_bounds_are_assumptions_not_probabilistic_forecasts"]
           is True,"Assumed gas bounds falsely called calibrated intervals")
    demand(report["no_gas_vent_grid_import_fuel_purchases_or_imbalance_market_slack"]
           is True,"Unauthorized balancing mechanism")
    demand(report["frozen_chp_schedule_for_sensitivity"]==
           "ALL_ON_24_SLOTS_EQUIPMENT_INITIAL_ON",
           "Benchmark reference first-stage schedule changed")
    pre=report["preregistration_grid"]
    demand(pre["storage_capacity_mwh_lhv"]==CAPS and
           pre["paired_gas_heat_shock_multipliers"]==ALPHAS and
           pre["backup_capacity_mw_th"]==BACKUPS and
           pre["hypothetical_awards_mwh_per_15min"]==AWARDS and
           pre["uniform_hypothetical_gas_bands_mw_lhv"]==BANDS,
           "Changed ex-ante parameter grid")

    prior_certificate=PREV.audit(source,baseline)
    demand(prior_certificate["status"].startswith("PASS_INDEPENDENT"),
           "Parent 92-day hard-export audit failed")
    train=[d for d in source["complete_days"] if
           d["partition"]=="TRAIN_PRIOR_TO_2019_10_01"]
    test=[d for d in source["complete_days"] if
          d["partition"]=="HOLDOUT_FROM_2019_10_01"]
    complete_dates={d["date_utc"] for d in source["complete_days"]}
    eligible=[d for d in test if
              (date.fromisoformat(d["date_utc"])-
               timedelta(days=7)).isoformat() in complete_dates]
    demand(len(eligible)==report["full_heldout_eligible_days"]==92,
           "Holdout denominator incomplete")
    demand(len(train)==report["complete_source_training_days"],
           "Training days count altered")
    demand([x["day_utc"] for x in baseline["cases"]]==
           [d["date_utc"] for d in eligible],"Different source-date sequence")
    expected_on_count=sum(
         baseline["cases"][i]["award_profiles"]["nominal_gas_0p100"]
         ["strategies"]["nominal"]["first_stage_on"]==[1]*24
         for i in range(len(eligible)))
    demand(expected_on_count==
           report["same_as_v0924_original_nominal_first_stage_days"],
           "False claim of parent-policy commitment equivalence")
    mismatch=0
    for i,day in enumerate(eligible):
        g,h=change_source(source,day,1.)
        for id,award in [("floor_budget_0p090",.09),
                         ("nominal_gas_0p100",.1),
                         ("initial_ramp_stress_0p150",.15)]:
            record=baseline["cases"][i]["award_profiles"][id]["strategies"]["nominal"]
            analytic=direct_path(g,h,award,1.5,.2,
                                 states=record["first_stage_on"])
            if record["replays"]["award_only"]["feasible"] and not analytic["ok"]:
                mismatch+=1
    demand(mismatch==0==
           report["v0924_reported_deliveries_contradict_original_expost_physics_count"],
           "Parent accepted award contradicts independent physical calculation")

    seven=seven_day_starts(train)
    demand(len(seven)==report["source_training_contiguous_7day_bootstrap_start_blocks"]
           and len(seven)>0,"Invalid training-only chronology/block sample")
    demand(source_pearson(train)==
           report["training_source_price_load_forecast_error_pearson"],
           "Training price/load paired correlation changed")
    demand(source_pearson(eligible)==
           report["heldout_source_price_load_forecast_error_pearson_DESCRIPTIVE_ONLY"],
           "Held-out price/load paired correlation changed")

    paths_train={alpha:[change_source(source,d,alpha) for d in train]
                 for alpha in ALPHAS}
    paths_test={alpha:[change_source(source,d,alpha) for d in eligible]
                for alpha in ALPHAS}
    rows=report["simulation_parameter_grid"]
    demand(len(rows)==len(CAPS)*len(ALPHAS)*len(BACKUPS)*len(AWARDS)==54,
           "Predeclared cell count altered")
    loc=0
    total_recomputed=0
    for cap in CAPS:
        for alpha in ALPHAS:
            for backup in BACKUPS:
                for award in AWARDS:
                    row=rows[loc];loc+=1
                    key=f"cap={cap:.2f}|paired_shock={alpha:.2f}|backup={backup:.2f}|award={award:.3f}"
                    demand(row["cell_id"]==key,"Out-of-order grid or changed cell ID")
                    demand((row["storage_capacity_mwh_lhv"],
                            row["paired_synthetic_gas_and_heat_shock_multiplier"],
                            row["heat_backup_capacity_mwth"],
                            row["hypothetical_award_mwh_per_15min"])==
                           (cap,alpha,backup,award),"Altered grid parameter")
                    training=[direct_path(*path,award,cap,backup)
                              for path in paths_train[alpha]]
                    holdout=[direct_path(*path,award,cap,backup)
                             for path in paths_test[alpha]]
                    total_recomputed+=len(training)+len(holdout)
                    train_flags=[p["ok"] for p in training]
                    demand(row["training_days"]==len(training) and
                           row["holdout_days"]==len(holdout) and
                           row["training_physically_feasible_days"]==sum(train_flags) and
                           row["holdout_expost_physically_feasible_days"]==
                           sum(x["ok"] for x in holdout),
                           "Independent exact fixed-award physical counts disagree")
                    demand(row["holdout_cyclic_inventory_matched_and_feasible_days"]==
                           sum(x["ok"] and x["cyclic"] for x in holdout),
                           "Cyclic matched-service count differs")
                    all_reasons=sorted(set(k for p in holdout for k in p["violations"]))
                    true_count={k:sum(k in p["violations"] for p in holdout)
                                for k in all_reasons}
                    demand(row["holdout_any_constraint_family_violation_day_counts"]
                           ==true_count,"Physical failure family attribution altered")
                    near(row["holdout_terminal_stock_delta_min_mwh_lhv"],
                         min(p["delta"] for p in holdout),"Minimum terminal stock delta")
                    near(row["holdout_terminal_stock_delta_max_mwh_lhv"],
                         max(p["delta"] for p in holdout),"Maximum terminal stock delta")
                    p05,p95=training_bootstrap(train_flags,seven,key)
                    near(row["training_descriptive_7day_block_bootstrap_p05"],
                         p05,"Training-only source-block bootstrap 5th percentile")
                    near(row["training_descriptive_7day_block_bootstrap_p95"],
                         p95,"Training-only source-block bootstrap 95th percentile")
                    demand(row["training_bootstrap_replicates"]==BOOT_REPS and
                           row["training_source_days_per_resample"]==BOOT_TARGET and
                           row["confidence_interval_or_field_probability_claim"] is False,
                           "Statistical interval falsely described or sampling changed")

    bands=report["analytical_full_interval_bound_certificates"]
    demand(len(bands)==len(CAPS)*len(BACKUPS)*len(AWARDS)*len(BANDS)==54,
           "Incorrect predeclared bounded gas cases")
    ix=0
    universal=0
    for cap in CAPS:
        for backup in BACKUPS:
            for award in AWARDS:
                for label,(lo,hi) in BANDS.items():
                    row=bands[ix];ix+=1
                    demand((row["storage_capacity_mwh_lhv"],
                            row["heat_backup_capacity_mwth"],
                            row["hypothetical_award_mwh_per_15min"],
                            row["declared_gas_interval_band"],
                            row["hypothetical_gas_lower_mw_lhv"],
                            row["hypothetical_gas_upper_mw_lhv"])==
                           (cap,backup,award,label,lo,hi),
                           "Interval certificate scenario changed")
                    true=intervals(award,cap,backup,lo,hi)
                    for k,v in true.items():
                        if isinstance(v,float):
                            near(row[k],v,"Independent interval "+k)
                        else:
                            demand(row[k]==v,"Interval bound certificate mismatch "+k)
                    original_gases=paths_test[1.]
                    coverage=sum(all(lo-EPS<=g<=hi+EPS for g in gas)
                                 for gas,heat in original_gases)
                    demand(row["historical_source_paired_unmodified_holdout_days_with_all_synthetic_gas_hours_in_band"]==coverage
                           and row["source_heldout_days"]==len(eligible),
                           "Original heldout interval coverage incorrectly stated")
                    universal+=int(row["all_independent_bounded_gas_paths_feasible"])
    return {
        "status":"PASS_INDEPENDENT_V0925_PREDECLARED_54CELL_GAS_HEAT_STOCK_ENVELOPE",
        "publisher_source_sha256":SOURCE.SRC_SHA,
        "full_source_heldout_days_verified":len(eligible),
        "training_source_days":len(train),
        "preregistered_cells_independently_recomputed":len(rows),
        "independent_analytical_worst_bound_certificates":len(bands),
        "physical_day_cell_paths_recomputed":total_recomputed,
        "frozen_training_only_calendar_consecutive_7day_bootstrap_blocks":len(seven),
        "training_only_whole_day_block_bootstrap_replicates_per_cell":BOOT_REPS,
        "robust_bounded_physical_certificates_passed":universal,
        "source_paired_forecast_error_vectors_not_independently_resampled":True,
        "expost_feasibility_not_true_causal_control":True,
        "real_chp_gas_heat_or_market_contracts_validated":False,
        "positive_field_certainty_claim":False,
        "previous_v0924_award_ledger_independent_audit":"PASS",
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True)
    p.add_argument("--study",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=inspect(json.loads(args.source.read_text(encoding="utf8")),
                   json.loads(args.baseline.read_text(encoding="utf8")),
                   json.loads(args.study.read_text(encoding="utf8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    main()
