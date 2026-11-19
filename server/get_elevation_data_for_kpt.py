"""Resume the original 300 x 300 Open-Elevation sampling grid.

Preserves the historical floating-point stepping and six-decimal API coordinates
so that an existing headerless elevation_data.csv can be resumed safely.
"""

import csv
import logging
import math
import os
from pathlib import Path

from core.data_fetcher import ElevationConnector, ElevationFetchError

CSV_PATH = Path('elevation_data.csv')
UPPER_LEFT = (36.536380, -82.567254)
LOWER_RIGHT = (36.462897, -82.454899)
GRID_SIZE = 300
BATCH_SIZE = 250
FIELDS = ('latitude', 'longitude', 'elevation')
PRECISION = 6  # Open-Elevation output in the existing CSV is rounded to 6 decimals.

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)


def key(latitude, longitude):
    return (round(float(latitude), PRECISION), round(float(longitude), PRECISION))


def expected_grid():
    """Reproduce the ORIGINAL repeated-addition sequence, not i * step.

    This is intentional: direct multiplication would shift some rounded grid
    coordinates and cause unnecessary re-fetches when resuming the old CSV.
    """
    lat_step = (UPPER_LEFT[0] - LOWER_RIGHT[0]) / GRID_SIZE
    lng_step = (UPPER_LEFT[1] - LOWER_RIGHT[1]) / GRID_SIZE
    lat = LOWER_RIGHT[0]
    for _row in range(GRID_SIZE):
        lng = LOWER_RIGHT[1]
        for _col in range(GRID_SIZE):
            latitude, longitude = key(lat, lng)
            yield {'latitude': latitude, 'longitude': longitude}
            lng += lng_step
        lat += lat_step


def load_completed(path):
    """Support the existing headerless CSV and a conventional headered CSV."""
    completed = set()
    if not path.exists() or path.stat().st_size == 0:
        return completed, False
    with path.open('r', newline='', encoding='utf-8-sig') as handle:
        reader = csv.reader(handle)
        first = next(reader, None)
        if first is None:
            return completed, False
        has_header = [value.strip().lower() for value in first[:3]] == list(FIELDS)
        if not has_header:
            handle.seek(0)
            reader = csv.reader(handle)
        for line_no, row in enumerate(reader, start=2 if has_header else 1):
            if not row or all(not value.strip() for value in row):
                continue
            try:
                latitude, longitude, elevation = map(float, row[:3])
                if not all(math.isfinite(v) for v in (latitude, longitude, elevation)):
                    raise ValueError('nonfinite value')
                completed.add(key(latitude, longitude))
            except (ValueError, IndexError) as exc:
                raise ValueError(f'Invalid CSV record on line {line_no}: {row!r}') from exc
    return completed, has_header


def save_batch(path, results, create_header):
    """Append a validated batch, then sync it to disk before continuing."""
    with path.open('a', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        if create_header and handle.tell() == 0:
            writer.writerow(FIELDS)
        for point in results:
            writer.writerow((point['latitude'], point['longitude'], point['elevation']))
        handle.flush()
        os.fsync(handle.fileno())


def main():
    expected = list(expected_grid())
    expected_keys = {key(p['latitude'], p['longitude']) for p in expected}
    if len(expected_keys) != GRID_SIZE ** 2:
        raise RuntimeError('Generated grid contains duplicate coordinates')

    completed, has_header = load_completed(CSV_PATH)
    unrelated = completed - expected_keys
    if unrelated:
        raise RuntimeError(
            f'{len(unrelated)} CSV coordinates do not match the configured grid. '
            'Stopping to avoid mixing datasets.'
        )

    missing = [p for p in expected if key(p['latitude'], p['longitude']) not in completed]
    logger.info('Grid: %d expected, %d complete, %d missing', len(expected), len(completed), len(missing))
    if not missing:
        logger.info('Dataset already complete; no API calls needed.')
        return

    # The existing CSV is headerless; preserve that format when appending.
    # A brand-new CSV is created with a header.
    create_header = not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0

    with ElevationConnector(batch_size=BATCH_SIZE) as connector:
        for offset in range(0, len(missing), BATCH_SIZE):
            batch = missing[offset:offset + BATCH_SIZE]
            batch_no = offset // BATCH_SIZE + 1
            logger.info('Requesting batch %d (%d points)', batch_no, len(batch))
            # Connector validates count/order/coordinates and raises on failure.
            # Never append a partial or failed batch.
            results = connector.fetch_elevation_for_coords(batch)
            if len(results) != len(batch):
                raise ElevationFetchError('Incomplete API response; no data saved for this batch')
            save_batch(CSV_PATH, results, create_header)
            create_header = False
            completed.update(key(p['latitude'], p['longitude']) for p in results)
            logger.info('Saved %d points; %d / %d complete', len(results), len(completed), len(expected))

    logger.info('Finished: %d / %d grid coordinates', len(completed), len(expected))


if __name__ == '__main__':
    main()
