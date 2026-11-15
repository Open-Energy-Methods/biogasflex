# BiogasFlex v0.9.11 — Independent hard-awarded-energy numerical audit

**Date:** 2026-11-15
**Status:** Software-method demonstration; entirely synthetic CHP,
accepted orders, prices, forecast assumptions, heat demand and costs.
Do not treat results as field operation, genuine Nord Pool orders,
metered grid-export electricity, balancing settlement, or profit.

## Research question

Can an accepted energy schedule that is *not* the unconstrained
economic optimum nonetheless be dispatched exactly while satisfying
the CHP MILP's original heat, gas mass balance, finite gas storage,
binary on/off, elapsed-hour ramp, dwell and terminal-stock constraints?

The earlier v0.9.10 post-clearing check rejected any awarded volume
different from the uncontracted optimum. A different schedule
might be feasible but financially inferior. Rejecting it solely
because of unconstrained optimization was a methodological error.

## New exact constraint and limits

For each interval `t`:

```text
fuel_use[t] [MW_LHV] × electric_eta [-] × interval_duration[t] [h]
  = accepted_contract_energy[t] [MWh_e]
```

This is an equality inside **the MILP model**, not an independent
post-solve correction. The original binary/ramp/dwell/gas/heat/terminal
constraints stay intact. The continuous LP relaxation is solved using
the identical *augmented* constraint matrix and remains a genuine
mathematical upper bound on that specific awarded contract.

The constrained output independently recomputes generated
`power_MW × dt_h` and fails if the maximum award-energy discrepancy
exceeds `1e-7 MWh_e`. A physically feasible *fixed* comparator is
not treated as feasible under this awarded model unless it also
satisfies every contracted MWh. This prevents a misleading
dominance assertion against a schedule with different obligations.

## Independent, hand-computed positive oracles

| Scenario | Duration | Accepted MWh_e | Required electrical MW_e | End gas stock MWh_LHV | Gross contract proxy EUR |
| --- | --- | --- | --- | --- | ---: |
| Two-slot | [1h,1h] | [0.2,0.6] | [0.2,0.6] | [0.5,0] | 20 |
| Four-slot | [0.25h]×4 | [0.05,0.15,0.10,0.10] | [0.2,0.6,0.4,0.4] | [0.125,0,0,0] | 9 |

Both use **invented** 1 MW_LHV per-hour biogas production,
40% CHP electrical efficiency, no original gas inventory and
0.5 MWh_LHV storage capacity. Synthetic thermal-efficiency,
auxiliary heat, dump and commitment constraints are explicitly
specified by `examples/v0911_synthetic_chp.json`.

For the two-hour contract, the accepted schedule needs gas
use [0.5,1.5] MW_LHV: first hour stores 0.5 MWh,
second consumes it. The **uncontracted** optimum produces
[0.4,0.4] MWh_e with invented cleared prices
[100,0] EUR/MWh, worth EUR40 as a *gross* electricity
proxy. The **awarded** [0.2,0.6] schedule is still
physically feasible, but its gross contract proxy is
**EUR20**. This counterexample proves the need to
constrain accepted quantities during solving.

For four quarter-hour periods, gas consumption
[0.125,0.375,0.25,0.25] MWh_LHV balances 1 MWh total
production, with post-slot storage [0.125,0,0,0].
At fictional prices [100,0,20,20] EUR/MWh,
gross accepted proxy:
0.05×100 + 0.15×0 + 0.1×20 + 0.1×20 = **EUR9**.
This independently checks the MW-to-MWh conversion.

The gross contractual proxy is **not additional**
revenue on top of the solver's net economic contribution:
the latter already values electric output. Double counting
or describing the proxy as plant profit is prohibited.

## Truly infeasible-award witnesses

Original uncontracted CHP remains feasible but the
following altered awards cannot be met **under the
declared constraints**:

- Storage cap 0.1 MWh_LHV vs required intermediate stock
  of 0.5 MWh_LHV for the 2h accepted schedule
- Strict continuous-ON ramp 0.05 MW_e/h that cannot
  change .4 MW_e initial output to .2 MW_e at the
  first slot midpoint
- First-hour 0.25 MW_th useful heat demand with
  backup limited 0.1 MW_th; awarded first-period
  generation supplies too little recovered heat
- Nonzero terminal gas-stock target inconsistent
  with the contracted electricity that consumes all
  net gas production
- Zero awards when the total production cannot
  be accommodated by existing storage/losses without
  electricity generation

All scenarios fail closed with
`CONTRACT_INFEASIBLE`. No uncontracted energy
is silently sold, balanced, or treated as exported.

## Backward compatibility and reproducibility

The original `optimize_commitment_milp(config,prices)`
and `market-boundary` default return their prior
uncontracted results. Only explicit
`contracted_delivery_mwh=...` in the solver or
`hard_contract=True` in the post-clear adapter
activates v0.9.11 constraints.

The earlier 286 original pinned scientific
source/result files and independently audited
216 primal-dual certificates, 96 solver-free LP
comparisons, 216+5 historical/hypothetical source
cases, and v0.9.5–v0.9.10 software research oracles
remain mandatory verification gates.
Release-integrity SHA256 and exact CI evidence
are recorded in the merge PR and GitHub Actions.

```bash
python -m pip install -e .
bash scripts/reproduce_v0911.sh
python scripts/audit_v0911_hard_contract.py
python -m biogasflex contract-dispatch
python -m biogasflex contract-dispatch --manifest examples/v0911_contract_quarterhour.json
```

On Windows: `./scripts/reproduce_v0911.ps1`.

## Critical remaining limits

The modelled contracted MWh are **CHP generator-terminal
electricity**, not metered electrical export at an
interconnection. Fixed efficiencies, gas availability,
heat demand and operating boundaries are invented;
bid size, block-order rules, actual participant
clearing, nominations, imbalance fees, network limits
and real industrial CHP transients are not validated.
Even a software-perfect hard contract is **not evidence
of real market trading feasibility or net profit**.

The next worthwhile research increment requires
source-verifiable as-of published ex-ante market
information and measured plant/export envelopes.
External scientific review is still unresolved in
[issue #3](https://github.com/Open-Energy-Methods/biogasflex/issues/3).
