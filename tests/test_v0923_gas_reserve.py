"""Adversarial v0.9.23 one-hour gas viability / prefix invariance tests."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

from biogasflex import causal_v0922 as c
from biogasflex import joint_v0921 as j
from biogasflex import viability_v0923 as v

SPEC=importlib.util.spec_from_file_location(
    "independent_v0923_reserve_check",
    Path(__file__).resolve().parents[1] /
        "scripts"/"audit_v0923_reserve_independent.py")
ORACLE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ORACLE)


def fixture():
    nominal={
       "price_eur_mwh":[55.+2.*(i//4) for i in range(j.N)],
       "synthetic_gas_production_mw_lhv":[1.]*j.N,
       "synthetic_site_heat_demand_mw_th":[.15]*j.N,
    }
    actual=copy.deepcopy(nominal)
    for i in range(j.N):
        actual["synthetic_gas_production_mw_lhv"][i] = [
            1.00,.78,1.06,.88,1.18,.82][i//4]
        actual["synthetic_site_heat_demand_mw_th"][i] = .15
        actual["price_eur_mwh"][i] += 7
    return nominal, actual


class SourceHourReserveTests(unittest.TestCase):
    def test_guarded_dispatch_has_independently_reconstructable_minimum_gas_witness(self):
        forecast,realized=fixture()
        result=c.replay_causal(forecast,realized,[1]*j.N,
                               next_hour_gas_floor=.78)
        self.assertTrue(result["feasible"],result.get("failure_reason"))
        self.assertEqual(len(result["completed_15min_rows"]),j.N)
        self.assertTrue(result["next_hour_gas_reserve_viability_guard_enabled"])
        for hour in range(5):
            self.assertTrue(ORACLE.check_next_hour_witness(
                [1]*j.N,result["completed_15min_rows"],
                result["hourly_observation_log"][hour],hour,.78))
        self.assertFalse(result["hourly_observation_log"][5]
                         ["next_hour_gas_floor_viability_witness_active"])

    def test_future_realized_gas_heat_and_price_are_unavailable_to_current_guard(self):
        nominal,actual=fixture()
        first=c.replay_causal(nominal,actual,[1]*j.N,
                              next_hour_gas_floor=.78)
        different=copy.deepcopy(actual)
        for t in range(16,j.N):
            different["synthetic_gas_production_mw_lhv"][t]=.79
            different["synthetic_site_heat_demand_mw_th"][t]=.19
            different["price_eur_mwh"][t]=-88.
        after=c.replay_causal(nominal,different,[1]*j.N,
                              next_hour_gas_floor=.78)
        self.assertTrue(first["feasible"])
        self.assertTrue(after["feasible"])
        self.assertEqual(first["completed_15min_rows"][:16],
                         after["completed_15min_rows"][:16])

    def test_changing_future_actual_price_cannot_change_control(self):
        n,a=fixture()
        before=c.replay_causal(n,a,[1]*j.N,next_hour_gas_floor=.78)
        modified=copy.deepcopy(a)
        modified["price_eur_mwh"]=[-120.]*j.N
        after=c.replay_causal(n,modified,[1]*j.N,
                              next_hour_gas_floor=.78)
        self.assertTrue(before["feasible"])
        self.assertTrue(after["feasible"])
        for x,y in zip(before["completed_15min_rows"],
                       after["completed_15min_rows"]):
            for key in ("gas_use_mw_lhv","stock_end_mwh_lhv",
                        "backup_heat_mw_th","dumped_heat_mw_th"):
                self.assertAlmostEqual(x[key],y[key],places=8)
        self.assertNotEqual(before["economic_contribution_eur"],
                            after["economic_contribution_eur"])

    def test_original_default_policy_remains_unchanged_by_opt_in_feature(self):
        n,a=fixture()
        original=c.replay_causal(n,a,[1]*j.N)
        explicit=c.replay_causal(n,a,[1]*j.N,
                                 next_hour_gas_floor=None)
        self.assertEqual(original,explicit)

    def test_invalid_gas_reserve_bound_rejected(self):
        n,a=fixture()
        for invalid in (-.1,float("nan"),float("inf"),3.):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                c.replay_causal(n,a,[1]*j.N,next_hour_gas_floor=invalid)

    def test_source_runner_disallows_false_model_lower_bound(self):
        with self.assertRaisesRegex(ValueError,"exceeds"):
            v.run({},max_days=1,synthetic_gas_floor_mw_lhv=.90)

    def test_reserve_auditor_rejects_tampered_witness(self):
        n,a=fixture()
        result=c.replay_causal(n,a,[1]*j.N,next_hour_gas_floor=.78)
        self.assertTrue(result["feasible"])
        forged=copy.deepcopy(result["hourly_observation_log"][0])
        forged["feasibility_witness_stock_end_mwh_lhv"][0] += .05
        with self.assertRaisesRegex(AssertionError,"mass balance"):
            ORACLE.check_next_hour_witness(
                [1]*j.N,result["completed_15min_rows"],forged,0,.78)

    def test_independent_witness_rejects_changed_gas_floor(self):
        n,a=fixture()
        result=c.replay_causal(n,a,[1]*j.N,next_hour_gas_floor=.78)
        self.assertTrue(result["feasible"])
        forged=copy.deepcopy(result["hourly_observation_log"][0])
        forged["predeclared_next_hour_synthetic_gas_floor_mw_lhv"]+=.05
        with self.assertRaisesRegex(AssertionError,"Bound changed"):
            ORACLE.check_next_hour_witness(
                [1]*j.N,result["completed_15min_rows"],forged,0,.78)


if __name__=="__main__":
    unittest.main()
