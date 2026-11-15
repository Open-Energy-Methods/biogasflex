"""Independent, solver-free read-only witness for the v0.9.13-A source register.

Intentionally does not import biogasflex nor its evidence parser. This is a
second implementation of source/units/applicability tests, not human peer review.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / "data/evidence/v0913_chp_parameter_register.json"
ANNUAL = ROOT / "data/observed/ciula_2023_landfill_chp_annual.csv"
SOURCES = {
    "ciula2023": ("ciula_landfill_chp", "https://doi.org/10.3390/en16052180"),
    "cat_cg132b8_2026": ("cat_cg132b8", "https://www.cat.com/en_GB/products/new/power-systems/electric-power/gas-generator-sets/15969935.html"),
    "jenbacher_j312_2026": ("jenbacher_j312", "https://www.jenbacher.com/en/gas-engines/type-3/j312/"),
}
EXPECTED = {
    "ciula_electric_rating": ("ciula_landfill_chp", .44, "MW_e"),
    "ciula_thermal_rating": ("ciula_landfill_chp", .52, "MW_th"),
    "ciula_electric_nominal_efficiency": ("ciula_landfill_chp", .376, "fraction"),
    "ciula_thermal_nominal_efficiency": ("ciula_landfill_chp", .428, "fraction"),
    "cat_continuous_rating": ("cat_cg132b8", .400, "MW_e"),
    "cat_max_electric_efficiency_slash": ("cat_cg132b8", ["43.1%", "42.1%"], "percent_alternatives"),
    "jen_j312_up_to_electric": ("jenbacher_j312", .635, "MW_e"),
    "jen_j312_up_to_elec_efficiency": ("jenbacher_j312", .431, "fraction"),
}
REQUIRED_UNKNOWN = {
    "minimum_stable_electrical_load", "upward_ramp_limit", "downward_ramp_limit",
    "minimum_up_time", "minimum_down_time", "start_cost",
    "electrical_efficiency_by_load", "recoverable_heat_by_load", "usable_gas_buffer",
    "heat_demand_profile", "engine_fuel_input_profile", "net_grid_export_profile",
    "dated_outage_intervals", "fuel_lhv_time_series",
}


def witness(path: Path = REGISTER) -> dict:
    data = json.loads(path.read_text(encoding="utf8"))
    assert data["protocol"] == "BIOGASFLEX_V0913_MANUFACTURER_EVIDENCE_REGISTER_V1"
    assert data["immutable_annual_input_path"] == "data/observed/ciula_2023_landfill_chp_annual.csv"
    assert len(data["sources"]) == 3 and len(data["equipment"]) == 3
    for s in data["sources"]:
        assert s["id"] in SOURCES
        assert (s["scope_equipment"], s["url"]) == SOURCES[s["id"]], s
    assert {e["id"] for e in data["equipment"]} == set(v[0] for v in SOURCES.values())
    site = next(e for e in data["equipment"] if e["id"] == "ciula_landfill_chp")
    assert site["installed_engine_make_model"] == "UNKNOWN"
    assert site["fuel_category"] == "LANDFILL_GAS"
    assert all(not flag for flag in data["flags"].values())
    entries = data["parameters"]
    assert len(entries) == 29 and len({e["id"] for e in entries}) == 29
    by_id = {r["id"]: r for r in entries}
    for rid, (equipment, value, unit) in EXPECTED.items():
        row = by_id[rid]
        assert (row["equipment_id"], row["value"], row["unit"]) == (equipment, value, unit), rid
    for p in entries:
        if p["source_id"] is not None:
            assert p["source_id"] in SOURCES
            assert p["equipment_id"] == SOURCES[p["source_id"]][0]
        if p["evidence_class"] == "MANUFACTURER_PUBLIC":
            assert p["admissibility"] == "REFERENCE_ONLY"
        if p["admissibility"] == "SOURCE_SITE_STATIC_SCREEN":
            assert p["id"] in ("ciula_electric_rating", "ciula_thermal_rating")
    missing = [p for p in entries if p["evidence_class"] == "UNIDENTIFIED"]
    assert {p["parameter"] for p in missing} == REQUIRED_UNKNOWN
    assert len(missing) == 14
    assert all(p["source_id"] is None and p["source_locator"] is None
               and p["value"] is None and p["admissibility"] == "BLOCKED"
               for p in missing)
    with ANNUAL.open(newline="", encoding="utf8") as f:
        rows = list(csv.DictReader(f))
    assert [int(r["year"]) for r in rows] == list(range(2012, 2023))
    assert len(rows) == 11
    return {
        "status": "PASS_INDEPENDENT_SOURCE_SCOPE",
        "sources": 3, "equipment_identities": 3, "parameter_rows": 29,
        "unidentified_dynamic_parameters": 14,
        "manufacturer_site_equivalence_asserted": False,
        "catalogue_efficiency_as_partload_curve": False,
        "physical_dispatch_calibrated": False,
        "source_claims_checked_against_frozen_human_curated_values": True,
        "live_manufacturer_revision_automatically_retrieved": False,
    }


if __name__ == "__main__":
    print(json.dumps(witness(), indent=2))
