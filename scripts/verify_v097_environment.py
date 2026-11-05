"""Offline environment and install metadata smoke check for v0.9.7."""
from __future__ import annotations
import argparse
from importlib import metadata
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

MIN_PYTHON = (3, 10)
RELEASE_VERSION = '0.9.7'

def run(check_install: bool = False) -> dict:
    from biogasflex import __version__
    from scipy import __version__ as scipy_version
    if sys.version_info[:2] < MIN_PYTHON:
        raise RuntimeError('BiogasFlex requires Python 3.10 or newer')
    if __version__ != RELEASE_VERSION:
        raise RuntimeError(f'Package version mismatch: {__version__} != {RELEASE_VERSION}')
    from scipy.optimize import linprog, milp, Bounds
    check = linprog([-1.0], bounds=[(0.0, 1.0)], method='highs')
    if not check.success or abs(check.x[0] - 1.0) > 1e-9:
        raise RuntimeError('Installed HiGHS cannot solve the one-variable LP smoke test')
    discrete = milp([-1.0], integrality=[1], bounds=Bounds([0.0], [1.0]))
    if not discrete.success or abs(discrete.x[0] - 1.0) > 1e-9:
        raise RuntimeError('Installed HiGHS MILP cannot solve a binary smoke test')
    script = subprocess.run(
        [sys.executable, '-m', 'biogasflex', '--help'],
        capture_output=True, text=True, check=True, timeout=30,
    )
    for expected in ('heat-dispatch', 'emergency-service', 'dispatch', 'operating-surrogate', 'forecast-regret', 'unit-commitment', 'hourly-commitment'):
        if expected not in script.stdout:
            raise RuntimeError(f'Missing CLI command: {expected}')
    dist_version: str | None
    try:
        dist_version = metadata.version('biogasflex')
    except metadata.PackageNotFoundError:
        dist_version = None
    if check_install and dist_version != RELEASE_VERSION:
        raise RuntimeError(f'Installed distribution mismatch: {dist_version!r} != {RELEASE_VERSION}')
    return {
        'status': 'PASS',
        'package_version': __version__,
        'python_version': platform.python_version(),
        'python_executable': sys.executable,
        'platform': platform.platform(),
        'os_name': os.name,
        'scipy_version': scipy_version,
        'highs_smoke_test': 'PASS',
        'cli_smoke_test': 'PASS',
        'mixed_integer_smoke_test': 'PASS',
        'installed_distribution_version': dist_version,
        'distribution_check': 'PASS' if dist_version == RELEASE_VERSION else 'NOT_CHECKED',
        'internet_required_for_tests': False,
    }

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--require-installed',action='store_true')
    args=p.parse_args()
    try:
        print(json.dumps(run(args.require_installed),indent=2))
    except Exception as exc:
        p.exit(1,f'ENVIRONMENT CHECK FAILED: {exc}\n')
