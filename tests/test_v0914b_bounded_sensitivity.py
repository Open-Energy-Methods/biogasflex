"""v0.9.14-B: predeclared factorial, analytical MILP oracle, no plant calibration."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.bounded_sensitivity_v0914b import (
    DEFAULT_MANIFEST, EVIDENCE, LEVELS, ORDER, OAT_ORDER,
    SensitivityError, _validate, _set, forced_physical_oracle, run_manifest,
)

class BoundedSensitivityStudy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = run_manifest(DEFAULT_MANIFEST)
        cls.study = json.loads(DEFAULT_MANIFEST.read_text(encoding="utf8"))

    def test_frozen_81_case_grid_and_feasibility(self):
        r=self.report
        self.assertEqual(r["summary"]["factorial_case_count"],81)
        self.assertEqual(r["summary"]["factorial_feasible_count"],16)
        self.assertEqual(r["summary"]["factorial_infeasible_count"],65)
        self.assertEqual(sum(x["milp_feasible"] for x in r["factorial_cases"]),16)
        self.assertTrue(all(x["milp_feasible"] == x["oracle_feasible"] for x in r["factorial_cases"]))
        self.assertEqual(len({x["case_id"] for x in r["factorial_cases"]}),81)

    def test_exact_conditional_box_certificate_and_counterexample(self):
        boxes=self.report["continuous_box_certificates"]
        self.assertEqual(len(boxes),2)
        wide,safe=boxes
        self.assertEqual(wide["corners_checked_analytically"],16)
        self.assertLess(wide["feasible_corners"],16)
        self.assertFalse(wide["model_conditionally_feasible_everywhere_in_continuous_rectangle"])
        self.assertTrue(wide["best_corner"]["milp_feasible"])
        self.assertFalse(wide["worst_corner"]["milp_feasible"])
        self.assertEqual(safe["feasible_corners"],16)
        self.assertTrue(safe["model_conditionally_feasible_everywhere_in_continuous_rectangle"])
        self.assertTrue(safe["worst_corner"]["milp_feasible"])
        self.assertEqual(safe["worst_corner"]["analytic_infeasibility_codes"],[])
        self.assertFalse(self.report["calibration_claim"])

    def test_feasible_cell_has_exact_energy_gas_and_electricity_cashflow(self):
        r=self.report
        good=[x for x in r["factorial_cases"] if x["milp_feasible"]]
        self.assertEqual(len(good),16)
        self.assertTrue(all(abs(x["contract_delivered_mwh"]-0.8)<1e-9 for x in good))
        self.assertTrue(all(x["maximum_energy_contract_residual_mwh"]<=1e-8 for x in good))
        self.assertEqual(r["summary"]["hypothetical_gross_award_cashflow_proxy_eur"],20.0)
        self.assertTrue(r["summary"]["distribution_free"])

    def test_conditional_marginals_not_real_probabilities(self):
        attr=self.report["finite_design_attribution"]
        self.assertEqual(attr["definition"],"EXACT_UNWEIGHTED_FINITE_GRID_VARIANCE_DECOMPOSITION_NOT_SOBOL_PROBABILITY")
        self.assertAlmostEqual(attr["grid_mean_binary_feasibility"],16/81)
        self.assertAlmostEqual(attr["grid_variance_binary_feasibility"],(16/81)*(65/81))
        self.assertEqual(len(attr["first_order"]),4)
        self.assertEqual(len(attr["second_order"]),6)
        self.assertFalse(attr["statistical_probability_claim"])
        for key in ORDER:
            ms=attr["first_order"][key]["finite_grid_feasibility_fraction_by_level"]
            self.assertEqual(len(ms),3)
            self.assertEqual(sorted(ms),[0.0,8/27,8/27])
        variances=sum(x["first_order_component_of_design_variance"] for x in attr["first_order"].values())
        variances+=sum(x["interaction_component_of_design_variance"] for x in attr["second_order"])
        variances+=attr["higher_order_residual_variance"]
        self.assertAlmostEqual(variances,attr["grid_variance_binary_feasibility"],places=10)

    def test_oat_efficiency_thermal_and_initial_ramp(self):
        oat=self.report["one_at_a_time_cases"]
        self.assertEqual(len(oat),9)
        by={key:[r["milp_feasible"] for r in oat if key in r["parameter_values"]] for key in OAT_ORDER}
        self.assertEqual(by[OAT_ORDER[0]],[False,True,False])
        self.assertEqual(by[OAT_ORDER[1]],[False,True,True])
        self.assertEqual(by[OAT_ORDER[2]],[False,True,True])
        eta_bad=[r for r in oat if r["parameter_values"]=={"electric_efficiency_lhv":0.42}][0]
        self.assertIn("GAS_TERMINAL_EQUALITY",eta_bad["analytic_infeasibility_codes"])

    def test_structure_not_measured_or_source_transferred(self):
        report=self.report
        self.assertEqual(report["assumption_source"],EVIDENCE)
        self.assertFalse(report["all_14_site_unknowns_resolved"])
        self.assertFalse(report["operational_market_eligibility_claim"])
        self.assertFalse(report["probabilistic_robustness_claim"])
        self.assertTrue(report["no_manufacturer_parameter_import"])
        self.assertEqual(len(report["source_fingerprint"]),3)

    def test_analytic_witness_independent_of_later_solver_decisions(self):
        cfg,intervals,awards,_=_validate(self.study)
        for name,val in zip(ORDER,(0.5,0.8,0.15,0.05)):
            _set(cfg,name,val)
        good=forced_physical_oracle(cfg,awards,[x.hours for x in intervals])
        self.assertTrue(good["feasible"])
        self.assertEqual(good["end_stock_mwh_lhv"],[.5,0.0])
        self.assertAlmostEqual(good["needed_backup_heat_mw_th"][0],.05)
        _set(cfg,"gas_storage_capacity_mwh_lhv",.4)
        witness=forced_physical_oracle(cfg,awards,[x.hours for x in intervals])
        self.assertFalse(witness["feasible"])
        self.assertIn("GAS_STORAGE_STOCK",witness["reasons"])

    def test_identical_annualized_aggregates_do_not_identify_ramps(self):
        a=[0.2,0.2,0.2,0.2]
        b=[0.1,0.3,0.1,0.3]
        self.assertEqual(sum(a),sum(b))
        self.assertEqual(sum(x>0 for x in a),sum(x>0 for x in b))
        ramp=lambda q:max(abs(x-y) for x,y in zip(q[:-1],q[1:]))
        self.assertNotEqual(ramp(a),ramp(b))
        start=lambda q:sum(x>0 and (i==0 or q[i-1]==0) for i,x in enumerate(q))
        c=[.2,.2,0,0];d=[.2,0,.2,0]
        self.assertEqual(sum(c),sum(d))
        self.assertEqual(sum(x>0 for x in c),sum(x>0 for x in d))
        self.assertNotEqual(start(c),start(d))

    def test_nonfinite_or_duplicate_levels_rejected(self):
        bad=deepcopy(self.study);bad["varied_parameters"][0]["levels"]=[0.4,0.5,0.5]
        with self.assertRaisesRegex(SensitivityError,"range changed"):
            _validate(bad)
        bad=deepcopy(self.study);bad["varied_parameters"][0]["levels"]=[0.4,math.inf,0.7]
        with self.assertRaises(SensitivityError):
            _validate(bad)
        bad=deepcopy(self.study);bad["varied_parameters"][0]["levels"]=[False,0.5,0.7]
        with self.assertRaises(SensitivityError):
            _validate(bad)

    def test_source_identity_or_award_substitution_rejected(self):
        bad=deepcopy(self.study);bad["source_evidence_register"]="examples/v0911_synthetic_chp.json"
        with self.assertRaisesRegex(SensitivityError,"reference path"):
            _validate(bad)
        bad=deepcopy(self.study);bad["contract_manifest_sha256"]="f"*64
        with self.assertRaises(SensitivityError):
            _validate(bad)
        bad=deepcopy(self.study);bad["evidence_class"]="MANUFACTURER_CALIBRATED"
        with self.assertRaisesRegex(SensitivityError,"Unreviewed"):
            _validate(bad)

    def test_cherry_picked_box_or_missing_out_of_scope_rejected(self):
        bad=deepcopy(self.study)
        bad["continuous_rectangles"][1]["bounds"][ORDER[0]][0]=0.49
        with self.assertRaisesRegex(SensitivityError,"rectangle"):
            _validate(bad)
        bad=deepcopy(self.study);bad["out_of_scope"]=[]
        with self.assertRaisesRegex(SensitivityError,"exclusions"):
            _validate(bad)

    def test_opt_in_cli_json_and_original_no_mutation(self):
        before={path:(ROOT/path).read_bytes() for path in (
            "examples/v0911_synthetic_chp.json","examples/v0911_contract_hourly.json",
            "data/evidence/v0914_chp_parameter_register.json")}
        with tempfile.TemporaryDirectory(prefix="biogasflex-v0914b-") as temp:
            out=Path(temp)/"sensitivity.json"
            p=subprocess.run(
                [sys.executable,"-m","biogasflex","bounded-sensitivity",
                 "--manifest",str(DEFAULT_MANIFEST),"--output",str(out)],
                cwd=ROOT,text=True,capture_output=True,check=True,timeout=180)
            cli=json.loads(p.stdout);full=json.loads(out.read_text(encoding="utf8"))
            self.assertEqual(cli["factorial_scenarios"],81)
            self.assertEqual(cli["feasible_grid_scenarios"],16)
            self.assertEqual(full["summary"]["oat_case_count"],9)
            self.assertFalse(full["calibration_claim"])
        for path,bytes_before in before.items():
            self.assertEqual((ROOT/path).read_bytes(),bytes_before,path)


if __name__=="__main__":
    unittest.main()
