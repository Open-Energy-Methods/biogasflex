"""Independent diagnostics unit tests for distinct physical infeasibility modes."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1]/"scripts"/"diagnose_v0922_feasibility.py"
SPEC = importlib.util.spec_from_file_location("v0922_failure_diagnostic", PATH)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class IndependentFailureReasonTests(unittest.TestCase):
    def params(self, **kw):
        data = dict(on=[1]*4, prior_on=1, prior_stock=.75,
                    prior_power=.4, gas=1.0, heat=.15,
                    global_hour_index=2)
        data.update(kw)
        return data

    def test_regular_on_hour_feasible(self):
        self.assertTrue(mod.current_hour_lp(**self.params()))

    def test_storage_overflow_can_be_caused_by_fixed_off_state(self):
        p = self.params(on=[0]*4, prior_on=0, prior_stock=1.45, gas=1.1)
        self.assertFalse(mod.current_hour_lp(**p))
        self.assertTrue(mod.current_hour_lp(**p, relax="stock_ceiling"))
        self.assertFalse(mod.current_hour_lp(**p, relax="ramps"))

    def test_storage_shortage_can_be_caused_by_minimum_on_fuel(self):
        p = self.params(on=[1]*4, prior_on=1, prior_stock=0., gas=0.)
        self.assertFalse(mod.current_hour_lp(**p))
        self.assertTrue(mod.current_hour_lp(**p, relax="stock_floor"))

    def test_ramp_conflict_can_be_diagnosed_without_rewriting_physics(self):
        p = self.params(on=[1]*4, prior_on=1, prior_stock=1.5,
                        prior_power=.4, gas=2.)
        self.assertFalse(mod.current_hour_lp(**p))
        self.assertTrue(mod.current_hour_lp(**p, relax="ramps"))

    def test_global_half_initial_ramp_distinct_from_later_replans(self):
        # At global t=0 the original first half-step ramp limit is tighter.
        # Starting at a later hour must never spuriously apply that rule.
        p = self.params(prior_stock=.75, prior_power=.4, gas=1.0,
                        global_hour_index=1)
        self.assertTrue(mod.current_hour_lp(**p))

    def test_tiny_stock_roundoff_does_not_invalidate_feasible_hour(self):
        self.assertTrue(mod.current_hour_lp(
            **self.params(prior_stock=-1e-10, gas=1.0, heat=.15)))
        self.assertTrue(mod.current_hour_lp(
            **self.params(prior_stock=1.5+1e-10, gas=1.0, heat=.15)))

    def test_invalid_binary_rejected(self):
        with self.assertRaisesRegex(ValueError, "commitment"):
            mod.current_hour_lp(**self.params(on=[1, 1, 2, 0]))


if __name__ == "__main__":
    unittest.main()
