"""v0.9.7 synthetic clock-hour CHP commitment + solver-free two-slot oracle.

The 2-slot oracle enumerates four binary patterns and solves the remaining
gas inventory variable by interval endpoints, with NO SciPy or MILP calls.
It is exact only for this declared eta_th=0, two-slot, zero-cost-heat fixture.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from itertools import product
import math
import unittest

from biogasflex.baseline import Interval
from biogasflex.dispatch import DispatchError
from biogasflex.experimental_v097 import MODEL, optimize_commitment_milp


def scenario(**patch):
    c = {
        "case_id":"v097_synthetic_clock_hour_toy_NOT_PLANT",
        "price_zone":"SE3","electric_rating_mw":0.8,
        "electric_efficiency_lhv":0.4,"thermal_efficiency_lhv":0.0,
        "gas_input_mw_lhv":1.0,"gas_storage_capacity_mwh_lhv":0.25,
        "initial_gas_inventory_mwh_lhv":0.0,
        "fixed_flaring_mw_lhv":0.0,"fixed_losses_mw_lhv":0.0,
        "heat_service_model":"instantaneous_heat_service_no_thermal_store_v07",
        "heat_demand_mw_th":0.0,"aux_heat_capacity_mw_th":0.5,
        "heat_dump_capacity_mw_th":0.5,"aux_heat_cost_eur_per_mwh_th":0.0,
        "heat_dump_penalty_eur_per_mwh_th":0.0,
        "chp_variable_cost_eur_per_mwh_e":0.0,
        "experimental_v097":{
            "model":MODEL,"ramp_up_mw_e_per_hour":100.0,
            "ramp_down_mw_e_per_hour":100.0,"minimum_on_power_mw_e":0.2,
            "initial_on":False,"initial_power_mw_e":0.0,
            "startup_cost_eur":5.0,"shutdown_cost_eur":2.0,
            "minimum_up_hours":1.0,"minimum_down_hours":0.5,
            "initial_remaining_dwell_hours":0.0,
        },
    }
    c.update(patch)
    return c


def slots(durations=(0.25,1.0),prices=(0.0,100.0)):
    cur=datetime(2020,1,1,tzinfo=timezone.utc)
    rows=[]
    for d,p in zip(durations,prices):
        rows.append(Interval(cur,float(p),float(d),"SE3"))
        cur+=timedelta(hours=float(d))
    return rows


def oracle_two_slot(*,minimum_up=1.0,minimum_down=0.5,
                    initial_on=False,remaining=0.0,startup_cost=5.0,
                    shutdown_cost=2.0,prices=(0.0,100.0)):
    """Exact independent toy oracle in stock S1, no general-purpose solver.

    q0=q1=1 MW_LHV; dt=(1/4,1) hour; S0=S2=0; capacity=1/4.
    eta_e=0.4; on fuel 0.5..2 MW_LHV; zero useful/dumped/backup heat.
    u0=1-4*S1; u1=1+S1. Contribution affine in S1 for each pattern.
    """
    periods=(0.25,1.0)
    starts=(0.0,0.25)
    total=1.25
    best=None
    winning=None
    for states in product((0,1),repeat=2):
        yprev=int(initial_on)
        start_events=[]
        stop_events=[]
        eligible=True
        for i,y in enumerate(states):
            if starts[i] < remaining-1e-9 and y!=int(initial_on):
                eligible=False
            z=int(y==1 and yprev==0)
            v=int(y==0 and yprev==1)
            start_events.append(z)
            stop_events.append(v)
            if z or v:
                required=minimum_up if z else minimum_down
                deadline=starts[i]+required
                if deadline>total+1e-9:
                    eligible=False
                for j in range(i,2):
                    if starts[j]<deadline-1e-9 and states[j]!=y:
                        eligible=False
            yprev=y
        if not eligible:
            continue
        slo,shi=0.0,0.25
        # u=a+b*S1 for each period; impose exact on/off fuel bands.
        for i,y in enumerate(states):
            a,b=(1.0,-4.0) if i==0 else (1.0,1.0)
            lo,hi=(0.5,2.0) if y else (0.0,0.0)
            limits=sorted(((lo-a)/b,(hi-a)/b))
            slo=max(slo,limits[0])
            shi=min(shi,limits[1])
        if slo>shi+1e-10:
            continue
        for stock in (slo,shi):
            u0=1-4*stock
            u1=1+stock
            objective=(0.4*(u0*0.25*prices[0]+u1*prices[1])
                       -startup_cost*sum(start_events)
                       -shutdown_cost*sum(stop_events))
            if best is None or objective>best:
                best=objective
                winning={"on":list(states),"starts":start_events,
                         "stops":stop_events,"s1":stock}
    return best,winning


class HourCommitmentTests(unittest.TestCase):
    def run_case(self,**kwargs):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],**kwargs}
        return optimize_commitment_milp(c,slots())

    def test_exact_one_hour_from_last_long_interval(self):
        r=self.run_case(minimum_up_hours=1.0)
        value,path=oracle_two_slot(minimum_up=1.0)
        self.assertAlmostEqual(value,45.0)
        self.assertAlmostEqual(r["net_contribution_eur"],value)
        self.assertEqual(r["on"],path["on"])
        self.assertEqual(r["starts"],[0,1])
        self.assertEqual(r["clock_hours_from_horizon_start"],[0.0,0.25,1.25])
        self.assertAlmostEqual(r["increment_over_feasible_fixed_eur"],10.0)

    def test_one_hour_plus_small_margin_forces_earlier_start(self):
        r=self.run_case(minimum_up_hours=1.01)
        value,path=oracle_two_slot(minimum_up=1.01)
        self.assertAlmostEqual(value,40.0)
        self.assertAlmostEqual(r["net_contribution_eur"],value)
        self.assertEqual(r["on"],[1,1])

    def test_too_long_dwell_cannot_complete_by_horizon_end(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],"minimum_up_hours":1.26}
        self.assertIsNone(oracle_two_slot(minimum_up=1.26)[0])
        with self.assertRaises(DispatchError):
            optimize_commitment_milp(c,slots())

    def test_exact_oracle_for_sign_reversed_and_negative_prices(self):
        for prices in ((100.0,0.0),(-20.0,80.0),(100.0,-90.0),
                       (0.0,0.0),(15.0,15.0),(-100.0,200.0)):
            with self.subTest(prices=prices):
                m=optimize_commitment_milp(scenario(),slots(prices=prices))
                oracle,_=oracle_two_slot(prices=prices)
                self.assertIsNotNone(oracle)
                self.assertAlmostEqual(m["net_contribution_eur"],oracle,places=6)

    def test_prior_off_residual_forces_first_short_slot_off(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],
                                 "initial_remaining_dwell_hours":0.25}
        r=optimize_commitment_milp(c,slots())
        best,_=oracle_two_slot(remaining=0.25)
        self.assertAlmostEqual(r["net_contribution_eur"],best)
        self.assertEqual(r["on"],[0,1])

    def test_prior_off_residual_crosses_next_boundary_and_fails(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],
                                 "initial_remaining_dwell_hours":0.2501}
        self.assertIsNone(oracle_two_slot(remaining=0.2501)[0])
        with self.assertRaises(DispatchError):
            optimize_commitment_milp(c,slots())

    def test_prior_on_residual_blocks_profitable_early_shutdown(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],
                                 "initial_on":True,
                                 "initial_power_mw_e":0.4,
                                 "startup_cost_eur":0.0,
                                 "shutdown_cost_eur":0.0,
                                 "initial_remaining_dwell_hours":0.25}
        r=optimize_commitment_milp(c,slots())
        best,_=oracle_two_slot(initial_on=True,remaining=0.25,
                               startup_cost=0.0,shutdown_cost=0.0)
        self.assertAlmostEqual(best,45.0)
        self.assertAlmostEqual(r["net_contribution_eur"],best)
        self.assertEqual(r["on"],[1,1])
        # With no carried obligation the first 15-minute slot could shut down.
        c["experimental_v097"]["initial_remaining_dwell_hours"]=0.0
        free=optimize_commitment_milp(c,slots())
        self.assertEqual(free["on"],[0,1])
        self.assertAlmostEqual(free["net_contribution_eur"],50.0)

    def test_three_equal_one_hour_slots_agree_with_v096_oracles(self):
        for minimum,expected in ((1.0,55.0),(2.0,35.0),(3.0,15.0)):
            c=scenario(gas_input_mw_lhv=0.5,
                       gas_storage_capacity_mwh_lhv=1.0)
            c["experimental_v097"]={**c["experimental_v097"],
                                     "minimum_up_hours":minimum}
            with self.subTest(minimum=minimum):
                r=optimize_commitment_milp(c,
                                           slots((1,1,1),(0,0,100)))
                self.assertAlmostEqual(r["net_contribution_eur"],expected)
                self.assertAlmostEqual(
                    r["optimized_dispatch"]["max_interval_balance_residual_mwh"],0)

    def test_residual_dwell_can_continue_beyond_horizon_and_is_reported(self):
        c=scenario(gas_input_mw_lhv=0.0,gas_storage_capacity_mwh_lhv=0.0)
        c["experimental_v097"]={**c["experimental_v097"],
                                 "minimum_down_hours":2.0,
                                 "initial_remaining_dwell_hours":1.5}
        r=optimize_commitment_milp(c,slots())
        self.assertEqual(r["on"],[0,0])
        self.assertAlmostEqual(r["carry_in_remaining_after_horizon_hours"],0.25)
        self.assertEqual(r["start_count"],0)

    def test_fractional_minimum_down_horizon_completion(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],
                                 "minimum_down_hours":1.1}
        r=optimize_commitment_milp(c,slots())
        self.assertEqual(r["stop_count"],0)

    def test_fixed_comparator_infeasibility_reports_no_uplift(self):
        c=scenario()
        c["experimental_v097"]={**c["experimental_v097"],
                                 "minimum_on_power_mw_e":0.45}
        r=optimize_commitment_milp(c,slots())
        self.assertFalse(r["fixed_reference_feasible"])
        self.assertIsNone(r["increment_over_feasible_fixed_eur"])

    def test_positive_thermal_conversion_preserves_heat(self):
        c=scenario(thermal_efficiency_lhv=0.35,heat_demand_mw_th=0.2,
                   aux_heat_capacity_mw_th=0.4,heat_dump_capacity_mw_th=0.7,
                   aux_heat_cost_eur_per_mwh_th=11.0)
        r=optimize_commitment_milp(c,slots())
        self.assertLess(r["optimized_dispatch"]["max_heat_conversion_residual_mwh"],1e-8)
        self.assertLess(r["optimized_dispatch"]["max_heat_service_residual_mwh"],1e-8)

    def test_explicit_config_validation_rejects_invalid_hours_and_state(self):
        base=scenario()["experimental_v097"]
        bad=[
            None,{"model":MODEL},
            {**base,"minimum_up_hours":0},
            {**base,"minimum_down_hours":-0.1},
            {**base,"initial_remaining_dwell_hours":0.6},
            {**base,"initial_on":1},
            {**base,"initial_remaining_dwell_hours":float("nan")},
            {**base,"minimum_up_hours":True},
            {**base,"minimum_down_hours":float("inf")},
            {**base,"initial_power_mw_e":0.3},
            {**base,"minimum_on_power_mw_e":0},
            {**base,"startup_cost_eur":-1},
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    optimize_commitment_milp(scenario(experimental_v097=raw),
                                             slots())


if __name__ == "__main__":
    unittest.main()
