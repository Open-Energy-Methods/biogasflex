# Data access and reuse — evidence update 2026-11-05

**Resolved:** The Svenska kraftnät (Svk) day-ahead area-price *resource* explicitly lists **CC BY 4.0** both in dataset metadata and resource format. Original source and attribution notice: https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/cf392ef3-7345-4e98-970e-83088c185570 . Creative Commons terms: https://creativecommons.org/licenses/by/4.0/ .

An attributed, reformatted 2020-01-01 SE3 24-record CSV snapshot is now in `data/observed`. Transformations: trimmed to zone SE3 and date, normalized UTC-offset syntax, reduced to four columns. Original EUR/MWh prices unchanged. No claim of actual electricity sales or market participation is implied.

The dataset contains historical day-ahead prices, not measured CHP operations. It may have gaps; metadata warns it stopped updating after July 1 2026. New time windows require completeness validation, including 23/25h daylight-saving transition days and quarter-hour periods after 2025-10-01.

**Plant reference:** Lövsta annual electricity, heat and rated motor values are reproduced as facts from an SLU 2024 thesis reporting 2022 data received from the plant. The thesis is a secondary publication of facility-supplied data. We do not republish thesis text or tabulated material beyond short isolated numerical facts, and we do not claim measured hourly operation or independently audited field data.

**Scenario caveat:** The Lövsta case uses **2022 annual energy and nameplate facts** to construct an assumed *constant mean* dispatch schedule, priced using **2020-01-01** observed SE3 prices. It is a cross-year numerical counterfactual, not Lövsta's 2020 or 2022 revenue and not a measured 2020 plant operation.
