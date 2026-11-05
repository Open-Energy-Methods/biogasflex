# BiogasFlex v0.9.7 — preliminary internal clock-hour commitment audit

**Prepared:** 5 November 2026. **Status:** experimental candidate
pending hosted multi-platform CI and independent scientific review.
This is a model/software audit, not real CHP operational
certification or an independent peer review.

## Modifications and freeze boundary

The original 286 pinned research files, original 216 market
solutions plus five explicitly hypothetical interruption cases,
inherited gas/heat LP, old solver-free analytical oracle, the
v0.9.5 operating LP and the v0.9.6 period-count MILP remain
byte-for-byte untouched. A **separate new opt-in** v0.9.7 MILP
implements clock-hour minimum operating duration and declared
initial residual obligations.

## Core reasoning and checks

1. All scenario timestamps remain sorted, distinct and UTC
   contiguous, with declared positive interval lengths.
2. Binary starts/stops at slot boundaries must meet all
   overlapping slots under `start_hour + minimum_up/down_hours`.
   An event lacking sufficient horizon hours is rejected.
3. A known initial ON/OFF dwell obligation locks each
   intersected early interval; remaining obligation beyond
   horizon is tracked explicitly rather than silently dropped.
4. Gas conservation, cyclic terminal gas, heat service and
   electric rating are unchanged; independent post-solve
   accounting checks gas/heat/CHP and switching cost ledgers.
5. Fixed comparator receives uplift only if it meets binary
   and carried-history obligations; prior unconstrained
   heat-service LP remains a modeled upper bound.
6. Solver-free analytical oracle exhaustively enumerates all
   four ON/OFF patterns and feasible inventory endpoints in
   a narrowly exact two-slot synthetic geometry; expected
   net €45 at 1h and €40 at 1.01h, with 1.26h infeasible.
7. 36-slot mixed quarter-hour/one-hour 24h synthetic
   exercise checks hour accounting, minimum ON 1.25h / OFF
   0.75h, gas conservation and steady-ON ramp requirements.
8. Retain all inherited scientific checks and test harnesses.

## Planned hosted release-engineering gates

- Expected **224 regression tests**: original 208 + 13
  new solver/clock/boundary tests + 3 new CLI tests.
- Original 216 market-case dual LP checks and 216+5 research
  result reproductions.
- All 286 inherited scientific file hashes and 96 prior
  two-interval solver-free comparisons.
- All v0.9.5 and v0.9.6 synthetic/analytical audits.
- Strict every-distributed-file SHA-256 and Git tree coverage.
- GitHub Actions: 9 Python/OS combinations and installed-wheel
  smoke, 10/10 required to merge.

## Unresolved research limitations

Event switch dynamics, gas fuel needed to start, minimum stable
load data, residual histories from a measured site, plant
hydraulics, CHP real controller tracking, heat storage,
market revenues, actual emissions/NPV and verified islanding
are outside this candidate. No empirical CHP validation
or independent human scientific review. Issue #3 remains open.
No automatic public GitHub Release or Zenodo DOI.

## Observed hosted mathematical and integrity QA

The [reviewed-code push](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052149427)
and [pull-request workflow](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42052216953)
both completed successfully with all ten jobs on the 3-OS,
3-Python-version and installed-wheel matrix.

Observed Ubuntu Python 3.12 output confirms **224 passing
tests**, **216 original market dual LP certificates**, **96
inherited solver-free small-case comparisons**, **286 original
research file hashes**, and **415 strict distribution SHA-256
file hashes** at the reviewed code tip.

The solver-free exact two-slot oracle reproduced the modeled
net contribution **€45 / €45 / €40** for minimum-up dwell
0.25h / 1h / 1.01h and correctly rejected the 1.26h
horizon-violating startup. The synthetic 24h/36-slot stress
reported max gas-balance residual **5.551e-17 MWh_LHV**
and max steady-ON ramp excess **2.637e-16 MW_e**.

The new reproducibility matrix is one more document and
requires final-commit integrity checks. These are solely
hypothetical software/model calculations, not plant validation
or externally peer-reviewed engineering evidence.
