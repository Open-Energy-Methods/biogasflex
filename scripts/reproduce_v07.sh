#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -v 2>&1 | tee reports/v07_test_results.txt
python scripts/run_v07_study.py --plots
python scripts/independent_v07_audit.py
python -m biogasflex dispatch --config config/v06_oracle_two_period.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.6/oracle.json
python -m biogasflex heat-dispatch --config config/v07_oracle_two_period_heat.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.7/synthetic_oracle_heat_cost80.json
printf '\nBiogasFlex v0.7 complete; 81 tests, numerical audit and source-mixed study regenerated.\n'
