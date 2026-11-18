"""v0.9.24 hard contracted MWh and independent award-meter adversarial checks."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
import unittest

from biogasflex import award_v0924 as a24
from biogasflex import causal_v0922 as c
from biogasflex import joint_v0921 as j


def audit_module():
    path=Path(__file__).resolve().parents[1]/"scripts"/"audit_v0924_award_independent.py"
    spec=importlib.util.spec_from_file_location("v0924_award_independent",path)
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


ORACLE=audit_module()


def fixture():
    nominal={
        "price_eur_mwh":[40+2*(t//4) for t in range(j.N)],
        "synthetic_gas_production_mw_lhv":[1.0]*j.N,
        "synthetic_site_heat_demand_mw_th":[.15]*j.N,
    }
    realized=copy.deepcopy(nominal)
    realized["price_eur_mwh"]=[50+3*(t//4) for t in range(j.N)]
    return nominal,realized


class ExactAwardCausalTests(unittest.TestCase):
    def test_exact_export_per_quarter_without_reserve(self):
        n,actual=fixture()
        awarded=[.10]*j.N
        r=c.replay_causal(n,actual,[1]*j.N,awarded_export_mwh=awarded)
        self.assertTrue(r["feasible"],r.get("failure_reason"))
        self.assertEqual(len(r["completed_15min_rows"]),24)
        for row in r["completed_15min_rows"]:
            self.assertAlmostEqual(row["gas_use_mw_lhv"],1.0,places=8)
            self.assertAlmostEqual(row["physical_chp_export_meter_mwh"],.1,places=9)
            self.assertAlmostEqual(row["contract_awarded_export_mwh"],.1,places=9)
        self.assertAlmostEqual(r["executed_physical_chp_meter_export_mwh_total"],2.4)
        self.assertEqual(r["contract_export_shortfall_mwh"],0.)
        self.assertFalse(r["contract_import_or_forgiveness_modeled"])
        self.assertTrue(ORACLE.independent_award_replay_check(
            [1]*j.N,{"quarter_hour_export_mwh":awarded,
                    "pre_reveal_award_sha256":a24.award_hash(awarded)},
            r,"award_only"))

    def test_exact_award_preserved_in_next_hour_lower_gas_witness(self):
        n,actual=fixture()
        awarded=[.09]*j.N
        r=c.replay_causal(n,actual,[1]*j.N,
                          next_hour_gas_floor=.78,
                          awarded_export_mwh=awarded)
        self.assertTrue(r["feasible"],r.get("failure_reason"))
        self.assertEqual(len(r["hourly_observation_log"]),6)
        for hour in range(5):
            witness=r["hourly_observation_log"][hour]
            for use in witness["feasibility_witness_gas_use_mw_lhv"]:
                self.assertAlmostEqual(.4*.25*use,.09,places=8)
        self.assertEqual(ORACLE.independent_award_replay_check(
            [1]*j.N,{"quarter_hour_export_mwh":awarded,
                    "pre_reveal_award_sha256":a24.award_hash(awarded)},
            r,"award_and_reserve"),24)

    def test_initial_ramp_stress_is_infeasible_without_hidden_buy_or_slack(self):
        n,actual=fixture()
        r=c.replay_causal(n,actual,[1]*j.N,
                          awarded_export_mwh=[.15]*j.N,
                          next_hour_gas_floor=.78)
        self.assertFalse(r["feasible"])
        self.assertEqual(r["failed_hour"],0)
        self.assertIsNone(r["economic_contribution_eur"])
        self.assertFalse(r["hard_award_service_feasible"])
        self.assertEqual(r["completed_15min_rows"],[])
        self.assertTrue(ORACLE.independent_award_replay_check(
            [1]*j.N,{"quarter_hour_export_mwh":[.15]*j.N,
                    "pre_reveal_award_sha256":a24.award_hash([.15]*j.N)},
            r,"award_and_reserve")==0)

    def test_off_commitment_cannot_export_positive_award(self):
        n,actual=fixture()
        r=c.replay_causal(n,actual,[0]*j.N,awarded_export_mwh=[.09]*j.N)
        self.assertFalse(r["feasible"])
        self.assertIsNone(r["economic_contribution_eur"])

    def test_zero_award_cannot_hide_minimum_on_fuel_requirement(self):
        n,actual=fixture()
        r=c.replay_causal(n,actual,[1]*j.N,awarded_export_mwh=[0.]*j.N)
        self.assertFalse(r["feasible"])
        self.assertEqual(r["failed_hour"],0)

    def test_invalid_awards_rejected_without_optimizer(self):
        n,actual=fixture()
        for invalid in ([.09]*23,[.09]*25,
                        [.09]*23+[-.01],[.09]*23+[float("nan")],
                        [.09]*23+[float("inf")]):
            with self.subTest(invalid=invalid),self.assertRaisesRegex(ValueError,"Award vector"):
                c.replay_causal(n,actual,[1]*j.N,awarded_export_mwh=invalid)

    def test_future_realized_site_state_cannot_change_completed_prefix(self):
        n,actual=fixture()
        baseline=c.replay_causal(n,actual,[1]*j.N,
                                 awarded_export_mwh=[.09]*j.N,
                                 next_hour_gas_floor=.78)
        changed=copy.deepcopy(actual)
        for t in range(16,24):
            changed["synthetic_gas_production_mw_lhv"][t]=.80
            changed["synthetic_site_heat_demand_mw_th"][t]=.19
            changed["price_eur_mwh"][t]=-100.
        second=c.replay_causal(n,changed,[1]*j.N,
                               awarded_export_mwh=[.09]*j.N,
                               next_hour_gas_floor=.78)
        self.assertTrue(baseline["feasible"])
        self.assertTrue(second["feasible"])
        self.assertEqual(baseline["completed_15min_rows"][:16],
                         second["completed_15min_rows"][:16])

    def test_realized_prices_only_change_ex_post_cash_not_export_dispatch(self):
        n,actual=fixture()
        before=c.replay_causal(n,actual,[1]*j.N,
                               awarded_export_mwh=[.09]*j.N)
        new_actual=copy.deepcopy(actual)
        new_actual["price_eur_mwh"]=[-50.]*j.N
        after=c.replay_causal(n,new_actual,[1]*j.N,
                              awarded_export_mwh=[.09]*j.N)
        self.assertTrue(before["feasible"])
        self.assertTrue(after["feasible"])
        self.assertEqual([r["physical_chp_export_meter_mwh"]
                          for r in before["completed_15min_rows"]],
                         [r["physical_chp_export_meter_mwh"]
                          for r in after["completed_15min_rows"]])
        self.assertNotEqual(before["economic_contribution_eur"],
                            after["economic_contribution_eur"])

    def test_independent_auditor_rejects_forged_meter(self):
        n,actual=fixture()
        awards=[.09]*j.N
        r=c.replay_causal(n,actual,[1]*j.N,awarded_export_mwh=awards)
        self.assertTrue(r["feasible"])
        forged=copy.deepcopy(r)
        forged["completed_15min_rows"][1]["physical_chp_export_meter_mwh"]+=.01
        with self.assertRaisesRegex(AssertionError,"meter|export"):
            ORACLE.independent_award_replay_check(
                [1]*j.N,{"quarter_hour_export_mwh":awards,
                        "pre_reveal_award_sha256":a24.award_hash(awards)},
                forged,"award_only")

    def test_independent_auditor_rejects_witness_ignoring_award(self):
        n,actual=fixture()
        awards=[.09]*j.N
        r=c.replay_causal(n,actual,[1]*j.N,
                          next_hour_gas_floor=.78,awarded_export_mwh=awards)
        self.assertTrue(r["feasible"])
        forged=copy.deepcopy(r)
        forged["hourly_observation_log"][0]["feasibility_witness_gas_use_mw_lhv"][0]+=.10
        with self.assertRaises(AssertionError):
            ORACLE.independent_award_replay_check(
                [1]*j.N,{"quarter_hour_export_mwh":awards,
                        "pre_reveal_award_sha256":a24.award_hash(awards)},
                forged,"award_and_reserve")

    def test_awards_predeclared_are_target_independent_and_hashed(self):
        first=a24.predeclare_award_profiles()
        second=a24.predeclare_award_profiles()
        self.assertEqual(first,second)
        self.assertEqual(set(first),set(a24.AWARD_PROFILES_MWH_PER_QUARTER))
        for key,p in first.items():
            self.assertEqual(p["pre_reveal_award_sha256"],
                             a24.award_hash(p["quarter_hour_export_mwh"]))
            self.assertEqual(len(p["quarter_hour_export_mwh"]),j.N)


if __name__=="__main__":
    unittest.main()
