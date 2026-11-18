"""Check frozen semantic outcomes and record exact run-local evidence hashes."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

EXPECTED={
 "joint_audit":{"source_training_real_price_and_electric_load_error_days":271,
    "source_heldout_real_price_and_electric_load_error_days":92,
    "conditional_KKT_and_heldout_checks":33,
    "global_MILP_optimality_independently_certified":False},
 "causal_audit":{"audited_days":92,"all_eligible_heldout_days_replayed":True,
    "infeasible_causal_replays_days":29,"matched_service_paired_cases":58},
 "reserve_audit":{"days_evaluated":92,"current_to_next_hour_witnesses_verified":920,
    "nominal_unprotected_full_horizon_feasible":63,"nominal_protected_full_horizon_feasible":92,
    "nominal_rescued_days":29,"joint_rescued_days":29},
 "award_audit":{"chronologically_eligible_days_audited":92,
    "modeled_15min_delivered_prefix_periods_verified":15584,
    "next_hour_award_locked_witness_quarters_verified":6592,
    "infeasible_hypothetical_contract_policy_replays_not_monetized":518},
 "award_diagnosis":{"source_heldout_days_audited":92,"failed_policy_replays_classified":518,
    "all_failed_ledger_paths_explicitly_classified":True},
 "sensitivity_audit":{"preregistered_cells_independently_recomputed":54,
    "independent_analytical_worst_bound_certificates":54,"physical_day_cell_paths_recomputed":19602,
    "robust_bounded_physical_certificates_passed":14},
 "si_audit":{"parameters_checked_against_literal_model":23,"heldout_days":92,
    "policy_replays_checked":1472,"quarter_hour_prefix_rows_checked":23288,
    "complete_replays":896,"failed_replays":576,"field_qualification":False},
 "contract_audit":{"eligible_days":92,"gates_checked":24,"day_gate_outcomes_checked":2208,
    "executed_intervals_checked":15232,"bounded_accepted_gates":1,
    "bounded_accepted_failures":0,"strict_cyclic_matched_pairs":0,
    "separate_equal_carryover_pairs":92,"market_or_field_validation":False},
 "canonical_audit":{"replays":1472,"heldout_days":92},
}
SOURCE_SHA="6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8"

def require(ok,msg):
    if not ok:raise AssertionError("A7 semantic freeze: "+msg)

def check_record(name,record):
    require(record["status"].startswith("PASS"),name+" audit not passed")
    for key,val in EXPECTED[name].items():
        require(type(record[key])==type(val) and record[key]==val,
                f"{name}/{key}: expected {val!r}, got {record[key]!r}")
    return {k:record[k] for k in ("status",*EXPECTED[name])}

def summary(directory):
    data={}
    for name in EXPECTED:
        path=directory/(name+".json")
        blob=path.read_bytes(); record=json.loads(blob)
        data[name]={"semantic_results":check_record(name,record),
                    "run_local_audit_file_sha256":hashlib.sha256(blob).hexdigest()}
    source=json.loads((directory/"source.json").read_text(encoding="utf8"))
    require(source["source"]["sha256"]==SOURCE_SHA,"wrong original publisher digest")
    # Record run-local exact bytes, without claiming bitwise solver/OS reproducibility.
    studies={}
    for n in ("source","joint","causal","reserve","award","sensitivity","contract"):
        path=directory/(n+".json")
        studies[n]=hashlib.sha256(path.read_bytes()).hexdigest()
    diagnoses=json.loads((directory/"causal_diagnosis.json").read_text(encoding="utf8"))
    require(diagnoses["heldout_days_checked"]==92 and len(diagnoses["failed_policy_replays"])==58,
            "causal failure denominator changed")
    reserve=json.loads((directory/"reserve.json").read_text(encoding="utf8"))
    for policy in ("nominal_policy","joint_policy"):
        require(reserve[policy]["protected"]["complete_and_terminal_matched_days"]==86,
                "reserve cyclic inventory matches changed")
    contract=json.loads((directory/"contract.json").read_text(encoding="utf8"))
    match=[r for r in contract["matched_service_comparisons"]
           if r["separate_equal_carryover_pairs"]>0]
    require(len(match)==1 and match[0]["separate_equal_carryover_pairs"]==92
            and match[0]["carryover_mean_operating_difference_eur"]==0.0,
            "matched carryover benchmark changed")
    require(all(r["strict_cyclic_mean_difference_eur"] is None
                for r in contract["matched_service_comparisons"]),"empty cyclic pair monetized")
    return {"status":"PASS_V0928_FROZEN_SEMANTIC_SOURCE_CHAIN",
            "git_sha":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
            "original_source_sha256":SOURCE_SHA,"audits":data,
            "run_local_study_sha256":studies,
            "causal_failures_classified":58,"reserve_cyclic_days_per_policy":86,
            "strict_cyclic_pairs":0,"equal_carryover_pairs":92,
            "carryover_mean_operating_difference_eur":0.,
            "all_global_milp_optimality_independently_proven":False,
            "bitwise_cross_platform_reproducibility_claimed":False,
            "real_site_and_market_qualification":False}

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--directory",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    x=p.parse_args()
    r=summary(x.directory)
    x.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf8")
    print(json.dumps(r,indent=2))
