"""Regression and adversarial checks for the solver-free BiogasFlex v0.9.3 oracle."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
sys.path.insert(0, str(ROOT/"scripts"))

from biogasflex.baseline import Interval
from biogasflex.heat_dispatch import optimize_heat_dispatch
from oracle_v093_two_interval import OracleFailure, verify_two_interval
from run_v093_stress import compare_solvers, run as run_stress


def sample(**changes):
    c = {
        "case_id": "v093_two_interval_test",
        "price_zone": "SE3",
        "electric_rating_mw": 0.55,
        "gas_input_mw_lhv": 0.6,
        "electric_efficiency_lhv": 0.4,
        "thermal_efficiency_lhv": 0.45,
        "gas_storage_capacity_mwh_lhv": 0.4,
        "initial_gas_inventory_mwh_lhv": 0.0,
        "fixed_flaring_mw_lhv": 0.0,
        "fixed_losses_mw_lhv": 0.0,
        "heat_service_model": "instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th": 0.27,
        "aux_heat_capacity_mw_th": 0.7,
        "heat_dump_capacity_mw_th": 0.9,
        "aux_heat_cost_eur_per_mwh_th": 25.0,
        "heat_dump_penalty_eur_per_mwh_th": 2.0,
        "chp_variable_cost_eur_per_mwh_e": 0.0,
    }
    c.update(changes)
    return c


class ExactTwoIntervalTests(unittest.TestCase):
    def test_solver_free_piecewise_oracle_known_8p25_eur(self):
        cfg = sample(
            electric_rating_mw=1.0, gas_input_mw_lhv=1.0,
            electric_efficiency_lhv=0.4, thermal_efficiency_lhv=0.5,
            gas_storage_capacity_mwh_lhv=0.5,
            heat_demand_mw_th=0.5, aux_heat_cost_eur_per_mwh_th=5,
            heat_dump_penalty_eur_per_mwh_th=2,
        )
        oracle, solved = compare_solvers(cfg, ((10.0,1.0),(60.0,1.0)))
        self.assertAlmostEqual(oracle["incremental_contribution_eur"], 8.25)
        self.assertAlmostEqual(
            solved["incremental_economic_contribution_proxy_eur"], 8.25
        )

    def test_negative_prices_and_unequal_durations(self):
        cfg = sample(
            gas_production_mw_lhv=[0.45,0.85],
            fixed_flaring_mw_lhv=[0.01,0.03],
            fixed_losses_mw_lhv=0.01,
            heat_demand_mw_th=[0.12,0.40],
            aux_heat_cost_eur_per_mwh_th=[10.0,80.0],
            heat_dump_penalty_eur_per_mwh_th=[0.0,10.0],
            chp_variable_cost_eur_per_mwh_e=[3.0,11.0],
            initial_gas_inventory_mwh_lhv=0.1,
        )
        oracle, numerical = compare_solvers(cfg, ((-65.0,0.5),(45.0,1.5)))
        self.assertLessEqual(oracle["candidate_count"], 4)
        self.assertGreaterEqual(oracle["incremental_contribution_eur"], -1e-7)

    def test_zero_thermal_conversion(self):
        cfg = sample(thermal_efficiency_lhv=0.0, heat_demand_mw_th=0.2)
        oracle, _ = compare_solvers(cfg, ((-10.0,0.25),(95.0,1.75)))
        self.assertEqual(oracle["candidate_count"], 2)

    def test_zero_capacity_forces_fixed_comparator(self):
        cfg = sample(gas_storage_capacity_mwh_lhv=0)
        oracle, _ = compare_solvers(cfg, ((-40.0,1.0),(110.0,1.0)))
        self.assertAlmostEqual(oracle["incremental_contribution_eur"], 0.0)
        self.assertAlmostEqual(oracle["optimal_stock_after_first_mwh_lhv"], 0.0)

    def test_increased_storage_cannot_reduce_optimal_contribution(self):
        values = []
        for cap in (0.0,0.1,0.3,0.8):
            c = sample(gas_storage_capacity_mwh_lhv=cap)
            result = verify_two_interval(c, ((15.0,1.0),(100.0,1.0)))
            values.append(result["optimized_contribution_eur"])
        self.assertTrue(all(b >= a-1e-7 for a,b in zip(values, values[1:])))

    def test_nonfinite_and_boolean_values_fail_closed(self):
        cases = [
            (sample(), ((float("nan"),1.0),(3.0,1.0))),
            (sample(), ((10.0,0.0),(3.0,1.0))),
            (sample(electric_rating_mw=True), ((10.0,1.0),(3.0,1.0))),
            (sample(aux_heat_cost_eur_per_mwh_th=-1), ((10.0,1.0),(3.0,1.0))),
            (sample(gas_storage_capacity_mwh_lhv=-1), ((10.0,1.0),(3.0,1.0))),
            (sample(), ((10.0,1.0),)),
        ]
        for config,prices in cases:
            with self.subTest(prices=prices, config=config), self.assertRaises(OracleFailure):
                verify_two_interval(config, prices)

    def test_infeasible_baseline_cannot_be_reported_optimal(self):
        cfg = sample(heat_demand_mw_th=0.8, aux_heat_capacity_mw_th=0.05)
        with self.assertRaisesRegex(OracleFailure, "Fixed gas-use comparator"):
            verify_two_interval(cfg, ((25.0,1.0),(35.0,1.0)))

    def test_price_translation_keeps_incremental_contribution(self):
        cfg = sample()
        base = verify_two_interval(cfg, ((-30.0,0.5),(50.0,1.5)))
        shifted = verify_two_interval(cfg, ((70.0,0.5),(150.0,1.5)))
        self.assertAlmostEqual(base["incremental_contribution_eur"],
                               shifted["incremental_contribution_eur"])
        # Cyclic inventory fixes total gas and hence the price-shift effect.
        self.assertAlmostEqual(
            shifted["optimized_contribution_eur"]-base["optimized_contribution_eur"],
            100*0.4*0.6*2.0,
        )

    def test_constant_variable_cost_shift_cancels(self):
        cfg = sample(chp_variable_cost_eur_per_mwh_e=[0,5])
        raised = sample(chp_variable_cost_eur_per_mwh_e=[17,22])
        a = verify_two_interval(cfg, ((5.0,1.0),(150.0,1.0)))
        b = verify_two_interval(raised, ((5.0,1.0),(150.0,1.0)))
        self.assertAlmostEqual(a["incremental_contribution_eur"],
                               b["incremental_contribution_eur"])

    def test_deterministic_stress_smoke(self):
        report = run_stress(count=8)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["synthetic_oracle_comparisons"], 8)
        self.assertEqual(report["capacity_monotonicity_chains"], 1)
        self.assertLess(report["max_abs_optimized_objective_disagreement_eur"], 2e-6)

    def test_no_solver_dependencies_in_analytical_oracle(self):
        source = (ROOT/"scripts/oracle_v093_two_interval.py").read_text(encoding="utf-8")
        self.assertNotIn("from scipy",source)
        self.assertNotIn("import scipy",source)
        self.assertNotIn("numpy",source.lower())


if __name__ == "__main__":
    unittest.main()
