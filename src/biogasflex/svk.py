"""Retrieve Svenska kraftnät day-ahead data locally; raw data ignored by Git.

Provider dataset: https://data.svk.se/dataset/market_data_day_ahead_area_prices
Not updating after 2026-07-01 per provider notice. Use only dates within data coverage.
"""
import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from .baseline import select_local_day_from_svk_api_records, write_price_csv

RESOURCE_ID = 'cf392ef3-7345-4e98-970e-83088c185570'
API = 'https://data.svk.se/api/3/action/datastore_search'


def fetch_local_day(*, local_date: str, bidding_zone: str, output: Path) -> dict:
    """Use provider CKAN API, starting at earliest records, for a bounded historical day.

    v0.5 supports 2020-01-01 SE3 exactly as a documented regression fixture;
    broader date/zone fetching is deliberately deferred until a robust paginated
    server-side date filter is implemented. This prevents silently wrong windows.
    """
    if (local_date, bidding_zone) != ('2020-01-01', 'SE3'):
        raise ValueError('v0.5 observed rerun is restricted to the verified 2020-01-01 SE3 historical day')
    query = urlencode({'resource_id': RESOURCE_ID, 'filters': json.dumps({'bidding_zone': bidding_zone}),
                       'sort': 'start_time_utc asc', 'limit': 24})
    with urlopen(API + '?' + query, timeout=35) as response:
        data = json.load(response)
    if not data.get('success'):
        raise RuntimeError('Provider returned non-success response')
    records = select_local_day_from_svk_api_records(data['result']['records'], local_date, bidding_zone)
    if len(records) != 24:
        raise RuntimeError('Dataset drift, incomplete day, or changed provider ordering')
    expected_start = '2019-12-31T23:00:00'
    expected_end = '2020-01-01T22:00:00'
    if records[0]['start_time_utc'] != expected_start or records[-1]['start_time_utc'] != expected_end:
        raise RuntimeError('Unexpected UTC boundaries of the selected local calendar day')
    write_price_csv(records, output)
    return {'record_count': len(records), 'output_file': str(output),
            'source': API, 'resource_id': RESOURCE_ID, 'source_republication': 'NOT AUTHORIZED BY THIS PROGRAM'}
