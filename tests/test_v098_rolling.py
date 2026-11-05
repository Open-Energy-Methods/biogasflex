"""v0.9.8 synthetic price-only receding-horizon controls, boundary and oracle tests.

Independent expected revenue uses two/three-period analytical fuel transfer
constraints, not SciPy nor production MILP code for the oracles.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import math
import unittest

from biogasflex.baseline import Interval
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v098 import MODEL,optimize_commitment_milp,evaluate_rolling_prices


def config(*,n=3,**change):
    d={
        "case_id":"v098_entirely_synthetic_rolling_prices",
        "price_zone":"SE3","electric_rating_mw":0.8,
        "electric_efficiency_lhv":0.4,"thermal_efficiency_lhv":0.0,
        "gas_input_mw_lhv":1.0,"gas_storage_capacity_mwh_lhv":0.5,
        "initial_gas_inventory_mwh_lhv":0.0,
        "fixed_flaring_mw_lhv":0.0,"fixed_losses_mw_lhv":0.0,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":0.0,"aux_heat_capacity_mw_th":0.5,
        "heat_dump_capacity_mw_th":0.5,"aux_heat_cost_eur_per_mwh_th":0.0,
        "heat_dump_penalty_eur_per_mwh_th":0.0,
        "chp_variable_cost_eur_per_mwh_e":0.0,
        "experimental_v098":{
            "model":MODEL,"ramp_up_mw_e_per_hour":100.0,
            "ramp_down_mw_e_per_hour":100.0,
            "minimum_on_power_mw_e":0.2,
            "initial_on":True,"initial_power_mw_e":0.4,
            "initial_power_observation_age_hours":0.0,
            "startup_cost_eur":5.0,"shutdown_cost_eur":2.0,
            "minimum_up_hours":1.0,"minimum_down_hours":1.0,
            "initial_remaining_dwell_hours":0.0,
            "terminal_gas_inventory_mwh_lhv":0.0,
        },
    }
    d.update(change)
    return d


def times(prices):
    first=datetime(2020,1,1,tzinfo=timezone.utc)
    return [Interval(first+timedelta(hours=i),float(p),1.0,"SE3")
            for i,p in enumerate(prices)]


def snapshots(actual,prices):
    return [
        [Interval(row.start_utc,float(p),row.hours,row.zone)
         for row,p in zip(actual[t:],suffix)]
        for t,suffix in enumerate(prices)
    ]


class RollingForecastTests(unittest.TestCase):
    def study(self,realized,forecast,**change):
        return evaluate_rolling_prices(config(n=len(realized),**change),
                                       times(realized),
                                       snapshots(times(realized),forecast))

    def test_reversed_two_interval_forecast_exact_independent_20_euro_regret(self):
        # Invented CHP: 1 MW_LHV constant inflow, 0 initial stock, 0.5MWh cap,
        # eta_e=.4. u0 is in [0.5,1], u1=2-u0.
        # Full hindsight actual prices [0,100]: u0=.5, u1=1.5 => EUR 60.
        # Wrong initial forecast [100,0]: u0=1, u1=1 => EUR 40 ex post.
        result=self.study([0,100],[[100,0],[100]])
        self.assertAlmostEqual(result["rolling_realized_contribution_eur"],40)
        self.assertAlmostEqual(result["perfect_foresight_net_contribution_eur"],60)
        self.assertAlmostEqual(result["perfect_foresight_regret_eur"],20)
        self.assertEqual([v["gas_use_mw_lhv"] for v in result["hourly_executed"]],[1,1])
        self.assertEqual(result["steps_executed"],2)

    def test_perfect_price_predictions_obtain_zero_regret(self):
        actual=[0,50,100]
        result=self.study(actual,[actual,actual[1:],actual[2:]])
        self.assertAlmostEqual(result["rolling_realized_contribution_eur"],80)
        self.assertAlmostEqual(result["perfect_foresight_regret_eur"],0)
        self.assertAlmostEqual(result["hourly_executed"][1]["stock_start_mwh_lhv"],0.5)
        self.assertAlmostEqual(result["terminal_inventory_mwh_lhv"],0)
        self.assertTrue(all(p["forecast_plan_continuous_relaxation_bound_eur"]>=
                            p["forecast_plan_value_eur"]-1e-6
                            for p in result["hourly_executed"]))

    def test_updated_forecast_recovers_ten_euros_against_fixed_forecast(self):
        actual=[0,50,100]
        # Fresh forecast at t=1 recognizes the high final price.
        revised=self.study(actual,[[100,0,0],[0,100],[100]])
        static=self.study(actual,[[100,0,0],[100,0],[100]])
        self.assertAlmostEqual(revised["rolling_realized_contribution_eur"],70)
        self.assertAlmostEqual(static["rolling_realized_contribution_eur"],60)
        self.assertAlmostEqual(revised["perfect_foresight_net_contribution_eur"],80)
        self.assertAlmostEqual(revised["perfect_foresight_regret_eur"],10)
        self.assertAlmostEqual(static["perfect_foresight_regret_eur"],20)
        self.assertAlmostEqual(revised["rolling_realized_contribution_eur"]-
                               static["rolling_realized_contribution_eur"],10)
        self.assertAlmostEqual(revised["hourly_executed"][1]["gas_use_mw_lhv"],0.5)
        self.assertAlmostEqual(static["hourly_executed"][1]["gas_use_mw_lhv"],1)

    def test_realistic_full_horizon_gas_target_not_reset_at_each_replan(self):
        actual=[0,50,100]
        result=self.study(actual,[actual,actual[1:],actual[2:]])
        self.assertEqual([v["stock_start_mwh_lhv"] for v in result["hourly_executed"]],
                         [0.0,0.5,0.5])
        self.assertAlmostEqual(result["original_initial_and_terminal_gas_inventory_mwh_lhv"],0)
        self.assertAlmostEqual(result["realized_physical_and_contribution_ledger"]["terminal_inventory_residual_mwh"],0)
        # The intermediate plan is NOT cyclic about its intermediate 0.5MWh
        # stock, so the old fixed cyclic comparator must not be used.
        self.assertAlmostEqual(result["hourly_executed"][1]["stock_end_mwh_lhv"],0.5)

    def test_operating_switch_state_and_start_stop_cost_carried_across_replans(self):
        actual=[0,0,100]
        c=config(gas_input_mw_lhv=0.0,
                 gas_production_mw_lhv=[1.0,0.0,1.0],
                 gas_storage_capacity_mwh_lhv=0.0)
        r=evaluate_rolling_prices(c,times(actual),
                                  snapshots(times(actual),[actual,actual[1:],actual[2:]]))
        self.assertEqual([v["on"] for v in r["hourly_executed"]],[1,0,1])
        self.assertEqual([v["startup"] for v in r["hourly_executed"]],[0,0,1])
        self.assertEqual([v["shutdown"] for v in r["hourly_executed"]],[0,1,0])
        self.assertAlmostEqual(r["total_realized_start_cost_eur"],5)
        self.assertAlmostEqual(r["total_realized_stop_cost_eur"],2)
        self.assertAlmostEqual(r["rolling_realized_contribution_eur"],33)
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],0)
        self.assertFalse(r["hourly_executed"][2]["previous_on"])

    def test_original_inventory_target_must_be_explicit_cycle_for_comparison(self):
        c=config()
        c["experimental_v098"]={**c["experimental_v098"],
                                "terminal_gas_inventory_mwh_lhv":0.3}
        a=times([0,0,100])
        with self.assertRaises(ValueError):
            evaluate_rolling_prices(c,a,snapshots(a,[[0,0,100],[0,100],[100]]))

    def test_direct_noncyclic_suffix_honors_initial_and_distinct_target(self):
        c=config(n=2,initial_gas_inventory_mwh_lhv=0.5)
        c["experimental_v098"]={**c["experimental_v098"],
                                "terminal_gas_inventory_mwh_lhv":0}
        r=optimize_commitment_milp(c,times([0,100]))
        self.assertAlmostEqual(r["hourly"][0]["stock_end_mwh_lhv"],0.5)
        self.assertAlmostEqual(r["hourly"][-1]["stock_end_mwh_lhv"],0)
        self.assertAlmostEqual(r["optimized_dispatch"]["terminal_inventory_residual_mwh"],0)
        self.assertAlmostEqual(r["optimized_dispatch"]["full_horizon_gas_residual_mwh"],0)
        self.assertFalse(r["fixed_reference_feasible"])
        self.assertIsNone(r["increment_over_feasible_fixed_eur"])
        self.assertGreaterEqual(r["same_boundary_LP_relaxation_upper_bound_eur"]+1e-7,
                                r["net_contribution_eur"])

    def test_negative_realized_prices_do_not_invalidate_hindsight_bound(self):
        r=self.study([-50,-10,75],[[100,0,0],[10,50],[75]])
        self.assertGreaterEqual(r["perfect_foresight_regret_eur"],-1e-8)
        self.assertAlmostEqual(r["realized_physical_and_contribution_ledger"]["full_horizon_gas_residual_mwh"],0)

    def test_non_price_heat_cost_and_demand_stay_in_realized_ledger(self):
        r=self.study([0,50,100],
                     [[100,0,0],[0,100],[100]],
                     thermal_efficiency_lhv=0.3,
                     heat_demand_mw_th=0.2,
                     aux_heat_capacity_mw_th=0.4,
                     heat_dump_capacity_mw_th=0.5,
                     aux_heat_cost_eur_per_mwh_th=10.0)
        l=r["realized_physical_and_contribution_ledger"]
        self.assertLess(l["max_heat_conversion_residual_mwh"],1e-8)
        self.assertLess(l["max_heat_service_residual_mwh"],1e-8)
        self.assertGreaterEqual(r["perfect_foresight_regret_eur"],0)

    def test_mismatched_forecast_horizon_counts_rejected(self):
        a=times([0,50,100])
        c=config()
        for snapshots_bad in ([],[a[:]],[[a[0]],[a[1]], [a[2]]],
                              [a,a[1:]]):
            with self.subTest(snapshots_bad=snapshots_bad):
                with self.assertRaises(ValueError):
                    evaluate_rolling_prices(c,a,snapshots_bad)

    def test_forecasts_require_identical_utc_grid_and_market_zone(self):
        a=times([0,100])
        predicted=snapshots(a,[[100,0],[100]])
        invalid=[
            [[Interval(a[0].start_utc+timedelta(minutes=15),100,1,"SE3"),predicted[0][1]],predicted[1]],
            [[Interval(a[0].start_utc,100,.25,"SE3"),predicted[0][1]],predicted[1]],
            [[Interval(a[0].start_utc,100,1,"SE2"),predicted[0][1]],predicted[1]],
            [[Interval(a[0].start_utc,float("nan"),1,"SE3"),predicted[0][1]],predicted[1]],
        ]
        for bad in invalid:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                evaluate_rolling_prices(config(n=2),a,bad)

    def test_opt_in_strict_parameter_validation(self):
        c=config(n=2)
        a=times([0,100])
        base=c["experimental_v098"]
        bad=[None,{"model":MODEL},{**base,"initial_power_observation_age_hours":-1},
             {**base,"terminal_gas_inventory_mwh_lhv":0.6},
             {**base,"terminal_gas_inventory_mwh_lhv":float("inf")},
             {**base,"minimum_up_hours":0},
             {**base,"initial_on":1}]
        for value in bad:
            with self.subTest(value=value),self.assertRaises(ValueError):
                optimize_commitment_milp({**c,"experimental_v098":value},a)

    def test_replanned_midpoint_ramp_timing_is_previous_half_plus_next_half(self):
        a=times([0,100])
        c=config(n=2)
        c["experimental_v098"]={**c["experimental_v098"],
                                 "ramp_up_mw_e_per_hour":0.1,
                                 "ramp_down_mw_e_per_hour":0.1}
        planned=optimize_commitment_milp(c,a)
        snap=snapshots(a,[[0,100],[100]])
        actual=evaluate_rolling_prices(c,a,snap)
        self.assertGreaterEqual(actual["perfect_foresight_regret_eur"],0)
        self.assertLessEqual(actual["max_steady_on_ramp_violation_mw_e"],1e-7)
        self.assertAlmostEqual(actual["rolling_realized_contribution_eur"],
                               planned["net_contribution_eur"],places=6)

    def test_roll_rejects_inconsistent_negative_inventory_reference(self):
        a=times([0,100])
        c=config(n=2,initial_gas_inventory_mwh_lhv=-0.1)
        with self.assertRaises(ValueError):
            evaluate_rolling_prices(c,a,snapshots(a,[[0,100],[100]]))

    def test_forecast_price_no_replanning_is_still_a_forecast_only_comparison(self):
        a=times([0,100])
        r=evaluate_rolling_prices(config(n=2),a,
                                  snapshots(a,[[0,100],[100]]))
        self.assertAlmostEqual(r["rolling_gain_over_feasible_fixed_eur"],20)
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],0)
        self.assertEqual(len(r["hourly_executed"]),2)


if __name__=="__main__":
    unittest.main()
