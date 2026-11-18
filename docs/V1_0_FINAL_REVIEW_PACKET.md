# BiogasFlex v1.0 — Final independent review and release decision packet

**State: REVIEW REQUIRED — NOT APPROVED FOR v1.0 OR FIELD USE.**

This packet extends the original review request in issue #3. It is an author/implementation-side handoff, not independent human peer review. A reviewer must independently assess the evidence and record their own findings. The actual release must use the commit that passed the complete integrated qualification and the post-merge main-branch checks.

## Evidence and claims under review

| Claim | Evidence | Limit |
|---|---|---|
| Independent source identity and 2019 regional prices/load-error pairing | A7 original source-chain certificate, v0.9.21 source register; original publisher SHA256 6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8 | Regional electricity evidence, not real site gas/heat or bid-time forecast vintages |
| Causal historical replay | 92 reused historical days; 29 infeasible days before protection; 58 failed policy replays | Fixed synthetic CHP assumptions |
| Gas reserve witness | 920 witnesses; 92/92 protected feasible per policy, 86/92 protected cyclic per policy | One next-source-hour synthetic lower gas witness; not future operational guarantee |
| Rigid hypothetical electrical awards | 15,584 executed prefix intervals; 6,592 witness quarters; 518 classified failures | No actual award settlement or grid-meter verification |
| Paired uncertainty and physical bounds | 19,602 training/holdout day-cell paths, 54 model cells and 54 bound certificates, 14 conditional passes | Proxy sensitivities, not empirical site covariance or reliability |
| SI energy and versioned parameter assumptions | 23 parameters; 1,472 replays; 23,288 executed quarters; 896 complete/576 failed | Not mass/pressure calibration, no target instrument uncertainty |
| Fixed contract acceptance | 2,208 day-gate outcomes; 15,232 executed intervals; one bounded accepted case, zero failed days within modeled support, 0 strict cyclic pairs | 92 equal-carryover paired outcomes, zero operating contribution difference; no real profit or repeated-day guarantee |
| Integrated numerical audit | A7 source-chain CI passed all semantic freezes and canonical/duplicate ledger identity checks (1,472 records) on ca1314ff688879a9a67e9e2c35864c14dd9022ee | Initial release CI failed three stale version assertions; corrected tree e8b9191 passed all nine workflows; final A8 edge correction requires new qualification |

Permanent aggregate certificates: data/evidence/v0928_executed_frozen_source_chain_certificate.json and data/evidence/v0928_green_a7_qualification_certificates.json (seven successful certificates, exact green A7 commit e8b9191bd5c221d31446ebbf402767d02adb6742; CI run 44412510533). Original job: https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44407079471/job/135165067350. A7 protocol: docs/V0928_RELEASE_QUALIFICATION.md. Original review context: docs/V09_REVIEW_PACKET.md and issue #3; the original review criteria also remain in force.

## Reviewer tasks (not automatically checked)

1. Independently derive the heat-aware dispatch, units, objective, physical boundaries and two-interval optimum; review the original 216-case conditional flexibility and five hypothetical emergency scenarios.
2. Verify source IDs, licence and attribution; inspect original publisher checksum and source transformations. Distinguish regional load forecast errors, lagged price baseline errors, synthetic gas/heat profiles, hourly source versus mathematical quarter intervals and repeated historical holdout.
3. Challenge causal information timing, commitment and switching, no-lookahead prefix tests, reserve witness semantics, full-foresight recourse and true versus conditional LP optimality. Verify that global MILP optimality is solver-reported where applicable.
4. Independently derive the fixed-award storage bounds, thermal feasibility, exact cyclic impossibility and terminal tolerance. Test adverse early/late burn and high/low gas paths. Check no terminal gas value, unavailable gas disposition, imported electricity or failed/rejected revenue was fabricated.
5. Check all complete and failed service denominators, matching of source dates and hardware, distinction of cyclic and carryover service, and canonical versus compatibility replay identity.
6. Re-run the full source-chain and offline qualification in a separately controlled environment. Start from the exact proposed release commit. Save package/OS/Python/SciPy versions, independent output checks, exit status, source digest and deviations.
7. Review field evidence gaps, real plant/gas pressure/volume/mass, backup fuel, actual net exports, equipment dynamics and authentic market claims. Reject any operational qualification or economic extrapolation unsupported by evidence.

## Human review record (to be completed by the reviewer)

- Reviewer identity and affiliation: NOT PROVIDED
- Relevant expertise and conflict-of-interest disclosure: NOT PROVIDED
- Exact reviewed commit and environment: NOT PROVIDED
- Independent reproduction instructions and result: NOT PROVIDED
- Review date: NOT PROVIDED
- Findings with file/line/evidence, severity (fatal/major/minor), consequences and requested fix: NOT PROVIDED
- Author response and verification of fixes: NOT PROVIDED
- Reviewer recommendation: NOT PROVIDED

No review has been performed simply by generating or committing this template.

## Release decision rules

A8 requires successful integrated CI and source-chain/study audits on the release candidate, independently recorded human methodological review with no unresolved fatal/major findings, consistent release version and licence metadata, source and code distribution checks, resolution of merge constraints, and successful main-branch post-merge regression. Use a review-approved tagged tree, not an arbitrary candidate version. Publish aggregate certificates in the durable source tree and retain exact CI links; do not redistribute raw underlying source data without appropriate permissions. Do not publish a v1.0 tag or DOI on CI success alone. External data and plant calibration remain explicit limits of the research release.


## A8 implementation-side final review finding — terminal tolerance

Finding A8-01 (numerical correctness; resolved in code, verification pending): the v0.9.25 bounded cyclic certificate compared gas rate differences (MW) to a stock-energy tolerance (MWh). At nominal fuel burn of 1 MW and constant gas arrivals of 1.00004 MW, the six-hour terminal deviation is 0.00024 MWh, greater than the 0.00005 MWh tolerance, although the old test returned a cyclic certificate. The production correction checks both extreme terminal inventory energy deviations against the tolerance; the independent oracle separately checks containment in the terminal energy band. Boundary adversaries include both high and low arrivals and a genuinely tolerable small support. No change to preregistered cells, data, or plant parameters. The original 54 bound certificates are expected to be identical; the full source-chain run must confirm.

This author-side finding is NOT independent human review or approval. Record actual reviewer findings separately and verify the exact final commit. Do not interpret the prior all-green A7 snapshot as approval for the changed tree.
