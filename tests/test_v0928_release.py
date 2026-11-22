"""Negative controls for release gate checks, with no source download."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import audit_v0928_release_summary as s
import audit_v0928_canonical_ledgers as c
from qualify_v0928_distribution import check_paths

class Qualification(unittest.TestCase):
    def test_unsafe_archive_entries(self):
        for name in ("../escape","/absolute","C:/x","a\\b"):
            with self.assertRaises(AssertionError): check_paths([name])
        with self.assertRaises(AssertionError):check_paths(["a","a"])
        check_paths(["src/a.py","LICENSE"])
    def test_frozen_counts_and_status(self):
        rec={"status":"PASS_INDEPENDENT",**s.EXPECTED["contract_audit"]}
        s.check_record("contract_audit",rec)
        for key,value in [("bounded_accepted_failures",1),("strict_cyclic_matched_pairs",1),
                          ("market_or_field_validation",True),("status","FAIL")]:
            changed=dict(rec,**{key:value})
            with self.assertRaises(AssertionError): s.check_record("contract_audit",changed)
    def test_canonical_replay_not_duplicate_forgery(self):
        p={"first_stage_sha256_pre_reveal":"hash","first_stage_on":[1],
           "first_stage_starts":[0],"first_stage_stops":[0],
           "unprotected":{"completed_15min_rows":[{"gas_use_mw_lhv":1.}]},
           "hindsight_upper_bound_eur":2.,"hindsight_feasible":True}
        cases=[{"day_utc":"2019-10-01","heldout_ordinal":0,"policies":{"nominal":p,"joint":deepcopy(p)}}]
        comparisons={}
        for n,q in cases[0]["policies"].items():
            comparisons[n]={k:deepcopy(q[k]) for k in ("first_stage_sha256_pre_reveal","first_stage_on","first_stage_starts","first_stage_stops")}
            comparisons[n].update(causal_hourly_observation_replay=deepcopy(q["unprotected"]),
                same_binary_full_future_recourse_upper_bound_eur=2.,same_binary_hindsight_feasible=True)
        view={"rows":[{"heldout_day_utc":"2019-10-01","heldout_ordinal":0,
                       "pre_reveal_policy_hashes":{"nominal":"hash","joint":"hash"},"comparisons":comparisons}]}
        def verify(): return c.same_view(cases,view,lambda d:d["policies"],"unprotected","hindsight_upper_bound_eur")
        self.assertEqual(verify(),2)
        view["rows"][0]["comparisons"]["nominal"]["causal_hourly_observation_replay"]["completed_15min_rows"][0]["gas_use_mw_lhv"]=1.1
        with self.assertRaisesRegex(AssertionError,"replay mismatch"):verify()

if __name__=="__main__":unittest.main()
