# BiogasFlex v0.5 — Implementation and verification report

**Status:** local implementation and internal verification complete; external scientific review, named-plant calibration, and price-data redistribution approval are **not** complete. This is a v0.5 research demonstrator, not a verified commercial plant model.

**Run date:** 2026-11-05.

## Work completed

- Implemented a dependency-free Python fixed-dispatch CHP model with gas-LHV, electrical and thermal-potential energy ledgers and gross day-ahead electricity revenue.
- Added an anonymous Svenska kraftnät (Svk) historical day-ahead price fetcher for one documented **SE3 2020-01-01 local day**; source provider resource ID `cf392ef3-7345-4e98-970e-83088c185570`.
- Acquired 24 complete hourly observations through the source API for this test, checked UTC boundaries, and generated aggregate model results. **The observations are excluded from public package pending clarification of row-redistribution rights.**
- Implemented a fully offline synthetic four-hour example for code reproducibility without internet or proprietary inputs.
- Created provenance, explicit hypothetical-plant assumptions, and reuse-rights documentation.

## Input boundaries

- Gas input: **0.6 MW LHV assumed**, constant.
- Electrical efficiency: **40% assumed**, thermal efficiency: **45% assumed**.
- Electrical rating: **0.4 MW assumed**, giving 0.24 MW continuous output and 40% nominal power headroom relative to maximum rating.
- Results do not represent measurements or simulation validation of any specific Swedish plant.
- Potential CHP heat production is reported; useful heat service and economics are not modelled.
- No gas storage, digestion response, optimization, policy instruments, or resilience benefits are modelled in v0.5.

## Results and independent arithmetic check

| Quantity | Synthetic 4-hour fixture | Historical-price 24-hour fixture |
|---|---:|---:|
| Duration (hours) | 4 | 24 |
| Gas consumed (MWh LHV) | 2.4 | 14.4 |
| Electricity generated (MWh) | 0.96 | 5.76 |
| Thermal energy potentially produced (MWh) | 1.08 | 6.48 |
| Gross day-ahead electric revenue (EUR) | 15.60 | 159.7632 |

For the historical-price fixture, the retrieved 24 hourly SE3 prices sum to **665.68 EUR/MWh** (the sum of 24 quotes, not an individual price), average **27.7366666667 EUR/MWh**, with minimum **24.81** and maximum **30.46 EUR/MWh**. Independent arithmetic: fixed power 0.6 × 0.4 = **0.24 MW**; fuel used 0.6 × 24 = **14.4 MWh**, electric output 0.24 × 24 = **5.76 MWh**, potential heat 0.6 × 0.45 × 24 = **6.48 MWh**; gross revenue 0.24 × 665.68 = **159.7632 EUR**.

These are model outputs for a **hypothetical CHP facility under observed market prices**, not actual plant earnings. Gross revenue omits OPEX, plant CAPEX, biogas costs, heat-service value, tariffs, balancing and transaction costs.

## Automated verification

Ran `PYTHONPATH=src python -m unittest discover -s tests -v` on 2026-11-05: **15 tests passed**. Coverage includes synthetic oracle, fuel/energy/revenue arithmetic, invalid inputs, duplicate timestamps, missing intervals, non-finite and negative prices, UTC offsets, spring/autumn DST day selection and 15-minute intervals. The 24-hour historical run is a documented provider-backed sample, not a continual integration test: a future data-access change could break it.

## Gate assessment

- [x] Reproducible offline fixed-dispatch baseline.
- [x] Assumptions separated from observed price data.
- [x] Conserved gas input to electrical and potential thermal energy using stipulated efficiencies.
- [x] CHP nameplate headroom under explicit illustrative assumptions.
- [x] Observed one-day SE3 price dataset acquired and independently aggregated.
- [x] Source and data-rights register.
- [x] Internal code tests and manual arithmetic review.
- [ ] Plant-specific rating/production supported by an individual facility reference — **open**.
- [ ] Permission to republish source price records — **open**; excluded from release.
- [ ] External independent technical review — **open**.

**Decision:** a useful **v0.5 development candidate**, not a fully source-backed plant case or independently reviewed research release. The next work should close open source/plant gate items before treating results as empirical evidence or moving to production optimization.


## Addendum — source-backed reference and licence audit (2026-11-05)

The following supersedes the above **open** entries on source-backed site rating and market-price rights, without changing the original candidate's historical status:

- **Plant reference conditionally closed:** SLU thesis (Åberg 2024) Table 1 reproduces Lövsta 2022 499 kWe rating, 3,002.6 MWh electric output, 2,939.5 MWh heat production. The annual-average constant-power case is a **stylized cross-year counterfactual** priced at 2020 SE3 day-ahead prices; neither hourly dispatch capability nor observed revenue is established.
- **Market data licence closed:** Svk resource metadata explicitly states CC BY 4.0. Added reformatted 24-row CC BY 4.0 CSV with source link, attribution, licence link and change disclosure. Raw publisher observations are otherwise unaltered.
- **Second-pass critical audit completed:** see V05_INDEPENDENT_AUDIT.md. This is AI-assisted internal technical review, **not independently signed external peer review**. A human technical reviewer and actual plant calibration remain unresolved.
- **New regression tests:** observed snapshot integrity, published rating/annual average, counterfactual energy/revenue oracle and licence attribution. Total test count now 19.

Scope is unchanged: no storage optimization, resilience valuation, site-specific heat-service constraints or actual electricity export data. These distinctions must survive any future release or LinkedIn write-up.
