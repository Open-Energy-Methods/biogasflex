"""v0.9.12 independent source-arithmetic and operational-block research gate."""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.evidence_v0912 import (
    run_evidence_audit, require_operational_validation, EvidenceError,
)


def audit():
    r=run_evidence_audit(ROOT/"examples/v0912_external_evidence.json",ROOT)
    m=r["market_archive"]
    c=r["independent_chp_reference"]
    p=c["periods"]
    if m["observed_intervals"]!=24 or abs(m["mean_price_eur_mwh"]-167.71/24)>1e-10:
        raise AssertionError("Frozen observed market price source/UTC/average oracle failed")
    if (m["per_price_original_publication_event_proven"] or
        m["asof_price_forecast_evidence_eligible"] or
        m["historical_bidtime_market_visibility_confirmed"] or
        m["this_archived_copy_existed_before_decision"]):
        raise AssertionError("Future archival snapshot falsely labelled ex-ante available")
    if c["annual_record_count"]!=11:
        raise AssertionError("CHP annual reference incomplete")
    reference={
        "2012-2017": (910533,1219.3916666666667,1615.935),
        "2018-2022": (1267253.2,2131.222,2799.444),
    }
    for period,(gas,ele,heat) in reference.items():
        q=p[period]
        for got,want in (
            (q["mean_annual_gas_recovered_m3"],gas),
            (q["mean_annual_electricity_mwh"],ele),
            (q["mean_annual_heat_mwh"],heat),
        ):
            if abs(got-want)>1e-7:
                raise AssertionError("Independent 11-row annual paper arithmetic oracle failed")
    if abs(c["source_published_mean_discrepancy_m3_per_year"]-24261.8)>1e-7:
        raise AssertionError("Published Table 3 discrepancy was hidden or corrected without attribution")
    if not c["source_table_mean_discrepancy_flag"]:
        raise AssertionError("Missing source-reported inconsistency flag")
    if (c["same_plant_as_hypothetical_dispatch"]
        or c["independent_hourly_chp_telemetry_available"]
        or c["hourly_ramp_dwell_and_startup_validated"]
        or c["electricity_at_grid_point_metered_for_model"]
        or r["real_contract_dispatch_eligible"]):
        raise AssertionError("Annual different-site evidence improperly elevated to site-operational validation")
    try:
        require_operational_validation(r)
    except EvidenceError as exc:
        if "REAL_OPERATIONAL_VALIDATION_BLOCKED" not in str(exc):
            raise AssertionError("Operational validation gate blocked for wrong reason") from exc
    else:
        raise AssertionError("Unsupported real market/CHP validation claim passed")
    return {
        "version":"0.9.12",
        "audit_status":"PASS_SOURCE_ACCOUNTING_ONLY",
        "historical_SvK_market_observations":m["observed_intervals"],
        "publication_proven_market_price_asof":False,
        "independent_lfg_chp_annual_records":c["annual_record_count"],
        "source_published_2018_2022_gas_mean_m3":c["published_2018_2022_gas_mean_m3"],
        "recomputed_2018_2022_gas_mean_m3":c["recomputed_2018_2022_gas_mean_m3"],
        "annual_source_discrepancy_m3_per_year":c["source_published_mean_discrepancy_m3_per_year"],
        "current_synthetic_model_electric_rating_mw":c["hypothetical_model_rating_mw"],
        "independent_reference_electric_rating_mw":c["source_plant_electric_rating_mw"],
        "operational_claim_denied":True,
        "unmodified_legacy_research":True,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(audit(),indent=2,allow_nan=False))
    except (EvidenceError,AssertionError) as exc:
        raise SystemExit(f"V0912 EXTERNAL EVIDENCE AUDIT FAIL: {exc}")
