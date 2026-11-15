"""v0.9.13 independent original 2020 SE3 retrospective source-timing oracle.

The v0.9.12 CHP annual study is audited by its inherited independent
script. This only tests the additional chronological market evidence gate.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.market_provenance_v0913 import (
    run_market_source_audit, require_operational_validation, EvidenceError,
)
from biogasflex.annual_chp_evidence import PUBLISHED_CSV_SHA256


def audit():
    r=run_market_source_audit(ROOT/"examples/v0913_market_provenance.json")
    market=r["market_archive"]
    chp=r["published_independent_annual_chp"]
    if market["observed_intervals"]!=24:
        raise AssertionError("Source SE3 April 2020 24 hourly values incomplete")
    if abs(market["mean_price_eur_mwh"]-167.71/24)>1e-10:
        raise AssertionError("Independent 24-row price arithmetic differs")
    if market["source_dataset_record_publication_date"]!="2026-04-09":
        raise AssertionError("Source publication timeline altered")
    if market["snapshot_retrieval_date"]!="2026-11-05":
        raise AssertionError("Original archive acquisition altered")
    if (market["per_price_original_publication_event_proven"] or
        market["historical_bidtime_market_visibility_confirmed"] or
        market["asof_price_forecast_evidence_eligible"]):
        raise AssertionError("Archive mistakenly treated as 2020 bid-time evidence")
    if (chp["years"]!=11 or chp["source_csv_sha256"]!=PUBLISHED_CSV_SHA256 or
        chp["rated_electric_mw"]!=.44 or chp["hourly_plant_calibration"]):
        raise AssertionError("Pre-existing independent v0.9.12 CHP study was duplicated or elevated to high-frequency calibration")
    if (r["operational_contract_dispatch_eligible"] or r["same_chp_site_as_published_source"]
        or r["site_specific_hourly_operating_limits_verified"]):
        raise AssertionError("Unjustified real plant/market operational claim")
    try:
        require_operational_validation(r)
    except EvidenceError as err:
        if "REAL_OPERATIONAL_VALIDATION_BLOCKED" not in str(err):
            raise AssertionError("Unexpected operational block reason") from err
    else:
        raise AssertionError("Retrospective data incorrectly authorizes real dispatch")
    return {
        "status":"PASS_EX_POST_MARKET_SOURCE_ONLY",
        "version":"0.9.13",
        "observed_2020_Svk_SE3_prices":market["observed_intervals"],
        "mean_observed_price_eur_mwh":market["mean_price_eur_mwh"],
        "source_dataset_publication_date":"2026-04-09",
        "original_historical_auction_publication_verified":False,
        "existing_annual_independent_chp_study_reused":True,
        "external_chp_observed_annual_records":11,
        "plant_specific_dynamic_chp_validated":False,
        "operational_contract_dispatch_blocked":True,
    }


if __name__=="__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (EvidenceError,AssertionError) as exc:
        raise SystemExit(f"V0913 MARKET PROVENANCE AUDIT FAILED: {exc}")
