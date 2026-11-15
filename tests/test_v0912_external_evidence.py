"""v0.9.12 adversarial provenance and independent annual CHP audit oracles.

No sources are silently interpolated. No original 2020 bid-time release
timestamp or real-site hourly CHP telemetry is invented from aggregates.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from biogasflex.evidence_v0912 import (
    ROOT, EvidenceError, _pinned_text,
    audit_market_archive, audit_external_annual_chp,
    require_operational_validation, run_evidence_audit,
)
MANIFEST=ROOT/"examples/v0912_external_evidence.json"


def metadata():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def temporary_repository(tempdir, manifest):
    """Clone only three sources, with an independent local SHA manifest."""
    root=Path(tempdir)
    files=[
        manifest["market_archive"]["path"],
        manifest["measured_chp_reference"]["csv_path"],
        manifest["hypothetical_chp_config"],
    ]
    checks=[]
    for name in files:
        orig=ROOT/name
        target=root/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(orig.read_bytes())
        checks.append(f"{sha256(target.read_bytes()).hexdigest()}  {name}")
    (root/"SHA256SUMS.txt").write_text("\n".join(sorted(checks))+"\n",encoding="utf-8")
    (root/"examples/v0912_external_evidence.json").write_text(
        json.dumps(manifest),encoding="utf-8")
    return root


class ExternalEvidenceTests(unittest.TestCase):
    def test_pinned_market_grid_retrospective_not_historic_bidtime(self):
        x=metadata()
        result=audit_market_archive(ROOT,x["market_archive"])
        self.assertEqual(result["observed_intervals"],24)
        self.assertEqual(result["zone"],"SE3")
        self.assertAlmostEqual(result["mean_price_eur_mwh"],167.71/24,places=9)
        self.assertFalse(result["this_archived_copy_existed_before_decision"])
        self.assertFalse(result["per_price_original_publication_event_proven"])
        self.assertFalse(result["asof_price_forecast_evidence_eligible"])
        self.assertEqual(result["source_dataset_record_publication_date"],"2026-04-09")

    def test_published_chp_annual_electric_and_thermal_oracles(self):
        x=metadata()
        r=audit_external_annual_chp(ROOT,x["measured_chp_reference"],
                                    x["hypothetical_chp_config"])
        self.assertEqual(r["annual_record_count"],11)
        self.assertEqual(r["source_plant_electric_rating_mw"],0.44)
        self.assertEqual(r["source_plant_thermal_rating_mw"],0.52)
        self.assertAlmostEqual(r["periods"]["2012-2017"]["mean_annual_gas_recovered_m3"],910533)
        self.assertAlmostEqual(r["periods"]["2012-2017"]["mean_annual_electricity_mwh"],1219.3916666666667)
        self.assertAlmostEqual(r["periods"]["2012-2017"]["mean_annual_heat_mwh"],1615.935)
        self.assertAlmostEqual(r["periods"]["2018-2022"]["mean_annual_running_hours"],7848.2)
        self.assertAlmostEqual(r["periods"]["2018-2022"]["mean_annual_electricity_mwh"],2131.222)
        self.assertAlmostEqual(r["periods"]["2018-2022"]["mean_annual_heat_mwh"],2799.444)
        self.assertAlmostEqual(r["periods"]["2018-2022"]["running_time_weighted_electric_mw"],.2715555159144772)
        self.assertAlmostEqual(r["periods"]["2018-2022"]["electric_nameplate_fraction_during_running"],.6171716270783572)

    def test_publication_average_gas_discrepancy_not_automatically_rewritten(self):
        x=metadata()
        r=audit_external_annual_chp(ROOT,x["measured_chp_reference"],
                                    x["hypothetical_chp_config"])
        self.assertTrue(r["source_table_mean_discrepancy_flag"])
        self.assertEqual(r["published_2018_2022_gas_mean_m3"],1291515)
        self.assertAlmostEqual(r["recomputed_2018_2022_gas_mean_m3"],1267253.2)
        self.assertAlmostEqual(r["source_published_mean_discrepancy_m3_per_year"],24261.8)

    def test_actual_annual_operating_power_not_engine_peak_or_minimum(self):
        r=run_evidence_audit(MANIFEST)["independent_chp_reference"]
        for row in r["annual_summary_series"]:
            self.assertLess(row["annual_mean_during_running_electric_mw"],.44)
            self.assertLess(row["annual_mean_during_running_thermal_mw"],.52)
            self.assertGreater(row["electric_fraction_of_nameplate_while_running"],0)
            self.assertLess(row["electric_fraction_of_nameplate_while_running"],1)
        self.assertFalse(r["hourly_ramp_dwell_and_startup_validated"])
        self.assertFalse(r["hourly_minimum_stable_power_validated"])
        self.assertFalse(r["fuel_LHV_and_electrical_efficiency_validated_for_model"])
        self.assertFalse(r["electricity_at_grid_point_metered_for_model"])

    def test_actual_source_is_an_independent_other_plant_not_a_calibration(self):
        r=run_evidence_audit(MANIFEST)
        c=r["independent_chp_reference"]
        self.assertEqual(c["hypothetical_model_rating_mw"],.8)
        self.assertEqual(c["source_plant_electric_rating_mw"],.44)
        self.assertEqual(c["source_chp_fuel"],"LANDFILL_GAS")
        self.assertFalse(c["same_plant_as_hypothetical_dispatch"])
        self.assertFalse(r["plant_specific_hourly_chp_envelope_validated"])
        self.assertFalse(r["real_contract_dispatch_eligible"])

    def test_real_operation_gate_fails_closed(self):
        r=run_evidence_audit(MANIFEST)
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation(r)

    def test_no_future_source_record_retroactive_asof(self):
        m=metadata()
        m["market_archive"]["source_dataset_first_publication_date"]="2019-04-09"
        with self.assertRaisesRegex(EvidenceError,"backdated"):
            audit_market_archive(ROOT,m["market_archive"])
        m=metadata()
        m["market_archive"]["snapshot_retrieval_date"]="2020-03-01"
        with self.assertRaisesRegex(EvidenceError,"backdated"):
            audit_market_archive(ROOT,m["market_archive"])

    def test_fake_original_price_publication_proof_is_rejected(self):
        m=metadata()
        m["market_archive"]["original_per_interval_publication_proof"]="2020-03-31T12:45:00Z"
        with self.assertRaisesRegex(EvidenceError,"elevated as-of"):
            audit_market_archive(ROOT,m["market_archive"])

    def test_fake_market_asof_preauction_date_is_rejected(self):
        m=metadata()
        m["market_archive"]["preauction_decision_utc"]="2020-04-01T20:00:00Z"
        with self.assertRaisesRegex(EvidenceError,"previous Stockholm"):
            audit_market_archive(ROOT,m["market_archive"])

    def test_naive_and_local_offset_market_decision_time_rejected(self):
        for bad in ("2020-03-31T09:00:00", "2020-03-31T11:00:00+02:00"):
            m=metadata()
            m["market_archive"]["preauction_decision_utc"]=bad
            with self.subTest(ts=bad),self.assertRaisesRegex(EvidenceError,"UTC"):
                audit_market_archive(ROOT,m["market_archive"])

    def test_wrong_zone_and_price_unit_fail(self):
        for field, bad in (("bidding_zone","SE4"),("price_unit","SEK-kWh"),
                           ("resource_id","not-svk-resource")):
            m=metadata()
            m["market_archive"][field]=bad
            with self.subTest(field=field),self.assertRaisesRegex(EvidenceError,"source"):
                audit_market_archive(ROOT,m["market_archive"])

    def test_source_sha256_price_tamper_fails(self):
        m=metadata()
        with tempfile.TemporaryDirectory() as tmp:
            root=temporary_repository(tmp,m)
            name=root/m["market_archive"]["path"]
            name.write_bytes(name.read_bytes()+b"tamper")
            with self.assertRaisesRegex(EvidenceError,"SHA256_SOURCE_TAMPERED"):
                audit_market_archive(root,m["market_archive"])

    def test_source_sha256_chp_tamper_fails(self):
        m=metadata()
        with tempfile.TemporaryDirectory() as tmp:
            root=temporary_repository(tmp,m)
            name=root/m["measured_chp_reference"]["csv_path"]
            name.write_bytes(name.read_bytes()+b"tamper")
            with self.assertRaisesRegex(EvidenceError,"SHA256_SOURCE_TAMPERED"):
                audit_external_annual_chp(root,m["measured_chp_reference"],
                                         m["hypothetical_chp_config"])

    def test_repinning_gap_or_duplicate_hour_still_fails_calendar_audit(self):
        m=metadata()
        with tempfile.TemporaryDirectory() as tmp:
            root=temporary_repository(tmp,m)
            path=m["market_archive"]["path"]
            file=root/path
            lines=file.read_text().splitlines()
            lines[2]=lines[1]  # duplicate first hour, omit second
            rewritten="\n".join(lines)+"\n"
            file.write_text(rewritten,encoding="utf-8")
            h=sha256(file.read_bytes()).hexdigest()
            m["market_archive"]["sha256"]=h
            pins=(root/"SHA256SUMS.txt").read_text()
            old=metadata()["market_archive"]["sha256"]
            (root/"SHA256SUMS.txt").write_text(pins.replace(old,h))
            with self.assertRaisesRegex(EvidenceError,"duplicated|Missing"):
                audit_market_archive(root,m["market_archive"])

    def test_repinning_nonconsecutive_chp_years_still_fails(self):
        m=metadata()
        with tempfile.TemporaryDirectory() as tmp:
            root=temporary_repository(tmp,m)
            path=m["measured_chp_reference"]["csv_path"]
            file=root/path
            content=file.read_text()
            content=content.replace("2019,7852,","2018,7852,")
            file.write_text(content,encoding="utf-8")
            h=sha256(file.read_bytes()).hexdigest()
            old=m["measured_chp_reference"]["csv_sha256"]
            m["measured_chp_reference"]["csv_sha256"]=h
            (root/"SHA256SUMS.txt").write_text(
                (root/"SHA256SUMS.txt").read_text().replace(old,h),encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError,"chronologically complete"):
                audit_external_annual_chp(root,m["measured_chp_reference"],
                                          m["hypothetical_chp_config"])

    def test_manipulated_source_reported_mean_is_rejected(self):
        m=metadata()
        m["measured_chp_reference"]["originally_reported_2018_2022_gas_mean_m3_per_year"]=1267253.2
        with self.assertRaisesRegex(EvidenceError,"reported Table 3 average"):
            audit_external_annual_chp(ROOT,m["measured_chp_reference"],
                                     m["hypothetical_chp_config"])

    def test_fake_paper_identity_or_elevated_temporal_resolution_rejected(self):
        for key, value in (("doi","10.9999/fake"),("licence","CLOSED"),
                           ("temporal_resolution","SUBSECOND_REAL_TIME"),
                           ("site_fuel_class","SAME_SITE_VERIFIED")):
            m=metadata()
            m["measured_chp_reference"][key]=value
            with self.subTest(key=key),self.assertRaisesRegex(EvidenceError,"Source study identity"):
                audit_external_annual_chp(ROOT,m["measured_chp_reference"],
                                         m["hypothetical_chp_config"])

    def test_there_is_no_independently_verified_operational_ready_option(self):
        m=metadata()
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation({
              **run_evidence_audit(MANIFEST),
              "operational_price_asof_validated":True,
              "plant_specific_hourly_chp_envelope_validated":False,
            })
        self.assertEqual(m["schema"],"biogasflex_external_evidence_v0912")

    def test_forged_boolean_claims_never_turn_source_audit_into_operational_certificate(self):
        r=run_evidence_audit(MANIFEST)
        forged=dict(r)
        forged.update({
            "operational_price_asof_validated":True,
            "plant_specific_hourly_chp_envelope_validated":True,
            "real_contract_dispatch_eligible":True,
        })
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation(forged)
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation({"version":"unknown","real_contract_dispatch_eligible":True})

    def test_cli_evidence_audit_and_real_mode_block(self):
        p=subprocess.run([sys.executable,"-m","biogasflex","evidence-audit"],
                         cwd=ROOT,capture_output=True,text=True,timeout=45)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout)
        self.assertEqual(data["observed_market_intervals"],24)
        self.assertEqual(data["external_chp_annual_years"],11)
        self.assertFalse(data["real_contract_dispatch_eligible"])
        p=subprocess.run([sys.executable,"-m","biogasflex","contract-dispatch",
                          "--require-operational-validation"],
                         cwd=ROOT,capture_output=True,text=True,timeout=45)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("REAL_OPERATIONAL_VALIDATION_BLOCKED",p.stderr+p.stdout)

    def test_legacy_synthetic_contract_dispatch_remains_available(self):
        p=subprocess.run([sys.executable,"-m","biogasflex","contract-dispatch"],
                         cwd=ROOT,capture_output=True,text=True,timeout=45)
        self.assertEqual(p.returncode,0,p.stderr)
        data=json.loads(p.stdout)
        self.assertEqual(data["phase"],"POST_CLEARING_EXOGENOUS_AWARD_HARD_CONTRACT_MATCHED")


if __name__ == "__main__":
    unittest.main()
