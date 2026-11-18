"""Adversarial fixed-award certification tests."""
import copy
import unittest
from biogasflex import contract_v0927 as c

def gate(awards=None,cap=3.,gas=(.78,1.22),heat=(.105,.195),service="carryover"):
    return c.acceptance([.09]*24 if awards is None else awards,capacity=cap,
        gas_lower=gas[0],gas_upper=gas[1],heat_lower=heat[0],heat_upper=heat[1],service=service)

class ContractGateTests(unittest.TestCase):
    def test_original_cap_rejects_high_gas_overflow(self):
        g=gate(cap=1.5)
        self.assertFalse(g["accepted"])
        self.assertIn("upper_storage_bound",g["rejection_reasons"])
    def test_large_cap_accepts_bounded_carryover_not_cyclic(self):
        g=gate()
        self.assertTrue(g["accepted"])
        self.assertAlmostEqual(g["terminal_lower_mwh_lhv"],.03)
        self.assertAlmostEqual(g["terminal_upper_mwh_lhv"],2.67)
        self.assertFalse(gate(service="cyclic")["accepted"])
    def test_nominal_gas_cyclic_mathematical_control(self):
        g=gate(awards=[.1]*24,cap=1.5,gas=(1.,1.),heat=(.15,.15),service="cyclic")
        self.assertTrue(g["accepted"])
        out=c.execute(g,[1.]*6,[.15]*6,[50.]*6)
        self.assertEqual(out["status"],"fulfilled")
        self.assertTrue(out["cyclic_stock_matched"])
    def test_nominal_cyclic_can_deliver_power_but_fail_terminal(self):
        g=gate(awards=[.1]*24,cap=1.5,gas=(1.,1.),heat=(.15,.15),service="cyclic")
        out=c.execute(g,[1.01]*6,[.15]*6,[50.]*6)
        self.assertEqual(out["status"],"terminal_service_failed")
        self.assertTrue(out["full_contract_energy_delivered"])
        self.assertIsNone(out["economic_contribution_eur"])
    def test_gas_extremes_are_feasible_for_accepted_bounded_case(self):
        g=gate()
        for x in (.78,1.22):
            for h in (.105,.195):
                o=c.execute(g,[x]*6,[h]*6,[30.]*6)
                self.assertEqual(o["status"],"fulfilled")
                self.assertFalse(o["cyclic_stock_matched"])
    def test_nominal_accepts_but_realized_path_fails(self):
        g=gate(cap=1.5,gas=(1.,1.),heat=(.15,.15))
        self.assertTrue(g["accepted"])
        o=c.execute(g,[1.22]*6,[.15]*6,[30.]*6)
        self.assertEqual(o["status"],"failed_during_delivery")
        self.assertIn("upper_storage_bound",o["failure_reasons"])
        self.assertIsNone(o["economic_contribution_eur"])
    def test_rejected_contract_neither_earns_nor_shuts_down(self):
        o=c.execute(gate(cap=1.5),[],[],[])
        self.assertEqual(o["status"],"rejected_pre_delivery")
        self.assertEqual(o["completed_rows"],[])
        self.assertIsNone(o["economic_contribution_eur"])
    def test_initial_ramp_incompatible_even_with_capacity(self):
        self.assertIn("consecutive_on_ramp",gate([.15]*24,cap=20)["rejection_reasons"])
    def test_nonconstant_award_prefix_cannot_hide_stock_violation(self):
        # Same aggregate as .09/slot, but early low burn fills a 1.5 MWh store.
        a=[.075]*12+[.105]*12
        g=gate(a,cap=1.5,gas=(1.,1.),heat=(.15,.15))
        self.assertTrue(g["accepted"])
        b=[.105]*12+[.075]*12
        self.assertTrue(gate(b,cap=1.5,gas=(1.,1.),heat=(.15,.15))["accepted"])
        g2=gate(a,cap=1.4,gas=(1.,1.),heat=(.15,.15))
        self.assertFalse(g2["accepted"])
        self.assertTrue(gate(b,cap=1.4,gas=(1.,1.),heat=(.15,.15))["accepted"])
    def test_nonconstant_ramp_jump(self):
        a=[.09]*23+[.15] # 0.24 MW jump exceeds 0.20 MW limit
        self.assertIn("consecutive_on_ramp",gate(a)["rejection_reasons"])
        self.assertNotIn("consecutive_on_ramp",gate([.09]*23+[.12])["rejection_reasons"])
    def test_zero_or_nonfinite_awards(self):
        self.assertFalse(gate([0.]*24)["accepted"])
        for v in (float("nan"),float("inf"),-.1):
            with self.assertRaises(ValueError):gate([.09]*23+[v])
    def test_future_source_hours_and_price_do_not_change_executed_prefix(self):
        g=gate()
        x=c.execute(g,[1.]*6,[.15]*6,[50.]*6)
        y=c.execute(g,[1.]*2+[1.22]*4,[.15]*2+[.195]*4,[50.]*2+[-20.]*4)
        self.assertEqual(x["completed_rows"][:8],y["completed_rows"][:8])
    def test_heat_service_bound(self):
        self.assertIn("bounded_heat_service",gate(heat=(.1,.5))["rejection_reasons"])
    def test_gate_lock_deterministic(self):
        self.assertEqual(c.digest(c.predeclare()),c.digest(c.predeclare()))
        g=gate();changed=copy.deepcopy(g);changed["accepted"]=False
        self.assertNotEqual(c.digest(g),c.digest(changed))

if __name__=="__main__":unittest.main()
