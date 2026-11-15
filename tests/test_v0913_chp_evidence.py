"""Adversarial, source-scoped CHP evidence validation tests (no manufacturer calibration)."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from biogasflex.chp_parameter_evidence import (
    EvidenceRegisterError, audit_register, run_register,
    EXPECTED_MANUFACTURER_REFERENCES,
    REQUIRED_MISSING_PARAMETERS,
)

SOURCE = ROOT / "data/evidence/v0913_chp_parameter_register.json"


def modified(original: dict, row_id: str) -> dict:
    return next(x for x in original["parameters"] if x["id"] == row_id)


class ManufacturerEvidenceContract(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(SOURCE.read_text(encoding="utf8"))

    def test_real_register_reports_not_operationally_validated(self):
        audit = run_register(SOURCE)
        self.assertEqual(audit["parameters_reviewed"], 29)
        self.assertEqual(audit["sources_checked_against_curated_source_catalogue"], 3)
        self.assertEqual(audit["equipment_identities_kept_separate"], 3)
        self.assertEqual(audit["unidentified_count"], 14)
        self.assertFalse(audit["auto_import_into_dispatch"])
        self.assertFalse(audit["physical_validation_of_v0911_contracts"])
        self.assertFalse(audit["site_ramps_and_minimum_load_identified"])
        self.assertEqual(
            set(audit["unidentified_operating_parameters"]),
            REQUIRED_MISSING_PARAMETERS,
        )

    def test_site_and_manufacturer_nominals_are_not_equivalent(self):
        audit = run_register(SOURCE)
        self.assertFalse(audit["source_site_and_references_equated"])
        self.assertEqual(modified(self.data, "ciula_electric_rating")["value"], 0.44)
        self.assertEqual(modified(self.data, "cat_continuous_rating")["value"], 0.40)
        self.assertEqual(modified(self.data, "jen_j312_up_to_electric")["value"], 0.635)
        self.assertEqual(
            modified(self.data, "cat_max_electric_efficiency_slash")["value"],
            ["43.1%", "42.1%"],
        )
        self.assertTrue(all(
            modified(self.data, key)["admissibility"] == "REFERENCE_ONLY"
            for key in EXPECTED_MANUFACTURER_REFERENCES
        ))

    def test_reject_ramp_invented_from_annual_data(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "ciula_upward_ramp")
        row["value"] = .05
        row["source_id"] = "ciula2023"
        row["source_locator"] = "Table 2"
        row["admissibility"] = "SOURCE_SITE_STATIC_SCREEN"
        with self.assertRaisesRegex(EvidenceRegisterError, "unidentified"):
            audit_register(bad)

    def test_reject_fabricated_site_minimum_power(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "ciula_minimum_stable_load")
        row["value"] = 0.25
        with self.assertRaises(EvidenceRegisterError):
            audit_register(bad)

    def test_reject_catalogue_plant_identity_transfer(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "cat_continuous_rating")
        row["equipment_id"] = "ciula_landfill_chp"
        with self.assertRaisesRegex(EvidenceRegisterError, "cannot be transferred"):
            audit_register(bad)

    def test_reject_manufacturer_reference_as_site_nameplate(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "jen_j312_up_to_electric")
        row["admissibility"] = "SOURCE_SITE_STATIC_SCREEN"
        with self.assertRaises(EvidenceRegisterError):
            audit_register(bad)

    def test_reject_manufacturer_page_substitution(self):
        bad = copy.deepcopy(self.data)
        src = next(x for x in bad["sources"] if x["id"] == "cat_cg132b8_2026")
        src["url"] = "https://example.invalid/fake-generator"
        with self.assertRaisesRegex(EvidenceRegisterError, "incorrect provider"):
            audit_register(bad)

    def test_reject_plausible_modified_catalogue_rating(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "cat_continuous_rating")
        row["value"] = 0.44
        with self.assertRaisesRegex(EvidenceRegisterError, "manufacturer stated"):
            audit_register(bad)

    def test_reject_unjustified_cat_slash_interpretation(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "cat_max_electric_efficiency_slash")
        row["value"] = 0.431
        row["unit"] = "fraction"
        with self.assertRaisesRegex(EvidenceRegisterError, "manufacturer stated"):
            audit_register(bad)

    def test_reject_fuel_reclassification_as_anaerobic_digestate(self):
        bad = copy.deepcopy(self.data)
        site = next(x for x in bad["equipment"] if x["id"] == "ciula_landfill_chp")
        site["fuel_category"] = "FARM_DIGESTER_BIOGAS"
        with self.assertRaisesRegex(EvidenceRegisterError, "landfill"):
            audit_register(bad)

    def test_reject_fake_hardware_validation(self):
        bad = copy.deepcopy(self.data)
        bad["flags"]["manufacturer_ramp_limit_verified"] = True
        with self.assertRaisesRegex(EvidenceRegisterError, "cannot be asserted"):
            audit_register(bad)

    def test_reject_manufacturer_model_identity_claim(self):
        bad = copy.deepcopy(self.data)
        bad["equipment"][0]["installed_engine_make_model"] = "CG132B-8"
        with self.assertRaises(EvidenceRegisterError):
            audit_register(bad)

    def test_reject_removed_unidentified_gap(self):
        bad = copy.deepcopy(self.data)
        row = modified(bad, "ciula_gas_buffer")
        row["parameter"] = "unrelated_measurement"
        with self.assertRaisesRegex(EvidenceRegisterError, "Missing essential"):
            audit_register(bad)

    def test_source_site_screening_not_a_dispatch_import(self):
        audited = run_register(SOURCE)
        self.assertEqual(
            audited["static_site_nameplate_screening_parameters"],
            ["ciula_electric_rating", "ciula_thermal_rating"],
        )
        self.assertFalse(audited["physical_validation_of_v0911_contracts"])
        self.assertFalse(audited["manufacturer_numeric_data_usable_as_site_performance"])

    def test_constructive_annual_aggregate_nonidentifiability(self):
        # Annual integrals and running hours do not uniquely specify ramps.
        a, b = [0.2, 0.2, 0.2, 0.2], [0.1, 0.3, 0.1, 0.3]
        self.assertEqual(sum(a), sum(b))
        self.assertEqual(sum(p > 0 for p in a), sum(p > 0 for p in b))
        self.assertNotEqual(max(abs(y-x) for x,y in zip(a,a[1:])),
                            max(abs(y-x) for x,y in zip(b,b[1:])))

    def test_cli_produces_scope_limited_report(self):
        result = subprocess.run(
            [sys.executable, "-m", "biogasflex", "chp-evidence-register",
             "--register", str(SOURCE)],
            cwd=ROOT, capture_output=True, text=True, check=True, timeout=60,
        )
        report = json.loads(result.stdout)
        self.assertEqual(report["evidence_level"], "SOURCE_SCOPED_CATALOGUE_AND_ANNUAL_PAPER")
        self.assertEqual(report["unidentified_dynamic_parameters"], 14)
        self.assertFalse(report["physical_dispatch_calibrated"])


if __name__ == "__main__":
    unittest.main()
