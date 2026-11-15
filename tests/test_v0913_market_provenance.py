"""v0.9.13 chronological Svk source provenance against existing annual CHP source.

The historical price snapshot was retrieved from a dataset first released in
2026, so its 2020 original bid-time publication is NOT verified. The original
2012–2022 CHP study already appears in v0.9.12; no data duplication.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from biogasflex.market_provenance_v0913 import (
    ROOT, EvidenceError, audit_market_archive,
    run_market_source_audit, require_operational_validation,
)
MANIFEST=ROOT/"examples/v0913_market_provenance.json"


def input_data():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


class MarketProvenanceTests(unittest.TestCase):
    def test_original_svk_price_integrity_and_24_hour_grid(self):
        m=input_data()
        p=audit_market_archive(ROOT,m["market_archive"])
        self.assertEqual(p["status"],"SOURCE_SHA256_AND_PRICE_GRID_VERIFIED")
        self.assertEqual(p["observed_intervals"],24)
        self.assertAlmostEqual(p["mean_price_eur_mwh"],167.71/24,places=8)
        self.assertEqual(p["source_csv_sha256"],"560415b0b38fd764c64bf40c182737d60b94838a39db677da96f7649ba4661b0")
        self.assertEqual(p["zone"],"SE3")

    def test_archived_2026_record_does_not_prove_2020_bidtime_knowledge(self):
        r=run_market_source_audit(MANIFEST)
        market=r["market_archive"]
        self.assertEqual(market["source_dataset_record_publication_date"],"2026-04-09")
        self.assertEqual(market["snapshot_retrieval_date"],"2026-11-05")
        self.assertEqual(market["historical_preauction_decision_utc"],"2020-03-31T09:00:00+00:00")
        self.assertFalse(market["this_archived_copy_existed_before_decision"])
        self.assertFalse(market["per_price_original_publication_event_proven"])
        self.assertFalse(market["asof_price_forecast_evidence_eligible"])
        self.assertFalse(market["historical_bidtime_market_visibility_confirmed"])

    def test_reuse_v0912_source_single_publication_not_duplicate_study(self):
        r=run_market_source_audit(MANIFEST)
        chp=r["published_independent_annual_chp"]
        self.assertEqual(chp["years"],11)
        self.assertEqual(chp["doi"],"10.3390/en16052180")
        self.assertEqual(chp["rated_electric_mw"],.44)
        self.assertEqual(chp["rated_thermal_mw"],.52)
        self.assertEqual(chp["source_csv_sha256"],
                         "ce018fd8ca3746a393c6a73c30321e8deb5c09ae8bef0497ab59b15bcbc33d10")
        self.assertNotEqual(r["hypothetical_dispatch_electric_rating_mw"],
                            chp["rated_electric_mw"])
        self.assertFalse(r["same_chp_site_as_published_source"])
        self.assertFalse(chp["hourly_plant_calibration"])
        self.assertTrue(chp["source_reported_average_discrepancies"])

    def test_bogus_market_publication_utc_and_decision_clock_rejected(self):
        for key,val in (
            ("source_dataset_first_publication_date","2020-03-31"),
            ("snapshot_retrieval_date","2020-03-31"),
            ("original_per_interval_publication_proof","2020-03-31T12:45:00Z"),
            ("permitted_claim","VERIFIED_PRE_AUCTION_PRICE"),
            ("preauction_decision_utc","2020-04-01T09:00:00Z"),
            ("preauction_decision_utc","2020-03-31T11:00:00+02:00"),
            ("preauction_decision_utc","2020-03-31T09:00:00"),
        ):
            m=input_data()
            m["market_archive"][key]=val
            with self.subTest(key=key,val=val),self.assertRaises(EvidenceError):
                audit_market_archive(ROOT,m["market_archive"])

    def test_forged_source_and_bidding_zone_rejected(self):
        for k,val in (
            ("bidding_zone","SE4"),("price_unit","SEK/kWh"),
            ("source_provider","not Svk"),("resource_id","arbitrary resource"),
            ("source_url","https://example.com/forged"),
            ("sha256","0"*64),
        ):
            m=input_data()
            m["market_archive"][k]=val
            with self.subTest(k=k),self.assertRaises(EvidenceError):
                audit_market_archive(ROOT,m["market_archive"])

    def test_original_price_mutation_breaks_sha256_pin(self):
        m=input_data()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=m["market_archive"]["path"]
            dest=root/path
            dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes((ROOT/path).read_bytes()+b"tampered")
            (root/"SHA256SUMS.txt").write_text(
                m["market_archive"]["sha256"]+"  "+path+"\n",encoding="utf8")
            with self.assertRaisesRegex(EvidenceError,"SHA256_SOURCE_TAMPERED"):
                audit_market_archive(root,m["market_archive"])

    def test_repinning_duplicate_utc_hour_still_fails_calendar_oracle(self):
        m=input_data()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            path=m["market_archive"]["path"]
            file=root/path
            file.parent.mkdir(parents=True,exist_ok=True)
            lines=(ROOT/path).read_text().splitlines()
            lines[2]=lines[1]
            file.write_text("\n".join(lines)+"\n",encoding="utf-8")
            digest=sha256(file.read_bytes()).hexdigest()
            m["market_archive"]["sha256"]=digest
            (root/"SHA256SUMS.txt").write_text(
                digest+"  "+path+"\n",encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError,"duplicated|overlapping|Missing"):
                audit_market_archive(root,m["market_archive"])

    def test_market_source_schema_is_strict(self):
        m=input_data()
        for key,val in (("schema","unsupported_source"),
                        ("published_chp_reference_path","data/example_fake.csv"),
                        ("hypothetical_chp_config","examples/fake_chp.json")):
            changed=dict(m)
            changed[key]=val
            with self.subTest(key=key),self.assertRaises(EvidenceError):
                run_market_source_audit_from_dict(changed)

    def test_real_market_and_site_readiness_rejected(self):
        r=run_market_source_audit(MANIFEST)
        self.assertEqual(r["version"],"0.9.13")
        self.assertFalse(r["market_asof_for_2020_preauction_verified"])
        self.assertFalse(r["site_specific_hourly_operating_limits_verified"])
        self.assertFalse(r["operational_contract_dispatch_eligible"])
        self.assertEqual(len(r["operational_blockers"]),4)
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation(r)

    def test_manual_status_flag_flip_cannot_forge_real_eligibility(self):
        r=run_market_source_audit(MANIFEST)
        r["operational_contract_dispatch_eligible"]=True
        r["market_asof_for_2020_preauction_verified"]=True
        r["site_specific_hourly_operating_limits_verified"]=True
        with self.assertRaisesRegex(EvidenceError,"REAL_OPERATIONAL_VALIDATION_BLOCKED"):
            require_operational_validation(r)

    def test_cli_market_provenance_and_strict_contract_gate(self):
        a=subprocess.run([sys.executable,"-m","biogasflex","market-provenance"],
                         cwd=ROOT,capture_output=True,text=True,timeout=40)
        self.assertEqual(a.returncode,0,a.stderr)
        r=json.loads(a.stdout)
        self.assertEqual(r["observed_price_intervals"],24)
        self.assertEqual(r["external_annual_chp_years"],11)
        self.assertFalse(r["operational_contract_dispatch_eligible"])
        b=subprocess.run([sys.executable,"-m","biogasflex","contract-dispatch",
                          "--require-operational-validation"],
                         cwd=ROOT,capture_output=True,text=True,timeout=40)
        self.assertNotEqual(b.returncode,0)
        self.assertIn("REAL_OPERATIONAL_VALIDATION_BLOCKED",b.stderr+b.stdout)

    def test_existing_annual_and_contract_dispatch_cli_unchanged(self):
        for command in ("annual-chp-evidence","contract-dispatch"):
            p=subprocess.run([sys.executable,"-m","biogasflex",command],
                             cwd=ROOT,capture_output=True,text=True,timeout=40)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertTrue(json.loads(p.stdout))


def run_market_source_audit_from_dict(data):
    with tempfile.TemporaryDirectory() as t:
        path=Path(t)/"manifest.json"
        path.write_text(json.dumps(data),encoding="utf8")
        return run_market_source_audit(path)


if __name__=="__main__":
    unittest.main()
