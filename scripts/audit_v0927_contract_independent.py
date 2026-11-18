"""Independent rational-arithmetic acceptance and matched-service audit.

No BiogasFlex imports, no optimizer. Enumerates every gate and every
historical outcome, verifies original source projection via independent
v0.9.22 code and independently checks each stock/heat/award/cash row.
"""
from __future__ import annotations
import argparse
from datetime import date,timedelta
from fractions import Fraction as F
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PROTOCOL="BIOGASFLEX_V0927_PRE_REVEAL_AWARD_GATE_MATCHED_SERVICE_V1"
SOURCE_SHA="6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"
PROFILES={"floor_budget_0p090":.09,"nominal_gas_0p100":.1,"initial_ramp_stress_0p150":.15}
DOMAINS={"nominal":([1.,1.],[.15,.15]),"bounded":([.78,1.22],[.105,.195])}
SERVICES=("cyclic","carryover")
EPS=F("0.000000001")
TOL=F("0.00005")
S0=F("0.75")
DT=F("0.25")
EE=F("0.4")
EH=F("0.2")

def check(ok,msg):
    if not ok:raise AssertionError("INDEPENDENT_V0927: "+msg)

def frac(x):
    check(type(x) in (int,float) and math.isfinite(x),"Invalid numeric scalar")
    return F(str(x))

def near(a,b,msg,tol=1e-8):
    check(a is not None and abs(float(a)-float(b))<=tol,msg)

def hash_json(v):
    return sha256(json.dumps(v,sort_keys=True,separators=(",",":"),
                             allow_nan=False).encode("utf8")).hexdigest()

def independent_certificate(awards,cap,gases,heats,service):
    """Cumulative interval support directly from partial energy sums."""
    a=[frac(x) for x in awards]; cap=frac(cap)
    gl,gu=map(frac,gases); hl,hu=map(frac,heats)
    lp=[]; hp=[]; reasons=set()
    for k in range(25):
        burned=sum(a[:k])/EE
        lp.append(S0+k*DT*gl-burned)
        hp.append(S0+k*DT*gu-burned)
    if min(lp)<-EPS:reasons.add("lower_storage_bound")
    if max(hp)>cap+EPS:reasons.add("upper_storage_bound")
    if service=="cyclic" and max(abs(lp[-1]-S0),abs(hp[-1]-S0))>TOL+EPS:
        reasons.add("universal_cyclic_terminal_inventory")
    prev=F(".4")
    for k,e in enumerate(a):
        p=e/DT; recovery=p*EH/EE
        if p<F(".2")-EPS or p>F(".8")+EPS:reasons.add("all_on_electric_rating")
        if abs(p-prev)>F(".8")*DT/(2 if k==0 else 1)+EPS:
            reasons.add("consecutive_on_ramp")
        # Monotone deficit and surplus sufficient at opposite heat extremes.
        if hu-recovery>F(".2")+EPS or recovery-hl>F(".4")+EPS:
            reasons.add("bounded_heat_service")
        prev=p
    return sorted(reasons),lp,hp

def source_module():
    spec=importlib.util.spec_from_file_location("source_projection_independent",ROOT/"scripts/audit_v0925_envelope_independent.py")
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m

def audit_gate(cell,cap,profile,val,service,method):
    gid=f"{cap:.2f}|{profile}|{service}|{method}"
    check(cell["cell_id"]==gid and cell["profile"]==profile and cell["method"]==method,"Gate identity changed")
    c=cell["certificate"]
    check(c["award_mwh_per_quarter"]==[val]*24 and c["capacity_mwh_lhv"]==cap and c["all_on"] is True,"Changed hardware or award")
    gases,heats=DOMAINS[method]
    check(c["gas_mw_lhv_bounds"]==gases and c["heat_mwth_bounds"]==heats and c["terminal_service"]==service,"Changed assumptions")
    check(c["terminal_tolerance_mwh_lhv"]==(.00005 if service=="cyclic" else None),"Terminal tolerance")
    check(c["initial_stock_mwh_lhv"]==.75,"Initial inventory changed")
    reasons,low,high=independent_certificate([val]*24,cap,gases,heats,service)
    check(c["rejection_reasons"]==reasons and c["accepted"]==(not reasons),"Incorrect acceptance or rejection")
    for actual,expected in [(c["lower_stock_path_mwh_lhv"],low),(c["upper_stock_path_mwh_lhv"],high)]:
        check(len(actual)==25,"Missing prefix stock certificate")
        for x,y in zip(actual,expected):near(x,y,"Incorrect cumulative gas envelope")
    near(c["terminal_lower_mwh_lhv"],low[-1],"Lower terminal")
    near(c["terminal_upper_mwh_lhv"],high[-1],"Upper terminal")
    near(c["total_fixed_fuel_burn_mwh_lhv"],24*frac(val)/EE,"Fuel obligation")
    near(c["total_award_mwh_e"],24*frac(val),"Electric obligation")
    check(c["pre_delivery_certificate_sha256"]==hash_json({k:v for k,v in c.items() if k!="pre_delivery_certificate_sha256"}),"Certificate digest")
    return c,not reasons

def audit_day(out,c,accepted,gas,heat,prices):
    rows=out["completed_rows"]
    if not accepted:
        check(out["status"]=="rejected_pre_delivery" and not rows and out["economic_contribution_eur"] is None
              and out["terminal_stock_mwh_lhv"] is None and out["cyclic_stock_matched"] is None
              and out["full_contract_energy_delivered"] is False and out["terminal_service_fulfilled"] is False
              and out["failed_quarter"] is None and out["failure_reasons"]==[],
              "Rejected contract fictitiously executed")
        return
    stock=S0; prev=F(".4"); cash=F(0)
    cap=frac(c["capacity_mwh_lhv"])
    for t,award in enumerate(c["award_mwh_per_quarter"]):
        a=frac(award); power=a/DT; u=power/EE
        g=frac(gas[t//4]);h=frac(heat[t//4]);price=frac(prices[t//4])
        nextstock=stock+DT*(g-u)
        recovered=EH*u; useful=min(h,recovered)
        backup=h-useful; dump=recovered-useful
        reasons=[]
        if not F(".2")-EPS<=power<=F(".8")+EPS:reasons.append("all_on_electric_rating")
        if abs(power-prev)>F(".8")*DT/(2 if t==0 else 1)+EPS:reasons.append("consecutive_on_ramp")
        if nextstock<-EPS:reasons.append("lower_storage_bound")
        if nextstock>cap+EPS:reasons.append("upper_storage_bound")
        if backup>F(".2")+EPS or dump>F(".4")+EPS:reasons.append("bounded_heat_service")
        if reasons:
            check(len(rows)==t and out["status"]=="failed_during_delivery" and out["failed_quarter"]==t
                  and out["failure_reasons"]==sorted(reasons) and out["economic_contribution_eur"] is None
                  and out["terminal_stock_mwh_lhv"] is None and out["cyclic_stock_matched"] is None
                  and not out["full_contract_energy_delivered"] and not out["terminal_service_fulfilled"],
                  "Infeasible prefix counted as full delivery")
            return
        check(t<len(rows),"Missing feasible executed quarter")
        r=rows[t];check(r["quarter"]==t,"Chronology mismatch")
        for key,val in {"gas_mw_lhv":g,"heat_mwth":h,"fuel_mw_lhv":u,"electric_mwh":a,
                        "useful_mwth":useful,"backup_mwth":backup,"dump_mwth":dump,"stock_end_mwh_lhv":nextstock,
                        "realized_price_expost_only_eur_mwh":price}.items():
            near(r[key],val,"Independent row "+key)
        # Greedy useful heat is the exact static minimum-cost split:
        # increasing useful by d reduces backup AND dump by d.
        cash+=a*(price-F(".75"))-DT*(6*backup+dump)
        stock=nextstock;prev=power
    matched=abs(stock-S0)<=TOL+EPS
    fulfilled=matched or c["terminal_service"]=="carryover"
    check(len(rows)==24 and out["full_contract_energy_delivered"] is True and
          out["cyclic_stock_matched"]==matched and out["terminal_service_fulfilled"]==fulfilled
          and out["failed_quarter"] is None and out["status"]==("fulfilled" if fulfilled else "terminal_service_failed")
          and out["failure_reasons"]==([] if fulfilled else ["cyclic_terminal_inventory"]),
          "Final service status disagreement")
    near(out["terminal_stock_mwh_lhv"],stock,"Final stock")
    if fulfilled:near(out["economic_contribution_eur"],cash,"Ex-post operating cash",1e-7)
    else:check(out["economic_contribution_eur"] is None,"Terminal failure monetized")

def audit(source,report):
    check(report["protocol"]==PROTOCOL and report["source_sha256"]==SOURCE_SHA==source["source"]["sha256"],"Source identity")
    check(report["source_gas_and_heat_uncalibrated"] is True and report["actual_market_awards"] is False
          and report["optimized_bidding"] is False and report["no_terminal_inventory_monetization"] is True
          and report["rejected_contract_plant_operation_not_modeled"] is True
          and report["future_realized_inputs_not_used_for_acceptance"] is True,"Unsupported claim")
    gates=report["predeclared_gates"];check(len(gates)==24,"Missing preregistered gates")
    check(hash_json(gates)==report["gate_lock_sha256"],"Gate lock changed")
    configs={}
    ix=0
    for cap in (1.5,3.):
        for profile,val in PROFILES.items():
            for service in SERVICES:
                for method in DOMAINS:
                    c,accepted=audit_gate(gates[ix],cap,profile,val,service,method)
                    configs[gates[ix]["cell_id"]]=(c,accepted)
                    ix+=1
    all_days=source["complete_days"];dates={d["date_utc"] for d in all_days}
    eligible=[d for d in all_days if d["partition"]=="HOLDOUT_FROM_2019_10_01"
              and (date.fromisoformat(d["date_utc"])-timedelta(days=7)).isoformat() in dates]
    train=[d for d in all_days if d["partition"]=="TRAIN_PRIOR_TO_2019_10_01"]
    check(len(eligible)==len(report["cases"])==report["eligible_days"]==92 and len(train)==report["training_days"]==271,"Source denominator")
    oracle=source_module()
    intervals=0; accepted_failures_bounded=0
    cases=report["cases"]
    for case,day in zip(cases,eligible):
        check(case["day_utc"]==day["date_utc"] and case["gate_lock_sha256"]==report["gate_lock_sha256"],"Chronology or lock")
        check(set(case["outcomes"])==set(configs),"Missing or extra gate case")
        g,h=oracle.change_source(source,day,1.)
        prices=day["delivery_price_eur_mwh"][8:14]
        for gid,(c,accepted) in configs.items():
            out=case["outcomes"][gid]
            audit_day(out,c,accepted,g,h,prices)
            intervals+=len(out["completed_rows"])
            if gid.endswith("|bounded") and accepted and out["status"]!="fulfilled":
                accepted_failures_bounded+=1
    check(accepted_failures_bounded==0,"Bounded accepted service failed inside support")
    summaries=report["summary"]
    check(len(summaries)==24 and [x["cell_id"] for x in summaries]==list(configs),"Summary grid")
    for row in summaries:
        gid=row["cell_id"];out=[d["outcomes"][gid] for d in cases]
        check(row["accepted_pre_delivery"]==configs[gid][1] and row["eligible_days"]==92,"Summary gate")
        for key,status in [("rejected_days","rejected_pre_delivery"),("failed_during_delivery_days","failed_during_delivery"),
                           ("terminal_service_failed_days","terminal_service_failed"),("fulfilled_days","fulfilled")]:
            check(row[key]==sum(r["status"]==status for r in out),"Summary count "+key)
        check(row["full_energy_delivered_days"]==sum(r["full_contract_energy_delivered"] for r in out)
              and row["physically_complete_cyclic_days"]==sum(r["cyclic_stock_matched"] is True for r in out),"Summary terminal count")
    comparisons=report["matched_service_comparisons"];check(len(comparisons)==12,"Comparison denominator")
    strict_total=carry_total=0; idx=0
    for cap in (1.5,3.):
        for profile in PROFILES:
            for service in SERVICES:
                row=comparisons[idx];idx+=1
                check((row["capacity_mwh_lhv"],row["profile"],row["terminal_service"],row["eligible_days"])==(cap,profile,service,92),"Comparison identity")
                pre=f"{cap:.2f}|{profile}|{service}|"
                strict=[];carry=[]
                for day in cases:
                    a=day["outcomes"][pre+"nominal"];b=day["outcomes"][pre+"bounded"]
                    if not (a["terminal_service_fulfilled"] and b["terminal_service_fulfilled"]):continue
                    check(a["completed_rows"]==b["completed_rows"],"Different service histories compared")
                    near(a["terminal_stock_mwh_lhv"],b["terminal_stock_mwh_lhv"],"Unmatched final stock")
                    diff=b["economic_contribution_eur"]-a["economic_contribution_eur"]
                    if a["cyclic_stock_matched"] and b["cyclic_stock_matched"]:strict.append(diff)
                    else:
                        check(service=="carryover","Cyclic-required comparison not cyclic")
                        carry.append(diff)
                for k,items in [("strict_cyclic_matched_pairs",strict),("separate_equal_carryover_pairs",carry)]:
                    check(row[k]==len(items),"Pair count")
                for k,items in [("strict_cyclic_mean_difference_eur",strict),("carryover_mean_operating_difference_eur",carry)]:
                    if items:near(row[k],sum(items)/len(items),"Paired mean")
                    else:check(row[k] is None,"Empty comparison monetized")
                check(row["not_comparable_days"]==92-len(strict)-len(carry),"Comparison exclusions")
                strict_total+=len(strict);carry_total+=len(carry)
    return {"status":"PASS_INDEPENDENT_V0927_FIXED_AWARD_GATE_MATCHED_SERVICE",
            "eligible_days":92,"gates_checked":24,"day_gate_outcomes_checked":92*24,
            "executed_intervals_checked":intervals,
            "bounded_accepted_gates":sum(c for gid,(_,c) in configs.items() if gid.endswith("|bounded")),
            "bounded_accepted_failures":accepted_failures_bounded,
            "strict_cyclic_matched_pairs":strict_total,"separate_equal_carryover_pairs":carry_total,
            "market_or_field_validation":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ("source","study","output"):p.add_argument("--"+k,type=Path,required=True)
    x=p.parse_args()
    result=audit(json.loads(x.source.read_text(encoding="utf8")),json.loads(x.study.read_text(encoding="utf8")))
    x.output.parent.mkdir(parents=True,exist_ok=True)
    x.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))
if __name__=="__main__":
    main()
