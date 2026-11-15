"""BiogasFlex v0.9.12 — source-pinned market history and external CHP evidence gates.

This module cannot independently verify historical per-slot price publication
timestamps (not present in the Svk archive) or calibrate dynamic plant physics
from published annual CHP aggregates. Both limitations are fail-closed.
No network or live credentials are required for the forensic audit.
"""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA = "biogasflex_external_evidence_v0912"
ROOT = Path(__file__).resolve().parents[2]
LOCAL_ZONE = ZoneInfo("Europe/Stockholm")
MARKET_KEYS = frozenset({
    "source_provider", "bidding_zone", "delivery_local_date", "price_unit",
    "path", "sha256", "resource_id", "source_url",
    "source_dataset_first_publication_date", "snapshot_retrieval_date",
    "preauction_decision_utc", "original_per_interval_publication_proof",
    "permitted_claim",
})
CHP_KEYS = frozenset({
    "classification", "site_id", "source_title", "source_url", "doi",
    "published_date", "licence", "source_tables", "csv_path", "csv_sha256",
    "rated_electrical_mw", "rated_thermal_mw",
    "originally_reported_2018_2022_gas_mean_m3_per_year",
    "site_fuel_class", "temporal_resolution",
})
DATA_HEADER = [
    "year", "plant_running_hours", "landfill_gas_recovered_m3",
    "electricity_generated_mwh", "heat_generated_mwh", "source_table",
]
PRICE_HEADER = ["start_time_utc", "bidding_zone", "price", "price_unit"]
SVK_SOURCE_ID = "cf392ef3-7345-4e98-970e-83088c185570"
SVK_SOURCE_URL = (
    "https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/"
    + SVK_SOURCE_ID
)
PAPER_DOI = "10.3390/en16052180"
PAPER_URL = "https://www.mdpi.com/1996-1073/16/5/2180"
ANNUAL_YEAR_RANGE = list(range(2012, 2023))


class EvidenceError(ValueError):
    """Source provenance, temporal availability, or data quality is unsupported."""


def _keys(obj: Any, keys: frozenset[str], label: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != keys:
        raise EvidenceError(f"{label} must declare exactly {sorted(keys)}")
    return obj


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise EvidenceError(f"{label} requires YYYY-MM-DD")
    try:
        x = date.fromisoformat(value)
    except ValueError as exc:
        raise EvidenceError(f"Invalid {label}") from exc
    if x.isoformat() != value:
        raise EvidenceError(f"Noncanonical {label}")
    return x


def _utc(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError(f"{label} needs explicit UTC timestamp")
    try:
        x = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"{label} invalid ISO timestamp") from exc
    if x.tzinfo is None or x.utcoffset() != timedelta(0):
        raise EvidenceError(f"{label} must have explicit UTC offset")
    return x.astimezone(timezone.utc)


def _numeric(x: Any, label: str, *, positive: bool = False) -> float:
    if type(x) not in (int, float):
        raise EvidenceError(f"{label}: expected numeric, not boolean/text")
    y = float(x)
    if not math.isfinite(y) or (positive and y <= 0):
        raise EvidenceError(f"{label}: nonfinite or nonpositive measurement")
    return y


def _pinned_text(root: Path, path: Any, expected_sha: Any) -> str:
    if not isinstance(path, str) or not path or not isinstance(expected_sha, str):
        raise EvidenceError("Source filepath and SHA-256 must be explicit")
    if len(expected_sha) != 64 or any(c not in "0123456789abcdef" for c in expected_sha):
        raise EvidenceError("Expected lowercase 64-character SHA-256 hash")
    root = root.resolve()
    selected = (root / path).resolve()
    try:
        relative = selected.relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceError("External data path cannot escape repository") from exc
    if relative != path or not selected.is_file():
        raise EvidenceError("Missing, noncanonical or unsupported repository source file")
    actual = sha256(selected.read_bytes()).hexdigest()
    if actual != expected_sha:
        raise EvidenceError(f"SHA256_SOURCE_TAMPERED: {path}")
    manifest = root / "SHA256SUMS.txt"
    pins = {}
    for line in manifest.read_text(encoding="utf-8").splitlines():
        if len(line) < 67 or line[64:66] != "  ":
            raise EvidenceError("Invalid repository-wide SHA-256 manifest")
        key = line[66:]
        if key in pins:
            raise EvidenceError("Duplicate pinned file entry")
        pins[key] = line[:64]
    if pins.get(relative) != expected_sha:
        raise EvidenceError(f"SOURCE_NOT_REPO_PINNED: {relative}")
    try:
        return selected.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise EvidenceError("Source is not valid UTF-8") from exc


def audit_market_archive(root: Path, market: dict) -> dict:
    """Verify original observed price values, NOT unrecorded bid-time availability."""
    _keys(market, MARKET_KEYS, "market_archive")
    if (market["source_provider"] != "Svenska kraftnät"
        or market["resource_id"] != SVK_SOURCE_ID
        or market["source_url"] != SVK_SOURCE_URL
        or market["bidding_zone"] != "SE3"
        or market["price_unit"] != "EUR-MWh"
        or market["permitted_claim"] != "OBSERVED_EX_POST_ONLY"
        or market["original_per_interval_publication_proof"] != "NOT_ARCHIVED"):
        raise EvidenceError("Unsupported market source or elevated as-of claim")
    delivery = _date(market["delivery_local_date"], "local delivery day")
    published = _date(market["source_dataset_first_publication_date"], "source dataset publication date")
    retrieved = _date(market["snapshot_retrieval_date"], "snapshot retrieval date")
    decision = _utc(market["preauction_decision_utc"], "preauction_decision_utc")
    if retrieved < published:
        raise EvidenceError("Snapshot cannot have been retrieved before the source dataset record")
    if decision.astimezone(LOCAL_ZONE).date() != delivery-timedelta(days=1):
        raise EvidenceError("Preauction decision must be on previous Stockholm local date")
    raw = _pinned_text(root, market["path"], market["sha256"])
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames != PRICE_HEADER:
        raise EvidenceError("Frozen Svk source columns/units altered")
    rows = list(reader)
    if not rows:
        raise EvidenceError("Empty observed market window")
    previous = None
    prices = []
    for i, row in enumerate(rows):
        if set(row) != set(PRICE_HEADER):
            raise EvidenceError("Unexpected or missing price-source columns")
        stamp = _utc(row["start_time_utc"], f"observed_market[{i}].start_utc")
        if stamp.astimezone(LOCAL_ZONE).date() != delivery:
            raise EvidenceError("Price source mixes Stockholm delivery days")
        if previous is not None and stamp-previous != timedelta(hours=1):
            raise EvidenceError("Missing, overlapping or duplicated observed market interval")
        if row["bidding_zone"] != "SE3" or row["price_unit"] != "EUR-MWh":
            raise EvidenceError("Observed market zone/units mismatch")
        try:
            price = float(row["price"])
        except (ValueError, TypeError) as exc:
            raise EvidenceError("Malformed market observation") from exc
        if not math.isfinite(price):
            raise EvidenceError("Nonfinite market observation")
        prices.append(price)
        previous = stamp
    civil_start = datetime(delivery.year,delivery.month,delivery.day,tzinfo=LOCAL_ZONE)
    next_start = datetime.fromordinal(delivery.toordinal()+1).replace(tzinfo=LOCAL_ZONE)
    earliest = civil_start.astimezone(timezone.utc)
    expected_n = round((next_start.astimezone(timezone.utc)-earliest).total_seconds()/3600)
    if len(rows) != expected_n or _utc(rows[0]["start_time_utc"], "first") != earliest:
        raise EvidenceError("Missing/extra hours in observed Stockholm civil day, including DST")
    # The archive was extracted in 2026. Do NOT retroactively pretend it
    # is an as-of 2020 feed. The source has no per-interval release event.
    archive_available_by_decision = retrieved <= decision.date()
    return {
        "status":"SOURCE_SHA256_AND_PRICE_GRID_VERIFIED",
        "source_type":"SVK_RETROSPECTIVE_DAY_AHEAD_OBSERVED_PRICE",
        "zone":"SE3", "unit":"EUR/MWh",
        "delivery_local_date":delivery.isoformat(),
        "observed_intervals":len(rows),
        "first_interval_utc":earliest.isoformat(),
        "last_interval_utc":previous.isoformat(),
        "mean_price_eur_mwh":mean(prices),
        "source_csv_sha256":market["sha256"],
        "source_dataset_record_publication_date":published.isoformat(),
        "snapshot_retrieval_date":retrieved.isoformat(),
        "historical_preauction_decision_utc":decision.isoformat(),
        "this_archived_copy_existed_before_decision":archive_available_by_decision,
        "per_price_original_publication_event_proven":False,
        "asof_price_forecast_evidence_eligible":False,
        "historical_bidtime_market_visibility_confirmed":False,
        "claim_limit":"Historical settled area prices only; no captured original auction publication/participant result event or verifiable as-of forecast",
    }


def audit_external_annual_chp(root: Path, chp: dict, hypothetical_config_path: Any) -> dict:
    """Read source-published annual operating summary; never infer hourly limits."""
    _keys(chp, CHP_KEYS, "measured_chp_reference")
    if (chp["classification"] != "PUBLISHED_METER_BASED_ANNUAL_SUMMARIES"
        or chp["doi"] != PAPER_DOI or chp["source_url"] != PAPER_URL
        or chp["published_date"] != "2023-02-24"
        or chp["licence"] != "CC-BY-4.0"
        or chp["source_tables"] != [1,2,3]
        or chp["site_id"] != "POLISH_LANDFILL_GAS_CHP_440KWE_EXTERNAL_REFERENCE"
        or chp["site_fuel_class"] != "LANDFILL_GAS_NOT_CALIBRATED_SAME_PLANT"
        or chp["temporal_resolution"] != "ANNUAL_AGGREGATE_ONLY"):
        raise EvidenceError("Source study identity, licence, scale or measured scope altered")
    er = _numeric(chp["rated_electrical_mw"], "published nominal electric MW", positive=True)
    hr = _numeric(chp["rated_thermal_mw"], "published nominal thermal MW", positive=True)
    if abs(er-.44)>1e-12 or abs(hr-.52)>1e-12:
        raise EvidenceError("Published Table 1 rated capacity mismatch")
    raw = _pinned_text(root,chp["csv_path"],chp["csv_sha256"])
    reader = csv.DictReader(io.StringIO(raw))
    if reader.fieldnames != DATA_HEADER:
        raise EvidenceError("Published CHP annual source columns/units altered")
    entries = list(reader)
    if len(entries) != len(ANNUAL_YEAR_RANGE):
        raise EvidenceError("Incomplete independent annual CHP record")
    years=[]
    by_period={"2012-2017":[],"2018-2022":[]}
    yearly=[]
    for item in entries:
        if set(item)!=set(DATA_HEADER):
            raise EvidenceError("Missing or extra annual CHP columns")
        try:
            yr=int(item["year"])
            hrs=int(item["plant_running_hours"])
            gas=int(item["landfill_gas_recovered_m3"])
            ele=float(item["electricity_generated_mwh"])
            heat=float(item["heat_generated_mwh"])
            table=int(item["source_table"])
        except (ValueError,TypeError) as exc:
            raise EvidenceError("Malformed annual CHP record") from exc
        if (str(yr)!=item["year"] or str(hrs)!=item["plant_running_hours"]
            or str(gas)!=item["landfill_gas_recovered_m3"]
            or str(table)!=item["source_table"]):
            raise EvidenceError("Annual source integer fields not canonical")
        period="2012-2017" if 2012<=yr<=2017 else "2018-2022"
        if table != (2 if period=="2012-2017" else 3):
            raise EvidenceError("Annual row transcribed from incorrect source table")
        if not (0<hrs<=8784 and gas>0 and math.isfinite(ele)
                and math.isfinite(heat) and ele>0 and heat>0):
            raise EvidenceError("Nonphysical annual operating time, gas or energy")
        electric_avg_mw=ele/hrs
        thermal_avg_mw=heat/hrs
        if electric_avg_mw>er+1e-9 or thermal_avg_mw>hr+1e-9:
            raise EvidenceError("Annual generation exceeds installed nameplate times operating hours")
        years.append(yr)
        by_period[period].append((hrs,gas,ele,heat))
        yearly.append({
            "year":yr,"running_hours":hrs,
            "electricity_mwh":ele,"heat_mwh":heat,
            "annual_mean_during_running_electric_mw":electric_avg_mw,
            "annual_mean_during_running_thermal_mw":thermal_avg_mw,
            "electric_fraction_of_nameplate_while_running":electric_avg_mw/er,
            "thermal_fraction_of_nameplate_while_running":thermal_avg_mw/hr,
        })
    if years != ANNUAL_YEAR_RANGE:
        raise EvidenceError("Annual CHP years must be chronologically complete and nonduplicated")
    period_stats={}
    for period,a in by_period.items():
        hrs=sum(r[0] for r in a)
        el=sum(r[2] for r in a)
        he=sum(r[3] for r in a)
        period_stats[period]={
            "years":len(a),
            "mean_annual_running_hours":hrs/len(a),
            "mean_annual_gas_recovered_m3":sum(r[1] for r in a)/len(a),
            "mean_annual_electricity_mwh":el/len(a),
            "mean_annual_heat_mwh":he/len(a),
            "running_time_weighted_electric_mw":el/hrs,
            "running_time_weighted_heat_mw":he/hrs,
            "electric_nameplate_fraction_during_running":el/(hrs*er),
        }
    recomputed=period_stats["2018-2022"]["mean_annual_gas_recovered_m3"]
    reported=_numeric(chp["originally_reported_2018_2022_gas_mean_m3_per_year"],
                      "source Table 3 reported mean",positive=True)
    if abs(reported-1291515)>1e-6:
        raise EvidenceError("Reported Table 3 average differs from published source")
    root=root.resolve()
    if not isinstance(hypothetical_config_path,str):
        raise EvidenceError("Hypothetical config path required")
    config_path=(root/hypothetical_config_path).resolve()
    try:
        relative=config_path.relative_to(root).as_posix()
    except ValueError as exc:
        raise EvidenceError("Model configuration must stay within repository") from exc
    if relative!=hypothetical_config_path:
        raise EvidenceError("Hypothetical config path not canonical")
    model=json.loads(config_path.read_text(encoding="utf-8"))
    model_power=_numeric(model.get("electric_rating_mw"),"hypothetical nameplate",positive=True)
    return {
        "status":"PUBLISHED_ANNUAL_AGGREGATES_SOURCE_AND_ARITHMETIC_AUDITED",
        "source_doi":chp["doi"],
        "publication_date":chp["published_date"],
        "licence":chp["licence"],
        "source_chp_fuel":"LANDILL_GAS",
        "source_plant_electric_rating_mw":er,
        "source_plant_thermal_rating_mw":hr,
        "annual_record_count":len(yearly),
        "annual_summary_series":yearly,
        "periods":period_stats,
        "published_2018_2022_gas_mean_m3":reported,
        "recomputed_2018_2022_gas_mean_m3":recomputed,
        "source_published_mean_discrepancy_m3_per_year":reported-recomputed,
        "source_table_mean_discrepancy_flag":abs(reported-recomputed)>1.0,
        "hypothetical_model_rating_mw":model_power,
        "same_plant_as_hypothetical_dispatch":False,
        "annual_operating_aggregate_available":True,
        "independent_hourly_chp_telemetry_available":False,
        "hourly_minimum_stable_power_validated":False,
        "hourly_ramp_dwell_and_startup_validated":False,
        "fuel_LHV_and_electrical_efficiency_validated_for_model":False,
        "electricity_at_grid_point_metered_for_model":False,
        "claim_limit":"Meter-derived published annual observations from a DIFFERENT landfill-gas CHP; no hourly physical envelope or model calibration",
    }


def run_evidence_audit(manifest_path: Path, root: Path = ROOT) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    _keys(manifest,frozenset({"schema","market_archive","measured_chp_reference","hypothetical_chp_config"}),
          "external evidence manifest")
    if manifest["schema"] != SCHEMA:
        raise EvidenceError("Unknown external evidence schema/version")
    market = audit_market_archive(root,manifest["market_archive"])
    chp = audit_external_annual_chp(root,manifest["measured_chp_reference"],
                                     manifest["hypothetical_chp_config"])
    obstacles = [
        "No archived original per-slot auction publication/as-of feed for 2020 decision",
        "Independent annual CHP reference belongs to a different plant than the synthetic MILP",
        "Annual aggregates cannot establish hourly minimum-load/ramp/dwell or generator-to-grid metering",
        "Actual participant-specific accepted auction volumes and site CHP export telemetry absent",
    ]
    return {
        "version":"0.9.12",
        "status":"PASS_RETROSPECTIVE_SOURCE_AUDIT_NOT_OPERATIONAL_VALIDATION",
        "market_archive":market,
        "independent_chp_reference":chp,
        "operational_price_asof_validated":False,
        "plant_specific_hourly_chp_envelope_validated":False,
        "real_contract_dispatch_eligible":False,
        "blocking_reasons":obstacles,
        "claim_limit":"Only observed ex-post market prices and independently published different-plant annual operating aggregates are source audited; no real market dispatch or plant validation",
    }


def require_operational_validation(evidence_result: dict) -> None:
    """Fail closed: synthetic samples cannot be escalated to operational validation."""
    if not (
        evidence_result.get("operational_price_asof_validated") is True
        and evidence_result.get("plant_specific_hourly_chp_envelope_validated") is True
        and evidence_result.get("real_contract_dispatch_eligible") is True
    ):
        raise EvidenceError(
            "REAL_OPERATIONAL_VALIDATION_BLOCKED: no verified bid-time market "
            "publication event plus plant-matched hourly CHP measurements "
            "and grid export/accepted award data; synthetic dispatch only"
        )
