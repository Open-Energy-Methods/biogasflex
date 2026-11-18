"""Adversarial standard-library-independent v0.9.24 failure taxonomy checks."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH=Path(__file__).resolve().parents[1]/"scripts"/"diagnose_v0924_award_failures.py"
spec=importlib.util.spec_from_file_location("v0924_failure_arithmetic",PATH)
oracle=importlib.util.module_from_spec(spec)
spec.loader.exec_module(oracle)


class ContractDeterministicFailureTests(unittest.TestCase):
    def defaults(self,**changes):
        x=dict(first_slot=0,starting_stock=.75,
               starting_power=.4,previous_on=1,
               on=[1]*4,awards=[.10]*4,gas_rate=1.,heat_rate=.15)
        x.update(changes)
        return x

    def test_regular_nominal_contract_hour_is_feasible(self):
        self.assertTrue(oracle.quarter_hour_path(**self.defaults())["feasible"])

    def test_initial_electrical_ramp_impossible_contract(self):
        r=oracle.quarter_hour_path(**self.defaults(awards=[.15]*4))
        self.assertFalse(r["feasible"])
        self.assertIn("consecutive_ON_electrical_ramp",r["violations"])

    def test_nonnegative_stock_required_for_fixed_export(self):
        r=oracle.quarter_hour_path(**self.defaults(
            first_slot=4,starting_stock=0.,gas_rate=.78))
        self.assertFalse(r["feasible"])
        self.assertIn("negative_gas_buffer_inventory",r["violations"])

    def test_overfull_gas_buffer_is_not_secretly_vented(self):
        r=oracle.quarter_hour_path(**self.defaults(
            first_slot=8,starting_stock=1.49,gas_rate=1.22,
            awards=[.09]*4))
        self.assertFalse(r["feasible"])
        self.assertIn("gas_buffer_upper_capacity",r["violations"])

    def test_off_generator_cannot_produce_awarded_mwh(self):
        r=oracle.quarter_hour_path(**self.defaults(on=[0]*4,awards=[.09]*4))
        self.assertFalse(r["feasible"])
        self.assertIn("frozen_binary_or_fuel_rating",r["violations"])

    def test_current_hour_relative_ramp_reset_is_not_applied_at_replan(self):
        r=oracle.quarter_hour_path(**self.defaults(
            first_slot=4,starting_power=.4,awards=[.14]*4))
        self.assertTrue(r["feasible"])
        r0=oracle.quarter_hour_path(**self.defaults(
            first_slot=0,starting_power=.4,awards=[.14]*4))
        self.assertFalse(r0["feasible"])
        self.assertIn("consecutive_ON_electrical_ramp",r0["violations"])

    def test_bad_number_of_award_intervals_rejected(self):
        with self.assertRaisesRegex(AssertionError,"Bad frozen binary"):
            oracle.quarter_hour_path(**self.defaults(awards=[.1]*3))

    def test_actual_heat_outside_backup_limit_rejected(self):
        r=oracle.quarter_hour_path(**self.defaults(
            heat_rate=.5,awards=[.09]*4))
        self.assertFalse(r["feasible"])
        self.assertIn("heat_backup_or_dump_capacity",r["violations"])


if __name__=="__main__":
    unittest.main()
