# BiogasFlex v0.9.14-B — Internal numerical research report

**Claim:** exact finite-grid synthetic contract-feasibility experiment,
not an observed plant reliability estimate.

The `[0.2,0.6] MWh_e` 2-hour synthetic award has a unique forced
power trajectory `[0.2,0.6] MW_e`, a corresponding gas-use trajectory
`[0.5,1.5] MW_LHV` at fixed `η_e=0.4`, and gas stock
`[0,0.5,0] MWh_LHV` at exactly fixed inlet
`1 MW_LHV` and zero terminal inventory.
For this particular model, the hard contract requires
storage ≥0.5 MWh_LHV, ramp-up ≥0.4 MW_e/h,
minimum-on power ≤0.2 MW_e, backup heat ≥0.05 MW_th.
These are model-derived thresholds, **not measured hardware specifications**.

The predeclared full factorial has **81** discrete cells;
the analytical witness predicts **16 feasible and 65 infeasible**.
The independent audit must confirm every classification, not only totals.
The marginal feasibility fractions at the three levels of each factor
are `[0,8/27,8/27]` when increasing the parameter helps,
except minimum-on power which has `[8/27,8/27,0]`.
Fractions refer to counting this arbitrary design grid; not
frequentist probabilities or posterior confidence intervals.

Exactly **nine** additional one-factor tests demonstrate:
`η_e` [0.38,0.40,0.42] -> [infeasible,feasible,infeasible];
`η_th` [0.15,0.20,0.25] -> [infeasible,feasible,feasible];
`r_down` [0.25,0.40,0.60] MW_e/h ->
[infeasible,feasible,feasible].

For the fixed four-parameter subproblem and exact locked
two-slot assumptions, a wide continuous rectangle fails its
analytical worst corner, while a narrower rectangle has
all 16 corners feasible and an algebraic monotonicity
certificate over its entire interior. This **does not**
establish that any real biogas engine has these ranges,
or that a real delivery is robust to all plant uncertainties.

**Verification gate:** run `python scripts/audit_v0914b_sensitivity.py`;
a final merged milestone should reference its actual hosted
GitHub Actions 10-job result and complete inherited tests.
This text states exact algebraic expectations, not a claim
that unexecuted CI tests have passed.

See `docs/V0914B_BOUNDED_SENSITIVITY_PROTOCOL.md`.
