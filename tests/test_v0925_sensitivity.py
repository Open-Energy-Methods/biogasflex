"""Adversarial energy/bounds/serial-correlation guards for v0.9.25."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

from biogasflex import sensitivity_v0925 as s

P=Path(__file__).resolve().parents[1]/"scripts"/"audit_v0925_envelope_independent.py"
SPEC=importlib.util.spec_from_file_location("independent_sensitivity_audit",P)
CHECK=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class FixedContractEnvelopeTests(unittest.TestCase):
    def trial(self,*,gas=None,heat=None,award=.10,cap=1.5,backup=.2,
              states=None):
        if gas is None:gas=[1.]*6
        if heat is None:heat=[.15]*6
        return s.physical_fixed_award(
            gas,heat,award_mwh=award,capacity_mwh=cap,
            backup_capacity_mwth=backup,
            states=states if states is not None else [1]*24)

    def test_constant_nominal_input_meets_cyclic_inventory_exactly(self):
        r=self.trial()
        self.assertTrue(r["physically_feasible_expost"])
        self.assertTrue(r["terminal_stock_matched"])
        self.assertAlmostEqual(r["terminal_stock_delta_mwh_lhv"],0.)
        self.assertAlmostEqual(r["total_synthetic_gas_arrival_mwh_lhv"],6.)

    def test_model_and_independent_physical_states_reconcile(self):
        cases=[
            dict(gas=[.78,1.22,.9,1.,1.18,.82],award=.09,cap=3.,backup=.2),
            dict(gas=[.78]*6,award=.10,cap=1.5,backup=.2),
            dict(gas=[1.22]*6,award=.09,cap=1.5,backup=.2),
            dict(gas=[1.]*6,award=.15,cap=3.,backup=.2),
        ]
        for case in cases:
            with self.subTest(case=case):
                real=self.trial(**case)
                independent=CHECK.direct_path(
                    case["gas"],[.15]*6,case["award"],case["cap"],case["backup"])
                self.assertEqual(real["physically_feasible_expost"],independent["ok"])
                self.assertEqual(real["constraint_families_violated"],independent["violations"])
                self.assertEqual(real["terminal_stock_delta_mwh_lhv"],independent["delta"])
                self.assertEqual(real["minimum_stock_mwh_lhv"],independent["min"])
                self.assertEqual(real["maximum_stock_mwh_lhv"],independent["max"])

    def test_gas_shortage_cannot_be_cured_by_assuming_grid_import(self):
        r=self.trial(gas=[.78]*6)
        self.assertFalse(r["physically_feasible_expost"])
        self.assertIn("gas_stock_lower_bound",r["constraint_families_violated"])

    def test_high_gas_causes_overfull_store_if_no_venting(self):
        r=self.trial(gas=[1.22]*6,award=.09,cap=1.5)
        self.assertFalse(r["physically_feasible_expost"])
        self.assertIn("gas_stock_upper_bound",r["constraint_families_violated"])
        extended=self.trial(gas=[1.22]*6,award=.09,cap=3.0)
        self.assertTrue(extended["physically_feasible_expost"])

    def test_ramp_incompatible_award_rejected_even_with_large_stock(self):
        r=self.trial(award=.15,cap=3.)
        self.assertFalse(r["physically_feasible_expost"])
        self.assertIn("on_to_on_electric_ramp",r["constraint_families_violated"])

    def test_minimum_generator_output_and_zero_award_not_compatible(self):
        r=self.trial(award=0.)
        self.assertFalse(r["physically_feasible_expost"])
        self.assertIn("binary_or_fuel_rating",r["constraint_families_violated"])

    def test_all_on_fixed_export_cannot_be_delivered_when_unit_off(self):
        r=self.trial(states=[0]*24)
        self.assertFalse(r["physically_feasible_expost"])
        self.assertIn("binary_or_fuel_rating",r["constraint_families_violated"])

    def test_nominal_constant_gas_robust_and_cyclic_when_justified(self):
        x=s.worst_case_fixed_award(
            award_mwh=.1,capacity_mwh=1.5,backup_capacity_mwth=.2,
            gas_lower=1.,gas_upper=1.)
        self.assertTrue(x["all_independent_bounded_gas_paths_feasible"])
        self.assertTrue(x["all_bounded_paths_terminal_stock_matched"])

    def test_wide_gas_support_has_stock_shortage_at_nominal_award(self):
        x=s.worst_case_fixed_award(
            award_mwh=.1,capacity_mwh=3.,backup_capacity_mwth=.2,
            gas_lower=.78,gas_upper=1.22)
        self.assertFalse(x["all_independent_bounded_gas_paths_feasible"])
        self.assertLess(x["worst_lower_stock_mwh_lhv"],0.)

    def test_wide_gas_support_reserve_award_can_be_supported_with_three_mwh(self):
        x=s.worst_case_fixed_award(
            award_mwh=.09,capacity_mwh=3.,backup_capacity_mwth=.2,
            gas_lower=.78,gas_upper=1.22)
        self.assertTrue(x["all_independent_bounded_gas_paths_feasible"])
        self.assertFalse(x["all_bounded_paths_terminal_stock_matched"])

    def test_backup_capacity_is_real_thermal_constraint(self):
        x=s.worst_case_fixed_award(
            award_mwh=.09,capacity_mwh=3.,backup_capacity_mwth=0.,
            gas_lower=.78,gas_upper=1.22)
        self.assertFalse(x["all_supported_heat_demands_serviceable"])

    def test_uncertainty_band_is_assumption_not_source_verified_forecast(self):
        tiny=s.worst_case_fixed_award(
            award_mwh=.1,capacity_mwh=1.5,backup_capacity_mwth=.2,
            gas_lower=.9,gas_upper=1.1)
        broad=s.worst_case_fixed_award(
            award_mwh=.1,capacity_mwh=1.5,backup_capacity_mwth=.2,
            gas_lower=.78,gas_upper=1.22)
        self.assertTrue(tiny["all_independent_bounded_gas_paths_feasible"])
        self.assertFalse(broad["all_independent_bounded_gas_paths_feasible"])

    def test_full_week_training_bootstrap_deterministic_and_bounded(self):
        statuses=[True]*7+[False]*7
        starts=[0,7]
        a=s.bootstrap_training_day_feasibility(statuses,starts,"PREDECLARED_C1")
        b=s.bootstrap_training_day_feasibility(statuses,starts,"PREDECLARED_C1")
        self.assertEqual(a,b)
        self.assertLessEqual(0.,a["training_descriptive_7day_block_bootstrap_p05"])
        self.assertLessEqual(a["training_descriptive_7day_block_bootstrap_p95"],1.)
        self.assertFalse(a["confidence_interval_or_field_probability_claim"])
        i,j=CHECK.training_bootstrap(statuses,starts,"PREDECLARED_C1")
        self.assertEqual(a["training_descriptive_7day_block_bootstrap_p05"],i)
        self.assertEqual(a["training_descriptive_7day_block_bootstrap_p95"],j)


if __name__=="__main__":
    unittest.main()
