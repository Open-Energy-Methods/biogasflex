"""Independent standard-library arithmetic witness for Ciula 2023 Tables 2-3.

Does not import biogasflex, optimization or the production evidence parser.
A deliberate source-paper discrepancy is a documented PASS WITH WARNINGS,
never an unreported correction to a published value.
"""
from __future__ import annotations
import csv
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/observed/ciula_2023_landfill_chp_annual.csv"


def run(path: Path = SOURCE) -> dict:
    with path.open(newline="", encoding="utf8") as handle:
        records = list(csv.DictReader(handle))
    if len(records) != 11 or [int(x["year"]) for x in records] != list(range(2012, 2023)):
        raise AssertionError("External CHP evidence year coverage changed")
    for row in records:
        h = int(row["running_hours"])
        volume = int(row["landfill_gas_recovered_m3"])
        electric = float(row["electricity_generated_mwh"])
        heat = float(row["heat_generated_mwh"])
        if min(h, volume, electric, heat) <= 0 or electric > .44*h or heat > .52*h:
            raise AssertionError(f"Out-of-rating or nonpositive annual row: {row['year']}")
    period1, period2 = records[:6], records[6:]
    avg = lambda rows, key: mean(float(item[key]) for item in rows)
    assert abs(avg(period1, "landfill_gas_recovered_m3") - 910533) < 1e-6
    assert abs(avg(period2, "landfill_gas_recovered_m3") - 1267253.2) < 1e-6
    assert abs(avg(period1, "electricity_generated_mwh") - 1219.3916666666667) < 1e-6
    assert abs(avg(period2, "electricity_generated_mwh") - 2131.222) < 1e-6
    assert abs(avg(period2, "heat_generated_mwh") - 2799.444) < 1e-6
    published_mean = 1291515
    assert abs(avg(period2, "landfill_gas_recovered_m3") - published_mean) > 24000
    conventional_electric_change_pct = 100 * (
        avg(period2, "electricity_generated_mwh") /
        avg(period1, "electricity_generated_mwh") - 1)
    assert 74 < conventional_electric_change_pct < 75
    return {
        "status": "PASS_WITH_DOCUMENTED_SOURCE_DISCREPANCIES",
        "recomputed_2018_2022_gas_average_m3_year": avg(period2, "landfill_gas_recovered_m3"),
        "source_reported_gas_average_m3_year": published_mean,
        "source_reported_electricity_increase_pct": 42.78,
        "conventional_earlier_period_denominator_electricity_change_pct":
            conventional_electric_change_pct,
        "source_type": "annual_recovered_landfill_gas_and_chp_outputs",
        "hourly_plant_calibration": False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run(), indent=2, allow_nan=False))
