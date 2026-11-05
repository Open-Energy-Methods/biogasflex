# v0.7 assumptions and provenance register

| Input or method | Source category | Quantification | Permitted interpretation |
|---|---|---|---|
| Lövsta nominal electrical rating | Documented plant detail quoted in Alexander Åberg (2024), SLU thesis | 499 kWe | Nameplate reference for cross-year scenario, *not* verified available hourly headroom |
| Lövsta electricity 2022 | Same thesis, citing plant records | 3,002.6 MWh | Annual generation, not site export or hourly profile |
| Lövsta produced heat 2022 | Same thesis | 2,939.5 MWh | Annual **heat production**; not observed load, sales or tariff |
| SE3 spot day | Svenska kraftnät, data.svk.se, licensed snapshot | 1 Jan 2020, 24 × 1 h, EUR/MWh | Observed price inputs, not plant revenue |
| Gas supply for counterfactual | Derived under assumed constant electric efficiency | 0.856906 MW_LHV | Hypothetical constant gas supply, not measured gas flow |
| Electric efficiency | Assumed | 0.4 LHV | Illustration only; no verified part-load efficiency |
| Heat conversion efficiency | Algebraically chosen to match annual heat:electric ratio | 0.39159395 LHV | Not independent plant-calibrated efficiency |
| Gas storage | Assumed | 1 MWh_LHV | Scenario energy capacity, *not* identified site tank |
| Heat service demand | Assumed from annual heat **production** average | 2,939.5 / 8,760 = 0.33555936 MW_th per hour | **Proxy** for a sensitivity test, not actual thermal demand |
| Auxiliary heater/sink capacities | Assumed | both 0.5 MW_th | Feasibility scenario, no equipment evidence |
| Auxiliary marginal heat cost | Assumed sensitivity grid | [0, 5, 10, 20, 80, 200] EUR/MWh_th | Screening coefficient, not site costs |
| Heat demand multipliers | Assumed sensitivity grid | [0, 0.75, 1, 1.1] | Comparative hypothetical demand, not demand observations |
| Dump penalty / variable CHP cost | Assumed zero for principal scenario | 0 EUR/MWh | Excluded, **not asserted zero** in real plants |
| Optimization solver | SciPy linprog / HiGHS continuous LP | Perfect foresight, instantaneous power modulation | Mathematical optimum under limited constraints only |
| Heat-use-first allocation | Model convention | `min(potential CHP heat, D)` | Source temperature and network constraints omitted |

Primary retrieval/attribution details and dataset checks are preserved in v0.5.1 `data/observed/README.md` and v0.6 `docs/plant_reference_and_boundaries.md`. SLU thesis: https://stud.epsilon.slu.se/20493/1/aberg-a-20240904.pdf. Observed dataset: https://data.svk.se/dataset/market_data_day_ahead_area_prices (dataset record at `docs/sources.csv`). This work does not claim participation by, review from, or endorsement by the named institution/plant/BSRC.

**Data-year integrity:** market inputs = 2020-01-01; documented plant aggregate = calendar 2022; current model = 2026 research study. No observed temporal pairing exists. Aggregating or extrapolating the selected day to a typical month or year is prohibited without sampling/stress-test justification.
