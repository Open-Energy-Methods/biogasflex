# Attributed observed market dataset snapshot

File: `svk_se3_20200101_CC-BY-4.0.csv`, 24 hourly observations from the Svenska kraftnät open-data service (SE3 bidding zone, local date 2020-01-01). Values EUR/MWh; timestamps UTC.

**Source:** Svenska kraftnät, *Dagen före-priser per elområde*, resource `cf392ef3-7345-4e98-970e-83088c185570`, https://data.svk.se/sv/dataset/market_data_day_ahead_area_prices/resource/cf392ef3-7345-4e98-970e-83088c185570 .

**Licence:** Creative Commons Attribution 4.0 International, https://creativecommons.org/licenses/by/4.0/ . Attribution: *Produced by Svenska kraftnät (Svk)*. The CSV is a reformatted extract (column choice and UTC offset normalized) retrieved 2026-11-05. No price observations were changed. Refer to official portal for latest corrections; provider warns of possible gaps and halted updates after 2026-07-01.

**Integrity/limitations:** This is 24 observations for one historical day, not a representative annual price sample. Independent tests assert record count, UTC boundary, average and sum. The file is openly licensed (attribution required) but secondary rights and upstream licence changes should be checked for newer snapshots.

## Additional observed days included at v0.8 (2026-11-05)

The following Svk SE3 daily samples were newly retrieved from the **same resource and CC BY 4.0 licence** as the original January 1 snapshot. Each is a complete hourly first civil day of its named month in 2020, with UTC offset normalized and observation values preserved:

- `svk_se3_2020_april_01_CC-BY-4.0.csv`: 24 hourly values, 2020-03-31T22:00:00Z through 2020-04-01T21:00:00Z; price sum 167.71 EUR/MWh.
- `svk_se3_2020_october_01_CC-BY-4.0.csv`: 24 hourly values, 2020-09-30T22:00:00Z through 2020-10-01T21:00:00Z; price sum 732.96 EUR/MWh.

**Preselected but rejected**: 2020-07-01 because the provider extraction returned an incomplete UTC hourly series (24 observations spanning 25 hourly positions). No extrapolated, silently filled, or replacement dates are present. Read `docs/V08_DATA_PROVENANCE.md` for exact selection and data-quality boundaries.
