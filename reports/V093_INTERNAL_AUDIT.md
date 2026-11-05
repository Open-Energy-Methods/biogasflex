# BiogasFlex v0.9.3 — internal numerical verification audit

**Date:** 2026-11-05. **Status:** awaiting first hosted v0.9.3 CI run.
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
