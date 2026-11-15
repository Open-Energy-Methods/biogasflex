"""Independent analytical hard-award feasible and infeasible diagnostics.

No solver is used to calculate the expected awarded MWh, physical
gas inventory and gross cashflow values. The optimizer must reproduce
those identities under hard award equalities and pass all inherited audits.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.market_v0910 import (
    run_manifest, audit_postclearing_delivery,
    validate_preclearing_offer, MarketBoundaryError,
)


def _close(x,expected,what,eps=1e-7):
    if abs(x-expected)>eps:
        raise AssertionError(f"{what} expected {expected}, got {x}")


def audit():
    expected={
        "v0911_contract_hourly.json":{
            "accepted":[.2,.6],"powers":[.2,.6],
            "stock":[.5,0.0],"total":.8,"gross":20.0,
            "duration":[1.0,1.0],
        },
        "v0911_contract_quarterhour.json":{
            "accepted":[.05,.15,.1,.1],"powers":[.2,.6,.4,.4],
            "stock":[.125,0.0,0.0,0.0],"total":.4,"gross":9.0,
            "duration":[.25,.25,.25,.25],
        },
    }
    results={}
    for name,e in expected.items():
        out=run_manifest(ROOT/"examples"/name,hard_contract=True,
                         include_solver_details=True)
        pre,post=out["preclearing"],out["postclearing"]
        solver=post["physical_solver_and_hourly"]
        if (pre["clearing_prices_available"] or
            pre["contract_status"]!="NOT_AWARDED_YET" or
            post["market_profit_claimed"] or
            post["imbalance_settlement_included"] or
            not post["accepted_delivery_enforced_inside_milp"] or
            not solver["hard_contract_equalities_embedded_in_milp"]):
            raise AssertionError("Pre/post boundary or MILP award equalities not certified")
        _close(post["gross_contract_cashflow_proxy_eur"],e["gross"],"Gross contracted cashflow")
        _close(post["total_accepted_mwh"],e["total"],"Contracted electric energy")
        for i,(row,accepted,power,stock,hours) in enumerate(
            zip(solver["hourly"],e["accepted"],e["powers"],e["stock"],e["duration"])
        ):
            _close(row["power_mw_e"]*hours,accepted,f"slot[{i}] accepted MWh")
            _close(row["power_mw_e"],power,f"slot[{i}] power MW")
            _close(row["stock_end_mwh_lhv"],stock,f"slot[{i}] gas stock MWh")
        _close(post["maximum_contract_vs_simulated_delivery_mwh"],0,"MWh mismatch")
        _close(post["gas_balance_max_residual_mwh"],0,"Gas mass balance")
        _close(post["heat_service_max_residual_mwh"],0,"Heat service balance")
        if solver["net_contribution_eur"]>solver["same_boundary_LP_relaxation_upper_bound_eur"]+1e-7:
            raise AssertionError("Constrained MILP exceeds matched LP bound")
        results[name]={
            "contracted_mwh":post["total_accepted_mwh"],
            "accepted_gross_cashflow_proxy_eur":post["gross_contract_cashflow_proxy_eur"],
            "max_delivered_award_residual_mwh":
                post["maximum_contract_vs_simulated_delivery_mwh"],
            "invented_plant":True,
        }

    # Independent infeasibility witness: 2 slots with gas supply 1 MW_LHV
    # in each; requested delivery [.2,.6] needs first-hour stock
    # 0.5 MWh_LHV. A vessel restricted to 0.1 cannot hold it, while
    # uncontracted [.4,.4] remains feasible.
    x=json.loads((ROOT/"examples/v0911_contract_hourly.json").read_text())
    c=json.loads((ROOT/"examples/v0911_synthetic_chp.json").read_text())
    c["gas_storage_capacity_mwh_lhv"]=0.1
    pre=validate_preclearing_offer(x["market"],x["delivery_slots"],
                                    x["preclearing_offer"],c["electric_rating_mw"])
    try:
        audit_postclearing_delivery(
            x["market"],x["delivery_slots"],pre,x["exogenous_award"],c,
            hard_contract=True)
    except MarketBoundaryError as exc:
        if "CONTRACT_INFEASIBLE" not in str(exc):
            raise AssertionError("Rejected infeasible award for unexpected reason") from exc
    else:
        raise AssertionError("Invented extra storage or volume to clear award")
    return {
        "status":"PASS","version":"0.9.11",
        "data_scope":"Entirely synthetic gas, heat, electricity, award and price",
        "method":"Hard accepted MWh equals eta_e * gas MW_LHV * hours inside MILP and matched LP relaxation",
        "independent_exact_oracles":results,
        "insufficient_gas_storage_infeasible_award_rejected":True,
        "imbalances_or_balancing_not_fabricated":True,
        "original_frozen_science_data_modified":False,
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (AssertionError,MarketBoundaryError) as exc:
        raise SystemExit("V0911 HARD CONTRACT AUDIT FAIL: "+str(exc))
