"""v0.9.20 ex-ante rectangular robust and frozen heldout adversarial tests."""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from itertools import product
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.robust_v0920 import (
    PROTOCOL, SOURCE, HOLDOUT, TRAIN, _nominal, _envelope,
    _holdout, _value, _schedule_sha, run, write_out,
)

SPEC=importlib.util.spec_from_file_location(
    "v0920_independent",ROOT/"scripts/audit_v0920_independent.py")
aud=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aud)

class PriceBoundedRobustStudyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.smoke=run(smoke=True)
        cls.check=aud.audit(cls.smoke)
        cls.case=cls.smoke["cases"][0]

    def test_rectangular_robust_8slot_global_independent_commitment(self):
        self.assertEqual(self.check["status"],
                         "PASS_BOUNDED_PRICE_ROBUST_CHRONOLOGY_AND_INDEPENDENT_REPLAY_CERTIFICATES")
        self.assertEqual(self.check["research_cases"],2)
        self.assertEqual(self.check["immutable_ex_ante_policies_audited"],4)
        self.assertEqual(self.check["selected_heldout_paths_replayed"],6)
        self.assertEqual(self.check["exhaustively_certified_eight_slot_MILP_policies"],4)
        self.assertFalse(self.check["real_bid_time_forecast_or_plant_calibration"])

    def test_explicit_every_price_uncertainty_vertex_proves_lower_worst(self):
        case=self.case;lo=case["rectangular_lower_price_eur_mwh"]
        hi=case["rectangular_upper_price_eur_mwh"]
        self.assertEqual(len(lo),8)
        for policy in case["policies"].values():
            values=[
                _value(policy["rows"],
                       [hi[i] if bit else lo[i]
                        for i,bit in enumerate(bits)],case["config"])
                for bits in product((0,1),repeat=8)
            ]
            self.assertAlmostEqual(min(values),
                policy["frozen_worst_case_rectangle_eur"],places=6)
        self.assertGreaterEqual(
            case["policies"]["rectangular_maximin"]["frozen_worst_case_rectangle_eur"]+1e-6,
            case["policies"]["nominal_forecast"]["frozen_worst_case_rectangle_eur"])

    def test_heldout_forecast_timing_and_no_operational_lookahead(self):
        case=self.case
        self.assertEqual(case["forecast_issued_at_utc"],"2019-12-31T23:00:00+00:00")
        self.assertEqual(case["service_begins_utc"],"2020-01-01T00:00:00+00:00")
        self.assertEqual([x["source_seed"] for x in case["heldout_paths"]],list(HOLDOUT))
        self.assertEqual(case["input_provenance"],SOURCE)
        for hold in case["heldout_paths"]:
            for p in ("nominal_forecast","rectangular_maximin"):
                self.assertEqual(
                    hold["frozen_policy_evaluations"][p]["frozen_schedule_decision_sha256"],
                    case["policies"][p]["decision_sha256"])
            for x,lo,hi in zip(hold["prices_revealed_only_after_schedule_fixed_eur_mwh"],
                               case["rectangular_lower_price_eur_mwh"],
                               case["rectangular_upper_price_eur_mwh"]):
                self.assertGreaterEqual(x+1e-9,lo)
                self.assertLessEqual(x-1e-9,hi)

    def test_heldout_changes_do_not_affect_source_schedule_decisions(self):
        data=deepcopy(self.case)
        before=[data["policies"][p]["decision_sha256"] for p in
                ("nominal_forecast","rectangular_maximin")]
        data["heldout_paths"][0]["prices_revealed_only_after_schedule_fixed_eur_mwh"][0]+=100
        after=[data["policies"][p]["decision_sha256"] for p in
               ("nominal_forecast","rectangular_maximin")]
        self.assertEqual(before,after)
        with self.assertRaisesRegex(AssertionError,"Heldout prices manipulated"):
            aud.audit_case(data)

    def test_reject_forged_forecast_or_worst_case_bound(self):
        data=deepcopy(self.case)
        data["nominal_train_forecast_eur_mwh"][0]+=1.
        with self.assertRaisesRegex(AssertionError,"Price confidence envelope"):
            aud.audit_case(data)
        data=deepcopy(self.case)
        data["policies"]["rectangular_maximin"]["frozen_worst_case_rectangle_eur"]+=10
        with self.assertRaisesRegex(AssertionError,"rectangular worst-case"):
            aud.audit_case(data)

    def test_reject_forged_lookahead_or_changed_decision(self):
        data=deepcopy(self.case)
        data["policies"]["rectangular_maximin"]["optimization_price_input"]="heldout_101"
        with self.assertRaisesRegex(AssertionError,"incorrect information"):
            aud.audit_case(data)
        data=deepcopy(self.case)
        data["policies"]["nominal_forecast"]["rows"][1]["gas_use_mw_lhv"]+=.3
        with self.assertRaisesRegex(AssertionError,"schedule changed"):
            aud.audit_case(data)
        data=deepcopy(self.case)
        data["heldout_paths"][1]["frozen_policy_evaluations"][
            "rectangular_maximin"]["frozen_schedule_decision_sha256"]="0"*64
        with self.assertRaisesRegex(AssertionError,"retroactively changed"):
            aud.audit_case(data)

    def test_regret_and_hindsight_cannot_be_edited(self):
        data=deepcopy(self.case)
        data["heldout_paths"][0]["frozen_policy_evaluations"][
            "nominal_forecast"]["perfect_information_regret_eur"]+=42
        with self.assertRaisesRegex(AssertionError,"hindsight-referenced"):
            aud.audit_case(data)
        data=deepcopy(self.case)
        data["heldout_paths"][0]["perfect_information_oracle_not_operational"][
            "reported_model_objective_eur"]+=42
        with self.assertRaisesRegex(AssertionError,"Hindsight oracle objective"):
            aud.audit_case(data)

    def test_no_stochastic_uncertainty_provenance_or_market_claims(self):
        self.assertIsNone(self.smoke["confidence_level_or_probabilistic_reliability"])
        self.assertFalse(any(self.smoke["claims"].values()))
        self.assertEqual(self.smoke["train_seeds"],[11])
        self.assertEqual(self.smoke["unseen_price_evaluation_seeds"],list(HOLDOUT))
        self.assertTrue(self.smoke["uncertainty_geometry"].startswith("RECTANGULAR_"))
        self.assertEqual(self.smoke["price_stress_classes"],["reference","wide_stress"])
        data=deepcopy(self.smoke)
        data["claims"]["actual_price_forecast_verified"]=True
        with self.assertRaisesRegex(AssertionError,"Unfounded"):
            aud.audit(data)

    def test_synthetic_training_paths_frozen_and_distinct(self):
        for seed in TRAIN:
            forecast=_nominal(seed,24)
            lo,hi=_envelope(forecast,"reference")
            self.assertEqual(len(forecast),24)
            self.assertNotEqual(_holdout(seed,101,lo,hi),
                                _holdout(seed,211,lo,hi))
            self.assertTrue(all(l<=f<=u for l,f,u in zip(lo,forecast,hi)))
        self.assertNotEqual(_nominal(TRAIN[0],24),_nominal(TRAIN[1],24))

    def test_wide_stress_is_distinct_and_reference_study_remains_present(self):
        reference,wide=self.smoke["cases"]
        self.assertEqual(reference["price_bound_class"],"reference")
        self.assertEqual(wide["price_bound_class"],"wide_stress")
        self.assertEqual(reference["nominal_train_forecast_eur_mwh"],
                         wide["nominal_train_forecast_eur_mwh"])
        self.assertTrue(all(w<=r+1e-12 for w,r in zip(
            wide["rectangular_lower_price_eur_mwh"],
            reference["rectangular_lower_price_eur_mwh"])))
        self.assertTrue(any(w<r-1e-6 for w,r in zip(
            wide["rectangular_lower_price_eur_mwh"],
            reference["rectangular_lower_price_eur_mwh"])))
        self.assertEqual(aud.audit_case(wide)["status"],
                         "PASS_SEPARATE_OPTIMALITY_AND_OUT_OF_SAMPLE_PHYSICAL_WITNESS")

    def test_plotting_rejects_incomplete_study_and_git_checkout_output(self):
        spec=importlib.util.spec_from_file_location(
            "v0920_svg",ROOT/"scripts/plot_v0920_robustness.py")
        plots=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(plots)
        with self.assertRaisesRegex(ValueError,"OUTSIDE the source checkout"):
            plots.render(self.smoke,ROOT/"charts/v0920")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,"Incomplete synthetic"):
                plots.render(self.smoke,Path(tmp))

    def test_reject_unsafe_output_path(self):
        with self.assertRaisesRegex(ValueError,"OUTSIDE git repository"):
            write_out(self.smoke,ROOT/"reports/oos-v0920.json")
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/"oos.json"
            write_out(self.smoke,output)
            self.assertTrue(output.exists())

if __name__=="__main__":
    unittest.main()
