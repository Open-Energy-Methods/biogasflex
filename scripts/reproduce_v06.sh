#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$(pwd)/src${PYTHONPATH:+:$PYTHONPATH}"
python -m unittest discover -s tests -v 2>&1 | tee reports/v06_test_results.txt
python -m biogasflex dispatch --config config/v06_oracle_two_period.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.6/oracle.json
python -m biogasflex sweep --config config/v06_oracle_two_period.json --prices data/synthetic/prices_2period_oracle.csv --output results/v0.6/oracle_sweep.json
python -m biogasflex dispatch --config config/v06_lovsta_counterfactual.json --prices data/observed/svk_se3_20200101_CC-BY-4.0.csv --output results/v0.6/lovsta_counterfactual.json
python -m biogasflex sweep --config config/v06_lovsta_counterfactual.json --prices data/observed/svk_se3_20200101_CC-BY-4.0.csv --output results/v0.6/lovsta_storage_sweep.json
python scripts/generate_v06_figures.py
