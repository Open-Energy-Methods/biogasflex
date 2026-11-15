"""v0.9.15 CHP raw telemetry ingestion and metrology-readiness gate.

This sidecar validates 15-minute measured ENERGY / normalized-volume
accounting. A passing CSV is NOT a site-calibrated model, a ramp test,
a trustworthy certificate, net-exports forecast or validated market award.
A synthetic, immutable 4-row fixture demonstrates every code path. Real
data and calibration certificates must never be committed to this repo.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = "BIOGASFLEX_V0915_RAW_CHP_15MIN_ENERGY_QA_V1"
DEMO_CSV = "examples/v0915_synthetic_chp_metering.csv"
DEMO_DIGEST = "9fe9b0d49311c683e7c741d9a4bddf881f5da3870ca8e0207c3d99bb11f72d8f"
DEFAULT_MANIFEST = ROOT / "examples/v0915_synthetic_acquisition_manifest.json"
NUMERIC = (
    "generator_electric_kwh", "net_grid_export_kwh",
    "site_electric_consumption_kwh", "auxiliary_electric_consumption_kwh",
    "engine_gas_nm3_dry", "produced_gas_nm3_dry", "flared_gas_nm3_dry",
    "fuel_lhv_mj_per_nm3_dry", "useful_recovered_heat_kwh",
    "buffer_gas_start_nm3_dry", "buffer_gas_end_nm3_dry",
)
COLUMNS = ("interval_start_utc", "interval_end_utc") + NUMERIC + (
    "engine_running_fraction", "max_clock_offset_s", "quality_flag",
)
UNITS = {
    "generator_electric_kwh":"kWh_e",
    "net_grid_export_kwh":"kWh_e",
    "site_electric_consumption_kwh":"kWh_e",
    "auxiliary_electric_consumption_kwh":"kWh_e",
    "engine_gas_nm3_dry":"Nm3_dry",
    "produced_gas_nm3_dry":"Nm3_dry",
    "flared_gas_nm3_dry":"Nm3_dry",
    "fuel_lhv_mj_per_nm3_dry":"MJ/Nm3_dry",
    "useful_recovered_heat_kwh":"kWh_th",
    "buffer_gas_start_nm3_dry":"Nm3_dry",
    "buffer_gas_end_nm3_dry":"Nm3_dry",
}
MANIFEST_KEYS = {
    "protocol", "declared_on_utc", "study_id", "evidence_class",
    "site_pseudonym", "installed_engine_identity", "equipment_identity_verified",
    "collection_authorization_ref", "raw_csv_path", "raw_csv_sha256",
    "file_encoding", "time_basis", "interval_seconds",
    "maximum_allowed_clock_offset_seconds", "numeric_locale",
    "standard_dry_gas_reference", "fuel_energy_basis",
    "electrical_meter_boundary", "heat_meter_boundary",
    "buffer_measurement_basis", "generator_nameplate_kw_e",
    "nameplate_evidence_class", "nameplate_source_ref",
    "screening_multiplier_of_individual_standard_uncertainty_sum",
    "uncertainty_combination_basis", "high_rate_ramp_and_startup_event_log_available",
    "site_physical_validation_claim_allowed",
    "covariance_matrix_authentic_and_reviewed",
    "all_instruments_independently_calibrated_and_reviewed",
    "instrument_registry",
}


class TelemetryQAError(ValueError):
    """Instrument provenance, raw-data schema or physical screen failed."""


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise TelemetryQAError(message)


def _number(value: object, label: str, nonnegative: bool = True) -> float:
    if type(value) is bool:
        raise TelemetryQAError(f"{label}: boolean is not a numerical measurement")
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise TelemetryQAError(f"{label}: not a numeric quantity") from exc
    _require(math.isfinite(x), f"{label}: nonfinite value")
    if nonnegative:
        _require(x >= 0, f"{label}: negative value")
    return x


def _utc(value: object, label: str) -> datetime:
    _require(
        type(value) is str and bool(re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)", value
        )),
        f"{label}: explicit ISO UTC timestamp required (no implicit local/DST times)",
    )
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryQAError(f"{label}: invalid UTC calendar date") from exc
    _require(ts.tzinfo is not None and ts.utcoffset() == timedelta(0),
             f"{label}: UTC required")
    return ts.astimezone(timezone.utc)


def _register(manifest: dict) -> tuple[dict, bool]:
    _require(type(manifest) is dict and set(manifest) == MANIFEST_KEYS,
             "Unapproved instrument manifest shape")
    _require(manifest["protocol"] == PROTOCOL, "Unapproved data contract")
    _utc(manifest["declared_on_utc"], "declared_on_utc")
    real = manifest["evidence_class"] == "REAL_SITE_DATA_UNVERIFIED"
    _require(
        real or manifest["evidence_class"] == "SYNTHETIC_DEMONSTRATION_ONLY",
        "Unknown source evidence class",
    )
    for key, expected in {
        "file_encoding":"UTF-8",
        "time_basis":"UTC_START_INCLUSIVE_END_EXCLUSIVE",
        "interval_seconds":900,
        "numeric_locale":"PERIOD_DECIMAL_NO_THOUSANDS",
        "standard_dry_gas_reference":"DRY_NM3_AT_273.15K_AND_101325PA",
        "fuel_energy_basis":"LHV_MJ_PER_DRY_NORMAL_CUBIC_METRE",
        "electrical_meter_boundary":"GENERATOR_TERMINALS_SEPARATE_FROM_GRID_PCC",
        "heat_meter_boundary":"USEFUL_DELIVERED_HEAT_NOT_RECOVERABLE_EXHAUST_POTENTIAL",
        "buffer_measurement_basis":"DIRECT_DRY_NORMALIZED_VOLUME_NOT_PRESSURE_DERIVED",
        "screening_multiplier_of_individual_standard_uncertainty_sum":3,
        "uncertainty_combination_basis":"SUM_OF_ABSOLUTE_COMPONENT_STANDARD_UNCERTAINTIES_NOT_COVARIANCE_ESTIMATED",
        "high_rate_ramp_and_startup_event_log_available":False,
        "site_physical_validation_claim_allowed":False,
        "covariance_matrix_authentic_and_reviewed":False,
        "all_instruments_independently_calibrated_and_reviewed":False,
    }.items():
        _require(type(manifest[key]) is type(expected) and manifest[key] == expected,
                 f"{key}: unreviewed or misleading metrology claim")
    limit = _number(manifest["maximum_allowed_clock_offset_seconds"],
                    "maximum allowed sensor clock offset")
    _require(0 < limit <= 2, "Clock tolerance exceeds predeclared 2-second screen")
    nameplate = _number(manifest["generator_nameplate_kw_e"], "rated generator power")
    _require(nameplate > 0, "Positive generator nameplate required")
    _require(
        type(manifest["raw_csv_sha256"]) is str
        and bool(re.fullmatch("[0-9a-f]{64}",manifest["raw_csv_sha256"])),
        "Raw bytes require a pinned SHA256 digest",
    )
    _require(type(manifest["study_id"]) is str and len(manifest["study_id"]) >= 12,
             "Source study identifier missing")
    if real:
        _require(
            type(manifest["site_pseudonym"]) is str
            and manifest["site_pseudonym"] not in ("NONE_SYNTHETIC","UNKNOWN","")
            and type(manifest["installed_engine_identity"]) is str
            and len(manifest["installed_engine_identity"]) >= 6
            and type(manifest["collection_authorization_ref"]) is str
            and len(manifest["collection_authorization_ref"]) >= 6
            and manifest["equipment_identity_verified"] is True
            and manifest["nameplate_evidence_class"] == "SITE_DOCUMENTED_UNAUTHENTICATED"
            and type(manifest["nameplate_source_ref"]) is str
            and len(manifest["nameplate_source_ref"]) >= 6,
            "Real dataset requires distinct site, declared engine, access authorization and nameplate documents",
        )
    else:
        _require(
            manifest["raw_csv_path"] == DEMO_CSV
            and manifest["raw_csv_sha256"] == DEMO_DIGEST
            and manifest["site_pseudonym"] == "NONE_SYNTHETIC"
            and manifest["installed_engine_identity"] == "NONE_SYNTHETIC"
            and manifest["equipment_identity_verified"] is False
            and manifest["collection_authorization_ref"] is None
            and manifest["nameplate_evidence_class"] == "SYNTHETIC_ASSUMPTION"
            and manifest["nameplate_source_ref"] is None
            and nameplate == 80,
            "Synthetic fixture or site identity changed; cannot represent a real plant",
        )
    raw = manifest["instrument_registry"]
    _require(type(raw) is list and len(raw) == len(UNITS),
             "Exactly 11 required energy/gas/heat/buffer measurement channels")
    out = {}
    for item in raw:
        _require(type(item) is dict and set(item) == {
            "channel", "unit", "measurement_point", "device_id",
            "calibration_status", "certificate_ref", "certificate_valid_until_utc",
            "standard_u_fraction", "standard_u_absolute", "uncertainty_evaluation"
        }, "Instrument registry channel schema mismatch")
        key=item["channel"]
        _require(key in UNITS and key not in out and item["unit"] == UNITS[key],
                 "Instrument role, physical unit or duplicate channel invalid")
        _require(type(item["device_id"]) is str and len(item["device_id"]) >= 6
                 and type(item["measurement_point"]) is str and len(item["measurement_point"]) >= 12,
                 f"{key}: measurement location or instrument tag missing")
        rel=_number(item["standard_u_fraction"], f"{key} relative standard u")
        abs_u=_number(item["standard_u_absolute"], f"{key} absolute standard u")
        _require(rel+abs_u > 0 and rel <= 0.5, f"{key}: measured uncertainty absent or implausible")
        if real:
            _require(
                item["calibration_status"] == "DOCUMENTED_METADATA_NOT_INDEPENDENTLY_AUTHENTICATED"
                and type(item["certificate_ref"]) is str and len(item["certificate_ref"]) >= 6
                and item["uncertainty_evaluation"] == "SITE_DECLARED_NOT_INDEPENDENTLY_AUDITED",
                f"{key}: real data needs calibration reference metadata, not demo uncertainties",
            )
            _utc(item["certificate_valid_until_utc"],f"{key} calibration validity")
        else:
            _require(
                item["calibration_status"] == "SYNTHETIC_UNCALIBRATED"
                and item["certificate_ref"] is None
                and item["certificate_valid_until_utc"] is None
                and item["uncertainty_evaluation"] == "ILLUSTRATIVE_NOT_VERIFIED"
                and item["device_id"].startswith("SYNTH-"),
                f"{key}: synthetic instrumentation must not impersonate a calibrated device",
            )
        out[key] = item
    _require(set(out) == set(UNITS), "Required plant boundary channel missing")
    return out,real


def audit_telemetry(manifest_path: str | Path = DEFAULT_MANIFEST,
                    csv_path: str | Path | None = None) -> dict:
    """Validate source traceability and dry-normalized gas/heat/electric ledgers.

    This does NOT validate model predictions, start-stop dynamics, hourly
    physical operating limits, heat demand, or any bid-time settlement.
    """
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf8"))
    instruments,real=_register(manifest)
    if real:
        _require(csv_path is not None, "Real data requires an explicitly selected --csv file")
        _require(not Path(manifest_path).resolve().is_relative_to(ROOT.resolve()),
                 "Authorized real manifest must reside outside public research checkout")
        _require(not Path(csv_path).resolve().is_relative_to(ROOT.resolve()),
                 "Real raw data must reside outside public research checkout")
    if csv_path is None:
        src=Path(manifest["raw_csv_path"])
        src=src if src.is_absolute() else ROOT/src
    else:
        src=Path(csv_path)
    _require(src.is_file(), "Raw CSV missing; acquire data before physical validation")
    data=src.read_bytes()
    digest=sha256(data).hexdigest()
    _require(digest==manifest["raw_csv_sha256"], "Raw input changed versus immutable SHA256")
    if not real:
        _require(digest==DEMO_DIGEST, "Synthetic demo source digest is not authentic")
    try:
        s=io.StringIO(data.decode("utf-8-sig"))
    except UnicodeError as exc:
        raise TelemetryQAError("Raw CSV must decode as UTF-8") from exc
    reader=csv.DictReader(s)
    _require(tuple(reader.fieldnames or ())==COLUMNS,
             "Telemetry schema, column order or physical units changed")
    rows=[]
    previous_end=None
    previous_buffer_end=None
    min_start=None
    max_end=None
    multiplier=manifest["screening_multiplier_of_individual_standard_uncertainty_sum"]
    limit=manifest["maximum_allowed_clock_offset_seconds"]
    worst_clock=0.
    max_electric_residual=0.
    max_gas_residual=0.
    max_screening_fraction=0.
    for n,raw_row in enumerate(reader):
        _require(None not in raw_row and set(raw_row)==set(COLUMNS),
                 f"Row {n}: extra/missing fields")
        start=_utc(raw_row["interval_start_utc"],f"row {n} start")
        end=_utc(raw_row["interval_end_utc"],f"row {n} end")
        _require((end-start).total_seconds()==900,f"row {n}: bad interval duration")
        if previous_end is not None:
            _require(start==previous_end, f"row {n}: duplicate, gap or overlapping UTC intervals")
        previous_end=end
        if min_start is None:
            min_start=start
        max_end=end
        v={key:_number(raw_row[key],f"row {n} {key}",
                       nonnegative=(key!="net_grid_export_kwh"))
           for key in NUMERIC}
        fraction=_number(raw_row["engine_running_fraction"],f"row {n} running fraction")
        _require(fraction<=1, f"row {n}: running fraction above unity")
        clock=_number(raw_row["max_clock_offset_s"],f"row {n} source clock offset")
        _require(clock<=limit,f"row {n}: clock not sufficiently synchronized")
        worst_clock=max(worst_clock,clock)
        _require(raw_row["quality_flag"]=="GOOD",f"row {n}: bad or suspect quality flag")
        if previous_buffer_end is not None:
            _require(abs(v["buffer_gas_start_nm3_dry"]-previous_buffer_end)<=1e-9,
                     f"row {n}: buffer measurement discontinuity between intervals")
        previous_buffer_end=v["buffer_gas_end_nm3_dry"]
        _require(fraction>0 or v["generator_electric_kwh"]==0,
                 f"row {n}: electrical generation with engine declared off")
        _require(v["fuel_lhv_mj_per_nm3_dry"]>0, f"row {n}: nonpositive LHV")
        _require(v["engine_gas_nm3_dry"]>0 or
                 (v["generator_electric_kwh"]==0 and
                  v["useful_recovered_heat_kwh"]==0),
                 f"row {n}: nonzero output without measured engine fuel")
        def std_u(key: str) -> float:
            instrument=instruments[key]
            return (abs(v[key])*instrument["standard_u_fraction"]+
                    instrument["standard_u_absolute"])
        ue=sum(std_u(key) for key in (
            "generator_electric_kwh", "net_grid_export_kwh",
            "site_electric_consumption_kwh","auxiliary_electric_consumption_kwh"
        ))
        electric_residual=(
            v["generator_electric_kwh"]-v["net_grid_export_kwh"]-
            v["site_electric_consumption_kwh"]-
            v["auxiliary_electric_consumption_kwh"]
        )
        _require(abs(electric_residual)<=multiplier*ue+1e-9,
                 f"row {n}: generator/PCC/on-site/aux electricity balance outside screening bound")
        ug=sum(std_u(key) for key in (
            "produced_gas_nm3_dry","engine_gas_nm3_dry","flared_gas_nm3_dry",
            "buffer_gas_start_nm3_dry","buffer_gas_end_nm3_dry"
        ))
        gas_residual=(
            v["produced_gas_nm3_dry"]-v["engine_gas_nm3_dry"]-
            v["flared_gas_nm3_dry"]-
            (v["buffer_gas_end_nm3_dry"]-v["buffer_gas_start_nm3_dry"])
        )
        _require(abs(gas_residual)<=multiplier*ug+1e-9,
                 f"row {n}: production/engine/flare/buffer gas volume imbalance")
        fuel_kwh=v["engine_gas_nm3_dry"]*v["fuel_lhv_mj_per_nm3_dry"]/3.6
        ulhv=std_u("fuel_lhv_mj_per_nm3_dry")
        uvolume=std_u("engine_gas_nm3_dry")
        fuel_screen_u=(
            uvolume*v["fuel_lhv_mj_per_nm3_dry"]+
            v["engine_gas_nm3_dry"]*ulhv+uvolume*ulhv
        )/3.6
        e=v["generator_electric_kwh"]
        h=v["useful_recovered_heat_kwh"]
        _require(e+h <= fuel_kwh+multiplier*(
            fuel_screen_u+std_u("generator_electric_kwh")+
            std_u("useful_recovered_heat_kwh"))+1e-9,
            f"row {n}: electric plus useful heat exceeds plausible measured LHV input")
        _require(
            e<=manifest["generator_nameplate_kw_e"]*.25+
            multiplier*std_u("generator_electric_kwh")+1e-9,
            f"row {n}: interval energy exceeds declared generator nameplate",
        )
        max_electric_residual=max(max_electric_residual,abs(electric_residual))
        max_gas_residual=max(max_gas_residual,abs(gas_residual))
        max_screening_fraction=max(
            max_screening_fraction,
            abs(electric_residual)/(multiplier*ue+1e-9),
            abs(gas_residual)/(multiplier*ug+1e-9),
        )
        rows.append({
            "start_utc":start.isoformat(),
            "end_utc":end.isoformat(),
            "measured_generator_electric_kwh":e,
            "measured_grid_export_signed_kwh":v["net_grid_export_kwh"],
            "calculated_engine_fuel_lhv_kwh":fuel_kwh,
            "measured_useful_heat_kwh":h,
            "apparent_electric_lhv_ratio":e/fuel_kwh if fuel_kwh else None,
            "apparent_useful_heat_lhv_ratio":h/fuel_kwh if fuel_kwh else None,
            "electric_balance_residual_kwh":electric_residual,
            "gas_volume_balance_residual_nm3_dry":gas_residual,
            "energy_quality_flag":"QA_SCREEN_PASS_NOT_MODEL_VALIDATION",
        })
    _require(bool(rows), "No source telemetry intervals present")
    if real:
        _require(len(rows)>=96,"Real-data QA requires >=24h contiguous quarter-hour intervals")
        for key,inst in instruments.items():
            _require(
                _utc(inst["certificate_valid_until_utc"],key+" expiry")>=max_end,
                f"{key}: calibration metadata expired before telemetry period end",
            )
    else:
        _require(len(rows)==4 and min_start.isoformat()=="2026-10-01T00:00:00+00:00",
                 "Only frozen four-interval synthetic demonstration is accepted")
    return {
        "protocol":PROTOCOL,
        "status":(
            "PASS_REAL_DATA_SCHEMA_AND_BALANCE_SCREEN_PENDING_HUMAN_VERIFICATION"
            if real else
            "PASS_SYNTHETIC_SCHEMA_AND_BALANCE_QA_NO_PHYSICAL_VALIDATION"
        ),
        "source_class":manifest["evidence_class"],
        "study_id":manifest["study_id"],
        "site_pseudonym":manifest["site_pseudonym"],
        "raw_sha256":digest,
        "interval_count":len(rows),
        "interval_minutes":15,
        "period_start_utc":min_start.isoformat(),
        "period_end_utc":max_end.isoformat(),
        "measurement_channels":len(instruments),
        "maximum_clock_offset_seconds":worst_clock,
        "maximum_absolute_electric_balance_residual_kwh":max_electric_residual,
        "maximum_absolute_gas_volume_residual_nm3_dry":max_gas_residual,
        "maximum_screening_allowance_fraction_used":max_screening_fraction,
        "uncertainty_screening_basis":manifest["uncertainty_combination_basis"],
        "uncertainty_is_gum_combined_standard_uncertainty":False,
        "calibration_certificates_cryptographically_verified":False,
        "normal_volume_and_fuel_gas_composition_independently_verified":False,
        "raw_data_quality_screen_passed":True,
        "real_plant_model_validation_performed":False,
        "manufacturer_ramp_or_startup_limit_inferred":False,
        "net_grid_export_equivalent_to_generator_terminal_output":False,
        "energy_market_participation_and_bid_provenance_verified":False,
        "plant_operational_readiness_certified":False,
        "high_rate_startup_ramp_evidence_available":False,
        "intervals":rows,
        "scientific_boundary":(
            "Raw data and declared metering inventory screening only. "
            "No independently verified certificates, covariance matrix, "
            "fitted engine model, power-to-gas partload curves, high-rate "
            "startup/ramp events, revenue or instrument traceability claim."
        ),
    }
