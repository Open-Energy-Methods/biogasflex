"""Independent no-biogasflex/no-solver v0.9.15 metering-oracle witness.

A Decimal arithmetic second implementation of the synthetic source
measurements; a separate subprocess runs the public telemetry-qa CLI.
This is NOT a physical calibration or independent human review.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/"examples/v0915_synthetic_chp_metering.csv"
META=ROOT/"examples/v0915_synthetic_acquisition_manifest.json"
EXPECTED_HASH="9fe9b0d49311c683e7c741d9a4bddf881f5da3870ca8e0207c3d99bb11f72d8f"

def independent_audit() -> dict:
    raw=RAW.read_bytes()
    assert sha256(raw).hexdigest()==EXPECTED_HASH
    manifest=json.loads(META.read_text(encoding="utf8"))
    assert manifest["evidence_class"]=="SYNTHETIC_DEMONSTRATION_ONLY"
    assert manifest["raw_csv_sha256"]==EXPECTED_HASH
    assert manifest["site_pseudonym"]=="NONE_SYNTHETIC"
    assert len(manifest["instrument_registry"])==11
    assert all(i["calibration_status"]=="SYNTHETIC_UNCALIBRATED"
               and i["certificate_ref"] is None for i in manifest["instrument_registry"])
    with RAW.open(newline="",encoding="utf8") as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==4
    d=lambda row,key:Decimal(row[key])
    gen=grid=heat=use=produced=Decimal(0)
    previous=None
    for r in rows:
        start=datetime.fromisoformat(r["interval_start_utc"].replace("Z","+00:00"))
        end=datetime.fromisoformat(r["interval_end_utc"].replace("Z","+00:00"))
        assert end-start==timedelta(minutes=15)
        if previous is not None:
            assert start==previous
        previous=end
        assert r["quality_flag"]=="GOOD"
        assert d(r,"max_clock_offset_s") <= 2
        assert d(r,"generator_electric_kwh")==(
            d(r,"net_grid_export_kwh")+
            d(r,"site_electric_consumption_kwh")+
            d(r,"auxiliary_electric_consumption_kwh"))
        assert d(r,"produced_gas_nm3_dry")-d(r,"engine_gas_nm3_dry")-(
            d(r,"flared_gas_nm3_dry")) == (
            d(r,"buffer_gas_end_nm3_dry")-
            d(r,"buffer_gas_start_nm3_dry"))
        fuel=d(r,"engine_gas_nm3_dry")*d(r,"fuel_lhv_mj_per_nm3_dry")/Decimal("3.6")
        assert d(r,"generator_electric_kwh")+d(r,"useful_recovered_heat_kwh") < fuel
        assert d(r,"generator_electric_kwh") <= Decimal("80")*Decimal(".25")
        gen+=d(r,"generator_electric_kwh")
        grid+=d(r,"net_grid_export_kwh")
        heat+=d(r,"useful_recovered_heat_kwh")
        use+=d(r,"engine_gas_nm3_dry")
        produced+=d(r,"produced_gas_nm3_dry")
    assert (gen,grid,heat,use,produced)==(
        Decimal(42),Decimal(28),Decimal(50),Decimal(21),Decimal(21))
    p=subprocess.run(
        [sys.executable,"-m","biogasflex","telemetry-qa",
         "--manifest",str(META)],
        cwd=ROOT,text=True,capture_output=True,check=True,timeout=45,
    )
    cli=json.loads(p.stdout)
    assert cli["intervals_checked"]==4
    assert cli["raw_sha256"]==EXPECTED_HASH
    assert cli["data_quality_screen_passed"]
    assert not cli["physical_validation_performed"]
    return {
        "status":"PASS_INDEPENDENT_SYNTHETIC_METER_QA_WITNESS",
        "raw_source_sha256":EXPECTED_HASH,
        "independent_decimal_energy_meter_kwh":str(gen),
        "independent_decimal_signed_export_kwh":str(grid),
        "independent_decimal_useful_heat_kwh":str(heat),
        "independent_decimal_engine_gas_nm3":str(use),
        "raw_interval_count":len(rows),
        "instrument_metadata_entries":11,
        "plant_data_recorded":False,
        "manufacturer_curve_calibrated":False,
        "calibration_certificates_verified":False,
    }

if __name__=="__main__":
    print(json.dumps(independent_audit(),indent=2))
