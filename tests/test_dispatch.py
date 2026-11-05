"""v0.6 numerical/physics regression tests independent of the solver's objective value."""
import copy
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from biogasflex.baseline import Interval, load_config, parse_prices
from biogasflex.dispatch import (DispatchError, optimize_dispatch, prepare_inputs,
                                 run_dispatch, run_sweep)

ROOT = Path(__file__).resolve().parents[1]
TOY = load_config(ROOT/'config/v06_oracle_two_period.json')
TOY_PRICES = parse_prices(ROOT/'data/synthetic/prices_2period_oracle.csv','SE3',
                          end_utc=TOY['price_window_end_utc'],required_hours=2)
LOVSTA = load_config(ROOT/'config/v06_lovsta_counterfactual.json')
LOVSTA_PRICES = parse_prices(ROOT/'data/observed/svk_se3_20200101_CC-BY-4.0.csv','SE3',
                             end_utc=LOVSTA['price_window_end_utc'],required_hours=24)


def intervals(prices, durations):
    t = datetime(2020,1,1,tzinfo=timezone.utc)
    rows=[]
    for price,d in zip(prices,durations):
        rows.append(Interval(t,float(price),float(d),'SE3'))
        t+=timedelta(hours=d)
    return rows


class ToyOracle(unittest.TestCase):
    def test_independent_two_period_analytic_optimum(self):
        """Independent algebra: u1=0.6-S1, u2=0.6+S1;
        p2<=0.4 implies S1<=0.4; R=60+60*S1, so optimum S1=0.4.
        """
        r=optimize_dispatch(TOY,TOY_PRICES)
        self.assertEqual(r['solver']['status_code'],0)
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'],60)
        self.assertAlmostEqual(r['optimized_dispatch']['gross_electricity_revenue_eur'],84)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],24)
        self.assertEqual(len(r['input_profile']),2)
        self.assertAlmostEqual(r['input_profile'][0]['optimized_gas_use_mw_lhv'],0.2)
        self.assertAlmostEqual(r['input_profile'][1]['optimized_gas_use_mw_lhv'],1.0)
        self.assertAlmostEqual(r['input_profile'][0]['stock_end_mwh_lhv'],0.4)
        self.assertAlmostEqual(r['input_profile'][1]['stock_end_mwh_lhv'],0.0)
        self.assertAlmostEqual(r['optimized_dispatch']['electricity_generated_mwh'],0.48)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_utilized_mwh_lhv'],1.2)
        self.assertAlmostEqual(r['optimized_dispatch']['max_interval_balance_residual_mwh'],0)

    def test_toy_sweep_plateaus_at_0p4(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run_sweep(ROOT/'config/v06_oracle_two_period.json',
                             ROOT/'data/synthetic/prices_2period_oracle.csv',Path(tmp)/'sweep.json')
        uplift=[v['incremental_gross_revenue_eur'] for v in result['cases']]
        for a,b in zip(uplift,[0,6,12,24,24]):self.assertAlmostEqual(a,b)

    def test_zero_storage_identical_schedule(self):
        r=optimize_dispatch(TOY,TOY_PRICES,capacity_mwh_lhv=0.0)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],0)
        self.assertTrue(all(abs(v['stock_end_mwh_lhv'])<1e-10 for v in r['input_profile']))

    def test_zero_upward_headroom(self):
        c={**TOY,'electric_rating_mw':0.24}
        r=optimize_dispatch(c,TOY_PRICES)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],0)
        self.assertAlmostEqual(r['optimized_dispatch']['max_over_rating_mw'],0)

    def test_flat_price_unchanged_gross_revenue(self):
        r=optimize_dispatch(TOY,intervals([30,30],[1,1]))
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],0)
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'],14.4)

    def test_negative_market_price_shifting(self):
        r=optimize_dispatch(TOY,intervals([-20,100],[1,1]))
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'],19.2)
        self.assertAlmostEqual(r['optimized_dispatch']['gross_electricity_revenue_eur'],38.4)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],19.2)

    def test_nonzero_fixed_flaring_and_losses_are_not_avoided(self):
        c={**TOY,'gas_input_mw_lhv':0.7,'fixed_flaring_mw_lhv':0.05,'fixed_losses_mw_lhv':0.05}
        r=optimize_dispatch(c,TOY_PRICES)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],24)
        self.assertAlmostEqual(r['fixed_dispatch']['gas_flared_mwh_lhv'],0.1)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_lost_mwh_lhv'],0.1)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_produced_mwh_lhv'],1.4)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_utilized_mwh_lhv'],1.2)

    def test_unequal_intervals_conserve_gas(self):
        rows=intervals([50,200],[0.25,1.0])
        c={**TOY, 'gas_storage_capacity_mwh_lhv':0.1}
        r=optimize_dispatch(c,rows)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_utilized_mwh_lhv'],0.75)
        self.assertAlmostEqual(r['optimized_dispatch']['electricity_generated_mwh'],0.3)
        self.assertLess(r['optimized_dispatch']['max_interval_balance_residual_mwh'],1e-10)
        self.assertGreaterEqual(r['gross_incremental_revenue_eur'],-1e-8)

    def test_starting_inventory_cyclic_not_depleted(self):
        c={**TOY,'initial_gas_inventory_mwh_lhv':0.1}
        r=optimize_dispatch(c,TOY_PRICES)
        self.assertAlmostEqual(r['optimized_dispatch']['terminal_inventory_residual_mwh'],0)
        self.assertAlmostEqual(r['input_profile'][0]['stock_start_mwh_lhv'],0.1)
        self.assertAlmostEqual(r['input_profile'][-1]['stock_end_mwh_lhv'],0.1)

    def test_infeasible_solver_does_not_write_valid_result(self):
        c={**TOY,'gas_input_mw_lhv':1.3}
        with self.assertRaisesRegex(DispatchError,'HiGHS did not find'):
            optimize_dispatch(c,TOY_PRICES)

    def test_infeasible_fixed_comparator_not_used(self):
        c={**TOY,'gas_production_mw_lhv':[1.1,0.1]}
        # Dispatch with a buffer is feasible; must-run comparison would exceed rating in period 1.
        with self.assertRaisesRegex(DispatchError,'Fixed comparator infeasible'):
            optimize_dispatch(c,TOY_PRICES)

    def test_reject_nonphysical_inputs(self):
        cases=[{'electric_efficiency_lhv':0}, {'electric_efficiency_lhv':0.9},
               {'thermal_efficiency_lhv':0.9},{'gas_storage_capacity_mwh_lhv':-1},
               {'initial_gas_inventory_mwh_lhv':0.5}, {'fixed_flaring_mw_lhv':0.7},
               {'gas_input_mw_lhv':-0.5}]
        for update in cases:
            with self.subTest(update=update),self.assertRaises(ValueError):
                optimize_dispatch({**TOY,**update},TOY_PRICES)

    def test_reject_gap_between_intervals(self):
        with self.assertRaisesRegex(ValueError,'Gap or overlap'):
            optimize_dispatch(TOY,[TOY_PRICES[0],Interval(TOY_PRICES[1].start_utc+timedelta(hours=1),200,1,'SE3')])

    def test_reject_missing_price_terminal_boundary(self):
        c={k:v for k,v in TOY.items() if k!='price_window_end_utc'}
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'config.json';f.write_text(json.dumps(c))
            with self.assertRaisesRegex(ValueError,'explicit price_window_end_utc'):
                run_dispatch(f,ROOT/'data/synthetic/prices_2period_oracle.csv',Path(tmp)/'out.json')

    def test_reject_wrong_terminal_timestamp(self):
        with self.assertRaisesRegex(ValueError,'terminal interval'):
            parse_prices(ROOT/'data/synthetic/prices_2period_oracle.csv','SE3',end_utc='2020-01-01T03:00:00+00:00')

    def test_input_file_hashes_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'result.json'
            r=run_dispatch(ROOT/'config/v06_oracle_two_period.json',ROOT/'data/synthetic/prices_2period_oracle.csv',p)
            self.assertEqual(len(r['provenance']['config_sha256']),64)
            self.assertEqual(json.loads(p.read_text())['gross_incremental_revenue_eur'],24)


class ReferenceCase(unittest.TestCase):
    def test_lovsta_24h_baseline_equals_v05(self):
        from biogasflex.baseline import baseline
        original=baseline(load_config(ROOT/'config/lovsta_2022_avg_with_se3_2020_prices.json'),LOVSTA_PRICES)
        r=optimize_dispatch(LOVSTA,LOVSTA_PRICES)
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'], original['gross_electricity_revenue_eur'])
        self.assertAlmostEqual(r['fixed_dispatch']['electricity_generated_mwh'],original['electricity_generated_mwh'])

    def test_lovsta_24h_energy_conservation(self):
        r=optimize_dispatch(LOVSTA,LOVSTA_PRICES)
        ledger=r['optimized_dispatch']
        self.assertAlmostEqual(ledger['gas_produced_mwh_lhv'], ledger['gas_utilized_mwh_lhv'])
        self.assertAlmostEqual(ledger['electricity_generated_mwh'],ledger['gas_utilized_mwh_lhv']*0.4)
        self.assertAlmostEqual(ledger['potential_heat_generated_mwh'],ledger['gas_utilized_mwh_lhv']*LOVSTA['thermal_efficiency_lhv'])
        self.assertLess(ledger['max_interval_balance_residual_mwh'],1e-8)
        self.assertGreater(r['gross_incremental_revenue_eur'],0)

    def test_predeclared_lovsta_sweep_contains_zero_and_monotonic(self):
        with tempfile.TemporaryDirectory() as tmp:
            s=run_sweep(ROOT/'config/v06_lovsta_counterfactual.json',
                        ROOT/'data/observed/svk_se3_20200101_CC-BY-4.0.csv',Path(tmp)/'r.json')
        a=s['cases'];self.assertEqual([v['capacity_mwh_lhv'] for v in a],[0,0.1,0.25,0.5,1.0,2.0])
        self.assertAlmostEqual(a[0]['incremental_gross_revenue_eur'],0)
        self.assertTrue(all(a[i+1]['optimal_revenue_eur']>=a[i]['optimal_revenue_eur']-1e-8 for i in range(len(a)-1)))

    def test_zero_upward_headroom_even_with_real_prices(self):
        baseline_rating=LOVSTA['gas_input_mw_lhv']*LOVSTA['electric_efficiency_lhv']
        c={**LOVSTA,'electric_rating_mw':baseline_rating}
        r=optimize_dispatch(c,LOVSTA_PRICES)
        self.assertAlmostEqual(r['gross_incremental_revenue_eur'],0,places=7)

    def test_verified_24_hour_utc_window(self):
        self.assertEqual(LOVSTA_PRICES[0].start_utc.isoformat(),'2019-12-31T23:00:00+00:00')
        self.assertEqual((LOVSTA_PRICES[-1].start_utc+timedelta(hours=LOVSTA_PRICES[-1].hours)).isoformat(),'2020-01-01T23:00:00+00:00')
        self.assertAlmostEqual(sum(r.hours for r in LOVSTA_PRICES),24)


if __name__ == '__main__':unittest.main()
