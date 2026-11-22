# v0.9.28 — Integrated release qualification (A7)

**Status: candidate only.** v1.0 is not released, and real field qualification remains blocked. This gate integrates the frozen v0.9.22–v0.9.27 implementation with the prior v0.9.21 code. No model parameters or historical dates are retuned. A7 passes only on the same integrated candidate tree with every required job successful; historical PASS certificates alone are insufficient.

## Prior scientific evidence and corrected regression

- A5 original [source audit job](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44392539659/job/135113724947): 23 parameters, 1,472 replays, 23,288 executed quarter-hours, 896 complete and 576 failed; maximum whole-horizon modeled energy residual 7.62939453125e-6 J; award energy residual zero. One macOS job was cancelled, so not an all-green A5 platform result.
- A6 original [source audit job](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44393700993/job/135117841620): all 92 dates, 24 gates, 2,208 outcomes, 15,232 executed intervals, one bounded accepted gate and zero failures for it; 0 strict cyclic matched pairs, 92 separate equal carryover pairs. The mean paired operating difference is structurally zero under identical awards and physical dispatch, not a profit improvement. The nominal gate accepted 0.100 MWh/interval cyclic contracts but failed terminal service on all 88 / 91 electrically completed cases at 1.5 / 3 MWh storage. Keep the historical failure denominator.
- A6 platform failure was traced to test_nonconstant_ramp_jump: 0.09 to 0.12 MWh in successive 15-minute slots is 0.12 MW, below the 0.20 MW limit. Replace with 0.09 to 0.15 (0.24 MW) and also assert the smaller step does not trigger ramp rejection. No solver behavior changed.

## Qualification matrix

Ubuntu, Windows and macOS × Python 3.11 and 3.13. In each environment:
1. Install current package, pip check, run the **full** unittest discovery suite.
2. Verify the entire tracked SHA-256 manifest and inherited frozen research input hashes.
3. Run the existing separately formulated LP primal/dual certificate (same HiGHS backend; not an independent solver implementation).
4. Create Git source ZIP of exact commit, extract and independently verify its manifest.
5. Build wheel, check exact package source bytes, distribution version, licence, internal RECORD member/checksum coverage and absence of unexpected wheel data. Install with dependencies into a fresh virtual environment in a temporary directory, with no checkout PYTHONPATH, verify actual installed module path and metadata, run CLI version and help, synthetic baseline CLI with explicit archived fixture paths, accepted and rejected hypothetical contract calculations, LP and MILP smoke tests. Record per-platform run-local ZIP/wheel SHA256; no claim of bitwise identical wheels across environments.
6. Record certificate and exact commit SHA. The code-only wheel is distinct from the source archive with fixture inputs and audit scripts. Checkout-relative legacy commands require the source archive or explicit input paths. Dependency installation requires network unless suitable cached wheels are supplied; offline calculations themselves need no new source download.

## Complete source chain

One Linux job acquires and SHA-verifies original OPSD release 2020-10-06, then runs the unmodified source-backed v0.9.21 joint study, causal study, reserve witness, hard awards, sensitivity, SI assurance and contract acceptance. Each independent source/physical/financial and conditional primal/dual checker is executed, and both failure diagnosis scripts run. A new independent compatibility view checker requires exact equality between canonical and duplicate legacy ledger entries (dates, all first-stage arrays and locks, hindsight fields, every replay) across all 1,472 replays. A semantic freeze compares audit counts and negative findings against previously executed values. Run-local hash fingerprints are not expected to equal earlier raw solver-time-dependent JSON hashes.

Preserve A1–A6 published claims exactly: 92 source days; 29 unprotected failures, 58 failed policy replays; 920 gas witnesses, 86 protected cyclic matches per policy; 518 classified failed hard-award replays; 54×363 sensitivity paths, 54 bounds; SI audit counts; 2,208 contract outcomes with no strict cyclic matched pairs. Any changed count fails the gate instead of silently updating the expected result. Original holdout has already been repeatedly inspected; no new independent external test-set claim.

Only aggregate source certificate and run-local hashes uploaded by this A7 job; no new raw provider CSV or hourly derived source copy. [Data attribution](../DATA_ATTRIBUTION.md) distinguishes MIT original software, provider attribution and upstream restrictions. Historical source registry and pinned technical references are preserved, no claim of blanket legal clearance.

## Integration and release no-go

Test the candidate against current main, preserve the main checksum hotfix, avoid force-pushing or discarding draft branch history. An aggregate integration PR should be merged only once CI is green, no unresolved conflicts, and required review is satisfied. No tag, DOI, v1.0 claim or field readiness at A7. Final A8 also requires issue #3 independent methodological review, scope statement and main-branch post-merge verification. No target gas composition, pressure/volume, real net export, calibrated site heat/gas, engine transient maps, authentic market award or forecast-vintage evidence is produced by release engineering.

## Executed integrated qualification and corrective action

On candidate ca1314ff688879a9a67e9e2c35864c14dd9022ee, the complete A1–A6 original-source semantic chain and all seven historical research workflows passed. The integrated platform regression ran 540 tests per environment; three stale assertions expecting v0.9.21 failed. The three version assertions are updated to the actual v0.9.28 package version, outside the inherited scientific byte freeze. No physical model changes. New qualification rerun required; the isolated wheel gate was not reached by those six jobs. Archive of the successful source job: data/evidence/v0928_executed_frozen_source_chain_certificate.json. Final human review and approval packet: docs/V1_0_FINAL_REVIEW_PACKET.md. The latter does not constitute independent review.
