# BiogasFlex v0.9.5 — internal operating-envelope and forecast experiment audit

**Prepared:** 5 November 2026. **Status:** software development candidate;
pending observed GitHub Actions verification. This is an internal
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
