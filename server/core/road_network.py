"""OpenStreetMap road retrieval, persistent caching, and graph construction.

Bounding boxes use (south, west, north, east). Distances in graph edge
``weight`` retain the original miles convention; ``length_m`` is also stored.

Dependencies: requests, networkx. No pickle files are read.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import math
import os
import tempfile
import time
from pathlib import Path

import networkx as nx
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from utils.geo_utils import haversine_distance, interpolate_point

LOGGER = logging.getLogger(__name__)
RAW_CACHE_VERSION = 2
GRAPH_CACHE_VERSION = 2
ROAD_CLASSES = (
    "residential", "tertiary", "unclassified", "path", "track", "footway",
    "secondary", "primary", "service", "living_street", "pedestrian",
    "cycleway", "secondary_link", "tertiary_link", "primary_link",
    "road", "bridleway", "steps",
)


def _validate_bbox(bounding_box):
    if len(bounding_box) != 4:
        raise ValueError("Bounding box must be (south, west, north, east)")
    south, west, north, east = (float(x) for x in bounding_box)
    if not all(math.isfinite(x) for x in (south, west, north, east)):
        raise ValueError("Bounding box must contain finite coordinates")
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Invalid bounding box or unsupported antimeridian crossing")
    return south, west, north, east


def _key(value):
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _load_gzip_json(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def _save_gzip_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json.gz", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb") as zipped:
                zipped.write(json.dumps(data, separators=(",", ":"), allow_nan=False).encode("utf-8"))
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class OSMConnector:
    """Fetch OSM ways via Overpass with persistent raw and graph caches."""

    def __init__(self, cache_dir="cache/osm", api_url="https://overpass-api.de/api/interpreter",
                 timeout=(15, 180), retries=3):
        self.api_url = api_url
        self.cache_dir = Path(cache_dir)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "KingsportRouteFinder/1.0 (contact: mike@mylopa.app)",
            "Accept": "application/json"
        })
        retry = Retry(
            total=retries, connect=retries, read=retries, status=retries,
            backoff_factor=1.5, status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset({"POST"}), respect_retry_after_header=True,
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.mount("http://", HTTPAdapter(max_retries=retry))

    def _query(self, bbox):
        south, west, north, east = bbox
        classes = "|".join(ROAD_CLASSES)
        return (f'[out:json][timeout:180];\n'
                f'(way["highway"~"^({classes})$"]'
                f'({south},{west},{north},{east}););\n'
                'out geom;')

    def _raw_key(self, bbox):
        return _key({"version": RAW_CACHE_VERSION, "api_url": self.api_url,
                     "query": self._query(bbox)})

    def get_road_network(self, bounding_box, force_refresh=False):
        """Return raw Overpass JSON, using exact-bbox disk cache when available.

        On failure returns None, consistent with the original interface.
        """
        bbox = _validate_bbox(bounding_box)
        path = self.cache_dir / "raw" / f"{self._raw_key(bbox)}.json.gz"
        if not force_refresh and path.is_file():
            try:
                data = _load_gzip_json(path)
                if isinstance(data, dict) and isinstance(data.get("elements"), list):
                    LOGGER.info("Loaded OSM data from %s", path)
                    return data
                LOGGER.warning("Invalid raw cache at %s; fetching again", path)
            except (OSError, ValueError, TypeError) as exc:
                LOGGER.warning("Cannot read OSM cache %s: %s", path, exc)
        try:
            LOGGER.info("Querying Overpass for bbox %s", bbox)
            response = self.session.post(self.api_url, data={"data": self._query(bbox)},
                                         timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("elements"), list):
                raise ValueError("Overpass response missing elements array")
            try:
                _save_gzip_json(path, data)
            except (OSError, ValueError, TypeError) as exc:
                LOGGER.warning("Unable to save OSM raw cache: %s", exc)
            return data
        except (requests.RequestException, ValueError) as exc:
            LOGGER.error("Failed to fetch OSM data: %s", exc)
            return None

    def get_road_graph(self, bounding_box, subdivision_distance_miles=0.031,
                       force_refresh=False):
        """Return a graph, caching it separately from the raw Overpass response.

        force_refresh=True re-fetches raw OSM and rebuilds the graph. The cache
        stores node-link JSON rather than untrusted pickle objects.
        """
        bbox = _validate_bbox(bounding_box)
        if subdivision_distance_miles <= 0 or not math.isfinite(subdivision_distance_miles):
            raise ValueError("subdivision_distance_miles must be positive and finite")
        cache_key = _key({"version": GRAPH_CACHE_VERSION, "raw": self._raw_key(bbox),
                          "subdivision_distance_miles": subdivision_distance_miles})
        path = self.cache_dir / "graphs" / f"{cache_key}.json.gz"
        if not force_refresh and path.is_file():
            try:
                payload = _load_gzip_json(path)
                graph = nx.node_link_graph(payload, edges="links")
                LOGGER.info("Loaded road graph from %s", path)
                return graph
            except (OSError, ValueError, KeyError, TypeError, nx.NetworkXError) as exc:
                LOGGER.warning("Cannot load graph cache %s: %s", path, exc)
        osm_data = self.get_road_network(bbox, force_refresh=force_refresh)
        if osm_data is None:
            return nx.Graph()
        graph = build_road_graph(osm_data, subdivision_distance_miles)
        try:
            _save_gzip_json(path, nx.node_link_data(graph, edges="links"))
        except (OSError, ValueError, TypeError) as exc:
            LOGGER.warning("Unable to save road graph cache: %s", exc)
        return graph

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


def build_road_graph(osm_data, subdivision_distance_miles=0.031):
    """Build an undirected, subdivided OSM graph, preserving way metadata.

    OSM ways connect only at shared OSM node IDs, never merely where their
    geometries cross. The original edge ``weight`` is in miles.
    """
    if subdivision_distance_miles <= 0 or not math.isfinite(subdivision_distance_miles):
        raise ValueError("subdivision_distance_miles must be positive and finite")
    graph = nx.Graph()
    if not osm_data or not isinstance(osm_data.get("elements"), list):
        return graph

    for element in osm_data["elements"]:
        if element.get("type") != "way":
            continue
        node_ids = element.get("nodes", [])
        geometry = element.get("geometry", [])
        if len(node_ids) != len(geometry) or len(node_ids) < 2:
            continue
        tags = element.get("tags", {}) or {}
        metadata = {"osm_way_id": element.get("id")}
        metadata.update({k: tags.get(k) for k in (
            "highway", "name", "surface", "sidewalk", "foot", "access",
            "bridge", "tunnel", "lit", "tracktype", "smoothness",
        ) if k in tags})

        for i in range(len(node_ids) - 1):
            a, b = geometry[i], geometry[i + 1]
            if not all(k in point for point in (a, b) for k in ("lat", "lon")):
                continue
            start, end = node_ids[i], node_ids[i + 1]
            graph.add_node(start, lat=a["lat"], lon=a["lon"])
            graph.add_node(end, lat=b["lat"], lon=b["lon"])
            length_miles = haversine_distance(a, b)
            if not math.isfinite(length_miles) or length_miles < 0:
                continue
            n_segments = max(1, math.ceil(length_miles / subdivision_distance_miles))
            previous = start
            for j in range(1, n_segments + 1):
                if j == n_segments:
                    current = end
                else:
                    current = f"sub:{element.get('id')}:{i}:{j}"
                    point = interpolate_point(a, b, j / n_segments)
                    graph.add_node(current, lat=point["lat"], lon=point["lon"])
                edge_miles = haversine_distance(graph.nodes[previous], graph.nodes[current])
                graph.add_edge(previous, current, weight=edge_miles,
                               length_m=edge_miles * 1609.344, **metadata)
                previous = current

    LOGGER.info("Built road graph: %s nodes, %s edges",
                graph.number_of_nodes(), graph.number_of_edges())
    return graph
