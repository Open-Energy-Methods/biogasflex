"""v0.9 adversarial provenance/physical contract and an independent toy oracle."""
from __future__ import annotations
import copy
import csv
from datetime import datetime,timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('v09_audit', ROOT/'scripts/audit_v09_candidate.py')
audit=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=audit
spec.loader.exec_module(audit)
from biogasflex.baseline import Interval
from biogasflex.heat_dispatch import optimize_heat_dispatch
from biogasflex.resilience import optimize_emergency_service
from biogasflex import __version__

REG=json.loads((ROOT/'scenarios/registry.json').read_text(encoding='utf8'))
BASE=json.loads((ROOT/'config/v07_lovsta_heat_proxy.json').read_text(encoding='utf8'))
ENTRIES=list(audit.scenario_grid(REG,BASE))
SAMPLE=ENTRIES[0]
with (ROOT/REG['market_windows'][0]['file']).open(newline='',encoding='utf8') as f:
    OBS=list(csv.DictReader(f))
with (ROOT/'results/v0.8/predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
    ROWS=list(csv.DictReader(f))
CASE=json.loads((ROOT/'results/v0.8/cases'/f'{SAMPLE["case_id"]}.json').read_text())
E_CASE=json.loads((ROOT/'results/v0.8/resilience/buffer_0p6.json').read_text())
E_ROWS={x['case_id']:x for x in csv.DictReader((ROOT/'results/v0.8/hypothetical_critical_service_results.csv').open(newline='',encoding='utf8'))}
E_COND=next(x for x in REG['resilience_cases'] if x['id']=='buffer_0p6')

def toy_config(*,p0=10.0,p1=60.0,capacity=.5,backup=5.0,dump=2.0):
    return dict(case_id='v09_two_interval_oracle',price_zone='SE3',
       electric_rating_mw=1.0,gas_input_mw_lhv=1.0,
       electric_efficiency_lhv=0.4,thermal_efficiency_lhv=0.5,
       gas_storage_capacity_mwh_lhv=capacity,initial_gas_inventory_mwh_lhv=0,
       fixed_flaring_mw_lhv=0,fixed_losses_mw_lhv=0,
       heat_service_model='instantaneous_heat_service_no_thermal_store_v07',
       heat_demand_mw_th=.5,aux_heat_capacity_mw_th=.5,
       heat_dump_capacity_mw_th=.25,aux_heat_cost_eur_per_mwh_th=backup,
       heat_dump_penalty_eur_per_mwh_th=dump,chp_variable_cost_eur_per_mwh_e=0)

def toy_intervals(p0,p1):
    return [Interval(datetime(2020,1,1,t,tzinfo=timezone.utc),p,1.,'SE3') for t,p in enumerate((p0,p1))]

class AuditContract(unittest.TestCase):
    def test_v09_runtime_and_package_metadata_agree(self):
        self.assertEqual(__version__,'0.9.3')
        self.assertIn('version = "0.9.3"',(ROOT/'pyproject.toml').read_text())
    def test_218_plus_3_scientific_gate(self):
        s=audit.audit(ROOT,verbose=False)
        self.assertEqual((s['market_cases_independently_recalculated'],s['emergency_cases_verified']),(216,5))
        self.assertEqual(s['source_registry_scenarios_reconstructed'],216)
    def test_pinned_snapshots_intact(self):
        self.assertEqual(len(audit.input_pins(ROOT)),5)
    def test_price_shares_same_declared_calendar_day(self):
        audit.check_market_contract(CASE,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_heat_requirement(self):
        d=copy.deepcopy(CASE)
        d['input_profile'][0]['heat_demand_mw_th']+=0.003
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_aux_cost(self):
        d=copy.deepcopy(CASE)
        d['input_profile'][0]['auxiliary_heat_cost_eur_per_mwh_th']+=10
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_source_price(self):
        d=copy.deepcopy(CASE)
        d['input_profile'][0]['price_eur_per_mwh']+=0.01
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_fuel(self):
        d=copy.deepcopy(CASE)
        d['input_profile'][0]['gas_production_mw_lhv']+=0.1
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_fixed_use(self):
        d=copy.deepcopy(CASE)
        d['input_profile'][0]['fixed_gas_use_mw_lhv']+=0.05
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_rating(self):
        d=copy.deepcopy(CASE)
        d['chp_electric_rating_mw']+=0.001
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(d,ROWS[0],SAMPLE,BASE,OBS)
    def test_reject_tampered_scenario_factor(self):
        r=copy.deepcopy(ROWS[0]);r['heat_demand_multiplier']='0.9'
        with self.assertRaises(audit.AuditFailure):audit.check_market_contract(CASE,r,SAMPLE,BASE,OBS)
    def test_reject_tampered_emergency_assumption(self):
        d=copy.deepcopy(E_CASE)
        d['assumptions']['electric_efficiency_lhv']+=.01
        with self.assertRaises(audit.AuditFailure):audit.check_emergency_contract(d,E_ROWS['buffer_0p6'],E_COND,REG['resilience_definition'])
    def test_reject_false_critical_service_fraction(self):
        r=copy.deepcopy(E_ROWS['buffer_0p6']);r['fraction_electric_served']='1.0'
        with self.assertRaises(audit.AuditFailure):audit.check_emergency_contract(E_CASE,r,E_COND,REG['resilience_definition'])
    def test_total_outage_must_have_zero_gas_inflow(self):
        cfg=copy.deepcopy(E_CASE['assumptions']);cfg['gas_inflow_mw_lhv']=0.01
        with self.assertRaisesRegex(ValueError,'total gas-inflow interruption'):
            optimize_emergency_service(cfg)
    def test_storage_oracle_known_optimal_boundary(self):
        cfg=toy_config()
        r=optimize_heat_dispatch(cfg,toy_intervals(10,60))
        # s1<=0.5 due to heat rejection capacity at t=1; objective rises with s1.
        # Gas flows (u0,u1)=(0.5,1.5), stock (0,0.5,0).
        self.assertAlmostEqual(r['input_profile'][0]['stock_end_mwh_lhv'],0.5,places=8)
        self.assertAlmostEqual(r['input_profile'][1]['optimized_gas_use_mw_lhv'],1.5,places=8)
        # Gross uplift = (60-10)*0.4*0.5=10 EUR;
        # backup = 0.25MWh*5=1.25, dump =0.25MWh*2=0.50.
        self.assertAlmostEqual(r['incremental_gross_electricity_value_eur'],10,places=8)
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],8.25,places=8)
    def test_no_upward_opportunity_when_flat_prices_and_no_heat_penalty(self):
        cfg=toy_config(p0=20,p1=20,backup=0,dump=0)
        r=optimize_heat_dispatch(cfg,toy_intervals(20,20))
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0,places=8)
    def test_oracle_zero_storage(self):
        cfg=toy_config(capacity=0)
        r=optimize_heat_dispatch(cfg,toy_intervals(10,60))
        self.assertAlmostEqual(r['incremental_economic_contribution_proxy_eur'],0,places=8)
    def test_uniform_price_translation_leaves_increment_unchanged(self):
        cfg=toy_config()
        a=optimize_heat_dispatch(cfg,toy_intervals(10,60))
        b=optimize_heat_dispatch(cfg,toy_intervals(35,85))
        # Equal generated electrical energy in fixed and flexible schedules.
        self.assertAlmostEqual(a['incremental_economic_contribution_proxy_eur'],
                               b['incremental_economic_contribution_proxy_eur'],places=7)
    def test_larger_storage_never_decreases_dispatch_contribution(self):
        vals=[]
        for cap in (0,0.1,0.3,0.5,0.8):
            cfg=toy_config(capacity=cap)
            r=optimize_heat_dispatch(cfg,toy_intervals(10,60))
            vals.append(r['optimized_dispatch']['economic_contribution_proxy_eur'])
        self.assertTrue(all(x<=y+1e-7 for x,y in zip(vals,vals[1:])))
    def test_negative_prices_do_not_create_negative_optimized_uplift(self):
        cfg=toy_config()
        r=optimize_heat_dispatch(cfg,toy_intervals(-30,30))
        self.assertGreaterEqual(r['incremental_economic_contribution_proxy_eur'],-1e-7)
    def test_unavailable_chp_precludes_outage_service(self):
        cfg=copy.deepcopy(E_CASE['assumptions']);cfg['island_capable']=False
        r=optimize_emergency_service(cfg)
        self.assertAlmostEqual(r['energy_totals']['electric_served_mwh'],0,places=9)
        self.assertAlmostEqual(r['energy_totals']['heat_served_mwh_th'],0,places=9)

if __name__=='__main__':unittest.main()
