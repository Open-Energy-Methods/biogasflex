"""v0.9.21 synthetic regression fixtures; never claimed as real observations."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex import opsd_v0921 as opsd
from biogasflex import joint_v0921 as joint
from tests.test_v0921_opsd_evidence import OPSDSourceContracts

class JointConditionalScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"SYNTHETIC_TEST_FIXTURE_NOT_OPSD.csv"
            OPSDSourceContracts()._make(p)
            with patch.object(opsd,"_check_sha",return_value=0):
                cls.source=opsd.analyze(p)
        cls.study=joint.run(cls.source,smoke=True)
        cls.case=cls.study["cases"][0]

    def test_original_source_categories_not_misrepresented(self):
        self.assertEqual(self.study["source_checksum_verified_expected"],opsd.SOURCE_SHA256)
        self.assertFalse(self.study["forecast_issue_gate_claim"])
        self.assertFalse(self.study["site_gas_heat_empirically_calibrated"])
        self.assertFalse(self.study["probabilistic_reliability_estimate"])
        self.assertFalse(any(self.study["provenance_limits"].values()))
        self.assertEqual(self.study["second_stage"],
            "FULL_SCENARIO_PATH_CONTINUOUS_PERFECT_INFORMATION_RECOURSE_OPTIMISTIC_BOUND")

    def test_heldout_scenario_does_not_exist_at_optimization_issue_time(self):
        pre=joint.build_source_scenarios(self.source,target_ordinal=8)
        self.assertNotIn("heldout_post_reveal",pre)
        self.assertTrue(pre["heldout_not_generated_at_forecast_time"])
        self.assertEqual(
            self.case["source_bundle"]["heldout_post_reveal"]["source_day_utc"],
            pre["target_day_utc"])

    def test_no_biogasflex_independent_joint_reconstruction_and_kkt(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location(
            "v0921_independent",ROOT/"scripts/audit_v0921_joint_independent.py")
        oracle=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(oracle)
        result=oracle.audit(self.source,self.study)
        self.assertEqual(result["status"],
            "PASS_INDEPENDENT_SOURCE_PAIRED_CORRELATED_STRESS_AND_IDEALIZED_RECOURSE")
        self.assertEqual(result["number_of_synthetic_CHP_heldout_targets"],1)
        self.assertEqual(result["conditional_KKT_and_heldout_checks"],11)
        self.assertFalse(result["global_MILP_optimality_independently_certified"])

    def test_frozen_first_stage_shared_across_all_eight_training_blocks(self):
        output=self.case["joint_block_maximin_first_stage"]
        self.assertEqual(len(output["binary_first_stage_on"]),24)
        self.assertEqual(len(output["scenario_second_stage_idealized_full_day_recourse"]),8)
        shared=output["binary_first_stage_on"]
        for block in output["scenario_second_stage_idealized_full_day_recourse"]:
            self.assertEqual([r["on"] for r in block["rows"]],shared)
        self.assertEqual(len(self.case["source_bundle"]["training_blocks"]),8)
        self.assertEqual(self.case["source_bundle"]["target_day_utc"],
                         self.source["complete_days"][-92+8]["date_utc"])

    def test_source_paired_full_day_sampling_and_no_hourly_independent_shuffle(self):
        source=self.case["source_bundle"]
        reference=source["training_blocks"][0]
        self.assertEqual(reference["source_day_utc"],
                         self.source["complete_days"][0]["date_utc"])
        self.assertEqual(len(reference["observed_price_persistence_errors_eur_mwh"]),6)
        self.assertEqual(len(reference["observed_regional_electric_load_errors_relative"]),6)
        self.assertEqual(len(reference["synthetic_gas_production_mw_lhv"]),24)
        self.assertEqual(len(reference["synthetic_site_heat_demand_mw_th"]),24)
        for channel in ("price_eur_mwh","synthetic_gas_production_mw_lhv",
                        "synthetic_site_heat_demand_mw_th"):
            vals=reference[channel]
            self.assertTrue(all(vals[k]==vals[k+1] for k in range(0,24,4)))

    def test_hypothetical_gas_heat_depend_on_joint_source_coordinates(self):
        b=self.case["source_bundle"]["training_blocks"][0]
        for i,(zp,zl) in enumerate(b["standardized_source_pair_latents"]):
            expgas=max(.78,min(1.22,1+.08*zp-.06*zl))
            expheat=max(.105,min(.195,.15*(1+.10*zl+.03*zp)))
            self.assertAlmostEqual(b["synthetic_gas_production_mw_lhv"][4*i],
                                   expgas,places=6)
            self.assertAlmostEqual(b["synthetic_site_heat_demand_mw_th"][4*i],
                                   expheat,places=6)

    def test_post_reveal_scenario_did_not_change_shared_binary_policy(self):
        policies=self.case["holdout_comparison"]
        for name,source_key in (("nominal","nominal_first_stage"),
                                ("joint_block_maximin","joint_block_maximin_first_stage")):
            self.assertTrue(policies[name]["first_stage_remained_frozen"])
            self.assertEqual(policies[name]["first_stage_sha256_before_realization"],
                             self.case[source_key]["first_stage_sha256"])
            self.assertTrue(policies[name]["holdout_recourse"]["feasible"])
            self.assertIsNotNone(
                policies[name]["realized_idealized_contribution_eur"])

    def test_train_holdout_dates_and_declared_ordinal_locked(self):
        for c in self.study["cases"]:
            self.assertGreaterEqual(c["source_bundle"]["target_day_utc"],"2019-10-01")
            self.assertTrue(all(day["source_day_utc"]<"2019-10-01"
                 for day in c["source_bundle"]["training_blocks"]))
        bad=deepcopy(self.source)
        bad["complete_days"][0]["date_utc"]="2019-11-25"
        with self.assertRaisesRegex(ValueError,"dates duplicated or reordered"):
            joint.build_source_scenarios(bad)

    def _independent(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location(
            "v0921_independent_adversarial",ROOT/"scripts/audit_v0921_joint_independent.py")
        audit=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        return audit

    def test_independent_oracle_rejects_forged_gas_and_heat_correlation(self):
        oracle=self._independent()
        invalid=deepcopy(self.study)
        invalid["cases"][0]["source_bundle"]["training_blocks"][0][
            "synthetic_gas_production_mw_lhv"][0]+=.05
        with self.assertRaisesRegex(AssertionError,"scenario"):
            oracle.audit(self.source,invalid)
        invalid=deepcopy(self.study)
        invalid["cases"][0]["source_bundle"]["heldout_post_reveal"][
            "synthetic_site_heat_demand_mw_th"][1]+=.02
        with self.assertRaisesRegex(AssertionError,"scenario"):
            oracle.audit(self.source,invalid)

    def test_independent_oracle_rejects_forged_locked_commitment_and_cash(self):
        oracle=self._independent()
        invalid=deepcopy(self.study)
        invalid["cases"][0]["nominal_first_stage"]["first_stage_sha256"]="0"*64
        with self.assertRaisesRegex(AssertionError,"fingerprint"):
            oracle.audit(self.source,invalid)
        invalid=deepcopy(self.study)
        invalid["cases"][0]["holdout_comparison"]["nominal"][
            "realized_idealized_contribution_eur"]+=17
        with self.assertRaisesRegex(AssertionError,"source-heldout"):
            oracle.audit(self.source,invalid)

    def test_fail_closed_on_false_measured_gas_claim(self):
        bad=deepcopy(self.source)
        bad["source"]["gas_production_or_heat_load_site_measurement_present"]=True
        with self.assertRaisesRegex(ValueError,"Wrongly claimed"):
            joint.build_source_scenarios(bad)

    def test_source_must_keep_original_publisher_digest(self):
        bad=deepcopy(self.source)
        bad["source"]["sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"publisher SHA256"):
            joint.build_source_scenarios(bad)

if __name__=="__main__":
    unittest.main()
