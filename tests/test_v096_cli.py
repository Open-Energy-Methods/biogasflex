"""CLI regression: new v0.9.6 on/off MILP explicitly opt-in and synthetic."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class CommitmentCommandTests(unittest.TestCase):
    def call(self,*args):
        return subprocess.run([sys.executable,"-m","biogasflex",*args],
                              cwd=ROOT,text=True,capture_output=True,
                              check=True,timeout=60)

    def test_synthetic_defaults_have_exact_55_euro_net(self):
        r=json.loads(self.call("unit-commitment").stdout)
        self.assertEqual(r["status"],"EXPERIMENTAL_NOT_PLANT_VALIDATED")
        self.assertAlmostEqual(r["net_contribution_eur"],55)
        self.assertEqual(r["start_count"],1)
        self.assertIsNone(r["output_path"])

    def test_optional_full_output_writes_without_modifying_frozen_results(self):
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/"commitment.json"
            meta=json.loads(self.call("unit-commitment","--output",str(target)).stdout)
            full=json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(full["on"],[0,0,1])
            self.assertEqual(full["starts"],[0,0,1])
            self.assertEqual(meta["output_path"],str(target))

    def test_cli_advertises_new_command(self):
        r=self.call("--help").stdout
        self.assertIn("unit-commitment",r)
        self.assertIn("forecast-regret",r)


if __name__=="__main__":
    unittest.main()
