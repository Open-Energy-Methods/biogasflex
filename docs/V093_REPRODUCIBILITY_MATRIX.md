# BiogasFlex v0.9.3 — observed hosted reproducibility matrix

**As of:** 5 November 2026. Distinguish verified hosted runs from
physical/epistemic validation. The 10-job
[GitHub Actions branch run 42038354589](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42038354589)
completed successfully on
`d06514fd7ed29627d81cb39c91029bb264029216`.

| Environment | Interpreter | Observed result |
|---|---|---|
| Ubuntu hosted | Python 3.11 | PASS |
| Ubuntu hosted | Python 3.12 | PASS |
| Ubuntu hosted | Python 3.13 | PASS |
| macOS hosted | Python 3.11 | PASS |
| macOS hosted | Python 3.12 | PASS |
| macOS hosted | Python 3.13 | PASS |
| Windows hosted, PowerShell | Python 3.11 | PASS |
| Windows hosted, PowerShell | Python 3.12 | PASS |
| Windows hosted, PowerShell | Python 3.13 | PASS |
| Ubuntu built-wheel outside checkout | Python 3.13 | PASS |

The complete `reproduce_v093` script, invoked on every OS/Python
research job, checks 174 tests, all 216 pre-existing mathematical dual
certificates, 216 original market and five hypothetical emergency
scenario recomputations, the 286 original frozen scientific files,
the deterministic 96-case synthetic oracle suite, checksum manifest,
and Git coverage.

The observed Linux Python 3.12 synthetic report (seed `20261105`):
**96** independent two-interval comparisons, **24** price translations,
**24** uniform CHP cost translations, **12** four-capacity monotonicity
chains, and **17** zero-buffer checks, all passed. Maximum observed
absolute difference between exact breakpoint oracle and HiGHS
economics: **€2.842170943040401e-14**, versus prespecified €2e-6
acceptance tolerance.

All 286 inherited files remain byte-identical. At the observed snapshot,
**375 distributed files** passed SHA-256 integrity, with 376 tracked
files including the manifest. Documentation changes made after this
run may increase manifest count; they must pass follow-up CI.

Scope: This proves no observed CHP plant profit, physical storage
design, forecast/annual-market generalization, black start, practical
islanding, or external human peer review. The two-interval solver-free
oracle is **not** a full 24-hour independent mathematical solver.
Dependencies may require the online package index for fresh
installation; source-data reproduction after installation is offline.
No public GitHub Release or Zenodo DOI was created.
