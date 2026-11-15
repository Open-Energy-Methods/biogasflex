"""v0.9.19 independent CHP model reformulation, KKT and finite-design tests."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.benchmark_v0919 import (
    PROTOCOL, _config, _intervals, _dominates, run, write_out, SEEDS,
)

SPEC=importlib.util.spec_from_file_location(
    "v0919_independent",ROOT/"scripts/audit_v0919_independent.py")
aud=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aud)

class EndogenousCHPFrontierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=run(smoke=True)
        cls.audit=aud.audit(cls.source)

    def test_8slot_true_endogenous_binary_enumeration(self):
        self.assertEqual(self.audit["status"],
                         "PASS_SYNTHETIC_ENDOGENOUS_RESEARCH_FRONTIERS_AND_PRIMAL_DUAL_KKT")
        self.assertEqual(self.audit["cases_verified"],3)
        self.assertEqual(self.audit["exhaustive_8slot_binary_oracles"],1)
        c=self.audit["case_witnesses"][0]
        certificate=c["exhaustive_8slot_binary_global_optimum"]
        self.assertEqual(certificate["binary_patterns_enumerated"],256)
        self.assertGreater(certificate["feasible_patterns_with_lp_solution"],1)
        self.assertLess(c["alternative_lp_primal_and_dual_certificate"]["residuals"]
                        ["absolute_primal_dual_objective_gap_eur"],3e-5)

    def test_no_fake_probabilistic_reliability_and_no_real_market(self):
        self.assertEqual(self.source["protocol"],PROTOCOL)
        self.assertFalse(self.source["design"]["probability_distributions_assumed"])
        self.assertFalse(self.source["design"]["real_energy_price_forecast"])
        self.assertFalse(self.source["design"]["real_plant_reliability_probability_estimated"])
        self.assertFalse(any(self.source["claims"].values()))
        self.assertTrue(all(c["config"]["input_provenance"].startswith("FULLY_SYNTHETIC_")
                            for c in self.source["cases"]))

    def test_source_profile_seed_distinct_and_reproducible(self):
        left=_intervals(SEEDS[0],24)
        right=_intervals(SEEDS[1],24)
        self.assertNotEqual([r.price_eur_per_mwh for r in left],
                            [r.price_eur_per_mwh for r in right])
        self.assertEqual([r.price_eur_per_mwh for r in left],
                         [r.price_eur_per_mwh for r in _intervals(SEEDS[0],24)])
        self.assertEqual(left[1].hours,.25)
        distinct={tuple(row.price_eur_per_mwh for row in _intervals(seed,24))
                  for seed in SEEDS}
        self.assertEqual(len(distinct),len(SEEDS),
                         "Modulo arithmetic produced duplicated supposedly distinct price scenarios")

    def test_primal_dual_auditor_rejects_forged_objective(self):
        fake=deepcopy(self.source["cases"][0])
        fake["reported_net_objective_eur"]+=2.
        with self.assertRaisesRegex(AssertionError,"objective"):
            aud.audit_case(fake)

    def test_independent_check_rejects_price_gas_and_ramp_tamper(self):
        fake=deepcopy(self.source["cases"][0])
        fake["prices_eur_mwh"][3]+=10
        with self.assertRaisesRegex(AssertionError,"price source mismatch"):
            aud.audit_case(fake)
        fake=deepcopy(self.source["cases"][0])
        fake["config"]["gas_production_mw_lhv"][0]=0
        with self.assertRaisesRegex(AssertionError,"gas source"):
            aud.audit_case(fake)
        fake=deepcopy(self.source["cases"][0])
        fake["config"]["experimental_v097"]["ramp_up_mw_e_per_hour"]=20
        with self.assertRaisesRegex(AssertionError,"commitment/ramp"):
            aud.audit_case(fake)

    def test_independent_dual_certificate_check_rejects_modified_primal_cost(self):
        x=self.source["cases"][2]
        cfg,lim,p=aud._predeclare(x)
        prob=aud.formulate(cfg,lim,p,None)
        sol=aud._solve(prob)
        aud._kkt_check(prob,sol)
        prob["c"][0]+=1
        with self.assertRaisesRegex(AssertionError,"KKT"):
            aud._kkt_check(prob,sol)

    def test_heat_energy_and_timestamp_forgery_rejected(self):
        fake=deepcopy(self.source["cases"][0])
        fake["rows"][1]["stock_end_mwh_lhv"]+=.1
        with self.assertRaisesRegex(AssertionError,"inventory"):
            aud.audit_case(fake)
        fake=deepcopy(self.source["cases"][0])
        fake["rows"][1]["useful_heat_mw_th"]+=.1
        with self.assertRaises(AssertionError):
            aud.audit_case(fake)
        fake=deepcopy(self.source["cases"][0])
        fake["timestamps_utc"][1]=fake["timestamps_utc"][0]
        with self.assertRaisesRegex(AssertionError,"timestamp"):
            aud.audit_case(fake)

    def test_pareto_dominance_only_compares_matched_assumptions(self):
        a={"reported_net_objective_eur":10.,
           "auxiliary_heat_fraction_of_demand":.3,"start_count":1}
        b={"reported_net_objective_eur":9.,
           "auxiliary_heat_fraction_of_demand":.5,"start_count":2}
        self.assertTrue(_dominates(a,b))
        self.assertFalse(_dominates(b,a))

    def test_cannot_write_full_synthetic_reports_into_checkout(self):
        with self.assertRaisesRegex(ValueError,"outside checked-out repository"):
            write_out(self.source,ROOT/"hidden_reports/v0919.json")
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"audit.json"
            write_out(self.source,path)
            self.assertTrue(path.exists())

if __name__=="__main__":
    unittest.main()
