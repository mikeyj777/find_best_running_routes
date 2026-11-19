"""Elevation retrieval utilities for the Open-Elevation API."""

import logging
import math
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

LOGGER = logging.getLogger(__name__)


class ElevationFetchError(RuntimeError):
    """Raised when a complete, validated elevation profile cannot be retrieved."""


class ElevationConnector:
    """Retrieve elevations in batches without silently returning partial results.

    The public Open-Elevation service may enforce coordinate quotas and rate limits.
    Batch size changes HTTP request count, not the number of coordinates billed.
    """

    def __init__(
        self,
        batch_size: int = 250,
        api_url: str = "https://api.open-elevation.com/api/v1/lookup",
        timeout: Tuple[float, float] = (10, 60),
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        pause_seconds: float = 0.2,
        session: Optional[requests.Session] = None,
        api_key: Optional[str] = None,
    ) -> None:
        if not isinstance(batch_size, int) or isinstance(batch_size, bool) or batch_size < 1:
            raise ValueError("batch_size must be a positive integer")
        if not isinstance(max_retries, int) or isinstance(max_retries, bool) or max_retries < 0:
            raise ValueError("max_retries must be a nonnegative integer")
        if backoff_factor < 0 or pause_seconds < 0:
            raise ValueError("backoff_factor and pause_seconds must be nonnegative")
        self.api_url = api_url
        self.batch_size = batch_size
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.pause_seconds = pause_seconds
        self.session = session or requests.Session()
        self._owns_session = session is None
        self.session.headers.update({"Accept": "application/json"})
        
        if api_key is not None:
            self.session.headers.update({
                "X-API-Key": api_key
            })

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def __enter__(self) -> "ElevationConnector":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    @staticmethod
    def _validate_coordinates(coordinates: Sequence[Dict[str, Any]]) -> List[Dict[str, float]]:
        validated = []
        for index, point in enumerate(coordinates):
            if not isinstance(point, dict):
                raise ValueError(f"Coordinate {index} must be an object")
            try:
                latitude = float(point["latitude"])
                longitude = float(point["longitude"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"Coordinate {index} requires numeric latitude and longitude") from exc
            if not math.isfinite(latitude) or not -90 <= latitude <= 90:
                raise ValueError(f"Coordinate {index} has an invalid latitude")
            if not math.isfinite(longitude) or not -180 <= longitude <= 180:
                raise ValueError(f"Coordinate {index} has an invalid longitude")
            validated.append({"latitude": latitude, "longitude": longitude})
        return validated

    @staticmethod
    def _validate_results(batch: List[Dict[str, float]], results: Any) -> List[Dict[str, Any]]:
        if not isinstance(results, list) or len(results) != len(batch):
            raise ElevationFetchError(
                f"Expected {len(batch)} results, received "
                f"{len(results) if isinstance(results, list) else 'invalid data'}"
            )
        for index, (requested, returned) in enumerate(zip(batch, results)):
            if not isinstance(returned, dict):
                raise ElevationFetchError(f"Result {index} is not an object")
            try:
                elevation = float(returned["elevation"])
                latitude = float(returned["latitude"])
                longitude = float(returned["longitude"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ElevationFetchError(f"Result {index} is missing valid fields") from exc
            if not all(map(math.isfinite, (elevation, latitude, longitude))):
                raise ElevationFetchError(f"Result {index} contains nonfinite values")
            # The service may round coordinates; tolerate sub-meter differences.
            if (abs(latitude - requested["latitude"]) > 0.00001 or
                    abs(longitude - requested["longitude"]) > 0.00001):
                raise ElevationFetchError(f"Result {index} does not match requested coordinate")
        return results

    def _fetch_batch(self, batch: List[Dict[str, float]], batch_number: int) -> List[Dict[str, Any]]:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.post(
                    self.api_url,
                    json={"locations": batch},
                    timeout=self.timeout,
                )
                if response.status_code in (408, 429, 500, 502, 503, 504):
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        try:
                            wait = max(0.0, float(retry_after)) if retry_after else 0.0
                        except ValueError:
                            wait = 0.0
                        wait = max(wait, self.backoff_factor * (2 ** attempt))
                        LOGGER.warning("Batch %d HTTP %d; retrying in %.1fs", batch_number, response.status_code, wait)
                        time.sleep(wait)
                        continue
                response.raise_for_status()
                try:
                    payload = response.json()
                except ValueError as exc:
                    raise ElevationFetchError(f"Batch {batch_number} returned invalid JSON") from exc
                if not isinstance(payload, dict):
                    raise ElevationFetchError(f"Batch {batch_number} returned an invalid response")
                return self._validate_results(batch, payload.get("results"))
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
                if attempt < self.max_retries:
                    wait = self.backoff_factor * (2 ** attempt)
                    LOGGER.warning("Batch %d network error; retrying in %.1fs: %s", batch_number, wait, exc)
                    time.sleep(wait)
                    continue
                raise ElevationFetchError(f"Batch {batch_number} failed after retries: {exc}") from exc
            except requests.exceptions.RequestException as exc:
                raise ElevationFetchError(f"Batch {batch_number} HTTP request failed: {exc}") from exc
        raise ElevationFetchError(f"Batch {batch_number} failed")

    def fetch_elevation_for_coords(self, coordinates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Return all elevations in input order or raise an exception.

        An empty input returns an empty list. No partial result is ever returned.
        """
        if coordinates is None:
            raise ValueError("coordinates cannot be None")
        validated = self._validate_coordinates(coordinates)
        if not validated:
            return []
        results: List[Dict[str, Any]] = []
        total_batches = (len(validated) + self.batch_size - 1) // self.batch_size
        for batch_index, start in enumerate(range(0, len(validated), self.batch_size)):
            batch_number = batch_index + 1
            batch = validated[start:start + self.batch_size]
            LOGGER.info("Fetching elevation batch %d/%d (%d points)", batch_number, total_batches, len(batch))
            results.extend(self._fetch_batch(batch, batch_number))
            if batch_number < total_batches and self.pause_seconds:
                time.sleep(self.pause_seconds)
        return results


def process_elevation_request(request_data: Any) -> Tuple[Dict[str, Any], int]:
    """Validate a Flask JSON payload and retrieve a complete elevation profile."""
    if not isinstance(request_data, dict) or "path" not in request_data:
        return {"error": "Invalid request: Missing 'path' in JSON body"}, 400
    path = request_data["path"]
    if not isinstance(path, list) or not path:
        return {"error": "'path' must be a nonempty list"}, 400
    try:
        coordinates = []
        for index, point in enumerate(path):
            if not isinstance(point, dict) or "lat" not in point or "lng" not in point:
                raise ValueError(f"Path point {index} must contain lat and lng")
            coordinates.append({"latitude": point["lat"], "longitude": point["lng"]})
        with ElevationConnector() as connector:
            elevation_data = connector.fetch_elevation_for_coords(coordinates)
        return {"status": "success", "elevationProfile": elevation_data}, 200
    except ValueError as exc:
        LOGGER.warning("Invalid elevation request: %s", exc)
        return {"error": str(exc)}, 400
    except ElevationFetchError as exc:
        LOGGER.error("Elevation service failure: %s", exc)
        return {"error": "Failed to fetch a complete elevation profile from external API"}, 502
    except Exception:
        LOGGER.exception("Unexpected error processing elevation request")
        return {"error": "An internal server error occurred"}, 500
