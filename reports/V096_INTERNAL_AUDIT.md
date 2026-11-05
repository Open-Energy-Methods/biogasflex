# BiogasFlex v0.9.6 — internal on/off commitment code audit

**Prepared:** 2026-11-05. **Status:** experimental software candidate with\n**10/10 hosted CI PASS**; external human scientific review outstanding. The scope is software
verification, **not** a validated CHP operator schedule.

## Scientific boundary

The original 286 protected research files, source assumptions,
original 216 historic market dispatch scenarios and five hypothetical
outage cases are **unchanged**. The new MILP is a separate opt-in module
and an explicit synthetic demonstration only.

## Primary mathematical audit

- Binary commitment `on`, `startup`, `shutdown` variables,
  checked for integrality and exact transition correctness.
- CHP electric power must be zero when off or within the
  declared nonzero min-power/rated-output band when on.
- Ramps apply **only in steady on/on intervals**; switches
  are exempt, not physically modeled.
- Complete finite-horizon minimum up/down interval dwell enforced.
- Gas conservation, terminal stock and instantaneous CHP heat
  plus auxiliary service remain intact; independent ledger recomputes
  cost and conservation totals.
- Added event-specific startup/shutdown penalties and verified
  objective reconstruction.
- An infeasible fixed comparator is flagged and receives no
  physically meaningful incremental value; compare MILP value
  against a separate original unconstrained upper bound.
- Predeclared exhaustive pure-Python fixture oracle on a 0.5-MW
  discretization of the 3-interval synthetic scenario, including
  min-up 1/2/3 economic oracles (€55, €35, €15).

## Required verification

1. 13 MILP numerical/adversarial tests and three CLI tests,
   bringing the total expected suite from 192 to **208 tests**.
2. Independent synthetic 3-period enumeration, positivity and\n   validation of ledger, mixed-integer transitions and constraints.\n   Separate 24-hour synthetic MILP checks with two-interval minimum\n   up/down obligations and finite-horizon gas/heat/ramp audits.
3. All original 216-case primal-dual checks, 216+5 original case
   reproductions, 286 inherited file checksums, 96 two-interval
   solver-free comparisons, and v0.9.5 24h experimental audit.
4. Strict SHA-256 distribution manifest and complete Git coverage.
5. Hosted Ubuntu, Windows, macOS × Python 3.11, 3.12, 3.13
   plus installed wheel test: 10/10 green before merge.

## Remaining scientific gaps

Real equipment startup/shutdown trajectories, exact minimum on/off
duration in hours, pre-horizon residual dwell, variable start fuel,
gas vessel physical capacity/dynamics, heat demand measurements,
electrical grid constraints, NPV/CAPEX, realistic market settlement
and islanding/black-start hardware are absent. Independent scientific
methodological review tracked in issue #3 is outstanding. No public
GitHub Release or DOI warranted by this incremental internal audit.

## Observed QA evidence — 5 November 2026

The [branch workflow 42046779132](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42046779132)
passed all **10/10 jobs** on Ubuntu/macOS/Windows Python 3.11–3.13
and a separate installed-wheel smoke test. The Linux Python 3.12
reproduction logs show **208 passing regression tests**, **216 original
market LP dual checks**, **96 older solver-free synthetic comparisons**,
**286 original frozen scientific hashes** and a complete **402-entry
checksum manifest**. The new three-hour independent exhaustive
fuel-grid oracle reproduced **€55/€35/€15** modeled net contributions
for minimum-up 1/2/3 intervals. The separate 24-hour synthetic
commitment case reported **zero** gas-balance residual and
steady-on ramp violation with two-interval minimum up/down times.

Final documentation changes add a v0.9.6 hosted matrix and one more
manifest entry; the final snapshot must be reverified before merge.

All values are internal **synthetic software consistency** checks,
not observed plant earnings, dynamics or validated reliability.
