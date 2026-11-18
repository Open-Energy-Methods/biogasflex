"""A6: pre-delivery fixed-award acceptance, explicit terminal services.

No optimization of the bid price or quantity. Positive rigid awards fix
fuel use and ON status in the constant-efficiency model. The gate is a
necessary and sufficient interval-box certificate for the declared static
CHP model with a known all-ON commitment, not a real-world market offer.
"""
from __future__ import annotations

import argparse
from datetime import date,timedelta
from hashlib import sha256
import json
import math
from pathlib import Path

from . import joint_v0921 as j
from . import sensitivity_v0925 as s
from . import award_v0924 as a

PROTOCOL="BIOGASFLEX_V0927_PRE_REVEAL_AWARD_GATE_MATCHED_SERVICE_V1"
SOURCE_SHA=j.SOURCE_SHA256
DT=.25
N=24
ETA_E=.4
ETA_H=.2
INITIAL=.75
INITIAL_POWER=.4
CAPACITIES=(1.5,3.)
HEAT_BACKUP=.2
DUMP=.4
RAMP=.8
# Strict arithmetic tolerance, not a physical or measurement allowance.
EPS=1e-9
CYCLIC_TOL=5e-5
METHODS={
    "nominal":{"gas":[1.,1.],"heat":[.15,.15]},
    "bounded":{"gas":[.78,1.22],"heat":[.105,.195]},
}
SERVICES=("cyclic","carryover")


def require(ok,message):
    if not ok:
        raise ValueError("v0.9.27 contract gate: "+message)


def digest(obj):
    return sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),
                             allow_nan=False).encode("utf8")).hexdigest()


def finite_number(v):
    return type(v) in (int,float) and math.isfinite(v)


def acceptance(awards,*,capacity,gas_lower,gas_upper,heat_lower,heat_upper,
               service):
    """Exact all-path feasibility for independent uniform gas/heat support.

    Arbitrary 24-slot known award profiles; no future source observations.
    Positive awards use the explicitly all-ON commitment. A zero award is
    rejected (outside this model's ON minimum). No startup claim.
    Terminal cyclic equality is tested against BOTH extreme totals.
    Carryover is a different contract: terminal stock in [0,C], no valuation.
    """
    require(len(awards)==N and all(finite_number(v) and v>=0 for v in awards),
            "Expected 24 finite nonnegative awarded MWh")
    require(finite_number(capacity) and INITIAL<=capacity<=20,
            "Invalid storage capacity")
    require(all(finite_number(x) for x in [gas_lower,gas_upper,heat_lower,heat_upper])
            and 0<=gas_lower<=gas_upper<=3 and 0<=heat_lower<=heat_upper<=1,
            "Invalid physical uncertainty support")
    require(service in SERVICES,"Unknown terminal service")
    violations=set()
    use=[v/(ETA_E*DT) for v in awards]
    low=high=INITIAL
    lows=[low]; highs=[high]
    prev_power=INITIAL_POWER
    for t,u in enumerate(use):
        p=ETA_E*u
        if not .2-EPS<=p<=.8+EPS:
            violations.add("all_on_electric_rating")
        if abs(p-prev_power)>RAMP*(DT/2 if t==0 else DT)+EPS:
            violations.add("consecutive_on_ramp")
        for h in (heat_lower,heat_upper):
            if max(0.,h-HEAT_BACKUP,ETA_H*u-DUMP)>min(h,ETA_H*u)+EPS:
                violations.add("bounded_heat_service")
        low+=DT*(gas_lower-u)
        high+=DT*(gas_upper-u)
        lows.append(low); highs.append(high)
        if low < -EPS:violations.add("lower_storage_bound")
        if high > capacity+EPS:violations.add("upper_storage_bound")
        prev_power=p
    if service=="cyclic" and (
        abs(low-INITIAL)>CYCLIC_TOL+EPS or abs(high-INITIAL)>CYCLIC_TOL+EPS):
        violations.add("universal_cyclic_terminal_inventory")
    result={
        "award_mwh_per_quarter":list(awards),
        "capacity_mwh_lhv":capacity,
        "gas_mw_lhv_bounds":[gas_lower,gas_upper],
        "heat_mwth_bounds":[heat_lower,heat_upper],
        "terminal_service":service,
        "terminal_tolerance_mwh_lhv":CYCLIC_TOL if service=="cyclic" else None,
        "accepted":not violations,
        "rejection_reasons":sorted(violations),
        "lower_stock_path_mwh_lhv":[round(x,10) for x in lows],
        "upper_stock_path_mwh_lhv":[round(x,10) for x in highs],
        "total_fixed_fuel_burn_mwh_lhv":round(math.fsum(use)*DT,10),
        "total_award_mwh_e":round(math.fsum(awards),10),
        "terminal_lower_mwh_lhv":round(low,10),
        "terminal_upper_mwh_lhv":round(high,10),
        "initial_stock_mwh_lhv":INITIAL,
        "all_on":True,
    }
    return {**result,"pre_delivery_certificate_sha256":digest(result)}


def predeclare():
    gates=[]
    for capacity in CAPACITIES:
        for label,value in a.AWARD_PROFILES_MWH_PER_QUARTER.items():
            for service in SERVICES:
                for method,domain in METHODS.items():
                    cert=acceptance([value]*N,capacity=capacity,
                        gas_lower=domain["gas"][0],gas_upper=domain["gas"][1],
                        heat_lower=domain["heat"][0],heat_upper=domain["heat"][1],
                        service=service)
                    gates.append({"cell_id":f"{capacity:.2f}|{label}|{service}|{method}",
                                  "profile":label,"method":method,"certificate":cert})
    return gates


def execute(cert,gas_hours,heat_hours,prices):
    """Only executed current-hour conditions determine the next output.

    A refused contract is not a shutdown instruction: no plant trajectory
    is simulated for that policy after rejection. For an accepted contract
    stop at first infeasible 15-minute step; no fictitious later revenue.
    The greedy useful heat split minimizes the inherited positive backup
    and dump proxy costs for each fixed burn; no price enters control.
    """
    if not cert["accepted"]:
        return {"status":"rejected_pre_delivery","completed_rows":[],
                "economic_contribution_eur":None,"terminal_stock_mwh_lhv":None,
                "cyclic_stock_matched":None,"full_contract_energy_delivered":False,
                "terminal_service_fulfilled":False,"failed_quarter":None,
                "failure_reasons":[]}
    require(len(gas_hours)==len(heat_hours)==len(prices)==6,
            "Expected six source-hour inputs")
    rows=[]
    stock=INITIAL
    previous_power=INITIAL_POWER
    capacity=cert["capacity_mwh_lhv"]
    for t,award in enumerate(cert["award_mwh_per_quarter"]):
        hour=t//4
        g=gas_hours[hour];h=heat_hours[hour]
        require(all(finite_number(v) for v in (g,h,prices[hour]))
                and g>=0 and h>=0,"Invalid current source hour")
        fuel=award/(ETA_E*DT)
        power=ETA_E*fuel
        end=stock+DT*(g-fuel)
        useful=min(h,ETA_H*fuel)
        backup=h-useful
        dump=ETA_H*fuel-useful
        reasons=[]
        if not .2-EPS<=power<=.8+EPS:reasons.append("all_on_electric_rating")
        if abs(power-previous_power)>RAMP*(DT/2 if t==0 else DT)+EPS:
            reasons.append("consecutive_on_ramp")
        if end<-EPS:reasons.append("lower_storage_bound")
        if end>capacity+EPS:reasons.append("upper_storage_bound")
        if backup>HEAT_BACKUP+EPS or dump>DUMP+EPS:
            reasons.append("bounded_heat_service")
        if reasons:
            return {"status":"failed_during_delivery","completed_rows":rows,
                    "economic_contribution_eur":None,
                    "terminal_stock_mwh_lhv":None,"cyclic_stock_matched":None,
                    "full_contract_energy_delivered":False,
                    "terminal_service_fulfilled":False,"failed_quarter":t,
                    "failure_reasons":sorted(reasons)}
        rows.append({"quarter":t,"gas_mw_lhv":g,"heat_mwth":h,
                     "fuel_mw_lhv":fuel,"electric_mwh":award,
                     "useful_mwth":useful,"backup_mwth":backup,"dump_mwth":dump,
                     "stock_end_mwh_lhv":end,
                     "realized_price_expost_only_eur_mwh":prices[hour]})
        stock=end;previous_power=power
    matched=abs(stock-INITIAL)<=CYCLIC_TOL+EPS
    fulfilled=cert["terminal_service"]=="carryover" or matched
    # Ex-post modeled proxy contribution only, and not a terminal valuation.
    cash=math.fsum(r["electric_mwh"]*(r["realized_price_expost_only_eur_mwh"]-.75)
                    -DT*(6*r["backup_mwth"]+r["dump_mwth"]) for r in rows)
    return {"status":"fulfilled" if fulfilled else "terminal_service_failed",
            "completed_rows":rows,"economic_contribution_eur":cash if fulfilled else None,
            "terminal_stock_mwh_lhv":stock,"cyclic_stock_matched":matched,
            "full_contract_energy_delivered":True,
            "terminal_service_fulfilled":fulfilled,"failed_quarter":None,
            "failure_reasons":[] if fulfilled else ["cyclic_terminal_inventory"]}


def run(source):
    # Lock every certificate before source outcomes are reconstructed.
    gates=predeclare()
    lock=digest(gates)
    train,test=j._source_validate(source)
    scales=j._standardizers(source)
    dates={d["date_utc"] for d in source["complete_days"]}
    eligible=[d for d in test if (date.fromisoformat(d["date_utc"])-
                 timedelta(days=7)).isoformat() in dates]
    require(len(eligible)==92,"Full frozen 92-day holdout required")
    cases=[]
    for d in eligible:
        p=s.paired_synthetic_six_hour_path(d,scales,1.)
        prices=d["delivery_price_eur_mwh"][8:14]
        cases.append({"day_utc":d["date_utc"],"gate_lock_sha256":lock,
                      "outcomes":{cell["cell_id"]:execute(cell["certificate"],
                          p["gas"],p["heat"],prices) for cell in gates}})
    summary=[]
    for cell in gates:
        outcomes=[d["outcomes"][cell["cell_id"]] for d in cases]
        count=lambda status:sum(x["status"]==status for x in outcomes)
        summary.append({"cell_id":cell["cell_id"],"eligible_days":len(cases),
            "accepted_pre_delivery":cell["certificate"]["accepted"],
            "rejected_days":count("rejected_pre_delivery"),
            "failed_during_delivery_days":count("failed_during_delivery"),
            "terminal_service_failed_days":count("terminal_service_failed"),
            "fulfilled_days":count("fulfilled"),
            "full_energy_delivered_days":sum(x["full_contract_energy_delivered"] for x in outcomes),
            "physically_complete_cyclic_days":sum(x["cyclic_stock_matched"] is True for x in outcomes)})
    comparisons=[]
    for capacity in CAPACITIES:
        for label in a.AWARD_PROFILES_MWH_PER_QUARTER:
            for service in SERVICES:
                prefix=f"{capacity:.2f}|{label}|{service}|"
                strict=[];carry=[];not_comparable=0
                for day in cases:
                    n=day["outcomes"][prefix+"nominal"]
                    b=day["outcomes"][prefix+"bounded"]
                    if n["terminal_service_fulfilled"] and b["terminal_service_fulfilled"]:
                        require(abs(n["terminal_stock_mwh_lhv"]-b["terminal_stock_mwh_lhv"])<=EPS,
                                "Matched award must imply equal end stock")
                        require(n["completed_rows"]==b["completed_rows"],
                                "Same fixed award and heat control must imply identical physical service")
                        diff=b["economic_contribution_eur"]-n["economic_contribution_eur"]
                        if n["cyclic_stock_matched"] and b["cyclic_stock_matched"]:
                            strict.append(diff)
                        elif service=="carryover":
                            carry.append(diff)
                        else:not_comparable+=1
                    else:not_comparable+=1
                comparisons.append({"capacity_mwh_lhv":capacity,"profile":label,
                    "terminal_service":service,"eligible_days":len(cases),
                    "strict_cyclic_matched_pairs":len(strict),
                    "strict_cyclic_mean_difference_eur":math.fsum(strict)/len(strict) if strict else None,
                    "separate_equal_carryover_pairs":len(carry),
                    "carryover_mean_operating_difference_eur":math.fsum(carry)/len(carry) if carry else None,
                    "not_comparable_days":not_comparable})
    return {"protocol":PROTOCOL,"source_sha256":SOURCE_SHA,
        "gate_lock_sha256":lock,"predeclared_gates":gates,
        "eligible_days":len(cases),"training_days":len(train),
        "source_gas_and_heat_uncalibrated":True,"actual_market_awards":False,
        "optimized_bidding":False,"rejected_contract_plant_operation_not_modeled":True,
        "future_realized_inputs_not_used_for_acceptance":True,
        "no_terminal_inventory_monetization":True,
        "summary":summary,"matched_service_comparisons":comparisons,"cases":cases}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=run(json.loads(args.source.read_text(encoding="utf8")))
    j.write_out(result,args.output)
    print(json.dumps({k:v for k,v in result.items() if k not in ("cases","predeclared_gates")},
                     indent=2,allow_nan=False))
if __name__=="__main__":
    main()
