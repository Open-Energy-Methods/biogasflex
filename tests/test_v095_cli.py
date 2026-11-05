"""v0.9.5 experimental CLI deterministic output and optional JSON export."""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class ExperimentalCLITests(unittest.TestCase):
    def invoke(self, command, *arguments):
        return subprocess.run([sys.executable,"-m","biogasflex",command,*arguments],
            cwd=ROOT,text=True,capture_output=True,check=True,timeout=30)

    def test_synthetic_operating(self):
        r=json.loads(self.invoke("operating-surrogate").stdout)
        self.assertEqual(r["status"],"EXPERIMENTAL_NOT_PLANT_VALIDATED")
        self.assertAlmostEqual(r["incremental_contribution_eur"],5.0)
        self.assertIsNone(r["output_path"])

    def test_synthetic_price_regret(self):
        r=json.loads(self.invoke("forecast-regret").stdout)
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],5.0)
        self.assertAlmostEqual(r["realized_increment_over_fixed_eur"],0.0)

    def test_explicit_full_json_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/"experiment.json"
            meta=json.loads(self.invoke("operating-surrogate","--output",str(target)).stdout)
            self.assertTrue(target.is_file())
            full=json.loads(target.read_text(encoding="utf-8"))
            self.assertAlmostEqual(full["incremental_contribution_eur"],5.0)
            self.assertEqual(meta["output_path"],str(target))

if __name__=="__main__":
    unittest.main()
