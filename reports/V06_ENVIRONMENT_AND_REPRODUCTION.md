# Verified v0.6 execution environment

- Python: 3.13.5
- SciPy / HiGHS interface: SciPy 1.17.0 (`scipy.optimize.linprog`)
- NumPy: 2.3.5 (transitive dependency)
- Matplotlib: 3.10.8 (optional figure regeneration only)
- Platform: Linux, CPython 3.13
- Verification: `PYTHONPATH=src python -m unittest discover -s tests -v` passes **40 tests**; all four built-in reproducibility commands execute successfully.
- Install smoke test: `python -m pip install --no-deps --no-build-isolation -e .` succeeded in the prepared development environment with build tools already available; executing the installed CLI from `/tmp` reproduced the EUR 24 two-period oracle.
- A separate minimal Python virtual environment lacked compatible `setuptools` build backend without downloading build dependencies. The ordinary `python -m pip install -e .` command is expected to resolve/build dependencies in a networked environment; the documented `PYTHONPATH=src` fallback can run offline once SciPy is installed. No claim of an independently network-free clean pip install is made.
- All reports, test cases, data snapshots, documented v0.5.1 references, and generated outputs are bundled; no private data access needed.
