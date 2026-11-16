#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -q
python scripts/recompute_v09_against_frozen.py
python scripts/independent_v08_audit.py
python scripts/audit_v09_candidate.py
python scripts/verify_v0921_environment.py
python scripts/verify_v091_inherited_frozen.py
python scripts/certify_v092_dual_bounds.py
python scripts/run_v093_stress.py
python scripts/audit_v095_operational.py
python scripts/audit_v096_commitment.py
python scripts/audit_v097_hourly.py
python scripts/audit_v098_rolling.py
python scripts/audit_v0981_maintenance.py
python scripts/audit_v099_historical.py
python scripts/audit_v0910_market_boundary.py
python scripts/audit_v0911_hard_contract.py
python scripts/audit_v0912_external_chp.py
python scripts/audit_v0913_market_provenance.py
python scripts/audit_v0914_chp_sources.py
python scripts/audit_v0914b_sensitivity.py
python scripts/audit_v0915_telemetry_qa.py
python -m biogasflex public-chp-sources
python -m biogasflex benchmark-v0918 --smoke
python -m biogasflex benchmark-v0919 --smoke
python -m biogasflex price-robust-v0920 --smoke
python -m unittest tests.test_v0921_opsd_evidence tests.test_v0921_joint_correlated -q
python -m unittest tests.test_v0917_kitakyushu_real -v
python scripts/verify_v09_manifest.py
python scripts/verify_v091_git_coverage.py
printf '%s\n' 'v0.9.21 market data provenance and inherited external annual CHP/optimization, exact duals, synthetic LP oracle, ramp model, binary on/off oracle and manifest PASS'
