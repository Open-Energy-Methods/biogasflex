"""Adversarial optimality-certificate checks; no new physical plant claims."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("dual092", ROOT/"scripts/certify_v092_dual_bounds.py")
dual = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(dual)
BASE = json.loads((ROOT/"config/v07_lovsta_heat_proxy.json").read_text(encoding="utf-8"))


def frozen_case(index=0):
    path = ROOT/"results/v0.8/cases"/f"V08-S{index:03d}.json"
    return json.loads(path.read_text(encoding="utf-8"))


class DualBoundTests(unittest.TestCase):
    def test_zero_buffer_degenerate_lp_certifies(self):
        result = dual.certify_case(frozen_case(0), BASE)
        self.assertEqual(result["status"], "PASS")
        self.assertLessEqual(result["abs_duality_gap_eur"], dual.GAP_TOL_EUR)

    def test_late_frozen_case_certifies(self):
        result = dual.certify_case(frozen_case(215), BASE)
        self.assertLessEqual(result["abs_duality_gap_eur"], dual.GAP_TOL_EUR)

    def test_tampered_gas_use_rejected(self):
        bad = frozen_case()
        bad["input_profile"][0]["optimized_gas_use_mw_lhv"] += 0.1
        with self.assertRaises(dual.CertificateFailure):
            dual.certify_case(bad, BASE)

    def test_fabricated_incremental_value_rejected(self):
        bad = frozen_case()
        bad["optimized_dispatch"]["economic_contribution_proxy_eur"] += 1
        with self.assertRaisesRegex(dual.CertificateFailure, "contribution"):
            dual.certify_case(bad, BASE)

    def test_false_electrical_rating_rejected(self):
        bad = frozen_case()
        bad["chp_electric_rating_mw"] = 0.01
        with self.assertRaises(dual.CertificateFailure):
            dual.certify_case(bad, BASE)

    def test_nonfinite_price_rejected(self):
        bad = frozen_case()
        bad["input_profile"][0]["price_eur_per_mwh"] = float("nan")
        with self.assertRaisesRegex(dual.CertificateFailure, "not finite"):
            dual.certify_case(bad, BASE)

    def test_analytical_two_interval_eur_8p25_oracle(self):
        from biogasflex.baseline import Interval
        from biogasflex.heat_dispatch import optimize_heat_dispatch
        case = {
            "case_id":"v092_two_interval_oracle", "price_zone":"SE3",
            "electric_rating_mw":1.0, "gas_input_mw_lhv":1.0,
            "electric_efficiency_lhv":0.4, "thermal_efficiency_lhv":0.5,
            "gas_storage_capacity_mwh_lhv":0.5, "initial_gas_inventory_mwh_lhv":0,
            "fixed_flaring_mw_lhv":0, "fixed_losses_mw_lhv":0,
            "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
            "heat_demand_mw_th":0.5, "aux_heat_capacity_mw_th":0.5,
            "heat_dump_capacity_mw_th":0.5, "aux_heat_cost_eur_per_mwh_th":5.0,
            "heat_dump_penalty_eur_per_mwh_th":2.0, "chp_variable_cost_eur_per_mwh_e":0
        }
        rows = [Interval(datetime(2020,1,1,i,tzinfo=timezone.utc),p,1.0,"SE3")
                for i,p in enumerate((10.0,60.0))]
        outcome = optimize_heat_dispatch(case, rows)
        self.assertAlmostEqual(outcome["incremental_economic_contribution_proxy_eur"], 8.25)
        cert = dual.certify_case(outcome, case)
        self.assertAlmostEqual(cert["dual_bound_eur"],
                               outcome["optimized_dispatch"]["economic_contribution_proxy_eur"], places=5)

    def test_release_version_and_ci_include_new_gate(self):
        from biogasflex import __version__
        self.assertEqual(__version__, "0.9.8.1")
        self.assertIn('version = "0.9.8.1"', (ROOT/"pyproject.toml").read_text(encoding="utf-8"))
        self.assertIn('version: "0.9.8.1"', (ROOT/"CITATION.cff").read_text(encoding="utf-8"))
        for p in ("reproduce_v0981.sh","reproduce_v0981.ps1","verify_v0981_environment.py"):
            self.assertTrue((ROOT/"scripts"/p).is_file())
            self.assertIn(p,(ROOT/".github/workflows/ci.yml").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
