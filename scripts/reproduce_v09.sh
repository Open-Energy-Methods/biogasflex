#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -q
python scripts/recompute_v09_against_frozen.py
python scripts/independent_v08_audit.py
python scripts/audit_v09_candidate.py
python scripts/verify_v09_manifest.py
printf '%s\n' 'v0.9 reproducibility and integrity gates PASS (no user credentials or network)' 
