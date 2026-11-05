"""v0.8 preregistered markets, source QA, physical emergency LP, and tamper checks."""
from __future__ import annotations
import copy
import csv
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('v08audit',ROOT/'scripts/independent_v08_audit.py')
audit=importlib.util.module_from_spec(spec)
sys.modules['v08audit']=audit;spec.loader.exec_module(audit)
from biogasflex.baseline import parse_prices
from biogasflex.heat_dispatch import optimize_heat_dispatch
from biogasflex.resilience import optimize_emergency_service
REG=json.loads((ROOT/'scenarios/registry.json').read_text(encoding='utf8'))
RESULT=ROOT/'results/v0.8'


def emergency(**changes):
    base={
        'case_id':'toy_blackout','duration_hours':3,
        'gas_inflow_mw_lhv':0,'electric_efficiency_lhv':0.4,
        'thermal_efficiency_lhv':0.3915939519083461,'chp_electric_rating_mw':0.499,
        'gas_storage_capacity_mwh_lhv':0.6,'initial_stock_mwh_lhv':0.6,
        'critical_electric_load_mw':0.12,'critical_heat_load_mw':0.1,
        'island_capable':True,'chp_available':True,'grid_available':False,'auxiliary_heat_available':False}
    base.update(changes);return base


class MarketEvidence(unittest.TestCase):
    def test_registry_is_exactly_expected_matrix_size(self):
        n= len(REG['market_windows'])*len(REG['gas_storage_mwh_lhv'])*len(REG['heat_demand_factors_of_2022_annual_mean_production'])*len(REG['assumed_backup_cost_eur_mwh_th'])*len(REG['electrical_efficiency_lhv'])*len(REG['rating_variants'])
        self.assertEqual(n,216)
        self.assertEqual(n,REG['scenario_count_expected'])

    def test_seasonal_days_separated(self):
        self.assertEqual([w['civil_date'] for w in REG['market_windows']],['2020-01-01','2020-04-01','2020-10-01'])

    def test_rejected_july_flagged_no_imputation(self):
        self.assertEqual(REG['rejected_window']['civil_date'],'2020-07-01')
        self.assertEqual(REG['rejected_window']['imputation'],'none')

    def test_all_three_market_windows_24_hours_without_gaps(self):
        for w in REG['market_windows']:
            with self.subTest(window=w['id']):
                rows=parse_prices(ROOT/w['file'],'SE3',end_utc=w['end_utc'],required_hours=24)
                self.assertEqual(len(rows),24)
                self.assertTrue(all(r.hours==1.0 for r in rows))

    def test_apr_price_sum_primary_api(self):
        w=REG['market_windows'][1]
        rows=parse_prices(ROOT/w['file'],'SE3',end_utc=w['end_utc'],required_hours=24)
        self.assertAlmostEqual(sum(x.price_eur_per_mwh for x in rows),167.71)
        self.assertEqual(rows[0].start_utc.isoformat(),'2020-03-31T22:00:00+00:00')

    def test_oct_price_sum_primary_api(self):
        w=REG['market_windows'][2]
        rows=parse_prices(ROOT/w['file'],'SE3',end_utc=w['end_utc'],required_hours=24)
        self.assertAlmostEqual(sum(x.price_eur_per_mwh for x in rows),732.96)
        self.assertEqual(rows[0].start_utc.isoformat(),'2020-09-30T22:00:00+00:00')

    def test_price_snapshot_observed_not_probabilistic(self):
        self.assertIn('NOT an annual',REG['price_window_selection_rule'])

    def test_source_market_price_hashes_match_published_summary(self):
        s=json.loads((RESULT/'v08_study_summary.json').read_text())
        for w in REG['market_windows']:
            self.assertEqual(hashlib.sha256((ROOT/w['file']).read_bytes()).hexdigest(),s['source_price_checksums'][w['id']]['sha256'])

    def test_max_scenario_value_positive_and_nulls_preserved(self):
        s=json.loads((RESULT/'v08_study_summary.json').read_text())['scenario_statistics']
        self.assertEqual(s['positive_scenarios_1e-7'],96)
        self.assertEqual(s['near_zero_scenarios_1e-7'],120)
        self.assertAlmostEqual(s['minimum_increment_eur'],0)
        self.assertGreater(s['maximum_increment_eur'],0)

    def test_economic_assumption_reversal(self):
        with (RESULT/'predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
            rows=list(csv.DictReader(f))
        candidates=[r for r in rows if r['market_window']=='apr'
                    and float(r['gas_storage_mwh_lhv'])==1.0
                    and float(r['heat_demand_multiplier'])==1.0
                    and float(r['electric_efficiency_lhv'])==0.42
                    and r['rating_variant']=='reference_499kw']
        self.assertEqual(len(candidates),2)
        vals={float(r['aux_cost_eur_mwh_th']):float(r['scenario_contribution_increment_eur']) for r in candidates}
        self.assertGreater(vals[20.0],0.5)
        self.assertAlmostEqual(vals[80.0],0,places=7)

    def test_zero_storage_means_no_timing_value(self):
        with (RESULT/'predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
            rows=list(csv.DictReader(f))
        all_zero=[float(r['scenario_contribution_increment_eur']) for r in rows if float(r['gas_storage_mwh_lhv'])==0]
        self.assertEqual(len(all_zero),72)
        self.assertTrue(all(abs(x)<1e-7 for x in all_zero))

    def test_registered_matrix_no_hiding_failed_scenarios(self):
        self.assertEqual(audit.audit(verbose=False)['market_cases_verified'],216)


class EmergencyOracle(unittest.TestCase):
    def test_no_buffer_no_gas_means_zero_service(self):
        r=optimize_emergency_service(emergency(gas_storage_capacity_mwh_lhv=0,initial_stock_mwh_lhv=0))
        self.assertEqual(r['energy_totals']['electric_served_mwh'],0)
        self.assertEqual(r['energy_totals']['heat_served_mwh_th'],0)

    def test_0p3_buffer_analytical_bound(self):
        r=optimize_emergency_service(emergency(gas_storage_capacity_mwh_lhv=.3,initial_stock_mwh_lhv=.3))
        self.assertAlmostEqual(r['energy_totals']['electric_served_mwh'],.12)
        self.assertAlmostEqual(r['energy_totals']['heat_served_mwh_th'],.3*.3915939519083461)

    def test_0p6_buffer_analytical_bound(self):
        r=optimize_emergency_service(emergency())
        self.assertAlmostEqual(r['energy_totals']['electric_served_mwh'],.24)
        self.assertAlmostEqual(r['energy_totals']['heat_served_mwh_th'],.6*.3915939519083461)
        self.assertAlmostEqual(r['energy_totals']['electric_service_fraction'],2/3)

    def test_no_islanding_disallows_service_even_with_gas(self):
        r=optimize_emergency_service(emergency(island_capable=False))
        self.assertEqual(r['energy_totals']['electric_served_mwh'],0)
        self.assertEqual(r['energy_totals']['terminal_inventory_mwh_lhv'],0.6)

    def test_chp_unavailable_disallows_service_even_with_gas(self):
        r=optimize_emergency_service(emergency(chp_available=False))
        self.assertEqual(r['energy_totals']['heat_served_mwh_th'],0)
        self.assertEqual(r['energy_totals']['terminal_inventory_mwh_lhv'],0.6)

    def test_emergency_uncycled_stock_depletes(self):
        r=optimize_emergency_service(emergency())
        self.assertAlmostEqual(r['energy_totals']['terminal_inventory_mwh_lhv'],0,places=8)
        self.assertGreater(r['energy_totals']['gas_utilized_mwh_lhv'],0)

    def test_auxiliary_heat_is_explicitly_unavailable(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(auxiliary_heat_available=True))

    def test_grid_support_is_explicitly_unavailable(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(grid_available=True))

    def test_boolean_numeric_rejected(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(initial_stock_mwh_lhv=True))

    def test_initial_stock_cannot_exceed_cap(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(gas_storage_capacity_mwh_lhv=0.2))

    def test_negative_gas_input_rejected(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(gas_inflow_mw_lhv=-.01))

    def test_efficiencies_must_conserve_energy(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(electric_efficiency_lhv=.8,thermal_efficiency_lhv=.5))

    def test_strict_boolean_gate(self):
        with self.assertRaises(ValueError):optimize_emergency_service(emergency(island_capable='yes'))

    def test_valid_empty_capacity_outage_only_empty_inventory(self):
        r=optimize_emergency_service(emergency(gas_storage_capacity_mwh_lhv=0,initial_stock_mwh_lhv=0))
        self.assertEqual(len(r['hourly']),3)


class TamperDetection(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry_sha=hashlib.sha256((ROOT/'scenarios/registry.json').read_bytes()).hexdigest()
        with (RESULT/'predeclared_scenario_matrix_results.csv').open(newline='',encoding='utf8') as f:
            cls.market_row=next(csv.DictReader(f))
        cls.saved=json.loads((RESULT/'cases'/f"{cls.market_row['case_id']}.json").read_text())
        cls.price_sha=json.loads((RESULT/'v08_study_summary.json').read_text())['source_price_checksums'][cls.market_row['market_window']]['sha256']
        with (RESULT/'hypothetical_critical_service_results.csv').open(newline='',encoding='utf8') as f:
            cls.outage_row=next(x for x in csv.DictReader(f) if x['case_id']=='buffer_0p6')
        cls.outage=json.loads((RESULT/'resilience/buffer_0p6.json').read_text())

    def test_untampered_market_passes(self):
        audit.audit_market_case(self.saved,self.market_row,self.registry_sha,self.price_sha)

    def test_tamper_market_electricity_value(self):
        modified=copy.deepcopy(self.saved)
        modified['optimized_dispatch']['gross_electricity_revenue_eur']+=1
        with self.assertRaises(audit.AuditError):audit.audit_market_case(modified,self.market_row,self.registry_sha,self.price_sha)

    def test_tamper_market_gas_stock(self):
        modified=copy.deepcopy(self.saved)
        modified['input_profile'][1]['stock_end_mwh_lhv']+=0.1
        with self.assertRaises(audit.AuditError):audit.audit_market_case(modified,self.market_row,self.registry_sha,self.price_sha)

    def test_tamper_market_heat_service(self):
        modified=copy.deepcopy(self.saved)
        modified['input_profile'][0]['optimized_auxiliary_heat_mw_th']+=0.1
        with self.assertRaises(audit.AuditError):audit.audit_market_case(modified,self.market_row,self.registry_sha,self.price_sha)

    def test_tamper_solver_status(self):
        modified=copy.deepcopy(self.saved)
        modified['solver']['status_code']=1
        with self.assertRaises(audit.AuditError):audit.audit_market_case(modified,self.market_row,self.registry_sha,self.price_sha)

    def test_tamper_registry_hash(self):
        modified=copy.deepcopy(self.saved)
        modified['v08_provenance']['registry_sha256']='fake'
        with self.assertRaises(audit.AuditError):audit.audit_market_case(modified,self.market_row,self.registry_sha,self.price_sha)

    def test_untampered_emergency_passes(self):
        audit.audit_emergency_case(self.outage,self.outage_row,self.registry_sha)

    def test_tamper_emergency_service(self):
        modified=copy.deepcopy(self.outage)
        modified['hourly'][0]['electric_served_mw']+=.05
        with self.assertRaises(audit.AuditError):audit.audit_emergency_case(modified,self.outage_row,self.registry_sha)

    def test_tamper_emergency_stock(self):
        modified=copy.deepcopy(self.outage)
        modified['hourly'][0]['stock_end_mwh_lhv']+=.1
        with self.assertRaises(audit.AuditError):audit.audit_emergency_case(modified,self.outage_row,self.registry_sha)

    def test_tamper_emergency_solver(self):
        modified=copy.deepcopy(self.outage)
        modified['solver']['success']=False
        with self.assertRaises(audit.AuditError):audit.audit_emergency_case(modified,self.outage_row,self.registry_sha)


if __name__=='__main__':unittest.main()
