# BiogasFlex v0.9.2 — internal optimality-certificate audit

**Dated:** 2026-11-05  
**Scope:** 216 *unchanged* finite sensitivity cases from the frozen v0.8
study, using the original v0.9 research files.  
**Reviewer status:** Internal AI-assisted code audit. Not a separate
optimization engine, human peer review, full plant validation or certification.

## Added scientific-numerical question

Can an independently constructed mathematical dual bound each reported
24-hour market-case contribution from above while the saved dispatch passes
its own exact storage, heat, nameplate and objective constraints?

The new `scripts/certify_v092_dual_bounds.py` creates an LP with
five decision blocks and one free dual multiplier per equality row.
It reads saved hourly inputs and reconstructs the objective rather than
importing `src/biogasflex/heat_dispatch.py`. It solves the *dual* LP
using the same SciPy/HiGHS backend as the historical primal.

## Observed development-branch results

[Ten-job hosted workflow](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42034376782)
on commit `2310e0ae155995a27004c91da942391db3004469`: **10/10 PASS**.

| Check | Evidence |
|---|---|
| 163 regression tests | Passed |
| 216 saved market-case dual certificates | Passed |
| Max absolute primal/dual gap | €4.263256414560601e-13 |
| Max primal equality residual | 1.1102230246251565e-16 |
| Max dual inequality violation | 5.329070518200751e-15 |
| 286 pinned inherited research files | Byte-identical |
| Manifest integrity | 363/363 passed before this report was added |
| Hosted OS/runtime | Ubuntu, macOS, Windows × Python 3.11–3.13 |
| Wheel installation outside checkout | Passed on Ubuntu Python 3.13 |

## Interpretation

The tiny numerical gaps establish an additional check of internal
mathematical LP optimality for the **specified frozen assumptions**.
They are not estimates of error in source measurements, predictions of
real plant performance or proof that market participation is feasible.

The scenario tally (96 positive and 120 numerically near-zero conditional
cases), maximum selected-day modeled €15.7953 uplift, original three 2020
price days and 2022 annual Lövsta reference remain unchanged.
The new checks do not identify new scientific findings.

The five hypothetical no-gas-inflow critical-service cases remain verified
by inherited input-contract and conservation checks, rather than a new
economic optimality dual.

## Open gates before a publication-grade scientific claim

The external reviewer issue remains
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
Still absent: physical CHP transient constraints, measured site heat and
electricity operational data, defensible storage and auxiliary heat
investment/operating cost estimation, and real islanding capability.
No GitHub Release or Zenodo DOI is authorized by this internal audit.

## Dedicated v0.9.2 environment verifier and final pre-merge checks

[Follow-up hosted Actions run 42034834791](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/42034834791) completed **10/10 PASS** with dedicated `scripts/verify_v092_environment.py`, including nine platform/Python combinations and the wheel smoke. No frozen source, input, scenario or reported output file changed; only code outside the frozen research hash set, documentation, metadata and release integrity manifests were modified. Final release status remains a *development candidate*, not an externally reviewed or DOI-published result.
