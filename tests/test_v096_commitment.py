"""Independent small-case enumeration and adversarial v0.9.6 MILP tests.

Independent oracle enumerates all feasible half-MW_LHV dispatch grid points
for deliberately constructed three-hour synthetic inputs. These are NOT
actual measured CHP load/startup values or a full general MILP verifier.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import product
import math
import unittest

from biogasflex.baseline import Interval
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v096 import MODEL, optimize_commitment_milp


def config(**changes):
    cfg = {
        "case_id":"v096_synthetic_commitment_oracle","price_zone":"SE3",
        "electric_rating_mw":0.8, "electric_efficiency_lhv":0.4,
        "thermal_efficiency_lhv":0.0,"gas_input_mw_lhv":0.5,
        "gas_storage_capacity_mwh_lhv":1.0,"initial_gas_inventory_mwh_lhv":0.0,
        "fixed_flaring_mw_lhv":0.0,"fixed_losses_mw_lhv":0.0,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":0.0,"aux_heat_capacity_mw_th":0.5,
        "heat_dump_capacity_mw_th":0.5,"aux_heat_cost_eur_per_mwh_th":0.0,
        "heat_dump_penalty_eur_per_mwh_th":0.0,"chp_variable_cost_eur_per_mwh_e":0.0,
        "experimental_v096":{
            "model":MODEL, "ramp_up_mw_e_per_hour":0.0,
            "ramp_down_mw_e_per_hour":0.0, "minimum_on_power_mw_e":0.2,
            "initial_on":False,"initial_power_mw_e":0.0,
            "startup_cost_eur":5.0,"shutdown_cost_eur":2.0,
            "minimum_up_intervals":1, "minimum_down_intervals":1,
        },
    }
    cfg.update(changes)
    return cfg


def times(prices=(0,0,100)):
    start=datetime(2020,1,1,tzinfo=timezone.utc)
    return [Interval(start+timedelta(hours=i),float(p),1.0,"SE3")
            for i,p in enumerate(prices)]


def half_grid_oracle(minimum_up=1, min_down=1, startup_cost=5.0):
    """Pure-Python exhaustive finite fixture oracle, no MILP or SciPy imports.

    This fixture uses hourly 0.5 MW_LHV gas supply, 0 initial gas,
    1 MWh_LHV maximum stock, eta_e=0.4, 0.2 MWe min-on (0.5 gas),
    no steady-on ramp allowance, and prices 0/0/100. For that
    constructed geometry all candidate objective vertices are on the
    0.5 MW_LHV fuel grid; it is not a general-purpose mathematical solver.
    """
    best=-float("inf")
    best_case=None
    choices=(0.0,0.5,1.0,1.5,2.0)
    for fuel in product(choices,repeat=3):
        if abs(sum(fuel)-1.5)>1e-9:
            continue
        s=0.0
        valid=True
        for u in fuel:
            s+=0.5-u
            if s < -1e-9 or s>1.0+1e-9:
                valid=False
        if not valid or abs(s)>1e-9:
            continue
        on=tuple(int(u>0) for u in fuel)
        previous=0
        starts=[];stops=[]
        for y in on:
            starts.append(int(y==1 and previous==0))
            stops.append(int(y==0 and previous==1))
            previous=y
        for i in range(3):
            if starts[i] and (i+minimum_up>3 or not all(on[i:i+minimum_up])):
                valid=False
            if stops[i] and (i+min_down>3 or any(on[i:i+min_down])):
                valid=False
            if i and on[i-1]==on[i]==1 and abs(fuel[i]-fuel[i-1])>1e-9:
                valid=False
        if not valid:
            continue
        value=40*fuel[2] - startup_cost*sum(starts) - 2*sum(stops)
        if value>best:
            best,best_case=value,{"use":fuel,"on":on,"starts":starts,"stops":stops}
    return best,best_case


class CommitmentMILPTests(unittest.TestCase):
    def test_exact_three_interval_oracle_base(self):
        r=optimize_commitment_milp(config(),times())
        value,case=half_grid_oracle()
        self.assertAlmostEqual(value,55)
        self.assertAlmostEqual(r["net_contribution_eur"],value)
        self.assertEqual(r["on"],[0,0,1])
        self.assertEqual(r["starts"],[0,0,1])
        self.assertEqual(r["stop_count"],0)
        self.assertAlmostEqual(r["unconstrained_LP_upper_bound_eur"],60)
        self.assertTrue(r["fixed_reference_feasible"])
        self.assertAlmostEqual(r["increment_over_feasible_fixed_eur"],40)

    def test_minimum_up_two_matches_exhaustive_oracle(self):
        c=config()
        c["experimental_v096"]=dict(c["experimental_v096"],minimum_up_intervals=2)
        r=optimize_commitment_milp(c,times())
        optimum,oracle=half_grid_oracle(minimum_up=2)
        self.assertAlmostEqual(optimum,35)
        self.assertAlmostEqual(r["net_contribution_eur"],optimum)
        self.assertEqual(r["on"],[0,1,1])

    def test_minimum_up_three_matches_exhaustive_oracle(self):
        c=config()
        c["experimental_v096"]=dict(c["experimental_v096"],minimum_up_intervals=3)
        r=optimize_commitment_milp(c,times())
        optimum,_=half_grid_oracle(minimum_up=3)
        self.assertAlmostEqual(optimum,15)
        self.assertAlmostEqual(r["net_contribution_eur"],optimum)
        self.assertEqual(r["on"],[1,1,1])

    def test_startup_cost_enforced(self):
        c=config()
        c["experimental_v096"]=dict(c["experimental_v096"],startup_cost_eur=12.0)
        r=optimize_commitment_milp(c,times())
        optimum,_=half_grid_oracle(startup_cost=12)
        self.assertAlmostEqual(optimum,48)
        self.assertAlmostEqual(r["net_contribution_eur"],optimum)
        self.assertAlmostEqual(r["startup_cost_eur"],12)

    def test_shutdown_and_restart_with_no_gas_in_between(self):
        c=config(gas_production_mw_lhv=[1,0,1],gas_storage_capacity_mwh_lhv=0.0)
        c["experimental_v096"]=dict(c["experimental_v096"],initial_on=True,
                                    initial_power_mw_e=0.4)
        r=optimize_commitment_milp(c,times((0,0,50)))
        self.assertEqual(r["on"],[1,0,1])
        self.assertEqual(r["starts"],[0,0,1])
        self.assertEqual(r["stops"],[0,1,0])
        self.assertAlmostEqual(r["startup_cost_eur"],5)
        self.assertAlmostEqual(r["shutdown_cost_eur"],2)
        self.assertAlmostEqual(r["net_contribution_eur"],13)

    def test_minimum_down_blocks_early_restart(self):
        c=config(gas_production_mw_lhv=[1,0,1],gas_storage_capacity_mwh_lhv=0.0)
        c["experimental_v096"]=dict(c["experimental_v096"],initial_on=True,
                                    initial_power_mw_e=0.4,
                                    minimum_down_intervals=2)
        with self.assertRaises(DispatchError):
            optimize_commitment_milp(c,times((0,0,50)))

    def test_positive_chp_heat_instantaneous_thermal_ledger(self):
        c=config(thermal_efficiency_lhv=0.35,heat_demand_mw_th=0.1,
                 aux_heat_capacity_mw_th=0.2,heat_dump_capacity_mw_th=0.6,
                 aux_heat_cost_eur_per_mwh_th=15.0)
        r=optimize_commitment_milp(c,times())
        self.assertLessEqual(r["optimized_dispatch"]["max_heat_service_residual_mwh"],1e-8)
        self.assertLessEqual(r["optimized_dispatch"]["max_heat_conversion_residual_mwh"],1e-8)
        self.assertAlmostEqual(r["optimized_dispatch"]["heat_demand_mwh_th"],0.3)

    def test_ramp_relaxation_when_switching_not_steady_operation(self):
        c=config(gas_production_mw_lhv=[1,0,1],gas_storage_capacity_mwh_lhv=0.0)
        c["experimental_v096"]=dict(c["experimental_v096"],initial_on=True,
                                    initial_power_mw_e=0.4,
                                    ramp_up_mw_e_per_hour=0,ramp_down_mw_e_per_hour=0)
        r=optimize_commitment_milp(c,times())
        self.assertAlmostEqual(r["max_steady_on_ramp_violation_mw_e"],0)

    def test_infeasible_reference_flagged_not_fabricated_as_uplift(self):
        c=config()
        c["experimental_v096"]=dict(c["experimental_v096"],
                                    minimum_on_power_mw_e=0.3)
        r=optimize_commitment_milp(c,times())
        self.assertFalse(r["fixed_reference_feasible"])
        self.assertIsNone(r["increment_over_feasible_fixed_eur"])

    def test_invalid_config_and_initial_conditions_fail_closed(self):
        baseline=config()["experimental_v096"]
        bad=[
            {"experimental_v096":None},
            {"experimental_v096":{"model":MODEL}},
            {"experimental_v096":dict(baseline,initial_on=1)},
            {"experimental_v096":dict(baseline,initial_power_mw_e=0.4)},
            {"experimental_v096":dict(baseline,minimum_on_power_mw_e=0)},
            {"experimental_v096":dict(baseline,minimum_on_power_mw_e=1)},
            {"experimental_v096":dict(baseline,minimum_up_intervals=True)},
            {"experimental_v096":dict(baseline,minimum_down_intervals=0)},
            {"experimental_v096":dict(baseline,startup_cost_eur=-1)},
            {"experimental_v096":dict(baseline,shutdown_cost_eur=float("nan"))},
        ]
        for item in bad:
            with self.subTest(bad=item),self.assertRaises(ValueError):
                optimize_commitment_milp(config(**item),times())

    def test_gas_inventory_never_negative(self):
        r=optimize_commitment_milp(config(),times())
        self.assertTrue(all(h["stock_end_mwh_lhv"]>=-1e-8 for h in r["hourly"]))
        self.assertLess(r["optimized_dispatch"]["max_interval_balance_residual_mwh"],1e-8)

    def test_no_generation_after_off_without_sufficient_storage(self):
        c=config(gas_storage_capacity_mwh_lhv=0)
        r=optimize_commitment_milp(c,times())
        self.assertEqual(r["on"],[1,1,1])
        self.assertAlmostEqual(r["net_contribution_eur"],15)

    def test_horizon_end_cannot_hide_unfinished_minimum_up_time(self):
        c=config()
        c["experimental_v096"]=dict(c["experimental_v096"],minimum_up_intervals=4)
        # A late start is forbidden; an initially off 3-slot horizon
        # must remain off, which cannot conserve 1.5 MWh with capacity 1.
        with self.assertRaises(DispatchError):
            optimize_commitment_milp(c,times())


if __name__=="__main__":
    unittest.main()
