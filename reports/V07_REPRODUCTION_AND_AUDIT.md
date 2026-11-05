# v0.7 reproduction and audit instructions

Run from project root with Python >=3.10 and SciPy >=1.11. Figures optionally require matplotlib. The supplied price CSV is attributed under Svenska kraftnät's stated CC BY 4.0 terms; rights details in `data/observed/README.md`.

Linux/macOS: `bash scripts/reproduce_v07.sh` (with matplotlib installed) or execute the commands below separately.
Windows PowerShell: `powershell -ExecutionPolicy Bypass -File scripts/reproduce_v07.ps1`.

1. `python -m pip install -e .` (install from local source; SciPy wheel may require access during initial environment setup)
2. `python -m unittest discover -s tests -v`
3. `python scripts/run_v07_study.py` (CSV, JSON, full 24-case sweep)
4. `python scripts/independent_v07_audit.py` (no SciPy import)
5. `python scripts/run_v07_study.py --plots` if matplotlib is available (figures optional)

The published results include SHA-256 input fingerprints in their JSON `provenance`. Verification of the saved source/config/price file hashes is distinct from independent checking of numerical outputs. The separate-code script can detect several kinds of tampering in outputs. It does not establish plant physical validation or external review.

**Automated tests:** 40 prior baseline/dispatch tests, 35 new thermal-model checks, and 6 separate-checker/integrity tests = 81 total. Original v0.6 source and results were not discarded. Mathematical toy oracle must match EUR 60 fixed, EUR 84 electricity gross optimized, EUR 14.40 auxiliary heat penalty and EUR 9.60 extra contribution.
