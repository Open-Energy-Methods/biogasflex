"""BiogasFlex v0.9.13 — source-pinned market history and external CHP evidence gates.

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
from .annual_chp_evidence import audit_annual_chp, PUBLISHED_CSV_SHA256
from zoneinfo import ZoneInfo

SCHEMA = "biogasflex_market_provenance_v0913"
ROOT = Path(__file__).resolve().parents[2]
LOCAL_ZONE = ZoneInfo("Europe/Stockholm")
MARKET_KEYS = frozenset({
    "source_provider", "bidding_zone", "delivery_local_date", "price_unit",
    "path", "sha256", "resource_id", "source_url",
    "source_dataset_first_publication_date", "snapshot_retrieval_date",
    "preauction_decision_utc", "original_per_interval_publication_proof",
    "permitted_claim",
})
PRICE_HEADER = ["start_time_utc", "bidding_zone", "price", "price_unit"]
SVK_SOURCE_ID = "cf392ef3-7345-4e98-970e-83088c185570"
SVK_SOURCE_URL = (
    "https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/"
    + SVK_SOURCE_ID
)


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
    # Verified dates are part of this SPECIFIC frozen Svk source lineage.
    # Do not accept user-supplied earlier dates as proof of 2020 availability.
    if published != date(2026,4,9) or retrieved != date(2026,11,5):
        raise EvidenceError("Frozen Svk dataset publication/retrieval metadata cannot be backdated")
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


def run_market_source_audit(manifest_path: Path, root: Path = ROOT) -> dict:
    """Combine independent *retrospective* market and published annual CHP audits.

    The CHP source is the existing v0.9.12 publication; not duplicated,
    calibrated, merged across plants or treated as hourly equipment data.
    """
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    _keys(manifest,frozenset({
        "schema","market_archive","published_chp_reference_path",
        "hypothetical_chp_config",
    }),"market provenance manifest")
    if manifest["schema"]!=SCHEMA:
        raise EvidenceError("Unsupported market provenance schema")
    if manifest["published_chp_reference_path"]!="data/observed/ciula_2023_landfill_chp_annual.csv":
        raise EvidenceError("v0.9.13 uses only existing independently sourced v0.9.12 CHP study")
    if manifest["hypothetical_chp_config"]!="examples/v0911_synthetic_chp.json":
        raise EvidenceError("Unsupported hypothetical CHP reference model")
    market=audit_market_archive(root,manifest["market_archive"])
    root=root.resolve()
    candidate=(root/manifest["published_chp_reference_path"]).resolve()
    if candidate.parent!=root/"data/observed":
        raise EvidenceError("External CHP reference path escaped repository")
    chp=audit_annual_chp(candidate)
    if chp["input_csv_sha256"]!=PUBLISHED_CSV_SHA256:
        raise EvidenceError("Independent external CHP annual paper hash mismatch")
    model=json.loads((root/manifest["hypothetical_chp_config"]).read_text(encoding="utf-8"))
    rating=_numeric(model.get("electric_rating_mw"),
                    "synthetic dispatch model electrical rating",positive=True)
    blockers=[
        "2026 Svk archive does not establish actual 2020 auction publication or 2020 D-1 as-of information",
        "Published CHP 2012-2022 annual records are from a different Polish landfill-gas engine",
        "Annual generation cannot validate CHP 15-minute ramp, startup/dwell, fixed gas input or net grid export",
        "No real participant accepted volumes, site-calibrated matched CHP telemetry or imbalance settlement evidence",
    ]
    return {
        "version":"0.9.13",
        "status":"SOURCE_AUDIT_PASS_OPERATIONAL_ELIGIBILITY_DENIED",
        "market_archive":market,
        "published_independent_annual_chp":{
            "doi":chp["doi"],
            "site_fuel":chp["plant_fuel"],
            "years":len(chp["annual_observations"]),
            "rated_electric_mw":chp["nameplate"]["electric_mw"],
            "rated_thermal_mw":chp["nameplate"]["thermal_mw"],
            "source_csv_sha256":chp["input_csv_sha256"],
            "source_reported_average_discrepancies":chp["documented_source_discrepancies"],
            "annual_observation_evidence_level":chp["evidence_level"],
            "hourly_plant_calibration":False,
        },
        "hypothetical_dispatch_electric_rating_mw":rating,
        "same_chp_site_as_published_source":False,
        "market_asof_for_2020_preauction_verified":False,
        "site_specific_hourly_operating_limits_verified":False,
        "operational_contract_dispatch_eligible":False,
        "operational_blockers":blockers,
        "claim_limit":"Real observed ex-post prices and unrelated published annual CHP data are audited; no real operational market/plant validation",
    }


def require_operational_validation(report: dict) -> None:
    """Never convert a 2026 retrospective source into a 2020 trading certificate.

    Independent time-stamped market observations and same-plant high-frequency
    CHP measurements are absent, regardless of any manually edited status flags.
    A future version must implement and independently test a new evidence class.
    """
    if not isinstance(report,dict) or report.get("version")!="0.9.13":
        raise EvidenceError("REAL_OPERATIONAL_VALIDATION_BLOCKED: unsupported evidence schema")
    raise EvidenceError(
        "REAL_OPERATIONAL_VALIDATION_BLOCKED: archived market data do not prove "
        "historical bid-time availability; no site-matched CHP telemetry, "
        "participant-specific accepted awards or metered grid export"
    )
