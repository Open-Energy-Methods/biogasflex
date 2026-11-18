"""v0.9.25 pre-registered, source-paired CHP physical uncertainty envelope.

This is an EX-POST physical-feasibility and EX-ANTE INTERVAL-bound analysis,
NOT a new causal dispatch policy, an optimized contract bidder, or true
plant-based forecast-error calibration. Historical regional price/load
errors inform fictional biogas and heat proxies only. A fixed 24-quarter
all-ON schedule and three *hypothetical* electricity awards are declared
before any target heldout physical path is reconstructed.

With a fixed award A_t and constant eta_e, CHP burn u_t=A_t/(eta_e*dt)
is uniquely determined, so fuel inventory, heat feasibility, and ramp
constraints can be evaluated by direct conservation without an optimizer.
No unmodelled gas vent, grid import, fuel backup, or settlement slack.
"""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from hashlib import sha256
import json
import math
from pathlib import Path
import random

from . import award_v0924 as a24
from . import causal_v0922 as c22
from . import joint_v0921 as j

PROTOCOL="BIOGASFLEX_V0925_PREDECLARED_PAIRED_SOURCE_EXPOST_PHYSICAL_AND_INTERVAL_ENVELOPE_V1"
CAPACITIES_MWH=(.75,1.5,3.0)
PAIRED_SHOCK_MULTIPLIERS=(0.,1.,1.5)
THERMAL_BACKUP_CAPACITIES_MWTH=(0.,.2)
AWARD_MWH=(.09,.10,.15)
BOUND_BANDS={
    "full_synthetic_clip":(.78,1.22),
    "narrow_assumption_not_guaranteed":(.90,1.10),
    "deterministic_nominal_only":(1.,1.),
}
BOUNDS_HEAT_MWTH=(.105,.195)
DT=.25
ETA_E=.4
ETA_H=.2
RAMP=.8
STOCK_INITIAL=.75
POWER_INITIAL=.4
DUMP_CAP=.4
SOURCE_HOUR_START=8
TARGET_HOURS=6
SLOTS=24
TOL=5e-5
BOOT_SEED=20261118
BOOT_DAYS=7
BOOT_SAMPLES=200
BOOT_TARGET_DAYS=92
FIXED_ALL_ON=tuple([1]*SLOTS)


def require(condition,reason):
    if not condition:
        raise ValueError("v0.9.25 scientific envelope: "+reason)


def clip(v,low,high):
    return min(high,max(low,v))


def physical_fixed_award(gas_hours,heat_hours,*,award_mwh,capacity_mwh,
                         backup_capacity_mwth,states=FIXED_ALL_ON):
    """Reconstruct all 24 stock states, meter energy, heat, and ramp.

    This is a retrospective mathematical test of a fixed awarded export,
    not a controller that could know future source-hour gas arrivals.
    Return ALL violated constraint families, never interpret a failure
    as zero market revenue.
    """
    require(len(gas_hours)==len(heat_hours)==TARGET_HOURS
            and len(states)==SLOTS,"Wrong six-hour trajectory or commitments")
    require(capacity_mwh>=STOCK_INITIAL and
            capacity_mwh<=20 and backup_capacity_mwth>=0,
            "Physical sensitivity values outside declared admissible domain")
    require(math.isfinite(award_mwh) and award_mwh>=0,
            "Nonfinite/negative hypothetical award")
    require(all(math.isfinite(x) and x>=0 for x in gas_hours+heat_hours),
            "Nonphysical synthetic source inputs")
    violations=set()
    stock=STOCK_INITIAL
    previous_power=POWER_INITIAL
    previous_on=1
    minimum_stock=STOCK_INITIAL
    maximum_stock=STOCK_INITIAL
    total_gas=0.
    use=award_mwh/(ETA_E*DT)
    for t in range(SLOTS):
        on=states[t]
        require(on in (0,1),"Nonbinary precommitted CHP state")
        if (on and not (.5-TOL<=use<=2.+TOL)) or (
            not on and not (-TOL<=use<=TOL)):
            violations.add("binary_or_fuel_rating")
        power=ETA_E*use
        if on==previous_on==1 and abs(power-previous_power) > (
            RAMP*(DT/2 if t==0 else DT)+TOL):
            violations.add("on_to_on_electric_ramp")
        h=t//4
        heat=heat_hours[h]
        thermal=ETA_H*use
        min_useful=max(0.,heat-backup_capacity_mwth,thermal-DUMP_CAP)
        max_useful=min(heat,thermal)
        if min_useful>max_useful+TOL:
            violations.add("heat_backup_or_dump_capacity")
        stock+=DT*(gas_hours[h]-use)
        total_gas+=DT*gas_hours[h]
        minimum_stock=min(minimum_stock,stock)
        maximum_stock=max(maximum_stock,stock)
        if stock < -TOL:
            violations.add("gas_stock_lower_bound")
        if stock > capacity_mwh+TOL:
            violations.add("gas_stock_upper_bound")
        previous_on=on
        previous_power=power
    return {
        "physically_feasible_expost":len(violations)==0,
        "constraint_families_violated":sorted(violations),
        "terminal_stock_delta_mwh_lhv":round(stock-STOCK_INITIAL,10),
        "terminal_stock_matched":abs(stock-STOCK_INITIAL)<=TOL,
        "minimum_stock_mwh_lhv":round(minimum_stock,10),
        "maximum_stock_mwh_lhv":round(maximum_stock,10),
        "total_synthetic_gas_arrival_mwh_lhv":round(total_gas,10),
        "total_locked_chp_burn_mwh_lhv":round(use*SLOTS*DT,10),
        "electricity_award_mwh_e":round(award_mwh*SLOTS,10),
    }


def paired_synthetic_six_hour_path(day,training_scalers,shock_multiplier):
    """Preserve real source hourly paired price/load shocks, transform SYNTHETIC gas/heat.

    The source standardizers are computed from training only. Multipliers
    stress both proxy channels TOGETHER. No independent hourly or
    cross-channel random reshuffling is permitted.
    """
    require(shock_multiplier in PAIRED_SHOCK_MULTIPLIERS,
            "Not a preregistered paired-source shock multiplier")
    sc=j._scenario(day,[0.]*24,training_scalers,key="SYNTHETIC_POST_SOURCE_SCORING_ONLY")
    gas=[float(sc["synthetic_gas_production_mw_lhv"][4*h]) for h in range(6)]
    heat=[float(sc["synthetic_site_heat_demand_mw_th"][4*h]) for h in range(6)]
    return {
        "gas":[round(clip(1.+shock_multiplier*(x-1.),.78,1.22),8)
               for x in gas],
        "heat":[round(clip(.15+shock_multiplier*(x-.15),.105,.195),8)
                for x in heat],
    }


def worst_case_fixed_award(*,award_mwh,capacity_mwh,backup_capacity_mwth,
                           gas_lower,gas_upper):
    """Exact interval bounding for a known all-ON fixed-award schedule.

    For every independent quarter-hour gas arrival in [low, high],
    s_k lies between s0+k*dt*(low-u) and s0+k*dt*(high-u).
    Thermal demand support [0.105,0.195] is also quantified by
    the default static output/backup/dump bounds, not site calibrated.
    No adaptive decisions are assumed.
    """
    require(0<=gas_lower<=gas_upper<=3.,"Bad hypothetical interval bounds")
    use=award_mwh/(ETA_E*DT)
    lower_at_end=STOCK_INITIAL+SLOTS*DT*(gas_lower-use)
    upper_at_end=STOCK_INITIAL+SLOTS*DT*(gas_upper-use)
    minimum= min(STOCK_INITIAL,lower_at_end)
    maximum= max(STOCK_INITIAL,upper_at_end)
    rating=.5-TOL<=use<=2.+TOL
    initial_ramp=abs(ETA_E*use-POWER_INITIAL)<=RAMP*DT/2+TOL
    lower_heat=max(0.,BOUNDS_HEAT_MWTH[1]-backup_capacity_mwth,
                   ETA_H*use-DUMP_CAP)
    high_heat=min(BOUNDS_HEAT_MWTH[1],ETA_H*use)
    # Check both heat demand extremes, not just the high one:
    thermal_all=True
    for h in BOUNDS_HEAT_MWTH:
        lower=max(0.,h-backup_capacity_mwth,ETA_H*use-DUMP_CAP)
        upper=min(h,ETA_H*use)
        thermal_all=thermal_all and lower<=upper+TOL
    certified=(rating and initial_ramp and thermal_all
               and minimum>=-TOL and maximum<=capacity_mwh+TOL)
    # Aggregate source gas can vary continuously on a nondegenerate
    # interval. A fixed-burn, zero-vent plant cannot guarantee exact
    # terminal inventory for ALL these gas paths unless low=high=use.
    cyclic_all=certified and abs(gas_upper-gas_lower)<=TOL and (
        abs(gas_lower-use)<=TOL)
    return {
        "all_independent_bounded_gas_paths_feasible":
            bool(certified),
        "all_bounded_paths_terminal_stock_matched":
            bool(cyclic_all),
        "worst_lower_stock_mwh_lhv":round(minimum,10),
        "worst_upper_stock_mwh_lhv":round(maximum,10),
        "lower_gas_terminal_stock_mwh_lhv":round(lower_at_end,10),
        "upper_gas_terminal_stock_mwh_lhv":round(upper_at_end,10),
        "generator_rating_ok":bool(rating),
        "initial_half_interval_ramp_ok":bool(initial_ramp),
        "all_supported_heat_demands_serviceable":bool(thermal_all),
        "all_future_gas_arrival_paths_within_assumed_bounds_only":True,
    }


def source_pair_correlation(days):
    x=[float(d["price_baseline_error_eur_mwh"][h])
       for d in days for h in range(SOURCE_HOUR_START,SOURCE_HOUR_START+TARGET_HOURS)]
    y=[float(d["regional_load_error_relative"][h])
       for d in days for h in range(SOURCE_HOUR_START,SOURCE_HOUR_START+TARGET_HOURS)]
    require(len(x)>=2 and len(x)==len(y),"Insufficient paired source samples")
    mx=math.fsum(x)/len(x)
    my=math.fsum(y)/len(y)
    numerator=math.fsum((a-mx)*(b-my) for a,b in zip(x,y))
    sx=math.sqrt(math.fsum((a-mx)**2 for a in x))
    sy=math.sqrt(math.fsum((b-my)**2 for b in y))
    return round(numerator/(sx*sy),10) if sx>0 and sy>0 else None


def source_training_7day_blocks(train):
    """Every block is seven calendar-consecutive, complete SOURCE days."""
    starts=[]
    for i in range(len(train)-BOOT_DAYS+1):
        if all(date.fromisoformat(train[i+k]["date_utc"]) ==
               date.fromisoformat(train[i]["date_utc"])+timedelta(days=k)
               for k in range(BOOT_DAYS)):
            starts.append(i)
    require(starts,"No calendar-contiguous seven-source-day training block")
    return starts


def bootstrap_training_day_feasibility(bools,starts,cell_key):
    """DESCRIPTIVE 7-day block bootstrap of TRAIN outcomes only.

    Fixed seed + cell SHA locks sample order. Samples whole consecutive
    source days preserving serial and cross-channel errors. The returned
    quantiles are not calibrated confidence intervals for site performance.
    """
    seed=int(sha256((str(BOOT_SEED)+"|"+cell_key).encode("utf8")).hexdigest()[:16],16)
    rng=random.Random(seed)
    estimates=[]
    number_blocks=(BOOT_TARGET_DAYS+BOOT_DAYS-1)//BOOT_DAYS
    for _ in range(BOOT_SAMPLES):
        indices=[]
        for _ in range(number_blocks):
            pos=starts[rng.randrange(len(starts))]
            indices.extend(range(pos,pos+BOOT_DAYS))
        subset=indices[:BOOT_TARGET_DAYS]
        estimates.append(math.fsum(float(bools[i]) for i in subset)/len(subset))
    sorted_est=sorted(estimates)
    return {
        "training_descriptive_7day_block_bootstrap_p05":
            round(sorted_est[int(.05*(BOOT_SAMPLES-1))],8),
        "training_descriptive_7day_block_bootstrap_p95":
            round(sorted_est[int(.95*(BOOT_SAMPLES-1))],8),
        "training_bootstrap_replicates":BOOT_SAMPLES,
        "training_source_days_per_resample":BOOT_TARGET_DAYS,
        "confidence_interval_or_field_probability_claim":False,
    }


def _baseline_checks(source,baseline):
    require(baseline["protocol"]==a24.PROTOCOL,
            "Must compare against frozen v0.9.24 hypothetical-award study")
    require(baseline["source_sha256"]==j.SOURCE_SHA256,
            "Baseline data publisher SHA disagreement")
    require(baseline["days_evaluated"]==92 and
            baseline["study_is_subset_smoke"] is False,
            "A4 needs the complete, not cherry-picked, v0.9.24 holdout")
    declared=a24.predeclare_award_profiles()
    require(baseline["award_profiles_predeclared"]==declared,
            "v0.9.24 pre-reveal award hashes/profiles modified")
    by_date={d["date_utc"]:d for d in source["complete_days"]}
    test=[d for d in source["complete_days"] if
          d["partition"]=="HOLDOUT_FROM_2019_10_01"]
    eligible=[day for day in test if
              c22._historical_baseline(day,by_date) is not None]
    require(len(eligible)==92 and
            [x["day_utc"] for x in baseline["cases"]]==
            [x["date_utc"] for x in eligible],
            "v0.9.24 date eligibility or order inconsistent")
    for case in baseline["cases"]:
        for profile in declared:
            actual=case["award_profiles"][profile]
            require(actual["pre_reveal_award_sha256"]==
                    declared[profile]["pre_reveal_award_sha256"],
                    "Actual case award hash differs from preregistration")
    return eligible


def run(source,baseline):
    train,holdout=j._source_validate(source)
    eligible=_baseline_checks(source,baseline)
    scales=j._standardizers(source)
    declared=a24.predeclare_award_profiles()
    starts=source_training_7day_blocks(train)
    all_on_days=0
    baseline_model_feasible_but_expost_impossible=0
    for c,day in zip(baseline["cases"],eligible):
        first=c["award_profiles"]["nominal_gas_0p100"]["strategies"]["nominal"]
        on=first["first_stage_on"]
        all_on_days+=on==list(FIXED_ALL_ON)
        sc=paired_synthetic_six_hour_path(day,scales,1.)
        for identifier in declared:
            val=declared[identifier]["quarter_hour_export_mwh"][0]
            b=c["award_profiles"][identifier]["strategies"]["nominal"]
            outcome=physical_fixed_award(sc["gas"],sc["heat"],
                         award_mwh=val,capacity_mwh=1.5,
                         backup_capacity_mwth=.2,
                         states=b["first_stage_on"])
            if (b["replays"]["award_only"]["feasible"] and
                not outcome["physically_feasible_expost"]):
                baseline_model_feasible_but_expost_impossible+=1
    require(baseline_model_feasible_but_expost_impossible==0,
            "Accepted original physical service contradicts exact ex-post conservation")

    source_train={
        alpha:[paired_synthetic_six_hour_path(d,scales,alpha) for d in train]
        for alpha in PAIRED_SHOCK_MULTIPLIERS}
    source_test={
        alpha:[paired_synthetic_six_hour_path(d,scales,alpha) for d in eligible]
        for alpha in PAIRED_SHOCK_MULTIPLIERS}

    cells=[]
    for cap in CAPACITIES_MWH:
        for alpha in PAIRED_SHOCK_MULTIPLIERS:
            for aux in THERMAL_BACKUP_CAPACITIES_MWTH:
                for award in AWARD_MWH:
                    key=f"cap={cap:.2f}|paired_shock={alpha:.2f}|backup={aux:.2f}|award={award:.3f}"
                    training=[physical_fixed_award(path["gas"],path["heat"],
                               award_mwh=award,capacity_mwh=cap,
                               backup_capacity_mwth=aux)
                              for path in source_train[alpha]]
                    tests=[physical_fixed_award(path["gas"],path["heat"],
                             award_mwh=award,capacity_mwh=cap,
                             backup_capacity_mwth=aux)
                           for path in source_test[alpha]]
                    ok_training=[r["physically_feasible_expost"] for r in training]
                    ok_test=[r["physically_feasible_expost"] for r in tests]
                    reasons=sorted(set(reason for r in tests for reason in
                                       r["constraint_families_violated"]))
                    cells.append({
                        "cell_id":key,
                        "storage_capacity_mwh_lhv":cap,
                        "paired_synthetic_gas_and_heat_shock_multiplier":alpha,
                        "heat_backup_capacity_mwth":aux,
                        "hypothetical_award_mwh_per_15min":award,
                        "training_days":len(training),
                        "holdout_days":len(tests),
                        "training_physically_feasible_days":sum(ok_training),
                        "holdout_expost_physically_feasible_days":sum(ok_test),
                        "holdout_cyclic_inventory_matched_and_feasible_days":
                            sum(r["physically_feasible_expost"] and
                                r["terminal_stock_matched"] for r in tests),
                        "holdout_first_failure_constraint_families_day_counts":{
                            reason:sum(reason in r["constraint_families_violated"]
                                       for r in tests) for reason in reasons},
                        "holdout_terminal_stock_delta_min_mwh_lhv":
                            min(r["terminal_stock_delta_mwh_lhv"] for r in tests),
                        "holdout_terminal_stock_delta_max_mwh_lhv":
                            max(r["terminal_stock_delta_mwh_lhv"] for r in tests),
                        **bootstrap_training_day_feasibility(
                            ok_training,starts,key),
                    })
    bounds=[]
    for cap in CAPACITIES_MWH:
        for aux in THERMAL_BACKUP_CAPACITIES_MWTH:
            for award in AWARD_MWH:
                for label,(lo,hi) in BOUND_BANDS.items():
                    result=worst_case_fixed_award(
                        award_mwh=award,capacity_mwh=cap,
                        backup_capacity_mwth=aux,
                        gas_lower=lo,gas_upper=hi)
                    # Narrow gas bands are *assumptions* for a
                    # sensitivity certificate, not empirically verified
                    # prediction bands. Report their ex-post coverage.
                    coverage=sum(all(lo-TOL<=g<=hi+TOL for g in p["gas"])
                                 for p in source_test[1.])
                    bounds.append({
                        "storage_capacity_mwh_lhv":cap,
                        "heat_backup_capacity_mwth":aux,
                        "hypothetical_award_mwh_per_15min":award,
                        "declared_gas_interval_band":label,
                        "hypothetical_gas_lower_mw_lhv":lo,
                        "hypothetical_gas_upper_mw_lhv":hi,
                        "historical_source_paired_unmodified_holdout_days_with_all_synthetic_gas_hours_in_band":coverage,
                        "source_heldout_days":len(eligible),
                        **result,
                    })
    return {
        "protocol":PROTOCOL,
        "status":"PREREGISTERED_SYNTHETIC_PARAMETER_STRESS_AND_ANALYTIC_BOUND_NOT_SITE_VALIDATED",
        "source_sha256":j.SOURCE_SHA256,
        "baseline_v0924_full_92days_required":True,
        "preregistration_grid":{
            "storage_capacity_mwh_lhv":list(CAPACITIES_MWH),
            "paired_gas_heat_shock_multipliers":list(PAIRED_SHOCK_MULTIPLIERS),
            "backup_capacity_mw_th":list(THERMAL_BACKUP_CAPACITIES_MWTH),
            "hypothetical_awards_mwh_per_15min":list(AWARD_MWH),
            "uniform_hypothetical_gas_bands_mw_lhv":{
                k:list(v) for k,v in BOUND_BANDS.items()},
        },
        "frozen_chp_schedule_for_sensitivity":"ALL_ON_24_SLOTS_EQUIPMENT_INITIAL_ON",
        "same_as_v0924_original_nominal_first_stage_days":all_on_days,
        "full_heldout_eligible_days":len(eligible),
        "complete_source_training_days":len(train),
        "source_training_contiguous_7day_bootstrap_start_blocks":len(starts),
        "training_source_price_load_forecast_error_pearson":
            source_pair_correlation(train),
        "heldout_source_price_load_forecast_error_pearson_DESCRIPTIVE_ONLY":
            source_pair_correlation(eligible),
        "holdout_data_used_to_choose_grid_or_awards":False,
        "historical_source_errors_joint_by_original_day_and_hour":True,
        "gas_and_heat_couplings_empirically_calibrated":False,
        "true_site_gas_heat_measurements_present":False,
        "original_bid_time_price_forecast_vintages_verified":False,
        "market_contract_awards_real":False,
        "expost_physical_feasibility_not_a_causal_dispatch_policy":True,
        "robust_interval_bounds_are_assumptions_not_probabilistic_forecasts":True,
        "full_support_fixed_award_robustness_is_not_real_engine_certification":True,
        "no_gas_vent_grid_import_fuel_purchases_or_imbalance_market_slack":True,
        "v0924_reported_deliveries_contradict_original_expost_physics_count":
            baseline_model_feasible_but_expost_impossible,
        "simulation_parameter_grid":cells,
        "analytical_full_interval_bound_certificates":bounds,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--baseline",type=Path,required=True,
                   help="Unmodified full 92-day v0.9.24 study JSON")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    source=json.loads(args.source.read_text(encoding="utf8"))
    baseline=json.loads(args.baseline.read_text(encoding="utf8"))
    result=run(source,baseline)
    j.write_out(result,args.output)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("simulation_parameter_grid",
                                   "analytical_full_interval_bound_certificates")},
                     indent=2,allow_nan=False))
    for row in result["simulation_parameter_grid"]:
        if row["paired_synthetic_gas_and_heat_shock_multiplier"]==1. and (
            row["heat_backup_capacity_mwth"]==.2):
            print("PREREGISTERED_BASE_SHOCK_GRID_ROW",json.dumps(row,sort_keys=True))
    print("PREDECLARED_GRID_CELLS",len(result["simulation_parameter_grid"]))
    print("EXACT_INTERVAL_BOUND_CERTIFICATES",len(result["analytical_full_interval_bound_certificates"]))


if __name__=="__main__":
    main()
