"""Fail-closed, source-scoped manufacturer and plant parameter evidence gate.

This is NOT physical calibration, interval feasibility proof or live web
scraping. The offline curated source observations are versioned and subject to
full release-manifest SHA256 integrity checks; online pages can later change.
"""
from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any

PROTOCOL = "BIOGASFLEX_V0914_MANUFACTURER_EVIDENCE_REGISTER_V1"
ALLOWED_ADMISSIBILITY = {"SOURCE_SITE_STATIC_SCREEN", "REFERENCE_ONLY", "BLOCKED"}
ALLOWED_CLASSES = {
    "PUBLISHED_PLANT_NOMINAL", "OBSERVED_ANNUAL_PUBLISHED",
    "MANUFACTURER_PUBLIC", "UNIDENTIFIED",
}
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTER = ROOT / "data/evidence/v0914_chp_parameter_register.json"
EXPECTED_SOURCES = {
    "ciula2023": (
        "ciula_landfill_chp",
        "PEER_REVIEWED_SITE_STUDY",
        "https://doi.org/10.3390/en16052180",
    ),
    "cat_cg132b8_2026": (
        "cat_cg132b8",
        "MANUFACTURER_PRODUCT_PAGE",
        "https://www.cat.com/en_GB/products/new/power-systems/electric-power/gas-generator-sets/15969935.html",
    ),
    "jenbacher_j312_2026": (
        "jenbacher_j312",
        "MANUFACTURER_PRODUCT_PAGE",
        "https://www.jenbacher.com/en/gas-engines/type-3/j312/",
    ),
}
EXPECTED_PLANT_NOMINAL = {
    "ciula_electric_rating": ("rated_electrical_output", 0.440, "MW_e"),
    "ciula_thermal_rating": ("rated_thermal_output", 0.520, "MW_th"),
    "ciula_electric_nominal_efficiency": ("nominal_electrical_efficiency", 0.376, "fraction"),
    "ciula_thermal_nominal_efficiency": ("nominal_thermal_efficiency", 0.428, "fraction"),
}
EXPECTED_MANUFACTURER_REFERENCES = {
    "cat_continuous_rating": (
        "cat_cg132b8", "continuous_electrical_rating", 0.400, "MW_e",
    ),
    "cat_max_electric_efficiency_slash": (
        "cat_cg132b8", "published_max_electric_efficiency_alternatives",
        ["43.1%", "42.1%"], "percent_alternatives",
    ),
    "jen_j312_up_to_electric": (
        "jenbacher_j312", "published_maximum_electrical_output_across_configs",
        0.635, "MW_e",
    ),
    "jen_j312_up_to_elec_efficiency": (
        "jenbacher_j312", "published_maximum_electrical_efficiency_across_configs",
        0.431, "fraction",
    ),
    "jen_biogas_reference_ch4": (
        "jenbacher_j312", "biogas_reference_ch4_fraction", 0.65, "volume_fraction",
    ),
    "jen_landfill_reference_ch4": (
        "jenbacher_j312", "landfill_reference_ch4_fraction", 0.55, "volume_fraction",
    ),
}
REQUIRED_MISSING_PARAMETERS = {
    "minimum_stable_electrical_load", "upward_ramp_limit",
    "downward_ramp_limit", "minimum_up_time", "minimum_down_time",
    "start_cost", "electrical_efficiency_by_load",
    "recoverable_heat_by_load", "usable_gas_buffer",
    "heat_demand_profile", "engine_fuel_input_profile",
    "net_grid_export_profile", "dated_outage_intervals",
    "fuel_lhv_time_series",
}
REQUIRED_PARAM_KEYS = {
    "id", "equipment_id", "parameter", "value", "unit", "source_id",
    "source_locator", "evidence_class", "temporal_resolution",
    "admissibility", "interpretation", "limitation",
}
EXPECTED_ANNUAL_FIELDS = {
    "annual_running_hours_series", "annual_electricity_generation_series",
    "annual_heat_generation_series", "annual_recovered_landfill_gas_series",
}
REQUIRED_FLAGS = {
    "manufacturer_identity_of_published_plant_verified": False,
    "vendor_page_archival_snapshot_sha256_available": False,
    "hourly_chp_measurements_available": False,
    "manufacturer_part_load_curve_verified": False,
    "manufacturer_ramp_limit_verified": False,
    "combined_plant_manufacturer_performance_case_admissible": False,
    "equipment_parameter_auto_import_into_solver_allowed": False,
}


class EvidenceRegisterError(ValueError):
    """Violation of manufacturer source scope or physical-evidence status."""


def _check(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceRegisterError(message)


def _positive_finite_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def audit_register(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate curated sources, units and equipment applicability, no solver import."""
    _check(type(payload) is dict, "Register must be JSON object")
    _check(payload.get("protocol") == PROTOCOL, "Unexpected evidence protocol")
    _check(payload.get("reviewed_on") == "2026-11-15", "Unreviewed source date")
    _check(
        payload.get("immutable_annual_input_path")
        == "data/observed/ciula_2023_landfill_chp_annual.csv",
        "Published original annual source cannot be replaced",
    )
    _check(
        payload.get("allowed_uses") == [
            "SOURCE_SITE_STATIC_SCREEN", "REFERENCE_ONLY", "BLOCKED"
        ],
        "Invalid declared admissibility list",
    )
    _check(
        payload.get("flags") == REQUIRED_FLAGS,
        "Physical validation or cross-equipment linkage cannot be asserted",
    )
    equipment = payload.get("equipment")
    _check(type(equipment) is list and len(equipment) == 3, "Expected three separate equipment identities")
    by_equipment: dict[str, dict] = {}
    for item in equipment:
        _check(type(item) is dict and type(item.get("id")) is str, "Malformed equipment identity")
        _check(item["id"] not in by_equipment, "Duplicate equipment identity")
        by_equipment[item["id"]] = item
    _check(set(by_equipment) == {"ciula_landfill_chp", "cat_cg132b8", "jenbacher_j312"}, "Equipment identities changed")
    _check(
        by_equipment["ciula_landfill_chp"].get("installed_engine_make_model") == "UNKNOWN"
        and by_equipment["ciula_landfill_chp"].get("fuel_category") == "LANDFILL_GAS",
        "Polish engine is not manufacturer-identified, and landfill fuel cannot be relabelled",
    )
    for key in ("cat_cg132b8", "jenbacher_j312"):
        _check(by_equipment[key].get("linkage") == "NO_LINK_TO_SOURCE_SITE",
               "Manufacturer catalogue example is not identified as the published site engine")
    sources = payload.get("sources")
    _check(type(sources) is list and len(sources) == 3, "Expected exactly three independently scoped source documents")
    observed = {}
    for item in sources:
        _check(type(item) is dict and item.get("id") in EXPECTED_SOURCES, "Unrecognised source")
        sid = item["id"]
        _check(sid not in observed, "Duplicate source")
        eq, kind, url = EXPECTED_SOURCES[sid]
        _check(
            item.get("scope_equipment") == eq
            and item.get("source_kind") == kind
            and item.get("url") == url
            and bool(item.get("is_manufacturer_document")) == (kind == "MANUFACTURER_PRODUCT_PAGE"),
            f"{sid}: incorrect provider, URL or equipment scope",
        )
        for k in ("publisher", "document", "source_locator"):
            _check(type(item.get(k)) is str and len(item[k]) >= 6, f"{sid}: missing source attribution {k}")
        observed[sid] = item
    _check(set(observed) == set(EXPECTED_SOURCES), "Missing evidence provider")
    params = payload.get("parameters")
    _check(type(params) is list and len(params) == 29, "Unreviewed parameter count")
    seen: dict[str, dict] = {}
    for row in params:
        _check(type(row) is dict and set(row) == REQUIRED_PARAM_KEYS, "Parameter schema error")
        rid = row["id"]
        _check(type(rid) is str and rid not in seen, "Duplicate or nonstring parameter ID")
        seen[rid] = row
        _check(row["equipment_id"] in by_equipment, f"{rid}: unknown equipment")
        _check(type(row["parameter"]) is str and bool(row["parameter"]), f"{rid}: parameter missing")
        _check(type(row["unit"]) is str and bool(row["unit"]), f"{rid}: unit missing")
        _check(row["evidence_class"] in ALLOWED_CLASSES, f"{rid}: invalid provenance class")
        _check(row["admissibility"] in ALLOWED_ADMISSIBILITY, f"{rid}: invalid use status")
        _check(type(row["temporal_resolution"]) is str and bool(row["temporal_resolution"]), f"{rid}: temporal basis missing")
        for key in ("interpretation", "limitation"):
            _check(type(row[key]) is str and len(row[key]) >= 12, f"{rid}: missing physical qualification")
        cls = row["evidence_class"]
        if cls == "UNIDENTIFIED":
            _check(
                row["equipment_id"] == "ciula_landfill_chp"
                and row["source_id"] is None and row["source_locator"] is None
                and row["value"] is None and row["admissibility"] == "BLOCKED"
                and row["temporal_resolution"] == "NOT_AVAILABLE",
                f"{rid}: unidentified parameter must remain absent and blocked",
            )
        else:
            _check(row["source_id"] in observed, f"{rid}: missing cited source")
            source = observed[row["source_id"]]
            _check(row["equipment_id"] == source["scope_equipment"],
                   f"{rid}: manufacturer/site source cannot be transferred to another engine")
            _check(type(row["source_locator"]) is str and len(row["source_locator"]) >= 5,
                   f"{rid}: missing exact page/table locator")
            _check(row["admissibility"] != "BLOCKED", f"{rid}: cited source unexpectedly blocked")
            if cls == "MANUFACTURER_PUBLIC":
                _check(source["is_manufacturer_document"] is True
                       and row["admissibility"] == "REFERENCE_ONLY",
                       f"{rid}: manufacturer catalogue is reference only")
            elif cls in ("PUBLISHED_PLANT_NOMINAL", "OBSERVED_ANNUAL_PUBLISHED"):
                _check(row["source_id"] == "ciula2023", f"{rid}: plant data requires site study")
        if row["admissibility"] == "SOURCE_SITE_STATIC_SCREEN":
            _check(
                rid in ("ciula_electric_rating", "ciula_thermal_rating")
                and cls == "PUBLISHED_PLANT_NOMINAL"
                and row["temporal_resolution"] == "NAMEPLATE",
                f"{rid}: only site-specific published electrical/thermal ratings may screen static nameplate",
            )
        if type(row["value"]) in (float,int):
            _check(_positive_finite_number(row["value"]), f"{rid}: invalid numeric value")
        if type(row["value"]) is list:
            _check(bool(row["value"]) and all(type(x) is str and x for x in row["value"]), f"{rid}: invalid alternatives")

    _check(
        {r["parameter"] for r in params if r["evidence_class"] == "UNIDENTIFIED"}
        == REQUIRED_MISSING_PARAMETERS,
        "Missing essential unidentifiable dynamic operating limits",
    )
    for rid, (param, nominal, units) in EXPECTED_PLANT_NOMINAL.items():
        row = seen.get(rid, {})
        _check(row.get("parameter") == param and row.get("value") == nominal
               and row.get("unit") == units and row.get("source_id") == "ciula2023"
               and row.get("evidence_class") == "PUBLISHED_PLANT_NOMINAL",
               f"{rid}: published site Table 1 nominal value changed")
    for rid, (equipment_id, param, value, units) in EXPECTED_MANUFACTURER_REFERENCES.items():
        row = seen.get(rid, {})
        _check(row.get("equipment_id") == equipment_id
               and row.get("parameter") == param
               and row.get("value") == value and row.get("unit") == units
               and row.get("evidence_class") == "MANUFACTURER_PUBLIC"
               and row.get("admissibility") == "REFERENCE_ONLY",
               f"{rid}: manufacturer stated reference or its meaning changed")
    for key in EXPECTED_ANNUAL_FIELDS:
        matches = [r for r in params if r["parameter"] == key]
        _check(len(matches) == 1
               and matches[0]["evidence_class"] == "OBSERVED_ANNUAL_PUBLISHED"
               and matches[0]["value"] is None
               and matches[0]["temporal_resolution"] == "ANNUAL"
               and matches[0]["admissibility"] == "REFERENCE_ONLY"
               and payload["immutable_annual_input_path"] in matches[0]["source_locator"],
               f"{key}: keep observations in pinned annual source, never invent time-resolved values")
    from .annual_chp_evidence import audit_annual_chp
    # Rechecks the independently published annual CSV and its pinned SHA256,
    # even if a caller supplies a temporary parameter register.
    yearly = audit_annual_chp(ROOT / payload["immutable_annual_input_path"])
    _check(yearly["nameplate"] == {"electric_mw": .44, "thermal_mw": .52},
           "Annual paper and nominal parameter register conflict")
    counts = dict(sorted(Counter(r["evidence_class"] for r in params).items()))
    unknown = sorted(r["parameter"] for r in params if r["evidence_class"] == "UNIDENTIFIED")
    return {
        "status": "PASS_SOURCE_SCOPED_NO_DISPATCH_CALIBRATION",
        "protocol": PROTOCOL,
        "audit_date": payload["reviewed_on"],
        "sources_checked_against_curated_source_catalogue": len(observed),
        "equipment_identities_kept_separate": len(by_equipment),
        "parameters_reviewed": len(params),
        "provenance_counts": counts,
        "unidentified_operating_parameters": unknown,
        "unidentified_count": len(unknown),
        "static_site_nameplate_screening_parameters": [
            "ciula_electric_rating", "ciula_thermal_rating"
        ],
        "manufacturer_numeric_data_usable_as_site_performance": False,
        "manufacturer_part_load_efficiency_identified": False,
        "site_ramps_and_minimum_load_identified": False,
        "site_hourly_heat_service_identified": False,
        "source_site_and_references_equated": False,
        "auto_import_into_dispatch": False,
        "physical_validation_of_v0911_contracts": False,
        "annual_source_sha256": yearly["input_csv_sha256"],
        "source_mutability_note": (
            "Curated manufacturer pages checked 2026-11-15; no complete local "
            "signed/archived vendor web snapshots. Verify revision and fuel/options "
            "with manufacturer before any hardware case."
        ),
        "next_evidence_needed": (
            "Named installed engine and spec revision, measured load/fuel/heat time series, "
            "minimum stable load, ramp tests, starts and downtime, buffer pressure-volume "
            "and LHV, usable heat load, net metered export."
        ),
    }


def run_register(path: str | Path = DEFAULT_REGISTER) -> dict[str, Any]:
    return audit_register(json.loads(Path(path).read_text(encoding="utf-8")))
