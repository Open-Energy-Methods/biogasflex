"""Integrity tests for separate standard-library-only result checker."""
import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('v07_audit',ROOT/'scripts/independent_v07_audit.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ORACLE=json.loads((ROOT/'results/v0.7/synthetic_oracle_heat_cost80.json').read_text())

class IndependentCheckerDefendsIntegrity(unittest.TestCase):
    def check_modified(self,new):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'edited.json';p.write_text(json.dumps(new))
            with self.assertRaises(AssertionError):module.check(p)

    def test_published_oracle_audit(self):
        self.assertTrue(module.check(ROOT/'results/v0.7/synthetic_oracle_heat_cost80.json')['heat_service_pass'])

    def test_published_lovsta_audit(self):
        self.assertTrue(module.check(ROOT/'results/v0.7/lovsta_crossyear_heat_cost80.json')['gas_balance_pass'])

    def test_detects_corrupted_heat_service(self):
        o=copy.deepcopy(ORACLE);o['input_profile'][0]['optimized_auxiliary_heat_mw_th'] += 0.03
        self.check_modified(o)

    def test_detects_corrupted_revenue_ledger(self):
        o=copy.deepcopy(ORACLE);o['optimized_dispatch']['gross_electricity_revenue_eur'] += 1
        self.check_modified(o)

    def test_detects_corrupted_stock(self):
        o=copy.deepcopy(ORACLE);o['input_profile'][0]['stock_end_mwh_lhv'] += 0.1
        self.check_modified(o)

    def test_detects_not_optimal_status(self):
        o=copy.deepcopy(ORACLE);o['solver']['success']=False
        self.check_modified(o)

if __name__=='__main__':unittest.main()
