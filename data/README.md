Synthetic 4-hour prices are independently invented and are not representative of observed Swedish prices. They are licensed with the project's original code.

The observed price retrieval script queries Svenska kraftnät's historical day-ahead prices. The dataset is public and available without fee, but explicit redistribution authorization for copied price rows has **not** been established here. `data/external/` is Git-ignored; no observed hourly/quarter-hour records are redistributed in the public package. Users can retrieve observations directly from the provider in their own environment if they are entitled to do so.

Dataset caveat: provider warns it is no longer updating after 2026-07-01 and may have gaps. v0.5 intentionally restricts observed regression to SE3 2020-01-01, which is 24 one-hour observations before the 2025 quarter-hour market change.
