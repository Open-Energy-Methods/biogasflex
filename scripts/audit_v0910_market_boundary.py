"""Independent exact market-information and no-imbalance numerical oracle.

Examples are entirely fictional. No auctions, observed exports, grid settlement
or participant prices are acquired or represented as historical events.
"""
from __future__ import annotations

from pathlib import Path
import copy
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.market_v0910 import (
    run_manifest, validate_preclearing_offer,
    audit_postclearing_delivery, MarketBoundaryError,
)


def audit():
    expected={
      "v0910_market_hourly.json":(2,32.0,0.8),
      "v0910_market_quarterhour.json":(4,20.0,0.4),
    }
    checked={}
    for name,(count,cash,total) in expected.items():
        path=ROOT/"examples"/name
        outcome=run_manifest(path)
        pre=outcome["preclearing"]
        post=outcome["postclearing"]
        if pre["clearing_prices_available"] or pre["cashflow_eur"] is not None:
            raise AssertionError("Future clearing price/award leaked into pre-auction report")
        if len(post["simulated_delivered_mwh"])!=count:
            raise AssertionError("Missing delivery intervals")
        if abs(post["gross_contract_cashflow_proxy_eur"]-cash)>1e-7:
            raise AssertionError("Independent gross contract price x MWh oracle failed")
        if abs(post["total_accepted_mwh"]-total)>1e-7:
            raise AssertionError("Independent accepted volume energy oracle failed")
        if (post["maximum_contract_vs_simulated_delivery_mwh"]>1e-8
            or post["gas_balance_max_residual_mwh"]>1e-8
            or post["heat_service_max_residual_mwh"]>1e-8):
            raise AssertionError("Unmatched acceptance or physical gas/heat imbalance")
        if (post["imbalance_settlement_included"]
            or post["real_exchange_transaction"]
            or post["bid_acceptance_optimization_included"]
            or post["actual_export_measurements_included"]
            or post["market_profit_claimed"]):
            raise AssertionError("Unsupported market claim found")
        checked[name]={
            "gross_contract_proxy_eur":post["gross_contract_cashflow_proxy_eur"],
            "accepted_mwh":post["total_accepted_mwh"],
            "max_contract_delivery_residual_mwh":post["maximum_contract_vs_simulated_delivery_mwh"],
            "forecast_asof_utc":pre["forecast_issued_utc"],
            "gate_close_utc":pre["gate_close_utc"],
            "prices_published_utc":post["prices_published_utc"],
            "participants_informed_utc":post["participant_result_received_utc"],
        }
    # Negative control: accepted volume is less than hypothetical
    # gas-mass-constrained generation: must throw, never sell surplus
    # nor price an unmodelled imbalance.
    case=json.loads((ROOT/"examples/v0910_market_hourly.json").read_text())
    config=json.loads((ROOT/"examples/v0910_synthetic_chp.json").read_text())
    pre=validate_preclearing_offer(case["market"],case["delivery_slots"],
                                     case["preclearing_offer"],config["electric_rating_mw"])
    case["exogenous_award"]["accepted_mwh"][1]=.1
    try:
        audit_postclearing_delivery(case["market"],case["delivery_slots"],
                                      pre,case["exogenous_award"],config)
    except MarketBoundaryError as exc:
        if "UNMODELLED_IMBALANCE" not in str(exc):
            raise AssertionError("Rejected mismatch for unexpected reason") from exc
    else:
        raise AssertionError("Accepted-delivered mismatched case was improperly valued")
    return {
        "status":"PASS","version":"0.9.10",
        "source":"entirely invented market timing, price/award and CHP, not observed operation",
        "gate":"Preclear forecasts isolated; postclear exogenous accepted MWh must exactly match physically audited synthetic CHP electricity",
        "independent_exact_gross_cashflow_oracles":checked,
        "rejected_unmodelled_imbalance":True,
        "real_market_profitability_claimed":False,
        "original_frozen_science_files_modified":False,
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (AssertionError,MarketBoundaryError) as exc:
        raise SystemExit("V0910 MARKET BOUNDARY AUDIT FAILED: "+str(exc))
