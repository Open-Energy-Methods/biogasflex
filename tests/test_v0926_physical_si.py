"""Adversarial tests for independent SI boundary and provenance assurance."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("audit_si",ROOT/"scripts/audit_v0926_physical_si.py")
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def fixture():
    row={"quarter_index":0,"hour_index":0,"on":1,"start":0,"stop":0,
        "gas_in_mw_lhv":1.,"gas_use_mw_lhv":1.,
        "stock_end_mwh_lhv":.75,"heat_demand_mw_th":.15,
        "useful_chp_heat_mw_th":.15,"backup_heat_mw_th":0.,
        "dumped_heat_mw_th":.05,"physical_chp_export_meter_mwh":.1,
        "contract_awarded_export_mwh":.1}
    rows=[dict(row,quarter_index=i,hour_index=i//4) for i in range(24)]
    replay={"feasible":True,"completed_15min_rows":rows,
        "terminal_stock_mwh_lhv":.75,"terminal_inventory_matches_initial_for_comparison":True}
    return replay,[1]*24,[0]*24,[0]*24,[.1]*24

class PhysicalSI(unittest.TestCase):
    def test_analytic_energy_ledger(self):
        result=a.audit_replay(*fixture())
        self.assertEqual(result["intervals"],24)
        self.assertTrue(result["terminal_matched"])
        self.assertAlmostEqual(result["energy_totals_j"]["electric_j"]/3.6e9,2.4)
        self.assertAlmostEqual(result["energy_totals_j"]["unrecovered_lhv_j"]/3.6e9,2.4)
        self.assertAlmostEqual(result["energy_totals_j"]["gas_in_j"]/3.6e9,6.)
    def test_dimension_power_as_energy_rejected(self):
        r,*args=fixture()
        r["completed_15min_rows"][0]["physical_chp_export_meter_mwh"]=.4
        with self.assertRaisesRegex(AssertionError,"Gross proxy meter"):
            a.audit_replay(r,*args)
    def test_gas_energy_created_rejected(self):
        r,*args=fixture()
        r["completed_15min_rows"][0]["stock_end_mwh_lhv"]+=.01
        with self.assertRaisesRegex(AssertionError,"Storage balance"):
            a.audit_replay(r,*args)
    def test_useful_heat_double_counting_rejected(self):
        r,*args=fixture()
        r["completed_15min_rows"][0]["dumped_heat_mw_th"]=.15
        with self.assertRaisesRegex(AssertionError,"Recovered heat allocation"):
            a.audit_replay(r,*args)
    def test_failed_prefix_cannot_claim_earnings(self):
        r,*args=fixture()
        r.update(feasible=False,completed_15min_rows=r["completed_15min_rows"][:4],
                 economic_contribution_eur=0.)
        with self.assertRaisesRegex(AssertionError,"Failed service assigned earnings"):
            a.audit_replay(r,*args)
        r["economic_contribution_eur"]=None
        self.assertEqual(a.audit_replay(r,*args)["intervals"],4)
    def test_invalid_ramp_even_with_fuel(self):
        r,*args=fixture()
        r["completed_15min_rows"][0]["gas_use_mw_lhv"]=1.5
        with self.assertRaisesRegex(AssertionError,"ramp"):
            a.audit_replay(r,*args)
    def test_nonfinite_rejected(self):
        r,*args=fixture()
        r["completed_15min_rows"][0]["gas_in_mw_lhv"]=float("nan")
        with self.assertRaisesRegex(AssertionError,"Nonfinite"):
            a.audit_replay(r,*args)
    def test_terminal_flag_rejected(self):
        r,*args=fixture()
        r["terminal_inventory_matches_initial_for_comparison"]=False
        with self.assertRaisesRegex(AssertionError,"terminal equivalence"):
            a.audit_replay(r,*args)
    def test_register_and_tampering(self):
        register=json.loads((ROOT/"data/evidence/v0926_physical_parameter_register.json").read_text(encoding="utf8"))
        source=(ROOT/"src/biogasflex/joint_v0921.py").read_text(encoding="utf8")
        external=json.loads((ROOT/"data/evidence/v0916_public_chp_source_registry.json").read_text(encoding="utf8"))
        self.assertEqual(a.check_register(register,source,external),23)
        altered=copy.deepcopy(register)
        altered["parameters"][0]["unit"]="s"
        with self.assertRaisesRegex(AssertionError,"Wrong units"):
            a.check_register(altered,source,external)
        altered=copy.deepcopy(register)
        altered["parameters"][0]["measured_on_target_equipment"]=True
        with self.assertRaisesRegex(AssertionError,"Fabricated calibration"):
            a.check_register(altered,source,external)
        with self.assertRaisesRegex(AssertionError,"Changed ETA_E"):
            a.check_register(register,source.replace("ETA_E=.4","ETA_E=.5"),external)

if __name__=="__main__":
    unittest.main()
