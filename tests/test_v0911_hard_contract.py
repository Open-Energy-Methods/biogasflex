"""v0.9.11: independent awarded-delivery hard-equality MILP witnesses.

All cashflows, forecasts, accepted energy and plant assumptions are invented.
Tests distinguish a feasible-but-suboptimal contractual schedule from a
genuinely infeasible contractual schedule; no real market settlement.
"""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

from biogasflex.baseline import Interval
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v098 import optimize_commitment_milp
from biogasflex.market_v0910 import (
    HARD_CONTRACT_MODEL, MarketBoundaryError,
    audit_postclearing_delivery, run_manifest, validate_preclearing_offer,
)
from test_v0910_market_boundary import sample as legacy_sample

ROOT=Path(__file__).resolve().parents[1]


def fixture(quarterhour: bool = False):
    name="v0911_contract_quarterhour.json" if quarterhour else "v0911_contract_hourly.json"
    market=json.loads((ROOT/"examples"/name).read_text(encoding="utf-8"))
    cfg=json.loads((ROOT/"examples/v0911_synthetic_chp.json").read_text(encoding="utf-8"))
    return market, cfg


def physical_rows(manifest):
    return [Interval(
        __import__("datetime").datetime.fromisoformat(
            r["start_utc"].replace("Z","+00:00")),
        float(price), float(r["duration_hours"]), "SE3",
    ) for r,price in zip(
        manifest["delivery_slots"],
        manifest["exogenous_award"]["clearing_prices_eur_mwh"],
    )]


def strict_post(market, config, *, details=True):
    receipt=validate_preclearing_offer(
        market["market"], market["delivery_slots"],market["preclearing_offer"],
        config["electric_rating_mw"])
    return audit_postclearing_delivery(
        market["market"],market["delivery_slots"],receipt,
        market["exogenous_award"],config,include_solver_details=details,
        hard_contract=True)


class HardContractMILPTests(unittest.TestCase):
    def test_hourly_award_differs_from_unconstrained_preferred_dispatch(self):
        m,c=fixture()
        rows=physical_rows(m)
        unconstrained=optimize_commitment_milp(c,rows)
        power=[x["power_mw_e"] for x in unconstrained["hourly"]]
        self.assertAlmostEqual(power[0],0.4)
        self.assertAlmostEqual(power[1],0.4)
        self.assertNotEqual(power,m["exogenous_award"]["accepted_mwh"])

        result=strict_post(m,c)
        self.assertEqual(result["phase"],"POST_CLEARING_EXOGENOUS_AWARD_HARD_CONTRACT_MATCHED")
        self.assertTrue(result["accepted_delivery_enforced_inside_milp"])
        self.assertEqual(result["hard_award_equality_count"],2)
        self.assertAlmostEqual(result["gross_contract_cashflow_proxy_eur"],20.0)
        self.assertAlmostEqual(result["total_accepted_mwh"],0.8)
        self.assertAlmostEqual(result["synthetic_chp_operating_contribution_eur"],20.0)
        self.assertAlmostEqual(result["maximum_contract_vs_simulated_delivery_mwh"],0.0)
        self.assertEqual(result["simulated_delivered_mwh"],[0.2,0.6])
        solver=result["physical_solver_and_hourly"]
        self.assertEqual([round(x["gas_use_mw_lhv"],6) for x in solver["hourly"]],[0.5,1.5])
        self.assertEqual([round(x["stock_end_mwh_lhv"],6) for x in solver["hourly"]],[0.5,0.0])
        self.assertFalse(solver["fixed_reference_feasible"])
        self.assertEqual(solver["fixed_reference_status"],"DIFFERENT_CONTRACTED_DELIVERY")
        self.assertIsNone(solver["increment_over_feasible_fixed_eur"])
        self.assertLessEqual(solver["net_contribution_eur"],
                             solver["matched_contract_LP_relaxation_bound_eur"]+1e-7)
        self.assertLess(result["gas_balance_max_residual_mwh"],1e-8)
        self.assertLess(result["heat_service_max_residual_mwh"],1e-8)

    def test_quarter_hour_exact_mwh_not_mw(self):
        m,c=fixture(quarterhour=True)
        r=strict_post(m,c)
        self.assertEqual(r["hard_award_equality_count"],4)
        self.assertAlmostEqual(r["gross_contract_cashflow_proxy_eur"],9.0)
        self.assertAlmostEqual(r["total_accepted_mwh"],0.4)
        self.assertEqual([round(x,7) for x in r["simulated_delivered_mwh"]],
                         [0.05,0.15,0.1,0.1])
        self.assertEqual([round(x["power_mw_e"],7)
                          for x in r["physical_solver_and_hourly"]["hourly"]],
                         [0.2,0.6,0.4,0.4])
        self.assertEqual([round(x["stock_end_mwh_lhv"],7)
                          for x in r["physical_solver_and_hourly"]["hourly"]],
                         [0.125,0.0,0.0,0.0])
        self.assertLess(r["maximum_contract_vs_simulated_delivery_mwh"],1e-8)

    def test_legacy_v0910_comparison_still_rejects_nonpreferred_award(self):
        m,c=fixture()
        receipt=validate_preclearing_offer(
            m["market"],m["delivery_slots"],m["preclearing_offer"],c["electric_rating_mw"])
        with self.assertRaisesRegex(MarketBoundaryError,"UNMODELLED_IMBALANCE"):
            audit_postclearing_delivery(
                m["market"],m["delivery_slots"],receipt,
                m["exogenous_award"],c)
        legacy,c0=legacy_sample()
        r=audit_postclearing_delivery(
            legacy["market"],legacy["delivery_slots"],
            validate_preclearing_offer(
                legacy["market"],legacy["delivery_slots"],legacy["preclearing_offer"],
                c0["electric_rating_mw"]),
            legacy["exogenous_award"],c0)
        self.assertEqual(r["version"],"0.9.10")
        self.assertNotIn("accepted_delivery_enforced_inside_milp",r)

    def test_no_award_constraint_changes_legacy_solver_output(self):
        m,c=fixture()
        rows=physical_rows(m)
        a=optimize_commitment_milp(c,rows)
        b=optimize_commitment_milp(c,rows,contracted_delivery_mwh=None)
        self.assertEqual(a,b)
        self.assertNotIn("hard_contract_equalities_embedded_in_milp",a)

    def test_perfectly_matching_award_has_same_objective_as_legacy(self):
        m,c=fixture()
        m["exogenous_award"]["accepted_mwh"]=[0.4,0.4]
        m["preclearing_offer"]["offered_mwh"]=[0.4,0.6]
        unconstrained=optimize_commitment_milp(c,physical_rows(m))
        contracted=strict_post(m,c)
        self.assertAlmostEqual(contracted["synthetic_chp_operating_contribution_eur"],
                               unconstrained["net_contribution_eur"])
        self.assertTrue(contracted["physical_solver_and_hourly"]["fixed_reference_feasible"])

    def test_genuinely_unreachable_award_under_gas_storage_cap(self):
        m,c=fixture()
        c["gas_storage_capacity_mwh_lhv"]=0.1
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)
        # Same plant without extra award equality can still run at 0.4 MW.
        normal=optimize_commitment_milp(c,physical_rows(m))
        self.assertTrue(normal["solver"]["success"])

    def test_contract_infeasible_due_to_ramp_rate(self):
        m,c=fixture()
        c["experimental_v098"]["ramp_up_mw_e_per_hour"]=0.05
        c["experimental_v098"]["ramp_down_mw_e_per_hour"]=0.05
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)
        self.assertTrue(optimize_commitment_milp(c,physical_rows(m))["solver"]["success"])

    def test_contract_infeasible_due_to_aux_heat_service(self):
        m,c=fixture()
        c["heat_demand_mw_th"]=[0.25,0.15]
        c["aux_heat_capacity_mw_th"]=0.1
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)
        self.assertTrue(optimize_commitment_milp(c,physical_rows(m))["solver"]["success"])

    def test_contract_infeasible_due_to_terminal_inventory(self):
        m,c=fixture()
        c["experimental_v098"]["terminal_gas_inventory_mwh_lhv"]=0.1
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)

    def test_zero_accepted_award_cannot_leak_uncontracted_electricity(self):
        m,c=fixture()
        m["exogenous_award"]["accepted_mwh"]=[0,0]
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)

    def test_invalid_contract_length_units_and_nan_are_rejected_before_milp(self):
        m,c=fixture()
        rows=physical_rows(m)
        for bad in ([0.2],[0.2,0.6,0.0],[-0.1,0.6],
                    [float("nan"),0.6],[float("inf"),0.6],
                    [True,0.6],[0.81,0.6], "0.2,0.6"):
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                optimize_commitment_milp(c,rows,contracted_delivery_mwh=bad)

    def test_no_accidental_silent_award_overfill_or_underfill(self):
        m,c=fixture()
        m["exogenous_award"]["accepted_mwh"][1]=0.7
        with self.assertRaisesRegex(MarketBoundaryError,"exceeds"):
            strict_post(m,c)
        m,c=fixture()
        m["exogenous_award"]["accepted_mwh"][0]=0.1
        with self.assertRaisesRegex(MarketBoundaryError,"CONTRACT_INFEASIBLE"):
            strict_post(m,c)

    def test_postgate_prices_and_award_never_enter_preclear_validation(self):
        m,c=fixture()
        receipt=validate_preclearing_offer(
            m["market"],m["delivery_slots"],m["preclearing_offer"],c["electric_rating_mw"])
        self.assertFalse(receipt["clearing_prices_available"])
        self.assertIsNone(receipt["cashflow_eur"])
        self.assertIsNone(receipt["matched_energy_mwh"])
        self.assertNotIn("accepted_mwh",receipt)

    def test_hard_contract_respects_day_ahead_timeline(self):
        m,c=fixture()
        m["exogenous_award"]["prices_published_utc"]="2026-11-17T10:00:00Z"
        with self.assertRaisesRegex(MarketBoundaryError,"Auction result"):
            strict_post(m,c)
        m,c=fixture()
        m["exogenous_award"]["participant_result_received_utc"]="2026-11-17T23:10:00Z"
        with self.assertRaisesRegex(MarketBoundaryError,"Auction result"):
            strict_post(m,c)

    def test_hard_contract_zone_and_version_cannot_be_confused(self):
        m,c=fixture()
        c["price_zone"]="SE4"
        with self.assertRaisesRegex(MarketBoundaryError,"zone"):
            strict_post(m,c)
        m,c=fixture()
        m["model"]="preclearing_postclearing_exogenous_award_synthetic_chp_v0910"
        with self.assertRaisesRegex(MarketBoundaryError,"mismatched contract model"):
            path=ROOT/"examples/v0910_market_hourly.json"
            # Check strict version discrimination using existing named manifest.
            run_manifest(path,hard_contract=True)

    def test_manifest_versions_and_output_is_opt_in(self):
        for name,expected in (("v0911_contract_hourly.json",20.0),
                              ("v0911_contract_quarterhour.json",9.0)):
            data=run_manifest(ROOT/"examples"/name,hard_contract=True)
            self.assertEqual(data["model_type"],HARD_CONTRACT_MODEL)
            self.assertAlmostEqual(data["postclearing"]["gross_contract_cashflow_proxy_eur"],expected)
            self.assertNotIn("physical_solver_and_hourly",data["postclearing"])
        proc=subprocess.run([sys.executable,"-m","biogasflex","--help"],
                            cwd=ROOT,capture_output=True,text=True,check=True,timeout=20)
        self.assertIn("contract-dispatch",proc.stdout)

    def test_electricity_generation_not_claimed_to_be_metered_export(self):
        m,c=fixture()
        output=strict_post(m,c)
        self.assertFalse(output["actual_export_measurements_included"])
        self.assertFalse(output["imbalance_settlement_included"])
        self.assertFalse(output["market_profit_claimed"])
        self.assertIn("terminal generation",output["contract_boundary"])
        self.assertTrue(output["accepted_delivery_enforced_inside_milp"])

    def test_negative_clearing_price_remains_valid_inside_hard_contract(self):
        m,c=fixture()
        m["exogenous_award"]["clearing_prices_eur_mwh"]=[-30,20]
        out=strict_post(m,c)
        self.assertAlmostEqual(out["gross_contract_cashflow_proxy_eur"],6.0)

    def test_exact_hard_award_mwh_equality_present_in_lp_bound(self):
        m,c=fixture()
        normal=optimize_commitment_milp(c,physical_rows(m))
        hard=optimize_commitment_milp(c,physical_rows(m),
            contracted_delivery_mwh=m["exogenous_award"]["accepted_mwh"])
        self.assertTrue(hard["hard_contract_equalities_embedded_in_milp"])
        self.assertLessEqual(hard["net_contribution_eur"],
                             hard["same_boundary_LP_relaxation_upper_bound_eur"]+1e-7)
        self.assertAlmostEqual(hard["matched_contract_LP_relaxation_bound_eur"],20.0)
        self.assertLess(hard["matched_contract_LP_relaxation_bound_eur"],
                        normal["same_boundary_LP_relaxation_upper_bound_eur"]-1.0)


if __name__=="__main__":
    unittest.main()
