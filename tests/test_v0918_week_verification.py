"""v0.9.18 adversarial quarter-hour MILP/LP scaling and independent proof tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from biogasflex.benchmark_v0918 import (
    _quarter_intervals, _forced_config, _flexible_config,
    _negative, run, write_out, PROTOCOL, _case
)

SPEC=importlib.util.spec_from_file_location(
    "v0918_independent",ROOT/"scripts/audit_v0918_independent.py")
aud=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(aud)

class QuarterHourResearchBench(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.study=run((4,8),include_infeasible=False)
        cls.independent=aud.audit(cls.study)

    def test_small_full_independent_numerical_witness(self):
        self.assertEqual(self.independent["status"],
                         "PASS_INDEPENDENT_SYNTHETIC_MULTISCALE_RESEARCH_MODEL_WITNESSES")
        self.assertEqual(self.independent["case_count"],6)
        self.assertEqual(self.independent["total_independently_rechecked_quarter_hour_rows"],36)
        self.assertEqual(self.independent["forced_zero_buffer_models_uniquely_optimal"],2)
        self.assertFalse(self.independent["plant_calibrated"])

    def test_forced_zero_buffer_unique_start_witness(self):
        for n in (4,8):
            data=next(x for x in self.study["cases"]
                      if x["interval_count"]==n and x["kind"]=="forced_commitment_milp")
            self.assertEqual(data["reported_start_count"],1)
            self.assertEqual(data["reported_stop_count"],0)
            self.assertEqual(
                [r["on"] for r in data["rows"]],
                [0]*(n//2)+[1]*(n//2))
            self.assertEqual(data["solver_mip_gap"],0.0)
            self.assertGreater(data["reported_lp_relaxation_upper_bound_eur"],
                               data["reported_net_contribution_eur"])
            self.assertEqual(aud.witness_case(data)["status"],
                             "PASS_INDEPENDENT_NUMERICAL_PRIMAL_CHECK_AND_CASE_SCOPED_WITNESS")

    def test_15min_utc_and_source_only_synthetic(self):
        rows=_quarter_intervals(96,"forced_commitment_milp")
        self.assertEqual(len(rows),96)
        self.assertEqual(rows[0].hours,.25)
        self.assertEqual(rows[-1].start_utc,datetime(2020,1,1,23,45,tzinfo=timezone.utc))
        self.assertTrue(all("INVENTED" in x["problem_input"]["input_provenance"]
                            for x in self.study["cases"]))
        self.assertFalse(self.study["claims"]["real_plant_telemetry_used"])
        self.assertFalse(self.study["claims"]["LP_global_optimality_independently_proven"])

    def test_24h_nontrivial_buffered_lp_optimizes_above_zero_buffer(self):
        zero=_case(96,"zero_storage_ramp_lp")
        flex=_case(96,"storage_ramp_lp")
        self.assertGreater(flex["reported_net_contribution_eur"],
                           zero["reported_net_contribution_eur"]+0.01)
        self.assertEqual(zero["reported_ledger"]["max_stock_mwh_lhv"],0)
        self.assertGreater(flex["reported_ledger"]["max_stock_mwh_lhv"],0)
        self.assertLess(flex["reported_ramp_violation_mw_e"],1e-7)
        aud.witness_case(zero);aud.witness_case(flex)

    def test_independent_oracle_rejects_fabricated_objective(self):
        bad=deepcopy(self.study["cases"][0])
        bad["reported_net_contribution_eur"]+=11.
        with self.assertRaisesRegex(AssertionError,"objective"):
            aud.witness_case(bad)

    def test_independent_oracle_rejects_gas_supply_and_inventory_tampering(self):
        bad=deepcopy(self.study["cases"][0])
        bad["rows"][1]["gas_use_mw_lhv"]=.25
        with self.assertRaises(AssertionError):
            aud.witness_case(bad)
        bad=deepcopy(self.study["cases"][0])
        bad["rows"][2]["stock_end_mwh_lhv"]=.1
        with self.assertRaises(AssertionError):
            aud.witness_case(bad)

    def test_independent_oracle_rejects_tampered_input_prices_or_gas(self):
        bad=deepcopy(self.study["cases"][0])
        bad["price_eur_mwh"][0]+=1
        with self.assertRaisesRegex(AssertionError,"price scenario altered"):
            aud.witness_case(bad)
        bad=deepcopy(self.study["cases"][0])
        bad["problem_input"]["gas_production_mw_lhv"][2]=1.
        with self.assertRaisesRegex(AssertionError,"gas-source pattern altered"):
            aud.witness_case(bad)
        bad=deepcopy(self.study["cases"][0])
        bad["problem_input"]["aux_heat_capacity_mw_th"]=.19
        with self.assertRaisesRegex(AssertionError,"base assumptions changed"):
            aud.witness_case(bad)

    def test_independent_optimum_proof_rejects_wasteful_heat_split(self):
        bad=deepcopy(self.study["cases"][0])
        # On interval 2 has .4 MWth potential and .15 MWth demand.
        # A less-direct heat split may satisfy heat balances but has
        # strictly higher auxiliary/dump costs and is not optimal.
        row=bad["rows"][2]
        row["useful_heat_mw_th"]-=.01
        row["aux_heat_mw_th"]+=.01
        row["dump_heat_mw_th"]+=.01
        with self.assertRaisesRegex(AssertionError,"cost-minimal"):
            aud.witness_case(bad)

    def test_independent_oracle_rejects_fake_start_and_times(self):
        bad=deepcopy(self.study["cases"][0])
        bad["rows"][2]["startup"]=0
        with self.assertRaisesRegex(AssertionError,"start transition"):
            aud.witness_case(bad)
        bad=deepcopy(self.study["cases"][0])
        bad["rows"][1]["start_utc"]="2020-01-01T05:00:00+00:00"
        with self.assertRaisesRegex(AssertionError,"time gap"):
            aud.witness_case(bad)

    def test_negative_96_hourly_contract_heat_and_dwell_gates(self):
        n=96
        for reason in ("insufficient_aux_heat","rating_too_small_for_forced_gas",
                       "mandatory_up_dwell_exceeds_remaining_horizon"):
            outcome=_negative(n,reason)
            self.assertTrue(outcome["optimizer_rejected"])
            self.assertEqual(outcome["interval_count"],n)

    def test_manifest_serialization_fails_inside_repo(self):
        with self.assertRaises(RuntimeError):
            write_out(self.study,ROOT/"results/v0.9.18/dont_commit.json")
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"test.json"
            write_out(self.study,path)
            self.assertTrue(path.exists())

    def test_no_false_plant_calibration_in_tampered_report(self):
        bad=deepcopy(self.study)
        bad["claims"]["biogas_engine_calibration_established"]=True
        with self.assertRaisesRegex(AssertionError,"exclusions"):
            aud.audit(bad)

if __name__=="__main__":
    unittest.main()
