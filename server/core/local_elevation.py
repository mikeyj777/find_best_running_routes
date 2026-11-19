from utils import consts

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


class LocalElevationConnector:

    FEET_PER_METER = 3.280839895
    EARTH_RADIUS_M = 6371008.8

    def __init__(
        self,
        cached_elevation_location_csv=None,
        tolerance_ft=50.0
    ):
        self.cached_elevation_location = (
            cached_elevation_location_csv
            if cached_elevation_location_csv is not None
            else consts.ELEVATION_DATA_PATH
        )

        self.tolerance_ft = tolerance_ft

        self.cached_elevation_df = pd.read_csv(
            self.cached_elevation_location
        )

        # Check required columns.
        required = {"latitude", "longitude", "elevation"}
        missing = required - set(self.cached_elevation_df.columns)

        if missing:
            raise ValueError(f"Missing CSV columns: {missing}")

        # Remove invalid or missing elevation records.
        self.cached_elevation_df = (
            self.cached_elevation_df
            .dropna(subset=["latitude", "longitude", "elevation"])
            .copy()
        )

        if self.cached_elevation_df.empty:
            raise ValueError("Elevation cache contains no valid records")

        # Convert lat/lon to local Cartesian coordinates in meters.
        # Suitable for the relatively small Kingsport test region.
        self.reference_latitude = np.deg2rad(
            self.cached_elevation_df["latitude"].mean()
        )

        cached_coords = self._to_xy(
            self.cached_elevation_df["latitude"].to_numpy(),
            self.cached_elevation_df["longitude"].to_numpy()
        )

        self.tree = cKDTree(cached_coords)

        # Populated by the filter call.
        self.match_results = None

    def _to_xy(self, latitudes, longitudes):
        lat_rad = np.deg2rad(np.asarray(latitudes, dtype=float))
        lon_rad = np.deg2rad(np.asarray(longitudes, dtype=float))

        x = (
            self.EARTH_RADIUS_M
            * lon_rad
            * np.cos(self.reference_latitude)
        )

        y = self.EARTH_RADIUS_M * lat_rad

        return np.column_stack((x, y))

    def filter_lat_long_return_missing_coords(self, lat_long_on_path):

        if not lat_long_on_path:
            self.match_results = pd.DataFrame()
            return []

        requested_df = pd.DataFrame(lat_long_on_path).copy()

        requested_xy = self._to_xy(
            requested_df["latitude"].to_numpy(),
            requested_df["longitude"].to_numpy()
        )

        # Find nearest cached point for each road coordinate.
        distances_m, indices = self.tree.query(requested_xy)

        nearest = self.cached_elevation_df.iloc[indices].reset_index(
            drop=True
        )

        requested_df["nearest_latitude"] = nearest["latitude"].to_numpy()
        requested_df["nearest_longitude"] = nearest["longitude"].to_numpy()
        requested_df["elevation"] = nearest["elevation"].to_numpy()
        requested_df["distance_ft"] = (
            distances_m * self.FEET_PER_METER
        )

        requested_df["within_tolerance"] = (
            requested_df["distance_ft"] <= self.tolerance_ft
        )

        self.match_results = requested_df

        missing_df = requested_df[
            ~requested_df["within_tolerance"]
        ]

        return missing_df[
            ["latitude", "longitude"]
        ].to_dict(orient="records")