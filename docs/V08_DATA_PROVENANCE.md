# v0.8 observed market-data and study provenance

**Provider:** Svenska kraftnät (Swedish TSO), *Market data day-ahead prices*, resource `cf392ef3-7345-4e98-970e-83088c185570`, public data-service catalog: https://data.svk.se/dataset/market_data_day_ahead_area_prices . Attribution: **Produced by Svenska kraftnät (Svk)**. Dataset license: **CC BY 4.0**, https://creativecommons.org/licenses/by/4.0/ . Historical data is not guaranteed complete; the provider's catalog warns that updates have stopped.

**Selection rule established before results:** first local civil day (Europe/Stockholm) of January, April, July, October **2020** in bidding zone SE3. These are chosen as quarter-start anchors, NOT as high- or low-value outcomes. July 1 failed provider sequence completeness; no replacement date was selected and no interpolation performed. The retained sample is therefore intentionally limited to three distinct, non-overlapping days, not four quarters or one representative year. Dates must not be interpreted as random sampling.

| File | Original local date | UTC first | UTC last | Count | Gross sum of hourly prices (EUR/MWh) |
|---|---|---|---|---:|---:|
| `svk_se3_20200101_CC-BY-4.0.csv` | 2020-01-01 | 2019-12-31T23:00 | 2020-01-01T22:00 | 24 | 665.68 |
| `svk_se3_2020_april_01_CC-BY-4.0.csv` | 2020-04-01 | 2020-03-31T22:00 | 2020-04-01T21:00 | 24 | 167.71 |
| `svk_se3_2020_october_01_CC-BY-4.0.csv` | 2020-10-01 | 2020-09-30T22:00 | 2020-10-01T21:00 | 24 | 732.96 |

**Provider retrieval:** via public CKAN `datastore_search` at `https://data.svk.se/api/3/action/datastore_search`, filtering `bidding_zone=SE3`, sorting `start_time_utc asc`, selecting provider rows for each local civil day. The initial July-day extraction returned 24 records covering UTC 2020-06-30T22:00 through 2020-07-01T22:00 (25-hour timestamp span), inconsistent with a complete 24-hour civil-day hourly series. The study records the date as rejected without altering values. Note the provider resource is not assumed complete in every historical month.

**Transformations:** retain observed price values and EUR/MWh units; convert provider ISO timestamp with UTC timezone marker for unambiguous parsing; select only four CSV fields; sort by UTC time. Price files are shipped for offline reproducibility with the stated attribution and the original URL. File SHA-256 hashes appear in `results/v0.8/v08_study_summary.json` and can be independently recomputed. Source rows may be rechecked against the provider API if still accessible.

**Counterfactual reference:** Åberg (2024), SLU thesis referring to Lövsta 2022 annual generation of 3,002.6 MWh_e, heat production 2,939.5 MWh_th, CHP 499 kW_e. We combine those 2022 plant-level annual observations with **2020 day-ahead price observations** and synthetic operating conditions; this is not a contemporaneous historical backtest or a plant validation.

**Sensitivity registry:** `scenarios/registry.json` freezes the scenario factors and market windows and is SHA-256 hashed. The human-readable `registry.yaml` is only a mirror; no YAML reader is required. The study uses no uncertain probability distributions or confidence intervals.
