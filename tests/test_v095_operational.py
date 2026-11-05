"""v0.9.5 experimental power ramp/min-load and forecast-regret oracles."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import math
import unittest

from biogasflex.baseline import Interval
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v095 import (
    EXPERIMENT, evaluate_fixed_forecast_schedule, optimize_operating_surrogate,
)


def synthetic(**changes):
    cfg = {
        "case_id":"v095_two_interval_synthetic", "price_zone":"SE3",
        "gas_input_mw_lhv":1.0, "electric_efficiency_lhv":0.4,
        "thermal_efficiency_lhv":0.0, "electric_rating_mw":0.8,
        "gas_storage_capacity_mwh_lhv":0.5,
        "initial_gas_inventory_mwh_lhv":0.0,
        "fixed_flaring_mw_lhv":0.0, "fixed_losses_mw_lhv":0.0,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":0.2, "aux_heat_capacity_mw_th":0.5,
        "heat_dump_capacity_mw_th":0.5, "aux_heat_cost_eur_per_mwh_th":10.0,
        "heat_dump_penalty_eur_per_mwh_th":0.0,
        "chp_variable_cost_eur_per_mwh_e":0.0,
        "experimental_v095": {
            "model":EXPERIMENT, "ramp_up_mw_e_per_hour":0.1,
            "ramp_down_mw_e_per_hour":0.1, "minimum_power_mw_e":0.0,
            "initial_power_mw_e":0.4,
        },
    }
    cfg.update(changes)
    return cfg


def prices(values=(0.0,100.0), durations=(1.0,1.0), start=None):
    t = start or datetime(2020,1,1,tzinfo=timezone.utc)
    rows = []
    for p,d in zip(values,durations):
        rows.append(Interval(t,p,d,"SE3"))
        t += timedelta(hours=d)
    return rows


class OperatingSurrogateTests(unittest.TestCase):
    def test_two_interval_ramp_analytical_five_euro_increment(self):
        result = optimize_operating_surrogate(synthetic(),prices())
        # With p0=0.4 MWe at the boundary, dt0/2=0.5 h limits
        # u0 >= 0.875. Cyclic gas requires u1=1.125.
        self.assertAlmostEqual(result["hourly"][0]["electric_power_mw_e"],0.35)
        self.assertAlmostEqual(result["hourly"][1]["electric_power_mw_e"],0.45)
        self.assertAlmostEqual(result["incremental_contribution_eur"],5.0)
        self.assertAlmostEqual(
            result["unconstrained_optimal_contribution_upper_bound_eur"]
            - result["fixed_dispatch"]["economic_contribution_proxy_eur"],20.0)
        self.assertLessEqual(result["max_ramp_violation_mw_e"],1e-8)

    def test_zero_ramp_forces_constant_output(self):
        cfg = synthetic()
        cfg["experimental_v095"] = dict(cfg["experimental_v095"],
                                         ramp_up_mw_e_per_hour=0.0,
                                         ramp_down_mw_e_per_hour=0.0)
        r = optimize_operating_surrogate(cfg,prices())
        self.assertAlmostEqual(r["incremental_contribution_eur"],0.0)
        self.assertTrue(all(abs(h["electric_power_mw_e"]-0.4)<1e-8 for h in r["hourly"]))

    def test_minimum_always_on_output_reduces_opportunity(self):
        cfg = synthetic()
        cfg["experimental_v095"] = dict(cfg["experimental_v095"],
                                         ramp_up_mw_e_per_hour=100.0,
                                         ramp_down_mw_e_per_hour=100.0,
                                         minimum_power_mw_e=0.36)
        r = optimize_operating_surrogate(cfg,prices())
        self.assertAlmostEqual(r["hourly"][0]["electric_power_mw_e"],0.36)
        self.assertAlmostEqual(r["incremental_contribution_eur"],4.0)

    def test_unrestricted_ramp_matches_unconstrained(self):
        cfg = synthetic()
        cfg["experimental_v095"] = dict(cfg["experimental_v095"],
                                         ramp_up_mw_e_per_hour=100.0,
                                         ramp_down_mw_e_per_hour=100.0)
        r = optimize_operating_surrogate(cfg,prices())
        self.assertAlmostEqual(r["incremental_contribution_eur"],20.0)
        self.assertAlmostEqual(
            r["optimized_dispatch"]["economic_contribution_proxy_eur"],
            r["unconstrained_optimal_contribution_upper_bound_eur"],places=6)

    def test_irregular_interval_midpoint_ramps(self):
        r = optimize_operating_surrogate(synthetic(),prices(durations=(0.5,1.5)))
        p = [h["electric_power_mw_e"] for h in r["hourly"]]
        self.assertLessEqual(abs(p[0]-0.4),0.1*0.25+1e-8)
        self.assertLessEqual(abs(p[1]-p[0]),0.1*1.0+1e-8)
        self.assertAlmostEqual(r["hourly"][0]["stock_end_mwh_lhv"],
                               r["hourly"][1]["stock_start_mwh_lhv"])
        self.assertGreaterEqual(r["incremental_contribution_eur"],-1e-7)

    def test_positive_heat_demand_and_cogenerated_heat(self):
        cfg = synthetic(thermal_efficiency_lhv=0.35,
                        heat_demand_mw_th=[0.28,0.36],
                        aux_heat_capacity_mw_th=0.4,
                        heat_dump_capacity_mw_th=0.4)
        r = optimize_operating_surrogate(cfg,prices())
        self.assertLess(r["optimized_dispatch"]["max_heat_service_residual_mwh"],1e-8)
        self.assertLess(r["optimized_dispatch"]["max_heat_conversion_residual_mwh"],1e-8)
        self.assertAlmostEqual(r["optimized_dispatch"]["heat_demand_mwh_th"],0.64)

    def test_capacity_zero_cannot_time_shift(self):
        r = optimize_operating_surrogate(synthetic(gas_storage_capacity_mwh_lhv=0.0),
                                         prices())
        self.assertAlmostEqual(r["incremental_contribution_eur"],0.0)

    def test_fixed_comparator_must_be_feasible_under_ramps(self):
        cfg = synthetic(gas_production_mw_lhv=[1.0,1.3])
        cfg["experimental_v095"] = dict(cfg["experimental_v095"],
                                         ramp_up_mw_e_per_hour=0,
                                         ramp_down_mw_e_per_hour=0)
        with self.assertRaisesRegex(DispatchError,"Fixed comparator"):
            optimize_operating_surrogate(cfg,prices())

    def test_explicit_opt_in_and_bad_metadata_fail_closed(self):
        bads = [
            {"experimental_v095":None},
            {"experimental_v095":{"model":EXPERIMENT}},
            {"experimental_v095":dict(synthetic()["experimental_v095"],
                                      model="unvalidated_unit_commitment")},
            {"experimental_v095":dict(synthetic()["experimental_v095"],
                                      minimum_power_mw_e=1.0)},
            {"experimental_v095":dict(synthetic()["experimental_v095"],
                                      initial_power_mw_e=True)},
            {"experimental_v095":dict(synthetic()["experimental_v095"],
                                      ramp_up_mw_e_per_hour=float("nan"))},
            {"experimental_v095":dict(synthetic()["experimental_v095"],
                                      ramp_down_mw_e_per_hour=-1.0)},
        ]
        for attrs in bads:
            with self.subTest(attrs=attrs), self.assertRaises(ValueError):
                optimize_operating_surrogate(synthetic(**attrs),prices())

    def test_uniform_price_shift_preserves_increment(self):
        base = optimize_operating_surrogate(synthetic(),prices())
        raised = optimize_operating_surrogate(synthetic(),prices((100,200)))
        self.assertAlmostEqual(base["incremental_contribution_eur"],
                               raised["incremental_contribution_eur"],places=6)
        self.assertAlmostEqual(
            raised["optimized_dispatch"]["economic_contribution_proxy_eur"]-
            base["optimized_dispatch"]["economic_contribution_proxy_eur"],80.0,places=6)


class ForecastRegretTests(unittest.TestCase):
    def _free(self):
        cfg = synthetic()
        cfg["experimental_v095"] = dict(cfg["experimental_v095"],
                                         ramp_up_mw_e_per_hour=100.0,
                                         ramp_down_mw_e_per_hour=100.0)
        return cfg

    def test_perfect_forecast_has_zero_regret(self):
        r = evaluate_fixed_forecast_schedule(self._free(),prices(),prices())
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],0.0)
        self.assertAlmostEqual(r["realized_increment_over_fixed_eur"],20.0)

    def test_reversed_price_signal_has_20_euro_regret_with_empty_initial_storage(self):
        r = evaluate_fixed_forecast_schedule(
            self._free(), prices((100,0)), prices((0,100)))
        self.assertAlmostEqual(r["realized_perfect_foresight_upper_bound_eur"],
                               60.0-4.0)
        self.assertAlmostEqual(r["perfect_foresight_regret_eur"],20.0)
        self.assertAlmostEqual(r["realized_increment_over_fixed_eur"],0.0)

    def test_forecast_misalignment_rejected(self):
        start = datetime(2020,1,2,tzinfo=timezone.utc)
        with self.assertRaises(ValueError):
            evaluate_fixed_forecast_schedule(self._free(),prices(),
                                             prices(start=start))

    def test_forecast_nonfinite_realization_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_fixed_forecast_schedule(
                self._free(),prices(),prices((float("nan"),100.0)))

    def test_regret_never_negative_for_different_valid_forecasts(self):
        for p in ((90,40),(100,-10),(-25,100),(10,10)):
            r = evaluate_fixed_forecast_schedule(
                self._free(),prices(p),prices((0,100)))
            self.assertGreaterEqual(r["perfect_foresight_regret_eur"],0.0)


if __name__ == "__main__":
    unittest.main()
