"""BiogasFlex v0.9.8.1: adversarial numerical state and reference hardening.

Scientific data and original v0.7 / v0.9.7 models are intentionally untouched.
These are entirely synthetic fixtures with exact expected fuel/stock arithmetic.
"""
from __future__ import annotations

import copy
import unittest

from biogasflex.experimental_v098 import optimize_commitment_milp, evaluate_rolling_prices
from biogasflex.dispatch import DispatchError
from test_v098_rolling import config, times, snapshots


class MaintenanceContract(unittest.TestCase):
    def test_initial_power_observation_age_is_not_erased_by_first_replan(self):
        # Exactly 1 MW_LHV must burn in a single one-hour slot because
        # storage=0, initial/final stock=0, inflow=1 MW_LHV.
        # p_init=.2, p_slot=.4, ramp_up=.1 MW/h. Age 2h permits this
        # (.1 * (2+.5) = .25 MW); replacing age by zero makes it infeasible.
        c=config(n=1,gas_storage_capacity_mwh_lhv=0.0)
        c["experimental_v098"]={
            **c["experimental_v098"],
            "initial_power_mw_e":0.2,
            "initial_power_observation_age_hours":2.0,
            "ramp_up_mw_e_per_hour":0.1,
            "ramp_down_mw_e_per_hour":0.1,
        }
        actual=times([100])
        single=optimize_commitment_milp(c,actual)
        rolling=evaluate_rolling_prices(c,actual,snapshots(actual,[[100]]))
        self.assertAlmostEqual(single["net_contribution_eur"],40)
        self.assertAlmostEqual(rolling["rolling_realized_contribution_eur"],40)
        self.assertAlmostEqual(rolling["perfect_foresight_regret_eur"],0)
        self.assertAlmostEqual(rolling["hourly_executed"][0]["power_mw_e"],0.4)

    def test_invalid_initial_age_still_fails_closed(self):
        c=config(n=1)
        c["experimental_v098"]={
            **c["experimental_v098"],
            "initial_power_observation_age_hours":-0.25,
        }
        actual=times([100])
        with self.assertRaises(ValueError):
            evaluate_rolling_prices(c,actual,snapshots(actual,[[100]]))

    def test_fixed_nameplate_infeasible_but_flexible_storage_dispatch_feasible(self):
        # Fixed use [3,1] MW_LHV requires 1.2 MW_e in first hour
        # but nameplate is .8 MW_e. Flexible [2,2] stores then consumes
        # 1 MWh_LHV, delivers .8 MW_e in both hours, ends stock at 0.
        c=config(n=2,gas_production_mw_lhv=[3.0,1.0],
                 gas_storage_capacity_mwh_lhv=1.0)
        actual=times([20,50])
        result=optimize_commitment_milp(c,actual)
        self.assertEqual(result["fixed_reference_status"],"PHYSICALLY_INFEASIBLE")
        self.assertFalse(result["fixed_reference_feasible"])
        self.assertIsNone(result["fixed_reference_net_contribution_eur"])
        self.assertIsNone(result["increment_over_feasible_fixed_eur"])
        self.assertAlmostEqual(result["net_contribution_eur"],56)
        self.assertEqual([round(r["gas_use_mw_lhv"],6) for r in result["hourly"]],[2,2])
        self.assertEqual([round(r["stock_end_mwh_lhv"],6) for r in result["hourly"]],[1,0])
        self.assertAlmostEqual(result["optimized_dispatch"]["full_horizon_gas_residual_mwh"],0)

    def test_physically_invalid_fixed_reference_returns_null_in_rolling_study(self):
        c=config(n=2,gas_production_mw_lhv=[3.0,1.0],
                 gas_storage_capacity_mwh_lhv=1.0)
        actual=times([20,50])
        out=evaluate_rolling_prices(c,actual,snapshots(actual,[[20,50],[50]]))
        self.assertFalse(out["rolling_fixed_reference_feasible"])
        self.assertIsNone(out["realized_original_fixed_reference_net_eur"])
        self.assertIsNone(out["rolling_gain_over_feasible_fixed_eur"])
        self.assertAlmostEqual(out["rolling_realized_contribution_eur"],56)
        self.assertAlmostEqual(out["perfect_foresight_regret_eur"],0)

    def test_fixed_heat_backup_infeasible_but_flexible_heat_service_feasible(self):
        # Constant fixed gas-use from production only would yield .075 MW_th
        # in first hour, requiring .225 MW_th backup (> .1 MW_th cap).
        # Flexible operation draws from a predeclared 1 MWh_LHV initial
        # gas stock, meets heat, then replenishes it in hour 2.
        c=config(n=2,initial_gas_inventory_mwh_lhv=1.0,
                 gas_storage_capacity_mwh_lhv=1.0,
                 gas_production_mw_lhv=[0.25,1.75],
                 thermal_efficiency_lhv=0.3,
                 heat_demand_mw_th=0.3,
                 aux_heat_capacity_mw_th=0.1,
                 heat_dump_capacity_mw_th=0.5)
        c["experimental_v098"]={
            **c["experimental_v098"],
            "terminal_gas_inventory_mwh_lhv":1.0,
        }
        r=optimize_commitment_milp(c,times([20,50]))
        self.assertEqual(r["fixed_reference_status"],"PHYSICALLY_INFEASIBLE")
        self.assertIsNone(r["fixed_reference_net_contribution_eur"])
        self.assertLess(r["optimized_dispatch"]["max_heat_service_residual_mwh"],1e-8)
        self.assertAlmostEqual(r["optimized_dispatch"]["terminal_inventory_residual_mwh"],0)

    def test_old_synthetic_exact_price_oracle_and_feasible_fixed_reference_remain(self):
        c=config(n=3)
        actual=times([0,50,100])
        r=evaluate_rolling_prices(c,actual,snapshots(actual,[[100,0,0],[0,100],[100]]))
        self.assertAlmostEqual(r["rolling_realized_contribution_eur"],70)
        self.assertAlmostEqual(r["perfect_foresight_net_contribution_eur"],80)
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],10)
        single=optimize_commitment_milp(c,actual)
        self.assertEqual(single["fixed_reference_status"],"FEASIBLE")
        self.assertTrue(single["fixed_reference_feasible"])
        self.assertIsNotNone(single["fixed_reference_net_contribution_eur"])
        self.assertIsNotNone(single["increment_over_feasible_fixed_eur"])


if __name__=="__main__":
    unittest.main()
