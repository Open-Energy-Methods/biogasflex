"""v0.9.12 published annual CHP evidence and fail-closed source audit."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from biogasflex.annual_chp_evidence import EvidenceError, audit_annual_chp, load_rows

DATA = ROOT / "data/observed/ciula_2023_landfill_chp_annual.csv"


class ExternalCHPEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.text = DATA.read_text(encoding="utf8")

    def with_tamper(self, old, new):
        self.assertIn(old, self.text)
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding="utf8", delete=False)
        try:
            f.write(self.text.replace(old, new, 1))
            f.close()
            return Path(f.name)
        except Exception:
            f.close()
            Path(f.name).unlink(missing_ok=True)
            raise

    def test_years_and_site_identity(self):
        r = audit_annual_chp(DATA)
        self.assertEqual([x["year"] for x in r["annual_observations"]], list(range(2012, 2023)))
        self.assertEqual(r["nameplate"], {"electric_mw": .44, "thermal_mw": .52})
        self.assertIn("LANDFILL_GAS", r["plant_fuel"])
        self.assertEqual(len(r["input_csv_sha256"]), 64)
        self.assertTrue(all(
            row["mean_electrical_mw_when_running"] <= .44 + 1e-9
            for row in r["annual_observations"]
        ))

    def test_published_gas_mean_mismatch_is_explicit(self):
        a = audit_annual_chp(DATA)
        x = a["periods"]["2018-2022"]["arithmetic_annual_means"]
        self.assertAlmostEqual(x["landfill_gas_recovered_m3"], 1267253.2)
        self.assertEqual(a["published_reported_averages_unchanged"]["2018-2022"]["landfill_gas_recovered_m3"], 1291515)
        self.assertAlmostEqual(
            a["documented_source_discrepancies"][0]["difference_recomputed_minus_published_m3_per_year"], -24261.8
        )
        self.assertEqual(a["status"], "PASS_WITH_PUBLISHED_SOURCE_DISCREPANCIES")

    def test_other_annual_averages_recomputed(self):
        a = audit_annual_chp(DATA)
        pre = a["periods"]["2012-2017"]["arithmetic_annual_means"]
        post = a["periods"]["2018-2022"]["arithmetic_annual_means"]
        self.assertEqual(pre["running_hours"], 7489)
        self.assertEqual(pre["landfill_gas_recovered_m3"], 910533)
        self.assertAlmostEqual(pre["electricity_generated_mwh"], 1219.3916666666667)
        self.assertAlmostEqual(post["electricity_generated_mwh"], 2131.222)
        self.assertAlmostEqual(post["heat_generated_mwh"], 2799.444)

    def test_leap_calendar_and_finite_aggregate_only(self):
        a = audit_annual_chp(DATA)
        y2020 = next(x for x in a["annual_observations"] if x["year"] == 2020)
        self.assertEqual(y2020["calendar_hours"], 8784)
        self.assertAlmostEqual(y2020["calendar_running_fraction"], 7883 / 8784)
        self.assertIn("engine_ramp_rate", a["no_direct_validation_of"])
        self.assertIn("gas_buffer_volume", a["no_direct_validation_of"])
        self.assertIn("net_grid_export", a["no_direct_validation_of"])

    def test_missing_year_rejected(self):
        f = self.with_tamper("2018,7876,1306298,2327.82,2788.38\n", "")
        try:
            with self.assertRaisesRegex(EvidenceError, "Exactly one"):
                load_rows(f)
        finally:
            f.unlink(missing_ok=True)

    def test_duplicate_year_rejected(self):
        f = self.with_tamper("2018,7876", "2017,7876")
        try:
            with self.assertRaisesRegex(EvidenceError, "Exactly one"):
                load_rows(f)
        finally:
            f.unlink(missing_ok=True)

    def test_capacity_exceedance_rejected(self):
        f = self.with_tamper("2012,7614,926732,1135.25", "2012,7614,926732,5000.25")
        try:
            with self.assertRaisesRegex(EvidenceError, "rated electrical"):
                load_rows(f)
        finally:
            f.unlink(missing_ok=True)

    def test_negative_gas_and_nonfinite_energy_rejected(self):
        for old, new in [
            ("2012,7614,926732", "2012,7614,-9"),
            ("2012,7614,926732,1135.25", "2012,7614,926732,nan"),
        ]:
            with self.subTest(new=new):
                f = self.with_tamper(old, new)
                try:
                    with self.assertRaises(EvidenceError):
                        load_rows(f)
                finally:
                    f.unlink(missing_ok=True)

    def test_running_hours_above_calendar_rejected(self):
        f = self.with_tamper("2020,7883", "2020,8800")
        try:
            with self.assertRaisesRegex(EvidenceError, "calendar"):
                load_rows(f)
        finally:
            f.unlink(missing_ok=True)

    def test_cli_is_explicitly_evidence_not_calibration(self):
        p = subprocess.run(
            [sys.executable, "-m", "biogasflex", "annual-chp-evidence",
             "--csv", str(DATA)],
            cwd=ROOT, text=True, capture_output=True, check=True, timeout=30,
        )
        result = json.loads(p.stdout)
        self.assertEqual(result["annual_records"], 11)
        self.assertEqual(result["evidence_level"], "PUBLISHED_SITE_ANNUAL_AGGREGATES_ONLY")
        self.assertEqual(result["source_discrepancies"], 3)


if __name__ == "__main__":
    unittest.main()
