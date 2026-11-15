"""v0.9.15 metering data contract: adversarial clock, gas, electrical and traceability tests.

Every "real" test record is algorithmically fabricated INSIDE a TemporaryDirectory.
It tests schema-only behavior and is NEVER evidence of a physical installation.
"""
from __future__ import annotations

import copy
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.telemetry_acquisition_v0915 import (
    COLUMNS,DEFAULT_MANIFEST,DEMO_DIGEST,TelemetryQAError,
    _register,audit_telemetry,
)
SOURCE=ROOT/"examples/v0915_synthetic_chp_metering.csv"


class CHPTimeResolvedAcquisitionQA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.demo=json.loads(DEFAULT_MANIFEST.read_text(encoding="utf8"))
        with SOURCE.open(newline="",encoding="utf8") as f:
            cls.frozen_rows=list(csv.DictReader(f))

    def test_frozen_synthetic_fixture_passes_without_calibration_claim(self):
        x=audit_telemetry()
        self.assertEqual(x["status"],"PASS_SYNTHETIC_SCHEMA_AND_BALANCE_QA_NO_PHYSICAL_VALIDATION")
        self.assertEqual(x["interval_count"],4)
        self.assertEqual(x["measurement_channels"],11)
        self.assertEqual(x["raw_sha256"],DEMO_DIGEST)
        self.assertEqual(x["maximum_absolute_electric_balance_residual_kwh"],0)
        self.assertEqual(x["maximum_absolute_gas_volume_residual_nm3_dry"],0)
        self.assertFalse(x["real_plant_model_validation_performed"])
        self.assertFalse(x["calibration_certificates_cryptographically_verified"])
        self.assertFalse(x["uncertainty_is_gum_combined_standard_uncertainty"])
        self.assertFalse(x["high_rate_startup_ramp_evidence_available"])

    def test_synthetic_gas_lhv_units_and_efficiency(self):
        result=audit_telemetry()
        first=result["intervals"][0]
        self.assertAlmostEqual(first["calculated_engine_fuel_lhv_kwh"],5*20/3.6,places=11)
        self.assertAlmostEqual(first["apparent_electric_lhv_ratio"],.36,places=11)
        self.assertAlmostEqual(sum(x["measured_generator_electric_kwh"] for x in result["intervals"]),42.)
        self.assertAlmostEqual(sum(x["measured_grid_export_signed_kwh"] for x in result["intervals"]),28.)
        self.assertNotEqual(first["measured_generator_electric_kwh"],
                            first["measured_grid_export_signed_kwh"])

    def test_demo_cannot_be_relabelled_as_real_site(self):
        altered=copy.deepcopy(self.demo)
        altered["evidence_class"]="REAL_SITE_DATA_UNVERIFIED"
        with self.assertRaises(TelemetryQAError):
            _register(altered)
        altered=copy.deepcopy(self.demo)
        altered["equipment_identity_verified"]=True
        with self.assertRaises(TelemetryQAError):
            _register(altered)

    def test_demo_hash_must_match_pinned_original(self):
        altered=copy.deepcopy(self.demo)
        altered["raw_csv_sha256"]="0"*64
        with self.assertRaisesRegex(TelemetryQAError,"Synthetic fixture"):
            _register(altered)

    def test_sensor_registry_missing_wrong_units_or_zero_uncertainty_fails(self):
        a=copy.deepcopy(self.demo);a["instrument_registry"].pop()
        with self.assertRaisesRegex(TelemetryQAError,"11 required"):
            _register(a)
        a=copy.deepcopy(self.demo);a["instrument_registry"][0]["unit"]="MW"
        with self.assertRaisesRegex(TelemetryQAError,"unit"):
            _register(a)
        a=copy.deepcopy(self.demo)
        a["instrument_registry"][0]["standard_u_fraction"]=0
        with self.assertRaisesRegex(TelemetryQAError,"uncertainty"):
            _register(a)

    def test_demonstration_calibration_claim_rejected(self):
        a=copy.deepcopy(self.demo)
        a["instrument_registry"][0]["calibration_status"]="ISO17025_CALIBRATED"
        with self.assertRaisesRegex(TelemetryQAError,"impersonate"):
            _register(a)
        a=copy.deepcopy(self.demo);a["all_instruments_independently_calibrated_and_reviewed"]=True
        with self.assertRaises(TelemetryQAError):
            _register(a)
        a=copy.deepcopy(self.demo);a["covariance_matrix_authentic_and_reviewed"]=True
        with self.assertRaises(TelemetryQAError):
            _register(a)

    def test_no_real_ramp_evidence_can_be_claimed(self):
        a=copy.deepcopy(self.demo)
        a["high_rate_ramp_and_startup_event_log_available"]=True
        with self.assertRaises(TelemetryQAError):
            _register(a)

    def _make_real_tmp(self, root: Path, mutator=None):
        # Entirely artificial test-only 96-row series; not an acquired real
        # dataset even though we exercise the REAL_SITE_DATA_UNVERIFIED schema.
        manifest=copy.deepcopy(self.demo)
        manifest.update({
            "study_id":"FAKE-FOR-ADVERSARIAL-SCHEMA-TEST-ONLY",
            "evidence_class":"REAL_SITE_DATA_UNVERIFIED",
            "site_pseudonym":"ARTIFICIAL-TEST-SITE",
            "installed_engine_identity":"ARTIFICIAL-ENGINE-MODEL",
            "equipment_identity_verified":True,
            "collection_authorization_ref":"UNVERIFIED-TEST-AUTHORIZATION",
            "nameplate_evidence_class":"SITE_DOCUMENTED_UNAUTHENTICATED",
            "nameplate_source_ref":"UNVERIFIED-TEST-NAMEPLATE",
            "raw_csv_path":str(root/"made_up.csv"),
        })
        for inst in manifest["instrument_registry"]:
            inst["device_id"]="ARTIFICIAL-"+inst["device_id"]
            inst["calibration_status"]="DOCUMENTED_METADATA_NOT_INDEPENDENTLY_AUTHENTICATED"
            inst["certificate_ref"]="UNVERIFIED-TEST-CERT-"+inst["channel"]
            inst["certificate_valid_until_utc"]="2027-01-01T00:00:00Z"
            inst["uncertainty_evaluation"]="SITE_DECLARED_NOT_INDEPENDENTLY_AUDITED"
        rows=[]
        start=datetime(2026,10,1,tzinfo=timezone.utc)
        for idx in range(96):
            row=copy.deepcopy(self.frozen_rows[idx%4])
            row["interval_start_utc"]=(start+timedelta(minutes=15*idx)).isoformat().replace("+00:00","Z")
            row["interval_end_utc"]=(start+timedelta(minutes=15*(idx+1))).isoformat().replace("+00:00","Z")
            rows.append(row)
        if mutator is not None:
            mutator(manifest,rows)
        stream=io.StringIO(newline="")
        w=csv.DictWriter(stream,fieldnames=COLUMNS,lineterminator="\n")
        w.writeheader();w.writerows(rows)
        data=stream.getvalue().encode("utf8")
        manifest["raw_csv_sha256"]=hashlib.sha256(data).hexdigest()
        csv_path=root/"made_up.csv"
        csv_path.write_bytes(data)
        mpath=root/"manifest.json"
        mpath.write_text(json.dumps(manifest)+"\n",encoding="utf8")
        return mpath,csv_path

    def test_real_like_input_is_only_schema_qa_never_physical_validation(self):
        with tempfile.TemporaryDirectory(prefix="v0915-FAKE-") as tmp:
            m,c=self._make_real_tmp(Path(tmp))
            report=audit_telemetry(m,c)
            self.assertEqual(report["interval_count"],96)
            self.assertEqual(report["status"],
                "PASS_REAL_DATA_SCHEMA_AND_BALANCE_SCREEN_PENDING_HUMAN_VERIFICATION")
            self.assertFalse(report["real_plant_model_validation_performed"])
            self.assertFalse(report["plant_operational_readiness_certified"])
            self.assertFalse(report["calibration_certificates_cryptographically_verified"])

    def _expect_error(self,change,pattern):
        with tempfile.TemporaryDirectory(prefix="v0915-FAKE-") as tmp:
            m,c=self._make_real_tmp(Path(tmp),change)
            with self.assertRaisesRegex(TelemetryQAError,pattern):
                audit_telemetry(m,c)

    def test_duplicate_gap_or_non_utc_timestamps_rejected(self):
        self._expect_error(lambda m,r:r[2].update(
            interval_start_utc=r[1]["interval_start_utc"],
            interval_end_utc=r[1]["interval_end_utc"]), "duplicate, gap")
        self._expect_error(lambda m,r:r[1].update(
            interval_start_utc="2026-10-01T00:15:00+01:00"),"explicit ISO UTC")

    def test_bad_quality_flag_or_clock_skew_rejected(self):
        self._expect_error(lambda m,r:r[5].update(quality_flag="SUSPECT"),"bad or suspect")
        self._expect_error(lambda m,r:r[5].update(max_clock_offset_s="2.1"),"clock not sufficiently")

    def test_electrical_balance_and_negative_export_semantics(self):
        self._expect_error(lambda m,r:r[3].update(net_grid_export_kwh="1"),"electricity balance")
        # Signed grid IMPORT can be negative, provided the energy ledger
        # closes with an explicit large non-CHP site load.
        with tempfile.TemporaryDirectory(prefix="v0915-FAKE-") as tmp:
            def mutate(m,r):
                r[0]["net_grid_export_kwh"]="-1"
                r[0]["site_electric_consumption_kwh"]="10"
            m,c=self._make_real_tmp(Path(tmp),mutate)
            out=audit_telemetry(m,c)
            self.assertEqual(out["intervals"][0]["measured_grid_export_signed_kwh"],-1.)

    def test_gas_balance_and_buffer_cross_interval_discontinuity(self):
        self._expect_error(lambda m,r:r[5].update(produced_gas_nm3_dry="0"),"gas volume imbalance")
        self._expect_error(lambda m,r:r[3].update(buffer_gas_start_nm3_dry="99"),"buffer measurement discontinuity")

    def test_nonfinite_negative_lhv_or_unphysical_generation_rejected(self):
        self._expect_error(lambda m,r:r[0].update(generator_electric_kwh="nan"),"nonfinite")
        self._expect_error(lambda m,r:r[0].update(engine_gas_nm3_dry="-5"),"negative")
        self._expect_error(lambda m,r:r[0].update(fuel_lhv_mj_per_nm3_dry="0"),"nonpositive LHV")
        self._expect_error(lambda m,r:r[0].update(generator_electric_kwh="50"),"electricity balance")

    def test_data_digest_tamper_fails_and_no_interpolation(self):
        with tempfile.TemporaryDirectory(prefix="v0915-FAKE-") as tmp:
            m,c=self._make_real_tmp(Path(tmp))
            c.write_bytes(c.read_bytes().replace(b",10,7,2,1,",b",12,7,2,1,",1))
            with self.assertRaisesRegex(TelemetryQAError,"SHA256"):
                audit_telemetry(m,c)

    def test_expired_calibration_metadata_rejected(self):
        def expired(m,r):
            m["instrument_registry"][0]["certificate_valid_until_utc"]="2026-09-30T00:00:00Z"
        self._expect_error(expired,"calibration metadata expired")

    def test_fewer_than_one_full_day_for_real_class_rejected(self):
        with tempfile.TemporaryDirectory(prefix="v0915-FAKE-") as tmp:
            def shorter(m,r):del r[80:]
            m,c=self._make_real_tmp(Path(tmp),shorter)
            with self.assertRaisesRegex(TelemetryQAError,">=24h"):
                audit_telemetry(m,c)

    def test_cli_stdout_is_clear_and_no_raw_file_created(self):
        before=SOURCE.read_bytes()
        with tempfile.TemporaryDirectory(prefix="v0915-cli-") as tmp:
            out=Path(tmp)/"full.json"
            r=subprocess.run(
                [sys.executable,"-m","biogasflex","telemetry-qa",
                 "--manifest",str(DEFAULT_MANIFEST),"--output",str(out)],
                cwd=ROOT,text=True,capture_output=True,check=True,timeout=45,
            )
            compact=json.loads(r.stdout);full=json.loads(out.read_text(encoding="utf8"))
            self.assertFalse(compact["physical_validation_performed"])
            self.assertEqual(compact["intervals_checked"],4)
            self.assertEqual(full["raw_sha256"],DEMO_DIGEST)
            self.assertFalse(full["calibration_certificates_cryptographically_verified"])
        self.assertEqual(SOURCE.read_bytes(),before)


if __name__=="__main__":
    unittest.main()
