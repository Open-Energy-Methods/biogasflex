# BiogasFlex v0.9.23 — Causal next-hour synthetic gas-reserve witness

**Status:** research implementation. Not a released or plant-certified controller.
Extends the frozen [v0.9.22 full heldout study](../reports/V0922_EXECUTED_FULL_HOLDOUT_CAUSAL_FEASIBILITY.md)
without modifying that historical source protocol or tuning synthetic gas
and heat couplings to held-out outcomes.

## Why this milestone is needed

The original 92-day experiment included 29 days with infeasible
six-hour causal CHP replay, in both compared commitment policies.
The independently reconstructed failed source hour was itself
infeasible in 58/58 policy failures. Alternative *unphysical*
one-family relaxations of stock nonnegativity or electrical
consecutive-ON ramp each restored this four-slot local LP feasibility.
Consequently the scientific next question is whether the existing
controller's present-hour consumption can be constrained **before**
the following gas observation arrives so that a legitimate next
source hour remains feasible under a declared low-gas scenario.

The underlying nominal and paired maximin binary commitments were
identical on 92/92 held-out dates. This milestone accordingly compares
the original and protected **continuous dispatch policy under exactly
the same frozen first-stage commitment**. It does not manufacture
artificial nominal-versus-robust binary differences.

## The protection constraint

At each source hour h=0,...,4, after the current source-hour's
hypothetical gas and heat observations have been revealed, the 15-min
forecast LP plans the remaining six-hour window as before.
It adds eight **zero-cost auxiliary feasibility-witness variables**:
four fuel-burn decisions u' (MW_LHV) and four end-of-quarter stocks
s' (MWh_LHV) for *only the next source hour h+1*.

The witness begins at the **same** gas-stock state and electric CHP
power chosen for the fourth current-hour 15-minute interval.
For each next-hour quarter interval q in [0,3]:

- Exact fuel balance: s'_q = s'_(q-1) + 0.25(g_min-u'_q),
  with the current hour's last forecast stock s_h,3 used as the
  predecessor for q=0.
- Exact physical bounds: 0 <= s'_q <= 1.5 MWh_LHV.
- Frozen CHP binary commitment: u'_q=0 when OFF and
  0.5 <= u'_q <= 2 MW_LHV when ON.
- Exact inherited consecutive-ON electric ramp:
  abs(0.4u'_q - 0.4u'_(q-1)) <= 0.8 * 0.25 MW_e.
  At q=0 the predecessor is the current hour's final actual
  planned power, not a freely invented witness state.
  Transitions involving OFF retain v0.9.22's documented exemption.

The witness uses **g_min = 0.78 MW_LHV**, the absolute lower
saturation of the unchanged *fictional* gas proxy formula in
v0.9.21. That is a predeclared exact **synthetic model-support
bound**, not a statistically estimated gas forecast lower
quantile, a manufacturer specification, or a measured plant
minimum supply. A public runner is not allowed to raise this
floor and claim it is still a guaranteed bound. Future realized
synthetic gas or source-day electricity prices are NEVER used
in constructing the witness.

The independent current-hour heat constraints can be omitted
from this specific witness for only the declared fictional
parameter bounds: site heat demand is at most 0.195 MWth,
below the 0.20 MWth backup rating, and even 2 MW_LHV fuel
burn creates only 0.4 MWth CHP heat, within the separate
0.4 MWth dump rating. The protected LP asserts these inequalities,
and independent tests check the physically constrained witnessed
future fuel and power trajectories. That simplification is **not**
transferable to arbitrary CHP plants or process-heat models.

The primary nominal remaining-horizon forecast LP, soft cyclic
terminal inventory penalty (EUR 50/MWh_LHV in forecast objective)
and all actual cashflow calculations are unchanged. The witness
only adds an **existential** next-hour feasibility condition
to the current LP. The witness's actual numerical controls are
not executed: upon new source-hour observation the actual
controller replans. There is no fictional liquid-fuel backup,
unbounded gas waste, negative inventory, invented heat supply,
or ramp relaxation.

## Limited nature of the guarantee

A feasible single subsequent source-hour branch at the model
floor is **not a universal robust viability certificate** for
all future arbitrary high/low-gas sequences, upper inventory
overflow at changing gas supply, physical reaction times,
four-quarter real measured gas variation, unknown biogas
composition, buffer pressure, original market bids or exact
terminal stock. This bounded test is useful because it
addresses the independently diagnosed failure mechanism
without retrospectively changing frozen policy commitments.

Realistic plant-safe reserve guarantees require a dynamic
viability kernel including both upper and lower future fuel
bounds, minimum switching time and startup transitions,
independently calibrated performance and time-stamped plant
forecast/vintage information. The current research protocol
explicitly refuses to claim more.

## Same-plant, same-policy comparison rules

For each 2019-10-01 to 2019-12-31 held-out date:

1. Verify all 24 UTC hourly source records and the complete
   exact 7-day-prior history. Freeze training standardizers,
   eight historical paired residual blocks and the nominal
   and joint binary MILPs before any held-out residual reveal.
2. Reveal the current source-hour's *synthetic* gas and heat
   state, while continuing to hide all future realized source
   hours and all contemporaneous/future realized electricity
   prices from the controller.
3. Replay both unprotected and witness-protected controllers
   with the **same prelocked binary schedule**. Record every
   physical state, source-hour observation, and next-hour
   witness; report any solver infeasibility without zero profit.
4. Independently recheck chronological historical price
   eligibility, v0.9.22 per-quarter gas/heat/electric balances,
   switched-unit commitment, ramp, source hashes and terminal
   inventory separately for each controller.
5. Independently reconstruct EVERY reported witness fuel
   balance and next-hour electrical ramp from executed output;
   tampered stock, gas floor, commitment or nonanticipativity
   flags must fail.
6. Count all feasible/infeasible/terminal-unmatched days for
   each controller. Compute a monetary differential **only
   when both complete six-hour physical service and match
   original terminal stock within 5e-5 MWh_LHV**.
7. Report any newly infeasible protected days, all negative
   outcomes, unresolved endpoint mismatches and nominal/joint
   policy identical commitments. Never cherry-pick a
   favorable subset. Full 92-day default; first-N flag is
   smoke only and cannot constitute population evidence.

## Reproduce without committing publisher source copies

~~~bash
python -m biogasflex source-evidence-v0921 \
  --csv /tmp/opsd_se3_original_60min.csv \
  --download \
  --output /tmp/v0921_verified_source.json

python -m biogasflex.viability_v0923 \
  --source /tmp/v0921_verified_source.json \
  --output /tmp/v0923_full_reserve_comparison.json

python scripts/audit_v0923_reserve_independent.py \
  --source /tmp/v0921_verified_source.json \
  --study /tmp/v0923_full_reserve_comparison.json \
  --output /tmp/v0923_independent_certificate.json
~~~

The entire 2019 period is historical. Economic values refer
only to hypothetical modeled CHP operations, not actual electricity
settlement or manufacturer-certified equipment.

## v1.0 release relation

See [v1.0 scientific release gates](V1_0_SCIENTIFIC_RELEASE_GATES.md).
This is a mathematical feasibility-research milestone, NOT proof
of a complete market-/site-validated decision support system.

## Independently executed 92-day results

The registered full study, unchanged nominal/maximin frozen commitments
and separate reserve witness passed [eight source-backed/cross-platform CI jobs](https://github.com/Open-Energy-Methods/biogasflex/actions/runs/44203856872).

The complete October–December 2019 holdout produced:
**63/92** feasible unprotected six-hour replays versus **92/92**
with the predeclared minimum synthetic gas witness, with **29**
recovered source days and no newly failed model paths.
Only **58** unprotected and **86** protected source days
returned to matched starting gas inventory; **six protected
days remain unmatched** and are not valid terminal-equivalent
economic comparisons.

All 92 nominal/maximin first-stage binary decisions remained
identical. The strict **57-day** original-versus-protected
same-terminal-stock/model-service comparison yielded a
mean modeled contribution difference **−EUR 0.009963723**
per hypothetical six-hour case. No earnings were imputed
to infeasible original cases.

See [executed methods and results](../reports/V0923_EXECUTED_92DAY_GAS_RESERVE.md)
and [machine-readable summary](../data/evidence/v0923_executed_92day_summary.json).
This is an independent *within-model* feasibility finding;
it does not establish a real-plant safety reserve or a
statistical future supply guarantee.
