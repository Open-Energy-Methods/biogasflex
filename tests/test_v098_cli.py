"""v0.9.8 rolling-forecast CLI is synthetic, opt-in and nonwriting by default."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class RollingCLI(unittest.TestCase):
    def cli(self,*args):
        return subprocess.run([sys.executable,"-m","biogasflex",*args],
                              cwd=ROOT,text=True,capture_output=True,
                              check=True,timeout=60)

    def test_help_advertises_new_and_old_opt_in_commands(self):
        output=self.cli("--help").stdout
        for command in ("rolling-forecast","hourly-commitment","unit-commitment","forecast-regret"):
            self.assertIn(command,output)

    def test_default_three_slot_reforecast_shows_eur_10_regret(self):
        result=json.loads(self.cli("rolling-forecast").stdout)
        self.assertEqual(result["status"],"EXPERIMENTAL_NOT_PLANT_VALIDATED")
        self.assertIsNone(result["output_path"])
        self.assertEqual(result["steps_executed"],3)
        self.assertAlmostEqual(result["rolling_realized_contribution_eur"],70)
        self.assertAlmostEqual(result["perfect_foresight_net_contribution_eur"],80)
        self.assertAlmostEqual(result["perfect_foresight_regret_eur"],10)

    def test_opt_in_full_output_records_actual_execution_and_bound(self):
        with tempfile.TemporaryDirectory() as d:
            dst=Path(d)/"rolling.json"
            meta=json.loads(self.cli("rolling-forecast","--output",str(dst)).stdout)
            body=json.loads(dst.read_text(encoding="utf-8"))
            self.assertEqual(meta["output_path"],str(dst))
            self.assertEqual(len(body["hourly_executed"]),3)
            self.assertAlmostEqual(body["terminal_inventory_mwh_lhv"],0)
            self.assertAlmostEqual(body["hourly_executed"][1]["gas_use_mw_lhv"],0.5)


if __name__=="__main__":
    unittest.main()
