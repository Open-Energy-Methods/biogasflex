# BiogasFlex v1.0 — Scientific release definition and evidence-based roadmap

**Release target:** a reproducible, source-citable **research optimization
software v1.0**, NOT an engineering-certified autonomous controller and
NOT proof of real Sweden SE3 CHP site revenues, physical reliability
or participation in a day-ahead market.

**Baseline now integrated on main:** v0.9.21 source-verified historical
SE3 source/paired scenario study, independent LP audits and synthetic CHP
physical equations. **v0.9.22 is a draft PR #28** with a 92-day
causal hourly source replay and independently diagnosed negative
feasibility result. **v0.9.23 is a stacked research milestone** for
a next-source-hour minimum synthetic gas reserve witness.
Neither should be described as merged until their PR is merged
and post-merge CI confirms the release tree.

## Two scientific validity levels that MUST NOT be conflated

### A. Research software v1.0 (possible without private site data)

Definition: stable package/CLI, explicit and independently audited
mathematical optimization, prescribed synthetic tests and
source-provenance validation, a fully documented and independently
reproducible finite historical benchmark, accepted contracts
**when supplied as hypothetical award inputs**, no-lookahead
causal dispatch tests, source license compliance and honestly reported
negative results. The hard guarantee is mathematical compliance
**with the stated model assumptions**, NOT that these equations
predict a specific real CHP engine.

A v1.0 software-release candidate is defensible only if
all gates A1–A8 below pass simultaneously. An unresolved physical
failure is acceptable only if it is faithfully reported, its
mathematical conditions diagnosed, and no operational success
claim is made. Any study that counts failed service as zero
earnings must fail the release gate.

### B. Industrial field-qualified decision support (BLOCKED)

This stronger label additionally requires confidential/authorized
engine and site telemetry, measured biogas composition/flow and
lower heating value, synchronized delivered grid-energy export
and useful-heat measurements, manufacturer/field-verified
startup/on-off/ramp/partial-load efficiency maps, gas storage
pressure and controls, timestamped historical bid-time price
forecasts and awarded export commitments, site heat/gas
forecasts with issuance timestamps, independent time-based
holdouts, valid uncertainty coverage and calibration/measurement
error budgets. None is presently established by the OPSD
regional electricity dataset. **Do not claim field validation
or actual profitability for v1.0 without that evidence.**

## Sequence and release-critical acceptance gates

| Gate | Milestone | Required evidence | Automatic no-go |
|---|---|---|---|
| **A1** | v0.9.22 historical causal benchmark | SHA-verified publisher original; 92/92 dates; fixed pre-reveal commitment; fully auditable energy/cash/feasibility; unconcealed null outcomes | A hidden source revision, missing dates or a lookahead leak |
| **A2** | v0.9.23 reserve viability | Declared lower gas bound; independent one-hour branch feasibility proof; causal prefix invariance; matched service economic effects; complete 92-day paired runs; original physics unchanged | Negative stock, unbounded ramps, future actual data supplied to control, or only successful dates reported |
| **A3** | v0.9.24 service/meter boundary | Bid-time/operation chronology; demand and accepted electrical MWh enforced exactly when **hypothetical award** is provided; explicit infeasibility under unknown/insufficient supply; meter sign convention and import/export | Calling final ex-post auction price an as-of-gate prediction, or treating unconditional CHP generation as a sold award |
| **A4** | v0.9.25 uncertainty and sensitivity | Frozen preregistered train/holdout split, block-paired errors, numerical sensitivity across uncertainty strength, gas storage, thermal backup, realistic lower/upper support; uncertainty intervals with serial dependence; explicit source vs uncalibrated proxy dimensions | Tuning proxy coupling after viewing holdout outcomes; reporting optimistic pseudo-probabilities |
| **A5** | v0.9.26 physics assurance | Independent residual tests of fuel mass/energy, heat, electric, stock, terminal and ramp; certified unit conventions; equipment parameters source register and normalized units; make calibration gaps machine-readable | Treating manufacturer generic spec or unrelated city-gas CHP observations as the selected biogas engine's exact calibration |
| **A6** | v0.9.27 comparison reproducibility | Same functional energy/heat service, initial/final stock, nominal vs robust objective, full infeasibility denominator, commitment decisions, perfect-hindsight upper bounds only on matched-service cases | Comparing different terminal inventory, different service obligations or different assumed plant equipment as an earnings win |
| **A7** | v0.9.28 independent release audit | At least 3 OS and 2 Python versions, full source-replay hash chain, independently recomputed physical/economic outcomes, adversarial input-corruption tests, release ZIP Git SHA256 coverage, wheel/install/CLI smoke tests, frozen negative-case examples | Any failing test, unaccounted distributed file, unverified source hash, or unpublished changed assumption |
| **A8** | v1.0 release/go-no-go | Version/tag/changelog/CITATION/README consistency, license attribution, machine-readable source limitations, signed-off scientific scope statement, separate blocked field-qualification section, reproducible DOI/archive plan | Claims of true market earnings, site reliability, production dispatch readiness, or a missing audit certificate |

Each milestone should have **one target PR**, a protocol
written before results, source/parameter provenance,
adversarial unit tests, an independent audit (not merely
the same optimizing model checked with itself), a complete
success-and-failure denominator, a full documented report,
and all CI green before merging. Stacked research PRs should
target their immediately preceding unmerged research branch;
merge in dependency order, rebase as necessary and rerun the
post-merge release matrix.

## v0.9.23 specific scientific question

Does a **one-hour nonanticipative, model-lower-bound
synthetic gas viability witness** avoid the observed current-
hour buffer/ramp infeasibilities, and at what cost, while
keeping frozen same-policy CHP commitments and every
original physical capacity limit?

Pre-registered principal outcomes on **all 92**
October–December 2019 source-complete days:
full six-hour feasible count; stock-matched feasible
count; terminal unmatched count; newly failed count;
rescued failed count; exact first-stage SHA identity;
mean protected-minus-unprotected modeled cashflow
**only among days where both policies fully deliver
the same service and matched terminal inventory**.
Secondary: minimum source-hour stock and number of
validated witness constraints. Report unchanged
nominal/maximin commitments as an explicit null result.

The one-hour lower-gas branch is not a true six-hour
robust viability kernel: no all-realization supply
claim, no simulated real sensors, no source-timestamp
proof. If all baseline failures disappear, that is
a conditional finding *within the synthetic model*,
not a 100% real-plant service guarantee.

## Data acquisition dependencies (cannot be fabricated)

| Dependency | Present state | Field claim blocked |
|---|---|---|
| Original OPSD SE3 prices and regional electric-load reported forecast | Source SHA known and verified | Market gate-time vintage of every archived forecast |
| Real biogas fuel input at selected CHP plant | Not available | Engine fuel availability, LHV, ramp and emissions |
| Useful process-heat and backup heat metering | Not available | Actual heat-service balance |
| Grid exported electricity and accepted day-ahead award | Not available | Actual settlement or contractual performance |
| CHP startup, ramp, minimum load and fuel map | Not plant-calibrated | Manufacturer-certified technical feasibility |
| Gas-holder pressure, volume and dispatch behavior | Not plant-calibrated | True safety reserve and transient constraints |
| Independent site-based forecast holdout | Not available | Out-of-sample field predictive accuracy |

The research-software release must retain these
blockers as machine-readable scope statements even if
every numerical test passes. Do not invent missing
measurements, private permissions, or vendor quotations.

## Software release quality definition

The release must be installable from a wheel without
network calls during normal optimization. The research
CLI must write user-specified results outside the
tracked source tree, with original publisher archive
download explicitly opt-in and all checksums verified.
All published model parameters must name units,
physical/empirical/synthetic origin and ranges.
Negative results, infeasible days and unmatched
terminal inventory must remain present in machine-
readable outputs and executive research summaries.

**Reproducibility statement:** independent audits
reusing the HiGHS backend verify separate primal
physical equations but do not substitute for global
MILP optimality certificates when mixed integer
proof is required. The original 92-day experience
cannot establish general future stochastic coverage.

**Success criterion for v1.0:** a serious peer can
run the archived version, reproduce every declared
mathematical/source-backed finding, detect injected
future-data leaks and broken energy/contract balances,
and understand exactly which field-validity claims
remain unproven.
