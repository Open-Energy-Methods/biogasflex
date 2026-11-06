#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -q
python scripts/recompute_v09_against_frozen.py
python scripts/independent_v08_audit.py
python scripts/audit_v09_candidate.py
python scripts/verify_v099_environment.py
python scripts/verify_v091_inherited_frozen.py
python scripts/certify_v092_dual_bounds.py
python scripts/run_v093_stress.py
python scripts/audit_v095_operational.py
python scripts/audit_v096_commitment.py
python scripts/audit_v097_hourly.py
python scripts/audit_v098_rolling.py
python scripts/audit_v0981_maintenance.py
python scripts/audit_v099_historical.py
python scripts/verify_v09_manifest.py
python scripts/verify_v091_git_coverage.py
printf '%s\n' 'v0.9.9 historical science, exact duals, synthetic LP oracle, ramp model, binary on/off oracle and manifest PASS'
