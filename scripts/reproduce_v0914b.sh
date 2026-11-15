#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/reproduce_v0914.sh
python scripts/audit_v0914b_sensitivity.py
printf '%s\n' 'v0.9.14-B: 81 factorial cases + 9 OAT + 2 hypothetical continuous-box proofs, independent oracle and original science PASS'
