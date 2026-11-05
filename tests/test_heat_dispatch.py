"""v0.7: analytical heat-feasibility and economic-boundary regression tests."""
import copy
import hashlib
import json
import math
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src'))
from biogasflex.baseline import Interval, load_config, parse_prices
from biogasflex.dispatch import DispatchError, optimize_dispatch
from biogasflex.heat_dispatch import (optimize_heat_dispatch, prepare_heat_inputs,
                                       run_heat_dispatch, _ledger, _audit_ledger)
ROOT=Path(__file__).resolve().parents[1]
TOY=load_config(ROOT/'config/v07_oracle_two_period_heat.json')
TOY_PRICES=parse_prices(ROOT/'data/synthetic/prices_2period_oracle.csv','SE3',end_utc=TOY['price_window_end_utc'],required_hours=2)
LOVSTA=load_config(ROOT/'config/v07_lovsta_heat_proxy.json')
LOVSTA_PRICES=parse_prices(ROOT/'data/observed/svk_se3_20200101_CC-BY-4.0.csv','SE3',end_utc=LOVSTA['price_window_end_utc'],required_hours=24)

def cp(**change):
    cfg=copy.deepcopy(TOY)
    cfg.update(change)
    return cfg

def special_intervals(prices,dt):
    t=datetime(2020,1,1,tzinfo=timezone.utc)
    res=[]
    for p,d in zip(prices,dt):
        res.append(Interval(t,float(p),float(d),'SE3'))
        t+=timedelta(hours=d)
    return res

class HeatAnalyticalOracle(unittest.TestCase):
    def test_80_eur_backup_exact_analytic_solution(self):
        """With S1=s, electricity=60+60s; backup=0.45s, cost=80*0.45s.
        Contribution=60+24s; max s=0.4 -> 69.60 EUR; baseline=60 EUR.
        """
        r=optimize_heat_dispatch(TOY,TOY_PRICES)
        self.assertEqual(r['solver']['status_code'],0)
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'],60)
        self.assertAlmostEqual(r['optimized_dispatch']['gross_electricity_revenue_eur'],84)
        self.assertAlmostEqual(r['optimized_dispatch']['auxiliary_heat_cost_eur'],14.4)
        self.assertAlmostEqual(r['optimized_dispatch']['economic_contribution_proxy_eur'],69.6)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],9.6)
        self.assertAlmostEqual(r['incremental_gross_electricity_value_eur'],24)
        self.assertAlmostEqual(r['optimized_dispatch']['useful_chp_heat_delivered_mwh_th'],0.36)
        self.assertAlmostEqual(r['optimized_dispatch']['auxiliary_heat_delivered_mwh_th'],0.18)
        self.assertAlmostEqual(r['optimized_dispatch']['heat_dumped_mwh_th'],0.18)
        self.assertAlmostEqual(r['optimized_dispatch']['heat_demand_mwh_th'],0.54)
        self.assertEqual(len(r['input_profile']),2)
        self.assertAlmostEqual(r['input_profile'][0]['stock_end_mwh_lhv'],0.4)
        self.assertAlmostEqual(r['input_profile'][1]['stock_end_mwh_lhv'],0)
        self.assertAlmostEqual(r['input_profile'][0]['optimized_auxiliary_heat_mw_th'],0.18)
        self.assertAlmostEqual(r['input_profile'][1]['optimized_heat_dump_mw_th'],0.18)

    def test_20_eur_heat_cost_analytic_uplift(self):
        # 60s electricity value - 0.45*20*s heat penalty -> 51s, * 0.4 = 20.4 EUR.
        r=optimize_heat_dispatch(cp(aux_heat_cost_eur_per_mwh_th=20),TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],20.4)
        self.assertAlmostEqual(r['change_in_auxiliary_heat_cost_eur'],3.6)

    def test_200_eur_auxiliary_cost_zero_uplift(self):
        # Shifting s would change objective by (60-0.45*200)s = -30s.
        r=optimize_heat_dispatch(cp(aux_heat_cost_eur_per_mwh_th=200),TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0,places=7)
        self.assertAlmostEqual(r['incremental_gross_electricity_value_eur'],0,places=7)
        self.assertAlmostEqual(r['optimized_dispatch']['auxiliary_heat_delivered_mwh_th'],0,places=7)

    def test_no_backup_means_fixed_output_when_thermally_binding(self):
        r=optimize_heat_dispatch(cp(aux_heat_capacity_mw_th=0),TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0)
        self.assertAlmostEqual(r['optimized_dispatch']['auxiliary_heat_delivered_mwh_th'],0)

    def test_no_heat_sink_cancels_shifting(self):
        r=optimize_heat_dispatch(cp(heat_dump_capacity_mw_th=0),TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0)
        self.assertAlmostEqual(r['optimized_dispatch']['heat_dumped_mwh_th'],0)

    def test_zero_storage_equals_feasible_baseline(self):
        r=optimize_heat_dispatch(TOY,TOY_PRICES,capacity_mwh_lhv=0)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0)
        self.assertAlmostEqual(r['optimized_dispatch']['auxiliary_heat_cost_eur'],0)

    def test_no_heat_load_reduces_to_v06_electricity_oracle(self):
        c=cp(heat_demand_mw_th=0,aux_heat_cost_eur_per_mwh_th=0,heat_dump_capacity_mw_th=0.6)
        h=optimize_heat_dispatch(c,TOY_PRICES)
        e=optimize_dispatch(TOY,TOY_PRICES)
        self.assertAlmostEqual(h['optimized_dispatch']['gross_electricity_revenue_eur'],e['optimized_dispatch']['gross_electricity_revenue_eur'])
        self.assertAlmostEqual(h['incremental_economic_contribution_proxy_eur'],24)
        self.assertAlmostEqual(h['optimized_dispatch']['heat_dumped_mwh_th'],0.54)
        self.assertAlmostEqual(h['optimized_dispatch']['auxiliary_heat_delivered_mwh_th'],0)

    def test_zero_cost_demand_still_prioritizes_direct_chp_heat(self):
        c=cp(aux_heat_cost_eur_per_mwh_th=0,heat_dump_penalty_eur_per_mwh_th=0)
        r=optimize_heat_dispatch(c,TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],24)
        for p in r['input_profile']:
            self.assertLess(min(p['optimized_auxiliary_heat_mw_th'],p['optimized_heat_dump_mw_th']),1e-8)

    def test_heat_dump_penalty_reduces_value(self):
        r=optimize_heat_dispatch(cp(heat_dump_penalty_eur_per_mwh_th=20),TOY_PRICES)
        # Net marginal shift 60 - 0.45*(80+20) = 15 per MWhgas, uplift=6 EUR.
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],6)
        self.assertAlmostEqual(r['change_in_heat_dump_penalty_eur'],3.6)

    def test_variable_chp_cost_cancels_if_equal_generation(self):
        r=optimize_heat_dispatch(cp(chp_variable_cost_eur_per_mwh_e=10),TOY_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],9.6)
        self.assertAlmostEqual(r['change_in_chp_variable_cost_eur'],0)
        self.assertAlmostEqual(r['fixed_dispatch']['chp_variable_cost_eur'],4.8)

    def test_flat_price_with_positive_backup_cost_no_positive_uplift(self):
        r=optimize_heat_dispatch(TOY,special_intervals([30,30],[1,1]))
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0)

    def test_negative_early_price_still_heat_constrained(self):
        r=optimize_heat_dispatch(TOY,special_intervals([-20,100],[1,1]))
        # Price timing = 0.4*(100-(-20))*0.4 = 19.2 EUR, backup 14.4 EUR.
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],4.8)

    def test_variable_timestep_keeps_both_conservation_laws(self):
        r=optimize_heat_dispatch(cp(heat_demand_mw_th=[0.27,0.27]),special_intervals([50,200],[0.25,1]))
        self.assertAlmostEqual(r['optimized_dispatch']['max_interval_balance_residual_mwh'],0,places=8)
        self.assertAlmostEqual(r['optimized_dispatch']['max_heat_conversion_residual_mwh'],0,places=8)
        self.assertAlmostEqual(r['optimized_dispatch']['max_heat_service_residual_mwh'],0,places=8)
        self.assertAlmostEqual(r['fixed_dispatch']['heat_demand_mwh_th'],0.3375)

    def test_varying_heat_demand_profiles_supported(self):
        r=optimize_heat_dispatch(cp(heat_demand_mw_th=[0.2,0.3]),TOY_PRICES)
        self.assertAlmostEqual(r['fixed_dispatch']['heat_demand_mwh_th'],0.5)
        self.assertAlmostEqual(r['optimized_dispatch']['heat_demand_mwh_th'],0.5)

    def test_common_fixed_flaring_losses_do_not_create_extra_gas(self):
        c=cp(gas_input_mw_lhv=0.7,fixed_flaring_mw_lhv=0.05,fixed_losses_mw_lhv=0.05)
        r=optimize_heat_dispatch(c,TOY_PRICES)
        self.assertAlmostEqual(r['fixed_dispatch']['gas_flared_mwh_lhv'],0.1)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_lost_mwh_lhv'],0.1)
        self.assertAlmostEqual(r['optimized_dispatch']['gas_utilized_mwh_lhv'],1.2)

    def test_nonzero_initial_gas_stock_cycles(self):
        r=optimize_heat_dispatch(cp(initial_gas_inventory_mwh_lhv=0.2),TOY_PRICES)
        self.assertAlmostEqual(r['input_profile'][0]['stock_start_mwh_lhv'],0.2)
        self.assertAlmostEqual(r['input_profile'][-1]['stock_end_mwh_lhv'],0.2)


class HeatInvalidInput(unittest.TestCase):
    def test_missing_model_identifier_rejected(self):
        c=cp();del c['heat_service_model']
        with self.assertRaises(ValueError): optimize_heat_dispatch(c,TOY_PRICES)

    def test_missing_heat_demand_rejected(self):
        c=cp();del c['heat_demand_mw_th']
        with self.assertRaises(ValueError): optimize_heat_dispatch(c,TOY_PRICES)

    def test_missing_heat_cost_rejected(self):
        c=cp();del c['aux_heat_cost_eur_per_mwh_th']
        with self.assertRaises(ValueError): optimize_heat_dispatch(c,TOY_PRICES)

    def test_negative_price_is_allowed_but_negative_demand_rejected(self):
        with self.assertRaises(ValueError): optimize_heat_dispatch(cp(heat_demand_mw_th=-.01),TOY_PRICES)

    def test_nan_heat_cost_rejected(self):
        with self.assertRaises(ValueError): optimize_heat_dispatch(cp(aux_heat_cost_eur_per_mwh_th=float('nan')),TOY_PRICES)

    def test_negative_dump_penalty_rejected(self):
        with self.assertRaises(ValueError): optimize_heat_dispatch(cp(heat_dump_penalty_eur_per_mwh_th=-1),TOY_PRICES)

    def test_invalid_length_rejected(self):
        with self.assertRaises(ValueError): optimize_heat_dispatch(cp(heat_demand_mw_th=[0.2]),TOY_PRICES)

    def test_bool_value_rejected(self):
        with self.assertRaises(ValueError): optimize_heat_dispatch(cp(aux_heat_capacity_mw_th=True),TOY_PRICES)

    def test_auxiliary_capacity_infeasible_fixed_rejected(self):
        # Max heat output at baseline is 0.27 MWth, demand 0.5, backup cap 0.1.
        with self.assertRaises(DispatchError):
            optimize_heat_dispatch(cp(heat_demand_mw_th=0.5,aux_heat_capacity_mw_th=0.1),TOY_PRICES)

    def test_dump_capacity_infeasible_fixed_rejected(self):
        with self.assertRaises(DispatchError):
            optimize_heat_dispatch(cp(heat_demand_mw_th=0.0,heat_dump_capacity_mw_th=0.2),TOY_PRICES)

    def test_unrealistic_generator_baseline_rejected(self):
        with self.assertRaises(DispatchError):optimize_heat_dispatch(cp(electric_rating_mw=0.2),TOY_PRICES)

    def test_negative_heat_flow_in_recomputed_ledger_is_caught(self):
        inp=prepare_heat_inputs(TOY,TOY_PRICES)
        wrong=_ledger(inp,[0.6,0.6],[0,0,0],[0.27,0.27],[-0.01,0.01],[0,0])
        with self.assertRaises(DispatchError):_audit_ledger(inp,wrong)

    def test_solver_error_never_reported_as_zero_uplift(self):
        # Gas would violate rated CHP capacity over horizon even with flexible store.
        with self.assertRaises(DispatchError):
            optimize_heat_dispatch(cp(gas_input_mw_lhv=1.3),TOY_PRICES)

    def test_requires_terminal_price_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=cp();del c['price_window_end_utc']
            config=Path(tmp)/'config.json'
            config.write_text(json.dumps(c),encoding='utf8')
            with self.assertRaises(ValueError):
                run_heat_dispatch(config,ROOT/'data/synthetic/prices_2period_oracle.csv',Path(tmp)/'result.json')

    def test_output_hash_and_recomputation(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'out.json'
            r=run_heat_dispatch(ROOT/'config/v07_oracle_two_period_heat.json',
                                ROOT/'data/synthetic/prices_2period_oracle.csv',target)
            self.assertTrue(target.exists())
            self.assertEqual(r['provenance']['config_sha256'],hashlib.sha256((ROOT/'config/v07_oracle_two_period_heat.json').read_bytes()).hexdigest())
            reloaded=json.loads(target.read_text())
            self.assertAlmostEqual(reloaded['optimized_dispatch']['economic_contribution_proxy_eur'],
                                   reloaded['optimized_dispatch']['gross_electricity_revenue_eur']
                                   -reloaded['optimized_dispatch']['auxiliary_heat_cost_eur']
                                   -reloaded['optimized_dispatch']['heat_dump_penalty_eur']
                                   -reloaded['optimized_dispatch']['chp_variable_cost_eur'])

class SourceBoundary(unittest.TestCase):
    def test_observed_prices_integrity_preserved(self):
        self.assertEqual(len(LOVSTA_PRICES),24)
        self.assertTrue(all(r.zone=='SE3' and r.hours==1 for r in LOVSTA_PRICES))
        self.assertAlmostEqual(sum(r.price_eur_per_mwh for r in LOVSTA_PRICES),665.68,places=4)

    def test_lovsta_heat_proxy_matches_public_annual_totals_algebraically(self):
        self.assertAlmostEqual(LOVSTA['heat_demand_mw_th']*8760,2939.5)
        self.assertAlmostEqual(LOVSTA['gas_input_mw_lhv']*LOVSTA['electric_efficiency_lhv']*8760,3002.6,places=3)
        self.assertAlmostEqual(LOVSTA['gas_input_mw_lhv']*LOVSTA['thermal_efficiency_lhv']*8760,2939.5,places=3)

    def test_lovsta_cost_80_null_uplift_not_mislabeled_actual(self):
        r=optimize_heat_dispatch(LOVSTA,LOVSTA_PRICES)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0,places=6)
        self.assertAlmostEqual(r['fixed_dispatch']['gross_electricity_revenue_eur'],228.1701789954,places=6)
        self.assertIn('not calibrated',r['claim_boundary'].lower())
        self.assertAlmostEqual(r['fixed_dispatch']['heat_demand_mwh_th'],2939.5/365,places=6)

    def test_optimized_contribution_never_below_fixed_in_lovsta_cost_sweep(self):
        for price in (0,5,20,80,200):
            r=optimize_heat_dispatch({**LOVSTA,'aux_heat_cost_eur_per_mwh_th':price},LOVSTA_PRICES)
            self.assertGreaterEqual(r['incremental_economic_contribution_proxy_eur'],-1e-7)
            self.assertAlmostEqual(r['fixed_dispatch']['heat_demand_mwh_th'],r['optimized_dispatch']['heat_demand_mwh_th'],places=7)
            self.assertAlmostEqual(r['fixed_dispatch']['gas_utilized_mwh_lhv'],r['optimized_dispatch']['gas_utilized_mwh_lhv'],places=7)

if __name__ == '__main__':unittest.main()
