"""v0.9.16-C: Matlink access/source admissibility must not become a physical validation claim."""
from __future__ import annotations
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
REGISTER=ROOT/"data/evidence/v0916c_matlink_source_access_register.json"

class MatlinkExternalAcquisitionAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(REGISTER.read_text(encoding="utf8"))

    def test_source_is_specific_real_biogas_engine_and_not_synthetic(self):
        d=self.data
        self.assertEqual(d["protocol"],"BIOGASFLEX_V0916C_MATLINK_DATA_ACCESS_EVIDENCE_GATE_V1")
        self.assertEqual(d["source_id"],"nyserda_matlink_farm_project_516")
        self.assertEqual(d["fuel_type"],"ANAEROBIC_DIGESTER_BIOGAS")
        self.assertIn("Waukesha",d["original_source_technology"])
        self.assertEqual(d["source_scope"]["logger_interval_minutes"],15)

    def test_no_original_source_bytes_or_checksum_claim(self):
        d=self.data
        self.assertFalse(d["data_received"])
        self.assertEqual(d["record_status"],"BLOCKED_AWAITING_AUTHORIZED_HUMAN_SOURCE_TRANSFER")
        provenance=d["immutable_data_provenance_template"]
        for field in ("original_source_sha256","original_source_md5",
                      "original_source_bytes","original_source_filename",
                      "original_source_retrieved_utc"):
            self.assertIsNone(provenance[field],field)
        self.assertFalse(provenance["raw_site_specific_signal_values_observed"])
        self.assertFalse(provenance["source_license_verified"])

    def test_access_control_must_not_be_bypassed(self):
        d=self.data
        self.assertEqual(d["official_access"]["public_raw_csv_direct_programmatic_access"],
                         "BLOCKED_BY_ACCESS_CONTROL")
        self.assertIn("BYPASS_ACCESS_CONTROL",d["official_access"]["explicitly_forbidden_actions"])
        self.assertFalse(d["official_access"]["contact_attempt_sent"])
        self.assertEqual(d["official_access"]["email_status"],"USER_GMAIL_DRAFT_PREPARED_NOT_SENT")

    def test_all_nine_evidence_dependencies_declared(self):
        d=self.data
        self.assertEqual({x["id"] for x in d["requested_evidence"]},
                         {"M1","M2","M3","M4","M5","M6","M7","M8","M9"})
        self.assertFalse(any(d["release_claim_gates"].values()))
        self.assertEqual(d["source_scope"]["time_zone_review"],"DST_CONVERSION_NOT_VERIFIED")
        self.assertEqual(d["source_scope"]["useful_heat_meter_integration"],
                         "UNVERIFIED_SAMPLE_VS_RATE_VS_TOTAL")

    def test_published_implausible_efficiencies_are_flagged_not_calibrated(self):
        d=self.data
        anomalies=d["source_scope"]["reported_source_month_efficiency_anomalies"]
        self.assertEqual({x["month"] for x in anomalies},{"2004-10","2004-12"})
        self.assertTrue(all(x["reported_electric_efficiency_hhv_pct"]>100 for x in anomalies))
        self.assertTrue(all(x["screen"]=="PHYSICALLY_IMPOSSIBLE_POINT" for x in anomalies))
        self.assertFalse(d["release_claim_gates"]["biogasflex_engine_model_site_calibrated"])

if __name__=="__main__":
    unittest.main()
