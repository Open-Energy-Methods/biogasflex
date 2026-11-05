# BiogasFlex v0.9.3 — internal numerical verification audit

**Date:** 2026-11-05. **Status:** hosted development-branch validation **PASS** (10/10 jobs).
This is an internal software QA document, not external scientific review.

## New verification

A solver-independent *two-period* exact oracle enumerates feasible
intermediate gas inventories and heat-cost breakpoints. A predeclared
seeded 96-case synthetic stress protocol checks the original dispatch
solver's optimized contribution and conservation-derived metamorphic
identities. Eleven new tests supplement 163 inherited tests, for an
expected **174 regression tests**.

## Acceptance gates

- 174 tests and all 96 synthetic comparisons pass without silent exclusions
- Original 216 saved 24-hour dual certificates pass
- Original 216 market + five hypothetical emergency runs reproduce
- Frozen 286 scientific files and whole distribution SHA-256 manifest pass
- Ubuntu, macOS, Windows × Python 3.11–3.13 and wheel smoke pass

## Limitations

This is **not** full-horizon solver-independent verification, measured
plant commissioning, probabilistic inference from the three selected
2020 SE3 price days, 2022 site annual operation, investment
profitability/NPV, or real-life black-start/islanding validation.
Independent human methodological review remains open (GitHub issue #3).
No public GitHub Release or Zenodo DOI is made by this increment.

## Observed hosted evidence (5 November 2026)

The first complete post-correction [branch-push workflow
42038354589](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42038354589)
passed **10/10 jobs** at commit
`d06514fd7ed29627d81cb39c91029bb264029216`.
Ubuntu, macOS and Windows each passed Python 3.11, 3.12 and 3.13.
The separate Ubuntu Python 3.13 built-wheel installed smoke test passed.

**Observed Linux/Python 3.12 results:**

| Gate | Result |
|---|---:|
| Automated regression tests | **174 PASS** |
| Solver-independent synthetic oracle comparisons | **96 PASS** |
| Common spot-price translation tests | **24 PASS** |
| Common CHP variable-cost translation tests | **24 PASS** |
| Storage-capacity monotonicity chains | **12 PASS** |
| Zero-buffer tests among seeded cases | **17 PASS** |
| Maximum oracle-vs-HiGHS absolute objective difference | **€2.842170943040401e-14** |
| Historical market scenario dual certificates | **216 PASS** |
| Maximum original 216-case primal/dual gap | **€4.263256414560601e-13** |
| Original research files pinned SHA-256 | **286 unchanged** |
| Strict release manifest | **375 files PASS**; 376 Git-tracked files including manifest |

The previous test failure on an earlier transient commit was a **false positive
in a string-search-based no-NumPy-import test**: the explanatory oracle
docstring mentioned NumPy. A corrected AST-based import inspection now
checks actual imports and passed on hosted systems. The mathematical oracle
and frozen scientific modules did not change to fix this test.

The audit verifies **mathematical consistency for the selected synthetic
two-period model inputs** only. Neither original 24-hour general-case
solver independence, probabilistic or annual market inference, physical
plant dynamics, external human methodological review nor field
performance is established.
