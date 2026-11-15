"""Source-verified annual landfill-gas CHP evidence; not dispatch calibration.

Ciuła et al. (2023), Energies 16(5), 2180,
DOI: 10.3390/en16052180, Tables 1-3.
Uses only Python's standard library.  No invented hourly observations.
"""
from __future__ import annotations

import calendar
import csv
import hashlib
import io
import math
from pathlib import Path
from statistics import mean

DOI = "10.3390/en16052180"
SOURCE_URL = "https://doi.org/" + DOI
PUBLISHED_CSV_SHA256 = "ce018fd8ca3746a393c6a73c30321e8deb5c09ae8bef0497ab59b15bcbc33d10"
PLANT = "polish_municipal_landfill_gas_chp"
ELECTRIC_RATING_MW = 0.440
THERMAL_RATING_MW = 0.520
COLUMNS = (
    "year", "running_hours", "landfill_gas_recovered_m3",
    "electricity_generated_mwh", "heat_generated_mwh",
)
EXPECTED_YEARS = tuple(range(2012, 2023))
REPORTED_AVERAGES = {
    "2012-2017": {"running_hours": 7489, "landfill_gas_recovered_m3": 910533,
                  "electricity_generated_mwh": 1219.39, "heat_generated_mwh": 1615.94},
    "2018-2022": {"running_hours": 7848, "landfill_gas_recovered_m3": 1291515,
                  "electricity_generated_mwh": 2131.22, "heat_generated_mwh": 2799.44},
}
# Period-average LFG heating values are reported by the authors. NOT
# simultaneous annual fuel-meter readings, and not assumed to be normal m3.
PERIOD_GAS_HEATING_VALUE_KJ_M3 = {
    "2012-2017": 16548.7, "2018-2022": 19635.2,
}


class EvidenceError(ValueError):
    """An inadmissible, incomplete or physically contradictory source extract."""


def _positive_int(value: str, label: str) -> int:
    if not isinstance(value, str) or not value.isdecimal():
        raise EvidenceError(f"{label}: expected nonnegative integer")
    number = int(value)
    if number <= 0:
        raise EvidenceError(f"{label}: expected positive integer")
    return number


def _positive_float(value: str, label: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise EvidenceError(f"{label}: invalid numerical quantity") from exc
    if not math.isfinite(number) or number <= 0:
        raise EvidenceError(f"{label}: expected finite positive quantity")
    return number


def load_rows(path: str | Path) -> tuple[list[dict], str]:
    """Parse immutable *annual* observations. Reject missing/extra/duplicate rows."""
    raw = Path(path).read_bytes()
    try:
        stream = io.StringIO(raw.decode("utf-8-sig"))
    except UnicodeError as exc:
        raise EvidenceError("CSV must use UTF-8") from exc
    reader = csv.DictReader(stream)
    if tuple(reader.fieldnames or ()) != COLUMNS:
        raise EvidenceError("Unexpected column schema; expected published annual measurements")
    parsed = []
    for row in reader:
        if None in row or set(row) != set(COLUMNS):
            raise EvidenceError("Malformed CSV row or additional columns")
        year = _positive_int(row["year"], "year")
        running = _positive_int(row["running_hours"], f"{year} running hours")
        volume = _positive_int(row["landfill_gas_recovered_m3"], f"{year} gas")
        electricity = _positive_float(row["electricity_generated_mwh"], f"{year} electricity")
        heat = _positive_float(row["heat_generated_mwh"], f"{year} heat")
        calendar_hours = 8784 if calendar.isleap(year) else 8760
        if running > calendar_hours:
            raise EvidenceError(f"{year}: running hours exceed calendar hours")
        if electricity > ELECTRIC_RATING_MW * running + 1e-7:
            raise EvidenceError(f"{year}: annual generation exceeds rated electrical output during reported running hours")
        if heat > THERMAL_RATING_MW * running + 1e-7:
            raise EvidenceError(f"{year}: annual heat exceeds rated thermal output during reported running hours")
        parsed.append({
            "year": year,
            "running_hours": running,
            "landfill_gas_recovered_m3": volume,
            "electricity_generated_mwh": electricity,
            "heat_generated_mwh": heat,
            "calendar_hours": calendar_hours,
            "calendar_running_fraction": running / calendar_hours,
            "mean_electrical_mw_when_running": electricity / running,
            "mean_thermal_mw_when_running": heat / running,
            "annual_mean_electrical_fraction_of_nameplate_while_running":
                electricity / (ELECTRIC_RATING_MW * running),
            "annual_mean_thermal_fraction_of_nameplate_while_running":
                heat / (THERMAL_RATING_MW * running),
        })
    observed_years = [r["year"] for r in parsed]
    if observed_years != list(EXPECTED_YEARS):
        raise EvidenceError("Exactly one chronological record per year 2012-2022 is required")
    return parsed, hashlib.sha256(raw).hexdigest()


def audit_annual_chp(path: str | Path) -> dict:
    """Benchmark published evidence, preserving discrepancies instead of hiding them.

    Does NOT estimate ramp rate, minimum on-state generation, storage sizing,
    hourly heat demand, generator efficiency or metered grid export.
    """
    rows, sha = load_rows(path)
    if sha != PUBLISHED_CSV_SHA256:
        raise EvidenceError(
            "Source extract SHA256 does not match the pinned, attributed "
            "2012-2022 publication transcription"
        )
    periods = {}
    for label, selected in (
        ("2012-2017", rows[:6]), ("2018-2022", rows[6:])
    ):
        averages = {
            key: mean(r[key] for r in selected)
            for key in COLUMNS if key != "year"
        }
        periods[label] = {
            "years": [r["year"] for r in selected],
            "arithmetic_annual_means": averages,
            "reported_period_average_gas_heating_value_kj_per_m3":
                PERIOD_GAS_HEATING_VALUE_KJ_M3[label],
            "mean_electric_output_mw_while_running":
                sum(r["electricity_generated_mwh"] for r in selected) /
                sum(r["running_hours"] for r in selected),
            "mean_heat_output_mw_while_running":
                sum(r["heat_generated_mwh"] for r in selected) /
                sum(r["running_hours"] for r in selected),
        }
    computed_post_gas = periods["2018-2022"]["arithmetic_annual_means"]["landfill_gas_recovered_m3"]
    pre = periods["2012-2017"]["arithmetic_annual_means"]
    post = periods["2018-2022"]["arithmetic_annual_means"]
    discrepancies = [{
        "code": "PUBLISHED_2018_2022_GAS_MEAN_MISMATCH",
        "source_location": "Table 3 Average / Table 8",
        "as_published_m3_per_year": REPORTED_AVERAGES["2018-2022"]["landfill_gas_recovered_m3"],
        "recomputed_from_published_annual_rows_m3_per_year": computed_post_gas,
        "difference_recomputed_minus_published_m3_per_year":
            computed_post_gas - REPORTED_AVERAGES["2018-2022"]["landfill_gas_recovered_m3"],
    }]
    conventional_gas_increase_pct = 100 * (post["landfill_gas_recovered_m3"] / pre["landfill_gas_recovered_m3"] - 1)
    if abs(conventional_gas_increase_pct - 29.5) > 0.1:
        discrepancies.append({
            "code": "PUBLISHED_GAS_INCREASE_PERCENT_UNREPRODUCIBLE",
            "source_location": "Abstract / Conclusions",
            "source_reported_percent": 29.5,
            "conventional_change_from_annual_table_percent": conventional_gas_increase_pct,
        })
    conventional_electric_change_pct = 100 * (
        post["electricity_generated_mwh"] / pre["electricity_generated_mwh"] - 1
    )
    if abs(conventional_electric_change_pct - 42.78) > 0.1:
        discrepancies.append({
            "code": "PUBLISHED_ELECTRICITY_INCREASE_DENOMINATOR_DIFFERS",
            "source_location": "Conclusions",
            "source_reported_percent": 42.78,
            "conventional_change_relative_to_earlier_period_percent":
                conventional_electric_change_pct,
            "change_relative_to_later_period_percent":
                100 * (post["electricity_generated_mwh"] - pre["electricity_generated_mwh"]) /
                post["electricity_generated_mwh"],
        })
    return {
        "status": "PASS_WITH_PUBLISHED_SOURCE_DISCREPANCIES",
        "evidence_level": "PUBLISHED_SITE_ANNUAL_AGGREGATES_ONLY",
        "doi": DOI,
        "source_url": SOURCE_URL,
        "source_tables": ["1", "2", "3", "8"],
        "plant_fuel": "LANDFILL_GAS_NOT_ANAEROBIC_DIGESTER_GAS",
        "observations_are": "annual_generation_running_hours_recovered_gas_not_hourly_scada",
        "input_csv_sha256": sha,
        "nameplate": {"electric_mw": ELECTRIC_RATING_MW,
                      "thermal_mw": THERMAL_RATING_MW},
        "annual_observations": rows,
        "periods": periods,
        "published_reported_averages_unchanged": REPORTED_AVERAGES,
        "documented_source_discrepancies": discrepancies,
        "year_2020_calendar_hours": 8784,
        "no_direct_validation_of": [
            "hourly_or_quarterhourly_dispatch", "minimum_stable_load",
            "engine_ramp_rate", "gas_buffer_volume", "heat_demand",
            "annual_gas_recovered_equal_to_engine_fuel_consumed",
            "normalized_gas_volume_basis", "net_grid_export",
            "electric_or_thermal_conversion_efficiency_at_each_operating_point",
            "auction_awards", "realized_profit",
        ],
        "integration_boundary": (
            "Treat rated electric and thermal capacities as published equipment facts. "
            "All derived running-time power levels are aggregate averages, NOT observed "
            "minimum outputs or operating limits. Never inject them as ramp/minimum "
            "or heat-demand parameters into the contract-dispatch MILP."
        ),
    }
