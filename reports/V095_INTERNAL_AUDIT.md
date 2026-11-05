# BiogasFlex v0.9.5 — internal operating-envelope and forecast experiment audit

**Prepared:** 5 November 2026. **Status:** software development candidate;
with **10/10 hosted branch CI jobs passed** ([run 42042375641](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42042375641)). This is an internal
mathematical and code audit, **not external human scientific review**.

## Research scope and freeze boundary

The original 286 pinned research files, market-price sources, frozen
heat-aware CHP solver and 216 scenario results plus five explicitly
hypothetical emergency calculations remain byte-identical. v0.9.5
implements a separate opt-in experimental optimizer, not a rewrite
or retroactive reinterpretation of the earlier published-number
candidate.

## New technical contract

- Continuous, always-on electric power output floor.
- Direction-specific MW_e/hour ramp constraints between slot midpoints,
  plus a declared initial operating boundary condition.
- Retain original heat conversion, immediate thermal service,
  auxiliary/dumped heat, gas conservation and cyclic inventory.
- Reject baseline if it violates any experimental requirement.
- Numerically audit constraints and ensure the constrained economic
  optimum lies between a feasible fixed baseline and the original
  unconstrained heat-service LP optimum.
- Re-evaluate a frozen forecast dispatch under realized prices
  without replanning, and compare with the same model's ex-post
  perfect-foresight upper bound.
- Analytical 2-hour ramp and lower-bound examples; 24-hour synthetic
  horizon checks; 18 added tests (15 model, 3 CLI).

## Hosted acceptance gates

1. Historical research results unchanged: 286 original SHA-256 pins,
   216 primal-dual checks, 216+5 reproductions and inherited
   independent research audit.
2. All 96 solver-free v0.9.3 synthetic comparisons retained.
3. v0.9.5 new regression tests and independent toy analytical audit pass.
4. Strict hash manifest and Git coverage include every distributed file.
5. Ubuntu/macOS/Windows Python 3.11, 3.12, 3.13 plus installed-wheel
   smoke: 10/10 hosted jobs.
6. No automatic scientific release, tag, DOI or claim of plant accuracy.

## Remaining scientific risks

No realistic on/off commitment or equipment transients, gas vessel
fluid constraints, measured CHP export/heat demand, market trading
rules, forecast quality validation, CAPEX/NPV, site islanding ability,
or field pilot evidence. Original simulated scenario counts are not
probabilities. External independent review tracked in GitHub issue #3.

## Analytical boundary correction found by hosted CI

The original synthetic reversed-forecast oracle erroneously assumed that a\nzero-initial-inventory CHP could *advance* gas from the future to\nthe first hour. Corrected exact forecast regret is **€20** with\nnonbinding ramps and **€5** with the declared 0.1 MW_e/hour ramp;\nforecast schedule realized incremental value over the fixed comparator\nis zero. This is a consequence of strict first-period gas conservation,\nnot a numerical solver flaw. The correction changes only synthetic\noracle expectations, internal documentation and tests, never the\noriginal scientific scenario results.\n
## Verified internal numerical results

The hosted Ubuntu Python 3.12 reproduction completed 192 tests and all
216 inherited primal-dual market cases, 96 inherited solver-free
synthetic cases, 286 original frozen research file SHA-256 pins and
389 manifest file hashes. The 24-interval synthetic experiment showed
zero ramp violation. Two-hour ramp limits 0, 0.05, 0.1, 0.2 and
100 MW_e/h resulted in expected modeled incremental contributions
€0, €2.50, €5, €10 and €20. Minimum always-on power 0, 0.2,
0.36 MW_e with nonbinding ramp gave €20, €20, €4. Corrected
synthetic reversed-forecast regret is €20 with loose ramp and €5
with the declared ramp, with €0 realized increment versus the
constant-stock fixed comparator. Full 10-host matrix is recorded in
`docs/V095_REPRODUCIBILITY_MATRIX.md`.

This is internal software mathematical/constraint QA, not an external
scientific review or an operational/financial plant performance study.
