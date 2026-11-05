# BiogasFlex v0.9 — external reviewer packet

**Review request**: independent methodological/software review of a *simulation-only* small study. Review is requested, not completed. The developer's AI-assisted checking must not be described as external peer review. No LiU/BSRC association is claimed.

## What to evaluate

1. **Scientific question** — In a stylized CHP system with externally imposed constant gas supply and a finite gas inventory buffer, how does perfect-foresight re-timing of fuel use affect a 24-hour electricity-price value *after contemporaneous heat service and specified operating costs*?
2. **Physical formulation** — Are LHV-based gas inventory, electrical conversion, heat co-product, cyclic stock and peak electrical rating constraints dimensionally coherent? How much would omitted part-load efficiency, minimum load, start/ramp costs or heat storage affect findings?
3. **Economic objective** — Is the chosen marginal backup heat cost legitimately a synthetic sensitivity parameter rather than an empirically estimated cost? Are energy revenue, net operating contribution proxy and project profitability kept apart?
4. **Source integrity** — Verify the original Åberg (2024) Lövsta table and Svenska kraftnät's CC BY 4.0 SE3 observed input. Price data reflect 2020; annual plant reference is 2022. Verify the July exclusion; do not infer representative annual sampling.
5. **Optimization mathematics** — Derive the LP equations independently, check dual feasibility/optimality on at least one two-interval test, and challenge constraint direction/tolerance handling.
6. **Resilience** — Challenge the assumed precharged gas store and island/availability gates. Does the model establish only conditional electric/heat energy fractions, not real black start or local self-sufficiency? The service objective weights electricity shortages 10:1 versus heat shortages; that is an arbitrary priority preference.
7. **Reproducibility** — Clean environment, no data credentials, Python>=3.10, SciPy>=1.11<2. Invoke `bash scripts/reproduce_v09.sh`; manually inspect failed-test/tamper behavior.
8. **Claims table** — Check `docs/V09_CLAIMS_EVIDENCE.csv` entry-by-entry and report claims that exceed available evidence.

## Materials and expected results

- `README.md`, `docs/V08_MODEL_BOUNDARY.md`, `docs/V09_FROZEN_INPUT_HASHES.json`, `docs/V09_CLAIMS_EVIDENCE.csv`.
- `src/biogasflex/heat_dispatch.py` core unchanged from v0.8; `src/biogasflex/resilience.py` has a zero-inflow-boundary repair.
- `scenarios/registry.json`: 216 cases and five emergency cases, immutable input SHA. `data/observed/` contains three CC BY 4.0 price snapshots.
- `scripts/independent_v08_audit.py`: independent output arithmetic; `scripts/audit_v09_candidate.py`: new frozen-source and input-contract checks.
- `tests/test_v09_audit_contract.py`: hand oracle and malicious-data mutations.
- `reports/V09_RELEASE_AUDIT.md`: internal results, severity classifications, decision and open issues.

## Structured review response template

For each finding, identify: **ID; severity (fatal/major/minor/editorial); exact file and line; reproduction; physical or research impact; proposed fix; tests needed; reviewer independence / conflicts**. Report disagreements and null findings. Distinguish a reproducible coding bug from omitted physics that the research paper already excludes from its claim boundary.

**Human review is presently outstanding.** This file is an invitation/review brief, not a signed review or accepted journal manuscript.
