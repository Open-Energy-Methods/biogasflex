#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -v 2>&1 | tee reports/v08_test_results.txt
python scripts/run_v07_study.py --plots
python scripts/independent_v07_audit.py
python scripts/run_v08_study.py --plots
python scripts/independent_v08_audit.py | tee reports/V08_INDEPENDENT_AUDIT.json
printf '\nBiogasFlex v0.8: legacy results, 216 market scenarios, 5 emergency scenarios, figures and audits reproduced.\n'
