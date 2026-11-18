"""A7: independently verify canonical results equal every compatibility view."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

def require(ok,message):
    if not ok: raise AssertionError("A7 canonical ledger: "+message)

def same_view(cases,view,select,mode,hindsight_key):
    rows=view["rows"]
    require(len(cases)==len(rows),"canonical/view size")
    count=0
    for c,r in zip(cases,rows):
        require(r["heldout_day_utc"]==c["day_utc"] and r["heldout_ordinal"]==c["heldout_ordinal"],
                "canonical/view chronology")
        policies=select(c)
        require(set(policies)==set(r["comparisons"])=={"nominal","joint"},"policy set")
        for name,p in policies.items():
            entry=r["comparisons"][name]
            for field in ("first_stage_sha256_pre_reveal","first_stage_on","first_stage_starts","first_stage_stops"):
                require(p[field]==entry[field],"canonical/view first-stage "+field)
            require(r["pre_reveal_policy_hashes"][name]==p["first_stage_sha256_pre_reveal"],"canonical/view lock")
            replay=p["replays"][mode] if "replays" in p else p[mode]
            require(replay==entry["causal_hourly_observation_replay"],"canonical/view replay mismatch")
            require(p[hindsight_key]==entry["same_binary_full_future_recourse_upper_bound_eur"]
                    and p["hindsight_feasible"]==entry["same_binary_hindsight_feasible"],"canonical/view oracle")
            count+=1
    return count

def audit(reserve,award):
    cases=reserve["cases"];aw_cases=award["cases"]
    require(len(cases)==len(aw_cases)==92,"full historical benchmark required")
    require([c["day_utc"] for c in cases]==[c["day_utc"] for c in aw_cases],"different dates")
    n=0
    for mode in ("unprotected","protected"):
        n+=same_view(cases,reserve["views_for_independent_v0922_ledger_audit"][mode],
                     lambda c:c["policies"],mode,"hindsight_upper_bound_eur")
    for profile in ("floor_budget_0p090","nominal_gas_0p100","initial_ramp_stress_0p150"):
        for mode in ("award_only","award_and_reserve"):
            n+=same_view(aw_cases,award["complete_replays_for_independent_v0922_audit"][profile][mode],
                         lambda c:c["award_profiles"][profile]["strategies"],mode,
                         "unconstrained_export_hindsight_upper_bound_eur")
    require(n==1472,"missing replay mapping")
    return {"status":"PASS_V0928_CANONICAL_COMPATIBILITY_IDENTITY","replays":n,"heldout_days":92}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("reserve","award","output"):p.add_argument("--"+name,required=True,type=Path)
    x=p.parse_args()
    result=audit(json.loads(x.reserve.read_text(encoding="utf8")),json.loads(x.award.read_text(encoding="utf8")))
    x.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf8")
    print(json.dumps(result,indent=2))
