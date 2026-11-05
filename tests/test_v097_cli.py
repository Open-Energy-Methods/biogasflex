"""v0.9.7 opt-in, nonwriting experimental clock-hour CLI."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class HourlyCLI(unittest.TestCase):
    def cli(self,*args):
        return subprocess.run([sys.executable,"-m","biogasflex",*args],
                              cwd=ROOT,text=True,capture_output=True,
                              check=True,timeout=40)

    def test_help_lists_new_and_historical_experimental_commands(self):
        text=self.cli("--help").stdout
        for token in ("hourly-commitment","unit-commitment","forecast-regret"):
            self.assertIn(token,text)

    def test_default_runs_synthetic_fractional_hours_without_file(self):
        p=json.loads(self.cli("hourly-commitment").stdout)
        self.assertEqual(p["status"],"EXPERIMENTAL_NOT_PLANT_VALIDATED")
        self.assertAlmostEqual(p["net_contribution_eur"],45.0)
        self.assertEqual(p["start_count"],1)
        self.assertIsNone(p["output_path"])

    def test_explicit_output_saves_clock_offsets_and_prior_dwell(self):
        with tempfile.TemporaryDirectory() as folder:
            target=Path(folder)/"hourly.json"
            meta=json.loads(self.cli("hourly-commitment","--output",str(target)).stdout)
            full=json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(full["clock_hours_from_horizon_start"],[0,0.25,1.25])
            self.assertEqual(full["on"],[0,1])
            self.assertEqual(meta["output_path"],str(target))


if __name__=="__main__":
    unittest.main()
